"""Collector für Kaseya Autotask (Weboberfläche, ausschließlich lesend)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from ..config import SourceConfig
from ..models import Item, Priority, Source, SourceStatus
from ..normalize import clean_body
from .browser import CollectorResult, unavailable

AUTOTASK_DEFAULTS = {
    "url": "https://ww1.autotask.net/",
    "ready": "body",
    "row": "tr[class*='GridRow'], div[role='row']",
    "cell": "td, div[role='gridcell']",
}
_TICKET_NUMBER = re.compile(r"\bT\d{8}\.\d{4}\b|\b\d{6,}\b")
_PRIORITY_MAP = {
    "kritisch": Priority.CRITICAL,
    "critical": Priority.CRITICAL,
    "hoch": Priority.HIGH,
    "high": Priority.HIGH,
    "mittel": Priority.NORMAL,
    "medium": Priority.NORMAL,
    "niedrig": Priority.LOW,
    "low": Priority.LOW,
}


def _cells(row: Any, selector: str) -> list[str]:
    try:
        return [c.inner_text().strip() for c in row.query_selector_all(selector)]
    except Exception:  # pragma: no cover - DOM-abhängig
        return []


def detect_priority(text: str) -> Priority:
    lowered = text.lower()
    for needle, priority in _PRIORITY_MAP.items():
        if needle in lowered:
            return priority
    return Priority.NORMAL


def collect_autotask(session, config: SourceConfig, now: datetime) -> CollectorResult:
    if not config.enabled:
        return unavailable(Source.AUTOTASK, "deaktiviert")

    url = config.url or AUTOTASK_DEFAULTS["url"]
    ready = config.selectors.get("ready") or AUTOTASK_DEFAULTS["ready"]
    row_selector = config.selectors.get("row") or AUTOTASK_DEFAULTS["row"]
    cell_selector = config.selectors.get("cell") or AUTOTASK_DEFAULTS["cell"]

    try:
        page = session.open(url, ready)
    except Exception as exc:
        return unavailable(Source.AUTOTASK, str(exc)[:120])

    items: list[Item] = []
    try:
        page.wait_for_timeout(4000)
        rows = page.query_selector_all(row_selector)
        for index, row in enumerate(rows[: config.max_items]):
            cells = [c for c in _cells(row, cell_selector) if c]
            if not cells:
                continue
            joined = " | ".join(cells)
            ticket = _TICKET_NUMBER.search(joined)
            items.append(
                Item(
                    id=f"ticket-{index + 1}",
                    source=Source.AUTOTASK,
                    sender=cells[1] if len(cells) > 1 else "Autotask",
                    received_at=now,
                    title=cells[0],
                    body=clean_body(joined),
                    link=url,
                    priority=detect_priority(joined),
                    ticket_ref=ticket.group(0) if ticket else "",
                )
            )
    except Exception as exc:  # pragma: no cover - DOM-abhängig
        return unavailable(Source.AUTOTASK, f"Auslesen fehlgeschlagen: {exc}"[:120])
    finally:
        page.close()

    return CollectorResult(
        items=items,
        status=SourceStatus(source=Source.AUTOTASK, ok=True, count=len(items)),
    )
