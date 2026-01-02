"""
Log rotation and disk management utilities for Barbossa agents.

Features:
- Size-based rotation (rotate when files exceed threshold)
- Compression of rotated logs using gzip
- Disk usage monitoring with warnings
- Cleanup of old logs based on age and disk pressure
"""

import gzip
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_MAX_LOG_SIZE_MB = 50  # Rotate when log exceeds this size
DEFAULT_COMPRESS_AFTER_DAYS = 3  # Compress logs older than this
DEFAULT_DELETE_AFTER_DAYS = 14  # Delete logs older than this
DEFAULT_DISK_WARNING_THRESHOLD = 85  # Warn if disk usage exceeds this %
DEFAULT_DISK_CRITICAL_THRESHOLD = 95  # Aggressive cleanup if disk usage exceeds this %


class LogRotationManager:
    """Manages log rotation, compression, and cleanup for Barbossa."""

    def __init__(
        self,
        logs_dir: Path,
        max_log_size_mb: int = DEFAULT_MAX_LOG_SIZE_MB,
        compress_after_days: int = DEFAULT_COMPRESS_AFTER_DAYS,
        delete_after_days: int = DEFAULT_DELETE_AFTER_DAYS,
        disk_warning_threshold: int = DEFAULT_DISK_WARNING_THRESHOLD,
        disk_critical_threshold: int = DEFAULT_DISK_CRITICAL_THRESHOLD,
    ):
        self.logs_dir = Path(logs_dir)
        self.max_log_size_bytes = max_log_size_mb * 1024 * 1024
        self.compress_after_days = compress_after_days
        self.delete_after_days = delete_after_days
        self.disk_warning_threshold = disk_warning_threshold
        self.disk_critical_threshold = disk_critical_threshold

    def get_disk_usage(self) -> Tuple[int, int, int]:
        """Get disk usage statistics for the logs directory.

        Returns:
            Tuple of (total_bytes, used_bytes, free_bytes)
        """
        try:
            stat = shutil.disk_usage(self.logs_dir)
            return stat.total, stat.used, stat.free
        except OSError as e:
            logger.warning(f"Could not get disk usage: {e}")
            return 0, 0, 0

    def get_disk_usage_percent(self) -> float:
        """Get disk usage as a percentage."""
        total, used, _ = self.get_disk_usage()
        if total == 0:
            return 0.0
        return (used / total) * 100

    def check_disk_health(self) -> Dict:
        """Check disk usage and return health status.

        Returns:
            Dict with status, percent_used, and any warnings
        """
        result = {
            'status': 'healthy',
            'percent_used': 0.0,
            'warning': None,
            'total_gb': 0.0,
            'free_gb': 0.0,
        }

        total, used, free = self.get_disk_usage()
        if total == 0:
            result['status'] = 'unknown'
            result['warning'] = 'Could not determine disk usage'
            return result

        percent_used = (used / total) * 100
        result['percent_used'] = round(percent_used, 1)
        result['total_gb'] = round(total / (1024**3), 2)
        result['free_gb'] = round(free / (1024**3), 2)

        if percent_used >= self.disk_critical_threshold:
            result['status'] = 'critical'
            result['warning'] = f'Disk usage CRITICAL: {percent_used:.1f}% used. Aggressive cleanup needed.'
        elif percent_used >= self.disk_warning_threshold:
            result['status'] = 'warning'
            result['warning'] = f'Disk usage high: {percent_used:.1f}% used. Consider cleanup.'

        return result

    def rotate_large_logs(self) -> Dict:
        """Rotate log files that exceed the size threshold.

        Renames large log files with a timestamp suffix so new logs can be written.
        This prevents any single log from growing unbounded.

        Returns:
            Dict with rotation statistics
        """
        result = {
            'action': 'log_rotation',
            'rotated': 0,
            'total_size_mb': 0.0,
            'files': [],
            'message': '',
        }

        if not self.logs_dir.exists():
            result['message'] = 'Logs directory does not exist'
            return result

        for log_file in self.logs_dir.glob("*.log"):
            try:
                size = log_file.stat().st_size
                if size > self.max_log_size_bytes:
                    # Rotate the file by renaming with timestamp
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    rotated_name = f"{log_file.stem}.{timestamp}.log"
                    rotated_path = log_file.with_name(rotated_name)

                    log_file.rename(rotated_path)

                    result['rotated'] += 1
                    result['total_size_mb'] += size / (1024 * 1024)
                    result['files'].append(rotated_name)

                    logger.info(f"Rotated large log: {log_file.name} ({size / (1024*1024):.1f}MB)")
            except OSError as e:
                logger.warning(f"Could not rotate {log_file}: {e}")

        result['total_size_mb'] = round(result['total_size_mb'], 2)
        result['message'] = f"Rotated {result['rotated']} oversized logs"
        return result

    def compress_old_logs(self) -> Dict:
        """Compress logs older than the threshold using gzip.

        Returns:
            Dict with compression statistics
        """
        result = {
            'action': 'log_compression',
            'compressed': 0,
            'saved_mb': 0.0,
            'files': [],
            'message': '',
        }

        if not self.logs_dir.exists():
            result['message'] = 'Logs directory does not exist'
            return result

        cutoff = datetime.now() - timedelta(days=self.compress_after_days)

        for log_file in self.logs_dir.glob("*.log"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    original_size = log_file.stat().st_size
                    compressed_path = log_file.with_suffix('.log.gz')

                    # Compress the file
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb', compresslevel=6) as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    compressed_size = compressed_path.stat().st_size
                    saved = original_size - compressed_size

                    # Remove original after successful compression
                    log_file.unlink()

                    result['compressed'] += 1
                    result['saved_mb'] += saved / (1024 * 1024)
                    result['files'].append(log_file.name)

                    logger.info(
                        f"Compressed {log_file.name}: "
                        f"{original_size / (1024*1024):.1f}MB -> {compressed_size / (1024*1024):.1f}MB "
                        f"(saved {saved / (1024*1024):.1f}MB)"
                    )
            except OSError as e:
                logger.warning(f"Could not compress {log_file}: {e}")
            except Exception as e:
                logger.warning(f"Error compressing {log_file}: {e}")

        result['saved_mb'] = round(result['saved_mb'], 2)
        result['message'] = f"Compressed {result['compressed']} logs, saved {result['saved_mb']}MB"
        return result

    def cleanup_old_logs(self, days: Optional[int] = None) -> Dict:
        """Delete logs older than the threshold.

        Args:
            days: Override the default delete_after_days setting

        Returns:
            Dict with cleanup statistics
        """
        delete_days = days if days is not None else self.delete_after_days

        result = {
            'action': 'log_cleanup',
            'deleted': 0,
            'freed_mb': 0.0,
            'message': '',
        }

        if not self.logs_dir.exists():
            result['message'] = 'Logs directory does not exist'
            return result

        cutoff = datetime.now() - timedelta(days=delete_days)
        deleted = 0
        freed_bytes = 0

        # Delete old .log files
        for log_file in self.logs_dir.glob("*.log"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    size = log_file.stat().st_size
                    log_file.unlink()
                    deleted += 1
                    freed_bytes += size
            except OSError as e:
                logger.warning(f"Could not delete {log_file}: {e}")

        # Delete old compressed .log.gz files
        for log_file in self.logs_dir.glob("*.log.gz"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    size = log_file.stat().st_size
                    log_file.unlink()
                    deleted += 1
                    freed_bytes += size
            except OSError as e:
                logger.warning(f"Could not delete {log_file}: {e}")

        if deleted > 0:
            freed_mb = round(freed_bytes / (1024 * 1024), 2)
            logger.info(f"Deleted {deleted} old logs, freed {freed_mb}MB")
            result['deleted'] = deleted
            result['freed_mb'] = freed_mb

        result['message'] = f"Deleted {deleted} logs older than {delete_days} days"
        return result

    def emergency_cleanup(self) -> Dict:
        """Aggressive cleanup when disk is critically full.

        Deletes logs more aggressively (older than 3 days) and compresses everything.

        Returns:
            Dict with emergency cleanup statistics
        """
        result = {
            'action': 'emergency_cleanup',
            'triggered': True,
            'rotation': {},
            'compression': {},
            'cleanup': {},
            'disk_before': 0.0,
            'disk_after': 0.0,
            'message': '',
        }

        disk_before = self.get_disk_usage_percent()
        result['disk_before'] = round(disk_before, 1)

        logger.warning(f"Emergency cleanup triggered - disk at {disk_before:.1f}%")

        # Step 1: Rotate any large logs immediately
        result['rotation'] = self.rotate_large_logs()

        # Step 2: Compress anything older than 1 day
        original_compress_days = self.compress_after_days
        self.compress_after_days = 1
        result['compression'] = self.compress_old_logs()
        self.compress_after_days = original_compress_days

        # Step 3: Delete logs older than 3 days (more aggressive)
        result['cleanup'] = self.cleanup_old_logs(days=3)

        disk_after = self.get_disk_usage_percent()
        result['disk_after'] = round(disk_after, 1)

        freed = disk_before - disk_after
        result['message'] = f"Emergency cleanup freed {freed:.1f}% disk space ({disk_before:.1f}% -> {disk_after:.1f}%)"

        logger.info(result['message'])
        return result

    def run_maintenance(self) -> Dict:
        """Run full log maintenance cycle.

        This is the main entry point for log maintenance. It:
        1. Checks disk health
        2. Rotates large logs
        3. Compresses old logs
        4. Deletes very old logs
        5. Triggers emergency cleanup if disk is critical

        Returns:
            Dict with all maintenance results
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'disk_health': {},
            'rotation': {},
            'compression': {},
            'cleanup': {},
            'emergency': None,
            'summary': '',
        }

        # Check disk health first
        result['disk_health'] = self.check_disk_health()

        # If disk is critical, do emergency cleanup instead of normal maintenance
        if result['disk_health']['status'] == 'critical':
            result['emergency'] = self.emergency_cleanup()
            result['summary'] = f"Emergency cleanup performed: {result['emergency']['message']}"
            return result

        # Normal maintenance cycle
        result['rotation'] = self.rotate_large_logs()
        result['compression'] = self.compress_old_logs()
        result['cleanup'] = self.cleanup_old_logs()

        # Build summary
        actions = []
        if result['rotation']['rotated'] > 0:
            actions.append(f"{result['rotation']['rotated']} rotated")
        if result['compression']['compressed'] > 0:
            actions.append(f"{result['compression']['compressed']} compressed")
        if result['cleanup']['deleted'] > 0:
            actions.append(f"{result['cleanup']['deleted']} deleted")

        if actions:
            result['summary'] = f"Log maintenance: {', '.join(actions)}"
        else:
            result['summary'] = "Log maintenance: no action needed"

        if result['disk_health'].get('warning'):
            result['summary'] += f" | {result['disk_health']['warning']}"

        return result

    def get_logs_summary(self) -> Dict:
        """Get a summary of current log state.

        Returns:
            Dict with log counts, sizes, and disk usage
        """
        result = {
            'log_count': 0,
            'compressed_count': 0,
            'total_size_mb': 0.0,
            'oldest_log': None,
            'newest_log': None,
            'disk_health': self.check_disk_health(),
        }

        if not self.logs_dir.exists():
            return result

        log_files = list(self.logs_dir.glob("*.log"))
        compressed_files = list(self.logs_dir.glob("*.log.gz"))

        result['log_count'] = len(log_files)
        result['compressed_count'] = len(compressed_files)

        total_size = 0
        oldest_mtime = None
        newest_mtime = None

        for f in log_files + compressed_files:
            try:
                stat = f.stat()
                total_size += stat.st_size
                mtime = stat.st_mtime

                if oldest_mtime is None or mtime < oldest_mtime:
                    oldest_mtime = mtime
                    result['oldest_log'] = f.name

                if newest_mtime is None or mtime > newest_mtime:
                    newest_mtime = mtime
                    result['newest_log'] = f.name
            except OSError:
                pass

        result['total_size_mb'] = round(total_size / (1024 * 1024), 2)
        return result
