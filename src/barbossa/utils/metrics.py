#!/usr/bin/env python3
"""
Barbossa Metrics - Execution Telemetry and Cost Tracking

Provides local execution metrics collection for agent runs:
- Runtime duration per agent/repo
- Token usage estimation from Claude CLI output
- Cost estimation based on Claude API pricing
- Success/failure tracking with error categorization

Metrics are stored in a JSONL file for time-series analysis.
Auto-rotates to keep 30 days of data.

Usage:
    from barbossa.utils.metrics import MetricsCollector

    # Start tracking
    metrics = MetricsCollector(agent='engineer', repo_name='my-repo')
    metrics.start()

    # ... run agent code ...

    # Complete tracking (extracts tokens from output if provided)
    metrics.complete(success=True, output_text=claude_output, pr_url=pr_url)

    # Or on failure
    metrics.complete(success=False, error_type='timeout', error_message='Claude timed out')
"""

import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Current version
VERSION = "2.1.0"

# Claude API pricing (per 1M tokens) as of January 2025
# Source: https://www.anthropic.com/pricing
CLAUDE_PRICING = {
    'opus': {
        'input': 15.00,   # $15 per 1M input tokens
        'output': 75.00,  # $75 per 1M output tokens
    },
    'sonnet': {
        'input': 3.00,    # $3 per 1M input tokens
        'output': 15.00,  # $15 per 1M output tokens
    },
    'haiku': {
        'input': 0.25,    # $0.25 per 1M input tokens
        'output': 1.25,   # $1.25 per 1M output tokens
    },
}

# Default to opus pricing (most commonly used)
DEFAULT_MODEL = 'opus'

# Metrics file configuration
METRICS_FILENAME = 'metrics.jsonl'
METRICS_RETENTION_DAYS = 30

logger = logging.getLogger('barbossa.metrics')

# Thread lock for file operations
_file_lock = threading.Lock()


def _get_metrics_path() -> Path:
    """Get the path to the metrics file."""
    data_dir = Path(os.environ.get('BARBOSSA_DIR', '/app')) / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / METRICS_FILENAME


