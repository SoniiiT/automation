"""Ablauf: sammeln, bereinigen, anonymisieren, zusammenfassen, planen."""

from __future__ import annotations

from datetime import datetime

from .collectors import (
    BrowserSession,
    collect_autotask,
    collect_calendar,
    collect_outlook_mail,
    collect_teams,
)
from .config import Config
from .models import Briefing, Item, Source, SourceStatus
from .normalize import clean_body, deduplicate
from .plan import build_briefing
from .privacy import Redactor
from .summarize import ClaudeSummarizer


def collect_all(config: Config, now: datetime) -> tuple[list[Item], list[SourceStatus]]:
    """Liest alle aktivierten Quellen. Fehler einer Quelle stoppen den Lauf nicht."""
    items: list[Item] = []
    statuses: list[SourceStatus] = []

    with BrowserSession(config.profile_dir, config.headless, config.login_timeout_seconds) as session:
        jobs = (
            (Source.OUTLOOK_MAIL, collect_outlook_mail, config.outlook),
            (Source.OUTLOOK_CALENDAR, collect_calendar, config.calendar),
            (Source.TEAMS, collect_teams, config.teams),
            (Source.AUTOTASK, collect_autotask, config.autotask),
        )
        for source, collector, source_config in jobs:
            if not session.ready:
                statuses.append(SourceStatus(source=source, ok=False, detail=session.error))
                continue
            result = collector(session, source_config, now)
            items.extend(result.items)
            statuses.append(result.status)

    return items, statuses


def sanitize(items: list[Item], redactor: Redactor) -> tuple[list[Item], bool]:
    """Bereinigt Texte und ersetzt vertrauliche Werte durch Platzhalter."""
    injection_seen = False
    for item in items:
        title = redactor.redact_report(clean_body(item.title, max_chars=200))
        body = redactor.redact_report(clean_body(item.body))
        item.title = title.text
        item.body = body.text
        item.sender = item.sender if redactor.keep_names else redactor.redact(item.sender)
        item.raw = {}
        injection_seen = injection_seen or title.injection_suspected or body.injection_suspected
    return items, injection_seen


def run(config: Config, now: datetime, items: list[Item] | None = None,
        statuses: list[SourceStatus] | None = None) -> tuple[Briefing, Redactor, list[Item]]:
    """Führt den kompletten Ablauf aus. Vorgegebene Items überspringen das Sammeln.

    Rückgabe: Briefing, Redactor für die lokale Rückersetzung und die
    bereinigten Vorgänge, wie sie an die KI übergeben wurden.
    """
    if items is None or statuses is None:
        items, statuses = collect_all(config, now)

    items = deduplicate(items)
    redactor = Redactor(
        company_terms=config.company_terms,
        keep_names=config.keep_names,
        extra_patterns=config.extra_redactions,
    )
    items, injection_seen = sanitize(items, redactor)

    notes: list[str] = []
    if injection_seen:
        notes.append(
            "Mindestens eine Nachricht enthielt anweisungsartigen Text. "
            "Inhalte wurden nur zusammengefasst, nicht ausgeführt."
        )

    summarizer = ClaudeSummarizer(
        command=config.claude_command,
        model=config.claude_model,
        timeout=config.claude_timeout_seconds,
        enabled=config.ai_enabled,
    )
    workload = [item for item in items if not item.is_calendar]
    ai_tasks = summarizer.summarize(workload, now, config.timezone, redactor)
    if not ai_tasks and summarizer.last_error:
        notes.append(f"Ohne KI-Zusammenfassung: {summarizer.last_error}")

    briefing = build_briefing(
        items=items,
        statuses=statuses,
        now=now,
        config=config,
        ai_tasks=ai_tasks,
        ai_note="; ".join(notes),
    )
    briefing.notes = notes
    return briefing, redactor, workload
