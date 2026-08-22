# HuggingFace Downloader – Installation & Launcher

Plattformübergreifendes Setup für [`bodaay/HuggingFaceModelDownloader`](https://github.com/bodaay/HuggingFaceModelDownloader).
Nach der Installation ist das Tool über die normale Betriebssystem-Suche
(Windows-Suche / Spotlight / GNOME-KDE-Anwendungssuche) unter dem Namen
**„HuggingFace Downloader"** auffindbar. Ein Klick startet die WebUI
**im Hintergrund** (kein Konsolenfenster) und öffnet automatisch den
Standardbrowser.

## Funktionsweise

- Läuft **immer im Flat-File-Modus** (`hfdownloader serve --local-dir <MODELS_ROOT>`),
  **nicht** im HF-Cache-Modus mit Symlinks – dadurch sind keine Admin-Rechte
  oder Windows-Entwicklermodus nötig, und Tools wie LM Studio/Ollama finden
  die `.gguf`-Dateien direkt im gewählten Ordner.
- Standardport `8080`; ist der Port belegt, wird automatisch der nächste
  freie Port gewählt und beim Öffnen des Browsers mitgegeben.
- Läuft bereits eine Instanz (Port-Check + PID-Datei), öffnet ein erneuter
  Klick nur den Browser – es wird **kein** zweiter Serverprozess gestartet.
- Alle Installationsskripte sind **idempotent**: mehrfaches Ausführen
  überschreibt sauber, erzeugt keine Duplikate, lädt die Binary nur bei
  fehlender/veralteter Version erneut herunter.
- Keine Admin-/Root-Rechte erforderlich, kein Autostart beim Systemboot.

## Installation

### Windows

```powershell
cd scripts\setup\huggingface-downloader\windows
powershell -ExecutionPolicy Bypass -File install.ps1
```

Optionale Parameter:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -ModelsRoot D:\Models -Port 9090 -Force -NoDesktopShortcut
```

- Binary: `%LOCALAPPDATA%\HFDownloader\hfdownloader.exe`
- Modelle: `%USERPROFILE%\lmstudio-models` (Standard)
- Startmenü-Verknüpfung: `HuggingFace Downloader.lnk` (zusätzlich Desktop-Verknüpfung,
  außer `-NoDesktopShortcut` wird angegeben)
- Danach einfach über die **Windows-Suche** „HuggingFace Downloader" eingeben und starten.

### macOS

```bash
cd scripts/setup/huggingface-downloader/macos
bash install.sh
```

Optionale Umgebungsvariablen:

```bash
MODELS_ROOT=~/Models PORT=9090 FORCE=1 bash install.sh
```

- Binary: `~/Applications/HFDownloader/hfdownloader`
- Modelle: `~/lmstudio-models` (Standard)
- App-Bundle: `~/Applications/HuggingFace Downloader.app`
- Danach per **Spotlight** (⌘+Leertaste) „HuggingFace Downloader" suchen und starten.

### Linux

```bash
cd scripts/setup/huggingface-downloader/linux
bash install.sh
```

Optionale Umgebungsvariablen:

```bash
MODELS_ROOT=~/Models PORT=9090 FORCE=1 bash install.sh
```

- Binary: `~/.local/share/HFDownloader/hfdownloader` (zusätzlich Symlink unter `~/.local/bin/hfdownloader`)
- Modelle: `~/lmstudio-models` (Standard)
- Anwendungseintrag: `~/.local/share/applications/huggingface-downloader.desktop`
- Danach in der **GNOME/KDE-Anwendungssuche** nach „HuggingFace Downloader" suchen und starten.

## Neuinstallation / Update erzwingen

Alle Skripte akzeptieren ein Force-Flag, um die Binary unabhängig vom
Versionsstand neu herunterzuladen:

- Windows: `-Force`
- macOS/Linux: `FORCE=1`

## Deinstallation

Es gibt keinen automatischen Uninstaller. Zum Entfernen genügt es, die
jeweiligen Installationsordner sowie die Verknüpfung/das App-Bundle/den
.desktop-Eintrag zu löschen:

- **Windows**: `%LOCALAPPDATA%\HFDownloader`, `HuggingFace Downloader.lnk`
  im Startmenü- und Desktop-Ordner.
- **macOS**: `~/Applications/HFDownloader`, `~/Applications/HuggingFace Downloader.app`.
- **Linux**: `~/.local/share/HFDownloader`, `~/.local/bin/hfdownloader`,
  `~/.local/share/applications/huggingface-downloader.desktop`.

Der Modell-Ordner (`MODELS_ROOT`) bleibt davon unberührt und muss bei Bedarf
separat gelöscht werden.
