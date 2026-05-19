#Requires -Version 5.1
<#
.SYNOPSIS
    Updates all Git repositories in a specified folder.
.DESCRIPTION
    Iterates over all subdirectories in $GithubFolder, stashes local changes,
    pulls the latest from the current branch's remote, then pops the stash.
    Results are written to a log file.
.PARAMETER GithubFolder
    Path to the folder containing your Git repositories.
    Defaults to the GITHUB_FOLDER environment variable or "$HOME\github".
#>
param(
    [string]$GithubFolder = $(
        if ($env:GITHUB_FOLDER) { $env:GITHUB_FOLDER }
        else { Join-Path $HOME "github" }
    )
)

$LogDir  = Join-Path $HOME ".logs"
$LogFile = Join-Path $LogDir "auto-update-repos.log"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

if (-not (Test-Path $GithubFolder)) {
    Write-Log "GitHub folder not found: $GithubFolder" "ERROR"
    exit 1
}

Write-Log "=== Starting repo update run ==="
Write-Log "Scanning: $GithubFolder"

$repos = Get-ChildItem -Path $GithubFolder -Directory |
         Where-Object { Test-Path (Join-Path $_.FullName ".git") }

if ($repos.Count -eq 0) {
    Write-Log "No Git repositories found in $GithubFolder" "WARN"
    exit 0
}

$success = 0
$failed  = 0
$skipped = 0

foreach ($repo in $repos) {
    $repoPath = $repo.FullName
    $repoName = $repo.Name
    Write-Log "--- [$repoName] Processing..."

    Push-Location $repoPath

    try {
        # Check for network connectivity to remote
        $remoteUrl = git remote get-url origin 2>$null
        if (-not $remoteUrl) {
            Write-Log "[$repoName] No remote 'origin' found, skipping." "WARN"
            $skipped++
            continue
        }

        # Stash local changes (including untracked files)
        $statusOutput = git status --porcelain 2>&1
        $hasChanges   = $statusOutput -ne $null -and $statusOutput.Length -gt 0

        if ($hasChanges) {
            Write-Log "[$repoName] Local changes detected — stashing..."
            git stash push --include-untracked -m "auto-update-repos stash $(Get-Date -Format 'yyyyMMdd-HHmmss')" 2>&1 | Out-Null
        }

        # Pull latest on current branch
        $pullOutput = git pull --ff-only 2>&1
        Write-Log "[$repoName] pull: $($pullOutput -join ' | ')"

        # Restore stash if we stashed
        if ($hasChanges) {
            $stashList = git stash list 2>&1
            if ($stashList -match "auto-update-repos stash") {
                Write-Log "[$repoName] Restoring stash..."
                $popOutput = git stash pop 2>&1
                Write-Log "[$repoName] stash pop: $($popOutput -join ' | ')"
            }
        }

        $success++
    }
    catch {
        Write-Log "[$repoName] Unexpected error: $_" "ERROR"
        $failed++
    }
    finally {
        Pop-Location
    }
}

Write-Log "=== Done. Success: $success | Failed: $failed | Skipped: $skipped ==="
