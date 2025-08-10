#!/bin/bash
# Setup cron job for Enhanced Barbossa automatic execution

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up Enhanced Barbossa cron job..."

# Create the cron job entry (runs every 4 hours)
CRON_JOB="0 */4 * * * $SCRIPT_DIR/run_barbossa.sh"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_barbossa.sh"; then
    echo "Enhanced Barbossa cron job already exists"
else
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Enhanced Barbossa cron job added successfully"
fi

# Display current crontab
echo ""
echo "Current cron jobs:"
crontab -l | grep barbossa

echo ""
echo "Enhanced Barbossa will run automatically every 4 hours"
echo "Next runs will be at: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC"
echo ""
echo "To manually trigger: python3 barbossa_enhanced.py"
echo "To check status: python3 barbossa_enhanced.py --status"
echo "To view logs: tail -f logs/cron_*.log"