#!/usr/bin/env bash
# Activate read-only KAOS R2 research jobs on cPanel, without touching website.
# CRON only; never enables AI trade execution or broker orders.
set -Eeuo pipefail
umask 077
LIVE="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
PY="${KAOS_PYTHON_BIN:-$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python}"
test -x "$PY" || { echo "ERROR: Missing venv"; exit 1; }
test -s "$LIVE/apps/api/kaos_r2_ai_cron.py" || { echo "ERROR: AI trainer not deployed"; exit 1; }
test -s "$LIVE/apps/api/kaos_r2_pattern_cron.py" || { echo "ERROR: R2 observer not deployed"; exit 1; }
test -s "$LIVE/apps/api/kaos_r2_shadow_cron.py" || { echo "ERROR: Shadow predictor not deployed"; exit 1; }
command -v crontab >/dev/null || { echo "ERROR: cPanel crontab executable unavailable"; exit 1; }
command -v flock >/dev/null || { echo "ERROR: flock unavailable; no tasks changed"; exit 1; }
LOGDIR="$HOME/kaos-private-research-logs"
mkdir -p "$LOGDIR"
chmod 700 "$LOGDIR"
CUR="$(mktemp "$HOME/.kaos-cron-current.XXXXXXXX")"
NEW="$(mktemp "$HOME/.kaos-cron-new.XXXXXXXX")"
trap 'rm -f "$CUR" "$NEW"' EXIT
crontab -l >"$CUR" 2>/dev/null || : 
# Preserve every existing user cron line; replace ONLY our marked research jobs.
sed '/# KAOS_R2_RESEARCH_MANAGED$/d' "$CUR" >"$NEW"
echo "*/10 * * * * KAOS_R2_PATTERN_OBSERVER_ENABLED=1 /usr/bin/flock -n $LOGDIR/pattern.lock $PY $LIVE/apps/api/kaos_r2_pattern_cron.py >> $LOGDIR/pattern.log 2>&1 # KAOS_R2_RESEARCH_MANAGED" >>"$NEW"
echo "5-59/10 * * * * KAOS_R2_SHADOW_PREDICT_ENABLED=1 /usr/bin/flock -n $LOGDIR/shadow.lock $PY $LIVE/apps/api/kaos_r2_shadow_cron.py >> $LOGDIR/shadow.log 2>&1 # KAOS_R2_RESEARCH_MANAGED" >>"$NEW"
echo "13 * * * * KAOS_R2_AI_RESEARCH_AUTO_TRAIN=1 /usr/bin/flock -n $LOGDIR/train.lock $PY $LIVE/apps/api/kaos_r2_ai_cron.py >> $LOGDIR/train.log 2>&1 # KAOS_R2_RESEARCH_MANAGED" >>"$NEW"
BACKUP="$LOGDIR/crontab-before-$(date -u +%Y%m%dT%H%M%SZ).txt"
cp "$CUR" "$BACKUP"
crontab "$NEW"
echo "KAOS READ-ONLY RESEARCH CRONS INSTALLED"
echo "Pattern scanner: every 10m; shadow predictions: every 10m; trainer: one market/hour"
echo "Existing crons preserved; previous cron saved to $BACKUP"
echo "No website files modified; no broker order authority enabled."
echo "To inspect: crontab -l | grep KAOS_R2_RESEARCH_MANAGED"
