#!/usr/bin/env bash
# Install an opt-in once-per-minute KAOS R2 training worker cron on cPanel.
# This starts RESEARCH TRAINING only, never broker orders or live AI execution.
set -Eeuo pipefail
umask 077

LIVE="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
PY="${KAOS_PYTHON_BIN:-$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python}"
WORKER="$LIVE/apps/api/kaos_ai_training_jobs.py"
ENVFILE="$LIVE/.env"
MARKER="KAOS_R2_RESEARCH_TRAINING_CRON_V1"
LOG="$HOME/kaos-r2-training-worker.log"
test -x "$PY" || { echo "Python environment unavailable"; exit 1; }
test -s "$WORKER" || { echo "Training worker is not deployed in live API"; exit 1; }
test -s "$ENVFILE" || { echo "Live backend .env unavailable; stop"; exit 1; }
test -s "$LIVE/kaos-paper-api-revision.txt" || {
  echo "Matching KAOS API deployment not verified; stop"; exit 1;
}
test -f "$LIVE/passenger_wsgi.py" || { echo "Passenger app not found"; exit 1; }
command -v crontab >/dev/null || { echo "crontab unavailable"; exit 1; }

# Never print R2 or Mongo keys or .env. Existing backend runtime values remain.
"$PY" - "$ENVFILE" <<'PY'
from pathlib import Path
import sys
from dotenv import dotenv_values
values=dotenv_values(sys.argv[1])
required=("MONGO_URL","DB_NAME","KAOS_R2_ACCOUNT_ID",
          "KAOS_R2_ACCESS_KEY_ID","KAOS_R2_SECRET_ACCESS_KEY",
          "KAOS_CANDLE_OWNER_USER_ID")
missing=[k for k in required if not values.get(k)]
if values.get("KAOS_R2_ENABLED","").lower()!="true":
    missing.append("KAOS_R2_ENABLED=true")
if missing:
    raise SystemExit("Missing backend research settings: "+", ".join(missing))
PY

# This opt-in is deliberately separate from KAOS live or paper broker flags.
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cp -p "$ENVFILE" "$ENVFILE.kaos-ai-training-backup-$STAMP"
"$PY" - "$ENVFILE" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
lines=path.read_text().splitlines()
key="KAOS_R2_TRAIN_WORKER_ENABLED"
lines=[line for line in lines if not line.startswith(key+"=")]
lines.append(key+"=1")
path.write_text("\n".join(lines)+"\n")
PY
chmod 600 "$ENVFILE"

# Avoid duplicate cron entries and never overwrite pre-existing user jobs.
EXISTING="$(crontab -l 2>/dev/null || true)"
if ! printf '%s\n' "$EXISTING" | grep -qF "$MARKER"; then
  ENTRY="* * * * * /bin/bash $HOME/kaos-deploy-source/scripts/run-kaos-r2-training-worker-cpanel.sh >> $LOG 2>&1 # $MARKER"
  { printf '%s\n' "$EXISTING"; printf '%s\n' "$ENTRY"; } | crontab -
fi
# Must verify actual installation; never say enabled after a crontab failure.
crontab -l | grep -qF "$MARKER" || { echo "STOP: training cron was not installed" >&2; exit 1; }
mkdir -p "$LIVE/tmp"
touch "$LIVE/tmp/restart.txt"
echo "KAOS R2 RESEARCH TRAINER ENABLED"
echo "Enabled persistent job processing (up to 2 markets per cron invocation)."
echo "Existing .env backed up securely; existing cron jobs preserved."
echo "Log: $LOG"
echo "AI broker order permissions and real-money trading remain unchanged."
