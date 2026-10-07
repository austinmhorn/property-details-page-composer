#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "===== PROPERTY DETAILS PAGE COMPOSER START ====="

echo "→ Fetching latest property data from Notion"
go run .

echo "→ Rendering portfolio HTML"
"$PYTHON_BIN" scripts/render_portfolio.py

if [[ "${1:-}" == "--publish" ]]; then
  echo "→ Publishing portfolio HTML to Interact"
  "$PYTHON_BIN" scripts/publish_portfolio.py
else
  echo "→ Preview only. Re-run with --publish to update Interact."
fi

echo "===== PROPERTY DETAILS PAGE COMPOSER COMPLETE ====="
