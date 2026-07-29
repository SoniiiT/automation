"""Browsersitzung mit persistentem Profil.

Die Anmeldung erfolgt bewusst manuell im sichtbaren Fenster. MFA wird nicht
automatisiert. Gespeichert wird nur das Browserprofil, niemals ein Passwort.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import Item, Source, SourceStatus


@dataclass
class CollectorResult:
    items: list[Item]
    status: SourceStatus


def unavailable(source: Source, detail: str) -> CollectorResult:
    return CollectorResult(items=[], status=SourceStatus(source=source, ok=False, detail=detail))


class BrowserSession:
    """Kapselt Playwright, damit der Rest des Projekts ohne Playwright läuft."""

    def __init__(self, profile_dir: Path, headless: bool = False, login_timeout: int = 300) -> None:
        self.profile_dir = profile_dir
        self.headless = headless
        self.login_timeout = login_timeout
        self._playwright: Any = None
        self._context: Any = None
        self.error = ""

    def __enter__(self) -> "BrowserSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.error = "Playwright fehlt (pip install -r requirements.txt)"
            return self
        try:
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            self._playwright = sync_playwright().start()
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=self.headless,
                viewport={"width": 1440, "height": 960},
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

    def open(self, url: str, ready_selector: str, wait_for_login: bool = True) -> Any:
        """Öffnet eine Seite und wartet gegebenenfalls auf die manuelle Anmeldung."""
        if not self.ready:
            raise RuntimeError(self.error or "Browsersitzung nicht bereit")

        page = self._context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        try:
            page.wait_for_selector(ready_selector, timeout=15_000)
            return page
        except Exception:
            pass

        if not wait_for_login or self.headless:
            page.close()
            raise TimeoutError("Anmeldung erforderlich, aber kein sichtbares Fenster verfügbar")

        print(f"  Anmeldung erforderlich: {url}")
        print("  Bitte im geöffneten Fenster anmelden. Es wird automatisch fortgesetzt.")
        page.bring_to_front()
        page.wait_for_selector(ready_selector, timeout=self.login_timeout * 1000)
        return page
