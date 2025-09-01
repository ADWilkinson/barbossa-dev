#!/bin/bash
"""
Setup Barbossa Personal Assistant v4 Cron Schedule
Runs daily at 7 AM to enrich new Todo tickets before work starts
"""

echo "🏴‍☠️ Setting up Barbossa Personal Assistant Cron"
echo "================================================"

# Script to run
BARBOSSA_SCRIPT="/home/dappnode/barbossa-engineer/run_barbossa_v4.sh"

# Create the run script
cat > "$BARBOSSA_SCRIPT" << 'EOF'
#!/bin/bash
# Barbossa v4 Daily Run Script

cd /home/dappnode/barbossa-engineer

# Set up environment
source venv_personal_assistant/bin/activate
set -a
source .env.personal_assistant
set +a

# Add timestamp to log
echo "=====================================" >> logs/barbossa/cron.log
echo "Starting Barbossa - $(date)" >> logs/barbossa/cron.log
echo "=====================================" >> logs/barbossa/cron.log

# Run Barbossa v4
python3 barbossa_personal_assistant_v4.py >> logs/barbossa/cron.log 2>&1

# Log completion
echo "Completed - $(date)" >> logs/barbossa/cron.log
echo "" >> logs/barbossa/cron.log
EOF

chmod +x "$BARBOSSA_SCRIPT"

# Add to crontab (avoiding duplicates)
CRON_ENTRY="0 7 * * * $BARBOSSA_SCRIPT"

# Check if already in crontab
if crontab -l 2>/dev/null | grep -q "barbossa_personal_assistant"; then
    echo "⚠️  Barbossa cron already exists. Updating..."
    # Remove old entry
    (crontab -l 2>/dev/null | grep -v "barbossa_personal_assistant") | crontab -
fi

# Add new cron entry
(crontab -l 2>/dev/null; echo "# Barbossa Personal Assistant - Daily Todo Enrichment") | crontab -
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron scheduled for 7 AM daily"
echo ""
echo "📋 Current crontab:"
crontab -l | grep -A1 -B1 barbossa

echo ""
echo "🔧 Alternative Schedules (edit crontab -e):"
echo "  Twice daily (7 AM & 1 PM):  0 7,13 * * *"
echo "  Every 6 hours:               0 */6 * * *"
echo "  Weekdays only at 7 AM:       0 7 * * 1-5"
echo "  Monday/Thursday at 7 AM:     0 7 * * 1,4"
echo ""
echo "📝 Logs will be at: logs/barbossa/cron.log"
echo ""
echo "🎯 What will happen:"
echo "  1. Check for new Todo tickets in Linear"
echo "  2. Enrich unprocessed tickets with dev context"
echo "  3. Find improvements in Davy Jones/Barbossa"
echo "  4. Skip already-processed items (state tracking)"
echo "  5. Log operations to logs/barbossa/"