#!/usr/bin/env python3
"""
Tests for scripts/validate.py exception handling and config validation

Tests configuration validation including URL format, duplicate detection,
and Discord webhook URL validation.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from validate import run_cmd


class TestRunCmd(unittest.TestCase):
    """Test run_cmd function exception handling"""

    @patch('validate.subprocess.run')
    def test_run_cmd_success(self, mock_run):
        """Test successful command execution"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='output',
            stderr=''
        )
        success, stdout, stderr = run_cmd('echo test')
        self.assertTrue(success)
        self.assertEqual(stdout, 'output')
        self.assertEqual(stderr, '')

    @patch('validate.subprocess.run')
    def test_run_cmd_failure(self, mock_run):
        """Test failed command execution"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='error'
        )
        success, stdout, stderr = run_cmd('false')
        self.assertFalse(success)
        self.assertEqual(stderr, 'error')

    @patch('validate.subprocess.run')
    def test_run_cmd_timeout(self, mock_run):
        """Test command timeout is caught specifically"""
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', timeout=10)
        success, stdout, stderr = run_cmd('sleep 100', timeout=1)
        self.assertFalse(success)
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, 'Command timed out')

    @patch('validate.subprocess.run')
    def test_run_cmd_subprocess_error(self, mock_run):
        """Test subprocess errors are caught specifically"""
        mock_run.side_effect = subprocess.SubprocessError('Test error')
        success, stdout, stderr = run_cmd('invalid')
        self.assertFalse(success)
        self.assertEqual(stdout, '')
        self.assertIn('Test error', stderr)


class TestNoBareExcepts(unittest.TestCase):
    """Test that validate.py has no bare except blocks"""

    def test_no_bare_except_blocks(self):
        """Ensure no bare 'except:' blocks exist in validate.py"""
        validate_path = Path(__file__).parent.parent / 'scripts' / 'validate.py'
        content = validate_path.read_text()

        # Find all except blocks
        lines = content.split('\n')
        bare_excepts = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Match 'except:' but not 'except SomeError:' or 'except (A, B):'
            if stripped == 'except:':
                bare_excepts.append(f"Line {i}: {line}")

        self.assertEqual(
            bare_excepts, [],
            f"Found bare except blocks:\n" + "\n".join(bare_excepts)
        )


class TestConfigValidation(unittest.TestCase):
    """Test configuration validation functions"""

    def setUp(self):
        """Create a temporary config file for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / 'repositories.json'

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_config(self, config):
        """Helper to write config JSON"""
        with open(self.config_path, 'w') as f:
            json.dump(config, f)

    @patch('validate.Path')
    def test_duplicate_repository_names_detected(self, mock_path):
        """Test that duplicate repository names are detected"""
        from validate import validate_config

        config = {
            "owner": "testuser",
            "repositories": [
                {"name": "my-app", "url": "https://github.com/testuser/my-app.git"},
                {"name": "my-app", "url": "https://github.com/testuser/my-app-2.git"}
            ]
        }

        # Mock Path to return our config
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.__truediv__ = lambda self, x: self.config_path if 'repositories' in x else self

        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_config()
            self.assertFalse(result)

    @patch('validate.Path')
    def test_valid_github_https_url(self, mock_path):
        """Test that valid GitHub HTTPS URLs pass validation"""
        from validate import validate_config

        config = {
            "owner": "testuser",
            "repositories": [
                {"name": "my-app", "url": "https://github.com/testuser/my-app.git"}
            ]
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_config()
            self.assertTrue(result)

    @patch('validate.Path')
    def test_valid_github_ssh_url(self, mock_path):
        """Test that valid GitHub SSH URLs pass validation"""
        from validate import validate_config

        config = {
            "owner": "testuser",
            "repositories": [
                {"name": "my-app", "url": "git@github.com:testuser/my-app.git"}
            ]
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_config()
            self.assertTrue(result)

    @patch('validate.Path')
    def test_invalid_repository_url_rejected(self, mock_path):
        """Test that invalid repository URLs are rejected"""
        from validate import validate_config

        config = {
            "owner": "testuser",
            "repositories": [
                {"name": "my-app", "url": "http://example.com/repo.git"}
            ]
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_config()
            self.assertFalse(result)

    @patch('validate.Path')
    def test_gitlab_url_accepted(self, mock_path):
        """Test that GitLab URLs are accepted"""
        from validate import validate_config

        config = {
            "owner": "testuser",
            "repositories": [
                {"name": "my-app", "url": "https://gitlab.com/testuser/my-app.git"}
            ]
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_config()
            self.assertTrue(result)


class TestNotificationValidation(unittest.TestCase):
    """Test Discord webhook URL validation"""

    @patch('validate.Path')
    def test_valid_discord_webhook_url(self, mock_path):
        """Test that valid Discord webhook URLs pass validation"""
        from validate import validate_notifications

        config = {
            "settings": {
                "notifications": {
                    "enabled": True,
                    "discord_webhook": "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJKLMNOP"
                }
            }
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_notifications()
            self.assertTrue(result)

    @patch('validate.Path')
    def test_valid_legacy_discord_webhook_url(self, mock_path):
        """Test that legacy discordapp.com webhook URLs pass validation"""
        from validate import validate_notifications

        config = {
            "settings": {
                "notifications": {
                    "enabled": True,
                    "discord_webhook": "https://discordapp.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz"
                }
            }
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_notifications()
            self.assertTrue(result)

    @patch('validate.Path')
    def test_invalid_discord_webhook_url_rejected(self, mock_path):
        """Test that invalid Discord webhook URLs are rejected"""
        from validate import validate_notifications

        config = {
            "settings": {
                "notifications": {
                    "enabled": True,
                    "discord_webhook": "https://example.com/webhook/123"
                }
            }
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_notifications()
            self.assertFalse(result)

    @patch('validate.Path')
    def test_disabled_notifications_skip_validation(self, mock_path):
        """Test that disabled notifications skip webhook validation"""
        from validate import validate_notifications

        config = {
            "settings": {
                "notifications": {
                    "enabled": False,
                    "discord_webhook": "invalid-url"
                }
            }
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_notifications()
            self.assertTrue(result)

    @patch('validate.Path')
    def test_missing_webhook_with_notifications_enabled_warns(self, mock_path):
        """Test that missing webhook URL with notifications enabled returns True (warning only)"""
        from validate import validate_notifications

        config = {
            "settings": {
                "notifications": {
                    "enabled": True
                }
            }
        }

        mock_path.return_value.exists.return_value = True
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_notifications()
            self.assertTrue(result)  # Non-critical warning


class TestRepositoryAccessValidation(unittest.TestCase):
    """Test repository accessibility validation"""

    @patch('validate.run_cmd')
    @patch('validate.Path')
    def test_accessible_repositories_pass(self, mock_path, mock_run_cmd):
        """Test that accessible repositories pass validation"""
        from validate import validate_repository_access

        config = {
            "repositories": [
                {"name": "my-app", "url": "https://github.com/testuser/my-app.git"}
            ]
        }

        mock_path.return_value.exists.return_value = True
        mock_run_cmd.return_value = (True, 'my-app', '')

        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_repository_access()
            self.assertTrue(result)

    @patch('validate.run_cmd')
    @patch('validate.Path')
    def test_inaccessible_repositories_warn(self, mock_path, mock_run_cmd):
        """Test that inaccessible repositories return True (warning only)"""
        from validate import validate_repository_access

        config = {
            "repositories": [
                {"name": "my-app", "url": "https://github.com/testuser/my-app.git"}
            ]
        }

        mock_path.return_value.exists.return_value = True
        mock_run_cmd.return_value = (False, '', 'Not found')

        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_repository_access()
            self.assertTrue(result)  # Non-critical warning

    @patch('validate.run_cmd')
    @patch('validate.Path')
    def test_non_github_urls_skipped(self, mock_path, mock_run_cmd):
        """Test that non-GitHub URLs skip accessibility check"""
        from validate import validate_repository_access

        config = {
            "repositories": [
                {"name": "my-app", "url": "https://gitlab.com/testuser/my-app.git"}
            ]
        }

        mock_path.return_value.exists.return_value = True

        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(config))):
            result = validate_repository_access()
            self.assertTrue(result)
            # run_cmd should NOT be called for non-GitHub URLs
            mock_run_cmd.assert_not_called()


if __name__ == '__main__':
    unittest.main()
