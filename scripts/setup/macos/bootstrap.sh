#!/usr/bin/env bash
# Bootstrap-Skript für ein neues Arbeits-MacBook.
#
# Läuft NACH der firmeneigenen MDM-/Jamf-Einrichtung als persönliches
# Zusatz-Setup. Es rührt keine Profile, Zertifikate oder von der IT
# verwalteten Einstellungen an, sondern installiert nur zusätzliche
# Apps/Tools und setzt persönliche macOS-Komfort-Einstellungen.
#
# Nutzung:
#   cd scripts/setup/macos
#   bash bootstrap.sh
#
# Das Skript ist idempotent: mehrfaches Ausführen ist sicher und
# überspringt bereits erledigte Schritte.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BREWFILE="$SCRIPT_DIR/Brewfile"
DEV_DIR="$HOME/Development"
COMPUTER_NAME="ITC-MB-2603-01"

# --- Repos, die unter $DEV_DIR ausgecheckt werden sollen -------------------
# Einfach weitere Zeilen ergänzen, jeweils "ziel-ordnername|owner/repo".
# Beispiel: "automation|SoniiiT/automation"
# Wird per "gh repo clone" geklont, funktioniert dadurch auch bei privaten
# Repos ohne eigenes SSH-Key-Setup (nutzt die gh-Anmeldung aus Schritt 6).
# Leer lassen/Zeilen löschen, wenn (noch) keine Repos geklont werden sollen.
REPOS=(
    "automation|SoniiiT/automation"
    "docker|SoniiiT/docker"
    "terraform|SoniiiT/terraform"
    "docker-container-template|SoniiiT/docker-container-template"
    "websites|SoniiiT/websites"
    "ai-bootcamp|SoniiiT/ai-bootcamp"
    "notes-n-docs|SoniiiT/notes-n-docs"
    "kubernetes-container-template|SoniiiT/kubernetes-container-template"
    "k3s-soniiit-prod-1|SoniiiT/k3s-soniiit-prod-1"
    "artifact-hub|SoniiiT/artifact-hub"
    "bot-hub|SoniiiT/bot-hub"
    "packer|SoniiiT/packer"
    "itc-k3s|itcares/itc-k3s"
    "itc-api-nx-adm-ui|itcares/itc-api-nx-adm-ui"
    "itc-msp-helpdesk-intelligence|itcares/itc-msp-helpdesk-intelligence"
    "itc-scripts-and-templates|itcares/itc-scripts-and-templates"
    "ITcares-API-2023|itcares/ITcares-API-2023"
    "claude-code|itcares/claude-code"
    "itc-api-nx-srvc-cevs|itcares/itc-api-nx-srvc-cevs"
    "itc-api-nx-srvc-lmc|itcares/itc-api-nx-srvc-lmc"
    "itc-api-nx-srvc-imi|itcares/itc-api-nx-srvc-imi"
    "itc-api-nx-srvc-atsk|itcares/itc-api-nx-srvc-atsk"
    "itc-api-nx-srvc-mlstr|itcares/itc-api-nx-srvc-mlstr"
    "itc-api-nx-srvc-sms|itcares/itc-api-nx-srvc-sms"
    "itc-api-nx-srvc-rmm|itcares/itc-api-nx-srvc-rmm"
    "itc-api-nx-srvc-pbx|itcares/itc-api-nx-srvc-pbx"
    "itc-api-nx-srvc-ms365|itcares/itc-api-nx-srvc-ms365"
    "itc-api-nx-srvc-itgl|itcares/itc-api-nx-srvc-itgl"
    "itc-api-nx-srvc-hrm|itcares/itc-api-nx-srvc-hrm"
    # "ordnername|owner/repo"
)

log()  { printf '\033[36m[bootstrap]\033[0m %s\n' "$1"; }
ok()   { printf '\033[32m[bootstrap]\033[0m %s\n' "$1"; }
warn() { printf '\033[33m[bootstrap]\033[0m %s\n' "$1"; }
err()  { printf '\033[31m[bootstrap]\033[0m %s\n' "$1" >&2; }

if [[ "$(uname -s)" != "Darwin" ]]; then
    err "Dieses Skript ist nur für macOS gedacht."
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Xcode Command Line Tools (Voraussetzung für Homebrew & Git)
# ---------------------------------------------------------------------------
if ! xcode-select -p >/dev/null 2>&1; then
    log "Installiere Xcode Command Line Tools ..."
    xcode-select --install || true
    warn "Bitte den Dialog für die Command Line Tools abschließen und dieses Skript danach erneut ausführen."
    exit 0
