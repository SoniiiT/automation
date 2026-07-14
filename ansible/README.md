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

---

## 📋 Playbook-Konventionen

### 🖥️ Multi-OS Unterstützung
Alle Playbooks müssen mit den folgenden Betriebssystemen kompatibel sein.
Verwende `ansible_os_family` für OS-spezifische Tasks:

| `ansible_os_family` | Distros                        | Package Manager | `become` nötig? |
|---------------------|--------------------------------|-----------------|-----------------|
| `Debian`            | Ubuntu, Debian                 | `apt`           | Ja (sudo)       |
| `RedHat`            | RHEL, CentOS, Fedora           | `dnf` / `yum`   | Ja (sudo)       |
| `Archlinux`         | Arch Linux                     | `pacman`        | Ja (sudo)       |
| `Alpine`            | Alpine Linux                   | `apk`           | Selten          |
| `Suse`              | openSUSE, SLES                 | `zypper`        | Ja (sudo)       |

> **Wichtig:** Debian-basierte LXC-Container laufen oft als `root` **ohne** `sudo`.
> Diese Gruppen haben in der Inventory `ansible_become: false` gesetzt.
> Playbooks müssen daher auf Task-Ebene mit `when: ansible_os_family == "..."` arbeiten
> statt auf einen generischen `package:`-Task zu setzen.

### 🔐 Privilege Escalation Regeln
- **`lxc_hosts`** → `ansible_user: root`, `ansible_become: false` (kein sudo vorhanden)
- **`hypervisors/proxmox`** → `ansible_user: root`, `ansible_become: false`
- **`vm_hosts`** → `ansible_user: soniiit`, `become: true` (sudo vorhanden)
- **`physical_hosts`** → `ansible_user: soniiit`, `become: true` (sudo vorhanden)