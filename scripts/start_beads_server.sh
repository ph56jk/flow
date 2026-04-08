#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT}/.beads-server"
CFG_DIR="${DATA_DIR}/.doltcfg"
HOST="${BD_SERVER_HOST:-127.0.0.1}"
PORT="${BD_SERVER_PORT:-3307}"

mkdir -p "${DATA_DIR}"

exec dolt sql-server \
  -H "${HOST}" \
  -P "${PORT}" \
  --data-dir "${DATA_DIR}" \
  --doltcfg-dir "${CFG_DIR}"