else
    ok "Xcode Command Line Tools bereits installiert."
fi

# ---------------------------------------------------------------------------
# 2. Homebrew installieren/aktualisieren
# ---------------------------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
    log "Installiere Homebrew ..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    if [[ -x /opt/homebrew/bin/brew ]]; then
        BREW_PREFIX="/opt/homebrew"
    else
        BREW_PREFIX="/usr/local"
    fi
    eval "$("$BREW_PREFIX/bin/brew" shellenv)"
else
    ok "Homebrew bereits installiert."
fi

# Analytics/Telemetrie von Homebrew deaktivieren (persistent in HOMEBREW_NO_ANALYTICS)
brew analytics off >/dev/null 2>&1 || true

log "Aktualisiere Homebrew ..."
brew update

# ---------------------------------------------------------------------------
# 3. Apps & CLI-Tools über das Brewfile installieren
# ---------------------------------------------------------------------------
log "Installiere Apps & Tools aus Brewfile ..."

EFFECTIVE_BREWFILE="$BREWFILE"
if [[ "$(uname -m)" != "arm64" ]]; then
    warn "Intel-Mac erkannt: 'lm-studio-bionic' erfordert Apple Silicon und wird übersprungen."
    EFFECTIVE_BREWFILE="$(mktemp)"
    grep -v '^cask "lm-studio-bionic"' "$BREWFILE" > "$EFFECTIVE_BREWFILE"
fi

brew bundle --file="$EFFECTIVE_BREWFILE" || warn "Mindestens eine Zeile aus dem Brewfile ist fehlgeschlagen (z. B. 'Command X' ohne App-Store-Anmeldung). Restliche Installationen liefen trotzdem durch; führe 'brew bundle --file=$BREWFILE' später erneut aus, um Fehlendes nachzuholen."
[[ "$EFFECTIVE_BREWFILE" != "$BREWFILE" ]] && rm -f "$EFFECTIVE_BREWFILE"

# ---------------------------------------------------------------------------
# 4. nvm & pyenv in die Shell-Konfiguration einhängen, aktuelle Versionen holen
# ---------------------------------------------------------------------------
ZSHRC="$HOME/.zshrc"
touch "$ZSHRC"

add_once() {
    local marker="$1"
    local block="$2"
    if ! grep -qF "$marker" "$ZSHRC" 2>/dev/null; then
        printf '\n%s\n' "$block" >> "$ZSHRC"
    fi
}

BREW_PREFIX="$(brew --prefix)"

