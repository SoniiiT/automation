#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Registers update-repos.ps1 as a Windows Task Scheduler job at logon.
.DESCRIPTION
    By default, the updater only fast-forwards clean repositories and never stashes or deletes local work.
    With Force, it resets tracked files and deletes untracked files at every logon.
.PARAMETER GithubFolder
    Path to your GitHub folder. Defaults to GITHUB_FOLDER env var or "$HOME\github".
.PARAMETER Recurse
    Also scan nested folders for Git repositories.
.PARAMETER Force
    Passes -Force to the updater. This discards tracked and untracked local work at every logon.
#>
param(
    [string]$GithubFolder = $(
        if ($env:GITHUB_FOLDER) { $env:GITHUB_FOLDER }
        else { Join-Path $HOME "github" }
    ),
    [Alias("Recursive")]
    [switch]$Recurse,
    [switch]$Force
)

$TaskName   = "AutoUpdateGitRepos"
$ScriptPath = Join-Path $PSScriptRoot "update-repos.ps1"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 1
}

$updaterArguments = "-NonInteractive -WindowStyle Hidden -File `"$ScriptPath`" -GithubFolder `"$GithubFolder`""
if ($Recurse) { $updaterArguments += " -Recurse" }
if ($Force) { $updaterArguments += " -Force" }

$action  = New-ScheduledTaskAction `
    -Execute "pwsh.exe" `
    -Argument $updaterArguments

# Fallback to Windows PowerShell if pwsh is not available
if (-not (Get-Command pwsh -ErrorAction SilentlyContinue)) {
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument $updaterArguments
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
    -Description "Updates Git repos in $GithubFolder at every logon; Force: $Force." `
    -RunLevel Highest | Out-Null

Write-Host "✅ Task '$TaskName' registered successfully."
Write-Host "   Script : $ScriptPath"
Write-Host "   Folder : $GithubFolder"
Write-Host "   Trigger: At every logon"
Write-Host "   Recurse: $Recurse"
Write-Host "   Force  : $Force"
if ($Force) {
    Write-Warning "Force mode discards tracked changes and deletes untracked files at every logon. Ignored files remain."
}
Write-Host ""
Write-Host "Logs will be written to: $HOME\.logs\auto-update-repos.log"
