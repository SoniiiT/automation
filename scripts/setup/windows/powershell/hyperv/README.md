# Hyper-V / Failover-Cluster Setup-Wizard

PowerShell-Setup-Skript für Hyper-V-Hosts und Failover-Cluster (Windows Server 2016+, Produktion).

## Modi

| Parameter | Zweck |
| --- | --- |
| `-Setup` | Interaktiver Setup-Wizard: Hyper-V installieren, optional Failover-Cluster aufbauen |
| `-Status` | Read-only Übersicht: Cluster-Gesundheit, Nodes, CSVs |

## Beispiele

```powershell
# Interaktiv, Nodes vorgegeben
.\hyperv-cluster.ps1 -Setup -Nodes node1,node2

# Nicht-interaktiv (Storage-Pfad + Cluster-IP vorab gesetzt)
.\hyperv-cluster.ps1 -Setup -Nodes node1,node2 -ClusterName hvcluster `
    -ClusterIP 10.0.10.50 -StoragePath SAN
```

## Wichtig — Vor der Ausführung

- **Von einer Management-Maschine** laufen lassen, **nicht** vom Cluster-Node.
- In einer **lokalen elevated (Administrator-)Session** starten.
  `New-Cluster` läuft nicht in `Enter-PSSession` ohne CredSSP.
- Management-Maschine sollte **dieselbe Windows-Version** haben wie die Nodes
  (sonst ggf. `Update-ClusterFunctionalLevel` nötig).
- **Alle Nodes** müssen dieselbe Windows-Version haben, domain-joined und in der
  gleichen Zeitzone sein. **Kein** Domain-Controller auf einem Node.
- WinRM auf allen Nodes erreichbar (`Enable-PSRemoting`).

## Storage-Pfade

Das Skript fragt den Storage-Weg interaktiv ab (oder via `-StoragePath`):

| Pfad | Format | Edition | Hinweis |
| --- | --- | --- | --- |
| **SAN** / iSCSI / FC / SAS | NTFS-CSV | Standard reicht | Shared LUNs auf allen Nodes |
| **S2D** (Storage Spaces Direct) | ReFS-CSV | **Datacenter nur** | lokale Platten, 2–16 Nodes |
| **Storage Replica** (Stretch) | NTFS | 2016: DC; 2019+: Standard (1 Vol ≤ 2 TB) | replizierte lokale Volumes |

> **Wichtig:** Reines lokales Storage ohne S2D kann NICHT in einen
> Failover-Cluster. Lokale Platten → S2D oder Storage Replica nötig.

## Netzwerk

- **SET** (Switch Embedded Teaming) wird beim Anlegen des vSwitch konfiguriert —
  nachträglich nicht möglich. Mitglieds-NICs müssen baugleich sein (gleicher
  Treiber/Firmware).
- Live-Migration-Netz optional als eigenes Subnetz/VLAN pinnen.

## Bekannte Lücken (Erst-Build)

- **SAN-Disk-Initialisierung** läuft aktuell lokal auf der Management-Maschine,
  muss aber auf den Owner-Nodes passieren (siehe TODO im Skript). Vor echtem
  Produktions-Einsatz nachziehen.
- Storage-Replica und S2D-Pool-Erstellung sind als Grundgerüst vorhanden, aber
  die vollständige Replica-Routine ist nicht ausimplementiert — geplant für die
  Maintenance-Iteration.

## Geplante nächste Iteration

`-Maintenance`-Modus: NIC zu SET hinzufügen, Node hinzufügen/entfernen
(VMs drainen + Live-Migrate), Storage erweitern.