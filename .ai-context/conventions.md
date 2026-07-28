# Conventions

## Documentation and language

- Repository documentation is primarily German; code and comments are mixed German/English.
- Each major area has a README with local usage guidance.
- New files should stay in the existing thematic directory structure and match the local language/style where practical.

## Ansible

- Use YAML playbooks grouped by concern under `ansible/playbooks/`.
- Prefer fully qualified module names such as `ansible.builtin.apt`.
- Target inventory groups deliberately; the README warns that local runs must use `--limit` because many playbooks use `hosts: all`.
- Account for the documented privilege model: LXC and Proxmox hosts run as `root` without `become`; VM and physical hosts use the `soniiit` user with escalation.
- Use `ansible_os_family` or package-manager facts for multi-OS tasks.
- K3s playbooks use explicit host/group conditions and Jinja hostvars for bootstrap tokens and cluster values.

## Kestra

- Flows declare `id`, `namespace`, labels, tasks, and triggers in YAML.
- Ansible flows use a working directory, local file staging, an Ansible CLI task, and usually a Docker task runner.
- Credentials are injected with `secret(...)`; do not commit their values.
- Terraform flows keep plan/apply output as local-file outputs.

## Scripts

- Scripts are executable entry points with dependencies declared in the nearest `requirements.txt`.
- Shell scripts use `set -euo pipefail` where present and write operational logs.
- PowerShell scripts expose parameters, validate prerequisites, print status, and use non-zero exits for failed prerequisite/build steps.
- Python tools mix direct `print` output and standard logging; GUI tools use Tkinter, CustomTkinter, or Streamlit.

## Testing and validation

No test suite, CI workflow, root package manifest, or repository-wide linter configuration was found. Validate changes with syntax/parse checks appropriate to the touched artifact and use the target tool's dry-run or plan mode where available.

## Safety-sensitive patterns

Inventory targeting, privilege escalation, destructive cleanup, system package changes, Docker daemon exposure, Terraform `apply -auto-approve`, and browser automation all have operational impact. Preserve explicit confirmations, limits, prerequisite checks, and secret indirection when modifying these areas.
