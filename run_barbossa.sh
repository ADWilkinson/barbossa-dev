#!/bin/bash
# Barbossa cron execution wrapper
# This script is called by cron to run Barbossa autonomously

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin"
export HOME="/home/dappnode"

# Log file
LOG_FILE="$SCRIPT_DIR/logs/cron_$(date +%Y%m%d_%H%M%S).log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "Starting Barbossa autonomous execution"

# Check if we're in business hours (7:30am - 6:30pm UTC, Monday-Friday)
CURRENT_HOUR=$(date -u +%-H)  # %-H to avoid leading zeros (octal issue)
CURRENT_MINUTE=$(date -u +%-M)  # %-M to avoid leading zeros
CURRENT_DAY=$(date -u +%u)  # 1=Monday, 7=Sunday
CURRENT_TIME=$((CURRENT_HOUR * 60 + CURRENT_MINUTE))  # Convert to minutes since midnight

# Business hours: 7:30am (450 minutes) to 6:30pm (1110 minutes) UTC
BUSINESS_START=450  # 7:30am = 7*60 + 30
BUSINESS_END=1110   # 6:30pm = 18*60 + 30

# Check if it's a weekday (Monday=1 to Friday=5)
if [ $CURRENT_DAY -ge 1 ] && [ $CURRENT_DAY -le 5 ]; then
    # Check if we're within business hours
    if [ $CURRENT_TIME -ge $BUSINESS_START ] && [ $CURRENT_TIME -lt $BUSINESS_END ]; then
        log_message "Skipping execution: Within business hours (7:30am-6:30pm UTC, Mon-Fri)"
        log_message "Current UTC time: $(date -u '+%A %H:%M')"
        exit 0
    fi
fi

log_message "Outside business hours - proceeding with execution"

# Check if already running
if pgrep -f "barbossa.py" > /dev/null; then
    log_message "Barbossa is already running, skipping"
    exit 0
fi

# Check Claude CLI availability
if ! command -v claude &> /dev/null; then
    log_message "ERROR: Claude CLI not found in PATH"
    exit 1
fi

# Execute Barbossa with optional area argument
if [ "$#" -gt 0 ]; then
    log_message "Executing Barbossa with arguments: $@"
    python3 "$SCRIPT_DIR/barbossa.py" "$@" >> "$LOG_FILE" 2>&1
else
    log_message "Executing Barbossa (auto-selecting work area)..."
    python3 "$SCRIPT_DIR/barbossa.py" >> "$LOG_FILE" 2>&1
fi

log_message "Barbossa execution completed"

# Optional: Clean up old logs (older than 30 days)
find "$SCRIPT_DIR/logs" -name "*.log" -type f -mtime +30 -delete 2>/dev/null

exit 0