#!/usr/bin/env bash
# update-repos.sh — Updates all Git repositories in a specified folder.
# Usage: ./update-repos.sh [/path/to/github/folder]
# Falls back to $GITHUB_FOLDER env var or "$HOME/github".

set -euo pipefail

GITHUB_FOLDER="${1:-${GITHUB_FOLDER:-$HOME/github}}"
LOG_DIR="$HOME/.logs"
LOG_FILE="$LOG_DIR/auto-update-repos.log"

mkdir -p "$LOG_DIR"

log() {
    local level="${2:-INFO}"
    local line="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $1"
    echo "$line" | tee -a "$LOG_FILE"
}

if [[ ! -d "$GITHUB_FOLDER" ]]; then
    log "GitHub folder not found: $GITHUB_FOLDER" "ERROR"
    exit 1
fi

log "=== Starting repo update run ==="
log "Scanning: $GITHUB_FOLDER"

success=0
failed=0
skipped=0

for repo_path in "$GITHUB_FOLDER"/*/; do
    [[ -d "$repo_path/.git" ]] || continue
    repo_name="$(basename "$repo_path")"

    log "--- [$repo_name] Processing..."

    pushd "$repo_path" > /dev/null

    # Verify remote exists
    if ! remote_url=$(git remote get-url origin 2>/dev/null); then
        log "[$repo_name] No remote 'origin' found, skipping." "WARN"
        ((skipped++)) || true
        popd > /dev/null
        continue
    fi

    # Stash local changes
    status_output=$(git status --porcelain 2>&1)
    has_changes=false
    if [[ -n "$status_output" ]]; then
        has_changes=true
        log "[$repo_name] Local changes detected — stashing..."
        git stash push --include-untracked \
            -m "auto-update-repos stash $(date '+%Y%m%d-%H%M%S')" >> "$LOG_FILE" 2>&1
    fi

    # Pull latest
    if pull_output=$(git pull --ff-only 2>&1); then
        log "[$repo_name] pull: $pull_output"
        ((success++)) || true
    else
        log "[$repo_name] pull failed: $pull_output" "ERROR"
        ((failed++)) || true
    fi

    # Restore stash
    if $has_changes; then
        if git stash list 2>/dev/null | grep -q "auto-update-repos stash"; then
            log "[$repo_name] Restoring stash..."
            pop_output=$(git stash pop 2>&1) || true
            log "[$repo_name] stash pop: $pop_output"
        fi
    fi

    popd > /dev/null
done

log "=== Done. Success: $success | Failed: $failed | Skipped: $skipped ==="
