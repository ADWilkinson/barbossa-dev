#!/usr/bin/env python3
"""
Barbossa Failure Analyzer - Systematic Failure Analysis System

Records and analyzes PR failures to help prevent repeated mistakes.
Provides context to Engineers about past failures before starting new issues.
Surfaces failure patterns to Auditor for health reports.

Design Principles:
- JSONL format for append-only writes (crash-safe)
- 90-day retention policy to prevent unbounded growth
- Thread-safe file operations
- Graceful degradation (never blocks agent execution)

Configuration in repositories.json:
{
  "settings": {
    "failure_analyzer": {
      "enabled": true,
      "retention_days": 90,
      "backoff_policy": {
        "skip_runs_after_failures": 1,
        "consecutive_failures_threshold": 2
      }
    }
  }
}
"""

import json
import logging
import os
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Current version
VERSION = "1.8.3"

logger = logging.getLogger('barbossa.failure_analyzer')

# File lock for thread-safe writes
_file_lock = threading.Lock()


@dataclass
class FailureRecord:
    """Structured failure record."""
    issue_id: str                # Issue identifier (e.g., "#42" or "MUS-123")
    repository: str              # Repository name
    pr_number: int               # PR number that failed
    pr_url: str                  # URL to the PR
    category: str                # Failure category (see FAILURE_CATEGORIES)
    root_cause: str              # Human-readable root cause
    evidence: str                # Evidence supporting the failure reason
    tech_lead_reasoning: str     # Original Tech Lead reasoning
    timestamp: str               # ISO format timestamp
    attempt_number: int = 1      # Which attempt this was (1, 2, 3...)
    issue_title: Optional[str] = None  # Issue title for matching
    issue_labels: List[str] = field(default_factory=list)  # Issue labels


# Standard failure categories for consistent classification
FAILURE_CATEGORIES = [
    'missing_tests',           # PR lacks required tests
    'test_only',               # PR only adds tests (low value)
    'missing_evidence',        # PR lacks evidence (issue link, repro, etc.)
    'ci_failures',             # Build/lint/test failures
    'lockfile_undisclosed',    # Lockfile changes not documented
    'major_upgrade_unjustified',  # Major version bump without justification
    'code_quality',            # Code quality issues (bloat, complexity, etc.)
    'scope_creep',             # PR does too much / off-topic
    'merge_conflicts',         # Unable to resolve conflicts
    'three_strikes',           # Failed 3 reviews, auto-closed
    'stale',                   # PR went stale, auto-closed
    'manual_close',            # Manually closed by Tech Lead
    'other',                   # Other reasons
]


