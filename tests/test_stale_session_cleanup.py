#!/usr/bin/env python3
"""
Tests for stale session cleanup in the Engineer agent.

Verifies that _cleanup_stale_sessions() properly handles:
- Sessions with missing timestamps
- Sessions with malformed timestamps
- Sessions that have been running too long
- Normal running sessions that should not be touched
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


class TestStaleSessionCleanup(unittest.TestCase):
    """Test session cleanup handling for edge cases."""

    def setUp(self):
        """Create temp directory structure for engineer."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.temp_dir / 'config'
        self.config_dir.mkdir()
        self.logs_dir = self.temp_dir / 'logs'
        self.logs_dir.mkdir()
        self.changelogs_dir = self.temp_dir / 'changelogs'
        self.changelogs_dir.mkdir()
        self.projects_dir = self.temp_dir / 'projects'
        self.projects_dir.mkdir()
        self.sessions_file = self.temp_dir / 'sessions.json'

        # Valid config for engineer initialization
        self.config_path = self.config_dir / 'repositories.json'
        self.config_path.write_text(json.dumps({
            'owner': 'test-owner',
            'repositories': [{'name': 'test-repo', 'url': 'https://github.com/test/test'}]
        }))

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_engineer(self):
        """Helper to create a Barbossa engineer instance with mocked dependencies."""
        with patch('barbossa.agents.engineer.get_client') as mock_get_client, \
             patch('barbossa.agents.engineer.check_version') as mock_check_version, \
             patch('barbossa.agents.engineer.logging') as mock_logging:
            mock_logger = MagicMock()
            mock_logging.getLogger.return_value = mock_logger
            mock_logging.INFO = 20
            mock_logging.FileHandler = MagicMock()
            mock_logging.StreamHandler = MagicMock()
            mock_check_version.return_value = None
            mock_get_client.return_value = None

            from barbossa.agents.engineer import Barbossa
            engineer = Barbossa(work_dir=self.temp_dir)
            return engineer, mock_logger

    def test_missing_timestamp_marked_as_error(self):
        """Session with missing 'started' timestamp should be marked as error."""
        engineer, mock_logger = self._create_engineer()

        # Create a session with missing timestamp
        sessions = [{
            'session_id': 'test-session-1',
            'status': 'running',
            'repo': 'test-repo'
            # Note: 'started' field is missing
        }]
        self.sessions_file.write_text(json.dumps(sessions))

        engineer._cleanup_stale_sessions()

        # Read back the sessions file
        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        self.assertEqual(len(updated_sessions), 1)
        session = updated_sessions[0]
        self.assertEqual(session['status'], 'error')
        self.assertIn('missing start timestamp', session.get('error_reason', ''))
        self.assertIn('completed', session)

    def test_empty_timestamp_marked_as_error(self):
        """Session with empty string timestamp should be marked as error."""
        engineer, mock_logger = self._create_engineer()

        sessions = [{
            'session_id': 'test-session-2',
            'status': 'running',
            'repo': 'test-repo',
            'started': ''  # Empty string
        }]
        self.sessions_file.write_text(json.dumps(sessions))

        engineer._cleanup_stale_sessions()

        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        session = updated_sessions[0]
        self.assertEqual(session['status'], 'error')
        self.assertIn('missing start timestamp', session.get('error_reason', ''))

    def test_malformed_timestamp_marked_as_error(self):
        """Session with malformed timestamp should be marked as error."""
        engineer, mock_logger = self._create_engineer()

        sessions = [{
            'session_id': 'test-session-3',
            'status': 'running',
            'repo': 'test-repo',
            'started': 'not-a-valid-timestamp'
        }]
        self.sessions_file.write_text(json.dumps(sessions))

        engineer._cleanup_stale_sessions()

        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        session = updated_sessions[0]
        self.assertEqual(session['status'], 'error')
        self.assertIn('malformed start timestamp', session.get('error_reason', ''))
        self.assertIn('not-a-valid-timestamp', session.get('error_reason', ''))

    def test_old_session_marked_as_timeout(self):
        """Session running for more than 2 hours should be marked as timeout."""
        engineer, mock_logger = self._create_engineer()

        old_time = datetime.now() - timedelta(hours=3)
        sessions = [{
            'session_id': 'test-session-4',
            'status': 'running',
            'repo': 'test-repo',
            'started': old_time.isoformat()
        }]
        self.sessions_file.write_text(json.dumps(sessions))

        engineer._cleanup_stale_sessions()

        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        session = updated_sessions[0]
        self.assertEqual(session['status'], 'timeout')
        self.assertIn('2 hour limit', session.get('timeout_reason', ''))

    def test_recent_session_not_modified(self):
        """Session started recently should not be modified."""
        engineer, mock_logger = self._create_engineer()

        recent_time = datetime.now() - timedelta(minutes=30)
        sessions = [{
            'session_id': 'test-session-5',
            'status': 'running',
            'repo': 'test-repo',
            'started': recent_time.isoformat()
        }]
        original_json = json.dumps(sessions)
        self.sessions_file.write_text(original_json)

        engineer._cleanup_stale_sessions()

        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        session = updated_sessions[0]
        self.assertEqual(session['status'], 'running')
        self.assertNotIn('completed', session)
        self.assertNotIn('error_reason', session)
        self.assertNotIn('timeout_reason', session)

    def test_completed_session_not_modified(self):
        """Already completed sessions should not be modified."""
        engineer, mock_logger = self._create_engineer()

        # Create a completed session with old timestamp - should not be touched
        old_time = datetime.now() - timedelta(hours=10)
        sessions = [{
            'session_id': 'test-session-6',
            'status': 'success',  # Not 'running'
            'repo': 'test-repo',
            'started': old_time.isoformat(),
            'completed': (old_time + timedelta(minutes=30)).isoformat()
        }]
        self.sessions_file.write_text(json.dumps(sessions))

        engineer._cleanup_stale_sessions()

        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        session = updated_sessions[0]
        self.assertEqual(session['status'], 'success')
        self.assertNotIn('error_reason', session)
        self.assertNotIn('timeout_reason', session)

    def test_multiple_sessions_mixed_states(self):
        """Multiple sessions with different states are handled correctly."""
        engineer, mock_logger = self._create_engineer()

        old_time = datetime.now() - timedelta(hours=5)
        recent_time = datetime.now() - timedelta(minutes=15)

        sessions = [
            {
                'session_id': 'session-missing-ts',
                'status': 'running',
                'repo': 'test-repo'
                # Missing started
            },
            {
                'session_id': 'session-malformed-ts',
                'status': 'running',
                'repo': 'test-repo',
                'started': 'garbage'
            },
            {
                'session_id': 'session-old',
                'status': 'running',
                'repo': 'test-repo',
                'started': old_time.isoformat()
            },
            {
                'session_id': 'session-recent',
                'status': 'running',
                'repo': 'test-repo',
                'started': recent_time.isoformat()
            },
            {
                'session_id': 'session-completed',
                'status': 'success',
                'repo': 'test-repo',
                'started': old_time.isoformat()
            }
        ]
        self.sessions_file.write_text(json.dumps(sessions))

        engineer._cleanup_stale_sessions()

        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        # Create a map for easier lookup
        session_map = {s['session_id']: s for s in updated_sessions}

        # Missing timestamp -> error
        self.assertEqual(session_map['session-missing-ts']['status'], 'error')
        # Malformed timestamp -> error
        self.assertEqual(session_map['session-malformed-ts']['status'], 'error')
        # Old timestamp -> timeout
        self.assertEqual(session_map['session-old']['status'], 'timeout')
        # Recent timestamp -> still running
        self.assertEqual(session_map['session-recent']['status'], 'running')
        # Already completed -> unchanged
        self.assertEqual(session_map['session-completed']['status'], 'success')

    def test_no_sessions_file(self):
        """Should handle missing sessions file gracefully."""
        engineer, mock_logger = self._create_engineer()

        # Don't create sessions file - should not raise
        engineer._cleanup_stale_sessions()

        # No exception means pass

    def test_empty_sessions_file(self):
        """Should handle empty sessions list gracefully."""
        engineer, mock_logger = self._create_engineer()

        self.sessions_file.write_text(json.dumps([]))

        engineer._cleanup_stale_sessions()

        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        self.assertEqual(updated_sessions, [])

    def test_null_timestamp_marked_as_error(self):
        """Session with null/None timestamp should be marked as error."""
        engineer, mock_logger = self._create_engineer()

        sessions = [{
            'session_id': 'test-session-null',
            'status': 'running',
            'repo': 'test-repo',
            'started': None  # Explicitly null
        }]
        self.sessions_file.write_text(json.dumps(sessions))

        engineer._cleanup_stale_sessions()

        with open(self.sessions_file) as f:
            updated_sessions = json.load(f)

        session = updated_sessions[0]
        self.assertEqual(session['status'], 'error')
        self.assertIn('missing start timestamp', session.get('error_reason', ''))


if __name__ == '__main__':
    unittest.main()
