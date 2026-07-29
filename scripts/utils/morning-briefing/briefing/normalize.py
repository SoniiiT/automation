"""Normalisierung: HTML entfernen, Signaturen kürzen, Duplikate zusammenführen."""

from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from html.parser import HTMLParser

from .models import Item, Source

_QUOTE_MARKERS = (
    "-----ursprüngliche nachricht-----",
    "-----original message-----",
    "von:",
    "from:",
    "am .* schrieb",
    "gesendet von meinem",
    "sent from my",
)
_SIGNATURE_MARKERS = (
    "mit freundlichen grüßen",
    "mit freundlichen gruessen",
    "freundliche grüße",
    "freundliche gruesse",
    "beste grüße",
    "beste gruesse",
    "viele grüße",
    "viele gruesse",
    "liebe grüße",
    "liebe gruesse",
    "kind regards",
    "best regards",
    "diese e-mail enthält vertrauliche",
    "this email contains confidential",
)
_WS = re.compile(r"[ \t\u00a0]+")
_BLANK = re.compile(r"\n{3,}")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "head"}:
            self._skip += 1
        elif tag in {"br", "p", "div", "tr", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "head"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def strip_html(value: str) -> str:
    if "<" not in value:
        return value
    parser = _TextExtractor()
    parser.feed(value)
    return parser.text()


def clean_body(value: str | None, max_chars: int = 1200) -> str:
    """Entfernt HTML, zitierte Verläufe und Signaturen und kürzt den Rest."""
    if not value:
        return ""
    text = strip_html(value)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = _WS.sub(" ", raw_line).strip()
        lowered = line.lower()
        if any(re.match(marker, lowered) for marker in _QUOTE_MARKERS):
            break
        if any(lowered.startswith(marker) for marker in _SIGNATURE_MARKERS):
            break
        if line.startswith(">"):
            continue
        lines.append(line)
    cleaned = _BLANK.sub("\n\n", "\n".join(lines)).strip()
    cleaned = _cut_inline_signature(cleaned)
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rsplit(" ", 1)[0] + " [gekuerzt]"
    return cleaned


def _cut_inline_signature(text: str) -> str:
    """Schneidet Grußformeln ab, die ohne Zeilenumbruch im Fließtext stehen."""
    lowered = text.lower()
    cut = len(text)
    for marker in _SIGNATURE_MARKERS:
        found = lowered.find(marker)
        if found > 0:
            cut = min(cut, found)
    return text[:cut].strip()


def _fingerprint(item: Item) -> str:
    """Erkennt inhaltsgleiche Meldungen auch bei unterschiedlich langem Text."""
    title = re.sub(r"\W+", " ", item.title.lower()).strip()
    body = re.sub(r"\W+", " ", item.body.lower()).strip()
    sender = re.sub(r"\W+", " ", item.sender.lower()).strip()
    # Der Titel ist über Quellen hinweg stabiler als der Nachrichtentext,
    # weil Autotask, Outlook und Teams unterschiedlich viel Kontext anhängen.
    core = title[:80] if len(title) >= 8 else body[:120]
    payload = f"{sender}|{core}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def deduplicate(items: list[Item], window: timedelta = timedelta(hours=12)) -> list[Item]:
    """Führt inhaltsgleiche Meldungen aus mehreren Quellen zusammen.

    Kalendereinträge bleiben unangetastet, weil Termine bewusst mehrfach
    auftreten können. Bei einem Treffer gewinnt der Eintrag mit der höheren
    Priorität und dem älteren Zeitstempel; die weiteren Quellen werden vermerkt.
    """
    result: list[Item] = []
    index: dict[str, Item] = {}
    ticket_index: dict[str, Item] = {}

    for item in sorted(items, key=lambda i: i.received_at):
        if item.is_calendar:
            result.append(item)
            continue

        key = _fingerprint(item)
        match = index.get(key)
        if match is None and item.ticket_ref:
            candidate = ticket_index.get(item.ticket_ref.lower())
            if candidate and abs(candidate.received_at - item.received_at) <= window:
                match = candidate

        if match is not None and abs(match.received_at - item.received_at) <= window:
            if item.source not in match.all_sources:
                match.merged_sources.append(item.source)
            if item.priority.rank < match.priority.rank:
                match.priority = item.priority
            if item.link and not match.link:
                match.link = item.link
            if item.due_at and not match.due_at:
                match.due_at = item.due_at
            match.mentioned = match.mentioned or item.mentioned
            continue

        index[key] = item
        if item.ticket_ref:
            ticket_index.setdefault(item.ticket_ref.lower(), item)
        result.append(item)

    return result


def source_label(source: Source) -> str:
    return {
        Source.OUTLOOK_MAIL: "Outlook",
        Source.OUTLOOK_CALENDAR: "Kalender",
        Source.TEAMS: "Teams",
        Source.AUTOTASK: "Autotask",
    }[source]
