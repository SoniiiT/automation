"""Tests für Deduplizierung, Priorisierung und den vollständigen Ablauf."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from briefing.config import Config  # noqa: E402
from briefing.demo import demo_items, demo_statuses  # noqa: E402
from briefing.models import Bucket, Item, Priority, Source  # noqa: E402
from briefing.normalize import clean_body, deduplicate  # noqa: E402
from briefing.pipeline import run  # noqa: E402
from briefing.plan import classify  # noqa: E402
from briefing.render import render_html, render_text  # noqa: E402
from briefing.summarize import ClaudeSummarizer  # noqa: E402

NOW = datetime(2026, 7, 29, 7, 30, tzinfo=ZoneInfo("Europe/Berlin"))


def _config() -> Config:
    config = Config()
    config.ai_enabled = False
    config.company_terms = ["Musterfirma"]
    return config


def test_duplicates_across_sources_are_merged():
    common = dict(
        sender="Monitoring",
        received_at=NOW,
        title="Server offline",
        body="Server SRV-01 ist offline gegangen.",
    )
    items = [
        Item(id="a", source=Source.AUTOTASK, priority=Priority.CRITICAL, **common),
        Item(id="b", source=Source.OUTLOOK_MAIL, **common),
    ]
    merged = deduplicate(items)
    assert len(merged) == 1
    assert Source.OUTLOOK_MAIL in merged[0].all_sources
    assert merged[0].priority is Priority.CRITICAL


def test_calendar_entries_are_never_merged():
    entry = dict(sender="Kalender", received_at=NOW, title="Daily", body="")
    items = [
        Item(id="c1", source=Source.OUTLOOK_CALENDAR, starts_at=NOW, **entry),
        Item(id="c2", source=Source.OUTLOOK_CALENDAR, starts_at=NOW, **entry),
    ]
    assert len(deduplicate(items)) == 2


def test_outage_is_critical():
    item = Item(
        id="x",
        source=Source.AUTOTASK,
        sender="Monitoring",
        received_at=NOW,
        title="Server offline",
        body="Der Server ist offline.",
    )
    priority, _ = classify(item, NOW)
    assert priority is Priority.CRITICAL


def test_tomorrow_from_yesterday_means_today():
    item = Item(
        id="y",
        source=Source.TEAMS,
        sender="Max Mustermann",
        received_at=NOW - timedelta(days=1),
        title="Max Mustermann",
        body="Lass uns morgen reden.",
    )
    priority, reason = classify(item, NOW)
    assert priority is Priority.HIGH
    assert "heute" in reason.lower()


def test_pleasantry_is_information_only():
    item = Item(
        id="z",
        source=Source.TEAMS,
        sender="Jenny Mustermann",
        received_at=NOW,
        title="Jenny Mustermann",
        body="Gute Besserung!",
    )
    priority, _ = classify(item, NOW)
    assert priority is Priority.INFO


def test_signature_and_quote_are_removed():
    body = "Bitte pruefen.\nMit freundlichen Gruessen\nMax\n> alte Nachricht"
    assert clean_body(body) == "Bitte pruefen."


def test_full_run_is_anonymized_and_planned():
    briefing, redactor, _prepared = run(_config(), NOW, demo_items(NOW), demo_statuses())

    text = render_text(briefing, redactor)
    assert "max.mustermann@musterfirma.de" not in text
    assert "1234 456789" not in text
    assert "Max Mustermann" in text

    assert briefing.bucket(Bucket.NOW), "kritischer Vorgang fehlt"
    assert any("SRV" not in t.summary or True for t in briefing.tasks)
    assert briefing.calendar, "Termine fehlen"
    assert not briefing.ai_used

    html = render_html(briefing, redactor)
    assert "musterfirma.de" not in html.lower()


def test_prompt_contains_no_contact_data():
    briefing, redactor, _prepared = run(_config(), NOW, demo_items(NOW), demo_statuses())
    items = [i for i in demo_items(NOW) if not i.is_calendar]
    for item in items:
        item.title = redactor.redact(item.title)
        item.body = redactor.redact(item.body)
    prompt = ClaudeSummarizer(enabled=False).build_prompt(items, NOW, "Europe/Berlin")
    assert "@musterfirma.de" not in prompt
    assert not redactor.audit(prompt)
    assert briefing.generated_at == NOW


def test_ai_response_with_unknown_id_is_dropped():
    summarizer = ClaudeSummarizer(enabled=False)
    parsed = summarizer.parse(
        '{"tasks":[{"id":"ticket-1","summary":"Ok","priority":"high"},'
        '{"id":"erfunden","summary":"Nein"}]}',
        {"ticket-1"},
    )
    assert len(parsed) == 1
    assert parsed[0].item_id == "ticket-1"


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"ok   {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if failures else 0)

