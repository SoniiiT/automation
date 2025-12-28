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

### ⚠️ Wichtiger Hinweis: Filter verwenden!
Die Playbooks sind standardmäßig auf `hosts: all` konfiguriert, um in Semaphore flexibel eingesetzt werden zu können.
**Bei lokaler Ausführung musst du zwingend `--limit` verwenden**, um nicht versehentlich alle Server anzusprechen!

**Beispiel: Nur auf Docker-Servern ausführen**
```bash
ansible-playbook -i inventory/inventory.yaml playbooks/docker/install-docker.yaml --limit docker_servers
```

**Beispiel: Nur auf einem spezifischen Host ausführen**
```bash
ansible-playbook -i inventory/inventory.yaml playbooks/system/update-upgrade.yaml --limit pve-srv-01
```

**How to install Ansible**
```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt install -y ansible
```