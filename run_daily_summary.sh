#!/bin/bash
# Generate daily summary and perform cleanup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "BARBOSSA DAILY SUMMARY & CLEANUP"
echo "Started: $(date)"
echo "================================================"

# Generate daily summary
python3 - <<'EOF'
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

work_dir = Path.cwd()
logs_dir = work_dir / 'logs'
summary_dir = work_dir / 'summaries'
summary_dir.mkdir(exist_ok=True)

today = datetime.now().strftime('%Y-%m-%d')
summary = {
    'date': today,
    'work_completed': {},
    'tickets_enriched': 0,
    'errors': [],
    'performance': {}
}

# Analyze work tally
tally_file = work_dir / 'work_tracking' / 'work_tally.json'
if tally_file.exists():
    with open(tally_file, 'r') as f:
        summary['work_completed'] = json.load(f)

# Check ticket enrichment
enrichment_state = work_dir / 'state' / 'ticket_enrichment.json'
if enrichment_state.exists():
    with open(enrichment_state, 'r') as f:
        data = json.load(f)
        summary['tickets_enriched'] = data.get('statistics', {}).get('total_enriched', 0)

# Count errors in logs
for log_file in logs_dir.glob(f'*{today}*.log'):
    with open(log_file, 'r') as f:
        errors = [line for line in f if 'ERROR' in line or 'CRITICAL' in line]
        if errors:
            summary['errors'].append({
                'file': log_file.name,
                'count': len(errors),
                'samples': errors[:3]
            })

# Save summary
summary_file = summary_dir / f'daily_summary_{today}.json'
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)

print(f"Daily summary saved to: {summary_file}")

# Generate markdown report
report = f"""# Barbossa Daily Report - {today}

## Work Completed
"""

for area, count in summary['work_completed'].items():
    report += f"- **{area}**: {count} sessions\n"

report += f"""
## Tickets Enriched
Total enriched issues: {summary['tickets_enriched']}

## Errors
"""

if summary['errors']:
    for error in summary['errors']:
        report += f"- {error['file']}: {error['count']} errors\n"
else:
    report += "No errors detected today ✅\n"

report_file = summary_dir / f'daily_report_{today}.md'
with open(report_file, 'w') as f:
    f.write(report)

print(f"Daily report saved to: {report_file}")
EOF

# Cleanup old logs (keep 30 days)
echo ""
echo "Cleaning up old logs..."
find "$SCRIPT_DIR/logs" -type f -name "*.log" -mtime +30 -delete
echo "✓ Removed logs older than 30 days"

# Compress logs from last week
echo "Compressing older logs..."
find "$SCRIPT_DIR/logs" -type f -name "*.log" -mtime +7 -exec gzip {} \;
echo "✓ Compressed logs older than 7 days"

# Clean cache
echo "Cleaning cache..."
find "$SCRIPT_DIR/cache" -type f -mtime +14 -delete
echo "✓ Removed cached files older than 14 days"

# Archive changelogs
if [ -d "$SCRIPT_DIR/changelogs" ]; then
    ARCHIVE_DIR="$SCRIPT_DIR/archives/changelogs/$(date +%Y-%m)"
    mkdir -p "$ARCHIVE_DIR"
    find "$SCRIPT_DIR/changelogs" -type f -name "*.md" -mtime +7 -exec mv {} "$ARCHIVE_DIR/" \;
    echo "✓ Archived changelogs older than 7 days"
fi

echo ""
echo "Daily summary and cleanup completed: $(date)"
echo "================================================"