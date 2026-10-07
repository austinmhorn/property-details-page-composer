#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

PYTHON="${PYTHON:-/home/birchstonereporting/shared-venvs/data-engines/bin/python}"

if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3)"
fi

LAST_RUN_FILE="$SCRIPT_DIR/last_run.json"

START_TIME=$(date +%s)
STARTED_AT=$(date -Iseconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S%z")

RUN_SOURCE="${RUN_SOURCE:-cron}"

echo "===== PROPERTY DETAILS PAGE COMPOSER START ====="

"$PYTHON" "$SCRIPT_DIR/scripts/oversee_process.py"
PY_EXIT=$?

END_TIME=$(date +%s)
FINISHED_AT=$(date -Iseconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S%z")
DURATION=$((END_TIME - START_TIME))

if [ "$PY_EXIT" -eq 0 ]; then
    STATUS="success"
else
    STATUS="failed"
fi

cat > "$LAST_RUN_FILE" <<EOF
{
  "status": "$STATUS",
  "started_at": "$STARTED_AT",
  "finished_at": "$FINISHED_AT",
  "duration_seconds": $DURATION,
  "run_source": "$RUN_SOURCE"
}
EOF

echo "Python exit code: $PY_EXIT"
echo "===== PROPERTY DETAILS PAGE COMPOSER COMPLETE ====="

exit "$PY_EXIT"
