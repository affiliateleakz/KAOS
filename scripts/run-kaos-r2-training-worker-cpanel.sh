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
test -s "$LIVE/apps/api/kaos_ai_paper_loop.py"
# A single flock protects training and paper prediction ticks. Neither calls a broker.
run_once() {
  "$PY" "$LIVE/apps/api/kaos_ai_training_jobs.py"
  "$PY" "$LIVE/apps/api/kaos_ai_paper_loop.py"
}
if command -v flock >/dev/null; then
  exec flock -n "$HOME/.kaos-r2-training.lock" /bin/bash -c '"$1" "$2"; "$1" "$3"' kaos "$PY" "$LIVE/apps/api/kaos_ai_training_jobs.py" "$LIVE/apps/api/kaos_ai_paper_loop.py"
fi
run_once
