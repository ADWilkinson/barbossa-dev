#!/usr/bin/env python3
"""
Tests for git branch fallback in _clone_or_update_repo.

Verifies that agents fall back from 'main' to 'master' branch when
repositories use 'master' as their default branch.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestBranchFallbackDiscovery(unittest.TestCase):
    """Test branch fallback in Discovery agent."""

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

    @patch('barbossa.agents.discovery.logging')
    def test_fallback_to_master_when_main_fails(self, mock_logging):
        """When 'main' branch fails, should fall back to 'master'."""
        from barbossa.agents.discovery import BarbossaDiscovery

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        discovery = BarbossaDiscovery(work_dir=self.temp_dir)

        # Create a fake repo directory
        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()

        # Track the commands that _run_cmd receives
        commands_received = []

        def mock_run_cmd(cmd, cwd=None, timeout=60):
            commands_received.append(cmd)
            # First call (main) fails, second call (master) succeeds
            if 'checkout main' in cmd:
                return None  # Simulate main branch not existing
            if 'checkout master' in cmd:
                return 'success'  # Simulate master branch exists
            return None

        with patch.object(discovery, '_run_cmd', side_effect=mock_run_cmd):
            result = discovery._clone_or_update_repo({'name': 'test-repo', 'url': 'https://github.com/test/test'})

        # Should have tried main first, then master
        self.assertEqual(len(commands_received), 2)
        self.assertIn('checkout main', commands_received[0])
        self.assertIn('checkout master', commands_received[1])
        # Should return the repo path
        self.assertEqual(result, repo_dir)

    @patch('barbossa.agents.discovery.logging')
    def test_no_fallback_when_main_succeeds(self, mock_logging):
        """When 'main' branch succeeds, should not try 'master'."""
        from barbossa.agents.discovery import BarbossaDiscovery

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        discovery = BarbossaDiscovery(work_dir=self.temp_dir)

        # Create a fake repo directory
        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()

        commands_received = []

        def mock_run_cmd(cmd, cwd=None, timeout=60):
            commands_received.append(cmd)
            if 'checkout main' in cmd:
                return 'success'  # main branch exists
            return None

        with patch.object(discovery, '_run_cmd', side_effect=mock_run_cmd):
            result = discovery._clone_or_update_repo({'name': 'test-repo', 'url': 'https://github.com/test/test'})

        # Should have only tried main (not master)
        self.assertEqual(len(commands_received), 1)
        self.assertIn('checkout main', commands_received[0])
        self.assertEqual(result, repo_dir)

    @patch('barbossa.agents.discovery.logging')
    def test_clone_failure_returns_none(self, mock_logging):
        """When clone fails for new repo, should return None."""
        from barbossa.agents.discovery import BarbossaDiscovery

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        discovery = BarbossaDiscovery(work_dir=self.temp_dir)

        # Don't create the repo directory - simulates new clone

        def mock_run_cmd(cmd, cwd=None, timeout=60):
            if 'clone' in cmd:
                return None  # Clone fails
            return None

        with patch.object(discovery, '_run_cmd', side_effect=mock_run_cmd):
            result = discovery._clone_or_update_repo({'name': 'new-repo', 'url': 'https://github.com/test/new'})

        # Should return None on clone failure
        self.assertIsNone(result)
        # Should have logged the error
        mock_logger.error.assert_called()


class TestBranchFallbackProduct(unittest.TestCase):
    """Test branch fallback in Product Manager agent."""

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

    @patch('barbossa.agents.product.logging')
    def test_fallback_to_master_when_main_fails(self, mock_logging):
        """When 'main' branch fails, should fall back to 'master'."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        product = BarbossaProduct(work_dir=self.temp_dir)

        # Create a fake repo directory
        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()

        commands_received = []

        def mock_run_cmd(cmd, cwd=None, timeout=60):
            commands_received.append(cmd)
            if 'checkout main' in cmd:
                return None  # main branch not existing
            if 'checkout master' in cmd:
                return 'success'
            return None

        with patch.object(product, '_run_cmd', side_effect=mock_run_cmd):
            result = product._clone_or_update_repo({'name': 'test-repo', 'url': 'https://github.com/test/test'})

        # Should have tried main first, then master
        self.assertEqual(len(commands_received), 2)
        self.assertIn('checkout main', commands_received[0])
        self.assertIn('checkout master', commands_received[1])
        self.assertEqual(result, repo_dir)

    @patch('barbossa.agents.product.logging')
    def test_clone_failure_returns_none(self, mock_logging):
        """When clone fails for new repo, should return None."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        product = BarbossaProduct(work_dir=self.temp_dir)

        def mock_run_cmd(cmd, cwd=None, timeout=60):
            if 'clone' in cmd:
                return None  # Clone fails
            return None

        with patch.object(product, '_run_cmd', side_effect=mock_run_cmd):
            result = product._clone_or_update_repo({'name': 'new-repo', 'url': 'https://github.com/test/new'})

        self.assertIsNone(result)
        mock_logger.error.assert_called()


class TestBranchFallbackSpecGenerator(unittest.TestCase):
    """Test branch fallback in Spec Generator agent (already implemented, verify consistency)."""

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

    @patch('barbossa.agents.spec_generator.logging')
    def test_spec_generator_fallback_to_master(self, mock_logging):
        """Spec Generator should also fall back from main to master."""
        from barbossa.agents.spec_generator import BarbossaSpecGenerator

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        spec_gen = BarbossaSpecGenerator(work_dir=self.temp_dir)

        # Create a fake repo directory
        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()

        commands_received = []

        def mock_run_cmd(cmd, cwd=None, timeout=60):
            commands_received.append(cmd)
            if 'checkout main' in cmd:
                return None
            if 'checkout master' in cmd:
                return 'success'
            return None

        with patch.object(spec_gen, '_run_cmd', side_effect=mock_run_cmd):
            result = spec_gen._clone_or_update_repo('test-repo', 'https://github.com/test/test')

        # Should have tried main first, then master
        self.assertEqual(len(commands_received), 2)
        self.assertIn('checkout main', commands_received[0])
        self.assertIn('checkout master', commands_received[1])
        self.assertEqual(result, repo_dir)


if __name__ == '__main__':
    unittest.main()
