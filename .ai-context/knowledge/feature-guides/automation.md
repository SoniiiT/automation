# Automation feature guide

## Ansible and Kestra path

- **Exposed by:** `ansible/playbooks/` and `workflows/kestra/ansible/workflows/`.
- **Implemented by:** inventory groups, playbook tasks, Kestra working directories, staged local files, and `AnsibleCLI` Docker runners.
- **Dependencies:** SSH access, target OS/package managers, inventory variables, and Kestra secret values.
- **Change obligations:** Update both the playbook and its Kestra wrapper when the staged filename, inventory, variables, or execution contract changes. Preserve `--limit` guidance and privilege assumptions.
- **Verification:** Parse YAML; use Ansible check mode or a narrow `--limit` in a safe environment; for Kestra, verify staged input names and runner/plugin configuration.

## Terraform flow path

- **Exposed by:** `workflows/kestra/terraform/workflows/`.
- **Implemented by:** cloning the external homelab repository, injecting credentials, and running Terraform plan/apply.
- **Change obligations:** Keep secret names, working-directory variables, output capture, and trigger behavior aligned with the external module.
- **Verification:** Prefer plan output and review before apply; the current flows explicitly use `apply -auto-approve`, so changes have immediate infrastructure impact.
