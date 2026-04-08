#!/usr/bin/env bash
set -euo pipefail

cd /Users/admin/VibeCoding/flow
source .venv/bin/activate
python -m unittest discover -s tests -v
