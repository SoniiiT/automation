"""Collectors für Outlook Web, Outlook-Kalender und Teams Web.

Die Selektoren sind bewusst konfigurierbar, weil Microsoft die Oberflächen
regelmäßig ändert. Alle Collectors arbeiten ausschließlich lesend.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from ..config import SourceConfig
from ..models import Item, Priority, Source
from ..normalize import clean_body
from .browser import CollectorResult, unavailable

OUTLOOK_DEFAULTS = {
    "url": "https://outlook.office.com/mail/",
    "ready": "div[role='main']",
    "row": "div[role='option']",
    "sender": "span[title]",
    "subject": "span[role='heading']",
    "preview": "span[class*='preview'], div[class*='preview']",
}
CALENDAR_DEFAULTS = {
    "url": "https://outlook.office.com/calendar/view/day",
    "ready": "div[role='main']",
    "row": "div[role='button'][aria-label*=':']",
    "label": "aria-label",
}
TEAMS_DEFAULTS = {
    "url": "https://teams.microsoft.com/v2/",
    "ready": "div[id='app-bar'], div[data-tid='app-bar']",
    "activity_button": "button[data-tid='app-bar-activity']",
    "row": "div[data-tid='activity-feed-item'], li[data-tid='activity-feed-item']",
    "sender": "span[data-tid='activity-title'], span[class*='title']",
    "preview": "span[data-tid='activity-preview'], div[class*='preview']",
}
_TIME = re.compile(r"(\d{1,2}):(\d{2})")


def _selector(config: SourceConfig, defaults: dict[str, str], key: str) -> str:
    return config.selectors.get(key) or defaults[key]


def _url(config: SourceConfig, defaults: dict[str, str]) -> str:
    return config.url or defaults["url"]


def _text(node: Any, selector: str) -> str:
    try:
        found = node.query_selector(selector)
        return (found.inner_text() if found else "").strip()
    except Exception:  # pragma: no cover - DOM-abhängig
        return ""


def collect_outlook_mail(session, config: SourceConfig, now: datetime) -> CollectorResult:
    if not config.enabled:
        return unavailable(Source.OUTLOOK_MAIL, "deaktiviert")
    try:
        page = session.open(
            _url(config, OUTLOOK_DEFAULTS),
            _selector(config, OUTLOOK_DEFAULTS, "ready"),
        )
    except Exception as exc:
        return unavailable(Source.OUTLOOK_MAIL, str(exc)[:120])

    items: list[Item] = []
    try:
        page.wait_for_timeout(2500)
        rows = page.query_selector_all(_selector(config, OUTLOOK_DEFAULTS, "row"))
        for index, row in enumerate(rows[: config.max_items]):
            sender = _text(row, _selector(config, OUTLOOK_DEFAULTS, "sender"))
            subject = _text(row, _selector(config, OUTLOOK_DEFAULTS, "subject"))
            preview = _text(row, _selector(config, OUTLOOK_DEFAULTS, "preview"))
            if not (sender or subject):
                continue
            items.append(
                Item(
                    id=f"mail-{index + 1}",
                    source=Source.OUTLOOK_MAIL,
                    sender=sender or "Unbekannt",
                    received_at=now,
                    title=subject,
                    body=clean_body(preview),
                    link=_url(config, OUTLOOK_DEFAULTS),
                )
            )
    except Exception as exc:  # pragma: no cover - DOM-abhängig
        return unavailable(Source.OUTLOOK_MAIL, f"Auslesen fehlgeschlagen: {exc}"[:120])
    finally:
        page.close()

    from ..models import SourceStatus

    return CollectorResult(
        items=items,
        status=SourceStatus(source=Source.OUTLOOK_MAIL, ok=True, count=len(items)),
    )


def collect_calendar(session, config: SourceConfig, now: datetime) -> CollectorResult:
    if not config.enabled:
        return unavailable(Source.OUTLOOK_CALENDAR, "deaktiviert")
    try:
        page = session.open(
            _url(config, CALENDAR_DEFAULTS),
            _selector(config, CALENDAR_DEFAULTS, "ready"),
        )
    except Exception as exc:
        return unavailable(Source.OUTLOOK_CALENDAR, str(exc)[:120])

    items: list[Item] = []
    try:
        page.wait_for_timeout(2500)
        rows = page.query_selector_all(_selector(config, CALENDAR_DEFAULTS, "row"))
        for index, row in enumerate(rows[: config.max_items]):
            label = (row.get_attribute(CALENDAR_DEFAULTS["label"]) or "").strip()
            if not label:
                continue
            match = _TIME.search(label)
            if not match:
                continue
            start = now.replace(
                hour=int(match.group(1)), minute=int(match.group(2)), second=0, microsecond=0
            )
            title = _TIME.sub("", label).strip(" ,-")
            items.append(
                Item(
                    id=f"cal-{index + 1}",
                    source=Source.OUTLOOK_CALENDAR,
                    sender="Kalender",
                    received_at=now,
                    title=title or "Termin",
                    body="",
                    starts_at=start,
                    ends_at=start + timedelta(minutes=30),
                    is_meeting=True,
                    is_external="extern" in label.lower(),
                    is_optional="optional" in label.lower(),
                    priority=Priority.NORMAL,
                )
            )
    except Exception as exc:  # pragma: no cover - DOM-abhängig
        return unavailable(Source.OUTLOOK_CALENDAR, f"Auslesen fehlgeschlagen: {exc}"[:120])
    finally:
        page.close()

    from ..models import SourceStatus

    return CollectorResult(
        items=items,
        status=SourceStatus(source=Source.OUTLOOK_CALENDAR, ok=True, count=len(items)),
    )


def collect_teams(session, config: SourceConfig, now: datetime) -> CollectorResult:
    if not config.enabled:
        return unavailable(Source.TEAMS, "deaktiviert")
    try:
        page = session.open(
            _url(config, TEAMS_DEFAULTS),
            _selector(config, TEAMS_DEFAULTS, "ready"),
        )
    except Exception as exc:
        return unavailable(Source.TEAMS, str(exc)[:120])

    items: list[Item] = []
    try:
        activity = page.query_selector(_selector(config, TEAMS_DEFAULTS, "activity_button"))
        if activity:
            activity.click()
        page.wait_for_timeout(3000)
        rows = page.query_selector_all(_selector(config, TEAMS_DEFAULTS, "row"))
        for index, row in enumerate(rows[: config.max_items]):
            sender = _text(row, _selector(config, TEAMS_DEFAULTS, "sender"))
            preview = _text(row, _selector(config, TEAMS_DEFAULTS, "preview"))
            if not (sender or preview):
                continue
            items.append(
                Item(
                    id=f"teams-{index + 1}",
                    source=Source.TEAMS,
                    sender=sender or "Teams",
                    received_at=now,
                    title=sender or "Teams-Nachricht",
                    body=clean_body(preview),
                    link=_url(config, TEAMS_DEFAULTS),
                    mentioned="@" in preview or "erwähnt" in preview.lower(),
                )
            )
    except Exception as exc:  # pragma: no cover - DOM-abhängig
        return unavailable(Source.TEAMS, f"Auslesen fehlgeschlagen: {exc}"[:120])
    finally:
        page.close()

    from ..models import SourceStatus

    return CollectorResult(
        items=items,
        status=SourceStatus(source=Source.TEAMS, ok=True, count=len(items)),
    )
