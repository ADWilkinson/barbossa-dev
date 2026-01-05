#!/usr/bin/env python3
"""
Tests for barbossa.utils.metrics module.

Tests the MetricsCollector class and related functions for:
- Metric collection and storage
- Token extraction from Claude CLI output
- Cost calculation
- Metrics aggregation and summary
- File rotation
"""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from barbossa.utils.metrics import (
    MetricsCollector,
    get_metrics,
    get_metrics_summary,
    rotate_metrics,
    _extract_token_usage,
    _calculate_cost,
    _get_metrics_path,
    _append_metric,
    _rotate_metrics_file,
    METRICS_RETENTION_DAYS,
    CLAUDE_PRICING,
)


@pytest.fixture
def temp_metrics_dir(tmp_path):
    """Create a temporary directory for metrics storage."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    with patch.dict(os.environ, {'BARBOSSA_DIR': str(tmp_path)}):
        yield tmp_path


@pytest.fixture
def sample_metric():
    """Create a sample metric entry."""
    return {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'agent': 'engineer',
        'repo_name': 'test-repo',
        'session_id': '20260105-120000-abc123',
        'model': 'opus',
        'duration_seconds': 45.5,
        'success': True,
        'input_tokens': 1000,
        'output_tokens': 3000,
        'total_tokens': 4000,
        'cost_usd': 0.24,
    }


class TestTokenExtraction:
    """Tests for _extract_token_usage function."""

    def test_extract_tokens_standard_format(self):
        """Test extraction from standard 'Input tokens: X' format."""
        output = """
        Some output here...
        Input tokens: 1234
        Output tokens: 5678
        Done!
        """
        result = _extract_token_usage(output)
        assert result['input_tokens'] == 1234
        assert result['output_tokens'] == 5678

    def test_extract_tokens_combined_format(self):
        """Test extraction from 'tokens: input=X, output=Y' format."""
        output = "tokens: input=2000, output=6000"
        result = _extract_token_usage(output)
        assert result['input_tokens'] == 2000
        assert result['output_tokens'] == 6000

    def test_extract_tokens_total_only(self):
        """Test estimation from total tokens only."""
        output = "Total tokens: 10000"
        result = _extract_token_usage(output)
        # Should estimate 25% input, 75% output
        assert result['input_tokens'] == 2500
        assert result['output_tokens'] == 7500

    def test_extract_tokens_empty_output(self):
        """Test with empty output."""
        result = _extract_token_usage("")
        assert result['input_tokens'] == 0
        assert result['output_tokens'] == 0

    def test_extract_tokens_no_match(self):
        """Test with output containing no token info."""
        output = "Just some random text without token counts"
        result = _extract_token_usage(output)
        assert result['input_tokens'] == 0
        assert result['output_tokens'] == 0

    def test_extract_tokens_case_insensitive(self):
        """Test case insensitive matching."""
        output = "INPUT TOKENS: 500\nOUTPUT TOKENS: 1500"
        result = _extract_token_usage(output)
        assert result['input_tokens'] == 500
        assert result['output_tokens'] == 1500


class TestCostCalculation:
    """Tests for _calculate_cost function."""

    def test_calculate_cost_opus(self):
        """Test cost calculation for opus model."""
        tokens = {'input_tokens': 1000000, 'output_tokens': 1000000}
        cost = _calculate_cost(tokens, 'opus')
        # Opus: $15/1M input + $75/1M output = $90
        assert cost == 90.0

    def test_calculate_cost_sonnet(self):
        """Test cost calculation for sonnet model."""
        tokens = {'input_tokens': 1000000, 'output_tokens': 1000000}
        cost = _calculate_cost(tokens, 'sonnet')
        # Sonnet: $3/1M input + $15/1M output = $18
        assert cost == 18.0

    def test_calculate_cost_haiku(self):
        """Test cost calculation for haiku model."""
        tokens = {'input_tokens': 1000000, 'output_tokens': 1000000}
        cost = _calculate_cost(tokens, 'haiku')
        # Haiku: $0.25/1M input + $1.25/1M output = $1.50
        assert cost == 1.5

    def test_calculate_cost_small_usage(self):
        """Test cost calculation for small token counts."""
        tokens = {'input_tokens': 1000, 'output_tokens': 3000}
        cost = _calculate_cost(tokens, 'opus')
        # 1K input @ $15/1M = $0.015
        # 3K output @ $75/1M = $0.225
        # Total = $0.24
        assert cost == 0.24

    def test_calculate_cost_zero_tokens(self):
        """Test cost with zero tokens."""
        tokens = {'input_tokens': 0, 'output_tokens': 0}
        cost = _calculate_cost(tokens, 'opus')
        assert cost == 0.0

    def test_calculate_cost_unknown_model_defaults_to_opus(self):
        """Test that unknown model falls back to default pricing."""
        tokens = {'input_tokens': 1000, 'output_tokens': 3000}
        cost = _calculate_cost(tokens, 'unknown-model')
        expected = _calculate_cost(tokens, 'opus')
        assert cost == expected


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_basic_collection(self, temp_metrics_dir):
        """Test basic metrics collection flow."""
        collector = MetricsCollector(
            agent='engineer',
            repo_name='test-repo',
            session_id='test-session',
            model='opus'
        )
        collector.start()
        time.sleep(0.1)  # Simulate some work

        metric = collector.complete(success=True)

        assert metric['agent'] == 'engineer'
        assert metric['repo_name'] == 'test-repo'
        assert metric['session_id'] == 'test-session'
        assert metric['model'] == 'opus'
        assert metric['success'] is True
        assert metric['duration_seconds'] >= 0.1
        assert 'timestamp' in metric

    def test_collection_with_output_text(self, temp_metrics_dir):
        """Test token extraction from output text."""
        collector = MetricsCollector(agent='tech_lead', model='opus')
        collector.start()

        output = "Input tokens: 500\nOutput tokens: 1500"
        metric = collector.complete(success=True, output_text=output)

        assert metric['input_tokens'] == 500
        assert metric['output_tokens'] == 1500
        assert metric['total_tokens'] == 2000
        assert metric['cost_usd'] > 0

    def test_collection_with_error(self, temp_metrics_dir):
        """Test metrics collection on failure."""
        collector = MetricsCollector(agent='engineer')
        collector.start()

        metric = collector.complete(
            success=False,
            error_type='timeout',
            error_message='Claude timed out after 30 minutes'
        )

        assert metric['success'] is False
        assert metric['error_type'] == 'timeout'
        assert 'timed out' in metric['error_message']

    def test_collection_with_pr_info(self, temp_metrics_dir):
        """Test metrics collection with PR information."""
        collector = MetricsCollector(agent='engineer', repo_name='my-repo')
        collector.start()

        metric = collector.complete(
            success=True,
            pr_url='https://github.com/owner/repo/pull/123',
            pr_number=123
        )

        assert metric['pr_url'] == 'https://github.com/owner/repo/pull/123'
        assert metric['pr_number'] == 123

    def test_collection_with_custom_data(self, temp_metrics_dir):
        """Test metrics collection with custom data."""
        collector = MetricsCollector(agent='tech_lead')
        collector.start()

        metric = collector.complete(
            success=True,
            custom_data={'decision': 'MERGE', 'value_score': 8}
        )

        assert metric['custom']['decision'] == 'MERGE'
        assert metric['custom']['value_score'] == 8

    def test_context_manager_success(self, temp_metrics_dir):
        """Test context manager with successful execution."""
        with MetricsCollector(agent='test') as collector:
            pass  # Simulate successful work

        # Metric should be auto-completed with success
        metrics = get_metrics(days=1)
        assert len(metrics) >= 1
        assert metrics[0]['success'] is True

    def test_context_manager_exception(self, temp_metrics_dir):
        """Test context manager with exception."""
        try:
            with MetricsCollector(agent='test') as collector:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Metric should be auto-completed with failure
        metrics = get_metrics(days=1)
        assert len(metrics) >= 1
        assert metrics[0]['success'] is False
        assert metrics[0]['error_type'] == 'ValueError'

    def test_double_complete_warning(self, temp_metrics_dir):
        """Test that double complete logs warning but doesn't crash."""
        collector = MetricsCollector(agent='test')
        collector.start()
        collector.complete(success=True)
        result = collector.complete(success=True)  # Second call
        assert result == {}  # Should return empty on duplicate

    def test_complete_without_start(self, temp_metrics_dir):
        """Test complete without start (duration should be 0)."""
        collector = MetricsCollector(agent='test')
        metric = collector.complete(success=True)
        assert metric['duration_seconds'] == 0


