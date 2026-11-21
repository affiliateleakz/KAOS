#!/usr/bin/env bash
# Cron entrypoint: use the deployed Passenger API modules, never local git code.
set -Eeuo pipefail
umask 077
LIVE="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
PY="${KAOS_PYTHON_BIN:-$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python}"
test -x "$PY"
test -s "$LIVE/.env"
test -s "$LIVE/apps/api/kaos_ai_training_jobs.py"
test -s "$LIVE/kaos-paper-api-revision.txt"
if command -v flock >/dev/null; then
  # Stagger overlapping runs during slow archive reads. Mongo also leases jobs.
  exec flock -n "$HOME/.kaos-r2-training.lock" "$PY" "$LIVE/apps/api/kaos_ai_training_jobs.py"
fi
exec "$PY" "$LIVE/apps/api/kaos_ai_training_jobs.py"
