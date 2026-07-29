"""Datenmodelle für das Morgenbriefing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Source(str, Enum):
    OUTLOOK_MAIL = "outlook_mail"
    OUTLOOK_CALENDAR = "outlook_calendar"
    TEAMS = "teams"
    AUTOTASK = "autotask"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.NORMAL: 2,
            Priority.LOW: 3,
            Priority.INFO: 4,
        }[self]


class Bucket(str, Enum):
    NOW = "now"
    TODAY = "today"
    TODAY_OPTIONAL = "today_optional"
    TOMORROW = "tomorrow"
    INFO = "info"


@dataclass
class Item:
    """Eine normalisierte Nachricht, ein Ticket oder ein Kalendereintrag."""

    id: str
    source: Source
    sender: str
    received_at: datetime
    title: str
    body: str
    link: str = ""
    priority: Priority = Priority.NORMAL
    due_at: datetime | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_meeting: bool = False
    is_external: bool = False
    is_optional: bool = False
    ticket_ref: str = ""
    unread: bool = True
    mentioned: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
    merged_sources: list[Source] = field(default_factory=list)

    @property
    def all_sources(self) -> list[Source]:
        return [self.source, *self.merged_sources]

    @property
    def is_calendar(self) -> bool:
        return self.source is Source.OUTLOOK_CALENDAR


@dataclass
class SourceStatus:
    """Erfassungsstatus je Quelle, damit fehlende Daten sichtbar bleiben."""

    source: Source
    ok: bool
    count: int = 0
    detail: str = ""

    @property
    def label(self) -> str:
        if self.ok:
            return f"{self.count} Eintraege"
        return self.detail or "nicht verfuegbar"


@dataclass
class PlannedTask:
    """Eine geplante Aufgabe inklusive Begründung und Quellenverweis."""

    item_id: str
    bucket: Bucket
    priority: Priority
    summary: str
    actions: list[str] = field(default_factory=list)
    reason: str = ""
    suggested_time: str = ""
    link: str = ""
    source_labels: list[str] = field(default_factory=list)
    ai_generated: bool = False


@dataclass
class Briefing:
    """Vollständiges Ergebnis eines Briefing-Laufs."""

    generated_at: datetime
    timezone: str
    tasks: list[PlannedTask] = field(default_factory=list)
    calendar: list[Item] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    statuses: list[SourceStatus] = field(default_factory=list)
    ai_used: bool = False
    notes: list[str] = field(default_factory=list)

    def bucket(self, bucket: Bucket) -> list[PlannedTask]:
        return [task for task in self.tasks if task.bucket is bucket]
