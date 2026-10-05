#!/usr/bin/env bash
set -eo pipefail

REPO_DIR="/Users/davidmahler/revenue-engine"
LOG_FILE="${REPO_DIR}/output/local_morning_dispatch.log"
mkdir -p "${REPO_DIR}/output"

echo "==================================================" >> "${LOG_FILE}"
echo "[$(date)] Running Local Morning Feed Failover Check" >> "${LOG_FILE}"

cd "${REPO_DIR}"

# If dispatch log was modified locally earlier, commit it before pulling
if [ -n "$(git status --porcelain portal/daily_dispatch_log.json 2>/dev/null)" ]; then
  git add portal/daily_dispatch_log.json
  git commit -m "chore(feed): record local morning dispatch log [skip ci]" >> "${LOG_FILE}" 2>&1 || true
fi

# Pull latest state to check if GitHub already dispatched today
git pull --rebase origin main >> "${LOG_FILE}" 2>&1 || true

# Execute sentinel failover check (checks idempotency log, sends only if missing)
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi

python3 "${REPO_DIR}/portal/sentinel_morning_failover.py" >> "${LOG_FILE}" 2>&1
python3 "${REPO_DIR}/outreach/schedule_alden_followup.py" >> "${LOG_FILE}" 2>&1 || true

# If sentinel dispatched and updated daily_dispatch_log.json, commit and push to remote so GitHub Actions stays in sync
if [ -n "$(git status --porcelain portal/daily_dispatch_log.json 2>/dev/null)" ]; then
  echo "[$(date)] Syncing local morning dispatch record to GitHub..." >> "${LOG_FILE}"
  git add portal/daily_dispatch_log.json
  git commit -m "chore(feed): record local morning dispatch log [skip ci]" >> "${LOG_FILE}" 2>&1 || true
  for attempt in 1 2 3; do
    git pull --rebase origin main >> "${LOG_FILE}" 2>&1 && git push origin main >> "${LOG_FILE}" 2>&1 && break || sleep 3
  done
fi

echo "[$(date)] Failover check finished." >> "${LOG_FILE}"
