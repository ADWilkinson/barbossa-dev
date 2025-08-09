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

# Execute Barbossa (let it select work area automatically)
log_message "Executing Barbossa..."
python3 "$SCRIPT_DIR/barbossa.py" >> "$LOG_FILE" 2>&1

log_message "Barbossa execution completed"

# Optional: Clean up old logs (older than 30 days)
find "$SCRIPT_DIR/logs" -name "*.log" -type f -mtime +30 -delete 2>/dev/null

exit 0