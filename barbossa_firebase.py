#!/usr/bin/env python3
"""
Barbossa Firebase Client

Central client for Firebase interactions:
- Fetching system prompts from cloud (cached for process lifetime)
- Version compatibility checking
- Simple unique user registration (transparent, no analytics)

This module creates a dependency on the Barbossa cloud infrastructure,
ensuring all installations connect to the official Firebase backend.
"""

import hashlib
import json
import logging
import os
from typing import Dict, Optional, Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# Firebase Configuration - Barbossa Official
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAXLIl-ocMtkFcH7l7CEXBAU8cr8sKmfrQ",
    "authDomain": "barbossa-dev.firebaseapp.com",
    "projectId": "barbossa-dev",
    "storageBucket": "barbossa-dev.firebasestorage.app",
    "messagingSenderId": "1022883740796",
    "appId": "1:1022883740796:web:f94249ee38bbffd4f39df9",
    "measurementId": "G-XNTRF7ZYQ5"
}

# Cloud Functions base URL
FUNCTIONS_BASE_URL = f"https://us-central1-{FIREBASE_CONFIG['projectId']}.cloudfunctions.net"

# Current client version
CLIENT_VERSION = "5.2.0"

# All agent types
AGENT_TYPES = ["engineer", "tech_lead", "discovery", "product_manager", "auditor"]

logger = logging.getLogger('barbossa.firebase')


def _generate_installation_id() -> str:
    """Generate a unique, anonymous installation ID.

    Uses a hash of machine-specific info to create a consistent ID
    without storing any personal information.
    """
    # Use hostname + home directory as a stable identifier
    # This is hashed so no actual machine info is transmitted
    machine_info = f"{os.uname().nodename}-{os.path.expanduser('~')}"
    return hashlib.sha256(machine_info.encode()).hexdigest()[:32]


