#!/usr/bin/env python3
"""
Generate crontab from config/repositories.json schedule settings.

Default schedule (if not configured):
- Engineer: every 2 hours at :00 (12x daily)
- Tech Lead: 1h after engineer (12x daily) - avoids collision, reviews fresh PRs
- Discovery: 6x daily offset from engineer - keeps backlog stocked
- Product Manager: 3x daily offset - quality over quantity
- Auditor: daily at 06:30

Schedule philosophy: Offset agents to avoid resource contention and ensure
fresh work is reviewed/processed in the next cycle.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple


def validate_cron_field(value: str, min_val: int, max_val: int, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a single cron field value.

    Supports:
    - Single values: "5", "10"
    - Wildcards: "*"
    - Step values: "*/5", "0-23/2"
    - Ranges: "1-5", "0-23"
    - Lists: "1,3,5", "0,6,12,18"

    Returns (is_valid, error_message)
    """
    if value == '*':
        return True, None

    # Step value: */N or range/N
    if '/' in value:
        base, step = value.split('/', 1)
        if not step.isdigit() or int(step) < 1:
            return False, f"{field_name}: invalid step value '{step}'"
        if base == '*':
            return True, None
        # Validate the base (it's a range like 0-23)
        value = base

    # List value: comma-separated
    if ',' in value:
        parts = value.split(',')
        for part in parts:
            is_valid, err = validate_cron_field(part.strip(), min_val, max_val, field_name)
            if not is_valid:
                return False, err
        return True, None

    # Range value: min-max
    if '-' in value:
        parts = value.split('-', 1)
        if len(parts) != 2:
            return False, f"{field_name}: invalid range '{value}'"
        try:
            start, end = int(parts[0]), int(parts[1])
            if start < min_val or start > max_val:
                return False, f"{field_name}: range start {start} out of bounds ({min_val}-{max_val})"
            if end < min_val or end > max_val:
                return False, f"{field_name}: range end {end} out of bounds ({min_val}-{max_val})"
            if start > end:
                return False, f"{field_name}: range start {start} greater than end {end}"
            return True, None
        except ValueError:
            return False, f"{field_name}: invalid range '{value}'"

    # Single numeric value
    if not value.isdigit():
        return False, f"{field_name}: invalid value '{value}'"

    num = int(value)
    if num < min_val or num > max_val:
        return False, f"{field_name}: value {num} out of bounds ({min_val}-{max_val})"

    return True, None


def validate_cron_expression(cron_expr: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a cron expression for semantic correctness.

    Validates:
    - Correct number of fields (5)
    - Minute: 0-59
    - Hour: 0-23
    - Day of month: 1-31
    - Month: 1-12
    - Day of week: 0-7 (0 and 7 both mean Sunday)

    Returns (is_valid, error_message)
    """
    parts = cron_expr.split()
    if len(parts) != 5:
        return False, f"expected 5 fields, got {len(parts)}"

    field_specs = [
        (parts[0], 0, 59, 'minute'),
        (parts[1], 0, 23, 'hour'),
        (parts[2], 1, 31, 'day-of-month'),
        (parts[3], 1, 12, 'month'),
        (parts[4], 0, 7, 'day-of-week'),
    ]

    for value, min_val, max_val, field_name in field_specs:
        is_valid, err = validate_cron_field(value, min_val, max_val, field_name)
        if not is_valid:
            return False, err

    return True, None


# Default schedules (cron format)
# Optimized to avoid resource contention and ensure fresh work is processed
DEFAULTS = {
    'engineer': {
        'cron': '0 0,2,4,6,8,10,12,14,16,18,20,22 * * *',
        'description': '12x daily at :00 (every 2 hours)'
    },
    'tech_lead': {
        'cron': '0 1,3,5,7,9,11,13,15,17,19,21,23 * * *',
        'description': '12x daily at :00 (1h after engineer, reviews fresh PRs)'
    },
    'discovery': {
        'cron': '0 1,5,9,13,17,21 * * *',
        'description': '6x daily offset (keeps backlog stocked)'
    },
    'product_manager': {
        'cron': '0 3,11,19 * * *',
        'description': '3x daily offset (quality over quantity)'
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

    # Validate as a cron expression with semantic checking
    is_valid, error = validate_cron_expression(schedule_value)
    if is_valid:
        return schedule_value

    print(f"Warning: Invalid schedule '{schedule_value}': {error}. Using default.", file=sys.stderr)
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
