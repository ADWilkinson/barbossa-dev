#!/usr/bin/env python3
"""
Tests for crontab generation and cron expression validation.
"""

import unittest
import sys
from pathlib import Path

# Add scripts directory to path for importing
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from generate_crontab import (
    validate_cron_field,
    validate_cron_expression,
    resolve_schedule,
    PRESETS,
    DEFAULTS
)


class TestValidateCronField(unittest.TestCase):
    """Test individual cron field validation."""

    def test_wildcard(self):
        """Wildcard (*) should always be valid."""
        is_valid, err = validate_cron_field('*', 0, 59, 'minute')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_single_value_in_range(self):
        """Single numeric value within range should be valid."""
        is_valid, err = validate_cron_field('30', 0, 59, 'minute')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_single_value_at_min(self):
        """Value at minimum boundary should be valid."""
        is_valid, err = validate_cron_field('0', 0, 59, 'minute')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_single_value_at_max(self):
        """Value at maximum boundary should be valid."""
        is_valid, err = validate_cron_field('59', 0, 59, 'minute')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_single_value_below_min(self):
        """Value below minimum should be invalid."""
        is_valid, err = validate_cron_field('0', 1, 31, 'day-of-month')
        self.assertFalse(is_valid)
        self.assertIn('out of bounds', err)

    def test_single_value_above_max(self):
        """Value above maximum should be invalid."""
        is_valid, err = validate_cron_field('60', 0, 59, 'minute')
        self.assertFalse(is_valid)
        self.assertIn('out of bounds', err)

    def test_invalid_hour_25(self):
        """Hour 25 should be invalid (common user error)."""
        is_valid, err = validate_cron_field('25', 0, 23, 'hour')
        self.assertFalse(is_valid)
        self.assertIn('out of bounds', err)
        self.assertIn('0-23', err)

    def test_step_value_wildcard(self):
        """Step value with wildcard (*/5) should be valid."""
        is_valid, err = validate_cron_field('*/5', 0, 59, 'minute')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_step_value_with_range(self):
        """Step value with range (0-23/2) should be valid."""
        is_valid, err = validate_cron_field('0-23/2', 0, 23, 'hour')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_step_value_zero(self):
        """Step value of 0 should be invalid."""
        is_valid, err = validate_cron_field('*/0', 0, 59, 'minute')
        self.assertFalse(is_valid)
        self.assertIn('invalid step', err)

    def test_step_value_non_numeric(self):
        """Non-numeric step value should be invalid."""
        is_valid, err = validate_cron_field('*/abc', 0, 59, 'minute')
        self.assertFalse(is_valid)
        self.assertIn('invalid step', err)

    def test_range_valid(self):
        """Valid range (1-5) should pass."""
        is_valid, err = validate_cron_field('1-5', 1, 31, 'day-of-month')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_range_start_out_of_bounds(self):
        """Range with start below minimum should be invalid."""
        is_valid, err = validate_cron_field('0-5', 1, 31, 'day-of-month')
        self.assertFalse(is_valid)
        self.assertIn('range start', err)

    def test_range_end_out_of_bounds(self):
        """Range with end above maximum should be invalid."""
        is_valid, err = validate_cron_field('1-32', 1, 31, 'day-of-month')
        self.assertFalse(is_valid)
        self.assertIn('range end', err)

    def test_range_start_greater_than_end(self):
        """Range with start > end should be invalid."""
        is_valid, err = validate_cron_field('10-5', 0, 23, 'hour')
        self.assertFalse(is_valid)
        self.assertIn('greater than end', err)

    def test_list_valid(self):
        """Valid list (0,6,12,18) should pass."""
        is_valid, err = validate_cron_field('0,6,12,18', 0, 23, 'hour')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_list_with_invalid_value(self):
        """List containing invalid value should fail."""
        is_valid, err = validate_cron_field('0,6,25,18', 0, 23, 'hour')
        self.assertFalse(is_valid)
        self.assertIn('out of bounds', err)

    def test_non_numeric_value(self):
        """Non-numeric value should be invalid."""
        is_valid, err = validate_cron_field('abc', 0, 59, 'minute')
        self.assertFalse(is_valid)
        self.assertIn('invalid value', err)