class BarbossaFirebase:
    """
    Firebase client for Barbossa agents.

    Handles:
    - Fetching system prompts from cloud (pre-fetched at init, cached for process lifetime)
    - Version compatibility checks
    - Simple unique user registration (transparent)
    """

    def __init__(self, version: str = CLIENT_VERSION, prefetch_prompts: bool = True):
        self.version = version
        self.config = FIREBASE_CONFIG
        self.base_url = FUNCTIONS_BASE_URL
        self._prompt_cache: Dict[str, str] = {}
        self._version_checked = False
        self._compatible = True
        self._registered = False
        self._initialized = False
        self.installation_id = _generate_installation_id()

        if prefetch_prompts:
            self._init()

    def _init(self):
        """Initialize by pre-fetching all prompts and checking version.

        Called once at startup. All prompts are cached for process lifetime.
        """
        if self._initialized:
            return

        logger.info("Initializing Barbossa Firebase client...")

        # Check version first
        self.check_version()

        # Register installation (for unique user counting)
        self.register_installation()

        # Pre-fetch all agent prompts
        self._prefetch_all_prompts()

        self._initialized = True
        logger.info("Firebase client initialized")

    def _prefetch_all_prompts(self):
        """Pre-fetch all agent prompts at startup.

        Prompts are cached for the lifetime of the process.
        This reduces network calls and ensures consistent behavior.
        """
        logger.info("Pre-fetching system prompts from cloud...")

        for agent in AGENT_TYPES:
            template = self._fetch_prompt(agent)
            if template:
                self._prompt_cache[agent] = template
                logger.info(f"  Cached prompt for {agent} ({len(template)} chars)")
            else:
                logger.warning(f"  Could not fetch prompt for {agent} - will use fallback")

        logger.info(f"Pre-fetched {len(self._prompt_cache)}/{len(AGENT_TYPES)} prompts")

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        timeout: int = 10
    ) -> Optional[Dict]:
        """Make HTTP request to Firebase Functions."""
        try:
            url = f"{self.base_url}/{endpoint}"

            if params:
                url += "?" + urlencode(params)

            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"Barbossa/{self.version}"
            }

            body = None
            if data:
                body = json.dumps(data).encode('utf-8')

            request = Request(url, data=body, headers=headers, method=method)

            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode('utf-8'))

        except HTTPError as e:
            logger.warning(f"HTTP error from {endpoint}: {e.code} {e.reason}")
            return None
        except URLError as e:
            logger.warning(f"Network error calling {endpoint}: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from {endpoint}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error calling {endpoint}: {e}")
            return None

    def check_version(self) -> Dict[str, Any]:
        """
        Check if this version is compatible with the cloud.

        Returns:
            Dict with keys: compatible, latest, message
        """
        if self._version_checked:
            return {
                "compatible": self._compatible,
                "checked": True
            }

        result = self._make_request("checkVersion", params={"version": self.version})

        if result:
            self._version_checked = True
            self._compatible = result.get("compatible", True)

            if not self._compatible:
                logger.error(f"Version {self.version} is no longer supported!")
                logger.error(result.get("message", "Please upgrade."))
            elif not result.get("latest"):
                logger.info(f"New version available: {result.get('latestVersion')}")

            return result

        # Fail open - if we can't reach the server, allow operation
        logger.warning("Could not check version - continuing anyway")
        return {"compatible": True, "checked": False}

    def _fetch_prompt(self, agent: str) -> Optional[str]:
        """Fetch a single prompt from the cloud."""
        result = self._make_request(
            "getSystemPrompt",
            params={"agent": agent, "version": self.version}
        )

        if result and "template" in result:
            return result["template"]

        return None

    def get_system_prompt(self, agent: str) -> Optional[str]:
        """
        Get the system prompt template for an agent.

        Prompts are pre-fetched at init and cached for process lifetime.
        Returns cached prompt if available, None otherwise.

        Args:
            agent: Agent type (engineer, tech_lead, discovery, product_manager, auditor)

        Returns:
            Prompt template string, or None if unavailable
        """
        # Ensure we're initialized
        if not self._initialized:
            self._init()

        # Return cached prompt
        return self._prompt_cache.get(agent)

    def register_installation(self) -> bool:
        """
        Register this installation for unique user counting.

        This is transparent:
        - Only sends an anonymous installation ID (hash)
        - Only sends version number
        - No personal information, no usage tracking

        This helps us understand how many unique users are using Barbossa.
        """
        if self._registered:
            return True

        result = self._make_request(
            "registerInstallation",
            method="POST",
            data={
                "installation_id": self.installation_id,
                "version": self.version
            }
        )

        if result and result.get("success"):
            self._registered = True
            return True

        return False

    def get_default_config(self) -> Optional[Dict]:
        """
        Get the default configuration template.

        Returns:
            Default config dict, or None if unavailable
        """
        result = self._make_request("getDefaultConfig")
        return result.get("config") if result else None

    def health_check(self) -> bool:
        """
        Check if Firebase backend is healthy.

        Returns:
            True if backend is reachable and healthy
        """
        result = self._make_request("health", timeout=5)
        return result is not None and result.get("status") == "healthy"


# Global instance - lazily initialized
_firebase: Optional[BarbossaFirebase] = None


def get_firebase() -> BarbossaFirebase:
    """Get the global Firebase client instance.

    The first call initializes the client and pre-fetches all prompts.
    Subsequent calls return the cached instance.
    """
    global _firebase
    if _firebase is None:
        _firebase = BarbossaFirebase()
    return _firebase


def check_version() -> Dict[str, Any]:
    """Check version compatibility."""
    return get_firebase().check_version()


def get_system_prompt(agent: str) -> Optional[str]:
    """Get system prompt for an agent (from cache)."""
    return get_firebase().get_system_prompt(agent)


def register_installation() -> bool:
    """Register this installation for unique user counting."""
    return get_firebase().register_installation()


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    print("Initializing Firebase client (will pre-fetch prompts)...")
    firebase = BarbossaFirebase()

    print("\nCached prompts:")
    for agent in AGENT_TYPES:
        prompt = firebase.get_system_prompt(agent)
        status = f"{len(prompt)} chars" if prompt else "NOT CACHED"
        print(f"  {agent}: {status}")
