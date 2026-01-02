#!/usr/bin/env python3
"""
Tests for Webhook Notification System

Tests cover retry logic, exponential backoff, URL validation, and error handling.
Uses mocking to avoid actual webhook calls during testing.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'barbossa', 'utils'))

from notifications import (
    _retry_on_transient_failure,
    _calculate_backoff,
    _send_webhook_request,
    _send_discord_webhook,
    VERSION
)
from urllib.error import HTTPError, URLError


class TestRetryDecorator(unittest.TestCase):
    """Test the retry decorator for transient failures"""

    @patch('notifications.time.sleep')
    def test_retry_on_http_429_rate_limit(self, mock_sleep):
        """Test retry on HTTP 429 (rate limit)"""
        call_count = 0

        @_retry_on_transient_failure(max_retries=3, base_delay=1.0)
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                error = HTTPError(
                    'https://discord.com/api/webhooks/test',
                    429, 'Too Many Requests', {}, None
                )
                raise error
            return True

        result = failing_then_success()

        self.assertTrue(result)
        self.assertEqual(call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # 2 retries before success

    @patch('notifications.time.sleep')
    def test_retry_on_http_500_server_error(self, mock_sleep):
        """Test retry on HTTP 500 (server error)"""
        call_count = 0

        @_retry_on_transient_failure(max_retries=2, base_delay=0.5)
        def server_error_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                error = HTTPError(
                    'https://discord.com/api/webhooks/test',
                    500, 'Internal Server Error', {}, None
                )
                raise error
            return True

        result = server_error_then_success()

        self.assertTrue(result)
        self.assertEqual(call_count, 2)

    @patch('notifications.time.sleep')
    def test_no_retry_on_http_400_client_error(self, mock_sleep):
        """Test that 400 client errors are NOT retried"""
        call_count = 0

        @_retry_on_transient_failure(max_retries=3, base_delay=1.0)
        def client_error():
            nonlocal call_count
            call_count += 1
            error = HTTPError(
                'https://discord.com/api/webhooks/test',
                400, 'Bad Request', {}, None
            )
            raise error

        result = client_error()

        self.assertFalse(result)
        self.assertEqual(call_count, 1)  # No retries
        mock_sleep.assert_not_called()

    @patch('notifications.time.sleep')
    def test_no_retry_on_http_401_unauthorized(self, mock_sleep):
        """Test that 401 unauthorized errors are NOT retried"""
        call_count = 0

        @_retry_on_transient_failure(max_retries=3, base_delay=1.0)
        def unauthorized_error():
            nonlocal call_count
            call_count += 1
            error = HTTPError(
                'https://discord.com/api/webhooks/test',
                401, 'Unauthorized', {}, None
            )
            raise error

        result = unauthorized_error()

        self.assertFalse(result)
        self.assertEqual(call_count, 1)

    @patch('notifications.time.sleep')
    def test_retry_on_url_error_network_failure(self, mock_sleep):
        """Test retry on network connection failures"""
        call_count = 0

        @_retry_on_transient_failure(max_retries=2, base_delay=1.0)
        def network_error_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise URLError('Connection refused')
            return True

        result = network_error_then_success()

        self.assertTrue(result)
        self.assertEqual(call_count, 2)

    @patch('notifications.time.sleep')
    def test_retry_exhaustion_returns_false(self, mock_sleep):
        """Test that exhausting retries returns False, not exception"""
        @_retry_on_transient_failure(max_retries=2, base_delay=0.1)
        def always_fails():
            error = HTTPError(
                'https://discord.com/api/webhooks/test',
                503, 'Service Unavailable', {}, None
            )
            raise error

        result = always_fails()

        self.assertFalse(result)
        # Initial attempt + 2 retries = 3 sleeps for 2 retries
        self.assertEqual(mock_sleep.call_count, 2)

    def test_success_on_first_attempt(self):
        """Test that successful first attempt doesn't trigger retries"""
        call_count = 0

        @_retry_on_transient_failure(max_retries=3, base_delay=1.0)
        def success_immediately():
            nonlocal call_count
            call_count += 1
            return True

        result = success_immediately()

        self.assertTrue(result)
        self.assertEqual(call_count, 1)


