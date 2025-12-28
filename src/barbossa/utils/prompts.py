#!/usr/bin/env python3
"""
Barbossa Prompt Loader

Simple local prompt loading from files. No network dependencies.
Prompts are stored in prompts/ directory as .txt files.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

# Prompt directory at project root (/app/prompts in container)
# Since this file is at /app/src/barbossa/utils/prompts.py, we need to go up 4 levels to /app
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"

# Valid agent types
AGENT_TYPES = ["engineer", "tech_lead", "discovery", "product_manager", "auditor"]

logger = logging.getLogger('barbossa.prompts')

# In-memory cache
_prompt_cache: Dict[str, str] = {}


def _load_prompt(agent: str) -> Optional[str]:
    """Load a prompt from file."""
    prompt_file = PROMPTS_DIR / f"{agent}.txt"

    if not prompt_file.exists():
        logger.error(f"Prompt file not found: {prompt_file}")
        return None

    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read prompt file {prompt_file}: {e}")
        return None


def get_system_prompt(agent: str) -> Optional[str]:
    """
    Get the system prompt template for an agent.

    Prompts are loaded from prompts/{agent}.txt files.
    Cached in memory after first load.

    Args:
        agent: Agent type (engineer, tech_lead, discovery, product_manager, auditor)

    Returns:
        Prompt template string, or None if unavailable
    """
    if agent not in AGENT_TYPES:
        logger.error(f"Unknown agent type: {agent}")
        return None

    # Return cached if available
    if agent in _prompt_cache:
        return _prompt_cache[agent]

    # Load and cache
    prompt = _load_prompt(agent)
    if prompt:
        _prompt_cache[agent] = prompt
        logger.debug(f"Loaded prompt for {agent} ({len(prompt)} chars)")

    return prompt


def preload_all() -> Dict[str, bool]:
    """
    Preload all prompts into cache.

    Returns:
        Dict mapping agent name to success status
    """
    results = {}
    for agent in AGENT_TYPES:
        prompt = get_system_prompt(agent)
        results[agent] = prompt is not None
        if prompt:
            logger.info(f"Loaded {agent} prompt ({len(prompt)} chars)")
        else:
            logger.error(f"FAILED to load {agent} prompt")

    return results


def clear_cache():
    """Clear the prompt cache (useful for testing)."""
    global _prompt_cache
    _prompt_cache = {}


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)

    print("Loading prompts from local files...")
    results = preload_all()

    print("\nPrompt status:")
    for agent, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {agent}: {status}")
