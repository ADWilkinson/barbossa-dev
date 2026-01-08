#!/usr/bin/env python3
"""
Tests for the FailureAnalyzer module.

This module provides systematic failure tracking and analysis
to help prevent repeated mistakes in PR submissions.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from barbossa.utils.failure_analyzer import (
    FailureAnalyzer,
    FailureRecord,
    FAILURE_CATEGORIES,
    _infer_category_from_reasoning,
    get_failure_analyzer,
)


class TestFailureRecord(unittest.TestCase):
    """Test the FailureRecord dataclass."""

    def test_failure_record_creation(self):
        """Test creating a FailureRecord with all fields."""
        record = FailureRecord(
            issue_id="#42",
            repository="test-repo",
            pr_number=123,
            pr_url="https://github.com/test/test-repo/pull/123",
            category="missing_tests",
            root_cause="No tests for new endpoint",
            evidence="PR adds 50+ lines to api/users.py without tests",
            tech_lead_reasoning="Rejected due to missing tests",
            timestamp="2026-01-08T10:00:00Z",
            attempt_number=1,
            issue_title="Add user deletion endpoint",
            issue_labels=["backlog", "api"],
        )

        self.assertEqual(record.issue_id, "#42")
        self.assertEqual(record.repository, "test-repo")
        self.assertEqual(record.pr_number, 123)
        self.assertEqual(record.category, "missing_tests")
        self.assertEqual(record.attempt_number, 1)
        self.assertEqual(record.issue_labels, ["backlog", "api"])


class TestCategoryInference(unittest.TestCase):
    """Test the category inference from reasoning text."""

    def test_infer_test_only(self):
        """Test inferring test-only category."""
        self.assertEqual(
            _infer_category_from_reasoning("This PR is test-only with no feature"),
            "test_only"
        )
        self.assertEqual(
            _infer_category_from_reasoning("Test-only PRs are not allowed"),
            "test_only"
        )

    def test_infer_missing_tests(self):
        """Test inferring missing tests category."""
        self.assertEqual(
            _infer_category_from_reasoning("PR is missing tests for new code"),
            "missing_tests"
        )
        self.assertEqual(
            _infer_category_from_reasoning("No tests were provided"),
            "missing_tests"
        )

    def test_infer_missing_evidence(self):
        """Test inferring missing evidence category."""
        self.assertEqual(
            _infer_category_from_reasoning("No evidence of the bug was provided"),
            "missing_evidence"
        )
        self.assertEqual(
            _infer_category_from_reasoning("PR has no issue link"),
            "missing_evidence"
        )

    def test_infer_ci_failures(self):
        """Test inferring CI failures category."""
        self.assertEqual(
            _infer_category_from_reasoning("CI build is failing"),
            "ci_failures"
        )
        self.assertEqual(
            _infer_category_from_reasoning("Failing checks need to be fixed"),
            "ci_failures"
        )

    def test_infer_lockfile(self):
        """Test inferring lockfile category."""
        self.assertEqual(
            _infer_category_from_reasoning("Lockfile changes were not disclosed"),
            "lockfile_undisclosed"
        )

    def test_infer_stale(self):
        """Test inferring stale category."""
        self.assertEqual(
            _infer_category_from_reasoning("PR has gone stale"),
            "stale"
        )

    def test_infer_other(self):
        """Test fallback to other category."""
        self.assertEqual(
            _infer_category_from_reasoning("Some unknown reason"),
            "other"
        )


class TestFailureAnalyzer(unittest.TestCase):
    """Test the FailureAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.work_dir = Path(self.temp_dir)
        self.logs_dir = self.work_dir / 'logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir = self.work_dir / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create a minimal config file
        config = {
            "owner": "test-owner",
            "repositories": [{"name": "test-repo", "url": "https://github.com/test/test-repo.git"}],
            "settings": {
                "failure_analyzer": {
                    "enabled": True,
                    "retention_days": 90,
                    "backoff_policy": {
                        "skip_runs_after_failures": 1,
                        "consecutive_failures_threshold": 2
                    }
                }
            }
        }
        with open(self.config_dir / 'repositories.json', 'w') as f:
            json.dump(config, f)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_record_failure(self):
        """Test recording a failure."""
        analyzer = FailureAnalyzer(self.work_dir)

        success = analyzer.record_failure(
            issue_id="#42",
            repository="test-repo",
            pr_number=123,
            pr_url="https://github.com/test/test-repo/pull/123",
            category="missing_tests",
            root_cause="No tests for new endpoint",
            evidence="PR adds 50+ lines without tests",
            tech_lead_reasoning="Rejected for missing tests",
            issue_title="Add user API",
            issue_labels=["backlog"],
        )

        self.assertTrue(success)
        self.assertTrue(analyzer.failures_file.exists())

        # Verify the content
        with open(analyzer.failures_file, 'r') as f:
            content = f.read().strip()
            record = json.loads(content)
            self.assertEqual(record['issue_id'], "#42")
            self.assertEqual(record['category'], "missing_tests")
            self.assertEqual(record['attempt_number'], 1)

    def test_record_multiple_failures_increments_attempt(self):
        """Test that recording multiple failures for same issue increments attempt number."""
        analyzer = FailureAnalyzer(self.work_dir)

        # First failure
        analyzer.record_failure(
            issue_id="#42",
            repository="test-repo",
            pr_number=123,
            pr_url="https://github.com/test/test-repo/pull/123",
            category="missing_tests",
            root_cause="No tests",
            evidence="No tests",
            tech_lead_reasoning="Missing tests",
        )

        # Second failure for same issue
        analyzer.record_failure(
            issue_id="#42",
            repository="test-repo",
            pr_number=124,
            pr_url="https://github.com/test/test-repo/pull/124",
            category="code_quality",
            root_cause="Poor quality",
            evidence="Bad code",
            tech_lead_reasoning="Quality issues",
        )

        # Verify attempt numbers
        failures = analyzer._load_failures()
        self.assertEqual(len(failures), 2)
        self.assertEqual(failures[0]['attempt_number'], 1)
        self.assertEqual(failures[1]['attempt_number'], 2)

    def test_invalid_category_falls_back_to_other(self):
        """Test that invalid category falls back to 'other'."""
        analyzer = FailureAnalyzer(self.work_dir)

        with patch.object(analyzer, 'enabled', True):
            success = analyzer.record_failure(
                issue_id="#42",
                repository="test-repo",
                pr_number=123,
                pr_url="https://github.com/test/test-repo/pull/123",
                category="invalid_category",
                root_cause="Test",
                evidence="Test",
                tech_lead_reasoning="Test",
            )

        self.assertTrue(success)
        failures = analyzer._load_failures()
        self.assertEqual(failures[0]['category'], 'other')

    def test_get_similar_failures_by_keywords(self):
        """Test finding similar failures by title keywords."""
        analyzer = FailureAnalyzer(self.work_dir)

        # Record a failure about user API
        analyzer.record_failure(
            issue_id="#42",
            repository="test-repo",
            pr_number=123,
            pr_url="https://github.com/test/test-repo/pull/123",
            category="missing_tests",
            root_cause="No tests",
            evidence="No tests",
            tech_lead_reasoning="Missing tests",
            issue_title="Add user deletion endpoint",
            issue_labels=["api"],
        )

        # Search for similar
        similar = analyzer.get_similar_failures(
            issue_title="Implement user update endpoint",
            issue_labels=["api"],
            repository="test-repo",
        )

        self.assertEqual(len(similar), 1)
        self.assertEqual(similar[0]['failure']['issue_id'], "#42")
        self.assertIn("user", str(similar[0]['match_reasons']).lower())

    def test_get_similar_failures_by_labels(self):
        """Test finding similar failures by labels."""
        analyzer = FailureAnalyzer(self.work_dir)

        # Record a failure with specific labels
        analyzer.record_failure(
            issue_id="#42",
            repository="test-repo",
            pr_number=123,
            pr_url="https://github.com/test/test-repo/pull/123",
            category="missing_tests",
            root_cause="No tests",
            evidence="No tests",
            tech_lead_reasoning="Missing tests",
            issue_title="Some API thing",
            issue_labels=["backlog", "api", "urgent"],
        )

        # Search by labels
        similar = analyzer.get_similar_failures(
            issue_title="Different title",
            issue_labels=["api", "backend"],
            repository="test-repo",
        )

        self.assertEqual(len(similar), 1)
        self.assertIn("api", str(similar[0]['match_reasons']).lower())

    def test_get_failure_warnings_format(self):
        """Test the formatted warning message."""
        analyzer = FailureAnalyzer(self.work_dir)

        # Record a failure
        analyzer.record_failure(
            issue_id="#42",
            repository="test-repo",
            pr_number=123,
            pr_url="https://github.com/test/test-repo/pull/123",
            category="missing_tests",
            root_cause="No tests for the endpoint",
            evidence="No test file",
            tech_lead_reasoning="Missing tests",
            issue_title="Add user endpoint",
            issue_labels=["api"],
        )

        # Get warnings
        warnings = analyzer.get_failure_warnings(
            issue_title="Update user endpoint",
            issue_labels=["api"],
            repository="test-repo",
        )

        self.assertIn("WARNING", warnings)
        self.assertIn("missing_tests", warnings)
        self.assertIn("No tests for the endpoint", warnings)

    def test_should_skip_issue_under_threshold(self):
        """Test that issues under failure threshold are not skipped."""
        analyzer = FailureAnalyzer(self.work_dir)

        # Record one failure (threshold is 2)
        analyzer.record_failure(
            issue_id="#42",
            repository="test-repo",
            pr_number=123,
            pr_url="https://github.com/test/test-repo/pull/123",
            category="missing_tests",
            root_cause="No tests",
            evidence="No tests",
            tech_lead_reasoning="Missing tests",
        )

        should_skip, reason = analyzer.should_skip_issue("#42", "test-repo")
        self.assertFalse(should_skip)
        self.assertEqual(reason, "")

    def test_should_skip_issue_at_threshold(self):
        """Test that issues at failure threshold are skipped."""
        analyzer = FailureAnalyzer(self.work_dir)

        # Record two failures (threshold is 2)
        for i in range(2):
            analyzer.record_failure(
                issue_id="#42",
                repository="test-repo",
                pr_number=123 + i,
                pr_url=f"https://github.com/test/test-repo/pull/{123 + i}",
                category="missing_tests",
                root_cause="No tests",
                evidence="No tests",
                tech_lead_reasoning="Missing tests",
            )

        should_skip, reason = analyzer.should_skip_issue("#42", "test-repo")
        self.assertTrue(should_skip)
        self.assertIn("failed 2 times", reason)
        self.assertIn("Backoff active", reason)

    def test_analyze_failure_patterns(self):
        """Test failure pattern analysis."""
        analyzer = FailureAnalyzer(self.work_dir)

        # Record various failures
        categories = ["missing_tests", "missing_tests", "missing_evidence", "ci_failures"]
        for i, cat in enumerate(categories):
            analyzer.record_failure(
                issue_id=f"#{40 + i}",
                repository="test-repo",
                pr_number=100 + i,
                pr_url=f"https://github.com/test/test-repo/pull/{100 + i}",
                category=cat,
                root_cause=f"Root cause {i}",
                evidence=f"Evidence {i}",
                tech_lead_reasoning=f"Reasoning {i}",
                issue_labels=["backlog"],
            )

        patterns = analyzer.analyze_failure_patterns(days=30)

        self.assertEqual(patterns['total_failures'], 4)
        self.assertEqual(len(patterns['top_categories']), 3)
        self.assertEqual(patterns['top_categories'][0]['category'], 'missing_tests')
        self.assertEqual(patterns['top_categories'][0]['count'], 2)
        self.assertEqual(patterns['failure_rate_by_label']['backlog'], 4)

    def test_analyze_failure_patterns_recurring_issues(self):
        """Test that recurring issues are detected."""
        analyzer = FailureAnalyzer(self.work_dir)

        # Record same issue failing multiple times
        for i in range(3):
            analyzer.record_failure(
                issue_id="#42",
                repository="test-repo",
                pr_number=100 + i,
                pr_url=f"https://github.com/test/test-repo/pull/{100 + i}",
                category="missing_tests",
                root_cause="No tests",
                evidence="No tests",
                tech_lead_reasoning="Missing tests",
            )

        patterns = analyzer.analyze_failure_patterns(days=30)

        self.assertEqual(len(patterns['recurring_issues']), 1)
        self.assertEqual(patterns['recurring_issues'][0]['issue_id'], '#42')
        self.assertEqual(patterns['recurring_issues'][0]['failure_count'], 3)

    def test_rotate_failures(self):
        """Test rotation of old failure records."""
        analyzer = FailureAnalyzer(self.work_dir)
        analyzer.retention_days = 7  # Short retention for testing

        # Write a record with old timestamp directly
        old_ts = (datetime.utcnow() - timedelta(days=10)).isoformat() + 'Z'
        new_ts = datetime.utcnow().isoformat() + 'Z'

        with open(analyzer.failures_file, 'w') as f:
            f.write(json.dumps({
                "issue_id": "#old",
                "repository": "test-repo",
                "pr_number": 100,
                "pr_url": "https://github.com/test/test-repo/pull/100",
                "category": "other",
                "root_cause": "Old failure",
                "evidence": "Old",
                "tech_lead_reasoning": "Old",
                "timestamp": old_ts,
                "attempt_number": 1,
            }) + '\n')
            f.write(json.dumps({
                "issue_id": "#new",
                "repository": "test-repo",
                "pr_number": 101,
                "pr_url": "https://github.com/test/test-repo/pull/101",
                "category": "other",
                "root_cause": "New failure",
                "evidence": "New",
                "tech_lead_reasoning": "New",
                "timestamp": new_ts,
                "attempt_number": 1,
            }) + '\n')

        rotated = analyzer.rotate_failures()

        self.assertEqual(rotated, 1)
        failures = analyzer._load_failures()
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]['issue_id'], '#new')

    def test_disabled_analyzer(self):
        """Test that disabled analyzer doesn't record failures."""
        # Create config with analyzer disabled
        config = {
            "owner": "test-owner",
            "repositories": [{"name": "test-repo", "url": "https://github.com/test/test-repo.git"}],
            "settings": {
                "failure_analyzer": {
                    "enabled": False,
                }
            }
        }
        with open(self.config_dir / 'repositories.json', 'w') as f:
            json.dump(config, f)

        analyzer = FailureAnalyzer(self.work_dir)

        success = analyzer.record_failure(
            issue_id="#42",
            repository="test-repo",
            pr_number=123,
            pr_url="https://github.com/test/test-repo/pull/123",
            category="missing_tests",
            root_cause="No tests",
            evidence="No tests",
            tech_lead_reasoning="Missing tests",
        )

        self.assertFalse(success)
        self.assertFalse(analyzer.failures_file.exists())

    def test_get_failure_insights_for_notification(self):
        """Test failure insights for notifications."""
        analyzer = FailureAnalyzer(self.work_dir)

        # Record multiple failures of same type
        for i in range(3):
            analyzer.record_failure(
                issue_id=f"#{40 + i}",
                repository="test-repo",
                pr_number=100 + i,
                pr_url=f"https://github.com/test/test-repo/pull/{100 + i}",
                category="missing_tests",
                root_cause="No tests",
                evidence="No tests",
                tech_lead_reasoning="Missing tests",
            )

        insight = analyzer.get_failure_insights_for_notification("test-repo", "missing_tests")

        self.assertIn("3", insight)  # "3th" or "3rd" - check for the count
        self.assertIn("missing tests", insight)

    def test_get_failure_analyzer_helper(self):
        """Test the get_failure_analyzer helper function."""
        analyzer = get_failure_analyzer(self.work_dir)
        self.assertIsInstance(analyzer, FailureAnalyzer)


class TestFailureCategories(unittest.TestCase):
    """Test that failure categories are properly defined."""

    def test_all_categories_defined(self):
        """Test that expected categories are in FAILURE_CATEGORIES."""
        expected = [
            'missing_tests',
            'test_only',
            'missing_evidence',
            'ci_failures',
            'lockfile_undisclosed',
            'code_quality',
            'scope_creep',
            'merge_conflicts',
            'three_strikes',
            'stale',
            'other',
        ]
        for cat in expected:
            self.assertIn(cat, FAILURE_CATEGORIES)


if __name__ == '__main__':
    unittest.main()
