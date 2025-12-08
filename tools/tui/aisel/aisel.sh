#!/usr/bin/env bash
# AISel: Hübsches Inline-Menü für AI CLIs
# Version: 1.1.2
# Features: Config, Add/Remove/Edit (STABLE), Memory, Args, Dry-Run, Footer (+Quit)
set -euo pipefail

# --- KONFIGURATION & DATEIPFADE ---
VERSION="1.1.2"
CONFIG_DIR="$HOME/.config/aisel"
CONFIG_FILE="$CONFIG_DIR/aisel.conf"
STATE_FILE="$CONFIG_DIR/state"

# --- FARBEN & STYLES ---
C_RESET='\033[0m'
C_CYAN='\033[1;36m'
C_BLUE='\033[1;34m'
C_GREY='\033[0;90m'
C_WHITE='\033[1;37m'
C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_BOLD='\033[1m'
C_WARN='\033[1;33m'

BOX_WIDTH=65

# --- INITIALISIERUNG / RESET ---

create_default_config() {
  mkdir -p "$CONFIG_DIR"
  cat <<EOF > "$CONFIG_FILE"
Copilot|GitHub Copilot CLI|copilot
Gemini|Google Gemini 3|gemini
Claude|Anthropic Claude|claude
Cursor|Cursor Agent|cursor-agent
EOF
}

# --- ARGUMENTE ---
PASS_ARGS=()
DRY_RUN=0

# Argument Parser Loop
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reset)
      echo -e "${C_WARN}Setze Konfiguration zurück auf Standardwerte...${C_RESET}"
      rm -f "$CONFIG_FILE" "$STATE_FILE"
      create_default_config
      echo -e "${C_GREEN}Erledigt.${C_RESET}"
      exit 0
      ;;
    --version|-v)
      echo "aisel version $VERSION"
      exit 0
      ;;
    --help|-h)
      echo -e "${C_CYAN}${C_BOLD}AISel v$VERSION${C_RESET}"
      echo -e "  aisel                 Startet Menü"
      echo -e "  aisel --dry-run       Zeigt Befehl ohne Ausführung"
      echo -e "  aisel --reset         Reset Config"
      echo -e "  aisel -- <args...>    Argumente weiterreichen"
      echo
      echo -e "${C_BOLD}Tastenkürzel:${C_RESET}"
      echo -e "  Nav:    ↑/↓, j/k, Tab/S-Tab, Ctrl+n/p"
      echo -e "  Action: Enter (Run), 1-9 (Quick Run)"
      echo -e "  Config: + (Add), - (Del), e (Edit)"
      exit 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --)
      shift
      PASS_ARGS+=("$@")
      break
      ;;
    *)
      PASS_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ ! -f "$CONFIG_FILE" ]]; then
  create_default_config
fi

# Arrays deklarieren
NAMES=()
DESCS=()
CMDS=()
AVAILABLE=()

# --- FUNKTIONEN ---

