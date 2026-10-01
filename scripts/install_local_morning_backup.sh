#!/usr/bin/env bash
# ==============================================================================
# Surplus Docket — Local macOS Morning Feed Redundancy Installer
# ==============================================================================
# Installs a launchd LaunchAgent on this Mac to check and trigger the 7:00 AM
# morning feed at 7:05 AM EST Monday through Friday.
#
# Idempotency:
# The local script pulls latest git changes and inspects portal/daily_dispatch_log.json.
# If GitHub Actions already dispatched today's feed at 7:00 AM, it does nothing and exits.
# If GitHub Actions was delayed or skipped, the Mac triggers the dispatch immediately!
# ==============================================================================

set -euo pipefail

REPO_DIR="/Users/davidmahler/revenue-engine"
PLIST_LABEL="com.surplusdocket.morningfeed"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
RUNNER_SCRIPT="${REPO_DIR}/scripts/run_local_morning_feed.sh"

echo "=== Surplus Docket: Installing Local Morning Feed Failover Agent ==="

# 1. Create the wrapper script
cat << 'EOF' > "${RUNNER_SCRIPT}"
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

echo "[$(date)] Failover check finished." >> "${LOG_FILE}"
EOF

chmod +x "${RUNNER_SCRIPT}"
echo "✓ Created runner script at: ${RUNNER_SCRIPT}"

# 2. Create the launchd plist
mkdir -p "$HOME/Library/LaunchAgents"

cat << EOF > "${PLIST_PATH}"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${RUNNER_SCRIPT}</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <!-- Monday through Friday at 7:05 AM local time -->
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>5</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>5</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>5</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>5</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>5</integer></dict>
        <!-- Second failover check at 7:35 AM -->
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>35</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>35</integer></dict>
    </array>
    <key>StandardOutPath</key>
    <string>${REPO_DIR}/output/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${REPO_DIR}/output/launchd_stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF

echo "✓ Created launchd configuration at: ${PLIST_PATH}"

# 3. Load the launchd agent
launchctl unload "${PLIST_PATH}" 2>/dev/null || true
launchctl load "${PLIST_PATH}"

echo "✅ Successfully loaded local launchd agent: ${PLIST_LABEL}"
echo "   It will trigger Monday-Friday at 7:05 AM & 7:35 AM."
echo "   Zero duplicate risk: strictly checks daily_dispatch_log.json before sending."
