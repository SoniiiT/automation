#!/usr/bin/env python3
"""Priorisierte Ticket-Arbeitsliste aus Autotask "Mein Arbeitsplatz & meine Queues".

Rein lesend: es werden keine Tickets angelegt, geändert, kommentiert oder
geschlossen. Für jedes Ticket wird ein direkter Autotask-Link ausgegeben,
damit die eigentliche Bearbeitung/das Abschließen bewusst manuell erfolgt
(oder in einer separaten, begleiteten Browser-Sitzung, in der jede Änderung
einzeln bestätigt wird).

Die Anmeldung erfolgt manuell im sichtbaren Fenster (inkl. MFA). Gespeichert
wird nur das lokale Browserprofil, niemals ein Passwort.

Beispiele:
    python ticket_worklist.py login
    python ticket_worklist.py list-queues
    python ticket_worklist.py worklist
    python ticket_worklist.py worklist --views "Offene Tickets,IT Level II-Support,Security" --html bericht.html
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - umgebungsabhängig
        pass

DEFAULT_ZONE = "ww18"
DEFAULT_PROFILE_DIR = Path.home() / ".autotask-worklist" / "browser-profile"
DEFAULT_VIEWS = ["Offene Tickets"]
GRID_PATH = "/Mvc/ServiceDesk/MyWorkspaceAndQueuesTickets.mvc/Summary"
TICKET_PATH = "/Mvc/ServiceDesk/TicketDetail.mvc?ticketId={ticket_id}"

PRIORITY_RANK = {
    "kritisch": 0,
    "critical": 0,
    "hoch": 1,
    "high": 1,
    "mittel": 2,
    "medium": 2,
    "niedrig": 3,
    "low": 3,
}

DUE_PATTERN = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})")

# Die Seitenleiste besteht aus <div class="SummaryMenuItem1">Name(Anzahl)</div>.
# Anklicken lädt das Raster per AJAX neu (keine Seitennavigation).
SIDEBAR_SELECT_JS = """(name) => {
    const els = Array.from(document.querySelectorAll('div.SummaryMenuItem1'));
    const match = els.find(el => el.textContent.trim().startsWith(name + '('));
    if (match) { match.click(); return true; }
    return false;
}"""

LIST_VIEWS_JS = (
    "() => Array.from(document.querySelectorAll('div.SummaryMenuItem1'))"
    ".map(el => el.textContent.trim())"
)

SET_PAGE_SIZE_JS = """(size) => {
    const selects = Array.from(document.querySelectorAll('select'));
    const target = selects.find(s => {
        const values = Array.from(s.options).map(o => o.value);
        return values.includes('100') && values.includes('25');
    });
    if (!target) return false;
    target.value = String(size);
    target.dispatchEvent(new Event('change', {bubbles: true}));
    return true;
}"""

# Kopfzeile steht in einer eigenen <table>, deren erste Zeile Zellen mit der
# Klasse 'SortCell' enthält. Die Datenzeilen sind <tr class="Display">,
# die interne Ticket-ID steckt in data-row-key.
SCRAPE_GRID_JS = """() => {
    const tables = Array.from(document.querySelectorAll('table'));
    const headerTbl = tables.find(t => t.rows.length > 0 &&
        Array.from(t.rows[0].cells).some(c => c.className.includes('SortCell')));
    const headers = headerTbl
        ? Array.from(headerTbl.rows[0].cells).map(c => c.innerText.trim())
        : [];
    const rows = Array.from(document.querySelectorAll('tr.Display'));
    return rows.map(row => {
        const cells = Array.from(row.cells);
        const rec = {};
        cells.forEach((c, i) => {
            const key = headers[i] || '';
            if (key) rec[key] = c.innerText.replace(/\\n/g, ' ').trim();
        });
        rec.__ticket_id = row.getAttribute('data-row-key') || '';
        return rec;
    });
}"""


class AutotaskSession:
    """Persistente Playwright-Sitzung. Anmeldung/MFA bleiben manuell."""

    def __init__(self, profile_dir: Path, zone: str, headless: bool = False, login_timeout: int = 300) -> None:
        self.profile_dir = profile_dir
        self.zone = zone
        self.headless = headless
        self.login_timeout = login_timeout
        self._playwright: Any = None
        self._context: Any = None
        self.error = ""

    @property
    def base_url(self) -> str:
        return f"https://{self.zone}.autotask.net"

    def __enter__(self) -> "AutotaskSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.error = "Playwright fehlt. Bitte 'pip install -r requirements.txt' und 'playwright install chromium' ausführen."
            return self
        try:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            self._playwright = sync_playwright().start()
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=self.headless,
                viewport={"width": 1600, "height": 960},
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as exc:  # pragma: no cover - umgebungsabhängig
            self.error = f"Browser konnte nicht gestartet werden: {exc}"
        return self

    def __exit__(self, *_exc: object) -> None:
        for closer in (self._context, self._playwright):
            try:
                if closer is not None:
                    closer.close() if closer is self._context else closer.stop()
            except Exception:  # pragma: no cover - Aufräumen darf nicht scheitern
                pass

    @property
    def ready(self) -> bool:
        return self._context is not None and not self.error

    def open_grid(self, wait_login: bool = True) -> Any:
        if not self.ready:
            raise RuntimeError(self.error or "Browsersitzung nicht bereit")

        page = self._context.new_page()
        page.goto(f"{self.base_url}{GRID_PATH}", wait_until="domcontentloaded", timeout=60_000)
        try:
            page.wait_for_selector("div.SummaryMenuItem1", timeout=15_000)
            return page
        except Exception:
            pass

        if not wait_login or self.headless:
            page.close()
            raise TimeoutError("Anmeldung erforderlich, aber kein sichtbares Fenster verfügbar.")

        print("  Anmeldung erforderlich: bitte im geöffneten Fenster manuell anmelden (inkl. MFA).")
        print("  Es geht automatisch weiter, sobald 'Mein Arbeitsplatz & meine Queues' sichtbar ist.")
        page.bring_to_front()
        page.wait_for_selector("div.SummaryMenuItem1", timeout=self.login_timeout * 1000)
        return page


def parse_due(raw: str) -> datetime | None:
    if not raw:
        return None
    match = DUE_PATTERN.search(raw)
    if not match:
        return None
    day, month, year, hour, minute = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def collect_tickets(page: Any, views: list[str], page_size: int = 100) -> list[dict[str, Any]]:
    tickets: dict[str, dict[str, Any]] = {}
    for view in views:
        found = page.evaluate(SIDEBAR_SELECT_JS, view)
        if not found:
            print(f"  Warnung: Ansicht/Queue '{view}' nicht gefunden. 'list-queues' zeigt die genauen Namen.")
            continue
        page.wait_for_timeout(1500)
        page.evaluate(SET_PAGE_SIZE_JS, page_size)
        page.wait_for_timeout(1500)

        rows = page.evaluate(SCRAPE_GRID_JS)
        for row in rows:
            number = (row.get("Ticketnr.") or "").strip()
            if not number:
                continue
            if number in tickets:
                tickets[number]["_views"].add(view)
                continue
            row["_views"] = {view}
            row["url"] = (
                f"{page.url.split('/Mvc/')[0]}{TICKET_PATH.format(ticket_id=row.get('__ticket_id', ''))}"
                if row.get("__ticket_id")
                else ""
            )
            tickets[number] = row

    return list(tickets.values())


def sort_tickets(tickets: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    def key(t: dict[str, Any]) -> tuple[int, int, datetime]:
        due = parse_due(t.get("Fällig", ""))
        overdue_rank = 0 if (due and due < now) else 1
        priority_rank = PRIORITY_RANK.get((t.get("Priorität") or "").strip().lower(), 4)
        return (overdue_rank, priority_rank, due or datetime.max)

    return sorted(tickets, key=key)


def render_text(tickets: list[dict[str, Any]], now: datetime) -> str:
    lines = [f"Priorisierte Ticket-Arbeitsliste - {len(tickets)} Tickets (Stand {now:%d.%m.%Y %H:%M})", ""]
    for index, ticket in enumerate(tickets, start=1):
        due_raw = ticket.get("Fällig", "-") or "-"
        due_dt = parse_due(ticket.get("Fällig", ""))
        overdue = due_dt is not None and due_dt < now
        marker = "  [UEBERFAELLIG]" if overdue else ""
        title = (ticket.get("Titel") or "").strip()
        if len(title) > 70:
            title = title[:67] + "..."
        lines.append(f"{index:>2}. [{(ticket.get('Priorität') or '?'):<8}] {ticket.get('Ticketnr.', ''):<16} {title}")
        lines.append(
            f"      Firma: {ticket.get('Firma', '-')}  |  Queue: {ticket.get('Queue', '-')}  |  Status: {ticket.get('Status', '-')}"
        )
        lines.append(f"      Faellig: {due_raw}{marker}")
        if ticket.get("url"):
            lines.append(f"      Link: {ticket['url']}")
        lines.append("")
    return "\n".join(lines)


def write_html(tickets: list[dict[str, Any]], now: datetime, path: Path) -> Path:
    rows_html = []
    for ticket in tickets:
        due_dt = parse_due(ticket.get("Fällig", ""))
        overdue = due_dt is not None and due_dt < now
        row_class = "overdue" if overdue else ""
        url = ticket.get("url") or "#"
        number = ticket.get("Ticketnr.", "")
        title = ticket.get("Titel", "")
        rows_html.append(
            f"""<tr class="{row_class}">
  <td>{ticket.get('Priorität', '')}</td>
  <td><a href="{url}">{number}</a></td>
  <td>{title}</td>
  <td>{ticket.get('Firma', '')}</td>
  <td>{ticket.get('Queue', '')}</td>
  <td>{ticket.get('Status', '')}</td>
  <td>{ticket.get('Fällig', '')}</td>