load_config() {
  NAMES=()
  DESCS=()
  CMDS=()
  AVAILABLE=()
  
  if [[ ! -f "$CONFIG_FILE" ]]; then return; fi
  
  while IFS='|' read -r name desc cmd || [ -n "$name" ]; do
    [[ -z "$name" ]] && continue
    [[ "$name" == \#* ]] && continue
    
    NAMES+=("$name")
    DESCS+=("$desc")
    CMDS+=("$cmd")
    
    if command -v "$cmd" >/dev/null 2>&1; then
      AVAILABLE+=("1")
    else
      AVAILABLE+=("0")
    fi
  done < "$CONFIG_FILE"
}

get_start_index() {
  local default_idx=0
  if [[ -f "$STATE_FILE" ]]; then
    local last_name
    last_name=$(<"$STATE_FILE")
    local i
    for i in "${!NAMES[@]}"; do
      if [[ "${NAMES[$i]}" == "$last_name" ]]; then
        echo "$i"
        return
      fi
    done
  fi
  echo "$default_idx"
}

hide_cursor() { tput civis >&2 2>/dev/null || printf '\e[?25l' >&2; }
show_cursor() { tput cnorm >&2 2>/dev/null || printf '\e[?25h' >&2; }
repeat_char() { local c; for ((c=0; c<$2; c++)); do printf "$1"; done; }

cleanup() {
  show_cursor
  stty echo 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT

# --- HAUPTMENÜ ---
arrow_menu() {
  load_config

  local selected=$(get_start_index)
  if (( selected >= ${#NAMES[@]} )); then selected=0; fi

  local key=""
  local esc=$'\e'

  get_total_lines() { echo $(( 3 + ${#NAMES[@]} + 3 )); }

  hide_cursor
  local h_line
  h_line=$(repeat_char "─" $((BOX_WIDTH - 2)))
  
  draw_menu() {
    local count=${#NAMES[@]}
    
    # Header
    printf "${C_GREY}╭${h_line}╮${C_RESET}\n" >&2
    local title=" AI SELECTOR "
    local title_len=${#title}
    local pad_len=$(( (BOX_WIDTH - 2 - title_len) / 2 ))
    local pad_rest=$(( BOX_WIDTH - 2 - pad_len - title_len ))
    printf "${C_GREY}│%*s${C_CYAN}${C_BOLD}%s${C_RESET}${C_GREY}%*s│${C_RESET}\n" "$pad_len" "" "$title" "$pad_rest" "" >&2
    printf "${C_GREY}├${h_line}┤${C_RESET}\n" >&2

    # Liste
    local i
    for ((i=0; i<count; i++)); do
      local name="${NAMES[$i]}"
      local desc="${DESCS[$i]}"
      local cmd="${CMDS[$i]}"
      local icon="●"
      local color_icon="${C_GREEN}"
      local color_text="${C_WHITE}"
      local color_desc="${C_GREY}"
      local ptr=" "

      # Nummer für Kurzwahl anzeigen (1-9)
      local shortcut_hint=""
      if (( i < 9 )); then
          :
      fi

      if [[ "${AVAILABLE[$i]}" -eq 0 ]]; then
        icon="○"
        color_icon="${C_GREY}"
        color_text="${C_GREY}"
        desc="Nicht installiert ($cmd)"
        color_desc="${C_RED}"
      fi

      if (( i == selected )); then
        ptr="➜" 
        color_icon="${C_CYAN}"
        color_text="${C_WHITE}${C_BOLD}"
        color_desc="${C_CYAN}"
        icon="$ptr" 
      fi

      local d_name="$name"
      while ((${#d_name} < 12)); do d_name+=" "; done
      
      local used_len=$(( 1 + 1 + 1 + 12 + 3 + 1 + 1 )) 
      local avail_desc=$(( BOX_WIDTH - 2 - used_len ))
      if (( avail_desc < 0 )); then avail_desc=0; fi

      local d_desc="${desc:0:$avail_desc}" 
      while ((${#d_desc} < avail_desc)); do d_desc+=" "; done 
      
      printf "${C_GREY}│ ${C_RESET}" >&2
      printf " ${color_icon}%s ${color_text}%s ${C_GREY}· ${color_desc}%s${C_RESET}" "$icon" "$d_name" "$d_desc" >&2
      printf "${C_GREY} │${C_RESET}\n" >&2
    done

    # Footer
    printf "${C_GREY}├${h_line}┤${C_RESET}\n" >&2
    local credit="Made by SoniiiT"
    
    # HIER: q:Quit hinzugefügt
    local hint="+:Add -:Del e:Edit q:Quit"
    
    local space_len=$(( BOX_WIDTH - 4 - ${#hint} - ${#credit} ))
    if (( space_len < 0 )); then space_len=0; fi
    
    printf "${C_GREY}│ ${C_RESET}" >&2
    printf "${C_GREY}%s${C_RESET}" "$hint" >&2
    printf "%*s" "$space_len" "" >&2
    printf "${C_BLUE}%s${C_RESET}" "$credit" >&2
    printf "${C_GREY} │${C_RESET}\n" >&2
    printf "${C_GREY}╰${h_line}╯${C_RESET}\n" >&2
  }

  draw_menu

  while :; do
    local total_lines=$(get_total_lines)
    key=""
    IFS= read -rsn1 key < /dev/tty || true
    
    # --- NUMMERN KURZWAHL (1-9) ---
    if [[ "$key" =~ [1-9] ]]; then
        local idx=$((key - 1))
        if (( idx < ${#NAMES[@]} )); then
            echo "$idx"
            return 0
        fi
    fi

    # --- NAVIGATION ---
    if [[ $key == "" ]]; then
      echo "$selected"
      return 0
    fi
    
    # TAB / Ctrl+N
    if [[ $key == $'\t' || $key == $'\x0e' ]]; then
        ((selected++)); (( selected >= ${#NAMES[@]} )) && selected=0
        tput cuu "$total_lines" >&2; tput ed >&2; draw_menu; continue
    fi
    
    # Ctrl+P
    if [[ $key == $'\x10' ]]; then
        ((selected--)); (( selected < 0 )) && selected=$((${#NAMES[@]}-1))
        tput cuu "$total_lines" >&2; tput ed >&2; draw_menu; continue
    fi

    # --- EDIT (e) [STABLE FIX] ---
    if [[ $key == "e" || $key == "E" ]]; then
      # UI bereinigen
      tput cuu "$total_lines" >&2; tput ed >&2
      
      # 1. Cursor zeigen & Terminal zurücksetzen (WICHTIG für Editor!)
      show_cursor
      stty sane 
      
      # 2. Editor starten (Input/Output explizit auf TTY erzwingen)
      ${EDITOR:-nano} "$CONFIG_FILE" < /dev/tty > /dev/tty || true
      
      # 3. Skript-Status wiederherstellen
      hide_cursor
      stty -echo 2>/dev/null || true # Echo wieder aus für den Loop
      load_config
      draw_menu
      continue
    fi

    # --- ADD (+) ---
    if [[ $key == "+" ]]; then
      tput cuu "$total_lines" >&2; tput ed >&2; show_cursor
      echo -e "${C_CYAN}--- Neuen Eintrag hinzufügen ---${C_RESET}" >&2
      read -rp "Name (z.B. MyAI): " new_name < /dev/tty
      
      if [[ -n "$new_name" ]]; then
        read -rp "Befehl (z.B. my-ai-cli): " new_cmd < /dev/tty
        read -rp "Beschreibung: " new_desc < /dev/tty
        if [[ -n "$new_cmd" ]]; then
          echo "$new_name|${new_desc:-KI Tool}|$new_cmd" >> "$CONFIG_FILE"
        fi
      fi
      
      hide_cursor; load_config; draw_menu; continue
    fi

    # --- REMOVE (-) ---
    if [[ $key == "-" ]]; then
      local count=${#NAMES[@]}
      if (( count > 1 )); then
        local del_name="${NAMES[$selected]}"
        tput cuu "$total_lines" >&2; tput ed >&2
        
        echo -e "${C_RED}⚠ Bestätigung erforderlich${C_RESET}" >&2
        echo -e "Möchten Sie ${C_BOLD}'$del_name'${C_RESET} wirklich entfernen? (y/n)" >&2
        
        local confirm=""
        read -rsn1 confirm < /dev/tty
        
        if [[ "$confirm" =~ [yY] ]]; then
          local tmp_file="$CONFIG_FILE.tmp"
          local i=0
          : > "$tmp_file"
          while IFS='|' read -r n d c || [ -n "$n" ]; do
            if (( i != selected )); then echo "$n|$d|$c" >> "$tmp_file"; fi
            ((i++))
          done < "$CONFIG_FILE"
          mv "$tmp_file" "$CONFIG_FILE"
          load_config
          if (( selected >= ${#NAMES[@]} )); then selected=$(( ${#NAMES[@]} - 1 )); fi
        fi
        
        tput cuu 2 >&2 2>/dev/null || true 
        tput ed >&2 2>/dev/null || printf '\e[J' >&2
        draw_menu
      fi
      continue
    fi

    if [[ $key == "q" ]]; then exit 130; fi

    if [[ $key == $esc ]]; then
      read -rsn2 -t 0.01 key2 < /dev/tty || true
      key+=$key2
      case "$key" in
        $'\e[A'|k) ((selected--)); (( selected < 0 )) && selected=$((${#NAMES[@]}-1)) ;;
        $'\e[B'|j) ((selected++)); (( selected >= ${#NAMES[@]} )) && selected=0 ;;
        $'\e[Z')   # Shift-TAB
           ((selected--)); (( selected < 0 )) && selected=$((${#NAMES[@]}-1)) ;;
        $'\e') exit 130 ;;
      esac
      
      tput cuu "$total_lines" >&2 2>/dev/null || true
      tput ed >&2 2>/dev/null || printf '\e[J' >&2
      draw_menu
    fi
  done
}

printf "\n" >&2
selected_idx="$(arrow_menu)"

if [[ -z "${selected_idx:-}" ]]; then exit 130; fi

load_config
name="${NAMES[$selected_idx]}"
cmd="${CMDS[$selected_idx]}"

echo "$name" > "$STATE_FILE"

if [[ "${AVAILABLE[$selected_idx]}" -eq 0 ]]; then
  echo "Fehler: '$cmd' ist nicht installiert." >&2
  exit 127
fi

if [[ "$name" == "Copilot" ]]; then
  if [[ ! " ${PASS_ARGS[*]} " =~ " --banner " ]]; then
      PASS_ARGS=("--banner" "${PASS_ARGS[@]}")
  fi
fi

display_args=""
if (( ${#PASS_ARGS[@]} > 0 )); then
  if [[ "$name" == "Copilot" && ${#PASS_ARGS[@]} -eq 1 && "${PASS_ARGS[0]}" == "--banner" ]]; then
     display_args=""
  else
     display_args=" with args: ${C_WHITE}${PASS_ARGS[*]}${C_GREY}"
  fi
fi

echo -e "${C_GREY}╰─> Starting ${C_CYAN}${name}${C_GREY}${display_args}...${C_RESET}\n" >&2

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo -e "${C_WARN}[DRY RUN] Befehl:${C_RESET} $cmd ${PASS_ARGS[*]}"
  exit 0
fi

exec "$cmd" "${PASS_ARGS[@]}"