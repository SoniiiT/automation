# Architecture

## Components and flows

```text
Inventory -> Ansible playbooks -> target hosts
                    ^
                    |
Kestra schedules/webhooks -> WorkingDirectory/LocalFiles -> AnsibleCLI in Docker

Kestra Terraform flows -> clone external homelab repo -> Terraform plan/apply

Standalone scripts -> local OS, GUI, browser, or external service
```

### Ansible control plane

`ansible/inventory/inventory.yaml` defines infrastructure and functional groups, including Proxmox, LXC, VM, Docker, application, GitHub runner, NAS, and physical hosts. Playbooks are grouped under `docker/`, `kubernetes/`, and `system/`. They commonly target inventory groups, use privilege escalation, and branch on `ansible_os_family` or package-manager facts.

The active Kubernetes path is K3s managed by Ansible. The K3s playbooks install server and agent nodes, configure Kube-VIP, retrieve a node token, and copy kubeconfig. The inventory contains the K3s group structure as commented configuration, so the live inventory and playbook assumptions must be reconciled before running that path.

### Kestra orchestration

Kestra Ansible flows stage inventory/playbook files and an SSH key from a Kestra secret, then run `cytopia/ansible:latest-tools` through the Docker task runner. Some flows are scheduled; others are manual or webhook-driven. The webhook flow `discord_alert_ansible` listens for failed or warning executions in the `ansible` namespace and sends a Discord execution notification.

Terraform flows clone `SoniiiT/homelab` at `main`, write provider credentials from Kestra secrets, run `terraform init`, then `plan` and `apply -auto-approve`. They cover DNS, Proxmox, and Twingate paths and emit plan/apply output files.

### Archived Kubernetes path

`kubernetes/Multi Master Cluster/` contains manual Ubuntu 20.04, 22.04, and 24.04 bootstrap scripts. Its README explicitly marks the path deprecated because infrastructure moved to K3s and Ansible. Do not extend this path for new automation without an explicit decision.

### Standalone tools

`scripts/` has no shared runtime or package manifest. Utilities are isolated by directory and use local requirements files where needed:

- Python GUI/CLI tools for SNMP XML exploration, CSV-to-Excel conversion, CLOC visualization, Minecraft server modpack creation, system cleanup, and anti-AFK input.
- Selenium/PyAutoGUI browser automation for Autotask.
- PowerShell and shell maintenance/setup scripts, including cross-platform repository updates.

## External boundaries

Observed integrations include SSH, Ansible, Docker, K3s, Kube-VIP, Terraform, Proxmox, Twingate, DNS/Tsig, Discord, Pushover, GitHub, CurseForge, Selenium/Chrome, Tkinter/CustomTkinter, Streamlit, and local OS package/service managers. Values for credentials and secret-backed configuration are not part of this context.
