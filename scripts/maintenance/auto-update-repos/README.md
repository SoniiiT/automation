# Auto-Update Git Repositories

Aktualisiert beim Systemstart / Login Git-Repositories in einem definierten Ordner. Standardmäßig werden lokale Änderungen geschützt; mit `-Force` bzw. `--force` wird der konfigurierte Upstream zur Source of Truth.

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

Die Zusammenfassung unterscheidet aktualisierte, bereits aktuelle, übersprungene und fehlgeschlagene Repositories. Übersprungene Repositories können mit `git status`, `git branch -vv` und `git log --oneline HEAD..@{upstream}` geprüft und anschließend bewusst manuell synchronisiert werden.
