# Morning Briefing

Ein Tagesbriefing aus **Outlook**, **Teams** und **Kaseya Autotask** in einer
Ansicht. Statt drei Oberflächen morgens einzeln zu prüfen, entsteht lokal eine
priorisierte Aufgabenliste mit Zeitvorschlägen.

Der Lauf ist **ausschließlich lesend**: keine Nachrichten senden, keine Tickets
ändern, keine Termine verschieben, nichts als gelesen markieren.

## Ablauf

```text
Outlook-Web  Teams-Web  Autotask-Web
        \        |        /
      lokale Browser-Automation (persistentes Profil)
                 |
      Bereinigung: HTML, Signaturen, Zitate, Duplikate
                 |
      Datenschutzschicht: Kontaktdaten -> Platzhalter
                 |
              Claude CLI
                 |
      Validierung + regelbasierte Priorisierung
                 |
      Terminalbericht und lokale HTML-Datei
```

## Datenschutz

Vor jedem KI-Aufruf werden lokal ersetzt:

| Kategorie | Beispiel | Platzhalter |
|---|---|---|
| E-Mail | `max@musterfirma.de` | `[EMAIL_01]` |
| Telefon | `+49 1234 456789` | `[PHONE_01]` |
| Firma | `Musterfirma GmbH` | `[COMPANY_01]` |
| Adresse | `Musterstr. 12, 12345 Musterstadt` | `[ADDRESS_01]` |
| Kunden-/Benutzernummer | `Kundennummer: 998877` | `[ACCOUNT_01]` |
| Links | `https://cloud.kunde.de/s/x` | `[LINK_01]` |
| Zugangsdaten | `Passwort: ...`, API-Keys, Tokens | `[SECRET_01]` |
| IBAN, Kartennummer, IP | | `[IBAN_01]`, `[CARD_01]`, `[IP_01]` |

**Personennamen bleiben erhalten**, weil sie ohne Kontaktdaten, Firmenbezug und
Kennungen nicht zur Identifikation ausreichen. Das ist bewusst gewählt, damit
die Zusammenfassung lesbar bleibt (`keep_names: false` schaltet es ab).

Weitere Schutzmechanismen:

- Die Zuordnung Platzhalter zu Originalwert bleibt im Prozess und wird nie gesendet.
- Der fertige Prompt wird vor dem Senden erneut geprüft. Bei einem Fund bricht
  der KI-Aufruf ab und der Bericht wird ohne KI erzeugt.
- Die KI-Antwort wird ebenfalls geprüft und bei Funden verworfen.
- Nach der Antwort werden lokal nur Ticketnummern zurückgesetzt, keine Links.
- Antworten zu unbekannten Vorgangs-IDs werden verworfen (keine Halluzinationen).
- Nachrichten gelten als Daten, nicht als Anweisungen. Anweisungsartiger Text
  wird erkannt und im Bericht vermerkt.

Zusätzlich gilt: Ob Inhalte überhaupt an einen externen Anbieter gehen dürfen,
ist eine organisatorische Entscheidung. Diese Schicht senkt das Risiko, ersetzt
aber keine Freigabe durch den Datenschutzverantwortlichen.

## Priorisierung

Lokale Regeln entscheiden über die Dringlichkeit, die KI liefert die Sprache.
Die KI darf **hochstufen, aber harte Signale nicht abschwächen**.

```text
Systemausfall / kritisch gemeldet
> Frist läuft heute ab
> Kundenticket mit hoher Priorität
> Kunde oder Kollege wartet
> für heute zugesagt
> offene Nachricht
> reine Information
```

Relative Zeitangaben werden gegen den Empfangszeitpunkt gerechnet: Schrieb
jemand gestern „lass uns morgen reden“, ist damit **heute** gemeint.

Kritische Vorgänge bleiben immer am heutigen Tag, auch wenn der Kalender voll
ist. Termine werden nie automatisch verschoben; bei Kollisionen erscheint nur
ein Vorschlag mit Begründung.

## Installation

```powershell
pip install -r requirements.txt
python -m playwright install chromium
Copy-Item config.example.yaml config.yaml
```

`config.yaml` ist bewusst nicht im Repository.

## Verwendung

```powershell
# Offline-Testlauf mit Beispieldaten, ohne Browser und ohne KI
python main.py --demo --no-ai

# Anzeigen, was die KI genau zu sehen bekäme
python main.py --demo --show-prompt

# Anmeldung erneuern (Microsoft beendet die Sitzung alle paar Tage)
python main.py --login

# Normaler Lauf mit HTML-Bericht
python main.py --html --open
```

| Option | Wirkung |
|---|---|
| `--demo` | Beispieldaten statt echter Quellen |
| `--no-ai` | Ohne Claude CLI, nur regelbasiert |
| `--login` | Öffnet die Portale zur manuellen Anmeldung |
| `--show-prompt` | Zeigt den anonymisierten Prompt |
| `--html` / `--open` | Schreibt bzw. öffnet den HTML-Bericht |
| `--config` | Alternative Konfigurationsdatei |

## Automatischer Start

```powershell
.\install-windows.ps1 -Time "07:45"
```

Die Aufgabe läuft sichtbar, damit eine fällige Microsoft-Anmeldung samt MFA
manuell abgeschlossen werden kann. MFA wird nicht automatisiert oder umgangen.

## Anmeldung

Gespeichert wird nur ein lokales Browserprofil unter `profile_dir`, niemals ein
Passwort. Läuft die Sitzung ab, öffnet sich das Anmeldefenster und der Lauf
setzt danach automatisch fort. Ist eine Quelle nicht verfügbar, weist der
Bericht das ausdrücklich aus, statt „keine Nachrichten“ zu melden.

## Selektoren anpassen

Microsoft und Autotask ändern ihre Oberflächen regelmäßig. Liefert eine Quelle
nichts, lassen sich die Selektoren in `config.yaml` überschreiben:

```yaml
teams:
  selectors:
    row: "div[data-tid='activity-feed-item']"
    sender: "span[data-tid='activity-title']"
```

Die Standardwerte stehen in `briefing/collectors/microsoft.py` und
`briefing/collectors/autotask.py`.

## Tests

```powershell
python tests\test_privacy.py
python tests\test_pipeline.py
```

Beide Testdateien laufen ohne Netzwerk, ohne Browser und ohne Claude CLI.

## Aufbau

| Datei | Zweck |
|---|---|
| `main.py` | CLI-Einstieg |
| `briefing/config.py` | Konfiguration |
| `briefing/models.py` | Datenmodell |
| `briefing/normalize.py` | Textbereinigung und Duplikate |
| `briefing/privacy.py` | Datenschutzschicht |
| `briefing/summarize.py` | Claude CLI und Antwortprüfung |
| `briefing/plan.py` | Priorisierung und Tagesplan |
| `briefing/render.py` | Terminal- und HTML-Ausgabe |
| `briefing/pipeline.py` | Gesamtablauf |
| `briefing/collectors/` | Outlook, Kalender, Teams, Autotask |
| `briefing/demo.py` | Beispieldaten |

## Grenzen

- Web-Oberflächen können sich ändern; dann müssen Selektoren angepasst werden.
- Die Erkennung vertraulicher Daten arbeitet mustergestützt und ist nicht
  fehlerfrei. `--show-prompt` sollte vor dem ersten Echtbetrieb geprüft werden.
- Anhänge werden bewusst nicht gelesen.
- Ohne Claude CLI entsteht weiterhin ein Bericht, nur ohne Zusammenfassung.