class TestMetricsRetrieval:
    """Tests for get_metrics and get_metrics_summary functions."""

    def test_get_metrics_empty(self, temp_metrics_dir):
        """Test get_metrics with no data."""
        metrics = get_metrics(days=7)
        assert metrics == []

    def test_get_metrics_with_data(self, temp_metrics_dir):
        """Test get_metrics with data."""
        # Add some metrics
        with MetricsCollector(agent='engineer', repo_name='repo1') as m:
            pass
        with MetricsCollector(agent='tech_lead', repo_name='repo2') as m:
            pass

        metrics = get_metrics(days=1)
        assert len(metrics) == 2

    def test_get_metrics_filtered_by_agent(self, temp_metrics_dir):
        """Test filtering metrics by agent."""
        with MetricsCollector(agent='engineer') as m:
            pass
        with MetricsCollector(agent='tech_lead') as m:
            pass

        metrics = get_metrics(days=1, agent='engineer')
        assert len(metrics) == 1
        assert metrics[0]['agent'] == 'engineer'

    def test_get_metrics_filtered_by_repo(self, temp_metrics_dir):
        """Test filtering metrics by repository."""
        with MetricsCollector(agent='engineer', repo_name='repo1') as m:
            pass
        with MetricsCollector(agent='engineer', repo_name='repo2') as m:
            pass

        metrics = get_metrics(days=1, repo_name='repo1')
        assert len(metrics) == 1
        assert metrics[0]['repo_name'] == 'repo1'

    def test_get_metrics_sorted_by_timestamp(self, temp_metrics_dir):
        """Test that metrics are sorted newest first."""
        with MetricsCollector(agent='test1') as m:
            pass
        time.sleep(0.01)
        with MetricsCollector(agent='test2') as m:
            pass

        metrics = get_metrics(days=1)
        assert len(metrics) == 2
        # Most recent should be first
        assert metrics[0]['agent'] == 'test2'
        assert metrics[1]['agent'] == 'test1'

    def test_get_metrics_summary_empty(self, temp_metrics_dir):
        """Test summary with no data."""
        summary = get_metrics_summary(days=7)
        assert summary['total_runs'] == 0
        assert summary['success_rate'] == 0

    def test_get_metrics_summary_with_data(self, temp_metrics_dir):
        """Test summary calculation."""
        # Add some metrics
        for i in range(5):
            collector = MetricsCollector(agent='engineer', repo_name='repo1')
            collector.start()
            collector.complete(
                success=(i < 4),  # 4 success, 1 failure
                output_text="Input tokens: 1000\nOutput tokens: 3000"
            )

        summary = get_metrics_summary(days=1)

        assert summary['total_runs'] == 5
        assert summary['successful_runs'] == 4
        assert summary['failed_runs'] == 1
        assert summary['success_rate'] == 80.0
        assert summary['total_tokens'] == 20000  # 5 * 4000
        assert 'by_agent' in summary
        assert 'engineer' in summary['by_agent']