class TestValidateCronExpression(unittest.TestCase):
    """Test full cron expression validation."""

    def test_valid_simple(self):
        """Simple valid cron should pass."""
        is_valid, err = validate_cron_expression('0 12 * * *')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_valid_complex(self):
        """Complex valid cron with lists should pass."""
        is_valid, err = validate_cron_expression('0 0,6,12,18 * * *')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_valid_every_minute(self):
        """Every minute cron should pass."""
        is_valid, err = validate_cron_expression('* * * * *')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_invalid_too_few_fields(self):
        """Cron with fewer than 5 fields should fail."""
        is_valid, err = validate_cron_expression('0 12 * *')
        self.assertFalse(is_valid)
        self.assertIn('expected 5 fields', err)

    def test_invalid_too_many_fields(self):
        """Cron with more than 5 fields should fail."""
        is_valid, err = validate_cron_expression('0 12 * * * *')
        self.assertFalse(is_valid)
        self.assertIn('expected 5 fields', err)

    def test_invalid_hour_99(self):
        """Hour 99 should be rejected."""
        is_valid, err = validate_cron_expression('0 99 * * *')
        self.assertFalse(is_valid)
        self.assertIn('hour', err)
        self.assertIn('out of bounds', err)

    def test_invalid_minute_60(self):
        """Minute 60 should be rejected."""
        is_valid, err = validate_cron_expression('60 12 * * *')
        self.assertFalse(is_valid)
        self.assertIn('minute', err)

    def test_invalid_day_32(self):
        """Day 32 should be rejected."""
        is_valid, err = validate_cron_expression('0 12 32 * *')
        self.assertFalse(is_valid)
        self.assertIn('day-of-month', err)

    def test_invalid_day_0(self):
        """Day 0 should be rejected (days are 1-31)."""
        is_valid, err = validate_cron_expression('0 12 0 * *')
        self.assertFalse(is_valid)
        self.assertIn('day-of-month', err)

    def test_invalid_month_13(self):
        """Month 13 should be rejected."""
        is_valid, err = validate_cron_expression('0 12 * 13 *')
        self.assertFalse(is_valid)
        self.assertIn('month', err)

    def test_invalid_month_0(self):
        """Month 0 should be rejected (months are 1-12)."""
        is_valid, err = validate_cron_expression('0 12 * 0 *')
        self.assertFalse(is_valid)
        self.assertIn('month', err)

    def test_valid_day_of_week_7(self):
        """Day of week 7 (Sunday) should be valid."""
        is_valid, err = validate_cron_expression('0 12 * * 7')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_valid_day_of_week_0(self):
        """Day of week 0 (Sunday) should be valid."""
        is_valid, err = validate_cron_expression('0 12 * * 0')
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_invalid_day_of_week_8(self):
        """Day of week 8 should be rejected."""
        is_valid, err = validate_cron_expression('0 12 * * 8')
        self.assertFalse(is_valid)
        self.assertIn('day-of-week', err)

    def test_all_defaults_valid(self):
        """All default schedules should be valid."""
        for agent, config in DEFAULTS.items():
            with self.subTest(agent=agent):
                is_valid, err = validate_cron_expression(config['cron'])
                self.assertTrue(is_valid, f"{agent} default cron is invalid: {err}")

    def test_all_presets_valid(self):
        """All non-None presets should be valid."""
        for preset_name, cron in PRESETS.items():
            if cron is not None:
                with self.subTest(preset=preset_name):
                    is_valid, err = validate_cron_expression(cron)
                    self.assertTrue(is_valid, f"Preset '{preset_name}' is invalid: {err}")


class TestResolveSchedule(unittest.TestCase):
    """Test schedule resolution with presets and custom crons."""

    def test_empty_returns_none(self):
        """Empty string should return None."""
        result = resolve_schedule('')
        self.assertIsNone(result)

    def test_none_returns_none(self):
        """None should return None."""
        result = resolve_schedule(None)
        self.assertIsNone(result)

    def test_preset_every_hour(self):
        """Preset 'every_hour' should resolve correctly."""
        result = resolve_schedule('every_hour')
        self.assertEqual(result, '0 * * * *')

    def test_preset_case_insensitive(self):
        """Presets should be case-insensitive."""
        result = resolve_schedule('EVERY_HOUR')
        self.assertEqual(result, '0 * * * *')

    def test_preset_disabled(self):
        """Preset 'disabled' should return None."""
        result = resolve_schedule('disabled')
        self.assertIsNone(result)

    def test_valid_custom_cron(self):
        """Valid custom cron expression should be returned."""
        result = resolve_schedule('0 8 * * 1-5')
        self.assertEqual(result, '0 8 * * 1-5')

    def test_invalid_custom_cron_returns_none(self):
        """Invalid custom cron should return None (fallback to default)."""
        result = resolve_schedule('0 25 * * *')  # Hour 25 is invalid
        self.assertIsNone(result)

    def test_invalid_cron_wrong_field_count(self):
        """Cron with wrong number of fields should return None."""
        result = resolve_schedule('0 12 * *')  # Only 4 fields
        self.assertIsNone(result)

    def test_invalid_cron_nonsense(self):
        """Complete nonsense should return None."""
        result = resolve_schedule('not a cron')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
