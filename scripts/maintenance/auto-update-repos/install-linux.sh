#!/usr/bin/env bash
# install-linux.sh — Installs update-repos.sh as a systemd user service
# that runs once at every login session.
# Usage: ./install-linux.sh [/path/to/github/folder]

set -euo pipefail

GITHUB_FOLDER="${1:-${GITHUB_FOLDER:-$HOME/github}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/update-repos.sh"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/auto-update-repos.service"

if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "ERROR: Script not found: $SCRIPT_PATH"
    exit 1
fi

chmod +x "$SCRIPT_PATH"
mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Auto-update all Git repositories in $GITHUB_FOLDER
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/env bash $SCRIPT_PATH $GITHUB_FOLDER
Environment=HOME=$HOME
StandardOutput=append:$HOME/.logs/auto-update-repos.log
StandardError=append:$HOME/.logs/auto-update-repos.log

[Install]
WantedBy=default.target
EOF

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable auto-update-repos.service

echo "✅ systemd user service installed."
echo "   Service : $SERVICE_FILE"
echo "   Folder  : $GITHUB_FOLDER"
echo "   Trigger : At every user login session"
echo ""
echo "Logs: $HOME/.logs/auto-update-repos.log"
echo ""
echo "Manual run: systemctl --user start auto-update-repos.service"