class TestMetricsRotation:
    """Tests for metrics file rotation."""

    def test_rotate_empty_file(self, temp_metrics_dir):
        """Test rotation with no metrics file."""
        removed = rotate_metrics()
        assert removed == 0

    def test_rotate_no_old_entries(self, temp_metrics_dir):
        """Test rotation when all entries are recent."""
        with MetricsCollector(agent='test') as m:
            pass

        removed = rotate_metrics()
        assert removed == 0

        # Entry should still exist
        metrics = get_metrics(days=1)
        assert len(metrics) == 1

    def test_rotate_removes_old_entries(self, temp_metrics_dir):
        """Test that rotation removes old entries."""
        metrics_path = _get_metrics_path()

        # Manually add an old entry
        old_timestamp = (datetime.utcnow() - timedelta(days=METRICS_RETENTION_DAYS + 1)).isoformat() + 'Z'
        old_entry = {
            'timestamp': old_timestamp,
            'agent': 'old_test',
            'success': True,
        }

        # Write old entry directly
        with open(metrics_path, 'w') as f:
            f.write(json.dumps(old_entry) + '\n')

        # Add a recent entry
        with MetricsCollector(agent='recent_test') as m:
            pass

        # Rotate
        removed = rotate_metrics()
        assert removed == 1

        # Only recent entry should remain
        metrics = get_metrics(days=METRICS_RETENTION_DAYS + 5)
        assert len(metrics) == 1
        assert metrics[0]['agent'] == 'recent_test'


class TestMetricsPersistence:
    """Tests for metrics file persistence."""

    def test_metrics_persisted_to_file(self, temp_metrics_dir):
        """Test that metrics are written to disk."""
        with MetricsCollector(agent='test') as m:
            pass

        metrics_path = _get_metrics_path()
        assert metrics_path.exists()

        # Read and verify
        with open(metrics_path) as f:
            lines = f.readlines()
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry['agent'] == 'test'

    def test_multiple_metrics_appended(self, temp_metrics_dir):
        """Test that multiple metrics are appended correctly."""
        for i in range(3):
            with MetricsCollector(agent=f'test{i}') as m:
                pass

        metrics_path = _get_metrics_path()
        with open(metrics_path) as f:
            lines = f.readlines()
        assert len(lines) == 3

    def test_error_message_truncated(self, temp_metrics_dir):
        """Test that long error messages are truncated."""
        long_message = "x" * 1000
        collector = MetricsCollector(agent='test')
        collector.start()
        metric = collector.complete(
            success=False,
            error_message=long_message
        )

        assert len(metric['error_message']) <= 500


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
