#!/usr/bin/env bash
# ============================================================
#  ATLAS — Full Stack Launcher (bash / WSL / macOS)
#  Usage:
#    ./start_atlas.sh              # backend + mock + frontend
#    ./start_atlas.sh --demo       # + fault scripts (real-time)
#    ./start_atlas.sh --demo --replay  # + fault scripts (instant)
# ============================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
DEMO=false
REPLAY=""

# ── Parse args ────────────────────────────────────────────────────────────────
for arg in "$@"; do
    case $arg in
        --demo)   DEMO=true ;;
        --replay) REPLAY="--replay" ;;
    esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; GRAY='\033[0;37m'; RESET='\033[0m'; BOLD='\033[1m'

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠${RESET} $1"; }
err()  { echo -e "  ${RED}✗${RESET} $1"; exit 1; }
hdr()  { echo -e "\n  ${CYAN}${BOLD}$1${RESET}\n  $(printf '─%.0s' $(seq 1 ${#1}))"; }
step() { printf "  ${GRAY}%-22s${RESET}%s\n" "$1" "$2"; }

# ── Pre-flight ────────────────────────────────────────────────────────────────
hdr "ATLAS Pre-flight Checks"

# Python 3.11+
PYTHON=""
for cmd in python3.11 python3.12 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '3\.\K\d+' | head -1)
        if [[ "${ver:-0}" -ge 11 ]]; then
            PYTHON="$cmd"
            ok "Python  → $($cmd --version) ($cmd)"
            break
        fi
    fi
done
[[ -z "$PYTHON" ]] && err "Python 3.11+ not found. Install from https://python.org"

# Node
command -v node &>/dev/null && ok "Node.js → $(node --version)" || err "Node.js not found."

# .env
[[ -f "$ROOT/.env" ]] && ok ".env    → found" || err ".env not found at repo root."

# node_modules
if [[ ! -d "$ROOT/ui-atlas/node_modules" ]]; then
    warn "ui-atlas/node_modules missing — running npm install..."
    (cd "$ROOT/ui-atlas" && npm install --silent)
    ok "npm install complete"
fi

# ── Terminal detection ────────────────────────────────────────────────────────
# Prefer: tmux > gnome-terminal > iTerm2/osascript > xterm > background &
open_tab() {
    local title="$1" dir="$2" cmd="$3"

    if [[ -n "${TMUX:-}" ]]; then
        tmux new-window -n "$title" "cd '$dir' && $cmd; exec bash"

    elif command -v gnome-terminal &>/dev/null; then
        gnome-terminal --tab --title="$title" -- bash -c "cd '$dir' && $cmd; exec bash" &

    elif [[ "$(uname)" == "Darwin" ]] && command -v osascript &>/dev/null; then
        osascript <<EOF
tell application "Terminal"
    do script "cd '$dir' && $cmd"
    set custom title of front window to "$title"
end tell
EOF

    elif command -v xterm &>/dev/null; then
        xterm -title "$title" -e "cd '$dir' && $cmd; exec bash" &

    else
        # Last resort: background process, log to file
        local logfile="$ROOT/logs/${title// /_}.log"
        mkdir -p "$ROOT/logs"
        (cd "$dir" && $cmd > "$logfile" 2>&1) &
        warn "No terminal emulator found — $title running in background → $logfile"
    fi
}

# ── Launch ────────────────────────────────────────────────────────────────────
hdr "Launching Services"

# 1 — Backend
ok "Starting ATLAS Backend (port $BACKEND_PORT)..."
open_tab "ATLAS Backend" "$ROOT" \
    "$PYTHON -m uvicorn backend.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload --log-level info"
sleep 0.4

# 2 — Mock PaymentAPI
ok "Starting Mock PaymentAPI (port 8001)..."
open_tab "Mock PaymentAPI" "$ROOT" \
    "$PYTHON data/mock_services/mock_payment_api.py"
sleep 0.4

# 3 — Frontend
ok "Starting Frontend (port $FRONTEND_PORT)..."
open_tab "ATLAS Frontend" "$ROOT/ui-atlas" \
    "npm run dev -- --port $FRONTEND_PORT"
sleep 0.4

# 4 — Fault scripts (demo mode only)
if [[ "$DEMO" == "true" ]]; then
    warn "Demo mode: fault scripts will fire. Wait ~30s for backend to be ready."

    ok "Starting FinanceCore fault script..."
    open_tab "Fault: FinanceCore" "$ROOT" \
        "$PYTHON data/fault_scripts/financecore_cascade.py $REPLAY"
    sleep 0.4

    ok "Starting RetailMax fault script..."
    open_tab "Fault: RetailMax" "$ROOT" \
        "$PYTHON data/fault_scripts/retailmax_redis_oom.py $REPLAY"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
hdr "ATLAS is starting"
step "Backend API"      "http://localhost:$BACKEND_PORT"
step "API Docs"         "http://localhost:$BACKEND_PORT/docs"
step "Frontend"         "http://localhost:$FRONTEND_PORT"
step "Mock PaymentAPI"  "http://localhost:8001/actuator/health"
step "WS logs"          "ws://localhost:$BACKEND_PORT/ws/logs/FINCORE_UK_001"
step "WS incidents"     "ws://localhost:$BACKEND_PORT/ws/incidents/FINCORE_UK_001"
step "WS activity"      "ws://localhost:$BACKEND_PORT/ws/activity"

echo ""
echo -e "  ${GRAY}Usage:${RESET}"
echo -e "  ${GRAY}  ./start_atlas.sh                  # backend + mock + frontend${RESET}"
echo -e "  ${GRAY}  ./start_atlas.sh --demo            # + fault scripts (real-time)${RESET}"
echo -e "  ${GRAY}  ./start_atlas.sh --demo --replay   # + fault scripts (instant)${RESET}"
echo ""
