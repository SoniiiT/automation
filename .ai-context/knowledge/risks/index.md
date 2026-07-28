# Risks and uncertainties

- **Inventory/playbook drift:** The active inventory has K3s groups commented out while K3s playbooks expect `k3s_cluster`, `server`, and `agent` groups. Reconcile before running the K3s path.
- **Broad targeting:** Several playbooks use `hosts: all`; accidental execution is possible without `--limit`.
- **Destructive operations:** Disk formatting/mounting, reboot, cleanup, package removal, K3s uninstall, and Windows debloat scripts modify hosts.
- **Infrastructure exposure:** The Docker install playbook configures a TCP listener on port 2375; review network controls before use.
- **Terraform blast radius:** Terraform flows run `apply -auto-approve` after cloning an external repository.
- **External placeholders:** Some workflow files contain placeholder webhook keys/URLs and require environment-specific configuration.
- **No automated regression suite:** There is no repository-wide test, lint, or CI configuration to detect YAML or script regressions.
- **Legacy code quality:** Some standalone scripts use broad exception handling or non-idempotent shell operations; preserve scope and validate before operational use.

These findings are evidence-backed review items, not claims that the referenced operations are currently active.
