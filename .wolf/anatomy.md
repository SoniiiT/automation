# anatomy.md

> Auto-maintained by OpenWolf. Last scanned: 2026-09-21T16:32:35.375Z
> Files: 145 tracked | Anatomy hits: 0 | Misses: 0

> Project structure index. Auto-maintained by OpenWolf hooks and daemon.
> Run `openwolf scan` to generate, or wait for the first Claude Code session.
> Status: Pending initial scan

## ./

- `.gitattributes` — Git attributes (~8 tok)
- `.gitignore` — Git ignore rules (~70 tok)
- `AGENTS.md` — Agent instructions (~242 tok)
- `CLAUDE.md` — OpenWolf (~179 tok)
- `README.md` — Project documentation (~420 tok)

## .ai-context/

- `architecture.md` — Architecture (~717 tok)
- `conventions.md` — Conventions (~586 tok)
- `dependencies.md` — Dependencies (~458 tok)
- `manifest.json` (~530 tok)
- `project-map.md` — Project map (~473 tok)

## .ai-context/indexes/

- `files.json` (~2020 tok)
- `symbols.json` (~733 tok)

## .ai-context/knowledge/

- `README.md` — Project documentation (~151 tok)

## .ai-context/knowledge/business-rules/

- `index.md` — Business and operational rules (~221 tok)

## .ai-context/knowledge/decisions/

- `index.md` — Decisions (~149 tok)

## .ai-context/knowledge/feature-guides/

- `automation.md` — Automation feature guide (~320 tok)
- `standalone-tools.md` — Standalone tools guide (~147 tok)

## .ai-context/knowledge/removal-guides/

- `automation.md` — Removal guidance (~342 tok)

## .ai-context/knowledge/risks/

- `index.md` — Risks and uncertainties (~319 tok)

## .github/

- `copilot-instructions.md` — Copilot instructions (~109 tok)

## ansible/

- `README.md` — Project documentation (~775 tok)

## ansible/inventory/

- `inventory.yaml` (~1125 tok)

## ansible/playbooks/docker/

- `configure-log-rotation.yaml` (~151 tok)
- `docker-cleanup.yaml` (~63 tok)
- `install-docker.yaml` (~1179 tok)
- `install-portainer.yaml` (~463 tok)
- `mount-docker-disk.yaml` (~347 tok)
- `setup-cleanup-cron.yaml` (~156 tok)

## ansible/playbooks/kubernetes/

- `install-agent.yaml` (~250 tok)
- `install-kubernetes.yaml` (~1166 tok)
- `install-server.yaml` (~402 tok)
- `longhorn-fix-known-issues.yaml` (~330 tok)
- `uninstall-kubernetes.yaml` (~102 tok)

## ansible/playbooks/system/

- `check-disk-space.yaml` (~133 tok)
- `extend-disk.yaml` (~225 tok)
- `hello-world.yaml` (~72 tok)
- `mount-disk.yaml` (~281 tok)
- `reboot-required.yaml` (~111 tok)
- `reboot-systems.yaml` (~47 tok)
- `semaphore-test.yaml` (~576 tok)
- `update-upgrade.yaml` (~1518 tok)

## ansible/playbooks/system/install/

- `install-cockpit-navigator.yaml` (~192 tok)
- `install-cockpit.yaml` (~730 tok)
- `install-doppler.yaml` (~1290 tok)
- `install-teleport.yaml` (~0 tok)

## ansible/playbooks/system/uninstall/

- `uninstall-teleport.yaml` (~291 tok)

## kubernetes/

- `README.md` — Project documentation (~357 tok)

## kubernetes/Multi Master Cluster/Setup_Script_Ubuntu-20-04/

- `install_Loadbalancer.sh` — Works Only on Ubuntu 20.04 (~1376 tok)
- `install_MasterWorker.sh` — Works Only on Ubuntu 20.04 (~392 tok)

## kubernetes/Multi Master Cluster/Setup_Script_Ubuntu-22-04/

- `install_Loadbalancer.sh` — Works Only on Ubuntu 22.04 (~1376 tok)
- `install_MasterWorker.sh` — Works Only on Ubuntu 22.04 (~392 tok)

## kubernetes/Multi Master Cluster/Setup_Script_Ubuntu-24-04/

- `install_Loadbalancer.sh` — Works Only on Ubuntu 24.04 (~1364 tok)
- `install_MasterWorker.sh` — Works Only on Ubuntu 24.04 (~318 tok)

