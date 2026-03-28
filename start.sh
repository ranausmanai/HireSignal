#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
#  HireSignal — One-click launcher
#  Just run:  ./start.sh
# ──────────────────────────────────────────────────────────
set -e

PORT=8021
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/.venv"
URL="http://localhost:$PORT"

# ── Colors ───────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

banner() {
  echo ""
  echo -e "${BLUE}${BOLD}  ┌─────────────────────────────────────┐${NC}"
  echo -e "${BLUE}${BOLD}  │     HireSignal                      │${NC}"
  echo -e "${BLUE}${BOLD}  │     Interview Feedback Intelligence │${NC}"
  echo -e "${BLUE}${BOLD}  └─────────────────────────────────────┘${NC}"
  echo ""
}

info()  { echo -e "  ${BLUE}▸${NC} $1"; }
ok()    { echo -e "  ${GREEN}✔${NC} $1"; }
warn()  { echo -e "  ${YELLOW}!${NC} $1"; }
fail()  { echo -e "  ${RED}✖${NC} $1"; exit 1; }

# ── Kill any existing instance on our port ───────────────
cleanup_port() {
  local pid
  pid=$(lsof -ti:"$PORT" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    warn "Port $PORT in use (pid $pid) — stopping it..."
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
}

# ── Check Python ─────────────────────────────────────────
check_python() {
  if command -v python3 &>/dev/null; then
    PYTHON=python3
  elif command -v python &>/dev/null; then
    PYTHON=python
  else
    fail "Python is not installed. Please install Python 3.9+ from https://www.python.org/downloads/"
  fi

  local ver
  ver=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  local major minor
  major=$(echo "$ver" | cut -d. -f1)
  minor=$(echo "$ver" | cut -d. -f2)

  if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 9 ]; }; then
    fail "Python $ver found, but 3.9+ is required. Please upgrade."
  fi

  ok "Python $ver"
}

# ── Set up virtual environment ───────────────────────────
setup_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment (first run only)..."
    $PYTHON -m venv "$VENV_DIR"
    ok "Virtual environment created"
  fi

  # Activate
  source "$VENV_DIR/bin/activate"

  # Install/update dependencies
  if [ "$VENV_DIR/bin/pip" -ot "$APP_DIR/requirements.txt" ] || [ ! -f "$VENV_DIR/.installed" ]; then
    info "Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r "$APP_DIR/requirements.txt"
    touch "$VENV_DIR/.installed"
    ok "Dependencies installed"
  else
    ok "Dependencies up to date"
  fi
}

# ── Check Claude Code (optional, for AI features) ───────
check_claude() {
  if command -v claude &>/dev/null; then
    ok "Claude Code available (AI features enabled)"
  else
    warn "Claude Code not found — AI features (deep analysis, chat, narrative) will use fallbacks"
    warn "Install from: https://docs.anthropic.com/en/docs/claude-code"
  fi
}

# ── Open browser ─────────────────────────────────────────
open_browser() {
  sleep 2
  if command -v open &>/dev/null; then
    open "$URL"  # macOS
  elif command -v xdg-open &>/dev/null; then
    xdg-open "$URL"  # Linux
  elif command -v start &>/dev/null; then
    start "$URL"  # Windows/Git Bash
  fi
}

# ── Main ─────────────────────────────────────────────────
banner
check_python
setup_venv
check_claude
cleanup_port

echo ""
echo -e "  ${GREEN}${BOLD}Starting HireSignal...${NC}"
echo -e "  ${BOLD}${URL}${NC}"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Open browser in background
open_browser &

# Run the app
cd "$APP_DIR"
exec $PYTHON app.py
