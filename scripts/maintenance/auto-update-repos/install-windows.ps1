#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Registers update-repos.ps1 as a Windows Task Scheduler job at logon.
.PARAMETER GithubFolder
    Path to your GitHub folder. Defaults to GITHUB_FOLDER env var or "$HOME\github".
#>
param(
    [string]$GithubFolder = $(
        if ($env:GITHUB_FOLDER) { $env:GITHUB_FOLDER }
        else { Join-Path $HOME "github" }
    )
)

$TaskName   = "AutoUpdateGitRepos"
$ScriptPath = Join-Path $PSScriptRoot "update-repos.ps1"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 1
}

$action  = New-ScheduledTaskAction `
    -Execute "pwsh.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -File `"$ScriptPath`" -GithubFolder `"$GithubFolder`""

# Fallback to Windows PowerShell if pwsh is not available
if (-not (Get-Command pwsh -ErrorAction SilentlyContinue)) {
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-NonInteractive -WindowStyle Hidden -File `"$ScriptPath`" -GithubFolder `"$GithubFolder`""
}

$trigger  = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -RunOnlyIfNetworkAvailable

# Remove existing task if present
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task '$TaskName'."
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Pulls the latest commits for all Git repos in $GithubFolder at every logon." `
    -RunLevel Highest | Out-Null

Write-Host "✅ Task '$TaskName' registered successfully."
Write-Host "   Script : $ScriptPath"
Write-Host "   Folder : $GithubFolder"
Write-Host "   Trigger: At every logon"
Write-Host ""
Write-Host "Logs will be written to: $HOME\.logs\auto-update-repos.log"
