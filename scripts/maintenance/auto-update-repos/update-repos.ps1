#Requires -Version 5.1
<#
.SYNOPSIS
    Updates Git repositories (including their submodules) in a specified folder.
.DESCRIPTION
    By default, only fast-forwards a branch when the working tree is clean and
    the branch is strictly behind its configured upstream. Local changes,
    untracked files, detached HEADs, missing upstreams, and divergent history
    are skipped. With Force, the upstream becomes the source of truth.
    Submodules are brought to the commit recorded by the parent repository
    (git submodule update --init --recursive) after the parent is up to date.
    Without Force, submodules with local changes or local commits are skipped.
    Environment: NETWORK_WAIT_SECONDS (default 60, 0 disables), NETWORK_CHECK_URL (default https://github.com).
.PARAMETER Force
    Makes the configured upstream the source of truth. Resets tracked files
    and removes untracked files and directories, but keeps ignored files.
.PARAMETER GithubFolder
    Path to the folder containing your Git repositories.
    Defaults to the GITHUB_FOLDER environment variable or "$HOME\github".
.PARAMETER Recurse
    Also scan nested folders for Git repositories.
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

$LogDir  = Join-Path $HOME ".logs"
$LogFile = Join-Path $LogDir "auto-update-repos.log"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

function Invoke-GitCommand {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = @(& git @Arguments 2>&1)
    [pscustomobject]@{
        Output   = $output
        ExitCode = $LASTEXITCODE
    }
}

function Get-CommandOutput {
    param([object[]]$Output)
    (($Output | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ }) -join " | ")
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Log "Git wurde nicht gefunden. Bitte Git installieren und erneut ausführen." "ERROR"
    exit 1
}

# Never block a boot/logon run on an interactive credential or host-key prompt.
$env:GIT_TERMINAL_PROMPT = "0"
if (-not $env:GIT_SSH_COMMAND -and -not (& git config --get core.sshCommand 2>$null)) {
    $env:GIT_SSH_COMMAND = "ssh -o BatchMode=yes -o ConnectTimeout=15"
}

# At boot/logon the network is often not up yet. Wait for it instead of failing every fetch.
function Wait-ForNetwork {
    $maxWait = if ($env:NETWORK_WAIT_SECONDS) { [int]$env:NETWORK_WAIT_SECONDS } else { 60 }
    $url = if ($env:NETWORK_CHECK_URL) { $env:NETWORK_CHECK_URL } else { "https://github.com" }
    $hostName = ([uri]$url).Host
    $waited = 0
    while ($maxWait -gt 0) {
        try {
            [void][System.Net.Dns]::GetHostEntry($hostName)
            return
        }
        catch { }
        if ($waited -ge $maxWait) {
            Write-Log "Netzwerk nach ${maxWait}s nicht erreichbar ($url). Fetch-Fehler sind möglich." "WARN"
            return
        }
        if ($waited -eq 0) { Write-Log "Warte auf Netzwerk ($url)..." }
        Start-Sleep -Seconds 3
        $waited += 3
    }
}

