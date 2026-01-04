#!/usr/bin/env python3
"""
Tests for OAuth token edge case handling in the Auditor agent.

Verifies that _check_oauth_token() handles missing or malformed
credential data gracefully instead of producing misleading results.
"""

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestOAuthTokenEdgeCases(unittest.TestCase):
    """Test OAuth token checking edge cases."""

    def setUp(self):
        """Create temp directory structure for auditor."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / 'config'
        self.config_dir.mkdir()
        self.logs_dir = self.temp_dir / 'logs'
        self.logs_dir.mkdir()
        self.claude_dir = self.temp_dir / '.claude'
        self.claude_dir.mkdir()
        self.creds_file = self.claude_dir / '.credentials.json'

        # Valid config for auditor initialization
        self.config_path = self.config_dir / 'repositories.json'
        self.config_path.write_text(json.dumps({
            'owner': 'test-owner',
            'repositories': [{'name': 'test-repo', 'url': 'https://github.com/test/test'}]
        }))

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('barbossa.agents.auditor.logging')
    @patch('barbossa.agents.auditor.get_client')
    @patch('barbossa.agents.auditor.check_version')
    def test_missing_claudeAiOauth_key(self, mock_check_version, mock_get_client, mock_logging):
        """When claudeAiOauth key is missing, should return error status."""
        from barbossa.agents.auditor import BarbossaAuditor

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()
        mock_check_version.return_value = None
        mock_get_client.return_value = None

        # Write credentials file without claudeAiOauth
        self.creds_file.write_text(json.dumps({'someOtherKey': 'value'}))

        auditor = BarbossaAuditor(work_dir=self.temp_dir)

        # Patch Path.home() to return our temp dir for the credential check
        with patch.object(Path, 'home', return_value=self.temp_dir):
            result = auditor._check_oauth_token()

        self.assertEqual(result['status'], 'error')
        self.assertIn('No claudeAiOauth data', result['message'])

    @patch('barbossa.agents.auditor.logging')
    @patch('barbossa.agents.auditor.get_client')
    @patch('barbossa.agents.auditor.check_version')
    def test_empty_claudeAiOauth_object(self, mock_check_version, mock_get_client, mock_logging):
        """When claudeAiOauth is an empty object, should return error status."""
        from barbossa.agents.auditor import BarbossaAuditor

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()
        mock_check_version.return_value = None
        mock_get_client.return_value = None

        # Write credentials file with empty claudeAiOauth
        self.creds_file.write_text(json.dumps({'claudeAiOauth': {}}))

        auditor = BarbossaAuditor(work_dir=self.temp_dir)

        with patch.object(Path, 'home', return_value=self.temp_dir):
            result = auditor._check_oauth_token()

        self.assertEqual(result['status'], 'error')
        self.assertIn('No claudeAiOauth data', result['message'])

    @patch('barbossa.agents.auditor.logging')
    @patch('barbossa.agents.auditor.get_client')
    @patch('barbossa.agents.auditor.check_version')
    def test_missing_expiresAt_field(self, mock_check_version, mock_get_client, mock_logging):
        """When expiresAt field is missing, should return error status."""
        from barbossa.agents.auditor import BarbossaAuditor

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()
        mock_check_version.return_value = None
        mock_get_client.return_value = None

        # Write credentials file with claudeAiOauth but no expiresAt
        self.creds_file.write_text(json.dumps({
            'claudeAiOauth': {'accessToken': 'some-token', 'refreshToken': 'some-refresh'}
        }))

        auditor = BarbossaAuditor(work_dir=self.temp_dir)

        with patch.object(Path, 'home', return_value=self.temp_dir):
            result = auditor._check_oauth_token()

        self.assertEqual(result['status'], 'error')
        self.assertIn('no expiration timestamp', result['message'])

    @patch('barbossa.agents.auditor.logging')
    @patch('barbossa.agents.auditor.get_client')
    @patch('barbossa.agents.auditor.check_version')
    def test_expiresAt_is_zero(self, mock_check_version, mock_get_client, mock_logging):
        """When expiresAt is 0, should return error status instead of epoch date."""
        from barbossa.agents.auditor import BarbossaAuditor

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()
        mock_check_version.return_value = None
        mock_get_client.return_value = None

        # Write credentials file with expiresAt = 0
        self.creds_file.write_text(json.dumps({
            'claudeAiOauth': {'accessToken': 'some-token', 'expiresAt': 0}
        }))

        auditor = BarbossaAuditor(work_dir=self.temp_dir)

        with patch.object(Path, 'home', return_value=self.temp_dir):
            result = auditor._check_oauth_token()

        # Should return error, not claim token expired at 1970
        self.assertEqual(result['status'], 'error')
        self.assertIn('no expiration timestamp', result['message'])
        # Verify it doesn't contain epoch date
        self.assertNotIn('1970', result['message'])

    @patch('barbossa.agents.auditor.logging')
    @patch('barbossa.agents.auditor.get_client')
    @patch('barbossa.agents.auditor.check_version')
    def test_valid_token_still_works(self, mock_check_version, mock_get_client, mock_logging):
        """Valid token with proper expiresAt should still work correctly."""
        from barbossa.agents.auditor import BarbossaAuditor

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()
        mock_check_version.return_value = None
        mock_get_client.return_value = None

        # Write credentials file with valid future expiresAt (in milliseconds)
        future_time = datetime.now() + timedelta(days=7)
        expires_at_ms = int(future_time.timestamp() * 1000)
        self.creds_file.write_text(json.dumps({
            'claudeAiOauth': {'accessToken': 'some-token', 'expiresAt': expires_at_ms}
        }))

        auditor = BarbossaAuditor(work_dir=self.temp_dir)

        with patch.object(Path, 'home', return_value=self.temp_dir):
            result = auditor._check_oauth_token()

        self.assertEqual(result['status'], 'ok')
        self.assertIn('valid for', result['message'])

    @patch('barbossa.agents.auditor.logging')
    @patch('barbossa.agents.auditor.get_client')
    @patch('barbossa.agents.auditor.check_version')
    def test_expired_token_detected(self, mock_check_version, mock_get_client, mock_logging):
        """Expired token should be correctly detected as expired."""
        from barbossa.agents.auditor import BarbossaAuditor

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()
        mock_check_version.return_value = None
        mock_get_client.return_value = None

        # Write credentials file with past expiresAt (in milliseconds)
        past_time = datetime.now() - timedelta(hours=2)
        expires_at_ms = int(past_time.timestamp() * 1000)
        self.creds_file.write_text(json.dumps({
            'claudeAiOauth': {'accessToken': 'some-token', 'expiresAt': expires_at_ms}
        }))

        auditor = BarbossaAuditor(work_dir=self.temp_dir)

        with patch.object(Path, 'home', return_value=self.temp_dir):
            result = auditor._check_oauth_token()

        self.assertEqual(result['status'], 'expired')
        self.assertIn('EXPIRED', result['message'])

    @patch('barbossa.agents.auditor.logging')
    @patch('barbossa.agents.auditor.get_client')
    @patch('barbossa.agents.auditor.check_version')
    def test_expiring_soon_warning(self, mock_check_version, mock_get_client, mock_logging):
        """Token expiring within 24 hours should get warning status."""
        from barbossa.agents.auditor import BarbossaAuditor

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()
        mock_check_version.return_value = None
        mock_get_client.return_value = None

        # Write credentials file with expiresAt in 12 hours (in milliseconds)
        future_time = datetime.now() + timedelta(hours=12)
        expires_at_ms = int(future_time.timestamp() * 1000)
        self.creds_file.write_text(json.dumps({
            'claudeAiOauth': {'accessToken': 'some-token', 'expiresAt': expires_at_ms}
        }))

        auditor = BarbossaAuditor(work_dir=self.temp_dir)

        with patch.object(Path, 'home', return_value=self.temp_dir):
            result = auditor._check_oauth_token()

        self.assertEqual(result['status'], 'warning')
        self.assertIn('expires in', result['message'])


if __name__ == '__main__':
    unittest.main()
