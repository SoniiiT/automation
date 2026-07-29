#!/usr/bin/env python3
"""Morgenbriefing aus Outlook, Teams und Autotask.

Der Lauf ist ausschließlich lesend: es werden keine Nachrichten gesendet,
keine Tickets geändert und keine Termine verschoben.

Beispiele:
    python main.py --demo
    python main.py --html
    python main.py --no-ai
    python main.py --login
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Umlaute sollen auch in einer Konsole mit alter Codepage lesbar bleiben.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - umgebungsabhängig
        pass

from briefing.collectors import BrowserSession  # noqa: E402
from briefing.config import Config  # noqa: E402
from briefing.demo import demo_items, demo_statuses  # noqa: E402
from briefing.pipeline import run  # noqa: E402
from briefing.render import render_text, write_html  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tägliches Arbeitsbriefing erstellen.")
    parser.add_argument("--config", type=Path, help="Pfad zur config.yaml")
    parser.add_argument("--demo", action="store_true", help="Offline-Lauf mit Beispieldaten")
    parser.add_argument("--no-ai", action="store_true", help="Ohne Claude CLI ausführen")
    parser.add_argument("--html", action="store_true", help="Zusätzlich HTML-Bericht schreiben")
    parser.add_argument("--open", action="store_true", help="HTML-Bericht anschließend öffnen")
    parser.add_argument(
        "--login",
        action="store_true",
        help="Nur die Anmeldefenster öffnen, um das Browserprofil zu erneuern",
    )
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Den anonymisierten Prompt anzeigen, der an die KI gehen würde",
    )
    return parser.parse_args(argv)


def _now(config: Config) -> datetime:
    try:
        return datetime.now(ZoneInfo(config.timezone))
    except Exception:
        return datetime.now().astimezone()


def do_login(config: Config) -> int:
    """Öffnet die Portale sichtbar, damit die Anmeldung erneuert werden kann."""
    from briefing.collectors.autotask import AUTOTASK_DEFAULTS
    from briefing.collectors.microsoft import (
        CALENDAR_DEFAULTS,
        OUTLOOK_DEFAULTS,
        TEAMS_DEFAULTS,
    )

    targets = [
        ("Outlook", config.outlook.url or OUTLOOK_DEFAULTS["url"], OUTLOOK_DEFAULTS["ready"]),
        ("Kalender", config.calendar.url or CALENDAR_DEFAULTS["url"], CALENDAR_DEFAULTS["ready"]),
        ("Teams", config.teams.url or TEAMS_DEFAULTS["url"], TEAMS_DEFAULTS["ready"]),
        ("Autotask", config.autotask.url or AUTOTASK_DEFAULTS["url"], AUTOTASK_DEFAULTS["ready"]),
    ]
    with BrowserSession(config.profile_dir, headless=False, login_timeout=config.login_timeout_seconds) as session:
        if not session.ready:
            print(f"Fehler: {session.error}")
            return 1
        for name, url, ready in targets:
            print(f"Öffne {name} ...")
            try:
                page = session.open(url, ready)
                print(f"  {name}: angemeldet")
                page.close()
            except Exception as exc:
                print(f"  {name}: {exc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = Config.load(args.config)
    if args.no_ai:
        config.ai_enabled = False

    if args.login:
        return do_login(config)

    now = _now(config)
    items = statuses = None
    if args.demo:
        items, statuses = demo_items(now), demo_statuses()

    briefing, redactor, prepared = run(config, now, items, statuses)

    if args.show_prompt:
        from briefing.summarize import ClaudeSummarizer

        print(ClaudeSummarizer(enabled=False).build_prompt(prepared, now, config.timezone))
        print("-" * 60)

    print(render_text(briefing, redactor))

    if args.html:
        target = write_html(briefing, redactor, config.output_dir)
        print(f"\nHTML-Bericht: {target}")
        if args.open:
            import webbrowser

            webbrowser.open(target.as_uri())

    failed = [s for s in briefing.statuses if not s.ok]
    return 2 if failed and len(failed) == len(briefing.statuses) else 0


if __name__ == "__main__":
    raise SystemExit(main())
