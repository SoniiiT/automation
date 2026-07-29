"""Beispieldaten für einen Offline-Lauf ohne Browser und ohne echte Konten."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import Item, Priority, Source, SourceStatus


def demo_items(now: datetime) -> list[Item]:
    yesterday = now - timedelta(days=1)
    return [
        Item(
            id="ticket-1",
            source=Source.AUTOTASK,
            sender="Monitoring",
            received_at=now - timedelta(minutes=40),
            title="Server offline",
            body=(
                "Server SRV-01 ist offline gegangen. Priorität Kritisch. "
                "Kunde Musterfirma GmbH betroffen, Kontakt max.mustermann@musterfirma.de, "
                "Telefon +49 1234 456789."
            ),
            link="https://ww1.autotask.net/ticket/T20260729.0001",
            priority=Priority.CRITICAL,
            ticket_ref="T20260729.0001",
        ),
        Item(
            id="ticket-2",
            source=Source.AUTOTASK,
            sender="Max Mustermann",
            received_at=now - timedelta(hours=2),
            title="T20260728.0042 - Zugriff auf TimeZest",
            body=(
                "Kunde hat geantwortet: Bitte E-Mail: jenny.mustermann@musterfirma.de "
                "freigeben und einen neuen Benutzer anlegen. Kundennummer: 998877."
            ),
            link="https://ww1.autotask.net/ticket/T20260728.0042",
            priority=Priority.HIGH,
            ticket_ref="T20260728.0042",
        ),
        Item(
            id="teams-1",
            source=Source.TEAMS,
            sender="Max Mustermann",
            received_at=yesterday.replace(hour=16, minute=30),
            title="Max Mustermann",
            body="Wie weit bist du mit der API? Lass uns morgen kurz reden.",
            link="https://teams.microsoft.com/v2/",
            mentioned=True,
        ),
        Item(
            id="teams-2",
            source=Source.TEAMS,
            sender="Jenny Mustermann",
            received_at=now - timedelta(hours=1),
            title="Jenny Mustermann",
            body="Gute Besserung! Melde dich, wenn es dir wieder besser geht.",
            link="https://teams.microsoft.com/v2/",
        ),
        Item(
            id="mail-1",
            source=Source.OUTLOOK_MAIL,
            sender="Max Mustermann",
            received_at=now - timedelta(hours=3),
            title="Einladung und Dateiablage",
            body=(
                "Ich habe dir eine Einladung geschickt. Der Nextcloud-Link ist "
                "https://cloud.musterfirma.de/s/abc123. Mit freundlichen Grüßen Max"
            ),
            link="https://outlook.office.com/mail/",
        ),
        Item(
            id="mail-2",
            source=Source.OUTLOOK_MAIL,
            sender="Monitoring",
            received_at=now - timedelta(minutes=38),
            title="Server offline",
            body="Server SRV-01 ist offline gegangen. Priorität Kritisch.",
            link="https://outlook.office.com/mail/",
        ),
        Item(
            id="cal-1",
            source=Source.OUTLOOK_CALENDAR,
            sender="Kalender",
            received_at=now,
            title="Teammeeting",
            body="",
            starts_at=now.replace(hour=9, minute=30, second=0, microsecond=0),
            ends_at=now.replace(hour=10, minute=0, second=0, microsecond=0),
            is_meeting=True,
        ),
        Item(
            id="cal-2",
            source=Source.OUTLOOK_CALENDAR,
            sender="Kalender",
            received_at=now,
            title="Kundentermin extern",
            body="",
            starts_at=now.replace(hour=14, minute=0, second=0, microsecond=0),
            ends_at=now.replace(hour=15, minute=0, second=0, microsecond=0),
            is_meeting=True,
            is_external=True,
        ),
    ]


def demo_statuses() -> list[SourceStatus]:
    return [
        SourceStatus(source=Source.OUTLOOK_MAIL, ok=True, count=2),
        SourceStatus(source=Source.OUTLOOK_CALENDAR, ok=True, count=2),
        SourceStatus(source=Source.TEAMS, ok=True, count=2),
        SourceStatus(source=Source.AUTOTASK, ok=True, count=2),
    ]
