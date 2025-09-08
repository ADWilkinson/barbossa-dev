#!/bin/bash
# Weekly diagnostics script for Barbossa
# Runs comprehensive system diagnostics

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin"
export HOME="/home/dappnode"

# Log file
LOG_FILE="$SCRIPT_DIR/logs/diagnostics_$(date +%Y%m%d).log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "Starting comprehensive diagnostics"

# Run diagnostics
python3 "$SCRIPT_DIR/barbossa.py" --diagnostics >> "$LOG_FILE" 2>&1

# Create summary for email/notification if needed
if [ -f "$SCRIPT_DIR/diagnostics/diagnostics_$(date +%Y%m%d)_*.json" ]; then
    log_message "Diagnostics report generated successfully"
fi

log_message "Diagnostics completed"
exit 0