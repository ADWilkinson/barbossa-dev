#!/usr/bin/env python3
"""
Tests for CLAUDE.md file reading with Unicode handling.

Verifies that _read_claude_md functions in Product and SpecGenerator agents
correctly handle files containing:
- Emoji characters
- Unicode quotes and special characters
- International characters (non-ASCII)
- Files with encoding errors (graceful fallback)
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


class TestClaudeMdEncodingProduct(unittest.TestCase):
    """Test CLAUDE.md encoding handling in Product Manager agent."""

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
    def test_reads_file_with_emoji(self, mock_logging):
        """CLAUDE.md with emoji should be read successfully."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        product = BarbossaProduct(work_dir=self.temp_dir)

        # Create a repo directory with CLAUDE.md containing emoji
        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        content_with_emoji = "# Test Project 🚀\n\nThis is a test with emoji ✅ and symbols ⚠️"
        claude_md.write_text(content_with_emoji, encoding='utf-8')

        result = product._read_claude_md(repo_dir)

        self.assertEqual(result, content_with_emoji)

    @patch('barbossa.agents.product.logging')
    def test_reads_file_with_unicode_quotes(self, mock_logging):
        """CLAUDE.md with unicode quotes should be read successfully."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        product = BarbossaProduct(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        content_with_quotes = "This has \u201ccurly quotes\u201d and \u2018apostrophes\u2019 and \u2013 em dashes"
        claude_md.write_text(content_with_quotes, encoding='utf-8')

        result = product._read_claude_md(repo_dir)

        self.assertEqual(result, content_with_quotes)

    @patch('barbossa.agents.product.logging')
    def test_reads_file_with_international_characters(self, mock_logging):
        """CLAUDE.md with international characters should be read successfully."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        product = BarbossaProduct(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        # Mix of Japanese, Chinese, German, French, and Arabic
        content_intl = "日本語 中文 Übersetzung Français العربية"
        claude_md.write_text(content_intl, encoding='utf-8')

        result = product._read_claude_md(repo_dir)

        self.assertEqual(result, content_intl)

    @patch('barbossa.agents.product.logging')
    def test_returns_empty_string_when_file_missing(self, mock_logging):
        """Should return empty string when CLAUDE.md doesn't exist."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        product = BarbossaProduct(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        # Don't create CLAUDE.md

        result = product._read_claude_md(repo_dir)

        self.assertEqual(result, "")

    @patch('barbossa.agents.product.logging')
    def test_truncates_large_file(self, mock_logging):
        """Should truncate content exceeding 15000 characters."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        product = BarbossaProduct(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        large_content = "A" * 20000
        claude_md.write_text(large_content, encoding='utf-8')

        result = product._read_claude_md(repo_dir)

        self.assertEqual(len(result), 15000)


class TestClaudeMdEncodingSpecGenerator(unittest.TestCase):
    """Test CLAUDE.md encoding handling in Spec Generator agent."""

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
    def test_reads_file_with_emoji(self, mock_logging):
        """CLAUDE.md with emoji should be read successfully."""
        from barbossa.agents.spec_generator import BarbossaSpecGenerator

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        spec_gen = BarbossaSpecGenerator(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        content_with_emoji = "# Test Project 🎉\n\nStatus: ✅ Complete"
        claude_md.write_text(content_with_emoji, encoding='utf-8')

        result = spec_gen._read_claude_md(repo_dir)

        self.assertEqual(result, content_with_emoji)

    @patch('barbossa.agents.spec_generator.logging')
    def test_reads_file_with_unicode_quotes(self, mock_logging):
        """CLAUDE.md with unicode quotes should be read successfully."""
        from barbossa.agents.spec_generator import BarbossaSpecGenerator

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        spec_gen = BarbossaSpecGenerator(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        content_with_quotes = "\u201cSmart quotes\u201d and \u2014 em-dashes and \u2026 ellipsis"
        claude_md.write_text(content_with_quotes, encoding='utf-8')

        result = spec_gen._read_claude_md(repo_dir)

        self.assertEqual(result, content_with_quotes)

    @patch('barbossa.agents.spec_generator.logging')
    def test_reads_file_with_international_characters(self, mock_logging):
        """CLAUDE.md with international characters should be read successfully."""
        from barbossa.agents.spec_generator import BarbossaSpecGenerator

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        spec_gen = BarbossaSpecGenerator(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        content_intl = "Привет мир こんにちは 你好世界 مرحبا"
        claude_md.write_text(content_intl, encoding='utf-8')

        result = spec_gen._read_claude_md(repo_dir)

        self.assertEqual(result, content_intl)

    @patch('barbossa.agents.spec_generator.logging')
    def test_returns_empty_string_when_file_missing(self, mock_logging):
        """Should return empty string when CLAUDE.md doesn't exist."""
        from barbossa.agents.spec_generator import BarbossaSpecGenerator

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        spec_gen = BarbossaSpecGenerator(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()

        result = spec_gen._read_claude_md(repo_dir)

        self.assertEqual(result, "")

    @patch('barbossa.agents.spec_generator.logging')
    def test_truncates_large_file_and_logs(self, mock_logging):
        """Should truncate content exceeding MAX_CLAUDE_MD_SIZE and log it."""
        from barbossa.agents.spec_generator import BarbossaSpecGenerator

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        spec_gen = BarbossaSpecGenerator(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        # Create content larger than MAX_CLAUDE_MD_SIZE (15000)
        large_content = "B" * 20000
        claude_md.write_text(large_content, encoding='utf-8')

        result = spec_gen._read_claude_md(repo_dir)

        self.assertEqual(len(result), spec_gen.MAX_CLAUDE_MD_SIZE)
        # Should have logged the truncation
        mock_logger.info.assert_called()


class TestClaudeMdEncodingFallback(unittest.TestCase):
    """Test graceful fallback when encoding errors occur."""

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
    def test_product_handles_io_error_gracefully(self, mock_logging):
        """Should return empty string and log warning on IOError."""
        from barbossa.agents.product import BarbossaProduct

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        product = BarbossaProduct(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        claude_md.write_text("test", encoding='utf-8')

        # Make the file unreadable by patching open to raise IOError
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            # Need to also patch exists to return True
            with patch.object(Path, 'exists', return_value=True):
                result = product._read_claude_md(repo_dir)

        self.assertEqual(result, "")
        mock_logger.warning.assert_called()

    @patch('barbossa.agents.spec_generator.logging')
    def test_spec_generator_handles_io_error_gracefully(self, mock_logging):
        """Should return empty string and log warning on IOError."""
        from barbossa.agents.spec_generator import BarbossaSpecGenerator

        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_logging.INFO = 20
        mock_logging.FileHandler = MagicMock()
        mock_logging.StreamHandler = MagicMock()

        spec_gen = BarbossaSpecGenerator(work_dir=self.temp_dir)

        repo_dir = self.projects_dir / 'test-repo'
        repo_dir.mkdir()
        claude_md = repo_dir / 'CLAUDE.md'
        claude_md.write_text("test", encoding='utf-8')

        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with patch.object(Path, 'exists', return_value=True):
                result = spec_gen._read_claude_md(repo_dir)

        self.assertEqual(result, "")
        mock_logger.warning.assert_called()


if __name__ == '__main__':
    unittest.main()
