#Requires -Version 5.1
<#
.SYNOPSIS
    Registriert das Morgenbriefing als Windows-Aufgabe.
.DESCRIPTION
    Der Lauf ist ausschliesslich lesend. Wenn die Microsoft-Anmeldung abgelaufen
    ist, oeffnet sich ein sichtbares Browserfenster fuer die manuelle Anmeldung.
    Deshalb laeuft die Aufgabe bewusst nicht versteckt.
.PARAMETER Time
    Startzeit im Format HH:mm. Standard: 07:45.
.PARAMETER Python
    Auszufuehrende Python-Datei. Standard: pythonw aus dem PATH.
.PARAMETER AtLogon
    Startet zusaetzlich bei jeder Anmeldung statt nur zur festen Uhrzeit.
#>
param(
    [string]$Time = "07:45",
    [string]$Python = "python",
    [switch]$AtLogon
)

$TaskName   = "MorningBriefing"
$ScriptPath = Join-Path $PSScriptRoot "main.py"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "main.py nicht gefunden: $ScriptPath"
    exit 1
}

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    Write-Error "Python nicht gefunden: $Python"
    exit 1
}

$action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$ScriptPath`" --html --open" `
    -WorkingDirectory $PSScriptRoot

$triggers = @(New-ScheduledTaskTrigger -Daily -At $Time)
if ($AtLogon) { $triggers += New-ScheduledTaskTrigger -AtLogOn }

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20) `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -RunOnlyIfNetworkAvailable

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Bestehende Aufgabe '$TaskName' entfernt."
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Description "Erstellt ein anonymisiertes Tagesbriefing aus Outlook, Teams und Autotask." | Out-Null

Write-Host "Aufgabe '$TaskName' registriert."
Write-Host "   Skript : $ScriptPath"
Write-Host "   Start  : taeglich $Time$(if ($AtLogon) { ' und bei Anmeldung' })"
Write-Host ""
Write-Host "Erster Testlauf:  $Python `"$ScriptPath`" --demo --no-ai"
