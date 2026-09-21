#!/usr/bin/env bash
# install-linux.sh — Installs update-repos.sh as a systemd user service
# that runs once at every login session.
# Usage: ./install-linux.sh [/path/to/github/folder] [--recurse] [--force]

set -euo pipefail

GITHUB_FOLDER="${GITHUB_FOLDER:-$HOME/github}"
UPDATER_ARGS=()

if [[ $# -gt 0 && "$1" != -* ]]; then
    GITHUB_FOLDER="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --recurse|--recursive|-r) UPDATER_ARGS+=(--recurse) ;;
        --force|-f)               UPDATER_ARGS+=(--force) ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            echo "Usage: $0 [/path/to/github/folder] [--recurse] [--force]" >&2
            exit 2
            ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/update-repos.sh"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/auto-update-repos.service"

if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "ERROR: Script not found: $SCRIPT_PATH"
    exit 1
fi

chmod +x "$SCRIPT_PATH"
mkdir -p "$SERVICE_DIR" "$HOME/.logs"

# The script writes its own log file (~/.logs/auto-update-repos.log); systemd captures stdout in the journal.
# User units cannot order against network-online.target, so the script itself waits for the network.
cat > "$SERVICE_FILE" <<UNIT
[Unit]
Description=Auto-update all Git repositories (including submodules) in $GITHUB_FOLDER

[Service]
Type=oneshot
TimeoutStartSec=10min
ExecStart=/usr/bin/env bash "$SCRIPT_PATH" "$GITHUB_FOLDER" ${UPDATER_ARGS[*]:-}

[Install]
WantedBy=default.target
UNIT

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable auto-update-repos.service

echo "✅ systemd user service installed."
echo "   Service : $SERVICE_FILE"
echo "   Folder  : $GITHUB_FOLDER"
echo "   Options : ${UPDATER_ARGS[*]:-(none)}"
echo "   Trigger : At every user login session"
echo ""
echo "Logs: $HOME/.logs/auto-update-repos.log  (journalctl --user -u auto-update-repos.service)"
echo ""
echo "Manual run: systemctl --user start auto-update-repos.service"
