# Automation & Routines

Dieses Repository dient als zentrale Sammelstelle ("Monorepo") für meine gesamte IT-Automatisierung, Infrastruktur-Konfiguration und Skripte.

## 📂 Struktur

### 🤖 [Ansible](./ansible)
Konfigurationsmanagement und Provisionierung.
- **Inventory**: Host-Definitionen.
- **Playbooks**: Automatisierte Abläufe für Server-Setup.
- **Roles**: Wiederverwendbare Aufgaben-Pakete.

### 🔄 [Workflows](./workflows)
Orchestrierung und komplexe Abläufe.
- **[Kestra](./workflows/kestra)**: YAML-basierte Flows für System-Orchestrierung.
- **[N8N](./workflows/n8n)**: Exportierte JSON-Workflows für Web-Automatisierung und Integrationen.

### ☸️ [Kubernetes](./kubernetes)
Cluster-Setup und Manifeste.
- **Clusters**: Setup-Skripte für Multi-Master Cluster (Ubuntu).
- **Manifests**: Kubernetes YAML Ressourcen.

### 📜 [Scripts](./scripts)
Sammlung von Standalone-Skripten und Tools.

#### 🛠️ [Maintenance](./scripts/maintenance)
Wartung und Hintergrund-Tasks.
- **System Cleanup**: Bereinigungsskripte.
- **Anti-AFK**: Automatisierungstools.
- **Voice Assistant**: Sprachsteuerung.

#### 🎮 [Gaming](./scripts/gaming)
Skripte rund um Gaming-Server.
- **Minecraft**: Modpack-Erstellung und Server-Management.

#### 💻 [Setup](./scripts/setup)
Initiale Einrichtung von Arbeitsumgebungen.
- **Windows**: Autopilot, Debloat-Skripte.
- **Linux**: Dotfiles-Setup, Basis-Konfiguration.
- **macOS**: Einrichtungsskripte.

#### 🔧 [Utils](./scripts/utils)
Hilfsprogramme und Konverter.
- **Converters**: CSV zu Excel etc.
- **Scrapers**: Dokumentations-Scraper.
- **TUI**: Terminal Interfaces (z.B. Aisel).

---
*Generiert für das konsolidierte Automation-Repository.*