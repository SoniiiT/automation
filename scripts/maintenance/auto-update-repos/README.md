# Auto-Update Git Repositories

Zieht beim Systemstart / Login automatisch die neusten Commits für alle Git-Repos in einem definierten Ordner.

## Funktionsweise

1. Scannt alle Unterordner im konfigurierten GitHub-Verzeichnis auf `.git`-Repos.
2. Erkennt lokale Änderungen und **stasht** sie temporär.
3. Führt `git pull --ff-only` auf dem aktuellen Branch aus.
4. Stellt den Stash danach wieder her.
5. Schreibt ein detailliertes Log nach `~/.logs/auto-update-repos.log`.

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
| `install-linux.sh` | Installiert systemd User Service |
| `install-macos.sh` | Installiert launchd LaunchAgent |

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
```

### macOS

```bash
chmod +x install-macos.sh
./install-macos.sh ~/github
```

## Manueller Testlauf

```powershell
# Windows
.\update-repos.ps1 -GithubFolder "C:\Users\<name>\github"
```

```bash
# Linux / macOS
bash update-repos.sh ~/github
```

## Logs

```
~/.logs/auto-update-repos.log
```
