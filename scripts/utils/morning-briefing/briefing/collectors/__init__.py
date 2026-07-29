"""Collectors für die einzelnen Quellen."""

from .autotask import collect_autotask
from .browser import BrowserSession, CollectorResult, unavailable
from .microsoft import collect_calendar, collect_outlook_mail, collect_teams

__all__ = [
    "BrowserSession",
    "CollectorResult",
    "collect_autotask",
    "collect_calendar",
    "collect_outlook_mail",
    "collect_teams",
    "unavailable",
]
