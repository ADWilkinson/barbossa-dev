#!/usr/bin/env python3
"""
Tests for Log Rotation Utility

Tests the LogRotationManager class which handles:
- Size-based log rotation
- Compression of old logs
- Cleanup of very old logs
- Disk usage monitoring
"""

import gzip
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'barbossa' / 'utils'))
from log_rotation import LogRotationManager


class TestLogRotationManager(unittest.TestCase):
    """Test the LogRotationManager class"""

    def setUp(self):
        """Create a temporary directory for test logs"""
        self.temp_dir = tempfile.mkdtemp()
        self.logs_dir = Path(self.temp_dir) / 'logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.manager = LogRotationManager(
            logs_dir=self.logs_dir,
            max_log_size_mb=1,  # 1MB for easier testing
            compress_after_days=1,
            delete_after_days=3,
        )

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_log_file(self, name: str, size_kb: int = 10, age_days: int = 0) -> Path:
        """Helper to create a log file with specific size and age"""
        log_path = self.logs_dir / name
        # Write content to achieve approximate size
        content = 'x' * (size_kb * 1024)
        log_path.write_text(content)

        if age_days > 0:
            # Set modification time to the past
            past_time = datetime.now() - timedelta(days=age_days)
            timestamp = past_time.timestamp()
            os.utime(log_path, (timestamp, timestamp))

        return log_path

    def test_disk_usage_check(self):
        """Test disk usage monitoring"""
        result = self.manager.check_disk_health()

        self.assertIn('status', result)
        self.assertIn('percent_used', result)
        self.assertIn('total_gb', result)
        self.assertIn('free_gb', result)
        self.assertIsInstance(result['percent_used'], float)

    def test_rotate_large_logs(self):
        """Test rotation of logs exceeding size limit"""
        # Create a log file larger than 1MB threshold
        large_log = self._create_log_file('agent_large.log', size_kb=1100)
        small_log = self._create_log_file('agent_small.log', size_kb=10)

        self.assertTrue(large_log.exists())
        self.assertTrue(small_log.exists())

        result = self.manager.rotate_large_logs()

        self.assertEqual(result['rotated'], 1)
        self.assertFalse(large_log.exists())  # Original should be renamed
        self.assertTrue(small_log.exists())  # Small file should remain

        # Check that rotated file exists
        rotated_files = list(self.logs_dir.glob('agent_large.*.log'))
        self.assertEqual(len(rotated_files), 1)

    def test_compress_old_logs(self):
        """Test compression of old log files"""
        # Create an old log file (2 days old, compress_after_days=1)
        old_log = self._create_log_file('old_agent.log', size_kb=100, age_days=2)
        new_log = self._create_log_file('new_agent.log', size_kb=100, age_days=0)

        self.assertTrue(old_log.exists())
        self.assertTrue(new_log.exists())

        result = self.manager.compress_old_logs()

        self.assertEqual(result['compressed'], 1)
        self.assertFalse(old_log.exists())  # Original should be deleted
        self.assertTrue(new_log.exists())  # New file should remain
        self.assertTrue((self.logs_dir / 'old_agent.log.gz').exists())  # Compressed file should exist

    def test_cleanup_old_logs(self):
        """Test cleanup of very old logs"""
        # Create logs with different ages
        recent_log = self._create_log_file('recent.log', size_kb=10, age_days=1)
        old_log = self._create_log_file('old.log', size_kb=10, age_days=5)

        self.assertTrue(recent_log.exists())
        self.assertTrue(old_log.exists())

        result = self.manager.cleanup_old_logs()

        self.assertEqual(result['deleted'], 1)
        self.assertTrue(recent_log.exists())  # Should remain
        self.assertFalse(old_log.exists())  # Should be deleted

    def test_cleanup_compressed_logs(self):
        """Test cleanup of old compressed logs"""
        # Create a compressed log file
        gz_path = self.logs_dir / 'old_compressed.log.gz'
        with gzip.open(gz_path, 'wt') as f:
            f.write('test content')

        # Set old modification time
        past_time = datetime.now() - timedelta(days=5)
        timestamp = past_time.timestamp()
        os.utime(gz_path, (timestamp, timestamp))

        result = self.manager.cleanup_old_logs()

        self.assertEqual(result['deleted'], 1)
        self.assertFalse(gz_path.exists())

    def test_run_maintenance_full_cycle(self):
        """Test the full maintenance cycle"""
        # Create various log files
        # Note: The order of operations is: rotate -> compress -> cleanup
        # Files older than compress_after_days get compressed, then cleanup deletes old files
        self._create_log_file('large.log', size_kb=1100)  # Will be rotated (recent, won't compress)
        self._create_log_file('old.log', size_kb=50, age_days=2)  # Will be compressed
        self._create_log_file('current.log', size_kb=10)  # Will remain

        # Create an old compressed file directly (since ancient.log would get
        # compressed before cleanup runs, we create a .gz file directly)
        gz_path = self.logs_dir / 'ancient.log.gz'
        with gzip.open(gz_path, 'wt') as f:
            f.write('old content')
        past_time = datetime.now() - timedelta(days=5)
        os.utime(gz_path, (past_time.timestamp(), past_time.timestamp()))

        result = self.manager.run_maintenance()

        self.assertIn('rotation', result)
        self.assertIn('compression', result)
        self.assertIn('cleanup', result)
        self.assertIn('disk_health', result)
        self.assertEqual(result['rotation']['rotated'], 1)
        # At least one file compressed (old.log)
        self.assertGreaterEqual(result['compression']['compressed'], 1)
        # ancient.log.gz should be deleted
        self.assertEqual(result['cleanup']['deleted'], 1)

        # Current log should still exist
        self.assertTrue((self.logs_dir / 'current.log').exists())

    def test_get_logs_summary(self):
        """Test getting logs summary"""
        self._create_log_file('agent1.log', size_kb=100)
        self._create_log_file('agent2.log', size_kb=200)

        gz_path = self.logs_dir / 'old.log.gz'
        with gzip.open(gz_path, 'wt') as f:
            f.write('compressed content')

        result = self.manager.get_logs_summary()

        self.assertEqual(result['log_count'], 2)
        self.assertEqual(result['compressed_count'], 1)
        self.assertGreater(result['total_size_mb'], 0)
        self.assertIn('disk_health', result)

    def test_empty_logs_directory(self):
        """Test handling of empty logs directory"""
        result = self.manager.run_maintenance()

        self.assertEqual(result['rotation']['rotated'], 0)
        self.assertEqual(result['compression']['compressed'], 0)
        self.assertEqual(result['cleanup']['deleted'], 0)

    def test_nonexistent_logs_directory(self):
        """Test handling when logs directory doesn't exist"""
        manager = LogRotationManager(
            logs_dir=Path('/nonexistent/path/logs'),
        )

        result = manager.run_maintenance()

        self.assertEqual(result['rotation']['rotated'], 0)
        self.assertIn('does not exist', result['rotation']['message'])

    @patch('shutil.disk_usage')
    def test_emergency_cleanup_on_critical_disk(self, mock_disk_usage):
        """Test emergency cleanup when disk is critically full"""
        # Simulate 96% disk usage (critical threshold is 95%)
        mock_disk_usage.return_value = MagicMock(
            total=100 * 1024**3,  # 100GB
            used=96 * 1024**3,    # 96GB used
            free=4 * 1024**3,     # 4GB free
        )

        # Create some logs
        self._create_log_file('log1.log', size_kb=100)
        self._create_log_file('log2.log', size_kb=100, age_days=2)

        result = self.manager.run_maintenance()

        # Emergency cleanup should be triggered
        self.assertIsNotNone(result.get('emergency'))
        self.assertTrue(result['emergency']['triggered'])

    def test_gzip_compression_reduces_size(self):
        """Test that gzip compression actually reduces file size"""
        # Create a log with repetitive content (highly compressible)
        log_path = self._create_log_file('compressible.log', size_kb=100, age_days=2)
        original_size = log_path.stat().st_size

        result = self.manager.compress_old_logs()

        compressed_path = self.logs_dir / 'compressible.log.gz'
        compressed_size = compressed_path.stat().st_size

        self.assertEqual(result['compressed'], 1)
        self.assertLess(compressed_size, original_size)
        self.assertGreater(result['saved_mb'], 0)


