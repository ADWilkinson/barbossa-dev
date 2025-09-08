#!/bin/bash
# Health check cron script for Barbossa
# Runs comprehensive health checks and logs results

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin"
export HOME="/home/dappnode"

# Log file
LOG_FILE="$SCRIPT_DIR/logs/health_check_$(date +%Y%m%d).log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "Starting health check"

# Run health check
python3 "$SCRIPT_DIR/barbossa.py" --health >> "$LOG_FILE" 2>&1

# Check if health is critical and send alert if needed
if grep -q "Overall Status: CRITICAL" "$LOG_FILE"; then
    log_message "ALERT: System health is CRITICAL"
    # Could add email/webhook notification here
fi

log_message "Health check completed"
exit 0