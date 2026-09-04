# Autotask Ticket-Arbeitsliste

Holt Tickets aus "Mein Arbeitsplatz & meine Queues" in Kaseya Autotask,
priorisiert sie (überfällig zuerst, dann Priorität, dann Fälligkeitsdatum)
und gibt eine Arbeitsliste mit direktem Link zu jedem Ticket aus.

**Rein lesend.** Es werden keine Tickets angelegt, geändert, kommentiert oder
geschlossen. Bearbeiten und Abschließen bleiben bewusst manuell (Klick auf
den Ticket-Link) bzw. erfolgen in einer separaten, begleiteten Sitzung, in
der jede Änderung einzeln bestätigt wird.

Es gibt keinen Autotask-API-Zugang für dieses Konto, daher liest das Skript
direkt die Weboberfläche aus (Playwright, sichtbares Fenster, persistentes
Browserprofil). Die Anmeldung inkl. MFA erfolgt immer manuell; gespeichert
wird nur das Browserprofil, niemals ein Passwort.

## Installation

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## Verwendung

```powershell
# Einmalig: Anmeldung/MFA im sichtbaren Fenster durchführen
python ticket_worklist.py login

# Verfügbare Ansichten/Queues aus der Seitenleiste anzeigen
python ticket_worklist.py list-queues

# Arbeitsliste für die eigenen offenen Tickets
python ticket_worklist.py worklist

# Arbeitsliste über mehrere Queues, zusätzlich als HTML-Bericht
python ticket_worklist.py worklist --views "Offene Tickets,IT Level II-Support,Security" --html bericht.html

# Nur die 10 dringendsten Tickets
python ticket_worklist.py worklist --top 10
```

`--views` erwartet die Namen genau wie in der Seitenleiste von "Mein
Arbeitsplatz & meine Queues" (z. B. `Offene Tickets`, `Überfällige Tickets`,
`IT Level I-Support`, `IT Level II-Support`, `Security`, `R&D`, ...).
Erscheint ein Queue-Name doppelt (einmal unter "Alle", einmal unter "Nicht
zugewiesen"), verwendet das Skript die erste Fundstelle – also alle Tickets
der Queue, nicht nur die unzugewiesenen. `list-queues` zeigt die exakten
Namen für die eigene Autotask-Instanz.

## Zone

Autotask-Konten hängen an einer nummerierten Zone (z. B. `ww18`). Falls die
Zone abweicht: `--zone ww1` (oder andere Nummer) angeben. Falsche Zone zeigt
in der Regel einfach die normale Login-Seite ohne Fehlermeldung.

## Grenzen

- Die Web-Oberfläche kann sich ändern; die Selektoren
  (`div.SummaryMenuItem1`, `tr.Display`, `data-row-key`, Spaltenüberschriften
  mit Klasse `SortCell`) wurden gegen die reale Oberfläche geprüft, sind aber
  nicht von Kaseya garantiert stabil.
- Pro Queue werden bis zu 100 Tickets pro Seite gelesen; bei mehr als 100
  Treffern in einer einzelnen Queue wird nicht automatisch weitergeblättert.
- MFA wird nicht automatisiert oder umgangen.
