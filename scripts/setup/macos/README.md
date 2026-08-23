# macOS Arbeits-Setup

Bootstrap-Skript für ein neues Arbeits-MacBook. Es läuft **nach** der
firmeneigenen MDM-/Jamf-Einrichtung als persönliches Zusatz-Setup und
rührt keine von der IT verwalteten Profile, Zertifikate oder
Einstellungen an.

## Was das Skript macht

1. Prüft/installiert die Xcode Command Line Tools (Voraussetzung für Homebrew/Git).
2. Installiert oder aktualisiert [Homebrew](https://brew.sh).
3. Installiert alle Apps & CLI-Tools aus `Brewfile`:
   - **CLI**: Git, GitHub CLI (`gh`), `nvm` (Node), `pyenv` (Python)
   - **Apps**: Microsoft Teams, Microsoft Office, Google Chrome, Firefox,
     1Password (+ CLI), Raycast, Visual Studio Code, Postman (API-Client),
     Logitech G HUB, Logitech Options+, iTerm2 (Terminal), Maccy
     (Zwischenablage-Verlauf), CleanShot X (Screenshots/Recording), Bartender
     (Menüleiste), MeetingBar (Meeting-Beitritt), Windows App (RDP-Client),
     Zoom, Vorssaint (Menüleisten-Toolkit: Keep-Awake, System-Monitor,
     Volume-Mixer), AlDente (Ladeprozent-Limit), BetterDisplay (Display-/
     Auflösungsverwaltung), MiddleClick (Mittelklick per Trackpad), Parallels
     Desktop (VMs), DockDoor (Fenster-Vorschau im Dock), Loop (Fenstermanager),
     Nextcloud-Client (Datei-Sync), Boring Notch (Notch-Erweiterung, Ersatz für
     NotchNook, via Third-Party-Tap `theboredteam/boring-notch`), Command X
     (Cut & Paste im Finder, **nur über Mac App Store/`mas`**, kostenpflichtig
     – erfordert vorherige Anmeldung in der App-Store-App mit der Apple-ID)
   - **KI/Lokale Modelle**: LM Studio, LM Studio Bionic (nur auf Apple
     Silicon; auf Intel-Macs wird der Eintrag automatisch übersprungen)
   - **KI-Coding-CLIs**: GitHub Copilot CLI, Claude Code, OpenCode, Superset
     (Terminal für Agenten-Orchestrierung, alle über Brewfile), plus Pi
     (`pi.dev`) via npm, siehe Schritt 4
   - **Gaming**: Steam, NVIDIA GeForce NOW
   - **Kubernetes**: `kubectl` (kubernetes-cli), `helm`
4. Richtet `nvm`/`pyenv` in `~/.zshrc` ein, installiert die aktuelle
   Node.js-LTS- sowie die aktuelle Python-3.x-Version und installiert
   anschließend die Pi-CLI (`@earendil-works/pi-coding-agent`) global via npm.
5. Setzt eine Git-Grundkonfiguration (`user.name`, `user.email`,
   `init.defaultBranch`, `pull.rebase`), fragt Name/E-Mail interaktiv ab,
   falls noch nicht gesetzt.
6. Bietet einen interaktiven `gh auth login` an, falls die GitHub CLI noch
   nicht angemeldet ist.
7. Legt `~/Development` an und klont dort alle Repos, die in der `REPOS`-
   Liste am Kopf von `bootstrap.sh` eingetragen sind (per `gh repo clone`,
   funktioniert dadurch auch bei privaten Repos ohne eigenes SSH-Key-Setup).
   Submodule werden automatisch mit initialisiert (`--recurse-submodules`
   beim Klonen, zusätzlich ein idempotenter `git submodule update --init
   --recursive`-Nachlauf für Repos mit `.gitmodules`).
8. Setzt persönliche macOS-Komfort-Einstellungen (keine MDM-verwalteten
   Bereiche):
   - Dock: Auto-Hide, kleinere Icons, keine "zuletzt verwendet"-Apps, Position unten
   - Finder: Dateiendungen/versteckte Dateien anzeigen, Pfadleiste, Listenansicht
   - Tastatur: schnellere Wiederholrate
   - Trackpad: Tippen zum Klicken
   - Screenshots: als PNG nach `~/Screenshots`
   - Erscheinungsbild: Dark Mode
   - Scrollen: klassische (nicht-natürliche) Scrollrichtung
   - Hintergrundbild wird von einer festen URL heruntergeladen (nach
     `~/Pictures/Wallpapers/`) und auf allen Displays gesetzt.
9. Setzt System-/Sicherheitseinstellungen (benötigen `sudo`-Passwort):
   - Computername/Hostname/LocalHostName auf `ITC-MB-2603-01`
   - Touch ID für `sudo` im Terminal aktivieren
   - Bildschirm sofort sperren, sobald Ruhezustand/Bildschirmschoner startet
   - macOS-Firewall aktivieren
   - Automatische Software-Updates (Suche/Download/kritische Installation)
   - Homebrew-Analytics/Telemetrie deaktivieren (`brew analytics off`, in
     Schritt 2)

Das Skript ist **idempotent**: mehrfaches Ausführen ist sicher, bereits
erledigte Schritte werden übersprungen bzw. nur aktualisiert.

## Nutzung auf einem komplett frischen Mac

Da auf einem nagelneuen Mac weder Git noch Homebrew vorhanden sind, kommt
das Skript per ZIP auf den Rechner:

1. Im Browser auf **https://github.com/SoniiiT/automation** einloggen
   (privates Repo) und über **Code → Download ZIP** herunterladen.
2. ZIP entpacken (Doppelklick im Finder).
3. Terminal öffnen und ins entpackte Verzeichnis wechseln:
   ```bash
   cd ~/Downloads/automation-main/scripts/setup/macos
   bash bootstrap.sh
   ```
4. Falls dabei die Xcode Command Line Tools noch nicht installiert waren,
   erscheint ein System-Dialog. Nach dessen Abschluss das Skript einfach
   erneut ausführen (`bash bootstrap.sh`).
5. Bei Schritt 6 (`gh auth login`) einmal anmelden – danach funktioniert
   auch das automatische Klonen der Repos aus Schritt 7.

## Eigene Repos für ~/Development eintragen

Am Kopf von `bootstrap.sh` befindet sich die `REPOS`-Liste:

```bash
REPOS=(
    "automation|SoniiiT/automation"
    # "mein-projekt|SoniiiT/mein-projekt"
)
```

Format: `"ordnername|owner/repo"`. Einfach weitere Zeilen ergänzen und das
Skript erneut ausführen – bereits vorhandene Ordner werden übersprungen,
neue Repos werden nach `~/Development/<ordnername>` geklont.

## Anpassen

- **Apps/Tools ändern**: `Brewfile` bearbeiten (Formeln mit `brew "..."`,
  Apps mit `cask "..."`), danach `bash bootstrap.sh` erneut ausführen.
  Aktuellen Stand exportieren: `brew bundle dump --file=Brewfile --force`.
- **macOS-Defaults ändern**: Abschnitt 8 in `bootstrap.sh` erweitern; die
  Syntax folgt `defaults write <domain> <key> <type> <value>`.
- **Computername ändern**: `COMPUTER_NAME` am Kopf von `bootstrap.sh` anpassen.

## Nicht enthalten

- Keine Änderungen an MDM-/Jamf-Profilen, VPN-Konfiguration oder
  Firmenzertifikaten – das übernimmt die IT-Einrichtung.
- Kein automatisches Login für Teams/Office/1Password – diese Apps beim
  ersten Start manuell mit dem Arbeitskonto anmelden.
- **Memtime** und **Zscaler Client Connector**: haben keinen Homebrew-Cask
  und erfordern vorab Login/Account bzw. einen firmeneigenen Download-Link
  (Zscaler wird ggf. ohnehin über MDM ausgerollt) – daher bewusst nicht im
  Skript enthalten, manuell installieren.
