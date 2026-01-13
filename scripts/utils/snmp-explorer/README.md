# SNMP OID Explorer

Dieses Tool ist ein Python-Skript mit einer grafischen Benutzeroberfläche (GUI), das entwickelt wurde, um SNMP-OIDs aus Zabbix XML-Exportdateien zu extrahieren, zu durchsuchen und zu verarbeiten.

## Funktionen

*   **XML Import**: Laden von Zabbix Exportdateien (`.xml`).
*   **Automatische Extraktion**: Findet automatisch Items und Item Prototypes mit `snmp_oid` Einträgen.
*   **Suche**: Echtzeit-Filterung nach Name, OID, Key oder Beschreibung.
*   **Ansicht**: Tabellarische Darstellung der OID-Informationen.
*   **Kopieren**: Rechtsklick-Kontextmenü zum Kopieren von OIDs oder vollständigen Details in die Zwischenablage.

## Voraussetzungen

*   Python 3.x installiert.
*   `tkinter` muss verfügbar sein (ist standardmäßig in den meisten Python-Installationen für Windows enthalten).

## Verwendung

1.  Starten Sie das Skript:
    ```bash
    python main.py
    ```
2.  Klicken Sie auf **"Load Zabbix XML"**.
3.  Wählen Sie eine Zabbix Export-XML-Datei aus (z.B. `FS Switch N8560 Series SNMP.xml`).
4.  Geben Sie Suchbegriffe in das Feld **"Search"** ein, um die Liste zu filtern.
5.  Rechtsklick auf eine Zeile, um die OID zu kopieren.
