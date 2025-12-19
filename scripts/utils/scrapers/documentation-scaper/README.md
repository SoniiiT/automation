# Documentation Scraper 📚

Ein leistungsstarker, rekursiver Web-Scraper für Dokumentationsseiten, der HTML in sauberes Markdown konvertiert - perfekt für die Verwendung mit KI-Modellen.

## Features ✨

- **Rekursives Scraping**: Navigiert automatisch durch Menüs und Unterseiten
- **Intelligente Inhaltsextraktion**: Entfernt Navigation, Header, Footer, Werbung und Cookie-Banner
- **Plattform-optimiert**: Spezielle Unterstützung für viele Dokumentationsplattformen
- **Markdown-Ausgabe**: Konvertiert HTML in sauberes, LLM-freundliches Markdown
- **Flexible Ausgabe**: Einzelne Datei oder separate Dateien pro Seite
- **Rate Limiting**: Einstellbare Verzögerung zwischen Requests
- **Pattern Matching**: Include/Exclude-Patterns für gezielte Filterung

## Unterstützte Plattformen 🌐

- Docker Docs
- Broadcom TechDocs  
- IT Glue (Kaseya)
- n8n Docs
- ReadTheDocs
- GitBook
- MkDocs
- Docusaurus
- VuePress
- Sphinx
- Confluence
- Notion
- Generische Dokumentationsseiten

## Installation 🚀

```bash
# Repository klonen
cd documentation-scraper

# Virtuelle Umgebung erstellen (empfohlen)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
.\venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt
```

## Verwendung 📖

### Grundlegende Verwendung

```bash
# Einfaches Scraping
python main.py https://docs.docker.com/

# Mit Output-Verzeichnis
python main.py https://docs.docker.com/ -o docker_docs

# Mit Tiefenbegrenzung
python main.py https://docs.docker.com/ -o docker_docs --depth 3
```

### Alle Inhalte in einer Datei

```bash
python main.py https://help.itglue.com/ -o itglue --single-file
```

### Mit Pattern-Filterung

```bash
# Nur bestimmte Pfade einschließen
python main.py https://docs.n8n.io/ -o n8n --include "/nodes/" --include "/integrations/"

# Bestimmte Pfade ausschließen
python main.py https://docs.example.com/ -o example --exclude "/api/" --exclude "/changelog/"
```

### Erweiterte Optionen

```bash
python main.py https://docs.docker.com/ \
    -o docker_docs \
    --depth 5 \
    --delay 2.0 \
    --max-pages 1000 \
    --single-file \
    --verbose
```

## Kommandozeilen-Optionen 🛠️

| Option | Kurz | Beschreibung | Standard |
|--------|------|--------------|----------|
| `url` | - | Basis-URL der Dokumentation | (erforderlich) |
| `--output` | `-o` | Output-Verzeichnis | `output` |
| `--depth` | `-d` | Maximale Rekursionstiefe | `5` |
| `--delay` | - | Sekunden zwischen Requests | `1.0` |
| `--max-pages` | - | Maximale Seitenanzahl (0 = unbegrenzt) | `0` |
| `--single-file` | - | Alles in einer Datei speichern | `False` |
| `--include` | - | URL-Pattern einschließen (Regex) | `[]` |
| `--exclude` | - | URL-Pattern ausschließen (Regex) | `[]` |
| `--verbose` | `-v` | Ausführliche Ausgabe | `False` |
| `--quiet` | `-q` | Nur Fehler ausgeben | `False` |

## Output-Struktur 📁

### Multiple Files (Standard)

```
output/
└── docs-docker-com/
    ├── 00_INDEX.md          # Inhaltsverzeichnis
    ├── 0001_index.md        # Startseite
    ├── 0002_get-started.md
    ├── 0003_manuals.md
    └── ...
```

### Single File

```
output/
├── docs-docker-com_20241201_143022.md  # Alle Inhalte
└── docs-docker-com_metadata.json       # Metadaten
```

## Markdown-Qualität 📝

Der Scraper erzeugt sauberes Markdown, das optimal für LLMs geeignet ist:

- **Überschriften**: Hierarchische `#` Struktur
- **Code-Blöcke**: Mit Spracherkennung (```python, ```bash, etc.)
- **Tabellen**: Korrekte Markdown-Tabellen
- **Links**: Relative Links werden aufgelöst
- **Listen**: Einheitliche Formatierung
- **Bereinigung**: Keine mehrfachen Leerzeilen, kein überflüssiger Whitespace

## Beispiel-Output 📄

```markdown
# Docker Desktop Overview

**URL:** https://docs.docker.com/desktop/

---

Docker Desktop is an easy-to-install application for your Mac, Windows, 
or Linux environment that enables you to build and share containerized 
applications and microservices.

## Key features

- **Simple Setup**: One-click installation
- **Kubernetes**: Built-in Kubernetes cluster
- **Extensions**: Extend functionality with Docker Extensions

## Installation

\```bash
# Download from docker.com
# Run the installer
# Start Docker Desktop
\```

...
```

## Workflow für KI-Training 🤖

1. **Scrapen**: Dokumentation mit diesem Tool scrapen
2. **Prüfen**: Output manuell prüfen und ggf. bereinigen
3. **Füttern**: Markdown als Kontext an LLM geben
4. **Instruktionen**: LLM erstellt spezifische Instruktionen basierend auf der Dokumentation

```
URL → Scraper → Markdown → LLM (Architekt) → Instruktionen → Spezialisiertes Modell
```

## Hinweise ⚠️

- **Robots.txt**: Der Scraper respektiert keine robots.txt - verwende ihn verantwortungsvoll
- **Rate Limiting**: Setze angemessene Delays (Standard: 1 Sekunde)
- **JavaScript**: Seiten die JavaScript zum Rendern benötigen funktionieren möglicherweise nicht
- **Authentifizierung**: Keine Unterstützung für Login-geschützte Seiten
- **Große Seiten**: Bei sehr großen Dokumentationen (`--max-pages` anpassen)

## Troubleshooting 🔧

### Keine Inhalte gefunden

- Prüfe ob die Seite JavaScript zum Rendern benötigt
- Versuche einen anderen Content-Selector
- Nutze `--verbose` für mehr Details

### Zu viele Seiten

- Reduziere `--depth`
- Setze `--max-pages`
- Nutze `--include` Pattern

### Rate Limiting

- Erhöhe `--delay`
- Reduziere parallele Anfragen

## Lizenz 📜

MIT License - Verwende es frei für persönliche und kommerzielle Projekte.

## Beitragen 🤝

Pull Requests sind willkommen! Für größere Änderungen bitte zuerst ein Issue öffnen.
