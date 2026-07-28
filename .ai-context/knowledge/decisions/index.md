# Decisions

## ADR-001: Use K3s and Ansible for active Kubernetes automation

- **Status:** documented decision
- **Decision:** The repository's active Kubernetes automation uses K3s managed through Ansible.
- **Evidence:** `kubernetes/README.md` marks the manual multi-master scripts deprecated and names K3s plus Ansible as the replacement.
- **Impact:** New cluster automation belongs under `ansible/playbooks/kubernetes/` and its Kestra wrappers, not under `kubernetes/Multi Master Cluster/`.

No other architecture decisions were explicitly recorded in the repository during this analysis.