class TestDiskHealthThresholds(unittest.TestCase):
    """Test disk health threshold configurations"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.logs_dir = Path(self.temp_dir) / 'logs'
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('shutil.disk_usage')
    def test_warning_threshold(self, mock_disk_usage):
        """Test that warning is triggered at warning threshold"""
        mock_disk_usage.return_value = MagicMock(
            total=100 * 1024**3,
            used=87 * 1024**3,  # 87% (above 85% warning)
            free=13 * 1024**3,
        )

        manager = LogRotationManager(
            logs_dir=self.logs_dir,
            disk_warning_threshold=85,
            disk_critical_threshold=95,
        )

        result = manager.check_disk_health()

        self.assertEqual(result['status'], 'warning')
        self.assertIsNotNone(result['warning'])
        self.assertIn('high', result['warning'].lower())

    @patch('shutil.disk_usage')
    def test_critical_threshold(self, mock_disk_usage):
        """Test that critical status is triggered at critical threshold"""
        mock_disk_usage.return_value = MagicMock(
            total=100 * 1024**3,
            used=97 * 1024**3,  # 97% (above 95% critical)
            free=3 * 1024**3,
        )

        manager = LogRotationManager(
            logs_dir=self.logs_dir,
            disk_warning_threshold=85,
            disk_critical_threshold=95,
        )

        result = manager.check_disk_health()

        self.assertEqual(result['status'], 'critical')
        self.assertIsNotNone(result['warning'])
        self.assertIn('CRITICAL', result['warning'])

    @patch('shutil.disk_usage')
    def test_healthy_disk(self, mock_disk_usage):
        """Test that healthy status is returned when below thresholds"""
        mock_disk_usage.return_value = MagicMock(
            total=100 * 1024**3,
            used=50 * 1024**3,  # 50% (below warning)
            free=50 * 1024**3,
        )

        manager = LogRotationManager(
            logs_dir=self.logs_dir,
            disk_warning_threshold=85,
            disk_critical_threshold=95,
        )

        result = manager.check_disk_health()

        self.assertEqual(result['status'], 'healthy')
        self.assertIsNone(result['warning'])


if __name__ == '__main__':
    unittest.main()
