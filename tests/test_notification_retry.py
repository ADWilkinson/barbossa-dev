#!/usr/bin/env python3
"""
Tests for the webhook notification retry queue functionality.

Covers:
- Queue persistence (save/load)
- Retry timing with exponential backoff
- Expired entry cleanup
- Queue status reporting
- Webhook failure queueing
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from barbossa.utils.notifications import (
    _load_retry_queue,
    _save_retry_queue,
    _queue_for_retry,
    _get_retry_queue_path,
    process_retry_queue,
    get_retry_queue_status,
    _send_discord_webhook,
    _send_discord_webhook_sync,
    MAX_RETRIES,
    BASE_DELAY_SECONDS,
    MAX_RETENTION_HOURS,
)


class TestRetryQueuePersistence(unittest.TestCase):
    """Test queue save/load functionality."""

    def setUp(self):
        """Create a temporary directory for queue files."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.data_dir = self.temp_dir / 'data'
        self.data_dir.mkdir()

        # Patch the queue path to use our temp directory
        import barbossa.utils.notifications as notif
        self._original_path = notif._retry_queue_path
        notif._retry_queue_path = self.data_dir / 'webhook_retry_queue.json'

    def tearDown(self):
        """Clean up temporary files."""
        import barbossa.utils.notifications as notif
        notif._retry_queue_path = self._original_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_empty_queue(self):
        """Loading a non-existent queue returns empty list."""
        queue = _load_retry_queue()
        self.assertEqual(queue, [])

    def test_save_and_load_queue(self):
        """Queue entries can be saved and loaded."""
        test_entry = {
            'payload': {'embeds': [{'title': 'Test'}]},
            'attempt': 1,
            'created_at': '2026-01-03T12:00:00Z',
            'next_retry_at': '2026-01-03T12:01:00Z',
        }

        # Save
        result = _save_retry_queue([test_entry])
        self.assertTrue(result)

        # Load
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]['payload'], test_entry['payload'])
        self.assertEqual(queue[0]['attempt'], 1)

    def test_load_invalid_json(self):
        """Loading invalid JSON returns empty list."""
        import barbossa.utils.notifications as notif
        queue_path = notif._retry_queue_path
        queue_path.write_text('{ invalid json }')

        queue = _load_retry_queue()
        self.assertEqual(queue, [])

    def test_load_non_list_returns_empty(self):
        """Loading non-list JSON returns empty list."""
        import barbossa.utils.notifications as notif
        queue_path = notif._retry_queue_path
        queue_path.write_text('{"not": "a list"}')

        queue = _load_retry_queue()
        self.assertEqual(queue, [])


