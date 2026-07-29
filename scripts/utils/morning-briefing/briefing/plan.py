"""Regelbasierte Priorisierung und Tagesplanung.

Die lokalen Regeln entscheiden über die Dringlichkeit. Die KI liefert Sprache
und Vorschläge, darf aber harte Signale wie einen Systemausfall oder eine
gesetzte Frist nicht abschwächen.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta

from .models import Briefing, Bucket, Item, PlannedTask, Priority, Source, SourceStatus
from .normalize import source_label
from .summarize import AiTask

_CRITICAL_WORDS = (
    "offline",
    "ausfall",
    "down",
    "notfall",
    "kritisch",
    "critical",
    "produktion steht",
    "nicht erreichbar",
    "totalausfall",
)
_HIGH_WORDS = (
    "dringend",
    "asap",
    "eskalation",
    "sla",
    "wartet",
    "blockiert",
    "urgent",
    "sofort",
)
_INFO_WORDS = (
    "gute besserung",
    "fyi",
    "zur info",
    "newsletter",
    "keine aktion",
    "danke",
    "willkommen",
)
_TODAY_WORDS = ("heute", "today", "noch heute", "bis heute")
_TOMORROW_WORDS = ("morgen", "tomorrow")
_ACTION_HINTS = (
    ("freigeben", "Freigabe erteilen"),
    ("zugriff", "Zugriff einrichten"),
    ("anlegen", "Benutzer oder Eintrag anlegen"),
    ("antworten", "Antwort senden"),
    ("rückmeldung", "Rückmeldung geben"),
    ("prüfen", "Vorgang prüfen"),
    ("termin", "Termin abstimmen"),
)


def classify(item: Item, now: datetime) -> tuple[Priority, str]:
    """Bestimmt Priorität und Begründung ausschließlich aus lokalen Signalen."""
    text = f"{item.title} {item.body}".lower()

    if item.priority is Priority.CRITICAL or any(w in text for w in _CRITICAL_WORDS):
        return Priority.CRITICAL, "Systemausfall oder als kritisch gemeldet"

    if item.due_at and item.due_at.date() <= now.date():
        return Priority.HIGH, "Frist läuft heute ab"

    if item.source is Source.AUTOTASK and item.priority.rank <= Priority.HIGH.rank:
        return Priority.HIGH, "Kundenticket mit hoher Priorität"

    if any(w in text for w in _HIGH_WORDS):
        return Priority.HIGH, "Kunde oder Kollege wartet auf Rückmeldung"

    if _mentions_today(item, now):
        return Priority.HIGH, "Für heute zugesagt oder angefragt"

    if item.source is Source.AUTOTASK:
        return Priority.NORMAL, "Offenes Ticket"

    if item.mentioned:
        return Priority.NORMAL, "Direkte Erwähnung"

    if any(w in text for w in _INFO_WORDS) and "?" not in text:
        return Priority.INFO, "Information ohne Aufgabe"

    return Priority.NORMAL, "Offene Nachricht"


def _mentions_today(item: Item, now: datetime) -> bool:
    """Wertet relative Zeitangaben gegen den Empfangszeitpunkt aus."""
    text = f"{item.title} {item.body}".lower()
    received_day = item.received_at.date()
    today = now.date()

    if any(w in text for w in _TODAY_WORDS) and received_day == today:
        return True
    # "morgen" von gestern meint heute.
    if any(w in text for w in _TOMORROW_WORDS) and received_day == today - timedelta(days=1):
        return True
    return False


def derive_actions(item: Item) -> list[str]:
    text = f"{item.title} {item.body}".lower()
    actions = [label for needle, label in _ACTION_HINTS if needle in text]
    return actions[:3] or ["Vorgang sichten"]


def fallback_summary(item: Item) -> str:
    """Kurzfassung ohne KI, damit der Lauf auch offline nutzbar bleibt."""
    snippet = re.sub(r"\s+", " ", item.body).strip()
    if len(snippet) > 160:
        snippet = snippet[:160].rsplit(" ", 1)[0] + " ..."
    title = item.title.strip()
    if title and snippet:
        return f"{item.sender}: {title} - {snippet}"
    return f"{item.sender}: {title or snippet or 'Neue Nachricht'}"


def _bucket_for(priority: Priority, due_today: bool) -> Bucket:
    if priority is Priority.CRITICAL:
        return Bucket.NOW
    if priority is Priority.HIGH or due_today:
        return Bucket.TODAY
    if priority is Priority.INFO:
        return Bucket.INFO
    if priority is Priority.LOW:
        return Bucket.TOMORROW
    return Bucket.TODAY_OPTIONAL


def free_slots(
    meetings: list[Item],
    day: date,
    work_start: str,
    work_end: str,
    lunch: tuple[str, str],
    slot_minutes: int,
    now: datetime,
) -> list[datetime]:
    """Berechnet freie Startzeiten zwischen den Terminen des Tages."""
    start = datetime.combine(day, _parse_time(work_start), tzinfo=now.tzinfo)
    end = datetime.combine(day, _parse_time(work_end), tzinfo=now.tzinfo)
    blocked = [
        (m.starts_at, m.ends_at or m.starts_at + timedelta(minutes=30))
        for m in meetings
        if m.starts_at
    ]
    blocked.append(
        (
            datetime.combine(day, _parse_time(lunch[0]), tzinfo=now.tzinfo),
            datetime.combine(day, _parse_time(lunch[1]), tzinfo=now.tzinfo),
        )
    )

    cursor = max(start, now.replace(second=0, microsecond=0))
    step = timedelta(minutes=slot_minutes)
    slots: list[datetime] = []
    while cursor + step <= end:
        overlap = any(b_start < cursor + step and cursor < b_end for b_start, b_end in blocked)
        if not overlap:
            slots.append(cursor)
        cursor += step
    return slots


def _parse_time(value: str) -> time:
    hour, _, minute = value.partition(":")
    return time(int(hour), int(minute or 0))


def build_briefing(
    items: list[Item],
    statuses: list[SourceStatus],
    now: datetime,
    config,
    ai_tasks: list[AiTask] | None = None,
    ai_note: str = "",
) -> Briefing:
    """Verbindet lokale Regeln, KI-Zusammenfassungen und Kalender zu einem Plan."""
    ai_by_id = {task.item_id: task for task in (ai_tasks or [])}
    meetings = sorted(
        (i for i in items if i.is_calendar and i.starts_at),
        key=lambda i: i.starts_at,
    )
    workload = [i for i in items if not i.is_calendar]

    tasks: list[PlannedTask] = []
    for item in workload:
        local_priority, reason = classify(item, now)
        ai = ai_by_id.get(item.id)

        priority = local_priority
        if ai and ai.priority:
            # Die KI darf hochstufen, aber harte lokale Signale nicht abschwächen.
            priority = ai.priority if ai.priority.rank < local_priority.rank else local_priority

        due_today = bool(ai and ai.due in {"now", "today"}) or (
            item.due_at is not None and item.due_at.date() <= now.date()
        )
        tasks.append(
            PlannedTask(
                item_id=item.id,
                bucket=_bucket_for(priority, due_today),
                priority=priority,
                summary=ai.summary if ai else fallback_summary(item),
                actions=ai.actions if ai and ai.actions else derive_actions(item),
                reason=ai.reason if ai and ai.reason else reason,
                link=item.link,
                source_labels=[source_label(s) for s in item.all_sources],
                ai_generated=ai is not None,
            )
        )

    tasks.sort(key=lambda t: (t.priority.rank, t.bucket.value))

    slots = free_slots(
        meetings,
        now.date(),
        config.work_start,
        config.work_end,
        (config.lunch_start, config.lunch_end),
        config.slot_minutes,
        now,
    )
    schedulable = [t for t in tasks if t.bucket in (Bucket.NOW, Bucket.TODAY)]
    for task, slot in zip(schedulable, slots):
        task.suggested_time = slot.strftime("%H:%M")

    conflicts = _conflicts(schedulable, slots, meetings, now)
    # Kritische Vorgänge bleiben immer am heutigen Tag, auch wenn der Kalender
    # voll ist oder der Lauf ausserhalb der Arbeitszeit startet.
    for task in schedulable[len(slots):]:
        if task.bucket is Bucket.NOW:
            task.reason = (task.reason + "; kein freier Slot, trotzdem sofort").strip("; ")
            continue
        task.bucket = Bucket.TOMORROW
        task.reason = (task.reason + "; kein freier Slot heute").strip("; ")

    notes = [ai_note] if ai_note else []
    return Briefing(
        generated_at=now,
        timezone=config.timezone,
        tasks=tasks,
        calendar=meetings,
        conflicts=conflicts,
        statuses=statuses,
        ai_used=bool(ai_by_id),
        notes=notes,
    )


def _conflicts(
    urgent: list[PlannedTask],
    slots: list[datetime],
    meetings: list[Item],
    now: datetime,
) -> list[str]:
    """Meldet Kollisionen, ohne Termine selbst zu verändern."""
    messages: list[str] = []
    critical = [t for t in urgent if t.priority is Priority.CRITICAL]
    if critical and len(slots) < len(urgent):
        messages.append(
            "Der Tag ist verplant. Kritische Vorgänge sollten Vorrang vor internen "
            "Terminen bekommen; verschiebbare Termine bitte manuell prüfen."
        )
    for meeting in meetings:
        if not meeting.starts_at or meeting.starts_at < now:
            continue
        if critical and not meeting.is_external and meeting.starts_at.date() == now.date():
            messages.append(
                f"{meeting.starts_at.strftime('%H:%M')} {meeting.title}: interner Termin, "
                "kann bei anhaltender Störung verschoben werden."
            )
            break
    if len(urgent) > len(slots):
        messages.append(
            f"{len(urgent) - len(slots)} dringende Vorgänge passen nicht mehr in den "
            "heutigen Arbeitstag und wurden auf morgen vorgeschlagen."
        )
    return messages
