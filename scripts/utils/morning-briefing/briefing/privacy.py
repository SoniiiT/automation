"""Lokale Datenschutzschicht.

Alle personenbezogenen und vertraulichen Werte werden hier durch stabile
Platzhalter ersetzt, bevor Text an ein externes Modell übergeben wird. Die
Zuordnung Platzhalter -> Originalwert verlässt diesen Prozess nicht.

Personennamen bleiben bewusst erhalten, weil sie ohne Kontaktdaten,
Firmenbezug und Kennungen nicht zur Identifikation ausreichen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Nur Ticketnummern werden nach der KI-Antwort lokal wieder eingesetzt.
# Links aus Nachrichtentexten bleiben Platzhalter, weil sie Kunden- und
# Firmendomains enthalten koennen.
RESTORABLE = ("TICKET",)

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>\"')]+", re.IGNORECASE)
_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
_PHONE = re.compile(
    r"(?<![\w\[])(?:\+\d{1,3}|00\d{1,3}|0)\d(?:[\d ()/-]{4,18}\d)(?!\d)"
)
_TICKET = re.compile(
    r"\b(?:T\d{8}\.\d{4}|(?:Ticket|Ticket-?Nr\.?|TicketNr|INC|REQ|CH)[ #:-]*\d{3,})\b",
    re.IGNORECASE,
)
_COMPANY = re.compile(
    r"\b[A-ZÄÖÜ][\wÄÖÜäöüß&.-]*(?:[ ][A-ZÄÖÜ0-9][\wÄÖÜäöüß&.-]*){0,3}"
    r"[ ](?:GmbH(?:[ ]&[ ]Co\.?[ ]?KG)?|AG|KG|OHG|UG|mbH|e\.?V\.?|Ltd\.?|Inc\.?|SE)\b"
)
_STREET = re.compile(
    r"\b[A-ZÄÖÜ][\wÄÖÜäöüß.-]*(?:str\.?|straße|strasse|weg|allee|platz|gasse|ring)"
    r"[ ]?\d+[a-zA-Z]?\b",
    re.IGNORECASE,
)
_ZIP_CITY = re.compile(r"\b\d{5}[ ][A-ZÄÖÜ][\wÄÖÜäöüß.-]+(?:[ -][A-ZÄÖÜ][\wÄÖÜäöüß.-]+)?\b")
_ACCOUNT_ID = re.compile(
    r"\b(?:Kundennummer|Kunden-?Nr\.?|Benutzernummer|Benutzer-?ID|User-?ID|"
    r"Personalnummer|Vertragsnummer|Mitarbeiternummer)\b[ :#-]*[\w.-]+",
    re.IGNORECASE,
)
# Label + Wert, z. B. "E-Mail: max@example.de" oder "Passwort: geheim".
_SECRET_LINE = re.compile(
    r"(?P<label>\b(?:Passwort|Kennwort|Password|Passphrase|API[- ]?Key|Api[- ]?Token|"
    r"Access[- ]?Token|Client[- ]?Secret|Secret|Token|Zugangsdaten|Credentials)\b)"
    r"(?P<sep>[ ]*[:=][ ]*)(?P<value>\S[^\r\n]*)",
    re.IGNORECASE,
)
_LABELLED_CONTACT = re.compile(
    r"(?P<label>\b(?:E-?Mail(?:[- ]?Adresse)?|Mailadresse|Telefon(?:nummer)?|Tel\.?|"
    r"Mobil(?:nummer)?|Handy|Fax|Durchwahl|Benutzer(?:name)?|Username|Login|Anschrift|"
    r"Adresse)\b)(?P<sep>[ ]*[:=][ ]*)(?P<value>[^\s\[\r\n][^\s\r\n]*)"
)
_LABEL_CATEGORY = {
    "mail": "EMAIL",
    "telefon": "PHONE",
    "tel": "PHONE",
    "mobil": "PHONE",
    "handy": "PHONE",
    "fax": "PHONE",
    "durchwahl": "PHONE",
    "benutzer": "USER",
    "username": "USER",
    "login": "USER",
    "anschrift": "ADDRESS",
    "adresse": "ADDRESS",
}
_PLACEHOLDER = re.compile(r"\[([A-Z]+)_(\d{2,})\]")

# Muster, die auf eingeschleuste Anweisungen in Fremdnachrichten hindeuten.
_INJECTION_HINTS = (
    "ignoriere",
    "ignore previous",
    "ignore all",
    "vergiss deine",
    "system prompt",
    "du bist jetzt",
    "you are now",
    "act as",
    "disregard",
)


@dataclass
class RedactionReport:
    """Ergebnis einer Bereinigung inklusive Zählung je Kategorie."""

    text: str
    counts: dict[str, int] = field(default_factory=dict)
    injection_suspected: bool = False


class Redactor:
    """Ersetzt vertrauliche Werte durch stabile, lokale Platzhalter."""

    def __init__(
        self,
        company_terms: tuple[str, ...] | list[str] = (),
        keep_names: bool = True,
        extra_patterns: dict[str, str] | None = None,
    ) -> None:
        self.keep_names = keep_names
        self._mapping: dict[str, str] = {}
        self._reverse: dict[str, str] = {}
        self._counters: dict[str, int] = {}
        self._company_terms: set[str] = {t for t in company_terms if t}
        self._extra = [
            (name.upper(), re.compile(pattern, re.IGNORECASE))
            for name, pattern in (extra_patterns or {}).items()
        ]

    # -- Platzhalterverwaltung ------------------------------------------------
    def _placeholder(self, category: str, value: str) -> str:
        key = f"{category}:{value.strip().lower()}"
        existing = self._mapping.get(key)
        if existing:
            return existing
        index = self._counters.get(category, 0) + 1
        self._counters[category] = index
        token = f"[{category}_{index:02d}]"
        self._mapping[key] = token
        self._reverse[token] = value.strip()
        return token

    @property
    def mapping(self) -> dict[str, str]:
        """Platzhalter -> Originalwert. Nur für die lokale Weiterverarbeitung."""
        return dict(self._reverse)

    # -- Bereinigung ----------------------------------------------------------
    def redact(self, text: str | None) -> str:
        return self.redact_report(text).text

    def redact_report(self, text: str | None) -> RedactionReport:
        if not text:
            return RedactionReport(text="")

        counts: dict[str, int] = {}

        def bump(category: str) -> None:
            counts[category] = counts.get(category, 0) + 1

        def sub(category: str, value: str) -> str:
            bump(category)
            return self._placeholder(category, value)

        working = text

        # Firmendomains vor der E-Mail-Ersetzung als Firmenbegriff registrieren.
        for match in _EMAIL.finditer(working):
            domain = match.group(0).split("@", 1)[1]
            label = domain.split(".")[0]
            if len(label) > 2 and label.lower() not in {"gmail", "outlook", "web", "gmx"}:
                self._company_terms.add(label)

        # 1. Zugangsdaten zuerst: deren Werte sind beliebige Zeichenfolgen.
        working = _SECRET_LINE.sub(
            lambda m: f"{m.group('label')}{m.group('sep')}"
            + sub("SECRET", m.group("value")),
            working,
        )

        # 2. Eindeutig strukturierte Werte. Diese laufen vor den Label-Mustern,
        #    damit der umgebende Satz für die Zusammenfassung erhalten bleibt.
        working = _TICKET.sub(lambda m: sub("TICKET", m.group(0)), working)
        working = _EMAIL.sub(lambda m: sub("EMAIL", m.group(0)), working)
        working = _URL.sub(lambda m: sub("LINK", m.group(0)), working)
        working = _IBAN.sub(lambda m: sub("IBAN", m.group(0)), working)
        working = _IPV4.sub(lambda m: sub("IP", m.group(0)), working)
        # Telefonnummern vor Kartennummern: lange Rufnummern mit Vorwahl
        # erreichen sonst die Ziffernlaenge einer Kartennummer.
        working = _PHONE.sub(lambda m: sub("PHONE", m.group(0)), working)
        working = _CARD.sub(lambda m: sub("CARD", m.group(0)), working)

        # 3. Sicherheitsnetz für benannte Werte, die oben nicht erkannt wurden.
        working = _ACCOUNT_ID.sub(lambda m: sub("ACCOUNT", m.group(0)), working)
        working = _LABELLED_CONTACT.sub(
            lambda m: f"{m.group('label')}{m.group('sep')}"
            + sub(_label_category(m.group("label")), m.group("value")),
            working,
        )

        # 4. Organisations- und Ortsbezug.
        working = _COMPANY.sub(lambda m: sub("COMPANY", m.group(0)), working)
        working = _STREET.sub(lambda m: sub("ADDRESS", m.group(0)), working)
        working = _ZIP_CITY.sub(lambda m: sub("ADDRESS", m.group(0)), working)

        for term in sorted(self._company_terms, key=len, reverse=True):
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            working = pattern.sub(lambda m: sub("COMPANY", m.group(0)), working)

        for name, pattern in self._extra:
            working = pattern.sub(lambda m, n=name: sub(n, m.group(0)), working)

        lowered = text.lower()
        injection = any(hint in lowered for hint in _INJECTION_HINTS)
        return RedactionReport(text=working, counts=counts, injection_suspected=injection)

    # -- Rückersetzung und Prüfung -------------------------------------------
    def restore(self, text: str, categories: tuple[str, ...] = RESTORABLE) -> str:
        """Setzt nur unkritische Platzhalter wie Ticketnummern und Links zurück."""

        def replace(match: re.Match[str]) -> str:
            token = match.group(0)
            category = match.group(1)
            if category not in categories:
                return token
            return self._reverse.get(token, token)

        return _PLACEHOLDER.sub(replace, text)

    def audit(self, text: str | None) -> list[str]:
        """Meldet vertrauliche Muster, die noch im Text stehen."""
        if not text:
            return []
        findings: list[str] = []
        checks = (
            ("E-Mail-Adresse", _EMAIL),
            ("Telefonnummer", _PHONE),
            ("URL", _URL),
            ("IP-Adresse", _IPV4),
            ("IBAN", _IBAN),
        )
        for label, pattern in checks:
            if pattern.search(text):
                findings.append(label)
        for term in self._company_terms:
            if re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
                findings.append(f"Firmenbezug ({term})")
                break
        return findings


def _label_category(label: str) -> str:
    key = label.lower().replace("-", "").replace(" ", "")
    for needle, category in _LABEL_CATEGORY.items():
        if needle in key:
            return category
    return "CONTACT"