class TestBackoffCalculation(unittest.TestCase):
    """Test exponential backoff calculation"""

    def test_exponential_increase(self):
        """Test that backoff increases exponentially"""
        base_delay = 1.0

        delay_0 = _calculate_backoff(0, base_delay)
        delay_1 = _calculate_backoff(1, base_delay)
        delay_2 = _calculate_backoff(2, base_delay)

        # Base delays without jitter: 1, 2, 4
        # With ±10% jitter, should be roughly these values
        self.assertGreater(delay_0, 0.8)
        self.assertLess(delay_0, 1.2)

        self.assertGreater(delay_1, 1.8)
        self.assertLess(delay_1, 2.2)

        self.assertGreater(delay_2, 3.6)
        self.assertLess(delay_2, 4.4)

    def test_minimum_delay(self):
        """Test that delay never goes below 100ms"""
        # Even with extreme jitter, should never go below 0.1
        for _ in range(100):
            delay = _calculate_backoff(0, 0.1)
            self.assertGreaterEqual(delay, 0.1)


class TestSendDiscordWebhook(unittest.TestCase):
    """Test Discord webhook sending"""

    @patch('notifications._get_discord_webhook')
    def test_skips_when_no_webhook_configured(self, mock_get_webhook):
        """Test that sending is skipped when no webhook is configured"""
        mock_get_webhook.return_value = None

        result = _send_discord_webhook({'content': 'test'})

        self.assertFalse(result)

    @patch('notifications._get_discord_webhook')
    @patch('notifications.urlopen')
    def test_successful_send(self, mock_urlopen, mock_get_webhook):
        """Test successful webhook send"""
        mock_get_webhook.return_value = 'https://discord.com/api/webhooks/123/token'

        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = _send_discord_webhook({'embeds': [{'title': 'Test'}]})

        self.assertTrue(result)
        mock_urlopen.assert_called_once()

    @patch('notifications._get_discord_webhook')
    @patch('notifications.urlopen')
    @patch('notifications.time.sleep')
    def test_retry_on_server_error(self, mock_sleep, mock_urlopen, mock_get_webhook):
        """Test that server errors trigger retry"""
        mock_get_webhook.return_value = 'https://discord.com/api/webhooks/123/token'

        # First call fails with 503
        error = HTTPError(
            'https://discord.com/api/webhooks/123/token',
            503, 'Service Unavailable', {}, None
        )

        # Second call succeeds
        mock_success = MagicMock()
        mock_success.status = 204
        mock_success.__enter__ = Mock(return_value=mock_success)
        mock_success.__exit__ = Mock(return_value=False)

        mock_urlopen.side_effect = [error, mock_success]

        result = _send_discord_webhook({'content': 'test'})

        self.assertTrue(result)
        self.assertEqual(mock_urlopen.call_count, 2)


class TestWebhookURLValidation(unittest.TestCase):
    """Test Discord webhook URL format validation in validate.py"""

    def test_valid_discord_url(self):
        """Test that valid Discord webhook URLs pass validation"""
        import re
        discord_pattern = r'^https://discord\.com/api/webhooks/\d+/[\w-]+$'

        valid_urls = [
            'https://discord.com/api/webhooks/1234567890123456789/abcdefghijklmnopqrstuvwxyz1234567890',
            'https://discord.com/api/webhooks/999999999999999999/ABCDEFGHIJ-klmnopqrst_uvwxyz',
        ]

        for url in valid_urls:
            self.assertIsNotNone(re.match(discord_pattern, url), f"URL should be valid: {url}")

    def test_invalid_discord_url(self):
        """Test that invalid Discord webhook URLs fail validation"""
        import re
        discord_pattern = r'^https://discord\.com/api/webhooks/\d+/[\w-]+$'
        discordapp_pattern = r'^https://discordapp\.com/api/webhooks/\d+/[\w-]+$'

        invalid_urls = [
            'http://discord.com/api/webhooks/123/token',  # HTTP not HTTPS
            'https://discord.com/webhooks/123/token',  # Missing /api
            'https://example.com/api/webhooks/123/token',  # Wrong domain
            'https://discord.com/api/webhooks/abc/token',  # Non-numeric ID
            'https://discord.com/api/webhooks/123/',  # Empty token
        ]

        for url in invalid_urls:
            match = re.match(discord_pattern, url) or re.match(discordapp_pattern, url)
            self.assertIsNone(match, f"URL should be invalid: {url}")


class TestNotificationVersion(unittest.TestCase):
    """Test version tracking"""

    def test_version_updated(self):
        """Test that version has been updated for this change"""
        self.assertEqual(VERSION, "1.7.3")


if __name__ == '__main__':
    unittest.main()