# Returns every folder below $Root that contains a .git directory. Submodules (.git file) are
# handled through their parent repository; node_modules and links are not descended into.
function Find-GitRepos {
    param([string]$Root)
    $children = @(Get-ChildItem -LiteralPath $Root -Directory -Force -ErrorAction SilentlyContinue)
    if ($children | Where-Object { $_.Name -eq ".git" }) {
        Get-Item -LiteralPath $Root
    }
    foreach ($child in $children) {
        if ($child.Name -in @(".git", "node_modules")) { continue }
        if ($child.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
        Find-GitRepos -Root $child.FullName
    }
}

# Brings the submodules of the current repository (cwd) to the commit recorded by the parent.
# Returns: 0 = ok / no submodules, 1 = skipped for safety, 2 = failed.
function Sync-Submodules {
    param([string]$RepoName)

    if (-not (Test-Path -LiteralPath ".gitmodules" -PathType Leaf)) { return 0 }

    $syncResult = Invoke-GitCommand @("submodule", "sync", "--recursive")
    if ($syncResult.ExitCode -ne 0) {
        Write-Log "[$RepoName] Submodule-Sync fehlgeschlagen: $(Get-CommandOutput $syncResult.Output)" "ERROR"
        return 2
    }

    if ($Force) {
        $updateResult = Invoke-GitCommand @("submodule", "update", "--init", "--recursive", "--force")
        if ($updateResult.ExitCode -ne 0) {
            Write-Log "[$RepoName] FORCE Submodule-Update fehlgeschlagen: $(Get-CommandOutput $updateResult.Output)" "ERROR"
            return 2
        }
        $cleanResult = Invoke-GitCommand @("submodule", "foreach", "--quiet", "--recursive", 'git clean -fd')
        if ($cleanResult.ExitCode -ne 0) {
            Write-Log "[$RepoName] FORCE Submodule-Clean fehlgeschlagen: $(Get-CommandOutput $cleanResult.Output)" "ERROR"
            return 2
        }
        Write-Log "[$RepoName] FORCE: Submodule auf den vom Parent gespeicherten Commit gesetzt." "WARN"
        return 0
    }

    # One line per initialized submodule: "<recorded sha> <path relative to this repo>"
    $listResult = Invoke-GitCommand @("submodule", "foreach", "--quiet", "--recursive", 'echo $sha1 $displaypath')
    if ($listResult.ExitCode -ne 0) {
        Write-Log "[$RepoName] Submodule konnten nicht aufgelistet werden: $(Get-CommandOutput $listResult.Output)" "ERROR"
        return 2
    }

    $dirty = @()
    $unsafe = @()
    foreach ($line in @($listResult.Output | ForEach-Object { $_.ToString().Trim() } | Where-Object { $_ })) {
        $parts = $line -split " ", 2
        $recorded = $parts[0]
        $subPath = $parts[1]

        $subStatus = Invoke-GitCommand @("-C", $subPath, "status", "--porcelain=v1", "--untracked-files=all")
        if ($subStatus.ExitCode -ne 0) {
            Write-Log "[$RepoName] Submodule-Status konnte nicht gelesen werden ($subPath): $(Get-CommandOutput $subStatus.Output)" "ERROR"
            return 2
        }
        if (Get-CommandOutput $subStatus.Output) {
            $dirty += $subPath
            continue
        }

        # Only move a submodule when its current commit is an ancestor of the recorded one (i.e. it is behind).
        $head = Get-CommandOutput (Invoke-GitCommand @("-C", $subPath, "rev-parse", "HEAD")).Output
        if ($head -eq $recorded) { continue }
        $known = Invoke-GitCommand @("-C", $subPath, "cat-file", "-e", ($recorded + '^{commit}'))
        if ($known.ExitCode -ne 0) { continue }
        $ancestor = Invoke-GitCommand @("-C", $subPath, "merge-base", "--is-ancestor", "HEAD", $recorded)
        if ($ancestor.ExitCode -ne 0) { $unsafe += $subPath }
    }

    if ($dirty.Count -gt 0) {
        Write-Log "[$RepoName] Submodule haben lokale Änderungen. Submodule-Update übersprungen: $($dirty -join ', ')" "WARN"
        return 1
    }
    if ($unsafe.Count -gt 0) {
        Write-Log "[$RepoName] Submodule mit lokalen Commits bzw. neuerem Stand als im Parent. Submodule-Update übersprungen: $($unsafe -join ', ')" "WARN"
        return 1
    }

    $updateResult = Invoke-GitCommand @("submodule", "update", "--init", "--recursive")
    if ($updateResult.ExitCode -ne 0) {
        Write-Log "[$RepoName] Submodule-Update fehlgeschlagen: $(Get-CommandOutput $updateResult.Output)" "ERROR"
        return 2
    }
    $updateOutput = Get-CommandOutput $updateResult.Output
    if ($updateOutput) {
        Write-Log "[$RepoName] Submodule aktualisiert: $updateOutput"
    }
    return 0
}

Wait-ForNetwork

if (-not (Test-Path $GithubFolder -PathType Container)) {
    Write-Log "GitHub-Ordner nicht gefunden: $GithubFolder" "ERROR"
    exit 1
}

if ($Force) {
    Write-Log "=== Starting FORCE repo update run (upstream is source of truth) ===" "WARN"
}
else {
    Write-Log "=== Starting safe repo update run ==="
}
Write-Log "Scanning: $GithubFolder$(if ($Recurse) { ' (recursive)' })"

if ($Recurse) {
    $repos = @(Find-GitRepos -Root $GithubFolder)
}
else {
    $repos = @(
        Get-ChildItem -Path $GithubFolder -Directory |
            Where-Object { Test-Path (Join-Path $_.FullName ".git") -PathType Container }
    )
}

$repos = @($repos | Sort-Object -Property FullName -Unique)

if ($repos.Count -eq 0) {
    Write-Log "Keine Git-Repositories in $GithubFolder gefunden." "WARN"
    exit 0
}

$updated = 0
$forced  = 0
$current = 0
$failed  = 0
$skipped = 0
$subSkipped = 0

foreach ($repo in $repos) {
    $repoPath = $repo.FullName
    $repoName = $repo.Name
    Write-Log "--- [$repoName] Processing..."

    Push-Location $repoPath

    try {
        $statusResult = Invoke-GitCommand @("status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=all")
        if ($statusResult.ExitCode -ne 0) {
            Write-Log "[$repoName] Git-Status konnte nicht gelesen werden: $(Get-CommandOutput $statusResult.Output)" "ERROR"
            $failed++
            continue
        }

        $hasLocalChanges = [bool](Get-CommandOutput $statusResult.Output)

        $branchResult = Invoke-GitCommand @("symbolic-ref", "--quiet", "--short", "HEAD")
        if ($branchResult.ExitCode -ne 0) {
            Write-Log "[$repoName] Detached HEAD erkannt. Übersprungen." "WARN"
            $skipped++
            continue
        }

        $branch = Get-CommandOutput $branchResult.Output
        $upstreamResult = Invoke-GitCommand @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if ($upstreamResult.ExitCode -ne 0) {
            Write-Log "[$repoName] Branch '$branch' hat keinen Upstream. Übersprungen." "WARN"
            $skipped++
            continue
        }

        $upstream = Get-CommandOutput $upstreamResult.Output
        $remoteResult = Invoke-GitCommand @("config", "--get", "branch.$branch.remote")
        if ($remoteResult.ExitCode -ne 0) {
            Write-Log "[$repoName] Remote für '$branch' konnte nicht bestimmt werden. Übersprungen." "WARN"
            $skipped++
            continue
        }

        $remote = Get-CommandOutput $remoteResult.Output
        $fetchResult = Invoke-GitCommand @("fetch", "--prune", $remote)
        if ($fetchResult.ExitCode -ne 0) {
            Write-Log "[$repoName] Fetch von '$remote' fehlgeschlagen: $(Get-CommandOutput $fetchResult.Output)" "ERROR"
            $failed++
            continue
        }

        $countResult = Invoke-GitCommand @("rev-list", "--left-right", "--count", "HEAD...$upstream")
        if ($countResult.ExitCode -ne 0) {
            Write-Log "[$repoName] Branch-Status konnte nicht bestimmt werden: $(Get-CommandOutput $countResult.Output)" "ERROR"
            $failed++
            continue
        }

        $countParts = (Get-CommandOutput $countResult.Output) -split "\s+"
        [int]$ahead = 0
        [int]$behind = 0
        if ($countParts.Count -ne 2 -or
            -not [int]::TryParse($countParts[0], [ref]$ahead) -or
            -not [int]::TryParse($countParts[1], [ref]$behind)) {
            Write-Log "[$repoName] Ungültiger Branch-Status: $(Get-CommandOutput $countResult.Output)" "ERROR"
            $failed++
            continue
        }

        if ($Force) {
            $cleanPreviewResult = Invoke-GitCommand @("clean", "-fdn")
            if ($cleanPreviewResult.ExitCode -ne 0) {
                Write-Log "[$repoName] Vorschau der lokalen Dateien konnte nicht erstellt werden: $(Get-CommandOutput $cleanPreviewResult.Output)" "ERROR"
                $failed++
                continue
            }

            $cleanPreview = Get-CommandOutput $cleanPreviewResult.Output
            if ($cleanPreview) {
                Write-Log "[$repoName] FORCE entfernt nicht getrackte Dateien/Ordner: $cleanPreview" "WARN"
            }

            $resetResult = Invoke-GitCommand @("reset", "--hard", $upstream)
            if ($resetResult.ExitCode -ne 0) {
                Write-Log "[$repoName] FORCE reset auf $upstream fehlgeschlagen: $(Get-CommandOutput $resetResult.Output)" "ERROR"
                $failed++
                continue
            }

            $cleanResult = Invoke-GitCommand @("clean", "-fd")
            if ($cleanResult.ExitCode -ne 0) {
                Write-Log "[$repoName] FORCE clean fehlgeschlagen: $(Get-CommandOutput $cleanResult.Output)" "ERROR"
                $failed++
                continue
            }

            Write-Log "[$repoName] FORCE synchronisiert: $branch -> $upstream. Ignorierte Dateien bleiben erhalten." "WARN"
            $subRc = Sync-Submodules -RepoName $repoName
            if ($subRc -eq 2) { $failed++ } else { $forced++ }
            continue
        }

        if ($hasLocalChanges) {
            if ($behind -gt 0) {
                Write-Log "[$repoName] Lokale Änderungen oder neue Dateien gefunden; Remote ist zusätzlich +$behind voraus. Übersprungen — nichts wird gestasht oder gelöscht." "WARN"
            }
            else {
                Write-Log "[$repoName] Lokale Änderungen oder neue Dateien gefunden. Übersprungen — nichts wird gestasht oder gelöscht." "WARN"
            }
            $skipped++
            continue
        }

        if ($ahead -gt 0 -and $behind -gt 0) {
            Write-Log "[$repoName] Branch ist divergiert (lokal +$ahead, Remote +$behind). Übersprungen — manueller Merge nötig." "WARN"
            $skipped++
            continue
        }

        if ($ahead -gt 0) {
            Write-Log "[$repoName] Lokale Commits vorhanden (+$ahead), Remote ist nicht voraus. Keine Änderung."
            $skipped++
            continue
        }

        if ($behind -eq 0) {
            Write-Log "[$repoName] Bereits aktuell."
            $subRc = Sync-Submodules -RepoName $repoName
            if ($subRc -eq 2) { $failed++ }
            else {
                $current++
                if ($subRc -eq 1) { $subSkipped++ }
            }
            continue
        }

        $preMergeStatusResult = Invoke-GitCommand @("status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=all")
        if ($preMergeStatusResult.ExitCode -ne 0) {
            Write-Log "[$repoName] Git-Status konnte vor dem Aktualisieren nicht gelesen werden: $(Get-CommandOutput $preMergeStatusResult.Output)" "ERROR"
            $failed++
            continue
        }

        if (Get-CommandOutput $preMergeStatusResult.Output) {
            Write-Log "[$repoName] Arbeitsverzeichnis wurde während des Laufs geändert. Übersprungen." "WARN"
            $skipped++
            continue
        }

        $mergeResult = Invoke-GitCommand @("merge", "--ff-only", $upstream)
        if ($mergeResult.ExitCode -eq 0) {
            Write-Log "[$repoName] Sicher aktualisiert: $branch -> $upstream ($(Get-CommandOutput $mergeResult.Output))"
            $subRc = Sync-Submodules -RepoName $repoName
            if ($subRc -eq 2) { $failed++ }
            else {
                $updated++
                if ($subRc -eq 1) { $subSkipped++ }
            }
        }
        else {
            Write-Log "[$repoName] Fast-forward fehlgeschlagen: $(Get-CommandOutput $mergeResult.Output)" "ERROR"
            $failed++
        }
    }
    catch {
        Write-Log "[$repoName] Unerwarteter Fehler: $_" "ERROR"
        $failed++
    }
    finally {
        Pop-Location
    }
}

Write-Log "=== Done. Updated: $updated | Forced: $forced | Current: $current | Failed: $failed | Skipped: $skipped | Submodule skipped: $subSkipped ==="
if ($failed -gt 0) { exit 1 }
exit 0
