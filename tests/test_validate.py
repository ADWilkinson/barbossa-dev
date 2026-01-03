#!/usr/bin/env python3
"""
Tests for scripts/validate.py exception handling

Ensures that bare except blocks have been replaced with specific exception types.
"""

import subprocess
import sys
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


if __name__ == '__main__':
    unittest.main()
