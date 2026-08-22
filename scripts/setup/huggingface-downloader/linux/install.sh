#!/usr/bin/env bash
# Installiert HuggingFaceModelDownloader (hfdownloader) auf Linux inkl.
# .desktop-Eintrag "HuggingFace Downloader" (in GNOME/KDE-Anwendungssuche
# auffindbar), der die WebUI im Hintergrund startet (kein Terminalfenster)
# und den Standardbrowser öffnet.
#
# Nutzung:
#   bash install.sh
#   MODELS_ROOT=/pfad/zu/modellen PORT=8080 FORCE=1 bash install.sh
#
set -euo pipefail

REPO="bodaay/HuggingFaceModelDownloader"
MODELS_ROOT="${MODELS_ROOT:-$HOME/lmstudio-models}"
PORT="${PORT:-8080}"
FORCE="${FORCE:-0}"

INSTALL_DIR="$HOME/.local/share/HFDownloader"
BIN_PATH="$INSTALL_DIR/hfdownloader"
VERSION_FILE="$INSTALL_DIR/version.txt"
LAUNCH_SCRIPT="$INSTALL_DIR/launch.sh"
BIN_SYMLINK_DIR="$HOME/.local/bin"
BIN_SYMLINK="$BIN_SYMLINK_DIR/hfdownloader"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/huggingface-downloader.desktop"

log()  { printf '\033[36m[hfdownloader]\033[0m %s\n' "$1"; }
ok()   { printf '\033[32m[hfdownloader]\033[0m %s\n' "$1"; }
warn() { printf '\033[33m[hfdownloader]\033[0m %s\n' "$1"; }

mkdir -p "$INSTALL_DIR" "$MODELS_ROOT" "$BIN_SYMLINK_DIR" "$DESKTOP_DIR"

# --- Architektur erkennen ---
ARCH_RAW="$(uname -m)"
case "$ARCH_RAW" in
    x86_64|amd64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) echo "Nicht unterstützte Architektur: $ARCH_RAW"; exit 1 ;;
esac

# --- Aktuelle Release-Version abfragen ---
log "Prüfe aktuelle Release-Version von $REPO ..."
LATEST_JSON="$(curl -fsSL -H "User-Agent: hfdownloader-installer" "https://api.github.com/repos/$REPO/releases/latest")"
TAG="$(printf '%s' "$LATEST_JSON" | grep -m1 '"tag_name"' | sed -E 's/.*"tag_name":[[:space:]]*"([^"]+)".*/\1/')"
if [ -z "$TAG" ]; then
    echo "Konnte Release-Tag nicht ermitteln."
    exit 1
fi

NEEDS_DOWNLOAD=1
if [ -f "$BIN_PATH" ] && [ -f "$VERSION_FILE" ] && [ "$FORCE" != "1" ]; then
    INSTALLED_TAG="$(cat "$VERSION_FILE")"
    if [ "$INSTALLED_TAG" = "$TAG" ]; then
        NEEDS_DOWNLOAD=0
        ok "hfdownloader ist bereits aktuell (Version $TAG), Download übersprungen."
    fi
fi

if [ "$NEEDS_DOWNLOAD" = "1" ]; then
    ASSET_NAME="hfdownloader_linux_${ARCH}_${TAG}"
    URL="https://github.com/$REPO/releases/download/$TAG/$ASSET_NAME"
    log "Lade hfdownloader $TAG ($ARCH) herunter -> $BIN_PATH"
    curl -fsSL "$URL" -o "$BIN_PATH"
    chmod +x "$BIN_PATH"
    echo "$TAG" > "$VERSION_FILE"
    ok "Installation abgeschlossen: $BIN_PATH"
fi

# --- Symlink für direkten CLI-Zugriff (idempotent) ---
ln -sf "$BIN_PATH" "$BIN_SYMLINK"

# --- Start-Skript erzeugen (Port-Check, Hintergrundstart, Browser-Open) ---
cat > "$LAUNCH_SCRIPT" <<LAUNCHER
#!/usr/bin/env bash
# Automatisch generiert von install.sh - nicht manuell bearbeiten.
set -uo pipefail

EXE_PATH="$BIN_PATH"
MODELS_ROOT="$MODELS_ROOT"
BASE_PORT="$PORT"
STATE_DIR="$INSTALL_DIR"
PID_FILE="\$STATE_DIR/server.pid"
PORT_FILE="\$STATE_DIR/server.port"

is_port_open() {
    (exec 3<>"/dev/tcp/127.0.0.1/\$1") 2>/dev/null
    local result=\$?
    exec 3>&- 2>/dev/null || true
    return \$result
}

get_running_port() {
    [ -f "\$PORT_FILE" ] || return 1
    local p
    p="\$(cat "\$PORT_FILE" 2>/dev/null)"
    [ -n "\$p" ] || return 1
    is_port_open "\$p" || return 1
    if [ -f "\$PID_FILE" ]; then
        local spid
        spid="\$(cat "\$PID_FILE" 2>/dev/null)"
        if [ -n "\$spid" ] && ! kill -0 "\$spid" 2>/dev/null; then
            return 1
        fi
    fi
    echo "\$p"
    return 0
}

open_browser() {
    local url="\$1"
    if command -v xdg-open >/dev/null 2>&1; then
        nohup xdg-open "\$url" >/dev/null 2>&1 &
    elif [ -n "\${BROWSER:-}" ]; then
        nohup "\$BROWSER" "\$url" >/dev/null 2>&1 &
    else
        echo "Bitte öffne \$url manuell im Browser."
    fi
}

RUNNING_PORT="\$(get_running_port || true)"
if [ -n "\$RUNNING_PORT" ]; then
    open_browser "http://localhost:\$RUNNING_PORT"
    exit 0
fi

PORT_TO_USE="\$BASE_PORT"
while is_port_open "\$PORT_TO_USE"; do
    PORT_TO_USE=\$((PORT_TO_USE + 1))
done

nohup "\$EXE_PATH" serve --local-dir "\$MODELS_ROOT" --port "\$PORT_TO_USE" >/tmp/hfdownloader.log 2>&1 &
SERVER_PID=\$!
disown "\$SERVER_PID" 2>/dev/null || true
echo "\$SERVER_PID" > "\$PID_FILE"
echo "\$PORT_TO_USE" > "\$PORT_FILE"

DEADLINE=\$((SECONDS + 5))
while [ \$SECONDS -lt \$DEADLINE ]; do
    if is_port_open "\$PORT_TO_USE"; then
        break
    fi
    sleep 0.2
done

open_browser "http://localhost:\$PORT_TO_USE"
LAUNCHER
chmod +x "$LAUNCH_SCRIPT"
ok "Start-Skript geschrieben: $LAUNCH_SCRIPT"

# --- .desktop-Datei erzeugen (idempotent: wird überschrieben) ---
cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=HuggingFace Downloader
Comment=Startet die HuggingFace Model Downloader WebUI im Hintergrund
Exec=$LAUNCH_SCRIPT
Terminal=false
Categories=Utility;Network;
Icon=folder-download
StartupNotify=false
DESKTOP
chmod +x "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

ok "Anwendungseintrag erstellt: $DESKTOP_FILE"
echo ""
ok "Fertig! Suche in der Anwendungssuche nach 'HuggingFace Downloader' und starte per Klick."
log "Modelle werden abgelegt in: $MODELS_ROOT"
log "Bevorzugter Port: $PORT (bei Belegung wird automatisch der nächste freie Port gewählt)"
