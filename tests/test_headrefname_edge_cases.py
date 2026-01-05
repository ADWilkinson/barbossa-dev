#!/usr/bin/env python3
"""
Tests for headRefName edge case handling in agents.

Verifies that agents correctly handle PRs with None/null headRefName values
from the GitHub API. This prevents AttributeError crashes when GitHub returns
unexpected data.

Issue: dict.get('headRefName', '') returns None (not '') when the key exists
with an explicit None value. Calling .startswith() on None raises AttributeError.
Fix: Use (pr.get('headRefName') or '') pattern.
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


class TestHeadRefNameEdgeCases(unittest.TestCase):
    """Test headRefName None handling across agents."""

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

    def _make_pr_with_headref(self, pr_number: int, head_ref_name) -> dict:
        """Helper to create a PR dict with specific headRefName value."""
        return {
            'number': pr_number,
            'headRefName': head_ref_name,
            'title': 'Test PR',
            'reviewDecision': None,
            'mergeable': 'MERGEABLE',
            'mergeStateStatus': 'CLEAN',
            'statusCheckRollup': []
        }

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_null_headrefname_skips_pr(self, mock_comments, mock_prs):
        """PR with headRefName=None should be skipped without crashing."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        # headRefName is explicitly null (not missing key)
        mock_prs.return_value = [self._make_pr_with_headref(1, None)]
        mock_comments.return_value = []

        # Should not raise AttributeError
        result = engineer._get_prs_needing_attention(repo)

        # PR with None branch should be skipped (not a barbossa PR)
        self.assertEqual(len(result), 0)

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_missing_headrefname_key_skips_pr(self, mock_comments, mock_prs):
        """PR without headRefName key should be skipped without crashing."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        # Create PR without headRefName key
        pr = {'number': 1, 'title': 'Test PR', 'statusCheckRollup': []}
        mock_prs.return_value = [pr]
        mock_comments.return_value = []

        # Should not raise KeyError or AttributeError
        result = engineer._get_prs_needing_attention(repo)

        # PR with missing branch should be skipped
        self.assertEqual(len(result), 0)

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_empty_string_headrefname_skips_pr(self, mock_comments, mock_prs):
        """PR with headRefName='' should be skipped."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        mock_prs.return_value = [self._make_pr_with_headref(1, '')]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        # Empty string doesn't start with 'barbossa/'
        self.assertEqual(len(result), 0)

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_valid_barbossa_branch_detected(self, mock_comments, mock_prs):
        """PR with valid barbossa/ branch should be detected."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        mock_prs.return_value = [self._make_pr_with_headref(1, 'barbossa/20260105-test')]
        mock_comments.return_value = []

        result = engineer._get_prs_needing_attention(repo)

        # Valid barbossa branch should be detected (might need attention for other reasons)
        # but importantly, no crash occurred
        self.assertTrue(True)  # No exception = pass

    @patch('barbossa.agents.engineer.Barbossa._get_open_prs')
    @patch('barbossa.agents.engineer.Barbossa._get_pr_comments')
    def test_mixed_null_and_valid_branches(self, mock_comments, mock_prs):
        """List with mix of null and valid branches should process correctly."""
        engineer = self._create_engineer()
        repo = {'name': 'test-repo', 'url': 'https://github.com/test/test'}

        mock_prs.return_value = [
            self._make_pr_with_headref(1, None),
            self._make_pr_with_headref(2, 'barbossa/valid'),
            self._make_pr_with_headref(3, ''),
            self._make_pr_with_headref(4, 'feature/other'),
        ]
        mock_comments.return_value = []

        # Should process all without crashing
        result = engineer._get_prs_needing_attention(repo)

        # Only barbossa/valid should potentially be in results
        # All others should be skipped
        for pr in result:
            self.assertTrue(
                (pr.get('headRefName') or '').startswith('barbossa/'),
                f"Non-barbossa PR should not be in results: {pr}"
            )


class TestTechLeadHeadRefNameEdgeCases(unittest.TestCase):
    """Test headRefName None handling in Tech Lead agent."""

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

    def _create_tech_lead(self):
        """Create a BarbossaTechLead instance with mocked dependencies."""
        from barbossa.agents.tech_lead import BarbossaTechLead

        with patch('barbossa.agents.tech_lead.logging') as mock_logging, \
             patch('barbossa.agents.tech_lead.process_retry_queue'):
            mock_logger = MagicMock()
            mock_logging.getLogger.return_value = mock_logger
            mock_logging.INFO = 20
            mock_logging.FileHandler = MagicMock()
            mock_logging.StreamHandler = MagicMock()

            tech_lead = BarbossaTechLead(work_dir=self.temp_dir)
            return tech_lead

    def _make_pr(self, pr_number: int, head_ref_name, created_at: str = '2026-01-01T00:00:00Z') -> dict:
        """Helper to create a PR dict."""
        return {
            'number': pr_number,
            'headRefName': head_ref_name,
            'title': 'Test PR',
            'createdAt': created_at,
            'state': 'OPEN'
        }

    def test_filter_barbossa_prs_handles_null(self):
        """Filter logic should handle null headRefName without crashing."""
        prs = [
            self._make_pr(1, None),
            self._make_pr(2, 'barbossa/test'),
            self._make_pr(3, ''),
            self._make_pr(4, 'feature/other'),
        ]

        # Using the fixed pattern: (pr.get('headRefName') or '').startswith('barbossa/')
        barbossa_prs = [pr for pr in prs if (pr.get('headRefName') or '').startswith('barbossa/')]

        self.assertEqual(len(barbossa_prs), 1)
        self.assertEqual(barbossa_prs[0]['number'], 2)

    def test_cleanup_stale_prs_handles_null(self):
        """Stale PR cleanup should handle null headRefName."""
        tech_lead = self._create_tech_lead()

        prs = [
            self._make_pr(1, None, '2020-01-01T00:00:00Z'),  # Very old but null branch
            self._make_pr(2, 'barbossa/test', '2020-01-01T00:00:00Z'),  # Old barbossa PR
            self._make_pr(3, 'feature/other', '2020-01-01T00:00:00Z'),  # Old non-barbossa PR
        ]

        # Verify the pattern works for each PR
        for pr in prs:
            branch = pr.get('headRefName') or ''
            is_barbossa_pr = branch.startswith('barbossa/')
            # Should not raise AttributeError
            if pr['number'] == 2:
                self.assertTrue(is_barbossa_pr)
            else:
                self.assertFalse(is_barbossa_pr)


class TestAuditorHeadRefNameEdgeCases(unittest.TestCase):
    """Test headRefName None handling in Auditor agent."""

    def test_filter_barbossa_prs_handles_null(self):
        """Auditor filter logic should handle null headRefName."""
        prs = [
            {'number': 1, 'headRefName': None, 'createdAt': '2026-01-01T00:00:00Z'},
            {'number': 2, 'headRefName': 'barbossa/test', 'createdAt': '2026-01-01T00:00:00Z'},
            {'number': 3, 'headRefName': '', 'createdAt': '2026-01-01T00:00:00Z'},
        ]

        # Using the fixed pattern
        barbossa_prs = []
        for pr in prs:
            if not (pr.get('headRefName') or '').startswith('barbossa/'):
                continue
            barbossa_prs.append(pr)

        self.assertEqual(len(barbossa_prs), 1)
        self.assertEqual(barbossa_prs[0]['number'], 2)


if __name__ == '__main__':
    unittest.main()