def _rotate_metrics_file() -> int:
    """
    Rotate metrics file by removing entries older than METRICS_RETENTION_DAYS.

    Returns:
        Number of entries removed
    """
    metrics_path = _get_metrics_path()
    if not metrics_path.exists():
        return 0

    cutoff = datetime.utcnow() - timedelta(days=METRICS_RETENTION_DAYS)
    cutoff_iso = cutoff.isoformat() + 'Z'

    removed_count = 0
    kept_entries = []

    try:
        with _file_lock:
            with open(metrics_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        timestamp = entry.get('timestamp', '')
                        # Keep entries newer than cutoff
                        if timestamp >= cutoff_iso:
                            kept_entries.append(line)
                        else:
                            removed_count += 1
                    except json.JSONDecodeError:
                        # Keep malformed entries to avoid data loss
                        kept_entries.append(line)

            # Write back only if we removed entries
            if removed_count > 0:
                temp_path = metrics_path.with_suffix('.tmp')
                with open(temp_path, 'w') as f:
                    for entry in kept_entries:
                        f.write(entry + '\n')
                temp_path.replace(metrics_path)
                logger.info(f"Rotated metrics file: removed {removed_count} old entries")

    except IOError as e:
        logger.warning(f"Failed to rotate metrics file: {e}")

    return removed_count


def _append_metric(metric: Dict) -> bool:
    """
    Append a metric entry to the metrics file.

    Args:
        metric: Dictionary containing metric data

    Returns:
        True if successful, False otherwise
    """
    metrics_path = _get_metrics_path()

    try:
        with _file_lock:
            with open(metrics_path, 'a') as f:
                f.write(json.dumps(metric) + '\n')
        return True
    except IOError as e:
        logger.warning(f"Failed to append metric: {e}")
        return False


def _extract_token_usage(output_text: str) -> Dict[str, int]:
    """
    Extract token usage from Claude CLI output.

    Claude CLI outputs usage info like:
    "Input tokens: 1234"
    "Output tokens: 5678"

    Args:
        output_text: The full output from Claude CLI

    Returns:
        Dict with 'input_tokens' and 'output_tokens' keys
    """
    result = {'input_tokens': 0, 'output_tokens': 0}

    if not output_text:
        return result

    # Look for token usage patterns in Claude CLI output
    # Pattern 1: "Input tokens: 1234" style
    input_match = re.search(r'input\s+tokens?[:\s]+(\d+)', output_text, re.IGNORECASE)
    if input_match:
        result['input_tokens'] = int(input_match.group(1))

    output_match = re.search(r'output\s+tokens?[:\s]+(\d+)', output_text, re.IGNORECASE)
    if output_match:
        result['output_tokens'] = int(output_match.group(1))

    # Pattern 2: "tokens: input=1234, output=5678" style
    if result['input_tokens'] == 0 and result['output_tokens'] == 0:
        combined_match = re.search(
            r'tokens?[:\s]+input\s*=\s*(\d+)\s*,?\s*output\s*=\s*(\d+)',
            output_text,
            re.IGNORECASE
        )
        if combined_match:
            result['input_tokens'] = int(combined_match.group(1))
            result['output_tokens'] = int(combined_match.group(2))

    # Pattern 3: Total tokens only (estimate 1:3 input:output ratio for agents)
    if result['input_tokens'] == 0 and result['output_tokens'] == 0:
        total_match = re.search(r'[Tt]otal\s+tokens?[:\s]+(\d+)', output_text)
        if total_match:
            total = int(total_match.group(1))
            # Typical agent ratio: ~25% input, ~75% output
            result['input_tokens'] = int(total * 0.25)
            result['output_tokens'] = int(total * 0.75)

    return result


def _calculate_cost(tokens: Dict[str, int], model: str = DEFAULT_MODEL) -> float:
    """
    Calculate estimated cost based on token usage.

    Args:
        tokens: Dict with 'input_tokens' and 'output_tokens'
        model: Model name (opus, sonnet, haiku)

    Returns:
        Estimated cost in USD
    """
    pricing = CLAUDE_PRICING.get(model.lower(), CLAUDE_PRICING[DEFAULT_MODEL])

    input_cost = (tokens.get('input_tokens', 0) / 1_000_000) * pricing['input']
    output_cost = (tokens.get('output_tokens', 0) / 1_000_000) * pricing['output']

    return round(input_cost + output_cost, 4)


class MetricsCollector:
    """
    Collects execution metrics for a single agent run.

    Usage:
        metrics = MetricsCollector(agent='engineer', repo_name='my-repo')
        metrics.start()
        # ... run agent ...
        metrics.complete(success=True, output_text=output)
    """

    def __init__(
        self,
        agent: str,
        repo_name: Optional[str] = None,
        session_id: Optional[str] = None,
        model: str = DEFAULT_MODEL
    ):
        """
        Initialize metrics collector.

        Args:
            agent: Agent type (engineer, tech_lead, discovery, etc.)
            repo_name: Repository name being processed (optional)
            session_id: Unique session identifier (optional)
            model: Claude model being used (opus, sonnet, haiku)
        """
        self.agent = agent
        self.repo_name = repo_name
        self.session_id = session_id
        self.model = model

        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._completed = False

    def start(self) -> 'MetricsCollector':
        """
        Start timing the execution.

        Returns:
            Self for chaining
        """
        self._start_time = datetime.utcnow()
        return self

    def complete(
        self,
        success: bool,
        output_text: Optional[str] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        pr_url: Optional[str] = None,
        pr_number: Optional[int] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Complete the metrics collection and save to file.

        Args:
            success: Whether the run was successful
            output_text: Claude CLI output (for token extraction)
            error_type: Type of error (timeout, api_error, parse_error, etc.)
            error_message: Error message if failed
            pr_url: URL of PR created (if any)
            pr_number: PR number (if any)
            custom_data: Additional custom metrics to include

        Returns:
            The complete metric entry
        """
        if self._completed:
            logger.warning("MetricsCollector.complete() called multiple times")
            return {}

        self._completed = True
        self._end_time = datetime.utcnow()

        # Calculate duration
        if self._start_time:
            duration_seconds = (self._end_time - self._start_time).total_seconds()
        else:
            duration_seconds = 0
            logger.warning("MetricsCollector.complete() called without start()")

        # Extract tokens from output
        tokens = _extract_token_usage(output_text or '')

        # Calculate cost
        cost = _calculate_cost(tokens, self.model)

        # Build metric entry
        metric = {
            'timestamp': self._end_time.isoformat() + 'Z',
            'agent': self.agent,
            'repo_name': self.repo_name,
            'session_id': self.session_id,
            'model': self.model,
            'duration_seconds': round(duration_seconds, 2),
            'success': success,
            'input_tokens': tokens['input_tokens'],
            'output_tokens': tokens['output_tokens'],
            'total_tokens': tokens['input_tokens'] + tokens['output_tokens'],
            'cost_usd': cost,
        }

        # Add optional fields
        if error_type:
            metric['error_type'] = error_type
        if error_message:
            metric['error_message'] = error_message[:500]  # Truncate long messages
        if pr_url:
            metric['pr_url'] = pr_url
        if pr_number:
            metric['pr_number'] = pr_number
        if custom_data:
            metric['custom'] = custom_data

        # Save to file
        _append_metric(metric)

        return metric

    def __enter__(self) -> 'MetricsCollector':
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - auto-complete on exception."""
        if not self._completed:
            if exc_type is not None:
                self.complete(
                    success=False,
                    error_type=exc_type.__name__ if exc_type else 'unknown',
                    error_message=str(exc_val) if exc_val else None
                )
            else:
                self.complete(success=True)


def get_metrics(
    days: int = 7,
    agent: Optional[str] = None,
    repo_name: Optional[str] = None
) -> List[Dict]:
    """
    Load metrics from file, optionally filtered.

    Args:
        days: Number of days to include (default 7)
        agent: Filter by agent type
        repo_name: Filter by repository name

    Returns:
        List of metric entries (newest first)
    """
    metrics_path = _get_metrics_path()
    if not metrics_path.exists():
        return []

    cutoff = datetime.utcnow() - timedelta(days=days)
    cutoff_iso = cutoff.isoformat() + 'Z'

    results = []

    try:
        with open(metrics_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)

                    # Apply time filter
                    if entry.get('timestamp', '') < cutoff_iso:
                        continue

                    # Apply agent filter
                    if agent and entry.get('agent') != agent:
                        continue

                    # Apply repo filter
                    if repo_name and entry.get('repo_name') != repo_name:
                        continue

                    results.append(entry)
                except json.JSONDecodeError:
                    continue

    except IOError as e:
        logger.warning(f"Failed to load metrics: {e}")

    # Sort by timestamp descending (newest first)
    results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    return results


def get_metrics_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get aggregated metrics summary.

    Args:
        days: Number of days to include

    Returns:
        Summary dictionary with totals and averages
    """
    metrics = get_metrics(days=days)

    if not metrics:
        return {
            'period_days': days,
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'success_rate': 0,
            'total_cost_usd': 0,
            'total_tokens': 0,
            'avg_duration_seconds': 0,
            'by_agent': {},
            'by_repo': {},
            'error_breakdown': {},
        }

    # Calculate totals
    total_runs = len(metrics)
    successful_runs = sum(1 for m in metrics if m.get('success'))
    failed_runs = total_runs - successful_runs
    total_cost = sum(m.get('cost_usd', 0) for m in metrics)
    total_tokens = sum(m.get('total_tokens', 0) for m in metrics)
    total_duration = sum(m.get('duration_seconds', 0) for m in metrics)

    # Group by agent
    by_agent: Dict[str, Dict] = {}
    for m in metrics:
        agent = m.get('agent', 'unknown')
        if agent not in by_agent:
            by_agent[agent] = {
                'runs': 0,
                'successes': 0,
                'cost_usd': 0,
                'tokens': 0,
                'duration_seconds': 0,
            }
        by_agent[agent]['runs'] += 1
        if m.get('success'):
            by_agent[agent]['successes'] += 1
        by_agent[agent]['cost_usd'] += m.get('cost_usd', 0)
        by_agent[agent]['tokens'] += m.get('total_tokens', 0)
        by_agent[agent]['duration_seconds'] += m.get('duration_seconds', 0)

    # Group by repo
    by_repo: Dict[str, Dict] = {}
    for m in metrics:
        repo = m.get('repo_name') or 'unknown'
        if repo not in by_repo:
            by_repo[repo] = {
                'runs': 0,
                'successes': 0,
                'failures': 0,
                'cost_usd': 0,
            }
        by_repo[repo]['runs'] += 1
        if m.get('success'):
            by_repo[repo]['successes'] += 1
        else:
            by_repo[repo]['failures'] += 1
        by_repo[repo]['cost_usd'] += m.get('cost_usd', 0)

    # Error breakdown
    error_breakdown: Dict[str, int] = {}
    for m in metrics:
        if not m.get('success') and m.get('error_type'):
            error_type = m['error_type']
            error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1

    return {
        'period_days': days,
        'total_runs': total_runs,
        'successful_runs': successful_runs,
        'failed_runs': failed_runs,
        'success_rate': round(successful_runs / total_runs * 100, 1) if total_runs > 0 else 0,
        'total_cost_usd': round(total_cost, 2),
        'total_tokens': total_tokens,
        'avg_duration_seconds': round(total_duration / total_runs, 1) if total_runs > 0 else 0,
        'avg_cost_per_run': round(total_cost / total_runs, 4) if total_runs > 0 else 0,
        'by_agent': by_agent,
        'by_repo': by_repo,
        'error_breakdown': error_breakdown,
    }


def rotate_metrics() -> int:
    """
    Rotate the metrics file, removing entries older than retention period.

    Returns:
        Number of entries removed
    """
    return _rotate_metrics_file()


# CLI for testing
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    print(f"Barbossa Metrics v{VERSION}")
    print("=" * 40)

    metrics_path = _get_metrics_path()
    print(f"Metrics file: {metrics_path}")
    print(f"File exists: {metrics_path.exists()}")

    if len(sys.argv) > 1:
        if sys.argv[1] == 'summary':
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            print(f"\nMetrics Summary (last {days} days):")
            print("-" * 40)
            summary = get_metrics_summary(days)
            print(json.dumps(summary, indent=2))

        elif sys.argv[1] == 'rotate':
            print("\nRotating metrics file...")
            removed = rotate_metrics()
            print(f"Removed {removed} old entries")

        elif sys.argv[1] == 'test':
            print("\nRunning test metric collection...")
            with MetricsCollector(agent='test', repo_name='test-repo') as m:
                import time
                time.sleep(0.1)  # Simulate work

            print("Test metric saved successfully")
            recent = get_metrics(days=1)
            if recent:
                print(f"Latest metric: {json.dumps(recent[0], indent=2)}")
    else:
        print("\nUsage:")
        print("  python -m barbossa.utils.metrics summary [days]")
        print("  python -m barbossa.utils.metrics rotate")
        print("  python -m barbossa.utils.metrics test")
