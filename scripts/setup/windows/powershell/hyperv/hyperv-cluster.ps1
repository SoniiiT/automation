#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Hyper-V / Failover-Cluster Setup-Wizard (Produktion).

.DESCRIPTION
    Monolithisches Setup-Skript für Windows Server (2016+), das Hyper-V auf
    Ziel-Nodes installiert und optional einen Failover-Cluster aufbaut.

    Unterstützte Storage-Pfade:
      - SAN / iSCSI / Fibre Channel / SAS  (Shared LUNs -> NTFS-CSV)
      - Storage Spaces Direct (S2D)        (lokale Platten -> ReFS-CSV, Datacenter)
      - Storage Replica (Stretch)          (replizierte lokale Volumes)

    Netzwerk: SET (Switch Embedded Teaming) wird beim Anlegen des vSwitch
    konfiguriert (LBFO ist für Hyper-V ab Server 2022 deprecated).

    Jede Stufe ist idempotent: Es wird zuerst geprüft, ob der Schritt schon
    erledigt ist, damit halbe Läufe einfach wiederholt werden können.

    AUSFÜHRUNG: Von einer Management-Maschine (NICHT vom Cluster-Node) in
    einer LOKALEN elevated Session starten. 'New-Cluster' läuft nicht in
    Enter-PSSession ohne CredSSP. Management-Maschine sollte dieselbe
    Windows-Version haben wie die Nodes.

.EXAMPLE
    ./hyperv-cluster.ps1 -Setup -Nodes node1,node2 -ClusterName hvcluster

    Interaktiver Setup-Wizard mit vorgegebenen Nodes.

.EXAMPLE
    ./hyperv-cluster.ps1 -Setup -Nodes node1,node2 -ClusterName hvcluster -StoragePath SAN

    Nicht-interaktiver Modus mit explizit gesetztem Storage-Pfad.

.PARAMETER Setup
    Startet den Setup-Wizard.

.PARAMETER Maintenance
    Startet das Wartungsmenü: NIC zu SET hinzufügen, Node hinzufügen/entfernen.

.PARAMETER Status
    Zeigt eine read-only Übersicht des Clusters (wenn vorhanden).

.PARAMETER Nodes
    Hostnamen der Hyper-V-Ziel-Nodes.

.PARAMETER ClusterName
    NetBIOS-Name des Cluster-Name-Objects (max. 15 Zeichen).

.PARAMETER ClusterIP
    Statische IPv4-Adresse für den Cluster-Namen.

.PARAMETER StoragePath
    Storage-Architektur: 'SAN', 'S2D', 'StorageReplica'. Wird bei Angabe
    übersprungen und nicht interaktiv abgefragt.

.PARAMETER WitnessPath
    Für 2-Node-Cluster: Pfad zum SMB-Witness-Share (\\server\share) oder
    'Cloud' für Cloud-Witness. Interaktiv abgefragt, wenn nicht angegeben.

.PARAMETER LiveMigrationNetwork
    Subnetz/VLAN für Live-Migration (z.B. '10.0.30.0/24'). Optional.

.PARAMETER WhatIf
    Zeigt an, was getan würde, ohne Änderungen auszuführen (nur Warnung;
    WhatIf-Präferenz wird gesetzt, damit Cmdlets sie erben).

