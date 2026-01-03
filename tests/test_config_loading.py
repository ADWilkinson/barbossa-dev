#!/usr/bin/env python3
"""
Tests for agent config loading error handling.

Verifies that all agents handle invalid JSON in config files gracefully
instead of crashing with unhandled JSONDecodeError exceptions.
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


class TestConfigLoadingErrorHandling(unittest.TestCase):
    """Test that agents handle invalid JSON config files gracefully."""

    def setUp(self):
        """Create a temporary directory with config subdirectory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / 'config'
        self.config_dir.mkdir()
        self.config_path = self.config_dir / 'repositories.json'
        # Write invalid JSON that will trigger JSONDecodeError
        self.config_path.write_text('{ invalid json content }')

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('barbossa.agents.discovery.logging')
    def test_discovery_handles_invalid_json(self, mock_logging):
        """Discovery agent should handle invalid JSON and raise ValueError for missing owner."""
        from barbossa.agents.discovery import BarbossaDiscovery

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        # With invalid JSON, the agent should log an error and then fail
        # with a clean ValueError (owner required) instead of JSONDecodeError
        with self.assertRaises(ValueError) as ctx:
            BarbossaDiscovery(work_dir=self.temp_dir)

        self.assertIn('owner', str(ctx.exception))
        # Should have logged the JSON error before raising ValueError
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        self.assertIn('Invalid JSON', error_call)

    @patch('barbossa.agents.product.logging')
    def test_product_handles_invalid_json(self, mock_logging):
        """Product Manager agent should handle invalid JSON and raise ValueError for missing owner."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            BarbossaProduct(work_dir=self.temp_dir)

        self.assertIn('owner', str(ctx.exception))
        mock_logger.error.assert_called()

    @patch('barbossa.agents.spec_generator.logging')
    def test_spec_generator_handles_invalid_json(self, mock_logging):
        """Spec Generator agent should handle invalid JSON and raise ValueError for missing owner."""
        from barbossa.agents.spec_generator import BarbossaSpecGenerator

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            BarbossaSpecGenerator(work_dir=self.temp_dir)

        self.assertIn('owner', str(ctx.exception))
        mock_logger.error.assert_called()


class TestValidJsonStillWorks(unittest.TestCase):
    """Ensure valid JSON config files still load correctly."""

    def setUp(self):
        """Create temp dir with valid JSON config."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / 'config'
        self.config_dir.mkdir()
        self.config_path = self.config_dir / 'repositories.json'
        self.valid_config = {
            'owner': 'test-owner',
            'repositories': [
                {'repo': 'test-repo', 'url': 'https://github.com/test/test'}
            ]
        }
        self.config_path.write_text(json.dumps(self.valid_config))

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('barbossa.agents.discovery.logging')
    def test_discovery_loads_valid_json(self, mock_logging):
        """Discovery agent should load valid JSON correctly."""
        from barbossa.agents.discovery import BarbossaDiscovery

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        discovery = BarbossaDiscovery(work_dir=self.temp_dir)
        config = discovery._load_config()

        self.assertEqual(config['owner'], 'test-owner')
        self.assertEqual(len(config['repositories']), 1)
        # Should NOT log any errors for valid JSON
        mock_logger.error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
