#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST="127.0.0.1"
PORT="8000"
RELOAD=0
PREPARE_ONLY=0
NO_OPEN_BROWSER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:?missing host}"
      shift 2
      ;;
    --port)
      PORT="${2:?missing port}"
      shift 2
      ;;
    --reload)
      RELOAD=1
      shift
      ;;
    --prepare-only)
      PREPARE_ONLY=1
      shift
      ;;
    --no-open-browser)
      NO_OPEN_BROWSER=1
      shift
      ;;
    *)
      echo "Khong nhan ra tham so: $1" >&2
      exit 1
      ;;
  esac
done

pick_python() {
  if command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return
  fi
  return 1
}

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  SYSTEM_PYTHON="$(pick_python || true)"
  if [[ -z "${SYSTEM_PYTHON:-}" ]]; then
    echo "Khong tim thay Python 3.11+. Hay cai Python 3.11 roi chay lai." >&2
    exit 1
  fi
  if ! "$SYSTEM_PYTHON" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
  then
    echo "Can Python 3.11+ de tao moi .venv cho app nay." >&2
    exit 1
  fi
  "$SYSTEM_PYTHON" -m venv "$ROOT/.venv"
fi

PYTHON="$ROOT/.venv/bin/python"
INSTALL_STAMP="$ROOT/.venv/.flow_install_stamp"

if [[ ! -f "$INSTALL_STAMP" || "$ROOT/pyproject.toml" -nt "$INSTALL_STAMP" ]]; then
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install -e .
  date -u +"%Y-%m-%dT%H:%M:%SZ" >"$INSTALL_STAMP"
fi

export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$ROOT/.pw-browsers}"
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

if ! find "$PLAYWRIGHT_BROWSERS_PATH" -type f \( -name "chrome" -o -name "Chromium" -o -name "chrome.exe" \) -print -quit | grep -q .; then
  "$PYTHON" -m playwright install chromium
fi

if [[ "$PREPARE_ONLY" -eq 1 ]]; then
  echo "Da setup xong. Chay app bang: ./scripts/run_flow_web.sh"
  exit 0
fi

if [[ "$NO_OPEN_BROWSER" -eq 0 ]]; then
  if command -v open >/dev/null 2>&1; then
    (sleep 2; open "http://${HOST}:${PORT}") >/dev/null 2>&1 &
  elif command -v xdg-open >/dev/null 2>&1; then
    (sleep 2; xdg-open "http://${HOST}:${PORT}") >/dev/null 2>&1 &
  fi
fi

ARGS=(-m uvicorn flow_web.main:app --host "$HOST" --port "$PORT")
if [[ "$RELOAD" -eq 1 ]]; then
  ARGS+=(--reload)
fi

exec "$PYTHON" "${ARGS[@]}"
