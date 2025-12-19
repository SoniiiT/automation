# 📊 CSV to Excel Converter

Ein leistungsstarker CSV zu Excel Konverter mit moderner GUI und CLI-Unterstützung. Konvertiert CSV-Dateien in professionell formatierte Excel-Tabellen mit anpassbaren Styles und Optionen.

## ✨ Features

### 🎨 Moderne Benutzeroberfläche
- Windows 11-inspiriertes Design
- Intuitive Bedienung mit Drag & Drop
- Live-Fortschrittsanzeige
- Batch-Verarbeitung mehrerer Dateien

### 📁 Vielseitige Verarbeitung
- **Einzeldatei-Konvertierung** - Schnelle Verarbeitung einzelner CSV-Dateien
- **Batch-Modus** - Mehrere Dateien gleichzeitig konvertieren
- **Ordner-Verarbeitung** - Alle CSV-Dateien eines Ordners auf einmal
- **Multi-Encoding Support** - Automatische Erkennung (UTF-8, ISO-8859-1, Windows-1252)

### 💼 Professionelle Excel-Ausgabe
- Formatierte Tabellen mit wählbaren Styles
- Automatische Spaltenbreiten-Anpassung
- Farbige Header mit Firmenlook
- Eingefrorene Kopfzeilen
- Rahmen und Gitterlinien
- Excel-Tabellen-Objekte mit Filter-Funktionen

## 🚀 Schnellstart

### Installation der Abhängigkeiten
```bash
pip install -r requirements.txt
```

### GUI starten
```bash
python csv_to_excel_gui_modern.py
```

### CLI-Verwendung
```bash
# Einzelne Datei konvertieren
python csv_to_excel_gui_modern.py datei.csv

# Mit benutzerdefiniertem Ausgabenamen
python csv_to_excel_gui_modern.py input.csv output.xlsx
```

## 📋 Verwendung

### GUI-Modus
1. Programm starten - Doppelklick auf csv_to_excel_gui_modern.py
2. Dateien auswählen - Klicke auf "📁 CSV Dateien auswählen" oder "📂 Ordner auswählen"
3. Optionen anpassen - Wähle Tabellenstil und Formatierungsoptionen
4. Konvertieren - Klicke auf "🚀 Konvertieren"

### Kommandozeilen-Modus
```bash
# Basis-Konvertierung
python csv_to_excel_gui_modern.py verkaufsdaten.csv

# Mehrere Dateien mit Wildcards (Windows)
for %f in (*.csv) do python csv_to_excel_gui_modern.py "%f"

# Mehrere Dateien mit Wildcards (Linux/Mac)
for file in *.csv; do python csv_to_excel_gui_modern.py "$file"; done
```

## ⚙️ Konfigurationsoptionen

### Verfügbare Tabellenstile
- TableStyleLight1 - Heller Stil mit dezenten Farben
- TableStyleLight2 - Heller Stil mit blauen Akzenten
- TableStyleMedium1 - Mittlerer Stil mit Orange
- TableStyleMedium2 - Mittlerer Stil mit Blau (Standard)
- TableStyleDark1 - Dunkler Stil mit starkem Kontrast
- TableStyleDark2 - Dunkler Stil mit Grau

### Formatierungsoptionen
| Option | Beschreibung | Standard |
|--------|--------------|----------|
| Excel-Tabelle erstellen | Erstellt ein Excel Table-Objekt mit Filtern | ✅ Ein |
| Header fixieren | Erste Zeile beim Scrollen sichtbar halten | ✅ Ein |
| Spaltenbreite anpassen | Automatische Anpassung an Inhalt | ✅ Ein |
| Rahmen hinzufügen | Gitternetzlinien um alle Zellen | ✅ Ein |

## 📊 Beispiele

### Vorher (CSV)
```csv
Kunde,Produkt,Menge,Preis,Datum
Müller GmbH,Laptop,5,899.99,2025-01-15
Schmidt AG,Monitor,10,299.99,2025-01-16
Weber & Co,Maus,50,19.99,2025-01-17
```

### Nachher (Excel)
📘 Professionell formatierte Tabelle
🎨 Farbiger Header (Dunkelblau mit weißer Schrift)
📏 Optimierte Spaltenbreiten
🔍 Aktivierte Filter und Sortierung
📊 Als Excel-Tabelle formatiert

## 🔧 Technische Details
### Systemanforderungen
- Python 3.7 oder höher
- Windows 10/11, macOS, oder Linux
- 50 MB freier Speicherplatz

### Unterstützte Dateiformate
- Eingabe: CSV, TSV (Tab-separiert)
- Ausgabe: XLSX (Excel 2007+)

### Encoding-Unterstützung
- UTF-8 (mit/ohne BOM)
- ISO-8859-1 (Latin-1)
- Windows-1252
- Automatische Erkennung

### Performance
- Kleine Dateien (< 1000 Zeilen): < 1 Sekunde
- Mittlere Dateien (< 10.000 Zeilen): 2-5 Sekunden
- Große Dateien (< 100.000 Zeilen): 10-30 Sekunden

## 💡 Tipps & Tricks
### Große Dateien verarbeiten
Bei sehr großen CSV-Dateien (> 1 Million Zeilen) empfiehlt sich die CLI-Version für bessere Performance.

### Sonderzeichen in Dateinamen
Das Tool bereinigt automatisch problematische Zeichen in Spaltenüberschriften.

### Mehrere Sheets
Jede CSV wird als separates Excel-File gespeichert. Für mehrere Sheets in einer Datei können die Ergebnisse manuell kombiniert werden.