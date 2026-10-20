#!/usr/bin/env bash
set -eo pipefail

REPO_DIR="/Users/davidmahler/revenue-engine"
LOG_FILE="${REPO_DIR}/output/local_morning_dispatch.log"
mkdir -p "${REPO_DIR}/output"

echo "==================================================" >> "${LOG_FILE}"
echo "[$(date)] Starting Surplus Docket Local Morning Dispatch (Target: 7:00 AM EST Sharp)" >> "${LOG_FILE}"

cd "${REPO_DIR}"

# Determine verified Python 3 binary with pandas & dependencies
PYTHON_BIN=""
for candidate in "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" "/opt/homebrew/bin/python3" "$(which python3 2>/dev/null)"; do
  if [ -x "$candidate" ] && "$candidate" -c "import pandas" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(which python3)"
fi

echo "[$(date)] Using Python interpreter: ${PYTHON_BIN}" >> "${LOG_FILE}"

# If dispatch log was modified locally earlier, commit it before pulling
if [ -n "$(git status --porcelain portal/daily_dispatch_log.json 2>/dev/null)" ]; then
  git add portal/daily_dispatch_log.json
  git commit -m "chore(feed): record local morning dispatch log [skip ci]" >> "${LOG_FILE}" 2>&1 || true
fi

# Pull latest state to check if GitHub already dispatched today
git pull --rebase origin main >> "${LOG_FILE}" 2>&1 || true

# Export environment variables safely from .env if present
if [ -f ".env" ]; then
  set -a
  source .env 2>/dev/null || true
  set +a
fi

export PYTHONPATH="${REPO_DIR}"

# Execute 7:00 AM EST Morning Court Intelligence Feed Dispatch directly
# (Idempotent: skips cleanly if already dispatched today; respects tight 7:00 - 7:30 AM window)
"$PYTHON_BIN" -u "${REPO_DIR}/portal/dispatch_morning_feed.py" --send >> "${LOG_FILE}" 2>&1

# Run scheduled client follow-up sentinel if configured
"$PYTHON_BIN" -u "${REPO_DIR}/outreach/schedule_alden_followup.py" >> "${LOG_FILE}" 2>&1 || true

# If dispatched and updated daily_dispatch_log.json, commit and push to remote so GitHub Actions stays in sync
if [ -n "$(git status --porcelain portal/daily_dispatch_log.json 2>/dev/null)" ]; then
  echo "[$(date)] Syncing local morning dispatch record to GitHub..." >> "${LOG_FILE}"
  git add portal/daily_dispatch_log.json
  git commit -m "chore(feed): record local morning dispatch log [skip ci]" >> "${LOG_FILE}" 2>&1 || true
  for attempt in 1 2 3; do
    git pull --rebase origin main >> "${LOG_FILE}" 2>&1 && git push origin main >> "${LOG_FILE}" 2>&1 && break || sleep 3
  done
fi

echo "[$(date)] Morning dispatch run complete." >> "${LOG_FILE}"
