#Requires -Version 5.1
<#
.SYNOPSIS
    Installiert HuggingFaceModelDownloader (hfdownloader) inkl. Hintergrund-Launcher
    und Startmenü-Verknüpfung ("HuggingFace Downloader") auf Windows.

.DESCRIPTION
    - Lädt die passende hfdownloader.exe (amd64) vom offiziellen GitHub Release
      (bodaay/HuggingFaceModelDownloader) herunter, falls noch nicht vorhanden
      oder veraltet (idempotent).
    - Installiert nach %LOCALAPPDATA%\HFDownloader\hfdownloader.exe
    - Legt einen Flat-File Modell-Ordner an (--local-dir, KEIN HF-Cache/Symlink-Modus).
    - Erzeugt ein PowerShell-Startskript + einen .vbs-Wrapper, der die WebUI
      komplett unsichtbar (kein Konsolenfenster) im Hintergrund startet und
      danach automatisch den Standardbrowser öffnet.
    - Erzeugt eine Startmenü-Verknüpfung "HuggingFace Downloader.lnk" (und optional
      eine Desktop-Verknüpfung), damit das Tool über die Windows-Suche auffindbar ist.
    - Läuft bereits ein Server (Port belegt / PID-Datei aktiv), wird beim erneuten
      Start nur der Browser geöffnet - kein zweiter Serverprozess.

.PARAMETER ModelsRoot
    Zielordner für heruntergeladene Modelle (Flat-File-Modus). Standard:
    %USERPROFILE%\lmstudio-models

.PARAMETER Port
    Bevorzugter Startport der WebUI. Standard: 8080. Ist der Port belegt,
    sucht der Launcher automatisch den nächsten freien Port.

.PARAMETER Force
    Erzwingt einen erneuten Download der Binary, auch wenn bereits eine
    aktuelle Version installiert ist.

.PARAMETER NoDesktopShortcut
    Überspringt das Anlegen der Desktop-Verknüpfung (Startmenü-Verknüpfung
    wird immer erstellt).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1 -ModelsRoot D:\Models -Port 9090 -Force
#>

[CmdletBinding()]
param(
    [string]$ModelsRoot = (Join-Path $env:USERPROFILE "lmstudio-models"),
    [int]$Port = 8080,
    [switch]$Force,
    [switch]$NoDesktopShortcut
)

$ErrorActionPreference = "Stop"

function Write-Info($msg)  { Write-Host "[hfdownloader] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "[hfdownloader] $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "[hfdownloader] $msg" -ForegroundColor Yellow }

$Repo        = "bodaay/HuggingFaceModelDownloader"
$InstallDir  = Join-Path $env:LOCALAPPDATA "HFDownloader"
$ExePath     = Join-Path $InstallDir "hfdownloader.exe"
$VersionFile = Join-Path $InstallDir "version.txt"
$StartPs1    = Join-Path $InstallDir "Start-HFDownloader.ps1"
$LauncherVbs = Join-Path $InstallDir "Launch-HFDownloader.vbs"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ModelsRoot | Out-Null

# --- Architektur-Check (nur amd64-Release verfügbar; läuft auf ARM64 via Emulation) ---
$arch = $env:PROCESSOR_ARCHITECTURE
if ($arch -eq "ARM64") {
    Write-Warn2 "Windows-ARM64 erkannt: es gibt kein natives ARM64-Release, es wird die amd64-Binary (x64-Emulation) verwendet."
}

# --- Idempotente Installation der Binary ---
Write-Info "Prüfe aktuelle Release-Version von $Repo ..."
try {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repo/releases/latest" -Headers @{ "User-Agent" = "hfdownloader-installer" }
} catch {
    throw "Konnte Release-Informationen nicht abrufen: $_"
}
$tag = $release.tag_name
$asset = $release.assets | Where-Object { $_.name -like "hfdownloader_windows_amd64_*.exe" } | Select-Object -First 1
if (-not $asset) { throw "Kein Windows-amd64-Asset im Release $tag gefunden." }

$needsDownload = $true
if ((Test-Path $ExePath) -and (Test-Path $VersionFile) -and (-not $Force)) {
    $installedTag = (Get-Content $VersionFile -Raw).Trim()
    if ($installedTag -eq $tag) {
        $needsDownload = $false
        Write-Ok "hfdownloader ist bereits aktuell (Version $tag), Download übersprungen."
    }
}

if ($needsDownload) {
    Write-Info "Lade hfdownloader $tag herunter -> $ExePath"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $ExePath -UseBasicParsing
    Set-Content -Path $VersionFile -Value $tag -NoNewline
    Write-Ok "Installation abgeschlossen: $ExePath"
}

