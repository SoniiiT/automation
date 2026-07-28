# Business and operational rules

These are repository-documented rules, not inferred domain requirements.

## Ansible targeting

- Local playbook runs must use `--limit`; many playbooks intentionally target `all` for Semaphore flexibility.
- LXC and Proxmox groups use `root` without privilege escalation; VM and physical groups use the `soniiit` user with escalation.
- Multi-OS playbooks should branch by `ansible_os_family` rather than assuming one package manager.

**Evidence:** `ansible/README.md`, `ansible/inventory/inventory.yaml`.

## Secret handling

- Kestra flows obtain SSH keys, Terraform credentials, and notification credentials through Kestra secret references.
- Secret values must not be committed to workflow YAML or copied into context files.

**Evidence:** `workflows/kestra/ansible/workflows/K3s-Install.yaml`, `workflows/kestra/terraform/workflows/*.yml`.
