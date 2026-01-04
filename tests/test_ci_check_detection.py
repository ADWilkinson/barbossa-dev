#!/usr/bin/env python3
"""
Tests for CI check detection in Engineer agent.

Verifies that the _get_prs_needing_attention method correctly identifies
failing CI checks for both CheckRun and StatusContext types from GitHub API.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestCICheckDetection(unittest.TestCase):
    """Test CI check detection in Engineer agent."""

    def setUp(self):
        """Create temp directory with valid config."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / 'config'
        self.config_dir.mkdir()
        self.projects_dir = self.temp_dir / 'projects'
        self.projects_dir.mkdir()
        self.config_path = self.config_dir / 'repositories.json'
        self.valid_config = {
            'owner': 'test-owner',
            'repositories': [
                {'name': 'test-repo', 'url': 'https://github.com/test/test'}
            ]
        }
        self.config_path.write_text(json.dumps(self.valid_config))

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_engineer(self):
        """Create an Engineer instance with mocked dependencies."""
        from barbossa.agents.engineer import Barbossa

        with patch('barbossa.agents.engineer.logging') as mock_logging, \
             patch('barbossa.agents.engineer.process_retry_queue'):
            mock_logger = MagicMock()
            mock_logging.getLogger.return_value = mock_logger
            mock_logging.INFO = 20
            mock_logging.FileHandler = MagicMock()
            mock_logging.StreamHandler = MagicMock()

            engineer = Barbossa(work_dir=self.temp_dir)
            return engineer

    def _make_pr_with_checks(self, pr_number: int, branch: str, checks: list) -> dict:
        """Helper to create a PR dict with checks."""
        return {
            'number': pr_number,
            'headRefName': branch,
            'reviewDecision': None,
            'mergeable': 'MERGEABLE',
            'mergeStateStatus': 'CLEAN',
            'statusCheckRollup': checks
        }

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_detects_checkrun_failure(self, mock_comments, mock_prs):
        """CheckRun with FAILURE conclusion should be detected."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'CheckRun',
                'name': 'CI Build',
                'status': 'COMPLETED',
                'conclusion': 'FAILURE'
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_detects_checkrun_error(self, mock_comments, mock_prs):
        """CheckRun with ERROR conclusion should be detected."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'CheckRun',
                'name': 'CI Build',
                'status': 'COMPLETED',
                'conclusion': 'ERROR'
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_detects_statuscontext_failure(self, mock_comments, mock_prs):
        """StatusContext with FAILURE state should be detected."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'StatusContext',
                'context': 'continuous-integration/travis-ci',
                'state': 'FAILURE'
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_detects_statuscontext_error(self, mock_comments, mock_prs):
        """StatusContext with ERROR state should be detected."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'StatusContext',
                'context': 'external-ci',
                'state': 'ERROR'
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_handles_lowercase_conclusion(self, mock_comments, mock_prs):
        """Lowercase failure status should still be detected (case insensitive)."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'CheckRun',
                'name': 'CI Build',
                'status': 'completed',
                'conclusion': 'failure'  # lowercase
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_handles_mixed_case(self, mock_comments, mock_prs):
        """Mixed case status should still be detected."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'StatusContext',
                'context': 'some-ci',
                'state': 'Failure'  # mixed case
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_passing_checks_not_flagged(self, mock_comments, mock_prs):
        """Passing checks should not flag the PR for attention."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'CheckRun',
                'name': 'CI Build',
                'status': 'COMPLETED',
                'conclusion': 'SUCCESS'
            },
            {
                '__typename': 'StatusContext',
                'context': 'coverage',
                'state': 'SUCCESS'
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        # Should not flag for failing_checks when all pass
        self.assertEqual(len(result), 0)

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_empty_checks_not_flagged(self, mock_comments, mock_prs):
        """Empty checks array should not cause errors or flag PR."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', [])]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 0)

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_null_checks_not_flagged(self, mock_comments, mock_prs):
        """Null/None checks should not cause errors or flag PR."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        pr = self._make_pr_with_checks(1, 'barbossa/test', None)
        mock_prs.return_value = [pr]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 0)

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_null_conclusion_not_flagged(self, mock_comments, mock_prs):
        """Null/None conclusion or state should not cause errors."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'CheckRun',
                'name': 'CI Build',
                'status': 'IN_PROGRESS',
                'conclusion': None  # Pending check has no conclusion
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        # Pending check should not flag as failing
        self.assertEqual(len(result), 0)

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_unknown_typename_fallback(self, mock_comments, mock_prs):
        """Unknown __typename should use fallback logic checking both fields."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        # Test with unknown typename but with failing conclusion
        checks = [
            {
                '__typename': 'SomeNewCheckType',
                'name': 'Unknown Check',
                'conclusion': 'FAILURE'
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_missing_typename_fallback(self, mock_comments, mock_prs):
        """Missing __typename should use fallback logic."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        # Test with missing typename
        checks = [
            {
                'name': 'Some Check',
                'state': 'ERROR'  # Using state field
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_skips_non_barbossa_prs(self, mock_comments, mock_prs):
        """PRs not created by Barbossa should be skipped."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'CheckRun',
                'name': 'CI Build',
                'status': 'COMPLETED',
                'conclusion': 'FAILURE'
            }
        ]
        # PR with non-barbossa branch
        mock_prs.return_value = [self._make_pr_with_checks(1, 'feature/my-branch', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        # Should skip non-barbossa PRs
        self.assertEqual(len(result), 0)

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_mixed_passing_and_failing_checks(self, mock_comments, mock_prs):
        """When any check fails, PR should be flagged."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        checks = [
            {
                '__typename': 'CheckRun',
                'name': 'Lint',
                'status': 'COMPLETED',
                'conclusion': 'SUCCESS'
            },
            {
                '__typename': 'CheckRun',
                'name': 'Tests',
                'status': 'COMPLETED',
                'conclusion': 'FAILURE'  # This one fails
            },
            {
                '__typename': 'StatusContext',
                'context': 'coverage',
                'state': 'SUCCESS'
            }
        ]
        mock_prs.return_value = [self._make_pr_with_checks(1, 'barbossa/test', checks)]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['attention_reason'], 'failing_checks')


if __name__ == '__main__':
    unittest.main()