class FailureAnalyzer:
    """
    Analyzes and records PR failures for pattern detection.

    Usage:
        # In Tech Lead - record a failure
        analyzer = FailureAnalyzer(work_dir)
        analyzer.record_failure(
            issue_id="#42",
            repository="my-repo",
            pr_number=123,
            pr_url="https://github.com/...",
            category="missing_tests",
            root_cause="No tests for new API endpoint",
            evidence="PR adds 50+ lines to api/users.py with no test file",
            tech_lead_reasoning="Original Tech Lead feedback..."
        )

        # In Engineer - check for similar failures
        warnings = analyzer.get_similar_failures(
            issue_title="Add user deletion endpoint",
            issue_labels=["backlog", "api"]
        )
        if warnings:
            print(f"Warning: Similar issues failed before: {warnings}")

        # In Auditor - get pattern analysis
        patterns = analyzer.analyze_failure_patterns(days=30)
        print(f"Top failure categories: {patterns['top_categories']}")
    """

    DEFAULT_RETENTION_DAYS = 90
    DEFAULT_BACKOFF_SKIP_RUNS = 1
    DEFAULT_BACKOFF_THRESHOLD = 2

    def __init__(self, work_dir: Optional[Path] = None):
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-dev'
        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.failures_file = self.logs_dir / 'failures.jsonl'
        self.config_file = self.work_dir / 'config' / 'repositories.json'

        # Ensure logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config()

        # Extract settings
        fa_settings = self.config.get('settings', {}).get('failure_analyzer', {})
        self.enabled = fa_settings.get('enabled', True)
        self.retention_days = fa_settings.get('retention_days', self.DEFAULT_RETENTION_DAYS)

        backoff = fa_settings.get('backoff_policy', {})
        self.backoff_skip_runs = backoff.get('skip_runs_after_failures', self.DEFAULT_BACKOFF_SKIP_RUNS)
        self.backoff_threshold = backoff.get('consecutive_failures_threshold', self.DEFAULT_BACKOFF_THRESHOLD)

    def _load_config(self) -> Dict:
        """Load repository configuration."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load config: {e}")
        return {}

    def record_failure(
        self,
        issue_id: str,
        repository: str,
        pr_number: int,
        pr_url: str,
        category: str,
        root_cause: str,
        evidence: str,
        tech_lead_reasoning: str,
        issue_title: Optional[str] = None,
        issue_labels: Optional[List[str]] = None,
    ) -> bool:
        """
        Record a failure to the failures log.

        Args:
            issue_id: Issue identifier (e.g., "#42" or "MUS-123")
            repository: Repository name
            pr_number: PR number
            pr_url: URL to the failed PR
            category: Failure category (from FAILURE_CATEGORIES)
            root_cause: Brief description of why it failed
            evidence: Specific evidence (file paths, test output, etc.)
            tech_lead_reasoning: Original Tech Lead feedback
            issue_title: Issue title (for future matching)
            issue_labels: Issue labels (for future matching)

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Failure analyzer disabled, skipping record")
            return False

        # Validate category
        if category not in FAILURE_CATEGORIES:
            logger.warning(f"Unknown failure category '{category}', using 'other'")
            category = 'other'

        # Determine attempt number by counting previous failures for this issue
        attempt_number = self._get_attempt_number(issue_id, repository)

        record = FailureRecord(
            issue_id=issue_id,
            repository=repository,
            pr_number=pr_number,
            pr_url=pr_url,
            category=category,
            root_cause=root_cause[:500],  # Truncate to prevent huge entries
            evidence=evidence[:1000],
            tech_lead_reasoning=tech_lead_reasoning[:1000],
            timestamp=datetime.utcnow().isoformat() + 'Z',
            attempt_number=attempt_number,
            issue_title=issue_title,
            issue_labels=issue_labels or [],
        )

        try:
            with _file_lock:
                with open(self.failures_file, 'a') as f:
                    f.write(json.dumps(asdict(record)) + '\n')

            logger.info(f"Recorded failure: {repository} #{pr_number} - {category} (attempt {attempt_number})")
            return True

        except IOError as e:
            logger.error(f"Failed to record failure: {e}")
            return False

    def _get_attempt_number(self, issue_id: str, repository: str) -> int:
        """Get the attempt number for this issue."""
        failures = self._load_failures()
        count = sum(
            1 for f in failures
            if f.get('issue_id') == issue_id and f.get('repository') == repository
        )
        return count + 1

    def _load_failures(self, days: Optional[int] = None) -> List[Dict]:
        """
        Load failure records from the JSONL file.

        Args:
            days: If provided, only return records from the last N days

        Returns:
            List of failure records as dicts
        """
        records = []

        if not self.failures_file.exists():
            return records

        cutoff = None
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)

        try:
            with _file_lock:
                with open(self.failures_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)

                            # Apply time filter if specified
                            if cutoff:
                                ts_str = record.get('timestamp', '')
                                try:
                                    ts = datetime.fromisoformat(ts_str.rstrip('Z'))
                                    if ts < cutoff:
                                        continue
                                except (ValueError, TypeError):
                                    continue  # Skip records with invalid timestamps

                            records.append(record)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping malformed line in failures.jsonl")

        except IOError as e:
            logger.error(f"Failed to load failures: {e}")

        return records

    def get_similar_failures(
        self,
        issue_title: Optional[str] = None,
        issue_labels: Optional[List[str]] = None,
        repository: Optional[str] = None,
        days: int = 30,
    ) -> List[Dict]:
        """
        Find similar past failures based on title keywords and labels.

        This is called by Engineer before starting work on an issue
        to warn about similar issues that failed before.

        Args:
            issue_title: Title of the issue being worked on
            issue_labels: Labels on the issue
            repository: Repository name (if specified, filter to this repo)
            days: Look back period in days

        Returns:
            List of similar failure records with relevance info
        """
        failures = self._load_failures(days=days)

        if not failures:
            return []

        # Filter by repository if specified
        if repository:
            failures = [f for f in failures if f.get('repository') == repository]

        if not issue_title and not issue_labels:
            return []

        similar = []

        # Extract keywords from title (words > 3 chars, excluding common words)
        stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'will', 'when', 'where'}
        keywords = []
        if issue_title:
            keywords = [
                w.lower() for w in issue_title.split()
                if len(w) > 3 and w.lower() not in stop_words
            ]

        for failure in failures:
            relevance_score = 0
            match_reasons = []

            # Check title keyword overlap
            failure_title = failure.get('issue_title', '') or ''
            if keywords and failure_title:
                failure_words = set(w.lower() for w in failure_title.split() if len(w) > 3)
                matches = set(keywords) & failure_words
                if matches:
                    relevance_score += len(matches) * 2
                    match_reasons.append(f"keywords: {', '.join(matches)}")

            # Check label overlap
            failure_labels = set(failure.get('issue_labels', []))
            if issue_labels:
                label_matches = set(issue_labels) & failure_labels
                if label_matches:
                    relevance_score += len(label_matches)
                    match_reasons.append(f"labels: {', '.join(label_matches)}")

            # Check category patterns (some categories indicate systemic issues)
            category = failure.get('category', '')
            if category in ['missing_tests', 'missing_evidence', 'scope_creep']:
                relevance_score += 1  # These are common patterns worth noting

            if relevance_score > 0:
                similar.append({
                    'failure': failure,
                    'relevance_score': relevance_score,
                    'match_reasons': match_reasons,
                })

        # Sort by relevance (most relevant first)
        similar.sort(key=lambda x: x['relevance_score'], reverse=True)

        return similar[:5]  # Return top 5 matches

    def get_failure_warnings(
        self,
        issue_title: Optional[str] = None,
        issue_labels: Optional[List[str]] = None,
        repository: Optional[str] = None,
    ) -> str:
        """
        Get a formatted warning message about similar past failures.

        This is designed to be included in Engineer prompts to provide
        context about what went wrong before.

        Returns:
            Formatted warning string or empty string if no warnings
        """
        similar = self.get_similar_failures(issue_title, issue_labels, repository)

        if not similar:
            return ""

        lines = ["⚠️ WARNING: Similar issues have failed before:\n"]

        for i, match in enumerate(similar, 1):
            failure = match['failure']
            reasons = match['match_reasons']

            lines.append(f"{i}. {failure.get('issue_title', 'Unknown issue')} (PR #{failure.get('pr_number', '?')})")
            lines.append(f"   Category: {failure.get('category', 'unknown')}")
            lines.append(f"   Root cause: {failure.get('root_cause', 'Unknown')}")
            lines.append(f"   Matched on: {', '.join(reasons)}")
            lines.append("")

        lines.append("Learn from these failures and ensure your implementation addresses these concerns.")

        return '\n'.join(lines)

    def should_skip_issue(
        self,
        issue_id: str,
        repository: str,
    ) -> tuple[bool, str]:
        """
        Check if an issue should be skipped due to backoff policy.

        Args:
            issue_id: Issue identifier
            repository: Repository name

        Returns:
            Tuple of (should_skip: bool, reason: str)
        """
        failures = self._load_failures(days=self.retention_days)

        # Get failures for this specific issue
        issue_failures = [
            f for f in failures
            if f.get('issue_id') == issue_id and f.get('repository') == repository
        ]

        if len(issue_failures) < self.backoff_threshold:
            return False, ""

        # Check if we're still in backoff period
        # We skip N runs after M consecutive failures
        latest_failure = max(issue_failures, key=lambda x: x.get('timestamp', ''))
        latest_ts_str = latest_failure.get('timestamp', '')

        try:
            latest_ts = datetime.fromisoformat(latest_ts_str.rstrip('Z'))
        except (ValueError, TypeError):
            return False, ""

        # Calculate backoff period based on number of failures
        # Each consecutive failure doubles the backoff period
        failure_count = len(issue_failures)
        backoff_hours = self.backoff_skip_runs * 2 * (2 ** (failure_count - self.backoff_threshold))
        backoff_hours = min(backoff_hours, 168)  # Cap at 1 week

        backoff_until = latest_ts + timedelta(hours=backoff_hours)

        if datetime.utcnow() < backoff_until:
            remaining = backoff_until - datetime.utcnow()
            reason = (
                f"Issue {issue_id} has failed {failure_count} times. "
                f"Backoff active for {remaining.total_seconds() / 3600:.1f} more hours. "
                f"Last failure: {latest_failure.get('category', 'unknown')}"
            )
            return True, reason

        return False, ""

    def analyze_failure_patterns(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze failure patterns for reporting.

        This is called by Auditor to surface failure patterns in health reports.

        Args:
            days: Analysis period in days

        Returns:
            Dict with pattern analysis including:
            - total_failures: Total count
            - top_categories: Top 3 failure categories with counts
            - by_repository: Failures grouped by repository
            - recurring_issues: Issues that failed multiple times
            - failure_rate_by_label: Failure rate by issue label
        """
        failures = self._load_failures(days=days)

        if not failures:
            return {
                'total_failures': 0,
                'top_categories': [],
                'by_repository': {},
                'recurring_issues': [],
                'failure_rate_by_label': {},
            }

        # Count by category
        category_counts = defaultdict(int)
        for f in failures:
            category_counts[f.get('category', 'other')] += 1

        top_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Group by repository
        by_repository = defaultdict(list)
        for f in failures:
            repo = f.get('repository', 'unknown')
            by_repository[repo].append(f)

        repo_summary = {
            repo: {
                'count': len(failures_list),
                'categories': dict(defaultdict(int, {
                    f.get('category', 'other'): 1
                    for f in failures_list
                }))
            }
            for repo, failures_list in by_repository.items()
        }

        # Find recurring issues (failed 2+ times)
        issue_counts = defaultdict(list)
        for f in failures:
            key = (f.get('issue_id', ''), f.get('repository', ''))
            issue_counts[key].append(f)

        recurring = [
            {
                'issue_id': key[0],
                'repository': key[1],
                'failure_count': len(failures_list),
                'categories': list(set(f.get('category', 'other') for f in failures_list)),
                'last_failure': max(f.get('timestamp', '') for f in failures_list),
            }
            for key, failures_list in issue_counts.items()
            if len(failures_list) >= 2
        ]
        recurring.sort(key=lambda x: x['failure_count'], reverse=True)

        # Analyze by label
        label_counts = defaultdict(int)
        for f in failures:
            for label in f.get('issue_labels', []):
                label_counts[label] += 1

        return {
            'total_failures': len(failures),
            'top_categories': [
                {'category': cat, 'count': count, 'percentage': round(count / len(failures) * 100, 1)}
                for cat, count in top_categories
            ],
            'by_repository': repo_summary,
            'recurring_issues': recurring[:10],  # Top 10 recurring
            'failure_rate_by_label': dict(sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def get_failure_insights_for_notification(self, repository: str, category: str) -> str:
        """
        Get failure insights to include in Discord notifications.

        Args:
            repository: Repository name
            category: Failure category

        Returns:
            Insight string or empty if no pattern detected
        """
        failures = self._load_failures(days=7)

        if not failures:
            return ""

        # Count recent failures in this category for this repo
        recent_count = sum(
            1 for f in failures
            if f.get('repository') == repository and f.get('category') == category
        )

        if recent_count >= 3:
            return f"⚠️ This is the {recent_count}th {category.replace('_', ' ')} failure this week"

        # Check for overall failure rate
        repo_failures = [f for f in failures if f.get('repository') == repository]
        if len(repo_failures) >= 5:
            return f"📊 {len(repo_failures)} PR failures in {repository} this week"

        return ""

    def rotate_failures(self) -> int:
        """
        Remove failure records older than retention period.

        Returns:
            Number of records removed
        """
        if not self.failures_file.exists():
            return 0

        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        kept = []
        removed = 0

        try:
            with _file_lock:
                # Read all records
                with open(self.failures_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            ts_str = record.get('timestamp', '')
                            ts = datetime.fromisoformat(ts_str.rstrip('Z'))

                            if ts >= cutoff:
                                kept.append(line)
                            else:
                                removed += 1
                        except (json.JSONDecodeError, ValueError):
                            kept.append(line)  # Keep malformed records

                # Rewrite file with only kept records
                if removed > 0:
                    with open(self.failures_file, 'w') as f:
                        for line in kept:
                            f.write(line + '\n')

                    logger.info(f"Rotated failures.jsonl: removed {removed} old records")

        except IOError as e:
            logger.error(f"Failed to rotate failures: {e}")

        return removed


def _infer_category_from_reasoning(reasoning: str) -> str:
    """
    Infer failure category from Tech Lead reasoning text.

    Used when category is not explicitly provided.
    """
    reasoning_lower = reasoning.lower()

    if 'test-only' in reasoning_lower or 'only test' in reasoning_lower:
        return 'test_only'
    if 'missing test' in reasoning_lower or 'no test' in reasoning_lower:
        return 'missing_tests'
    if 'evidence' in reasoning_lower or 'no issue' in reasoning_lower:
        return 'missing_evidence'
    if 'ci' in reasoning_lower or 'build' in reasoning_lower or 'failing check' in reasoning_lower:
        return 'ci_failures'
    if 'lockfile' in reasoning_lower:
        return 'lockfile_undisclosed'
    if 'major' in reasoning_lower and 'upgrade' in reasoning_lower:
        return 'major_upgrade_unjustified'
    if 'quality' in reasoning_lower or 'bloat' in reasoning_lower:
        return 'code_quality'
    if 'scope' in reasoning_lower or 'too much' in reasoning_lower:
        return 'scope_creep'
    if 'conflict' in reasoning_lower:
        return 'merge_conflicts'
    if '3' in reasoning_lower and 'strike' in reasoning_lower:
        return 'three_strikes'
    if 'stale' in reasoning_lower:
        return 'stale'

    return 'other'


# Convenience function for agents
def get_failure_analyzer(work_dir: Optional[Path] = None) -> FailureAnalyzer:
    """Get a FailureAnalyzer instance."""
    return FailureAnalyzer(work_dir)
