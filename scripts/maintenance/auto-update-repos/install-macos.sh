#!/usr/bin/env bash
# install-macos.sh — Installs update-repos.sh as a launchd agent
# that runs once at every login.
# Usage: ./install-macos.sh [/path/to/github/folder]

set -euo pipefail

GITHUB_FOLDER="${1:-${GITHUB_FOLDER:-$HOME/github}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/update-repos.sh"
PLIST_LABEL="com.user.auto-update-repos"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$LAUNCH_AGENTS_DIR/$PLIST_LABEL.plist"
LOG_DIR="$HOME/.logs"

if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "ERROR: Script not found: $SCRIPT_PATH"
    exit 1
fi

chmod +x "$SCRIPT_PATH"
mkdir -p "$LAUNCH_AGENTS_DIR" "$LOG_DIR"

cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/env</string>
        <string>bash</string>
        <string>$SCRIPT_PATH</string>
        <string>$GITHUB_FOLDER</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$LOG_DIR/auto-update-repos.log</string>

    <key>StandardErrorPath</key>
    <string>$LOG_DIR/auto-update-repos.log</string>

    <!-- Wait for network before running -->
    <key>NetworkState</key>
    <true/>
</dict>
</plist>
EOF

# Unload existing agent if running
launchctl unload "$PLIST_FILE" 2>/dev/null || true

# Load the new agent
launchctl load "$PLIST_FILE"

echo "✅ launchd agent installed."
echo "   Plist  : $PLIST_FILE"
echo "   Folder : $GITHUB_FOLDER"
echo "   Trigger: At every login (RunAtLoad)"
echo ""
echo "Logs: $LOG_DIR/auto-update-repos.log"
echo ""
echo "Manual run: launchctl start $PLIST_LABEL"
