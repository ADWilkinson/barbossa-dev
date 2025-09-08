#!/bin/bash
# Cleanup cron script for Barbossa
# Runs automated cleanup to manage storage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin"
export HOME="/home/dappnode"

# Log file
LOG_FILE="$SCRIPT_DIR/logs/cleanup_$(date +%Y%m%d).log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "Starting storage cleanup"

# Check disk usage before cleanup
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
log_message "Current disk usage: ${DISK_USAGE}%"

# Run cleanup if disk usage is above 50% or on scheduled day
if [ "$DISK_USAGE" -gt 50 ] || [ "$(date +%d)" = "01" ] || [ "$(date +%d)" = "15" ]; then
    log_message "Running cleanup (disk usage: ${DISK_USAGE}%)"
    python3 "$SCRIPT_DIR/barbossa.py" --cleanup >> "$LOG_FILE" 2>&1
else
    log_message "Skipping cleanup (disk usage: ${DISK_USAGE}% is acceptable)"
fi

log_message "Cleanup check completed"
exit 0