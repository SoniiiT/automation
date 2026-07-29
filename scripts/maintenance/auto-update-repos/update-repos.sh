#!/usr/bin/env bash
# update-repos.sh — Safely fast-forwards or forcibly synchronizes Git repositories.
# Usage: ./update-repos.sh [/path/to/github/folder] [--recurse|--recursive] [--force]
# Falls back to $GITHUB_FOLDER or "$HOME/github".

set -euo pipefail

GITHUB_FOLDER="${GITHUB_FOLDER:-$HOME/github}"
RECURSE=false
FORCE=false

if [[ $# -gt 0 && "$1" != -* ]]; then
    GITHUB_FOLDER="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --recurse|--recursive|-r)
            RECURSE=true
            ;;
        --force|-f)
            FORCE=true
            ;;
        --help|-h)
            printf 'Usage: %s [/path/to/github/folder] [--recurse|--recursive] [--force]\n' "$0"
            exit 0
            ;;
        *)
            printf 'ERROR: Unknown option: %s\n' "$1" >&2
            exit 2
            ;;
    esac
    shift
done

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

if ! command -v git >/dev/null 2>&1; then
    log "Git wurde nicht gefunden. Bitte Git installieren und erneut ausführen." "ERROR"
    exit 1
fi

if $FORCE; then
    log "=== Starting FORCE repo update run (upstream is source of truth) ===" "WARN"
else
    log "=== Starting safe repo update run ==="
fi
if $RECURSE; then
    log "Scanning: $GITHUB_FOLDER (recursive)"
else
    log "Scanning: $GITHUB_FOLDER"
fi

updated=0
forced=0
current=0
failed=0
skipped=0
found=0

