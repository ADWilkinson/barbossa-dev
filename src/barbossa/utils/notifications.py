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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Current version
VERSION = "1.7.3"

# Timeout for webhook calls (short - we never want to block)
WEBHOOK_TIMEOUT = 10

logger = logging.getLogger('barbossa.notifications')

# Global configuration state
_config: Optional[Dict] = None
_config_loaded = False

# Track pending notification threads so we can wait for them before process exit
_pending_threads: List[threading.Thread] = []
_threads_lock = threading.Lock()


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


def wait_for_pending(timeout: float = 5.0):
    """Wait for all pending notification threads to complete.

    Call this at the end of agent runs to ensure notifications are sent
    before the process exits.

    Args:
        timeout: Maximum seconds to wait (default 5s, enough for webhook calls)
    """
    with _threads_lock:
        threads = list(_pending_threads)

    if not threads:
        return

    logger.debug(f"Waiting for {len(threads)} pending notification(s)...")

    for thread in threads:
        thread.join(timeout=timeout / len(threads) if threads else timeout)

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
}


def _send_discord_webhook(payload: Dict) -> bool:
    """
    Send a payload to Discord webhook.

    NEVER raises exceptions - all errors are logged and swallowed.
    This ensures webhook issues never break agent execution.
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

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print("\nSending test notification...")
        test_webhook()
