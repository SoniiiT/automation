# Project map

## Shape

This is a small infrastructure-automation monorepo rather than an application. It contains Ansible configuration, Kestra orchestration definitions, archived manual Kubernetes bootstrap scripts, and independent local utilities for Windows, Linux, macOS, gaming, data conversion, scraping, and browser automation.

## Top-level navigation

| Path | Purpose | Status |
| --- | --- | --- |
| `ansible/` | Inventory and active infrastructure playbooks for Docker, K3s, and system operations | Active |
| `workflows/kestra/` | Kestra YAML flows that run Ansible, Terraform, and notifications | Active |
| `kubernetes/` | Manual multi-master Kubernetes shell bootstrap scripts | Archived/deprecated |
| `scripts/` | Standalone utilities and setup/maintenance scripts | Mixed; inspect each subdirectory |
| `README.md` | Repository orientation and links | Documentation |

## Entry points

- Ansible: `ansible/inventory/inventory.yaml` plus a playbook under `ansible/playbooks/`.
- Kestra: a flow under `workflows/kestra/**/workflows/`; most Ansible flows stage files and invoke `AnsibleCLI`.
- Terraform orchestration: `workflows/kestra/terraform/workflows/*.yml`; these clone the external `SoniiiT/homelab` repository and run Terraform.
- Standalone tools: each Python, PowerShell, or shell file is generally run directly; local dependencies are declared in the nearest `requirements.txt`.

## Safe navigation

1. Read the target module README before changing it.
2. For Ansible, inspect inventory group membership and privilege variables before selecting hosts.
3. For Kestra, trace staged inputs, secret references, runner image, trigger, and referenced playbook together.
4. Treat `kubernetes/` as historical reference; active K3s automation is in `ansible/playbooks/kubernetes/`.
5. Do not assume a root-level build, test, or package manager exists; none was found.
