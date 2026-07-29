"""Konfiguration des Morgenbriefings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # PyYAML ist optional; ohne YAML greifen die Standardwerte.
    import yaml
except ImportError:  # pragma: no cover - abhängig von der Installation
    yaml = None

DEFAULT_CONFIG_NAME = "config.yaml"


@dataclass
class SourceConfig:
    enabled: bool = True
    url: str = ""
    max_items: int = 25
    lookback_hours: int = 24
    selectors: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    timezone: str = "Europe/Berlin"
    work_start: str = "08:00"
    work_end: str = "17:00"
    lunch_start: str = "12:00"
    lunch_end: str = "12:30"
    slot_minutes: int = 30
    profile_dir: Path = Path.home() / ".morning-briefing" / "browser-profile"
    output_dir: Path = Path.home() / ".morning-briefing" / "reports"
    headless: bool = False
    login_timeout_seconds: int = 300
    claude_command: str = "claude"
    claude_model: str = ""
    claude_timeout_seconds: int = 180
    ai_enabled: bool = True
    keep_names: bool = True
    company_terms: list[str] = field(default_factory=list)
    extra_redactions: dict[str, str] = field(default_factory=dict)
    internal_domains: list[str] = field(default_factory=list)
    outlook: SourceConfig = field(default_factory=SourceConfig)
    calendar: SourceConfig = field(default_factory=SourceConfig)
    teams: SourceConfig = field(default_factory=SourceConfig)
    autotask: SourceConfig = field(default_factory=SourceConfig)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        data: dict[str, Any] = {}
        candidate = path or _default_path()
        if candidate and candidate.is_file():
            if yaml is None:
                raise RuntimeError(
                    "PyYAML fehlt. Bitte 'pip install -r requirements.txt' ausführen."
                )
            data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        config = cls()
        for key, value in (data or {}).items():
            if key in {"outlook", "calendar", "teams", "autotask"}:
                setattr(config, key, SourceConfig(**(value or {})))
            elif key in {"profile_dir", "output_dir"}:
                setattr(config, key, Path(os.path.expandvars(str(value))).expanduser())
            elif hasattr(config, key):
                setattr(config, key, value)
        return config

    def source(self, name: str) -> SourceConfig:
        return getattr(self, name)


def _default_path() -> Path | None:
    env_path = os.environ.get("MORNING_BRIEFING_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    local = Path(__file__).resolve().parent.parent / DEFAULT_CONFIG_NAME
    if local.is_file():
        return local
    return Path.home() / ".morning-briefing" / DEFAULT_CONFIG_NAME
