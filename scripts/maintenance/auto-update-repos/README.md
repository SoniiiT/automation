# Auto-Update Git Repositories

Aktualisiert beim Systemstart / Login Git-Repositories (inklusive verschachtelter Submodule) in einem definierten Ordner. Standardmäßig werden lokale Änderungen geschützt; mit `-Force` bzw. `--force` wird der konfigurierte Upstream zur Source of Truth.

## Sicherheitsregeln

Das Skript verfolgt bewusst eine konservative Strategie:

1. Es scannt standardmäßig nur direkte Unterordner auf Git-Repositories.
2. Bei lokalen Änderungen oder neuen, nicht getrackten Dateien wird das Repository übersprungen; der Remote-Stand wird trotzdem per `git fetch --prune` sichtbar gemacht.
3. Es verwendet den konfigurierten Upstream-Branch und prüft, wie viele Commits lokal bzw. in der Cloud fehlen.
4. Im Standardmodus wird ausschließlich per Fast-Forward aktualisiert. Es gibt keinen automatischen Stash, Merge, Rebase, Reset oder Delete.
5. Lokale Commits und divergierende Branches werden im Standardmodus übersprungen und als manuelle Aufgabe protokolliert.
6. Mit `-Force` bzw. `--force` wird auf den Remote-Upstream zurückgesetzt (`git reset --hard`) und anschließend werden nicht getrackte Dateien/Ordner mit `git clean -fd` gelöscht.
7. Ignorierte Dateien wie `.env` oder `node_modules` bleiben auch mit `-Force` erhalten; `git clean -fdx` wird nicht verwendet.
8. Mit `-Recurse`/`-Recursive` bzw. `--recurse`/`--recursive` können verschachtelte Repositories zusätzlich gefunden werden.

## Submodule

Submodule werden nicht als eigene Repositories gescannt (ihr `.git` ist eine Datei), sondern über ihr Parent-Repository behandelt – auch verschachtelte:

1. Sobald das Parent-Repository aktuell ist (bereits aktuell oder gerade per Fast-Forward aktualisiert), wird `git submodule sync --recursive` und `git submodule update --init --recursive` ausgeführt. Submodule stehen danach auf dem Commit, den der Parent festgeschrieben hat (Standardverhalten von Git, Detached HEAD).
2. Der Lokale-Änderungen-Check des Parents ignoriert Submodule (`--ignore-submodules=all`); der Zustand der Submodule wird separat geprüft.
3. Ohne `--force` wird das Submodule-Update übersprungen und als `Submodule skipped` gezählt, wenn ein Submodule
   - lokale Änderungen oder neue Dateien hat, oder
   - einen Commit ausgecheckt hat, der nicht hinter dem gespeicherten Commit liegt (lokale Commits bzw. neuerer Stand).
   Ob das Ziel-Commit lokal noch fehlt, kann vor dem Fetch nicht geprüft werden; dann wird nur auf lokale Änderungen geprüft.
4. Mit `--force` werden Submodule per `update --force` auf den gespeicherten Commit gesetzt und mit `git clean -fd` bereinigt.

## Boot-/Login-Verhalten

- Vor dem ersten Fetch wartet das Skript bis zu `NETWORK_WAIT_SECONDS` (Standard 60, `0` = aus) auf das Netzwerk (`NETWORK_CHECK_URL`, Standard `https://github.com`). systemd-User-Units können nicht auf `network-online.target` warten.
- `GIT_TERMINAL_PROMPT=0` und (falls nicht anders konfiguriert) `ssh -o BatchMode=yes`: Es gibt nie eine interaktive Passwort-/Host-Key-Abfrage, die den Start blockiert. SSH-Schlüssel müssen also über einen Agent oder ein Credential-Helper verfügbar sein.
- `node_modules` wird beim rekursiven Scan übersprungen.

`-Force` ist absichtlich destruktiv. Lokale Änderungen, lokale Commits und ungetrackte Zusatzordner müssen vorher nicht committed werden, wenn sie verworfen werden sollen.

## Konfiguration

Der GitHub-Ordner wird in folgender Reihenfolge ermittelt:

| Priorität | Quelle |
|-----------|--------|
| 1 | Argument beim Aufruf des Skripts / Installers |
| 2 | Umgebungsvariable `GITHUB_FOLDER` |
| 3 | Standardwert `~/github` |

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `update-repos.ps1` | Hauptskript für Windows (PowerShell) |
| `update-repos.sh`  | Hauptskript für Linux & macOS (Bash) |
| `install-windows.ps1` | Registriert Task Scheduler Job (bei Anmeldung) |
| `install-linux.sh` | Installiert systemd User Service (`[Ordner] [--recurse] [--force]`) |
| `install-macos.sh` | Installiert launchd LaunchAgent (`[Ordner] [--recurse] [--force]`) |

## Installation

### Windows

```powershell
# Als Administrator ausführen
.\install-windows.ps1 -GithubFolder "C:\Users\<name>\github"
```

Oder mit Umgebungsvariable:

```powershell
$env:GITHUB_FOLDER = "C:\Users\<name>\github"
.\install-windows.ps1
```

### Linux

```bash
chmod +x install-linux.sh
./install-linux.sh ~/github

# Verschachtelte Repositories (z. B. ~/Development/<Gruppe>/<Repo>) ebenfalls aktualisieren
./install-linux.sh ~/Development --recurse
```

Ausgabe: `~/.logs/auto-update-repos.log` sowie `journalctl --user -u auto-update-repos.service`.

### macOS

```bash
chmod +x install-macos.sh
./install-macos.sh ~/github

# Verschachtelte Repositories ebenfalls aktualisieren
./install-macos.sh ~/github --recurse
```

## Manueller Testlauf

```powershell
# Windows
.\update-repos.ps1 -GithubFolder "C:\Users\<name>\github"

# Verschachtelte Repositories ebenfalls scannen
.\update-repos.ps1 -GithubFolder "C:\Users\<name>\github" -Recurse

# Cloud als Source of Truth: lokale Änderungen und ungetrackte Dateien verwerfen
.\update-repos.ps1 -GithubFolder "C:\Users\<name>\github" -Force -Recursive
```

```bash
# Linux / macOS
bash update-repos.sh ~/github

# Verschachtelte Repositories ebenfalls scannen
bash update-repos.sh ~/github --recurse

# Cloud als Source of Truth: lokale Änderungen und ungetrackte Dateien verwerfen
bash update-repos.sh ~/github --force --recursive
```

## Logs

```
~/.logs/auto-update-repos.log
```

Unter macOS schreibt launchd zusätzlich nach `~/.logs/auto-update-repos.launchd.log`.

Die Zusammenfassung unterscheidet aktualisierte, bereits aktuelle, übersprungene und fehlgeschlagene Repositories sowie übersprungene Submodule. Übersprungene Repositories können mit `git status`, `git branch -vv` und `git log --oneline HEAD..@{upstream}` geprüft und anschließend bewusst manuell synchronisiert werden.
