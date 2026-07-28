# Removal guidance

## Removing or replacing active automation

1. Identify the source playbook or script and every Kestra flow that stages or invokes it.
2. Remove or disable schedules/webhooks before deleting the implementation.
3. Check inventory groups, secret references, external credentials, and generated outputs for remaining consumers.
4. Preserve a migration note and verify that alert flows do not reference removed namespaces or flow IDs.
5. Keep rollback instructions for infrastructure changes; do not delete historical files automatically.

## Archived manual Kubernetes scripts

- The manual scripts under `kubernetes/Multi Master Cluster/` are already documented as archived.
- Do not delete them solely because they are deprecated; they are retained as reference.
- If removal is explicitly approved, first confirm no operational runbook, host bootstrap, or external link still references them, then update `kubernetes/README.md` and this guide.

## Teleport

`ansible/playbooks/system/install/install-teleport.yaml` is currently an empty placeholder, while `ansible/playbooks/system/uninstall/uninstall-teleport.yaml` contains the removal implementation. Before removing or completing Teleport automation, check inventory targeting and any running proxy/agent hosts, then execute a constrained uninstall and document configuration/data cleanup.
