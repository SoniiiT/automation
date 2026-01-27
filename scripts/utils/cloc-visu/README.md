# CLOC Visualizer

Ein Python-Tool zur Visualisierung von CLOC (Count Lines of Code) Statistiken mit Streamlit.

## Installation

1. Erstellen Sie eine virtuelle Umgebung (optional aber empfohlen):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. Installieren Sie die Abhängigkeiten:
   ```bash
   pip install -r requirements.txt
   ```

## Starten

Führen Sie den folgenden Befehl im Terminal aus:

```bash
streamlit run cloc_visualizer.py
```

Das Tool öffnet sich automatisch in Ihrem Standard-Webbrowser.

## Funktionen

- **Daten Import**: Laden Sie eine CSV-Datei hoch oder fügen Sie Text direkt ein.
- **Sprachauswahl**: Filtern Sie die angezeigten Sprachen.
- **Diagramme**: Wählen Sie zwischen Balken-, Kreis- und Donut-Diagrammen.
- **Summe**: Positionieren Sie die Gesamtsumme frei auf dem Diagramm.
- **Export**: Laden Sie das fertige Diagramm als PNG herunter.
