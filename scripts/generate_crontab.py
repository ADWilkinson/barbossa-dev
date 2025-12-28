#!/usr/bin/env python3
"""
Generate crontab from config/repositories.json schedule settings.

Default schedule (if not configured):
- Engineer: every 2 hours at :00
- Tech Lead: every 2 hours at :35
- Discovery: 4x daily (00:00, 06:00, 12:00, 18:00)
- Product Manager: 3x daily (07:00, 15:00, 23:00)
- Auditor: daily at 06:30
"""

import json
import sys
from pathlib import Path


# Default schedules (cron format)
DEFAULTS = {
    'engineer': {
        'cron': '0 0,2,4,6,8,10,12,14,16,18,20,22 * * *',
        'description': 'Every 2 hours at :00'
    },
    'tech_lead': {
        'cron': '35 0,2,4,6,8,10,12,14,16,18,20,22 * * *',
        'description': 'Every 2 hours at :35 (after engineer)'
    },
    'discovery': {
        'cron': '0 0,6,12,18 * * *',
        'description': '4x daily (00:00, 06:00, 12:00, 18:00)'
    },
    'product_manager': {
        'cron': '0 7,15,23 * * *',
        'description': '3x daily (07:00, 15:00, 23:00)'
    },
    'auditor': {
        'cron': '30 6 * * *',
        'description': 'Daily at 06:30'
    }
}

# Human-readable schedule presets
PRESETS = {
    # Engineer presets
    'every_hour': '0 * * * *',
    'every_2_hours': '0 0,2,4,6,8,10,12,14,16,18,20,22 * * *',
    'every_3_hours': '0 0,3,6,9,12,15,18,21 * * *',
    'every_4_hours': '0 0,4,8,12,16,20 * * *',
    'every_6_hours': '0 0,6,12,18 * * *',

    # Daily presets
    'daily_morning': '0 9 * * *',
    'daily_evening': '0 18 * * *',
    'daily_night': '0 2 * * *',

    # Multiple times daily
    '2x_daily': '0 9,18 * * *',
    '3x_daily': '0 7,15,23 * * *',
    '4x_daily': '0 0,6,12,18 * * *',

    # Disabled
    'disabled': None,
    'never': None,
}


def resolve_schedule(schedule_value: str) -> str:
    """Convert preset name or cron expression to cron format."""
    if not schedule_value:
        return None

    # Check if it's a preset
    if schedule_value.lower() in PRESETS:
        return PRESETS[schedule_value.lower()]

    # Assume it's a cron expression
    # Basic validation: should have 5 space-separated parts
    parts = schedule_value.split()
    if len(parts) == 5:
        return schedule_value

    print(f"Warning: Invalid schedule '{schedule_value}', using default", file=sys.stderr)
    return None


def generate_crontab(config_path: Path) -> str:
    """Generate crontab content from config."""

    # Load config
    config = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config: {e}", file=sys.stderr)

    settings = config.get('settings', {})
    schedule = settings.get('schedule', {})

    lines = [
        "# Barbossa Crontab - Generated from config",
        "# Edit config/repositories.json to change schedule",
        "",
        "SHELL=/bin/bash",
        "PATH=/usr/local/bin:/usr/bin:/bin",
        "",
    ]

    # Engineer
    engineer_settings = settings.get('engineer', {})
    if engineer_settings.get('enabled', True):
        cron = resolve_schedule(schedule.get('engineer')) or DEFAULTS['engineer']['cron']
        lines.append(f"# Engineer - {DEFAULTS['engineer']['description']}")
        lines.append(f'{cron} cd /app && PYTHONPATH=/app/src python3 -m barbossa.agents.engineer >> /app/logs/cron.log 2>&1')
        lines.append("")

    # Tech Lead
    tech_lead_settings = settings.get('tech_lead', {})
    if tech_lead_settings.get('enabled', True):
        cron = resolve_schedule(schedule.get('tech_lead')) or DEFAULTS['tech_lead']['cron']
        lines.append(f"# Tech Lead - {DEFAULTS['tech_lead']['description']}")
        lines.append(f'{cron} cd /app && PYTHONPATH=/app/src python3 -m barbossa.agents.tech_lead >> /app/logs/tech_lead_cron.log 2>&1')
        lines.append("")

    # Discovery
    discovery_settings = settings.get('discovery', {})
    if discovery_settings.get('enabled', True):
        cron = resolve_schedule(schedule.get('discovery')) or DEFAULTS['discovery']['cron']
        lines.append(f"# Discovery - {DEFAULTS['discovery']['description']}")
        lines.append(f'{cron} cd /app && PYTHONPATH=/app/src python3 -m barbossa.agents.discovery >> /app/logs/discovery_cron.log 2>&1')
        lines.append("")

    # Product Manager
    product_settings = settings.get('product_manager', {})
    if product_settings.get('enabled', True):
        cron = resolve_schedule(schedule.get('product_manager')) or DEFAULTS['product_manager']['cron']
        lines.append(f"# Product Manager - {DEFAULTS['product_manager']['description']}")
        lines.append(f'{cron} cd /app && PYTHONPATH=/app/src python3 -m barbossa.agents.product >> /app/logs/product_cron.log 2>&1')
        lines.append("")

    # Auditor
    auditor_settings = settings.get('auditor', {})
    if auditor_settings.get('enabled', True):
        cron = resolve_schedule(schedule.get('auditor')) or DEFAULTS['auditor']['cron']
        lines.append(f"# Auditor - {DEFAULTS['auditor']['description']}")
        lines.append(f'{cron} cd /app && PYTHONPATH=/app/src python3 -m barbossa.agents.auditor --days 7 >> /app/logs/auditor_cron.log 2>&1')
        lines.append("")

    # Required empty line at end
    lines.append("")

    return "\n".join(lines)


def main():
    config_path = Path('/app/config/repositories.json')

    # Allow override via argument
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])

    crontab = generate_crontab(config_path)
    print(crontab)


if __name__ == '__main__':
    main()