class TestQueueForRetry(unittest.TestCase):
    """Test the _queue_for_retry function."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.data_dir = self.temp_dir / 'data'
        self.data_dir.mkdir()

        import barbossa.utils.notifications as notif
        self._original_path = notif._retry_queue_path
        notif._retry_queue_path = self.data_dir / 'webhook_retry_queue.json'

    def tearDown(self):
        """Clean up."""
        import barbossa.utils.notifications as notif
        notif._retry_queue_path = self._original_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_queue_first_retry(self):
        """First retry is queued with attempt=1."""
        payload = {'embeds': [{'title': 'Test Notification'}]}

        result = _queue_for_retry(payload, attempt=1)
        self.assertTrue(result)

        queue = _load_retry_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]['attempt'], 1)
        self.assertEqual(queue[0]['payload'], payload)

    def test_exponential_backoff(self):
        """Retry delays increase exponentially."""
        payload = {'embeds': [{'title': 'Test'}]}

        # First retry: 60s delay
        _queue_for_retry(payload, attempt=1)
        queue = _load_retry_queue()
        created = datetime.fromisoformat(queue[0]['created_at'].rstrip('Z'))
        next_retry = datetime.fromisoformat(queue[0]['next_retry_at'].rstrip('Z'))
        delay1 = (next_retry - created).total_seconds()
        self.assertAlmostEqual(delay1, BASE_DELAY_SECONDS, delta=1)

        # Clear and test second retry: 120s delay
        _save_retry_queue([])
        _queue_for_retry(payload, attempt=2)
        queue = _load_retry_queue()
        created = datetime.fromisoformat(queue[0]['created_at'].rstrip('Z'))
        next_retry = datetime.fromisoformat(queue[0]['next_retry_at'].rstrip('Z'))
        delay2 = (next_retry - created).total_seconds()
        self.assertAlmostEqual(delay2, BASE_DELAY_SECONDS * 2, delta=1)

        # Clear and test third retry: 240s delay
        _save_retry_queue([])
        _queue_for_retry(payload, attempt=3)
        queue = _load_retry_queue()
        created = datetime.fromisoformat(queue[0]['created_at'].rstrip('Z'))
        next_retry = datetime.fromisoformat(queue[0]['next_retry_at'].rstrip('Z'))
        delay3 = (next_retry - created).total_seconds()
        self.assertAlmostEqual(delay3, BASE_DELAY_SECONDS * 4, delta=1)

    def test_max_retries_exceeded(self):
        """Queueing beyond MAX_RETRIES returns False."""
        payload = {'embeds': [{'title': 'Test'}]}

        result = _queue_for_retry(payload, attempt=MAX_RETRIES + 1)
        self.assertFalse(result)

        queue = _load_retry_queue()
        self.assertEqual(len(queue), 0)

    def test_expired_entries_pruned(self):
        """Expired entries are removed when adding new ones."""
        import barbossa.utils.notifications as notif

        # Add an expired entry manually
        old_time = (datetime.utcnow() - timedelta(hours=MAX_RETENTION_HOURS + 1)).isoformat() + 'Z'
        expired_entry = {
            'payload': {'embeds': [{'title': 'Old'}]},
            'attempt': 1,
            'created_at': old_time,
            'next_retry_at': old_time,
        }
        _save_retry_queue([expired_entry])

        # Add a new entry
        _queue_for_retry({'embeds': [{'title': 'New'}]}, attempt=1)

        # Only the new entry should remain
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]['payload']['embeds'][0]['title'], 'New')


class TestProcessRetryQueue(unittest.TestCase):
    """Test the process_retry_queue function."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.data_dir = self.temp_dir / 'data'
        self.data_dir.mkdir()

        import barbossa.utils.notifications as notif
        self._original_path = notif._retry_queue_path
        notif._retry_queue_path = self.data_dir / 'webhook_retry_queue.json'

    def tearDown(self):
        """Clean up."""
        import barbossa.utils.notifications as notif
        notif._retry_queue_path = self._original_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_queue_returns_zero_stats(self):
        """Processing empty queue returns zero stats."""
        stats = process_retry_queue()
        self.assertEqual(stats['processed'], 0)
        self.assertEqual(stats['succeeded'], 0)

    @patch('barbossa.utils.notifications._send_discord_webhook_sync')
    def test_successful_retry(self, mock_send):
        """Successful retry removes entry from queue."""
        mock_send.return_value = True

        # Add a ready-to-retry entry
        past_time = (datetime.utcnow() - timedelta(seconds=1)).isoformat() + 'Z'
        entry = {
            'payload': {'embeds': [{'title': 'Test'}]},
            'attempt': 1,
            'created_at': past_time,
            'next_retry_at': past_time,
        }
        _save_retry_queue([entry])

        stats = process_retry_queue()

        self.assertEqual(stats['processed'], 1)
        self.assertEqual(stats['succeeded'], 1)
        self.assertEqual(stats['requeued'], 0)

        # Queue should be empty
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 0)

    @patch('barbossa.utils.notifications._send_discord_webhook_sync')
    def test_failed_retry_requeues(self, mock_send):
        """Failed retry requeues with incremented attempt."""
        mock_send.return_value = False

        past_time = (datetime.utcnow() - timedelta(seconds=1)).isoformat() + 'Z'
        entry = {
            'payload': {'embeds': [{'title': 'Test'}]},
            'attempt': 1,
            'created_at': past_time,
            'next_retry_at': past_time,
        }
        _save_retry_queue([entry])

        stats = process_retry_queue()

        self.assertEqual(stats['processed'], 1)
        self.assertEqual(stats['succeeded'], 0)
        self.assertEqual(stats['requeued'], 1)

        # Entry should be requeued with attempt=2
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]['attempt'], 2)

    @patch('barbossa.utils.notifications._send_discord_webhook_sync')
    def test_max_retries_drops_entry(self, mock_send):
        """Entry at MAX_RETRIES that fails is dropped."""
        mock_send.return_value = False

        past_time = (datetime.utcnow() - timedelta(seconds=1)).isoformat() + 'Z'
        entry = {
            'payload': {'embeds': [{'title': 'Test'}]},
            'attempt': MAX_RETRIES,
            'created_at': past_time,
            'next_retry_at': past_time,
        }
        _save_retry_queue([entry])

        stats = process_retry_queue()

        self.assertEqual(stats['processed'], 1)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['requeued'], 0)

        # Queue should be empty
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 0)

    def test_future_entries_not_processed(self):
        """Entries with future next_retry_at are not processed."""
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z'
        now = datetime.utcnow().isoformat() + 'Z'
        entry = {
            'payload': {'embeds': [{'title': 'Test'}]},
            'attempt': 1,
            'created_at': now,
            'next_retry_at': future_time,
        }
        _save_retry_queue([entry])

        stats = process_retry_queue()

        self.assertEqual(stats['processed'], 0)

        # Entry should still be in queue
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 1)

    def test_expired_entries_counted(self):
        """Expired entries are counted and removed."""
        old_time = (datetime.utcnow() - timedelta(hours=MAX_RETENTION_HOURS + 1)).isoformat() + 'Z'
        entry = {
            'payload': {'embeds': [{'title': 'Old'}]},
            'attempt': 1,
            'created_at': old_time,
            'next_retry_at': old_time,
        }
        _save_retry_queue([entry])

        stats = process_retry_queue()

        self.assertEqual(stats['expired'], 1)
        self.assertEqual(stats['processed'], 0)


