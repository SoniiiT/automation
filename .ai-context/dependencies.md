# Dependencies

## Infrastructure and orchestration

| Dependency | Evidence | Role |
| --- | --- | --- |
| Ansible | `ansible/README.md`, `ansible/playbooks/` | Host configuration and provisioning |
| SSH/private key access | `ansible/README.md`, Kestra flows | Remote execution; Kestra uses a secret-backed key |
| Kestra | `workflows/kestra/` | Scheduled, manual, and webhook orchestration |
| Docker | Ansible Docker playbooks, Kestra task runners, PowerShell builder | Container runtime and image workflows |
| K3s/Kube-VIP/Longhorn | Kubernetes Ansible playbooks | Active lightweight Kubernetes path |
| Terraform CLI and Terraform Cloud token | Kestra Terraform flows | External homelab infrastructure provisioning |

## Python environments

Dependencies are intentionally per-tool rather than centralized:

- `scripts/gaming/minecraft-modpack/requirements.txt`: `requests`, `zipfile38`.
- `scripts/utils/anti-afk/requirements.txt`: `pynput`.
- `scripts/utils/cloc-visu/requirements.txt`: Streamlit, pandas, matplotlib, seaborn.
- `scripts/utils/converters/csv-to-excel/requirements.txt`: pandas, openpyxl, CustomTkinter, XlsxWriter, chardet.
- `scripts/utils/scrapers/documentation-scaper/requirements.txt`: requests, BeautifulSoup, lxml, markdownify; Selenium and Playwright are optional.
- `scripts/utils/web-automation/autotask/requirements.txt`: Selenium, python-dotenv, webdriver-manager, PyAutoGUI.

Other Python files use only the standard library or have no local manifest; verify imports before packaging or execution.

## Platform dependencies

The repository assumes target-specific tools such as `apt`, `dnf/yum`, `pacman`, `apk`, `zypper`, systemd, Docker CLI, Chrome/WebDriver, Java, Streamlit, and Windows PowerShell/Appx/DISM depending on the selected script. There is no single supported runtime matrix.
