#!/usr/bin/env python3
"""
Barbossa Firebase Client

Provides:
- Usage analytics via Google Analytics 4 Measurement Protocol
- State tracking via Firebase Cloud Functions (for agent coordination)
- Soft version checking (warns but never blocks)

Privacy:
- Anonymous installation ID (SHA256 hash, not reversible)
- No repository names, usernames, or code content
- Opt-out options:
  1. Config file: settings.telemetry = false
  2. Environment variable: BARBOSSA_ANALYTICS_OPT_OUT=true

Design principles:
- NEVER blocks agent execution - all Firebase calls are fire-and-forget
- Graceful degradation - if Firebase is down, everything still works
- Soft version checks - warns about updates, never blocks running processes

NOTE: System prompts are loaded locally from prompts/ directory.
See barbossa_prompts.py for prompt loading.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError
import threading

# Firebase Cloud Functions base URL
FIREBASE_BASE_URL = os.environ.get(
    "BARBOSSA_FIREBASE_URL",
    "https://us-central1-barbossa-450802.cloudfunctions.net"
)

# Google Analytics 4 Measurement Protocol
GA4_CONFIG = {
    "measurement_id": "G-XNTRF7ZYQ5",
    "api_secret": os.environ.get("GA4_API_SECRET", ""),
    "endpoint": "https://www.google-analytics.com/mp/collect"
}

# Telemetry state - can be disabled via config or env var
_telemetry_enabled = True
_telemetry_configured = False


def _check_telemetry_config() -> bool:
    """
    Check if telemetry is enabled. Checks (in order):
    1. Environment variable BARBOSSA_ANALYTICS_OPT_OUT
    2. Config file settings.telemetry

    Returns True if telemetry is enabled, False if disabled.
    """
    # Check environment variable first (takes precedence)
    env_opt_out = os.environ.get("BARBOSSA_ANALYTICS_OPT_OUT", "").lower()
    if env_opt_out in ("true", "1", "yes"):
        return False

    # Check config file
    config_paths = [
        Path(os.environ.get('BARBOSSA_DIR', '/app')) / 'config' / 'repositories.json',
        Path.home() / 'barbossa-dev' / 'config' / 'repositories.json',
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    settings = config.get('settings', {})
                    # Check for telemetry setting (defaults to True if not specified)
                    telemetry = settings.get('telemetry', True)
                    if telemetry is False or str(telemetry).lower() in ('false', '0', 'no'):
                        return False
                    break
            except (json.JSONDecodeError, IOError):
                pass

    return True


def _get_telemetry_enabled() -> bool:
    """Get telemetry enabled state, checking config on first call."""
    global _telemetry_enabled, _telemetry_configured

    if not _telemetry_configured:
        _telemetry_enabled = _check_telemetry_config()
        _telemetry_configured = True

    return _telemetry_enabled


def configure_telemetry(enabled: bool):
    """
    Explicitly configure telemetry state.
    Called by agents after loading config.
    """
    global _telemetry_enabled, _telemetry_configured
    _telemetry_enabled = enabled
    _telemetry_configured = True


# Current client version
CLIENT_VERSION = "1.8.1"

# Timeout for Firebase calls (short - we never want to block)
FIREBASE_TIMEOUT = 5

logger = logging.getLogger('barbossa.firebase')


def _generate_installation_id() -> str:
    """Generate a unique, anonymous installation ID."""
    machine_info = f"{os.uname().nodename}-{os.path.expanduser('~')}"
    return hashlib.sha256(machine_info.encode()).hexdigest()[:32]


def _fire_and_forget(func):
    """Decorator to run function in background thread. Never blocks."""
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
        thread.start()
    return wrapper


def _call_firebase(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Dict]:
    """
    Call a Firebase Cloud Function. Returns None on any error.

    NEVER raises exceptions - all errors are logged and swallowed.
    This ensures Firebase issues never break agent execution.
    """
    try:
        url = f"{FIREBASE_BASE_URL}/{endpoint}"

        if method == "GET" and data:
            params = "&".join(f"{k}={v}" for k, v in data.items())
            url = f"{url}?{params}"
            body = None
        else:
            body = json.dumps(data).encode('utf-8') if data else None

        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"} if body else {},
            method=method
        )

        with urlopen(request, timeout=FIREBASE_TIMEOUT) as response:
            if response.status in (200, 204):
                try:
                    return json.loads(response.read().decode('utf-8'))
                except json.JSONDecodeError:
                    return {"success": True}  # Response was successful but not JSON
        return None

    except URLError as e:
        logger.debug(f"Firebase call failed (non-critical): {endpoint} - {e}")
        return None
    except Exception as e:
        logger.debug(f"Firebase call error (non-critical): {endpoint} - {e}")
        return None


class BarbossaClient:
    """
    Barbossa Firebase client for analytics and state tracking.

    Key design principles:
    - NEVER blocks agent execution
    - All network calls are fire-and-forget or have short timeouts
    - Graceful degradation - everything works if Firebase is down
    - Soft version checks - warns but never blocks
    """

    def __init__(self, version: str = CLIENT_VERSION):
        self.version = version
        self._registered = False
        self._version_checked = False
        self._update_available = None
        self.installation_id = _generate_installation_id()

    def register_installation(self) -> bool:
        """
        Register this installation via Google Analytics 4.

        This is transparent and privacy-respecting:
        - Only sends an anonymous client ID (hash of machine info)
        - Only sends version number
        - No personal information
        - Opt-out via config (settings.telemetry: false) or env var
        """
        if self._registered:
            return True

        if not _get_telemetry_enabled():
            logger.debug("Analytics opted out - skipping registration")
            self._registered = True
            return True

        success = self._send_ga4_event("install", {
            "engagement_time_msec": "1"
        })

        if success:
            self._registered = True

        return success

    def _send_ga4_event(self, event_name: str, params: Optional[Dict] = None) -> bool:
        """Send an event to Google Analytics 4."""
        if not GA4_CONFIG["api_secret"]:
            logger.debug("GA4 API secret not configured - skipping analytics")
            return True

        if not _get_telemetry_enabled():
            return True

        try:
            url = (
                f"{GA4_CONFIG['endpoint']}"
                f"?measurement_id={GA4_CONFIG['measurement_id']}"
                f"&api_secret={GA4_CONFIG['api_secret']}"
            )

            payload = {
                "client_id": self.installation_id,
                "events": [{
                    "name": event_name,
                    "params": params or {}
                }]
            }

            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"Barbossa/{self.version}"
            }

            request = Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method="POST"
            )

            with urlopen(request, timeout=5) as response:
                return response.status in (200, 204)

        except Exception as e:
            logger.debug(f"GA4 event send failed (non-critical): {e}")
            return False

    def track_agent_run(self, agent: str) -> bool:
        """Track an agent run event (anonymous usage only)."""
        return self._send_ga4_event("agent_run", {
            "agent_type": agent,
            "engagement_time_msec": "1"
        })

    # =========================================================================
    # VERSION CHECKING (soft - warns but never blocks)
    # =========================================================================

    def check_version(self) -> Optional[str]:
        """
        Check if a newer version is available. Returns update message or None.

        IMPORTANT: This NEVER blocks execution. It's purely informational.
        Users with running processes won't be interrupted.
        """
        if self._version_checked:
            return self._update_available

        result = _call_firebase("checkVersion", "GET", {"version": self.version})

        self._version_checked = True

        if result and not result.get("latest", True):
            self._update_available = result.get("message")
            return self._update_available

        return None

    # =========================================================================
    # STATE TRACKING (for agent coordination)
    # =========================================================================

    @_fire_and_forget
    def track_run_start(self, agent: str, session_id: str, repo_count: int = 1):
        """
        Record that an agent run has started. Fire-and-forget.

        This enables:
        - Visibility into active runs across all installations
        - Future coordination features
        - Usage patterns (without identifying info)
        """
        if not _get_telemetry_enabled():
            return

        _call_firebase("trackRunStart", "POST", {
            "installation_id": self.installation_id,
            "agent": agent,
            "session_id": session_id,
            "repo_count": repo_count,
            "version": self.version,
            "started_at": datetime.utcnow().isoformat()
        })

    @_fire_and_forget
    def track_run_end(self, agent: str, session_id: str, success: bool, pr_created: bool = False):
        """
        Record that an agent run has completed. Fire-and-forget.

        This enables:
        - Success rate tracking
        - Performance insights
        - Debugging patterns
        """
        if not _get_telemetry_enabled():
            return

        _call_firebase("trackRunEnd", "POST", {
            "installation_id": self.installation_id,
            "agent": agent,
            "session_id": session_id,
            "success": success,
            "pr_created": pr_created,
            "version": self.version,
            "ended_at": datetime.utcnow().isoformat()
        })

    @_fire_and_forget
    def heartbeat(self):
        """
        Send a heartbeat to indicate this installation is active.
        Called periodically during long-running operations.
        """
        if not _get_telemetry_enabled():
            return

        _call_firebase("heartbeat", "POST", {
            "installation_id": self.installation_id,
            "version": self.version,
            "timestamp": datetime.utcnow().isoformat()
        })


# =========================================================================
# BACKWARD COMPATIBLE ALIASES
# =========================================================================

# Alias for backward compatibility
BarbossaAnalytics = BarbossaClient


# Global instance
_client: Optional[BarbossaClient] = None


def get_client() -> BarbossaClient:
    """Get the global client instance."""
    global _client
    if _client is None:
        _client = BarbossaClient()
    return _client


# Backward compatible alias
def get_analytics() -> BarbossaClient:
    """Get the global client instance (backward compatible alias)."""
    return get_client()


def register_installation() -> bool:
    """Register this installation."""
    return get_client().register_installation()


def track_agent_run(agent: str) -> bool:
    """Track an agent run event."""
    return get_client().track_agent_run(agent)


def check_version() -> Optional[str]:
    """Check for updates. Returns message if update available, None otherwise."""
    return get_client().check_version()


def track_run_start(agent: str, session_id: str, repo_count: int = 1):
    """Track agent run start (fire-and-forget)."""
    get_client().track_run_start(agent, session_id, repo_count)


def track_run_end(agent: str, session_id: str, success: bool, pr_created: bool = False):
    """Track agent run end (fire-and-forget)."""
    get_client().track_run_end(agent, session_id, success, pr_created)


def heartbeat():
    """Send heartbeat (fire-and-forget)."""
    get_client().heartbeat()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Barbossa Firebase Client")
    print(f"Version: {CLIENT_VERSION}")
    print(f"Telemetry enabled: {_get_telemetry_enabled()}")
    print(f"Firebase URL: {FIREBASE_BASE_URL}")

    client = BarbossaClient()
    print(f"Installation ID: {client.installation_id[:8]}...")

    # Test version check
    print("\nChecking for updates...")
    update_msg = client.check_version()
    if update_msg:
        print(f"Update available: {update_msg}")
    else:
        print("You're running the latest version.")