# --- Start-Skript schreiben (führt Port-Check, Hintergrundstart, Browser-Open aus) ---
$startScriptContent = @"
# Automatisch generiert von install.ps1 - nicht manuell bearbeiten.
`$ErrorActionPreference = 'SilentlyContinue'

`$ExePath     = '$ExePath'
`$ModelsRoot  = '$ModelsRoot'
`$BasePort    = $Port
`$StateDir    = '$InstallDir'
`$PidFile     = Join-Path `$StateDir 'server.pid'
`$PortFile    = Join-Path `$StateDir 'server.port'

function Test-PortOpen([int]`$p) {
    try {
        `$client = New-Object System.Net.Sockets.TcpClient
        `$iar = `$client.BeginConnect('127.0.0.1', `$p, `$null, `$null)
        `$ok = `$iar.AsyncWaitHandle.WaitOne(300)
        if (`$ok -and `$client.Connected) { `$client.Close(); return `$true }
        `$client.Close()
        return `$false
    } catch { return `$false }
}

function Get-RunningPort() {
    if (-not (Test-Path `$PortFile)) { return `$null }
    `$p = (Get-Content `$PortFile -Raw -ErrorAction SilentlyContinue)
    if (-not `$p) { return `$null }
    `$p = `$p.Trim()
    if (-not (Test-PortOpen ([int]`$p))) { return `$null }
    if (Test-Path `$PidFile) {
        `$storedPid = (Get-Content `$PidFile -Raw -ErrorAction SilentlyContinue)
        if (`$storedPid) {
            `$storedPid = `$storedPid.Trim()
            if (-not (Get-Process -Id `$storedPid -ErrorAction SilentlyContinue)) { return `$null }
        }
    }
    return [int]`$p
}

`$existingPort = Get-RunningPort
if (`$existingPort) {
    Start-Process "http://localhost:`$existingPort"
    return
}

# Freien Port ab BasePort suchen
`$port = `$BasePort
while (Test-PortOpen `$port) { `$port++ }

`$proc = Start-Process -FilePath `$ExePath -ArgumentList @('serve', '--local-dir', `$ModelsRoot, '--port', "`$port") -WindowStyle Hidden -PassThru
Set-Content -Path `$PidFile -Value `$proc.Id -NoNewline
Set-Content -Path `$PortFile -Value `$port -NoNewline

# Bis zu 5 Sekunden auf Serverstart warten
`$deadline = (Get-Date).AddSeconds(5)
while ((Get-Date) -lt `$deadline) {
    if (Test-PortOpen `$port) { break }
    Start-Sleep -Milliseconds 200
}

Start-Process "http://localhost:`$port"
"@

Set-Content -Path $StartPs1 -Value $startScriptContent -Encoding UTF8
Write-Ok "Start-Skript geschrieben: $StartPs1"

# --- VBS-Wrapper: startet PowerShell komplett unsichtbar (kein Fenster-Flackern) ---
$vbsContent = @"
' Automatisch generiert von install.ps1 - nicht manuell bearbeiten.
Set WshShell = CreateObject("WScript.Shell")
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""$StartPs1"""
WshShell.Run cmd, 0, False
"@
Set-Content -Path $LauncherVbs -Value $vbsContent -Encoding ASCII
Write-Ok "Launcher geschrieben: $LauncherVbs"

# --- Verknüpfungen erzeugen (Startmenü + optional Desktop) ---
function New-HFShortcut([string]$Path) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = "$env:WINDIR\System32\wscript.exe"
    $shortcut.Arguments = "`"$LauncherVbs`""
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.IconLocation = "$ExePath,0"
    $shortcut.Description = "HuggingFace Downloader WebUI starten"
    $shortcut.Save()
}

$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$startMenuLnk = Join-Path $startMenuDir "HuggingFace Downloader.lnk"
New-HFShortcut -Path $startMenuLnk
Write-Ok "Startmenü-Verknüpfung erstellt: $startMenuLnk"

if (-not $NoDesktopShortcut) {
    $desktopLnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "HuggingFace Downloader.lnk"
    New-HFShortcut -Path $desktopLnk
    Write-Ok "Desktop-Verknüpfung erstellt: $desktopLnk"
}

Write-Host ""
Write-Ok "Fertig! Suche im Startmenü nach 'HuggingFace Downloader' und starte per Klick."
Write-Info "Modelle werden abgelegt in: $ModelsRoot"
Write-Info "Bevorzugter Port: $Port (bei Belegung wird automatisch der nächste freie Port gewählt)"
