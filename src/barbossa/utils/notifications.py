#!/usr/bin/env python3
"""
Barbossa Notifications - Webhook Notification System

Provides real-time insights into Barbossa's operations via webhooks.
Currently supports Discord, designed for future extensibility (Slack, Teams, etc.)

Design Principles:
- NEVER blocks agent execution - all notifications are fire-and-forget
- Graceful degradation - if webhook fails, everything still works
- Not spammy - only insightful notifications about meaningful events
- Rich formatting - Discord embeds for clear, visual messages

Configuration in repositories.json:
{
  "settings": {
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/...",
      "notify_on": {
        "run_complete": true,
        "pr_created": true,
        "pr_merged": true,
        "error": true
      }
    }
  }
}
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Current version
VERSION = "2.1.0"

# Timeout for webhook calls (short - we never want to block)
WEBHOOK_TIMEOUT = 10

logger = logging.getLogger('barbossa.notifications')

# Global configuration state
_config: Optional[Dict] = None
_config_loaded = False

# Track pending notification threads so we can wait for them before process exit
_pending_threads: List[threading.Thread] = []
_threads_lock = threading.Lock()

# =============================================================================
# RETRY QUEUE IMPLEMENTATION
# =============================================================================
# Failed webhooks are queued for retry with exponential backoff.
# Queue is persisted to disk so retries survive process restarts.

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 60  # 1 minute base delay
MAX_RETENTION_HOURS = 24  # Drop queued items after 24 hours

# Queue state
_retry_queue_path: Optional[Path] = None
_retry_queue_lock = threading.Lock()


def _get_retry_queue_path() -> Path:
    """Get the path to the retry queue file."""
    global _retry_queue_path
    if _retry_queue_path is not None:
        return _retry_queue_path

    # Use same config directory as repositories.json
    data_dir = Path(os.environ.get('BARBOSSA_DIR', '/app')) / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    _retry_queue_path = data_dir / 'webhook_retry_queue.json'
    return _retry_queue_path


def _load_retry_queue() -> List[Dict]:
    """Load the retry queue from disk."""
    queue_path = _get_retry_queue_path()
    if not queue_path.exists():
        return []

    try:
        with open(queue_path, 'r') as f:
            queue = json.load(f)
            if not isinstance(queue, list):
                logger.warning("Invalid retry queue format, resetting")
                return []
            return queue
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load retry queue: {e}")
        return []


def _save_retry_queue(queue: List[Dict]) -> bool:
    """Save the retry queue to disk."""
    queue_path = _get_retry_queue_path()
    try:
        # Atomic write using temp file
        temp_path = queue_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(queue, f, indent=2)
        temp_path.replace(queue_path)
        return True
    except IOError as e:
        logger.warning(f"Failed to save retry queue: {e}")
        return False


def _parse_iso_timestamp(value: str) -> Optional[datetime]:
    """Safely parse an ISO timestamp string, returning None on failure.

    Handles timestamps with or without trailing 'Z' suffix.
    """
    if not value or not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value.rstrip('Z'))
    except (ValueError, AttributeError):
        return None


def _queue_for_retry(payload: Dict, attempt: int = 1) -> bool:
    """
    Add a failed webhook payload to the retry queue.

    Args:
        payload: The webhook payload that failed
        attempt: Current attempt number (1 = first failure)

    Returns:
        True if queued successfully
    """
    if attempt > MAX_RETRIES:
        logger.warning(f"Webhook exhausted {MAX_RETRIES} retries, dropping")
        return False

    # Calculate next retry time with exponential backoff
    delay_seconds = BASE_DELAY_SECONDS * (2 ** (attempt - 1))
    next_retry = datetime.utcnow() + timedelta(seconds=delay_seconds)

    queue_entry = {
        'payload': payload,
        'attempt': attempt,
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'next_retry_at': next_retry.isoformat() + 'Z',
    }

    with _retry_queue_lock:
        queue = _load_retry_queue()
        queue.append(queue_entry)

        # Prune expired entries
        cutoff = datetime.utcnow() - timedelta(hours=MAX_RETENTION_HOURS)
        queue = [
            entry for entry in queue
            if datetime.fromisoformat(entry['created_at'].rstrip('Z')) > cutoff
        ]

        _save_retry_queue(queue)

    logger.info(f"Queued webhook for retry (attempt {attempt + 1}) in {delay_seconds}s")
    return True


def process_retry_queue() -> Dict[str, int]:
    """
    Process any pending webhook retries.

    This should be called at the start of agent runs to flush
    any webhooks that failed on previous runs.

    Returns:
        Dict with 'processed', 'succeeded', 'failed', 'requeued', 'malformed' counts
    """
    stats = {'processed': 0, 'succeeded': 0, 'failed': 0, 'requeued': 0, 'expired': 0, 'malformed': 0}

    with _retry_queue_lock:
        queue = _load_retry_queue()
        if not queue:
            return stats

        now = datetime.utcnow()
        remaining = []
        to_process = []

        # Separate items ready to retry from those still waiting
        for entry in queue:
            created_at = _parse_iso_timestamp(entry.get('created_at', ''))
            next_retry = _parse_iso_timestamp(entry.get('next_retry_at', ''))

            # Skip malformed entries with invalid timestamps
            if created_at is None or next_retry is None:
                stats['malformed'] += 1
                logger.warning(f"Skipping malformed retry queue entry: invalid timestamps")
                continue

            # Check if expired (older than MAX_RETENTION_HOURS)
            if created_at < now - timedelta(hours=MAX_RETENTION_HOURS):
                stats['expired'] += 1
                continue

            # Check if ready for retry
            if next_retry <= now:
                to_process.append(entry)
            else:
                remaining.append(entry)

        # Update queue immediately with items not being processed
        _save_retry_queue(remaining)

    # Process outside the lock to avoid blocking
    for entry in to_process:
        stats['processed'] += 1
        payload = entry['payload']
        attempt = entry['attempt']

        success = _send_discord_webhook_sync(payload)

        if success:
            stats['succeeded'] += 1
            logger.info(f"Retry succeeded on attempt {attempt + 1}")
        else:
            # Queue for another retry if attempts remain
            if attempt < MAX_RETRIES:
                _queue_for_retry(payload, attempt + 1)
                stats['requeued'] += 1
            else:
                stats['failed'] += 1
                logger.warning(f"Webhook failed after {MAX_RETRIES + 1} attempts")

    if stats['processed'] > 0 or stats['malformed'] > 0:
        logger.info(
            f"Retry queue: {stats['processed']} processed, "
            f"{stats['succeeded']} succeeded, {stats['requeued']} requeued, "
            f"{stats['failed']} failed, {stats['expired']} expired, "
            f"{stats['malformed']} malformed"
        )

    return stats


def get_retry_queue_status() -> Dict[str, Any]:
    """
    Get the current status of the retry queue.

    Returns:
        Dict with queue size, oldest entry age, next retry time, malformed count, etc.
    """
    with _retry_queue_lock:
        queue = _load_retry_queue()

    if not queue:
        return {'size': 0, 'oldest_age_minutes': 0, 'next_retry_in_seconds': None, 'malformed': 0}

    now = datetime.utcnow()
    ages = []
    next_retries = []
    malformed_count = 0

    for entry in queue:
        created_at = _parse_iso_timestamp(entry.get('created_at', ''))
        next_retry = _parse_iso_timestamp(entry.get('next_retry_at', ''))

        # Skip malformed entries
        if created_at is None or next_retry is None:
            malformed_count += 1
            continue

        ages.append((now - created_at).total_seconds() / 60)
        if next_retry > now:
            next_retries.append((next_retry - now).total_seconds())

    return {
        'size': len(queue),
        'oldest_age_minutes': max(ages) if ages else 0,
        'next_retry_in_seconds': min(next_retries) if next_retries else None,
        'malformed': malformed_count,
    }


def _load_notification_config() -> Dict:
    """Load notification configuration from repositories.json."""
    global _config, _config_loaded

    if _config_loaded:
        return _config or {}

    config_paths = [
        Path(os.environ.get('BARBOSSA_DIR', '/app')) / 'config' / 'repositories.json',
        Path.home() / 'barbossa-dev' / 'config' / 'repositories.json',
        Path.cwd() / 'config' / 'repositories.json',  # Also check current directory
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    full_config = json.load(f)
                    _config = full_config.get('settings', {}).get('notifications', {})
                    _config_loaded = True
                    return _config
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Failed to load config from {config_path}: {e}")

    _config_loaded = True
    _config = {}
    return {}


def _is_enabled() -> bool:
    """Check if notifications are enabled."""
    config = _load_notification_config()
    return config.get('enabled', False)


def _should_notify(event_type: str) -> bool:
    """Check if we should send notifications for this event type."""
    if not _is_enabled():
        return False

    config = _load_notification_config()
    notify_on = config.get('notify_on', {})

    # Default events that are always on unless explicitly disabled
    defaults = {
        'run_complete': True,
        'pr_created': True,
        'pr_merged': True,
        'pr_closed': False,  # Less important, off by default
        'error': True,
    }

    return notify_on.get(event_type, defaults.get(event_type, False))


def _get_discord_webhook() -> Optional[str]:
    """Get the Discord webhook URL from config."""
    config = _load_notification_config()
    return config.get('discord_webhook')


def _fire_and_forget(func):
    """Decorator to run function in background thread. Never blocks.

    Threads are tracked so wait_for_pending() can ensure they complete
    before the main process exits.
    """
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        with _threads_lock:
            # Clean up completed threads
            _pending_threads[:] = [t for t in _pending_threads if t.is_alive()]
            _pending_threads.append(thread)
        thread.start()
    return wrapper


def wait_for_pending(timeout: float = 5.0, min_per_thread: float = 2.0):
    """Wait for all pending notification threads to complete.

    Call this at the end of agent runs to ensure notifications are sent
    before the process exits.

    Uses an adaptive timeout strategy: each thread gets at least min_per_thread
    seconds, and any time saved by threads completing quickly is redistributed
    to remaining threads. This prevents the issue where dividing total timeout
    evenly among many threads gives each too little time (e.g., 10 threads with
    5s total = 0.5s per thread, but webhooks may need 2-3s).

    Args:
        timeout: Maximum total seconds to wait (default 5s)
        min_per_thread: Minimum seconds to wait per thread (default 2s)
    """
    import time as time_module  # Avoid name conflict with datetime.time

    with _threads_lock:
        threads = list(_pending_threads)

    if not threads:
        return

    logger.debug(f"Waiting for {len(threads)} pending notification(s)...")

    start_time = time_module.monotonic()
    deadline = start_time + timeout

    for thread in threads:
        # Calculate remaining time until deadline
        remaining_time = deadline - time_module.monotonic()
        if remaining_time <= 0:
            break

        # Give thread at least min_per_thread seconds, but not more than remaining time
        thread_timeout = min(max(min_per_thread, remaining_time), remaining_time)
        thread.join(timeout=thread_timeout)

    # Clean up
    with _threads_lock:
        _pending_threads[:] = [t for t in _pending_threads if t.is_alive()]

    remaining = len(_pending_threads)
    if remaining > 0:
        logger.debug(f"{remaining} notification(s) did not complete in time")


# =============================================================================
# DISCORD WEBHOOK IMPLEMENTATION
# =============================================================================

# Color constants for Discord embeds (in decimal)
COLORS = {
    'success': 0x2ECC71,    # Green
    'warning': 0xF1C40F,    # Yellow
    'error': 0xE74C3C,      # Red
    'info': 0x3498DB,       # Blue
    'purple': 0x9B59B6,     # Purple (for Tech Lead)
    'orange': 0xE67E22,     # Orange (for Discovery)
    'pink': 0xE91E63,       # Pink (for Product Manager)
}

# Agent emoji and color mapping
AGENT_STYLES = {
    'engineer': {'emoji': '\U0001F527', 'color': COLORS['info'], 'name': 'Engineer'},
    'tech_lead': {'emoji': '\U0001F50D', 'color': COLORS['purple'], 'name': 'Tech Lead'},
    'discovery': {'emoji': '\U0001F50E', 'color': COLORS['orange'], 'name': 'Discovery'},
    'product': {'emoji': '\U0001F4A1', 'color': COLORS['pink'], 'name': 'Product Manager'},
    'auditor': {'emoji': '\U0001F4CA', 'color': COLORS['warning'], 'name': 'Auditor'},
    'spec_generator': {'emoji': '\U0001F4DC', 'color': COLORS['purple'], 'name': 'Spec Generator'},
}


def _send_discord_webhook_sync(payload: Dict) -> bool:
    """
    Send a payload to Discord webhook synchronously.

    NEVER raises exceptions - all errors are logged and swallowed.
    This ensures webhook issues never break agent execution.

    Returns:
        True if sent successfully, False otherwise
    """
    webhook_url = _get_discord_webhook()
    if not webhook_url:
        logger.debug("No Discord webhook configured - skipping notification")
        return False

    try:
        data = json.dumps(payload).encode('utf-8')
        request = Request(
            webhook_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': f'Barbossa/{VERSION}'
            },
            method='POST'
        )

        with urlopen(request, timeout=WEBHOOK_TIMEOUT) as response:
            if response.status in (200, 204):
                logger.debug("Discord notification sent successfully")
                return True
            else:
                logger.warning(f"Discord webhook returned status {response.status}")
                return False

    except HTTPError as e:
        logger.warning(f"Discord webhook HTTP error: {e.code} - {e.reason}")
        return False
    except URLError as e:
        logger.warning(f"Discord webhook URL error: {e.reason}")
        return False
    except Exception as e:
        logger.warning(f"Discord webhook error: {e}")
        return False


def _send_discord_webhook(payload: Dict, queue_on_failure: bool = True) -> bool:
    """
    Send a payload to Discord webhook, queueing for retry on failure.

    NEVER raises exceptions - all errors are logged and swallowed.
    This ensures webhook issues never break agent execution.

    Args:
        payload: The webhook payload to send
        queue_on_failure: If True, queue failed webhooks for retry

    Returns:
        True if sent successfully (or queued), False otherwise
    """
    success = _send_discord_webhook_sync(payload)

    if not success and queue_on_failure:
        # Queue for retry - return True since we've handled the failure
        _queue_for_retry(payload, attempt=1)
        return True  # Queued counts as handled

    return success


def _build_discord_embed(
    title: str,
    description: str = None,
    color: int = COLORS['info'],
    fields: List[Dict] = None,
    footer: str = None,
    url: str = None,
    thumbnail: str = None
) -> Dict:
    """Build a Discord embed object."""
    embed = {
        'title': title,
        'color': color,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }

    if description:
        embed['description'] = description[:4096]  # Discord limit

    if fields:
        embed['fields'] = fields[:25]  # Discord limit

    if footer:
        embed['footer'] = {'text': footer[:2048]}

    if url:
        embed['url'] = url

    if thumbnail:
        embed['thumbnail'] = {'url': thumbnail}

    return embed


# =============================================================================
# PUBLIC NOTIFICATION FUNCTIONS
# =============================================================================

@_fire_and_forget
def notify_agent_run_complete(
    agent: str,
    success: bool,
    summary: str,
    details: Dict = None,
    duration_seconds: int = None
):
    """
    Notify that an agent run has completed.

    Args:
        agent: Agent type (engineer, tech_lead, discovery, product, auditor)
        success: Whether the run was successful
        summary: Brief summary of what happened
        details: Optional dict with additional details
        duration_seconds: How long the run took
    """
    if not _should_notify('run_complete'):
        return

    style = AGENT_STYLES.get(agent, {'emoji': '\U0001F916', 'color': COLORS['info'], 'name': agent.title()})

    status_emoji = '\U00002705' if success else '\U0000274C'
    color = COLORS['success'] if success else COLORS['error']

    title = f"{style['emoji']} {style['name']} Run Complete {status_emoji}"

    fields = []

    if duration_seconds:
        mins, secs = divmod(duration_seconds, 60)
        duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"
        fields.append({'name': 'Duration', 'value': duration_str, 'inline': True})

    if details:
        for key, value in list(details.items())[:5]:  # Limit to 5 detail fields
            fields.append({
                'name': key.replace('_', ' ').title(),
                'value': str(value)[:1024],
                'inline': True
            })

    embed = _build_discord_embed(
        title=title,
        description=summary[:2000] if summary else None,
        color=color,
        fields=fields if fields else None,
        footer=f"Barbossa v{VERSION}"
    )

    _send_discord_webhook({'embeds': [embed]})


@_fire_and_forget
def notify_pr_created(
    repo_name: str,
    pr_number: int,
    pr_title: str,
    pr_url: str,
    description: str = None,
    issue_number: int = None
):
    """
    Notify that a PR was created.

    Args:
        repo_name: Repository name
        pr_number: PR number
        pr_title: PR title
        pr_url: URL to the PR
        description: Optional brief description
        issue_number: Optional linked issue number
    """
    if not _should_notify('pr_created'):
        return

    title = f"\U0001F4DD PR Created: #{pr_number}"

    fields = [
        {'name': 'Repository', 'value': repo_name, 'inline': True},
        {'name': 'Title', 'value': pr_title[:256], 'inline': False},
    ]

    if issue_number:
        fields.append({'name': 'Closes Issue', 'value': f"#{issue_number}", 'inline': True})

    embed = _build_discord_embed(
        title=title,
        description=description[:500] if description else None,
        color=COLORS['info'],
        fields=fields,
        url=pr_url,
        footer=f"Barbossa v{VERSION}"
    )

    _send_discord_webhook({'embeds': [embed]})


@_fire_and_forget
def notify_pr_merged(
    repo_name: str,
    pr_number: int,
    pr_title: str,
    pr_url: str,
    value_score: int = None,
    quality_score: int = None
):
    """
    Notify that a PR was merged.

    Args:
        repo_name: Repository name
        pr_number: PR number
        pr_title: PR title
        pr_url: URL to the PR
        value_score: Tech Lead's value score
        quality_score: Tech Lead's quality score
    """
    if not _should_notify('pr_merged'):
        return

    title = f"\U00002705 PR Merged: #{pr_number}"

    fields = [
        {'name': 'Repository', 'value': repo_name, 'inline': True},
        {'name': 'Title', 'value': pr_title[:256], 'inline': False},
    ]

    if value_score is not None and quality_score is not None:
        fields.append({
            'name': 'Scores',
            'value': f"Value: {value_score}/10 | Quality: {quality_score}/10",
            'inline': True
        })

    embed = _build_discord_embed(
        title=title,
        color=COLORS['success'],
        fields=fields,
        url=pr_url,
        footer=f"Barbossa v{VERSION}"
    )

    _send_discord_webhook({'embeds': [embed]})


@_fire_and_forget
def notify_pr_closed(
    repo_name: str,
    pr_number: int,
    pr_title: str,
    pr_url: str,
    reason: str = None
):
    """
    Notify that a PR was closed (not merged).

    Args:
        repo_name: Repository name
        pr_number: PR number
        pr_title: PR title
        pr_url: URL to the PR
        reason: Why it was closed
    """
    if not _should_notify('pr_closed'):
        return

    title = f"\U0001F6AB PR Closed: #{pr_number}"

    fields = [
        {'name': 'Repository', 'value': repo_name, 'inline': True},
        {'name': 'Title', 'value': pr_title[:256], 'inline': False},
    ]

    if reason:
        fields.append({'name': 'Reason', 'value': reason[:500], 'inline': False})

    embed = _build_discord_embed(
        title=title,
        description=reason[:500] if reason else None,
        color=COLORS['warning'],
        fields=fields,
        url=pr_url,
        footer=f"Barbossa v{VERSION}"
    )

    _send_discord_webhook({'embeds': [embed]})


@_fire_and_forget
def notify_error(
    agent: str,
    error_message: str,
    context: str = None,
    repo_name: str = None
):
    """
    Notify about an error during agent execution.

    Args:
        agent: Agent type that encountered the error
        error_message: The error message
        context: What was happening when the error occurred
        repo_name: Optional repository name
    """
    if not _should_notify('error'):
        return

    style = AGENT_STYLES.get(agent, {'emoji': '\U0001F916', 'color': COLORS['error'], 'name': agent.title()})

    title = f"\U0000274C Error: {style['name']}"

    fields = []

    if repo_name:
        fields.append({'name': 'Repository', 'value': repo_name, 'inline': True})

    if context:
        fields.append({'name': 'Context', 'value': context[:256], 'inline': False})

    fields.append({'name': 'Error', 'value': f"```\n{error_message[:1000]}\n```", 'inline': False})

    embed = _build_discord_embed(
        title=title,
        color=COLORS['error'],
        fields=fields,
        footer=f"Barbossa v{VERSION}"
    )

    _send_discord_webhook({'embeds': [embed]})


@_fire_and_forget
def notify_issue_created(
    repo_name: str,
    issue_title: str,
    issue_url: str,
    issue_type: str = 'backlog',
    created_by: str = 'discovery'
):
    """
    Notify that an issue was created.

    Args:
        repo_name: Repository name
        issue_title: Issue title
        issue_url: URL to the issue
        issue_type: Type of issue (backlog, feature, quality)
        created_by: Which agent created it
    """
    # Issues are less important - bundle with run_complete instead
    # This is here for future use but not actively sent
    pass


@_fire_and_forget
def notify_tech_lead_decision(
    repo_name: str,
    pr_number: int,
    pr_title: str,
    pr_url: str,
    decision: str,
    reasoning: str = None,
    value_score: int = None,
    quality_score: int = None
):
    """
    Notify about Tech Lead's decision on a PR.

    Args:
        repo_name: Repository name
        pr_number: PR number
        pr_title: PR title
        pr_url: URL to the PR
        decision: MERGE, CLOSE, or REQUEST_CHANGES
        reasoning: Why this decision was made
        value_score: Value score given
        quality_score: Quality score given
    """
    # Map decision to notification type
    if decision == 'MERGE':
        notify_pr_merged(repo_name, pr_number, pr_title, pr_url, value_score, quality_score)
    elif decision == 'CLOSE':
        notify_pr_closed(repo_name, pr_number, pr_title, pr_url, reasoning)
    # REQUEST_CHANGES doesn't need a notification - it's part of the normal flow


@_fire_and_forget
def notify_spec_created(
    product_name: str,
    spec_title: str,
    parent_url: str,
    child_count: int,
    affected_repos: List[str],
    value_score: int = None
):
    """
    Notify when a new product spec is created with linked tickets.

    Args:
        product_name: Name of the product
        spec_title: Title of the spec
        parent_url: URL to the parent spec issue
        child_count: Number of child implementation tickets created
        affected_repos: List of repository names affected
        value_score: Value score of the spec
    """
    if not _should_notify('spec_created'):
        # Fall back to run_complete notification type
        if not _should_notify('run_complete'):
            return

    title = f"\U0001F4DC New Spec: {spec_title[:50]}"

    fields = [
        {'name': 'Product', 'value': product_name, 'inline': True},
        {'name': 'Tickets Created', 'value': str(child_count + 1), 'inline': True},
    ]

    if value_score is not None:
        fields.append({'name': 'Value Score', 'value': f"{value_score}/10", 'inline': True})

    if affected_repos:
        fields.append({
            'name': 'Affected Repos',
            'value': ', '.join(affected_repos[:5]),
            'inline': False
        })

    embed = _build_discord_embed(
        title=title,
        color=COLORS['purple'],
        fields=fields,
        url=parent_url,
        footer=f"Barbossa v{VERSION}"
    )

    _send_discord_webhook({'embeds': [embed]})


def reload_config():
    """Force reload of notification configuration."""
    global _config, _config_loaded
    _config = None
    _config_loaded = False
    _load_notification_config()


# =============================================================================
# TESTING / CLI
# =============================================================================

def test_webhook():
    """Send a test notification to verify webhook configuration."""
    webhook_url = _get_discord_webhook()

    if not webhook_url:
        print("No Discord webhook configured in settings.notifications.discord_webhook")
        return False

    print(f"Testing webhook: {webhook_url[:50]}...")

    embed = _build_discord_embed(
        title="\U0001F3F4\u200D\U00002620\uFE0F Barbossa Test Notification",
        description="This is a test notification to verify your webhook configuration is working correctly.",
        color=COLORS['info'],
        fields=[
            {'name': 'Status', 'value': 'Webhook configured successfully!', 'inline': True},
            {'name': 'Version', 'value': VERSION, 'inline': True},
        ],
        footer="Barbossa Notification System"
    )

    # Send synchronously for testing
    result = _send_discord_webhook({'embeds': [embed]})

    if result:
        print("Test notification sent successfully!")
    else:
        print("Failed to send test notification. Check the webhook URL and logs.")

    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    print(f"Barbossa Notifications v{VERSION}")
    print("=" * 40)

    config = _load_notification_config()
    print(f"Enabled: {_is_enabled()}")
    print(f"Discord webhook: {'configured' if _get_discord_webhook() else 'not configured'}")

    # Show retry queue status
    queue_status = get_retry_queue_status()
    print(f"Retry queue size: {queue_status['size']}")
    if queue_status['size'] > 0:
        print(f"  Oldest entry: {queue_status['oldest_age_minutes']:.1f} minutes")
        if queue_status['next_retry_in_seconds']:
            print(f"  Next retry in: {queue_status['next_retry_in_seconds']:.0f} seconds")

    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            print("\nSending test notification...")
            test_webhook()
        elif sys.argv[1] == 'retry':
            print("\nProcessing retry queue...")
            stats = process_retry_queue()
            print(f"Processed: {stats['processed']}, Succeeded: {stats['succeeded']}, "
                  f"Requeued: {stats['requeued']}, Failed: {stats['failed']}, "
                  f"Expired: {stats['expired']}")