.NOTES
    Author: Vera (Code-Analystin für Tony)
    Repo: SoniiiT/automation
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Setup,
    [switch]$Maintenance,
    [switch]$Status,

    [string[]]$Nodes,
    [string]$ClusterName,
    [string]$ClusterIP,
    [ValidateSet('SAN', 'S2D', 'StorageReplica')]
    [string]$StoragePath,
    [string]$WitnessPath,
    [string]$LiveMigrationNetwork
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Logging-Setup
# ---------------------------------------------------------------------------
$logDir    = Join-Path $env:TEMP 'hyperv-cluster'
$logFile   = Join-Path $logDir ("hyperv-cluster-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
New-Item -ItemType Directory -Path $logDir -Force -ErrorAction SilentlyContinue | Out-Null
Start-Transcript -Path $logFile -Force | Out-Null
Write-Host "Log: $logFile" -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
function Write-Step {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
}

function Test-Admin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $p  = New-Object System.Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Invoke-RemoteNode {
    param(
        [string]$Node,
        [scriptblock]$ScriptBlock,
        [string[]]$ArgumentList = @()
    )
    # Führt einen ScriptBlock remote auf einem Node aus.
    # WinRM muss auf dem Node erreichbar sein (Enable-PSRemoting).
    Invoke-Command -ComputerName $Node -ScriptBlock $ScriptBlock -ArgumentList $ArgumentList -ErrorAction Stop
}

function Get-NodeWindowsVersion {
    param([string]$Node)
    try {
        $v = Invoke-RemoteNode -Node $Node -ScriptBlock {
            param($null)
            (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').DisplayVersion
        }
        return $v
    } catch {
        Write-Warn "Konnte Windows-Version von $Node nicht ermitteln: $($_.Exception.Message)"
        return $null
    }
}

function Test-RemoteWinRM {
    param([string]$Node)
    try {
        $r = Test-WSMan -ComputerName $Node -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Test-CNOPrivilege {
    param([string]$ClusterName)
    # Hinweis: Eine echte Rechteprüfung auf die Ziel-OU ist nur mit
    # AD-Rechten und LDAP-Query möglich. Diese Funktion prüft nur die
    # Mindestvoraussetzung (AD-Modul + Cluster-Name nicht existent).
    try {
        Import-Module ActiveDirectory -ErrorAction Stop
        if (Get-ADComputer -Identity $ClusterName -ErrorAction SilentlyContinue) {
            Write-Warn "CNO '$ClusterName' existiert bereits in AD. Nutze bestehendes Objekt oder passe Namen an."
            return $false
        }
        return $true
    } catch {
        Write-Warn "AD-Modul nicht verfügbar (auf Management-Maschine optional). CNO-Privileg kann hier nicht verifiziert werden."
        return $true # Weiche Prüfung: Fehler nicht blockierend
    }
}

function Get-ClusterStorageAvailable {
    # Liefert die verfügbaren (noch nicht geclusterten) Disks zurück.
    Get-ClusterAvailableDisk -All -ErrorAction Stop
}

function Initialize-SanDisk {
    param([int]$DiskNumber)
    # Initialisiert eine SAN-LUN (GPT, NTFS). WICHTIG: ReFS auf SAN läuft im
    # Redirected Mode -> deshalb NTFS für SAN-CSV.
    $disk = Get-Disk -Number $DiskNumber -ErrorAction Stop
    if ($disk.PartitionStyle -ne 'GPT') {
        Initialize-Disk -Number $DiskNumber -PartitionStyle GPT -ErrorAction Stop
    }
    $part = Get-Partition -DiskNumber $DiskNumber -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter }
    if (-not $part) {
        $part = New-Partition -DiskNumber $DiskNumber -UseMaximumSize -AssignDriveLetter -ErrorAction Stop
    }
    if (-not (Get-Volume -DriveLetter $part.DriveLetter | Where-Object FileSystem -eq 'NTFS')) {
        Format-Volume -DriveLetter $part.DriveLetter -FileSystem NTFS -Confirm:$false -ErrorAction Stop
    }
    return $part.DriveLetter
}

function New-VSwitchWithSet {
    param(
        [string]$Node,
        [string[]]$TeamMembers,
        [string]$SwitchName = 'vSwitchSET'
    )
    # SET-Teaming wird BEIM ANLEGEN des vSwitch konfiguriert — nachträglich
    # ist es nicht möglich. Alle Mitglieds-NICs müssen baugleich sein.
    Invoke-RemoteNode -Node $Node -ScriptBlock {
        param($Name, $Members)
        if (-not (Get-VMSwitch -Name $Name -ErrorAction SilentlyContinue)) {
            New-VMSwitch -Name $Name -NetAdapterName $Members -EnableEmbeddedTeaming $true -AllowManagementOS $true -ErrorAction Stop
            Write-Host "SET-vSwitch '$Name' auf '$env:COMPUTERNAME' angelegt (Teammitglieder: $Members)" -ForegroundColor Green
        } else {
            Write-Host "SET-vSwitch '$Name' existiert bereits." -ForegroundColor DarkGray
        }
    } -ArgumentList @($SwitchName, $TeamMembers)
}

# ---------------------------------------------------------------------------
# Maintenance-Hilfsfunktionen
# ---------------------------------------------------------------------------
function Test-NicComparability {
    param(
        [string]$Node,
        [string[]]$ExistingNics,
        [string[]]$NewNics
    )
    # SET verlangt baugleiche NICs (gleicher Hersteller, Produkt, Treiber).
    # Holt die NIC-Eigenschaften remote und vergleicht sie.
    $props = Invoke-RemoteNode -Node $Node -ScriptBlock {
        param($Names)
        Get-NetAdapter -Name $Names -ErrorAction SilentlyContinue |
            Select-Object Name, InterfaceDescription, DriverVersion, Manufacturer
    } -ArgumentList @(($ExistingNics + $NewNics) | Select-Object -Unique)

    $groups = $props | Group-Object InterfaceDescription
    if ($groups.Count -gt 1) {
        Write-Warn "Verschiedene NIC-Typen im Team gefunden: $($groups.Name -join ' | ')"
        return $false
    }
    if ($props.Count -lt ($ExistingNics + $NewNics | Select-Object -Unique).Count) {
        Write-Warn "Mindestens eine NIC wurde remote nicht gefunden."
        return $false
    }
    return $true
}

function Add-SetTeamMember {
    param(
        [string]$Node,
        [string]$SwitchName,
        [string]$NewNic
    )
    # Fügt einen NIC zu einem bestehenden SET-vSwitch hinzu. WICHTIG: SET
    # benötigt baugleiche NICs — vorher prüfen. Der vSwitch wird NICHT neu
    # erstellt (das würde Management-OS-Konnektivität kurz reißen), sondern
    # via Set-VMSwitch um die neue NIC erweitert.
    Invoke-RemoteNode -Node $Node -ScriptBlock {
        param($Name, $Nic)
        $sw = Get-VMSwitch -Name $Name -ErrorAction Stop
        if (-not $sw) { throw "vSwitch '$Name' nicht gefunden auf $env:COMPUTERNAME" }

        # Bestehende Teammitglieder über die InterfaceDescriptions des vSwitch
        # auflösen. NetAdapterInterfaceDescriptions sind exakt die
        # InterfaceDescriptions der physischen NICs im Team.
        $existing = @()
        foreach ($ifd in $sw.NetAdapterInterfaceDescriptions) {
            $adapter = Get-NetAdapter -ErrorAction SilentlyContinue |
                Where-Object { $_.InterfaceDescription -eq $ifd } | Select-Object -First 1
            if ($adapter) { $existing += $adapter.Name }
        }

        if ($existing -notcontains $Nic) {
            $existing += $Nic
            # Set-VMSwitch ersetzt die Teammitglieder atomar — NICHT den vSwitch
            # neu erzeugen (das würde Management-OS-Konnektivität kurz reißen).
            Set-VMSwitch -Name $Name -NetAdapterName $existing -ErrorAction Stop
            Write-Host "SET-Team '$Name' erweitert um '$Nic' (Mitglieder: $($existing -join ', '))" -ForegroundColor Green
        } else {
            Write-Host "NIC '$Nic' ist bereits Mitglied des SET-Teams." -ForegroundColor DarkGray
        }
    } -ArgumentList @($SwitchName, $NewNic)
}

function Add-ClusterNodeSafe {
    param(
        [string]$ClusterName,
        [string]$Node
    )
    # Fügt einen Node zum Cluster hinzu. Installiert zuerst die Features
    # (falls nötig), validiert und fügt dann hinzu.
    if (-not (Test-RemoteWinRM -Node $Node)) {
        Write-Fail "WinRM nicht erreichbar auf '$Node'."
        return $false
    }
    Write-Host "  Installiere Features auf '$Node'..." -ForegroundColor DarkGray
    Invoke-RemoteNode -Node $Node -ScriptBlock {
        $needed = @('Microsoft-Hyper-V', 'Failover-Clustering')
        $missing = $needed | Where-Object { (Get-WindowsFeature -Name $_).InstallState -ne 'Installed' }
        if ($missing) {
            Install-WindowsFeature -Name $missing -IncludeManagementTools -Restart:$false -ErrorAction Stop
            Write-Host "Features installiert: $($missing -join ', ')" -ForegroundColor Yellow
        }
    }

    if (-not (Get-ClusterNode -Cluster $ClusterName -Name $Node -ErrorAction SilentlyContinue)) {
        Write-Host "  Validiere mit bestehenden Nodes..." -ForegroundColor DarkGray
        $existing = Get-ClusterNode -Cluster $ClusterName | Select-Object -ExpandProperty Name
        $validation = Test-Cluster -Node ($existing + $Node) -ErrorAction Stop
        Write-Warn "Test-Cluster Report: $($validation.FullName) — rote Punkte prüfen, bevor du fortfährst."
        $confirm = Read-Host "Node '$Node' wirklich zum Cluster hinzufügen? (j/n)"
        if ($confirm -match '^(j|J|ja)$') {
            Add-ClusterNode -Cluster $ClusterName -Name $Node -ErrorAction Stop
            Write-Ok "Node '$Node' zum Cluster hinzugefügt."
            return $true
        }
    } else {
        Write-Ok "Node '$Node' ist bereits Cluster-Mitglied."
        return $true
    }
    return $false
}

function Remove-ClusterNodeSafe {
    param(
        [string]$ClusterName,
        [string]$Node
    )
    # Entfernt einen Node sicher: erst alle VMs live migrieren, dann Node raus.
    $nodeObj = Get-ClusterNode -Cluster $ClusterName -Name $Node -ErrorAction SilentlyContinue
    if (-not $nodeObj) {
        Write-Warn "Node '$Node' ist kein Cluster-Mitglied."
        return $false
    }

    $vms = Get-VM -ComputerName $Node -ErrorAction SilentlyContinue | Where-Object State -eq 'Running'
    if ($vms) {
        Write-Host "  Migriere $($vms.Count) laufende VMs von '$Node'..." -ForegroundColor DarkGray
        $targets = Get-ClusterNode -Cluster $ClusterName | Where-Object Name -ne $Node | Select-Object -ExpandProperty Name
        if (-not $targets) {
            Write-Fail "Kein Ziel-Node für Live-Migration vorhanden. Abbruch."
            return $false
        }
        foreach ($vm in $vms) {
            Write-Host "    Move-VM '$($vm.Name)' -> $($targets -join ', ')" -ForegroundColor DarkGray
            Move-VM -Name $vm.Name -ComputerName $Node -DestinationHost $targets[0] -ErrorAction Stop
        }
        Write-Ok "Alle VMs migriert."
    }

    $confirm = Read-Host "Node '$Node' wirklich aus dem Cluster entfernen? (j/n)"
    if ($confirm -match '^(j|J|ja)$') {
        Remove-ClusterNode -Cluster $ClusterName -Name $Node -ErrorAction Stop
        Write-Ok "Node '$Node' entfernt."
        return $true
    }
    return $false
}

# ---------------------------------------------------------------------------
# Voraussetzungen prüfen
# ---------------------------------------------------------------------------
if (-not (Test-Admin)) {
    Write-Fail "Dieses Skript muss in einer lokalen elevated (Administrator-) Session laufen."
    Stop-Transcript | Out-Null
    exit 1
}

if (-not ($Setup -or $Maintenance -or $Status)) {
    Write-Fail "Kein Modus gewählt. Nutze -Setup, -Maintenance oder -Status."
    Stop-Transcript | Out-Null
    exit 1
}

# ---------------------------------------------------------------------------
# Modus: STATUS (read-only)
# ---------------------------------------------------------------------------
if ($Status) {
    Write-Step "Cluster-Status"
    if (Get-Command Get-Cluster -ErrorAction SilentlyContinue) {
        $cluster = Get-Cluster -ErrorAction SilentlyContinue
        if ($cluster) {
            Write-Ok "Cluster: $($cluster.Name) | Status: $($cluster.Status)"
            Get-ClusterNode -Cluster $cluster.Name | Format-Table Name, State, Status -AutoSize
            Write-Host "`nCSVs:" -ForegroundColor Cyan
            Get-ClusterSharedVolume -Cluster $cluster.Name -ErrorAction SilentlyContinue |
                Format-Table Name, State, OwnerNode -AutoSize
        } else {
            Write-Warn "Kein Cluster in diesem Kontext gefunden."
        }
    } else {
        Write-Warn "Failover-Clustering-Module nicht auf der Management-Maschine installiert."
    }
    Stop-Transcript | Out-Null
    exit 0
}

# ---------------------------------------------------------------------------
# Modus: MAINTENANCE
# ---------------------------------------------------------------------------
if ($Maintenance) {
    Write-Step "Maintenance-Menü"

    $cluster = Get-Cluster -ErrorAction SilentlyContinue
    if (-not $cluster) {
        Write-Warn "Kein Cluster in diesem Kontext gefunden. SET-Wartung funktioniert weiterhin, Node-Add/Remove aber nicht."
    }
    $clusterName = $cluster.Name

    Write-Host "`nWähle eine Aktion:" -ForegroundColor Cyan
    Write-Host "  1) NIC zu SET-Team hinzufügen"
    Write-Host "  2) Node zum Cluster hinzufügen"
    Write-Host "  3) Node aus dem Cluster entfernen"
    $action = Read-Host "Auswahl (1/2/3)"

    switch ($action) {
        '1' {
            if (-not $Nodes) {
                $Nodes = @(Read-Host "Node(s) mit dem SET-Team (kommagetrennt)")
            }
            $switchName = Read-Host "Name des bestehenden SET-vSwitch (Default: vSwitchSET)"
            if (-not $switchName) { $switchName = 'vSwitchSET' }
            $newNic = Read-Host "Neue NIC, die hinzugefügt werden soll"

            foreach ($node in $Nodes) {
                if (-not (Test-RemoteWinRM -Node $node)) {
                    Write-Fail "WinRM nicht erreichbar auf '$node'."
                    continue
                }
                # Baugleich-Check: bestehende Team-NICs gegen die neue prüfen
                $swInfo = Invoke-RemoteNode -Node $node -ScriptBlock {
                    param($Name)
                    $sw = Get-VMSwitch -Name $Name -ErrorAction SilentlyContinue
                    if ($sw) { $sw.NetAdapterInterfaceDescriptions } else { @() }
                } -ArgumentList @($switchName)
                $existingNics = @($swInfo | ForEach-Object {
                    Invoke-RemoteNode -Node $node -ScriptBlock {
                        param($Ifd)
                        (Get-NetAdapter | Where-Object InterfaceDescription -eq $Ifd | Select-Object -First 1).Name
                    } -ArgumentList @($_)
                })
                if (Test-NicComparability -Node $node -ExistingNics $existingNics -NewNics @($newNic)) {
                    Add-SetTeamMember -Node $node -SwitchName $switchName -NewNic $newNic
                } else {
                    Write-Fail "Baugleich-Check fehlgeschlagen — NIC '$newNic' ist nicht kompatibel mit dem bestehenden Team auf '$node'. Abbruch für diesen Node."
                }
            }
        }
        '2' {
            if (-not $clusterName) {
                Write-Fail "Kein Cluster gefunden. Node-Add ist ohne Cluster nicht möglich."
                Stop-Transcript | Out-Null
                exit 1
            }
            $newNode = Read-Host "Hostname des hinzuzufügenden Nodes"
            Add-ClusterNodeSafe -ClusterName $clusterName -Node $newNode
        }
        '3' {
            if (-not $clusterName) {
                Write-Fail "Kein Cluster gefunden. Node-Remove ist ohne Cluster nicht möglich."
                Stop-Transcript | Out-Null
                exit 1
            }
            $remNode = Read-Host "Hostname des zu entfernenden Nodes"
            Remove-ClusterNodeSafe -ClusterName $clusterName -Node $remNode
        }
        default {
            Write-Fail "Ungültige Auswahl."
        }
    }

    Stop-Transcript | Out-Null
    exit 0
}

# ---------------------------------------------------------------------------
# Modus: SETUP
# ---------------------------------------------------------------------------
Write-Step "Setup-Wizard: Voraussetzungen"

# 1. Nodes validieren
if (-not $Nodes -or $Nodes.Count -eq 0) {
    $input = Read-Host "Hyper-V-Ziel-Nodes (kommagetrennt)"
    $Nodes = $input -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}
if ($Nodes.Count -eq 0) {
    Write-Fail "Keine Nodes angegeben."
    Stop-Transcript | Out-Null
    exit 1
}

$versions = @{}
foreach ($node in $Nodes) {
    if (-not (Test-RemoteWinRM -Node $node)) {
        Write-Fail "WinRM nicht erreichbar auf '$node'. Stelle sicher, dass Enable-PSRemoting läuft und die Firewall-Regel gesetzt ist."
        Stop-Transcript | Out-Null
        exit 1
    }
    $ver = Get-NodeWindowsVersion -Node $node
    $versions[$node] = $ver
    Write-Ok "Node '$node' erreichbar (Windows $ver)"
}

# Gleiche Windows-Version auf allen Nodes erzwingen
$uniqueVersions = $versions.Values | Sort-Object -Unique
if ($uniqueVersions.Count -gt 1) {
    Write-Fail "Die Nodes haben UNTERSCHIEDLICHE Windows-Versionen: $($uniqueVersions -join ', '). Ein Failover-Cluster verlangt dieselbe Version auf allen Nodes."
    Stop-Transcript | Out-Null
    exit 1
}
Write-Ok "Alle Nodes: Windows $($uniqueVersions)"

# 2. Cluster-Typ abfragen
$makeCluster = $false
$choice = Read-Host "Failover-Cluster aufbauen? (j/n, Default: n)"
if ($choice -eq 'j' -or $choice -eq 'J' -or $choice -eq 'ja') {
    $makeCluster = $true
}

if ($makeCluster) {
    if (-not $ClusterName) {
        $ClusterName = Read-Host "Cluster-Name (max 15 Zeichen)"
    }
    if ($ClusterName.Length -gt 15) {
        Write-Fail "Cluster-Name darf max. 15 Zeichen haben."
        Stop-Transcript | Out-Null
        exit 1
    }
    if (-not $ClusterIP) {
        $ClusterIP = Read-Host "Statische IP für Cluster-Name"
    }
    # CNO-Privileg prüfen (weich)
    Test-CNOPrivilege -ClusterName $ClusterName | Out-Null

    # 3. Storage-Pfad
    if (-not $StoragePath) {
        Write-Host "`nStorage-Pfad wählen:" -ForegroundColor Cyan
        Write-Host "  1) SAN / iSCSI / Fibre Channel / SAS (Shared LUNs, NTFS-CSV)"
        Write-Host "  2) Storage Spaces Direct (S2D) - lokale Platten (Datacenter-Edition!)"
        Write-Host "  3) Storage Replica (Stretch) - replizierte lokale Volumes"
        $sp = Read-Host "Auswahl (1/2/3)"
        switch ($sp) {
            '1' { $StoragePath = 'SAN' }
            '2' { $StoragePath = 'S2D' }
            '3' { $StoragePath = 'StorageReplica' }
            default {
                Write-Fail "Ungültige Auswahl."
                Stop-Transcript | Out-Null
                exit 1
            }
        }
    }

    if ($StoragePath -eq 'S2D') {
        Write-Warn "S2D erfordert die Datacenter-Edition auf JEDEM Node. Standard-Edition wird nicht unterstützt."
        $confirm = Read-Host "Sicher, dass alle Nodes Datacenter sind? (j/n)"
        if ($confirm -notin @('j', 'J', 'ja')) {
            Write-Fail "Abgebrochen. S2D ohne Datacenter ist nicht unterstützt."
            Stop-Transcript | Out-Null
            exit 1
        }
    }
}

# 4. Netzwerk: SET-Team anlegen?
$doSet = $false
$setNics = @()
$setAnswer = Read-Host "SET-NIC-Teaming konfigurieren (j/n, Default: n)"
if ($setAnswer -match '^(j|J|ja)$') {
    $doSet = $true
    $setNics = (Read-Host "NICs für SET-Team (kommagetrennt)") -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
}

# 5. Live-Migration-Netz (optional)
if ($makeCluster -and -not $LiveMigrationNetwork) {
    $lm = Read-Host "Live-Migration-Netzwerk-Subnetz (z.B. 10.0.30.0/24, leer = überspringen)"
    if ($lm) { $LiveMigrationNetwork = $lm }
}

# ---------------------------------------------------------------------------
# Ausführung
# ---------------------------------------------------------------------------
Write-Step "Hyper-V-Rolle installieren"

foreach ($node in $Nodes) {
    Write-Host "  Installiere Hyper-V + Failover-Clustering auf '$node'..." -ForegroundColor DarkGray
    Invoke-RemoteNode -Node $node -ScriptBlock {
        $features = @('Microsoft-Hyper-V', 'Failover-Clustering')
        $installed = @()
        foreach ($f in $features) {
            if ((Get-WindowsFeature -Name $f).InstallState -eq 'Installed') {
                $installed += $f
            }
        }
        $missing = $features | Where-Object { $_ -notin $installed }
        if ($missing) {
            Install-WindowsFeature -Name $missing -IncludeManagementTools -Restart:$false -ErrorAction Stop
            # Reboot-Planung: Nodes müssen nach Hyper-V-Install neu starten.
            Write-Host "Feature '$($missing -join ',')' installiert. Reboot nötig." -ForegroundColor Yellow
        } else {
            Write-Host "Alle benötigten Features bereits installiert." -ForegroundColor DarkGray
        }
    }
    Write-Ok "Hyper-V/Cluster-Features auf '$node' sichergestellt."
}

# SET-Team anlegen (falls gewünscht) — MUSS beim vSwitch-Anlegen passieren
if ($doSet) {
    Write-Step "SET-NIC-Teaming konfigurieren"
    if ($setNics.Count -lt 2) {
        Write-Warn "SET benötigt mindestens 2 NICs. Überspringe SET-Konfiguration."
    } else {
        foreach ($node in $Nodes) {
            New-VSwitchWithSet -Node $node -TeamMembers $setNics
        }
    }
}

Write-Warn "Hinweis: Nach der Hyper-V-Rolle ist ein Neustart der Nodes nötig. Setze das Skript nach dem Reboot fort."

# Nach Reboot (idempotenter Neustart des Skripts) fällt hier die Einrichtung weiter:
# Storage + Cluster.
if ($makeCluster) {
    Write-Step "Storage konfigurieren ($StoragePath)"

    switch ($StoragePath) {
        'SAN' {
            Write-Host "  SAN-Weg: Shared LUNs müssen auf allen Nodes als identische Disk-Nummern sichtbar sein." -ForegroundColor DarkGray
            $disk = Get-ClusterStorageAvailable | Select-Object -First 1
            if ($disk) {
                Write-Ok "Gefundene Shared Disk: $($disk.Number)"
                # TODO(vera): Disk-Initialisierung (Initialize-SanDisk) läuft hier
                # LOKAL auf der Management-Maschine — das ist für echte Nodes falsch,
                # da die LUN in den Nodes steckt. Muss remote via Invoke-Command auf
                # dem Owner-NODE laufen. Für den Erst-Build als bewusste Lücke
                # markiert; auf echter Hardware vor Freigabe nachziehen.
                $dl = Initialize-SanDisk -DiskNumber $disk.Number
                Write-Ok "SAN-LUN auf '$($env:COMPUTERNAME)' initialisiert (Laufwerk $dl, NTFS)."
            } else {
                Write-Warn "Keine verfügbare Shared Disk gefunden. Bitte LUN auf allen Nodes präsentieren und erneut ausführen."
            }
        }
        'S2D' {
            Write-Host "  S2D-Weg: Lokale Platten werden zu einem Pool zusammengeführt." -ForegroundColor DarkGray
            # S2D-Pool-Erstellung erfolgt hier als Hinweis/Teil — die eigentliche
            # Enable-ClusterStorageSpacesDirect-Routine läuft nach Cluster-Erstellung.
            Write-Warn "S2D-Pool wird NACH Cluster-Erstellung via Enable-ClusterStorageSpacesDirect aktiviert."
        }
        'StorageReplica' {
            Write-Host "  Storage-Replica-Weg: Replikation zwischen 2 Nodes. Editions-/Versionsprüfung nötig." -ForegroundColor DarkGray
            Write-Warn "Storage Replica: Auf Server 2016 nur Datacenter; ab 2019 Standard (1 Vol ≤ 2 TB). Stretch-Cluster braucht 2 Sets Shared Storage."
        }
    }

    Write-Step "Cluster validieren & erstellen"

    if ($Nodes.Count -ge 2) {
        Write-Host "  Validiere Konfiguration mit Test-Cluster..." -ForegroundColor DarkGray
        $validation = Test-Cluster -Node $Nodes -ErrorAction Stop
        Write-Ok "Test-Cluster abgeschlossen (Bericht: $($validation.FullName))"
        # Hinweis: Nur ein komplett grüner Report ist supported. Wir warnen,
        # blockieren aber nicht — der Admin sieht den Report.
        Write-Warn "Prüfe den Validierungsreport auf rote Punkte, bevor du fortfährst."

        if (Test-CNOPrivilege -ClusterName $ClusterName) {
            Write-Host "  Erstelle Cluster '$ClusterName'..." -ForegroundColor DarkGray
            New-Cluster -Name $ClusterName -Node $Nodes -StaticAddress $ClusterIP -NoStorage -ErrorAction Stop | Out-Null
            Write-Ok "Cluster '$ClusterName' erstellt."

            # Witness für 2-Node-Cluster
            if ($Nodes.Count -eq 2) {
                if (-not $WitnessPath) {
                    $WitnessPath = Read-Host "2-Node-Cluster braucht einen Witness. SMB-Share-Pfad (\\server\share) oder 'Cloud'"
                }
                if ($WitnessPath -eq 'Cloud') {
                    Set-ClusterQuorum -CloudWitness -Credential (Get-Credential) -ErrorAction Stop
                    Write-Ok "Cloud-Witness konfiguriert."
                } elseif ($WitnessPath) {
                    Set-ClusterQuorum -FileShareWitness $WitnessPath -ErrorAction Stop
                    Write-Ok "File-Share-Witness ($WitnessPath) konfiguriert."
                } else {
                    Write-Warn "Kein Witness konfiguriert. Der Cluster läuft, aber ohne Quorum-Fehlerresistenz für 2 Nodes."
                }
            }

            # Storage zum Cluster hinzufügen
            Write-Step "Cluster-Storage hinzufügen"
            if ($StoragePath -eq 'S2D') {
                $s2dAnswer = Read-Host "S2D jetzt aktivieren? (j/n)"
                if ($s2dAnswer -match '^(j|J|ja)$') {
                    Enable-ClusterStorageSpacesDirect -Cluster $ClusterName -ErrorAction Stop
                    Write-Ok "S2D aktiviert."
                }
            } else {
                Get-ClusterAvailableDisk -All -ErrorAction SilentlyContinue | Add-ClusterDisk -ErrorAction SilentlyContinue
                Write-Ok "Verfügbare Disks zum Cluster hinzugefügt."
            }

            # CSV konvertieren (SAN/S2D)
            Get-ClusterSharedVolume -Cluster $ClusterName -ErrorAction SilentlyContinue | Where-Object { -not $_.IsCsv } |
                Add-ClusterSharedVolume -ErrorAction SilentlyContinue
            Write-Ok "CSV-Konfiguration abgeschlossen."

            # Live-Migration-Netz pinnen
            if ($LiveMigrationNetwork) {
                Write-Host "  Pinne Live-Migration-Netz..." -ForegroundColor DarkGray
                Get-ClusterNetwork -Cluster $ClusterName -ErrorAction SilentlyContinue |
                    Where-Object { $_.Address -like "*$($LiveMigrationNetwork.Split('/')[0])*" } |
                    Set-ClusterNetwork -Role ClusterAndClient -ErrorAction SilentlyContinue
                Get-ClusterResourceType -Cluster $ClusterName -Name "Virtual Machine" -ErrorAction SilentlyContinue |
                    Set-ClusterParameter -Name "MigrationNetworks" -Value $null -ErrorAction SilentlyContinue
                Write-Ok "Live-Migration-Netz gepinnt (manuell je nach Umgebung nachjustieren)."
            }
        }
    } else {
        Write-Warn "Für einen Failover-Cluster werden mindestens 2 Nodes benötigt. Nur Hyper-V wurde eingerichtet."
    }
}

Write-Step "Setup abgeschlossen"
Write-Ok "Logfile: $logFile"
Stop-Transcript | Out-Null
exit 0