</tr>"""
        )

    html = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Ticket-Arbeitsliste</title>
<style>
body {{ font-family: sans-serif; background: #111; color: #eee; padding: 24px; }}
h1 {{ font-size: 1.2rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid #333; padding: 6px 10px; text-align: left; font-size: 0.9rem; }}
th {{ color: #9ab; }}
tr.overdue td {{ color: #ff8a8a; }}
a {{ color: #7db8ff; }}
</style>
</head>
<body>
<h1>Priorisierte Ticket-Arbeitsliste - {len(tickets)} Tickets (Stand {now:%d.%m.%Y %H:%M})</h1>
<table>
<tr><th>Prioritaet</th><th>Ticket</th><th>Titel</th><th>Firma</th><th>Queue</th><th>Status</th><th>Faellig</th></tr>
{''.join(rows_html)}
</table>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def do_login(zone: str, profile_dir: Path, login_timeout: int) -> int:
    with AutotaskSession(profile_dir, zone, headless=False, login_timeout=login_timeout) as session:
        if not session.ready:
            print(f"Fehler: {session.error}")
            return 1
        print(f"Oeffne Autotask ({session.base_url}) ...")
        page = session.open_grid()
        print("  Angemeldet. 'Mein Arbeitsplatz & meine Queues' ist sichtbar.")
        page.close()
    return 0


def do_list_queues(zone: str, profile_dir: Path, login_timeout: int) -> int:
    with AutotaskSession(profile_dir, zone, headless=False, login_timeout=login_timeout) as session:
        if not session.ready:
            print(f"Fehler: {session.error}")
            return 1
        page = session.open_grid()
        names = page.evaluate(LIST_VIEWS_JS)
        print("Verfuegbare Ansichten/Queues (Reihenfolge wie in der Seitenleiste):\n")
        for name in names:
            print(f"  {name}")
        print(
            "\nHinweis: Queue-Namen koennen doppelt erscheinen (einmal unter 'Alle', "
            "einmal unter 'Nicht zugewiesen'). --views nutzt jeweils die erste Fundstelle, "
            "also die 'Alle'-Variante der Queue."
        )
        page.close()
    return 0


def do_worklist(
    zone: str,
    profile_dir: Path,
    login_timeout: int,
    views: list[str],
    top: int,
    html_path: Path | None,
    json_path: Path | None,
) -> int:
    with AutotaskSession(profile_dir, zone, headless=False, login_timeout=login_timeout) as session:
        if not session.ready:
            print(f"Fehler: {session.error}")
            return 1
        page = session.open_grid()
        tickets = collect_tickets(page, views)
        page.close()

    now = datetime.now()
    tickets = sort_tickets(tickets, now)
    if top > 0:
        tickets = tickets[:top]

    print(render_text(tickets, now))

    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps([{k: v for k, v in t.items() if not k.startswith("_")} for t in tickets], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nJSON: {json_path}")

    if html_path:
        target = write_html(tickets, now, html_path)
        print(f"HTML-Bericht: {target}")

    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Priorisierte Ticket-Arbeitsliste aus Autotask erzeugen (rein lesend).")
    parser.add_argument("--zone", default=DEFAULT_ZONE, help=f"Autotask-Zone/Subdomain, z.B. ww18 (Standard: {DEFAULT_ZONE})")
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR, help="Ort des lokalen Browserprofils")
    parser.add_argument("--login-timeout", type=int, default=300, help="Sekunden, die auf die manuelle Anmeldung gewartet wird")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("login", help="Autotask sichtbar oeffnen, um Anmeldung/MFA einmalig durchzufuehren")
    sub.add_parser("list-queues", help="Verfuegbare Ansichten/Queues aus der Seitenleiste auflisten")

    worklist_p = sub.add_parser("worklist", help="Priorisierte Ticket-Arbeitsliste erzeugen")
    worklist_p.add_argument(
        "--views",
        default=",".join(DEFAULT_VIEWS),
        help="Kommagetrennte Ansichten/Queues, genau wie in der Seitenleiste, z.B. "
        "'Offene Tickets,IT Level II-Support,Security'",
    )
    worklist_p.add_argument("--top", type=int, default=0, help="Nur die obersten N Tickets anzeigen (0 = alle)")
    worklist_p.add_argument("--html", type=Path, default=None, help="Zusaetzlich HTML-Bericht unter diesem Pfad schreiben")
    worklist_p.add_argument("--json", type=Path, default=None, help="Rohdaten zusaetzlich als JSON schreiben")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command == "login":
        return do_login(args.zone, args.profile_dir, args.login_timeout)
    if args.command == "list-queues":
        return do_list_queues(args.zone, args.profile_dir, args.login_timeout)
    if args.command == "worklist":
        views = [v.strip() for v in args.views.split(",") if v.strip()]
        return do_worklist(args.zone, args.profile_dir, args.login_timeout, views, args.top, args.html, args.json)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
