# Kubernetes Scripts (Deprecated)

> **⚠️ STATUS: DEPRECATED**
>
> Dieses Projekt wird nicht mehr aktiv weiterentwickelt. Die Infrastruktur wurde auf **K3s** umgestellt und wird nun vollständig über **Ansible** verwaltet.

Die Skripte in diesem Verzeichnis verbleiben hier ausschließlich zu Archivzwecken und als Referenz für manuelle Kubernetes-Setups ("Kubernetes from Scratch").

## 🛑 Grund für die Archivierung

Der Aufwand für die Wartung und das Setup eines manuell aufgesetzten Kubernetes-Clusters (Vanilla K8s) stand in keinem Verhältnis zum Nutzen. Die neue Lösung basiert auf:
1.  **K3s**: Leichtgewichtiger und einfacher zu warten.
2.  **Ansible**: Vollständige Automatisierung statt manueller Shell-Skripte.

Die aktuellen, aktiven Automatisierungs-Skripte befinden sich im Ordner: [`../ansible/playbooks/kubernetes`](../ansible/playbooks/kubernetes).

## 📂 Inhalt (Archiv)

Dieses Verzeichnis enthält alte Shell-Skripte und Konfigurationen für:

- Manuelles Bootstrapping eines Kubernetes Clusters.
- Zertifikats-Erstellung und Verwaltung.
- etcd Cluster Konfiguration.
- Manuelles Setup von Control Plane und Worker Nodes.

## ⚠️ Nutzungswarnung

**Die Nutzung dieser Skripte wird nicht mehr empfohlen.** 
Sie sind möglicherweise nicht kompatibel mit aktuellen Kubernetes-Versionen, Container-Runtimes oder Betriebssystem-Updates. Es erfolgt kein Support und keine Aktualisierung mehr.

---
*Archived on 2024-06*