add_once "# >>> nvm init >>>" "# >>> nvm init >>>
export NVM_DIR=\"\$HOME/.nvm\"
[ -s \"$BREW_PREFIX/opt/nvm/nvm.sh\" ] && \. \"$BREW_PREFIX/opt/nvm/nvm.sh\"
[ -s \"$BREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm\" ] && \. \"$BREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm\"
# <<< nvm init <<<"

add_once "# >>> pyenv init >>>" "# >>> pyenv init >>>
export PYENV_ROOT=\"\$HOME/.pyenv\"
export PATH=\"\$PYENV_ROOT/bin:\$PATH\"
eval \"\$(pyenv init -)\"
# <<< pyenv init <<<"

mkdir -p "$HOME/.nvm"
export NVM_DIR="$HOME/.nvm"
# shellcheck disable=SC1091
[ -s "$BREW_PREFIX/opt/nvm/nvm.sh" ] && . "$BREW_PREFIX/opt/nvm/nvm.sh"
if command -v nvm >/dev/null 2>&1; then
    log "Installiere aktuelle Node.js LTS-Version via nvm ..."
    nvm install --lts
    nvm alias default 'lts/*'

    log "Installiere Pi CLI (pi.dev) via npm ..."
    npm install -g --ignore-scripts @earendil-works/pi-coding-agent || warn "Pi-CLI-Installation fehlgeschlagen."
else
    warn "nvm konnte nicht geladen werden, überspringe Node-Installation."
fi

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv >/dev/null 2>&1; then
    LATEST_PY="$(pyenv install --list | grep -E '^\s*3\.[0-9]+\.[0-9]+$' | tail -1 | tr -d ' ')"
    if [[ -n "$LATEST_PY" ]] && ! pyenv versions --bare | grep -qx "$LATEST_PY"; then
        log "Installiere Python $LATEST_PY via pyenv ..."
        pyenv install "$LATEST_PY"
    fi
    if [[ -n "$LATEST_PY" ]]; then
        pyenv global "$LATEST_PY"
        ok "Python $LATEST_PY als globale Version gesetzt."
    fi
else
    warn "pyenv konnte nicht geladen werden, überspringe Python-Installation."
fi

# ---------------------------------------------------------------------------
# 5. Git-Grundkonfiguration (nur setzen, falls noch leer)
# ---------------------------------------------------------------------------
if [[ -z "$(git config --global user.name 2>/dev/null || true)" ]]; then
    read -r -p "Git user.name (für Commits): " GIT_NAME
    git config --global user.name "$GIT_NAME"
fi
if [[ -z "$(git config --global user.email 2>/dev/null || true)" ]]; then
    read -r -p "Git user.email (für Commits): " GIT_EMAIL
    git config --global user.email "$GIT_EMAIL"
fi
git config --global init.defaultBranch main
git config --global pull.rebase false

# ---------------------------------------------------------------------------
# 6. GitHub CLI Login (falls noch nicht angemeldet)
# ---------------------------------------------------------------------------
if command -v gh >/dev/null 2>&1; then
    if ! gh auth status >/dev/null 2>&1; then
        log "GitHub CLI ist noch nicht angemeldet."
        read -r -p "Jetzt 'gh auth login' interaktiv ausführen? [y/N] " RUN_GH_LOGIN
        if [[ "$RUN_GH_LOGIN" =~ ^[Yy]$ ]]; then
            gh auth login
        else
            warn "Übersprungen. Später manuell mit 'gh auth login' nachholen."
        fi
    else
        ok "GitHub CLI bereits angemeldet."
    fi
fi

# ---------------------------------------------------------------------------
# 7. Dev-Umgebung: ~/Development anlegen und Repos auschecken
# ---------------------------------------------------------------------------
mkdir -p "$DEV_DIR"
ok "Dev-Ordner bereit: $DEV_DIR"

if [[ ${#REPOS[@]} -eq 0 ]]; then
    warn "Keine Repos in REPOS[] eingetragen (Kopf von bootstrap.sh). Überspringe Klon-Schritt."
elif ! command -v gh >/dev/null 2>&1 || ! gh auth status >/dev/null 2>&1; then
    warn "GitHub CLI nicht verfügbar/angemeldet. Überspringe Klon-Schritt (erst 'gh auth login' ausführen, dann Skript erneut laufen lassen)."
else
    log "Klone/aktualisiere ${#REPOS[@]} Repo(s) in $DEV_DIR ..."
    for ENTRY in "${REPOS[@]}"; do
        FOLDER_NAME="${ENTRY%%|*}"
        REPO_SLUG="${ENTRY#*|}"
        TARGET="$DEV_DIR/$FOLDER_NAME"

        if [[ -d "$TARGET/.git" ]]; then
            ok "Bereits vorhanden, überspringe Klon: $FOLDER_NAME"
            continue
        fi

        log "Klone $REPO_SLUG -> $TARGET"
        if ! gh repo clone "$REPO_SLUG" "$TARGET" -- --recurse-submodules; then
            warn "Klonen von $REPO_SLUG fehlgeschlagen (z. B. fehlender Zugriff). Überspringe."
            continue
        fi

        # Falls beim Klon Submodule nicht initialisiert wurden (z. B. ältere
        # gh-Version), hier idempotent nachziehen; bei Repos ohne .gitmodules
        # ist dieser Befehl ein No-Op.
        if [[ -f "$TARGET/.gitmodules" ]]; then
            log "Initialisiere Submodule für $FOLDER_NAME ..."
            git -C "$TARGET" submodule update --init --recursive || warn "Submodule-Init für $FOLDER_NAME fehlgeschlagen."
        fi
    done
fi

# ---------------------------------------------------------------------------
# 8. Persönliche macOS-Systemeinstellungen (keine MDM-verwalteten Bereiche)
# ---------------------------------------------------------------------------
log "Setze macOS-Komfort-Einstellungen ..."

# Screenshots als PNG in einen eigenen Ordner statt auf den Desktop
mkdir -p "$HOME/Screenshots"
defaults write com.apple.screencapture location -string "$HOME/Screenshots"
defaults write com.apple.screencapture type -string "png"

# Tastatur: schnellere Wiederholrate
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15

# Finder: Dateiendungen immer anzeigen, Pfadleiste einblenden, versteckte Dateien anzeigen
defaults write NSGlobalDomain AppleShowAllExtensions -bool true
defaults write com.apple.finder ShowPathbar -bool true
defaults write com.apple.finder AppleShowAllFiles -bool true
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"

# Dock: automatisch ausblenden, kleinere Icons, keine "zuletzt verwendet"-Apps
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock tilesize -int 40
defaults write com.apple.dock show-recents -bool false
defaults write com.apple.dock orientation -string "bottom"

# Trackpad: Tippen zum Klicken aktivieren
defaults write com.apple.AppleMultitouchTrackpad Clicking -bool true
defaults write NSGlobalDomain com.apple.mouse.tapBehavior -int 1

# Erscheinungsbild: Dark Mode erzwingen
defaults write NSGlobalDomain AppleInterfaceStyle -string "Dark"
osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to true' >/dev/null 2>&1 || true

# Scrollen: "natürliches" (umgekehrtes) Scrollen deaktivieren -> klassische Richtung
defaults write NSGlobalDomain com.apple.swipescrolldirection -bool true

# Hintergrundbild: von einer festen URL herunterladen und für alle Displays setzen.
WALLPAPER_URL="https://raw.githubusercontent.com/dharmx/walls/main/digital/a_car_with_trees_on_it.png"
WALLPAPER_DIR="$HOME/Pictures/Wallpapers"
WALLPAPER_PATH="$WALLPAPER_DIR/a_car_with_trees_on_it.png"

mkdir -p "$WALLPAPER_DIR"
log "Lade Hintergrundbild herunter ..."
if curl -fsSL "$WALLPAPER_URL" -o "$WALLPAPER_PATH"; then
    osascript -e "tell application \"System Events\" to tell every desktop to set picture to (\"$WALLPAPER_PATH\" as POSIX file as text)" >/dev/null 2>&1 \
        && ok "Hintergrundbild gesetzt: $WALLPAPER_PATH" \
        || warn "Hintergrundbild konnte nicht per osascript gesetzt werden (z. B. fehlende Bedienungshilfen-Rechte für 'Systemereignisse')."
else
    warn "Download des Hintergrundbilds fehlgeschlagen, überspringe."
fi

# Änderungen für Finder & Dock übernehmen
killall Finder >/dev/null 2>&1 || true
killall Dock >/dev/null 2>&1 || true
killall SystemUIServer >/dev/null 2>&1 || true

ok "macOS-Einstellungen gesetzt."

# ---------------------------------------------------------------------------
# 9. System & Sicherheit
# ---------------------------------------------------------------------------
log "Setze System-/Sicherheitseinstellungen ..."

# Computername (Finder-Freigabe, lokales Netzwerk, Bonjour) setzen
sudo scutil --set ComputerName "$COMPUTER_NAME"
sudo scutil --set HostName "$COMPUTER_NAME"
sudo scutil --set LocalHostName "$COMPUTER_NAME"
ok "Computername gesetzt: $COMPUTER_NAME"

# Touch ID für sudo im Terminal aktivieren (idempotent: nur einfügen, falls fehlend)
PAM_SUDO_FILE="/etc/pam.d/sudo"
if [[ -f "$PAM_SUDO_FILE" ]] && ! grep -q "pam_tid.so" "$PAM_SUDO_FILE"; then
    log "Aktiviere Touch ID für sudo ..."
    sudo sed -i '' '1s;^;auth       sufficient     pam_tid.so\n;' "$PAM_SUDO_FILE"
    ok "Touch ID für sudo aktiviert (in neuen Terminal-Sitzungen wirksam)."
else
    ok "Touch ID für sudo bereits aktiviert oder PAM-Datei nicht vorhanden."
fi

# Bildschirm sofort sperren, sobald Ruhezustand/Bildschirmschoner startet
defaults write com.apple.screensaver askForPassword -int 1
defaults write com.apple.screensaver askForPasswordDelay -int 0

# macOS-Firewall aktivieren
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on >/dev/null
ok "Firewall aktiviert."

# Automatische Software-Updates (Suche, Download, Installation im Hintergrund)
sudo softwareupdate --schedule on >/dev/null 2>&1 || true
defaults write com.apple.SoftwareUpdate AutomaticCheckEnabled -bool true
defaults write com.apple.SoftwareUpdate AutomaticDownload -bool true
defaults write com.apple.SoftwareUpdate CriticalUpdateInstall -bool true
ok "Automatische Software-Updates aktiviert."

ok "System-/Sicherheitseinstellungen gesetzt."

# ---------------------------------------------------------------------------
# Abschluss
# ---------------------------------------------------------------------------
echo ""
ok "Setup abgeschlossen!"
log "Bitte ein neues Terminal öffnen (oder 'source ~/.zshrc' ausführen), damit nvm/pyenv aktiv sind."
warn "1Password, Teams & Office ggf. noch einmal öffnen und mit dem Arbeitskonto anmelden."
warn "Computername-/Firewall-/Update-Änderungen erfordern ggf. das Admin-Passwort (sudo)."

