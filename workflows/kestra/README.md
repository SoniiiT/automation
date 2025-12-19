# Kestra Workflows

Dieses Verzeichnis dient der Speicherung und Versionierung von Kestra Orchestrierungs-Flows. Die Flows werden hier als YAML-Dateien abgelegt.

## 📂 Struktur

Die geplante Struktur für dieses Verzeichnis:

- **flows/**: Enthält die YAML-Definitionen der Flows (ggf. nach Namespaces organisiert).
- **scripts/**: (Optional) Externe Skripte (Python, Shell, Node), die von den Flows referenziert oder ausgeführt werden.

## 🚀 Nutzung & Deployment

Kestra Flows werden deklarativ in YAML definiert.

### Import über die UI
1. Öffne die Kestra Web-Oberfläche.
2. Gehe zu **Flows** -> **Create**.
3. Kopiere den Inhalt der entsprechenden `.yaml` Datei aus diesem Repository in den Editor.
4. Klicke auf **Save**.

### Import über CLI (Optional)
Falls die Kestra CLI verwendet wird, können Flows direkt angewendet werden:

```bash
kestra flow create flows/mein-flow.yaml