## scripts/

- `README.md` — Project documentation (~340 tok)

## scripts/gaming/minecraft-modpack/

- `create-server-modpack.py` — download_file, extract_zip, detect_loader, download_server_jar + 5 more (~2318 tok)
- `requirements.txt` — Python dependencies (~9 tok)

## scripts/maintenance/auto-update-repos/

- `install-linux.sh` — install-linux.sh — Installs update-repos.sh as a systemd user service (~401 tok)
- `install-macos.sh` — install-macos.sh — Installs update-repos.sh as a launchd agent (~525 tok)
- `install-windows.ps1` — Requires -RunAsAdministrator (~728 tok)
- `README.md` — Project documentation (~900 tok)
- `update-repos.ps1` — Requires -Version 5.1 (~2522 tok)
- `update-repos.sh` — update-repos.sh — Safely fast-forwards or forcibly synchronizes Git repositories. (~2187 tok)

## scripts/maintenance/opencode-venice-sync/

- `README.md` — Project documentation (~379 tok)
- `sync-venice-models.py` — strip_jsonc_comments, load_config, save_config, fetch_live_models + 1 more (~935 tok)

## scripts/maintenance/system-cleanup/

- `start_cleanup.py` — get_disk_usage, cleanup_system, main (~539 tok)

## scripts/setup/huggingface-downloader/

- `README.md` — Project documentation (~935 tok)

## scripts/setup/huggingface-downloader/linux/

- `install.sh` — Installiert HuggingFaceModelDownloader (hfdownloader) auf Linux inkl. (~1519 tok)

## scripts/setup/huggingface-downloader/macos/

- `install.sh` — Installiert HuggingFaceModelDownloader (hfdownloader) auf macOS inkl. (~1490 tok)

## scripts/setup/huggingface-downloader/windows/

- `install.ps1` — Requires -Version 5.1 (~2161 tok)

## scripts/setup/linux/

- `empty.md` (~0 tok)

## scripts/setup/macos/

- `bootstrap.sh` — Bootstrap-Skript für ein neues Arbeits-MacBook. (~4398 tok)
- `Brewfile` — Brewfile für das MacBook-Arbeitsplatz-Setup. (~926 tok)
- `README.md` — Project documentation (~1599 tok)

## scripts/setup/windows/

- `README.md` — Project documentation (~141 tok)

## scripts/setup/windows/powershell/autopilot/

- `autopilot_general_gaming.ps1` — Check if PowerShell is running with elevated privileges (~757 tok)
- `autopilot_itcares.ps1` — Debloat Windows (~2530 tok)
- `autopilot_sweniii11.ps1` — Install Chocolatey (if not already installed) (~304 tok)

## scripts/setup/windows/powershell/docker/

- `build-local-docker-image.ps1` (~1219 tok)

## scripts/setup/windows/powershell/system/

- `debloat-windows.ps1` — Declares Remove (~6071 tok)

## scripts/utils/anti-afk/

- `antiafk.py` — Keyboard Controller erstellen (~278 tok)
- `requirements.txt` — Python dependencies (~4 tok)

## scripts/utils/cloc-visu/

- `cloc_visualizer.py` — parse_data, get_col_index, make_autopct, my_autopct (~3978 tok)
- `README.md` — Project documentation (~238 tok)
- `requirements.txt` — Python dependencies (~9 tok)

## scripts/utils/converters/csv-to-excel/

- `csv_to_excel_converter.py` — GUI Imports (~4292 tok)
- `README.md` — Project documentation (~1019 tok)
- `requirements.txt` — Python dependencies (~49 tok)

## scripts/utils/morning-briefing/

- `config.example.yaml` — Konfiguration des Morgenbriefings. (~328 tok)
- `install-windows.ps1` — Requires -Version 5.1 (~562 tok)
- `main.py` — Morgenbriefing aus Outlook, Teams und Autotask. (~1304 tok)
- `README.md` — Project documentation (~1527 tok)
- `requirements.txt` — Python dependencies (~8 tok)

## scripts/utils/morning-briefing/briefing/

