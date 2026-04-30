<#
.SYNOPSIS
    Builds a local Docker image (optional tar export and cleanup).

.DESCRIPTION
    This script only handles local Docker image creation.
    It does not upload to servers and does not interact with Kubernetes.

.PARAMETER ImageName
    Optional image tag, e.g. myapp:latest

.PARAMETER DockerPath
    Optional path to Docker build context. Default is current folder (.)

.PARAMETER ExportTar
    If set, exports the built image as a .tar file.

.PARAMETER TarPath
    Optional output tar path. If not set, %TEMP% is used.

.PARAMETER CleanupLocalImage
    If set, removes the local image after successful build/export.
#>

param(
    [string]$ImageName,
    [string]$DockerPath = ".",
    [switch]$ExportTar,
    [string]$TarPath,
    [switch]$CleanupLocalImage
)

$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Cyan"

Write-Host "================================================" -ForegroundColor $BLUE
Write-Host "   Local Docker Image Builder (PowerShell)" -ForegroundColor $BLUE
Write-Host "================================================`n" -ForegroundColor $BLUE

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Fehler: Docker CLI wurde nicht gefunden." -ForegroundColor $RED
    Write-Host "Bitte Docker Desktop / Docker CLI installieren und PATH pruefen." -ForegroundColor $YELLOW
    exit 1
}

if ([string]::IsNullOrWhiteSpace($ImageName)) {
    Write-Host "Schritt 1: Docker Image Name" -ForegroundColor $YELLOW
    $ImageName = Read-Host "Bitte gib den Namen des Docker Images ein (z.B. myapp:latest)"
}

if ([string]::IsNullOrWhiteSpace($ImageName)) {
    Write-Host "Fehler: Image Name darf nicht leer sein." -ForegroundColor $RED
    exit 1
}

if (-not $PSBoundParameters.ContainsKey("DockerPath")) {
    Write-Host "Schritt 2: Docker Build-Kontext" -ForegroundColor $YELLOW
    $dockerPathInput = Read-Host "Pfad zum Dockerfile-Verzeichnis (. fuer aktuelles Verzeichnis)"
    if (-not [string]::IsNullOrWhiteSpace($dockerPathInput)) {
        $DockerPath = $dockerPathInput
    }
}

if (-not (Test-Path $DockerPath)) {
    Write-Host "Fehler: Der angegebene Pfad existiert nicht: $DockerPath" -ForegroundColor $RED
    exit 1
}

Write-Host "`nSchritt 3: Docker Image wird gebaut..." -ForegroundColor $YELLOW
docker build -t "$ImageName" "$DockerPath"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Fehler beim Bauen des Docker Images." -ForegroundColor $RED
    exit 1
}

Write-Host "✓ Docker Image erfolgreich gebaut: $ImageName`n" -ForegroundColor $GREEN

$imageTar = $null

# Interactive fallback if ExportTar was not provided as a switch.
if (-not $PSBoundParameters.ContainsKey("ExportTar")) {
    $exportChoice = Read-Host "Moechtest du das Image als tar exportieren? (j/n)"
    if ($exportChoice -match '^[jJyY]') {
        $ExportTar = $true
    }
}

if ($ExportTar) {
    Write-Host "Schritt 4: Image wird exportiert..." -ForegroundColor $YELLOW

    if ([string]::IsNullOrWhiteSpace($TarPath)) {
        $safeImageName = $ImageName -replace '[:/\\]', '_'
        $TarPath = Join-Path $env:TEMP "$safeImageName.tar"
    }

    docker save "$ImageName" -o "$TarPath"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Fehler beim Exportieren des Images." -ForegroundColor $RED
        exit 1
    }

    $imageTar = Get-Item $TarPath -ErrorAction SilentlyContinue
    if ($null -ne $imageTar) {
        $imageSize = "{0:N0} MB" -f ($imageTar.Length / 1MB)
        Write-Host "✓ Image exportiert: $TarPath ($imageSize)`n" -ForegroundColor $GREEN
    } else {
        Write-Host "✓ Image exportiert: $TarPath`n" -ForegroundColor $GREEN
    }
}

# Interactive fallback if CleanupLocalImage was not provided as a switch.
if (-not $PSBoundParameters.ContainsKey("CleanupLocalImage")) {
    $cleanupChoice = Read-Host "Moechtest du das lokale Image wieder loeschen? (j/n)"
    if ($cleanupChoice -match '^[jJyY]') {
        $CleanupLocalImage = $true
    }
}

if ($CleanupLocalImage) {
    Write-Host "Schritt 5: Lokales Image wird entfernt..." -ForegroundColor $YELLOW
    docker rmi "$ImageName" | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Lokales Image entfernt" -ForegroundColor $GREEN
    } else {
        Write-Host "Warnung: Lokales Image konnte nicht vollstaendig entfernt werden" -ForegroundColor $YELLOW
    }
}

Write-Host "`n================================================" -ForegroundColor $BLUE
Write-Host "Fertig: Lokaler Docker Build abgeschlossen." -ForegroundColor $GREEN
Write-Host "================================================" -ForegroundColor $BLUE