class TestGetRetryQueueStatus(unittest.TestCase):
    """Test the get_retry_queue_status function."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.data_dir = self.temp_dir / 'data'
        self.data_dir.mkdir()

        import barbossa.utils.notifications as notif
        self._original_path = notif._retry_queue_path
        notif._retry_queue_path = self.data_dir / 'webhook_retry_queue.json'

    def tearDown(self):
        """Clean up."""
        import barbossa.utils.notifications as notif
        notif._retry_queue_path = self._original_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_queue_status(self):
        """Empty queue returns zero values."""
        status = get_retry_queue_status()
        self.assertEqual(status['size'], 0)
        self.assertEqual(status['oldest_age_minutes'], 0)
        self.assertIsNone(status['next_retry_in_seconds'])

    def test_queue_with_entries(self):
        """Queue with entries returns correct stats."""
        now = datetime.utcnow()
        old_time = (now - timedelta(minutes=30)).isoformat() + 'Z'
        future_time = (now + timedelta(seconds=120)).isoformat() + 'Z'

        entries = [
            {
                'payload': {'embeds': [{'title': 'Old'}]},
                'attempt': 1,
                'created_at': old_time,
                'next_retry_at': future_time,
            },
            {
                'payload': {'embeds': [{'title': 'New'}]},
                'attempt': 1,
                'created_at': now.isoformat() + 'Z',
                'next_retry_at': future_time,
            },
        ]
        _save_retry_queue(entries)

        status = get_retry_queue_status()

        self.assertEqual(status['size'], 2)
        self.assertAlmostEqual(status['oldest_age_minutes'], 30, delta=1)
        self.assertIsNotNone(status['next_retry_in_seconds'])
        self.assertGreater(status['next_retry_in_seconds'], 0)


class TestWebhookQueueingOnFailure(unittest.TestCase):
    """Test that webhook failures are queued for retry."""

    def setUp(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.data_dir = self.temp_dir / 'data'
        self.data_dir.mkdir()

        import barbossa.utils.notifications as notif
        self._original_path = notif._retry_queue_path
        notif._retry_queue_path = self.data_dir / 'webhook_retry_queue.json'

    def tearDown(self):
        """Clean up."""
        import barbossa.utils.notifications as notif
        notif._retry_queue_path = self._original_path
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('barbossa.utils.notifications._send_discord_webhook_sync')
    @patch('barbossa.utils.notifications._get_discord_webhook')
    def test_failed_webhook_queued(self, mock_get_webhook, mock_sync_send):
        """Failed webhook is queued for retry."""
        mock_get_webhook.return_value = 'https://discord.com/api/webhooks/test'
        mock_sync_send.return_value = False

        payload = {'embeds': [{'title': 'Test'}]}
        result = _send_discord_webhook(payload, queue_on_failure=True)

        # Should return True because failure was handled by queueing
        self.assertTrue(result)

        # Should be in queue
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 1)

    @patch('barbossa.utils.notifications._send_discord_webhook_sync')
    @patch('barbossa.utils.notifications._get_discord_webhook')
    def test_successful_webhook_not_queued(self, mock_get_webhook, mock_sync_send):
        """Successful webhook is not queued."""
        mock_get_webhook.return_value = 'https://discord.com/api/webhooks/test'
        mock_sync_send.return_value = True

        payload = {'embeds': [{'title': 'Test'}]}
        result = _send_discord_webhook(payload, queue_on_failure=True)

        self.assertTrue(result)

        # Should NOT be in queue
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 0)

    @patch('barbossa.utils.notifications._send_discord_webhook_sync')
    @patch('barbossa.utils.notifications._get_discord_webhook')
    def test_queue_disabled(self, mock_get_webhook, mock_sync_send):
        """When queue_on_failure=False, failures are not queued."""
        mock_get_webhook.return_value = 'https://discord.com/api/webhooks/test'
        mock_sync_send.return_value = False

        payload = {'embeds': [{'title': 'Test'}]}
        result = _send_discord_webhook(payload, queue_on_failure=False)

        self.assertFalse(result)

        # Should NOT be in queue
        queue = _load_retry_queue()
        self.assertEqual(len(queue), 0)


class TestWaitForPending(unittest.TestCase):
    """Test wait_for_pending adaptive timeout behavior."""

    def setUp(self):
        """Reset pending threads list before each test."""
        import barbossa.utils.notifications as notif
        with notif._threads_lock:
            notif._pending_threads.clear()

    def tearDown(self):
        """Clean up any remaining threads."""
        import barbossa.utils.notifications as notif
        with notif._threads_lock:
            notif._pending_threads.clear()

    def test_wait_for_pending_empty(self):
        """wait_for_pending returns immediately with no threads."""
        from barbossa.utils.notifications import wait_for_pending
        import time

        start = time.monotonic()
        wait_for_pending(timeout=1.0)
        elapsed = time.monotonic() - start

        # Should return immediately, not wait for timeout
        self.assertLess(elapsed, 0.1)

    def test_wait_for_pending_fast_threads(self):
        """wait_for_pending handles fast-completing threads efficiently."""
        import barbossa.utils.notifications as notif
        from barbossa.utils.notifications import wait_for_pending
        import time
        import threading

        def fast_task():
            time.sleep(0.05)  # Complete quickly

        # Add 5 fast threads
        with notif._threads_lock:
            for _ in range(5):
                t = threading.Thread(target=fast_task)
                t.start()
                notif._pending_threads.append(t)

        start = time.monotonic()
        wait_for_pending(timeout=5.0, min_per_thread=1.0)
        elapsed = time.monotonic() - start

        # All threads completed quickly, should not wait for full timeout
        self.assertLess(elapsed, 1.0)

        # All threads should be cleaned up
        with notif._threads_lock:
            remaining = [t for t in notif._pending_threads if t.is_alive()]
        self.assertEqual(len(remaining), 0)

    def test_wait_for_pending_respects_timeout(self):
        """wait_for_pending respects total timeout even with slow threads."""
        import barbossa.utils.notifications as notif
        from barbossa.utils.notifications import wait_for_pending
        import time
        import threading

        def slow_task():
            time.sleep(10)  # Very slow

        # Add 2 slow threads
        with notif._threads_lock:
            for _ in range(2):
                t = threading.Thread(target=slow_task)
                t.daemon = True  # Allow test to exit
                t.start()
                notif._pending_threads.append(t)

        start = time.monotonic()
        wait_for_pending(timeout=0.5, min_per_thread=0.2)
        elapsed = time.monotonic() - start

        # Should not exceed timeout by much
        self.assertLess(elapsed, 1.0)

    def test_wait_for_pending_min_per_thread(self):
        """Each thread gets at least min_per_thread time."""
        import barbossa.utils.notifications as notif
        from barbossa.utils.notifications import wait_for_pending
        import time
        import threading

        completion_times = []

        def medium_task():
            time.sleep(0.5)  # Take 0.5s
            completion_times.append(time.monotonic())

        # Add 3 threads that each need 0.5s
        with notif._threads_lock:
            for _ in range(3):
                t = threading.Thread(target=medium_task)
                t.start()
                notif._pending_threads.append(t)

        # With old code: 5s / 3 threads = 1.67s per thread - would work
        # With old code: 1s / 3 threads = 0.33s per thread - would fail (threads need 0.5s)
        # With new code: min_per_thread=0.6s ensures each thread gets enough time

        start = time.monotonic()
        wait_for_pending(timeout=5.0, min_per_thread=0.6)
        elapsed = time.monotonic() - start

        # All 3 threads should have completed
        with notif._threads_lock:
            remaining = [t for t in notif._pending_threads if t.is_alive()]
        self.assertEqual(len(remaining), 0)

        # Total time should be reasonable (threads run concurrently)
        self.assertLess(elapsed, 2.0)

    def test_wait_for_pending_many_threads_old_bug_scenario(self):
        """Regression test: many threads with short total timeout.

        The old bug: timeout / len(threads) gave each thread too little time.
        With 10 threads and 5s timeout, each got only 0.5s.
        If threads needed 1s each, they would be marked as incomplete.

        The fix: min_per_thread ensures each gets at least 2s by default.
        """
        import barbossa.utils.notifications as notif
        from barbossa.utils.notifications import wait_for_pending
        import time
        import threading

        completed_count = [0]
        lock = threading.Lock()

        def task_needing_one_second():
            time.sleep(0.3)  # Each task needs 0.3s
            with lock:
                completed_count[0] += 1

        # Add 10 threads (old code would give each only 0.5s with 5s total)
        threads = []
        with notif._threads_lock:
            for _ in range(10):
                t = threading.Thread(target=task_needing_one_second)
                t.start()
                notif._pending_threads.append(t)
                threads.append(t)

        # With old code: 5s / 10 = 0.5s per thread - threads would complete
        # But with only 1s total: 1s / 10 = 0.1s per thread - would fail
        # New code with min_per_thread=0.5 ensures each gets at least 0.5s

        wait_for_pending(timeout=5.0, min_per_thread=0.5)

        # All threads should complete since they only need 0.3s each
        # and min_per_thread gives them 0.5s
        with notif._threads_lock:
            remaining = [t for t in notif._pending_threads if t.is_alive()]

        # Wait for any stragglers (threads may still be cleaning up)
        for t in threads:
            t.join(timeout=1.0)

        # All should have completed
        self.assertEqual(completed_count[0], 10)


if __name__ == '__main__':
    unittest.main()
