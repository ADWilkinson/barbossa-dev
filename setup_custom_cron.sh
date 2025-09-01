#!/bin/bash
# Custom Barbossa Cron Setup - All systems except personal projects
# This sets up the enhanced scheduling without personal project automation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "BARBOSSA CUSTOM SCHEDULING SYSTEM"
echo "(Without Personal Projects Automation)"
echo "================================================"
echo ""

# Function to add or update a cron job
add_cron_job() {
    local schedule="$1"
    local command="$2"
    local description="$3"
    
    # Check if the job already exists
    if crontab -l 2>/dev/null | grep -q "$command"; then
        echo "  ✓ $description already scheduled"
    else
        # Add the cron job
        (crontab -l 2>/dev/null; echo "$schedule $command") | crontab -
        echo "  + Added: $description"
    fi
}

echo "Setting up Barbossa Custom Scheduling..."
echo ""

# 1. TICKET ENRICHMENT - Daily at 9 AM UTC
echo "1. Ticket Enrichment (Daily at 09:00 UTC)"
add_cron_job "0 9 * * *" \
    "$SCRIPT_DIR/run_ticket_enrichment.sh >> $SCRIPT_DIR/logs/ticket_enrichment_cron.log 2>&1" \
    "Daily ticket enrichment"

# 2. DAVY JONES INTERN - Every 8 hours (moderate frequency)
echo ""
echo "2. Davy Jones Intern (Every 8 hours: 02:00, 10:00, 18:00 UTC)"
add_cron_job "0 2,10,18 * * *" \
    "$SCRIPT_DIR/run_barbossa.sh --area davy_jones >> $SCRIPT_DIR/logs/davy_jones_cron.log 2>&1" \
    "Davy Jones improvements"

# 3. INFRASTRUCTURE - Every 2 hours (monitoring & quick fixes only)
echo ""
echo "3. Infrastructure Check (Every 2 hours)"
add_cron_job "0 */2 * * *" \
    "$SCRIPT_DIR/run_infrastructure_check.sh >> $SCRIPT_DIR/logs/infrastructure_cron.log 2>&1" \
    "Infrastructure monitoring"

# 4. BARBOSSA SELF-IMPROVEMENT - Weekly on Sundays at 3 AM UTC
echo ""
echo "4. Barbossa Self-Improvement (Weekly on Sundays at 03:00 UTC)"
add_cron_job "0 3 * * 0" \
    "$SCRIPT_DIR/run_barbossa.sh --area barbossa_self >> $SCRIPT_DIR/logs/barbossa_self_cron.log 2>&1" \
    "Barbossa self-improvement"

# 5. DAILY SUMMARY & CLEANUP - Daily at 23:00 UTC
echo ""
echo "5. Daily Summary & Cleanup (Daily at 23:00 UTC)"
add_cron_job "0 23 * * *" \
    "$SCRIPT_DIR/run_daily_summary.sh >> $SCRIPT_DIR/logs/daily_summary_cron.log 2>&1" \
    "Daily summary and cleanup"

# 6. PERFORMANCE OPTIMIZATION - Every 4 hours
echo ""
echo "6. Performance Monitoring (Every 4 hours)"
add_cron_job "30 */4 * * *" \
    "$SCRIPT_DIR/run_performance_check.sh >> $SCRIPT_DIR/logs/performance_cron.log 2>&1" \
    "Performance optimization check"

echo ""
echo "================================================"
echo "CURRENT BARBOSSA CRON SCHEDULE:"
echo "================================================"
echo ""
crontab -l 2>/dev/null | grep -E "(barbossa|ticket_enrichment|infrastructure|performance|daily_summary)" | while read -r line; do
    echo "  $line"
done

echo ""
echo "================================================"
echo "ACTIVE SCHEDULE SUMMARY:"
echo "================================================"
echo ""
echo "DAILY TASKS:"
echo "  09:00 UTC - Ticket Enrichment (GitHub/Linear issues)"
echo "  23:00 UTC - Daily Summary & Cleanup"
echo ""
echo "FREQUENT TASKS:"
echo "  Every 2h  - Infrastructure monitoring (critical only)"
echo "  Every 4h  - Performance optimization check"
echo "  Every 8h  - Davy Jones Intern improvements"
echo ""
echo "WEEKLY TASKS:"
echo "  Sunday 03:00 UTC - Barbossa self-improvement"
echo ""
echo "DISABLED:"
echo "  ❌ Personal Projects (manual trigger only)"
echo ""
echo "================================================"
echo ""
echo "To manually trigger personal projects:"
echo "  python3 barbossa.py --area personal_projects"
echo ""
echo "Setup complete! Barbossa is running without personal project automation."