- `__init__.py` — Morning Briefing - Paketinitialisierung. (~28 tok)
- `config.py` — Konfiguration des Morgenbriefings. (~867 tok)
- `demo.py` — Beispieldaten für einen Offline-Lauf ohne Browser und ohne echte Konten. (~1200 tok)
- `models.py` — Datenmodelle für das Morgenbriefing. (~864 tok)
- `normalize.py` — Normalisierung: HTML entfernen, Signaturen kürzen, Duplikate zusammenführen. (~1560 tok)
- `pipeline.py` — Ablauf: sammeln, bereinigen, anonymisieren, zusammenfassen, planen. (~1102 tok)
- `plan.py` — Regelbasierte Priorisierung und Tagesplanung. (~2681 tok)
- `privacy.py` — Lokale Datenschutzschicht. (~2677 tok)
- `render.py` — Ausgabe des Briefings als Terminaltext und als lokale HTML-Datei. (~1807 tok)
- `summarize.py` — Anbindung der Claude CLI. (~1762 tok)

## scripts/utils/morning-briefing/briefing/collectors/

- `__init__.py` — Collectors für die einzelnen Quellen. (~116 tok)
- `autotask.py` — Collector für Kaseya Autotask (Weboberfläche, ausschließlich lesend). (~884 tok)
- `browser.py` — Browsersitzung mit persistentem Profil. (~952 tok)
- `microsoft.py` — Collectors für Outlook Web, Outlook-Kalender und Teams Web. (~2140 tok)

## scripts/utils/morning-briefing/tests/

- `test_pipeline.py` — Tests für Deduplizierung, Priorisierung und den vollständigen Ablauf. (~1410 tok)
- `test_privacy.py` — Tests der Datenschutzschicht. (~982 tok)

## scripts/utils/scrapers/documentation-scaper/

- `main.py` — class: convert_pre, convert_code, convert_table, md + 3 more (~8002 tok)
- `README.md` — Project documentation (~1396 tok)
- `requirements.txt` — Python dependencies (~94 tok)

## scripts/utils/snmp-explorer/

- `main.py` — SNMPExplorerApp: setup_ui, load_xml, extract_item, update_tree + 4 more (~1782 tok)
- `README.md` — Project documentation (~292 tok)

## scripts/utils/tui/aisel/

- `aisel.sh` — AISel: Hübsches Inline-Menü für AI CLIs (~3049 tok)
- `README.md` — Project documentation (~1403 tok)

## scripts/utils/web-automation/autotask/

- `befehle.txt` — 1. System updaten und Python + pip installieren (~117 tok)
- `requirements.txt` — Python dependencies (~21 tok)
- `Start_Autotask.py` — wait, normalize_browser_viewport, ensure_autotask_window_state, stabilize_presentation_mode + 3 more (~7488 tok)

## workflows/kestra/

- `README.md` — Project documentation (~221 tok)

## workflows/kestra/ansible/playbooks/

- `check-disk-space.yaml` (~230 tok)
- `docker-clean-up.yaml` (~156 tok)
- `install-kubernetes.yaml` (~1168 tok)
- `inventory-k3s.yaml` (~442 tok)
- `inventory.yaml` (~1088 tok)
- `k3s-add-disk.yaml` (~708 tok)
- `k3s-extend-disk.yaml` (~552 tok)
- `longhorn-fix-known-issues.yaml` (~210 tok)
- `reboot-required-linux.yaml` (~210 tok)
- `uninstall-kubernetes.yaml` (~105 tok)
- `update-linux.yaml` (~107 tok)

## workflows/kestra/ansible/workflows/

- `Check-Disk-Space.yaml` (~248 tok)
- `Docker-Clean-Up.yaml` (~230 tok)
- `example.yaml` (~0 tok)
- `K3s-Add-Disk.yaml` (~229 tok)
- `K3s-Extend-Disk.yaml` (~232 tok)
- `K3s-Install.yaml` (~234 tok)
- `K3s-Longhorn-Fix-Known-Issues.yaml` (~245 tok)
- `K3s-Uninstall.yaml` (~236 tok)
- `Reboot-Required-Linux.yaml` (~270 tok)
- `Update-Linux.yaml` (~246 tok)

## workflows/kestra/terraform/workflows/

- `Terraform-DNS.yml` (~345 tok)
- `Terraform-PVE-SRV-01.yml` (~387 tok)
- `Terraform-Twingate.yml` (~350 tok)

## workflows/kestra/webhook/workflows/

- `discord_alert_ansible.yml` (~232 tok)

## workflows/n8n/

- `README.md` — Project documentation (~555 tok)
