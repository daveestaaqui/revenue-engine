#!/bin/bash
# ==============================================================================
# Surplus Docket — Local Morning Dispatch Daemon Runner (7:00 AM EST)
# ==============================================================================
# Runs locally on macOS via launchd to guarantee 7:00 AM sharp delivery,
# bypassing GitHub Actions schedule queue delays completely.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$REPO_DIR/output"
LOG_FILE="$LOG_DIR/morning_dispatch_local.log"

mkdir -p "$LOG_DIR"
exec >> "$LOG_FILE" 2>&1

echo "======================================================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Starting Surplus Docket Morning Feed"
echo "======================================================================"

cd "$REPO_DIR"

# Ensure environment variables from .env are loaded
if [ -f "$REPO_DIR/.env" ]; then
    export $(grep -v '^#' "$REPO_DIR/.env" | xargs)
fi

export PYTHONPATH="$REPO_DIR"

# Step 1: Attempt fast pull if online
git pull --rebase origin main --quiet || true

# Step 2: Run feed generation if raw files were updated
python3 portal/feed_generator.py --quiet 2>/dev/null || python3 portal/feed_generator.py

# Step 3: Dispatch Morning Feed (idempotent — skips if already sent today)
python3 portal/dispatch_morning_feed.py --send

# Step 4: Run 7-day retention sentinel
python3 portal/trial_retention_sentinel.py --send || true

# Step 5: If log updated, push upstream so GitHub Actions knows it's done
if git status --porcelain portal/daily_dispatch_log.json portal/trial_lifecycle_log.json | grep -q .; then
    git config --global user.name "Surplus Docket Bot"
    git config --global user.email "bot@surplusdocket.com"
    git add portal/daily_dispatch_log.json portal/trial_lifecycle_log.json
    git commit -m "chore(feed): record local morning dispatch [skip ci]" || true
    git push origin main || true
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] Surplus Docket Morning Feed finished successfully."