process_repo() {
    local repo_path="$1"
    local repo_name="${repo_path%/}"
    repo_name="${repo_name##*/}"
    local branch upstream remote status_output fetch_output count_output pre_merge_status
    local clean_preview reset_output clean_output
    local ahead behind
    local has_local_changes=false

    found=$((found + 1))
    log "--- [$repo_name] Processing..."

    if ! pushd "$repo_path" >/dev/null; then
        log "[$repo_name] Repository konnte nicht geöffnet werden." "ERROR"
        failed=$((failed + 1))
        return
    fi

    if ! status_output=$(git status --porcelain=v1 --untracked-files=all 2>&1); then
        log "[$repo_name] Git-Status konnte nicht gelesen werden: $status_output" "ERROR"
        failed=$((failed + 1))
        popd >/dev/null
        return
    fi

    if [[ -n "$status_output" ]]; then
        has_local_changes=true
    fi

    if ! branch=$(git symbolic-ref --quiet --short HEAD 2>&1); then
        log "[$repo_name] Detached HEAD erkannt. Übersprungen." "WARN"
        skipped=$((skipped + 1))
        popd >/dev/null
        return
    fi

    if ! upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>&1); then
        log "[$repo_name] Branch '$branch' hat keinen Upstream. Übersprungen." "WARN"
        skipped=$((skipped + 1))
        popd >/dev/null
        return
    fi

    if ! remote=$(git config --get "branch.$branch.remote" 2>&1); then
        log "[$repo_name] Remote für '$branch' konnte nicht bestimmt werden. Übersprungen." "WARN"
        skipped=$((skipped + 1))
        popd >/dev/null
        return
    fi

    if ! fetch_output=$(git fetch --prune "$remote" 2>&1); then
        log "[$repo_name] Fetch von '$remote' fehlgeschlagen: $fetch_output" "ERROR"
        failed=$((failed + 1))
        popd >/dev/null
        return
    fi

    if ! count_output=$(git rev-list --left-right --count "HEAD...$upstream" 2>&1); then
        log "[$repo_name] Branch-Status konnte nicht bestimmt werden: $count_output" "ERROR"
        failed=$((failed + 1))
        popd >/dev/null
        return
    fi

    read -r ahead behind <<< "$count_output"
    if [[ ! "$ahead" =~ ^[0-9]+$ || ! "$behind" =~ ^[0-9]+$ ]]; then
        log "[$repo_name] Ungültiger Branch-Status: $count_output" "ERROR"
        failed=$((failed + 1))
        popd >/dev/null
        return
    fi

    if $FORCE; then
        if ! clean_preview=$(git clean -fdn 2>&1); then
            log "[$repo_name] Vorschau der lokalen Dateien konnte nicht erstellt werden: $clean_preview" "ERROR"
            failed=$((failed + 1))
            popd >/dev/null
            return
        fi

        if [[ -n "$clean_preview" ]]; then
            log "[$repo_name] FORCE entfernt nicht getrackte Dateien/Ordner: $clean_preview" "WARN"
        fi

        if ! reset_output=$(git reset --hard "$upstream" 2>&1); then
            log "[$repo_name] FORCE reset auf $upstream fehlgeschlagen: $reset_output" "ERROR"
            failed=$((failed + 1))
            popd >/dev/null
            return
        fi

        if ! clean_output=$(git clean -fd 2>&1); then
            log "[$repo_name] FORCE clean fehlgeschlagen: $clean_output" "ERROR"
            failed=$((failed + 1))
            popd >/dev/null
            return
        fi

        log "[$repo_name] FORCE synchronisiert: $branch -> $upstream. Ignorierte Dateien bleiben erhalten." "WARN"
        forced=$((forced + 1))
        popd >/dev/null
        return
    fi

    if $has_local_changes; then
        if (( behind > 0 )); then
            log "[$repo_name] Lokale Änderungen oder neue Dateien gefunden; Remote ist zusätzlich +$behind voraus. Übersprungen — nichts wird gestasht oder gelöscht." "WARN"
        else
            log "[$repo_name] Lokale Änderungen oder neue Dateien gefunden. Übersprungen — nichts wird gestasht oder gelöscht." "WARN"
        fi
        skipped=$((skipped + 1))
        popd >/dev/null
        return
    fi

    if (( ahead > 0 && behind > 0 )); then
        log "[$repo_name] Branch ist divergiert (lokal +$ahead, Remote +$behind). Übersprungen — manueller Merge nötig." "WARN"
        skipped=$((skipped + 1))
        popd >/dev/null
        return
    fi

    if (( ahead > 0 )); then
        log "[$repo_name] Lokale Commits vorhanden (+$ahead), Remote ist nicht voraus. Keine Änderung."
        skipped=$((skipped + 1))
        popd >/dev/null
        return
    fi

    if (( behind == 0 )); then
        log "[$repo_name] Bereits aktuell."
        current=$((current + 1))
        popd >/dev/null
        return
    fi

    if ! pre_merge_status=$(git status --porcelain=v1 --untracked-files=all 2>&1); then
        log "[$repo_name] Git-Status konnte vor dem Aktualisieren nicht gelesen werden: $pre_merge_status" "ERROR"
        failed=$((failed + 1))
        popd >/dev/null
        return
    fi

    if [[ -n "$pre_merge_status" ]]; then
        log "[$repo_name] Arbeitsverzeichnis wurde während des Laufs geändert. Übersprungen." "WARN"
        skipped=$((skipped + 1))
        popd >/dev/null
        return
    fi

    if merge_output=$(git merge --ff-only "$upstream" 2>&1); then
        log "[$repo_name] Sicher aktualisiert: $branch -> $upstream ($merge_output)"
        updated=$((updated + 1))
    else
        log "[$repo_name] Fast-forward fehlgeschlagen: $merge_output" "ERROR"
        failed=$((failed + 1))
    fi

    popd >/dev/null
}

if $RECURSE; then
    while IFS= read -r -d '' git_dir; do
        process_repo "$(dirname "$git_dir")"
    done < <(find "$GITHUB_FOLDER" -type d -name .git -prune -print0)
else
    for repo_path in "$GITHUB_FOLDER"/*/; do
        [[ -d "$repo_path/.git" ]] || continue
        process_repo "$repo_path"
    done
fi

if (( found == 0 )); then
    log "Keine Git-Repositories in $GITHUB_FOLDER gefunden." "WARN"
fi

log "=== Done. Updated: $updated | Forced: $forced | Current: $current | Failed: $failed | Skipped: $skipped ==="
if (( failed > 0 )); then
    exit 1
fi
exit 0
