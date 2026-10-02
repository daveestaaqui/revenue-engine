#!/usr/bin/env bash
set -eo pipefail

REPO_DIR="/Users/davidmahler/revenue-engine"
LOG_FILE="${REPO_DIR}/output/local_morning_dispatch.log"
mkdir -p "${REPO_DIR}/output"

echo "==================================================" >> "${LOG_FILE}"
echo "[$(date)] Running Local Morning Feed Failover Check" >> "${LOG_FILE}"

cd "${REPO_DIR}"

# Pull latest state to check if GitHub already dispatched today
git pull --rebase origin main >> "${LOG_FILE}" 2>&1 || true

# Execute sentinel failover check (checks idempotency log, sends only if missing)
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi

python3 "${REPO_DIR}/portal/sentinel_morning_failover.py" >> "${LOG_FILE}" 2>&1
python3 "${REPO_DIR}/outreach/schedule_alden_followup.py" >> "${LOG_FILE}" 2>&1 || true

echo "[$(date)] Failover check finished." >> "${LOG_FILE}"
