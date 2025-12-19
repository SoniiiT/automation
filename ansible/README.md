# Ansible Automation

Dieses Verzeichnis enthält Ansible Playbooks und Inventar-Dateien zur Automatisierung der Infrastruktur-Verwaltung. Die Skripte decken Bereiche wie Docker, Kubernetes (K3s) Cluster-Setup und allgemeine Systemwartung ab.

## 📂 Struktur

- **inventory/**: Enthält die Host-Definitionen für verschiedene Umgebungen.
- **playbooks/**: Enthält die eigentlichen Automatisierungs-Skripte, unterteilt in Kategorien.
- **roles/**: (Optional) Enthält wiederverwendbare Ansible-Rollen.

## 🛠️ Playbooks

### 🐳 Docker (`playbooks/docker/`)

### ☸️ Kubernetes (`playbooks/kubernetes/`)

### 🖥️ System (`playbooks/system/`)

## 🚀 Nutzung

Stelle sicher, dass Ansible installiert ist und du Zugriff auf die privaten SSH-Schlüssel hast (standardmäßig wird nach `id_rsa` gesucht).

**Beispiel: System Updates ausführen**
```bash
ansible-playbook -i inventory/inventory.yaml playbooks/system/update-upgrade.yaml