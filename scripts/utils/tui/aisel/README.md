# AISel 🎯

Eine elegante Terminal User Interface (TUI) Anwendung, die als zentraler Launcher für alle AI CLI-Tools dient. Statt verschiedene Befehle wie `gemini`, `cursor-agent` oder `claude` einzutippen, startest du einfach `aisel` und wählst aus einem interaktiven Menü aus.

**Version:** 1.1.2

## Features ✨

- 🎨 **Schönes TUI-Menü**: Elegantes, farbiges Terminal-Interface
- 🔍 **Automatische Erkennung**: Zeigt an, welche AI CLIs installiert sind
- 💾 **Memory**: Merkt sich die zuletzt verwendete Auswahl
- ➕ **Dynamische Konfiguration**: Einträge hinzufügen, entfernen und bearbeiten direkt im Menü
- 🚀 **Argument-Weiterleitung**: Argumente an die gewählte AI CLI weiterreichen
- 🧪 **Dry-Run Modus**: Befehle testen ohne Ausführung
- ⌨️ **Viele Tastenkürzel**: Schnelle Navigation und Auswahl

## Installation 🚀

### 1. Skript kopieren

```bash
# Skript nach ~/.local/bin/ kopieren
cp tools/tui/aisel/aisel.sh ~/.local/bin/aisel
```

### 2. Ausführungsrechte setzen

```bash
chmod +x ~/.local/bin/aisel
```

### 3. PATH hinterlegen

Füge `~/.local/bin` zu deinem PATH hinzu, falls noch nicht vorhanden:

**Für Bash:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Für Zsh:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Für Fish:**
```fish
echo 'set -gx PATH $HOME/.local/bin $PATH' >> ~/.config/fish/config.fish
source ~/.config/fish/config.fish
```

### 4. Verifizierung

```bash
aisel --version
```

## Verwendung 📖

### Grundlegende Verwendung

```bash
# Menü starten
aisel
```

### Mit Argumenten

```bash
# Argumente an die gewählte AI CLI weiterreichen
aisel -- --help
aisel -- --version
aisel -- "Was ist Python?"
```

### Dry-Run Modus

```bash
# Zeigt den Befehl an, ohne ihn auszuführen
aisel --dry-run
```

### Konfiguration zurücksetzen

```bash
# Setzt die Konfiguration auf Standardwerte zurück
aisel --reset
```

### Hilfe anzeigen

```bash
aisel --help
# oder
aisel -h
```

## Tastenkürzel ⌨️

### Navigation

| Taste | Aktion |
|-------|--------|
| `↑` / `↓` | Nach oben/unten navigieren |
| `j` / `k` | Nach unten/oben (Vim-Style) |
| `Tab` / `Shift+Tab` | Nächster/Vorheriger Eintrag |
| `Ctrl+N` / `Ctrl+P` | Nächster/Vorheriger Eintrag |

### Aktionen

| Taste | Aktion |
|-------|--------|
| `Enter` | Gewählten Eintrag ausführen |
| `1-9` | Direkt Eintrag 1-9 auswählen und ausführen |
| `q` / `ESC` | Beenden |

### Konfiguration

| Taste | Aktion |
|-------|--------|
| `+` | Neuen Eintrag hinzufügen |
| `-` | Gewählten Eintrag entfernen |
| `e` | Konfigurationsdatei im Editor öffnen |

## Konfiguration ⚙️

Die Konfigurationsdatei befindet sich unter:
```
~/.config/aisel/aisel.conf
```

### Format

Jede Zeile folgt dem Format:
```
Name|Beschreibung|Befehl
```

### Standard-Konfiguration

Bei der ersten Ausführung wird eine Standard-Konfiguration erstellt:

```
Copilot|GitHub Copilot CLI|copilot
Gemini|Google Gemini 3|gemini
Claude|Anthropic Claude|claude
Cursor|Cursor Agent|cursor-agent
```

### Konfiguration bearbeiten

**Option 1: Im Menü**
- Drücke `e` im Menü, um die Konfigurationsdatei im Editor zu öffnen
- Der Editor wird durch die `$EDITOR` Umgebungsvariable bestimmt (Standard: `nano`)

**Option 2: Manuell**
```bash
nano ~/.config/aisel/aisel.conf
# oder
vim ~/.config/aisel/aisel.conf
```

**Option 3: Im Menü hinzufügen**
- Drücke `+` im Menü
- Folge den Anweisungen

### Beispiel-Konfiguration

```
Copilot|GitHub Copilot CLI|copilot
Gemini|Google Gemini 3|gemini
Claude|Anthropic Claude|claude
Cursor|Cursor Agent|cursor-agent
Ollama|Ollama Local AI|ollama
ChatGPT|OpenAI ChatGPT|chatgpt-cli
```

## State/Memory 💾

AISel speichert die zuletzt gewählte Auswahl in:
```
~/.config/aisel/state
```

Beim nächsten Start wird automatisch der zuletzt verwendete Eintrag ausgewählt.

## Beispiele 💡

### Einfache Verwendung

```bash
# Startet das Menü
aisel

# Wähle mit Pfeiltasten oder j/k
# Drücke Enter zum Ausführen
```

### Mit Argumenten

```bash
# Startet Gemini mit einem Prompt
aisel -- "Erkläre mir Docker"

# Startet Claude mit --help
aisel -- --help
```

### Schnellauswahl

```bash
# Drücke direkt 1-9 im Menü für schnelle Auswahl
# (ohne Enter zu drücken)
```

### Konfiguration erweitern

```bash
# Im Menü:
# 1. Drücke '+'
# 2. Gib Name ein: "Ollama"
# 3. Gib Befehl ein: "ollama"
# 4. Gib Beschreibung ein: "Local AI Model"
```

## Kompatibilität 🖥️

- ✅ **Linux**: Vollständig getestet
- ⚠️ **macOS**: Sollte funktionieren (nicht getestet)
- ✅ **Windows WSL**: Funktioniert unter Windows Subsystem for Linux
- ❌ **Windows PowerShell**: Nicht unterstützt (benötigt Bash)

## Troubleshooting 🔧

### "aisel: command not found"

Stelle sicher, dass `~/.local/bin` in deinem PATH ist:
```bash
echo $PATH | grep -q "$HOME/.local/bin" || echo "PATH nicht gesetzt!"
```

### "Fehler: 'xyz' ist nicht installiert"

Die AI CLI ist nicht im PATH verfügbar. Installiere sie zuerst oder passe den Befehl in der Konfiguration an.

### Editor öffnet sich nicht

Setze die `EDITOR` Umgebungsvariable:
```bash
export EDITOR=nano  # oder vim, code, etc.
```

### Menü wird nicht richtig angezeigt

Stelle sicher, dass dein Terminal ANSI-Farben unterstützt. Die meisten modernen Terminals unterstützen dies standardmäßig.

## Dateien 📁

```
~/.config/aisel/
├── aisel.conf    # Konfigurationsdatei
└── state         # Zuletzt gewählter Eintrag
```

## Lizenz 📜

MIT License - Verwende es frei für persönliche und kommerzielle Projekte.

## Credits 👏

Made by SoniiiT

---

**Tipp:** Erstelle ein Alias für noch schnellere Nutzung:
```bash
alias ai='aisel'
```

