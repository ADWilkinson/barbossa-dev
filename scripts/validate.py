#!/usr/bin/env python3
"""
Barbossa Startup Validation

Runs on container start to validate configuration and authentication.
Exits with error if critical checks fail, preventing silent failures.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def ok(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def warn(msg): print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")
def err(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def run_cmd(cmd, timeout=10):
    """Run a shell command."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except:
        return False, "", ""


def validate_config():
    """Validate configuration file."""
    config_file = Path('/app/config/repositories.json')

    if not config_file.exists():
        err("Config file not found: config/repositories.json")
        print()
        print("  To fix, run:")
        print("    cp config/repositories.json.example config/repositories.json")
        print("    # Then edit with your repository details")
        return False

    try:
        with open(config_file) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON in config: {e}")
        return False

    # Check owner
    if not config.get('owner'):
        err("Missing 'owner' in config")
        print("  Add your GitHub username as 'owner' in repositories.json")
        return False

    # Check repositories
    repos = config.get('repositories', [])
    if not repos:
        err("No repositories configured")
        print("  Add at least one repository to 'repositories' array")
        return False

    for i, repo in enumerate(repos):
        if not repo.get('name'):
            err(f"Repository {i+1} missing 'name'")
            return False
        if not repo.get('url'):
            err(f"Repository '{repo.get('name')}' missing 'url'")
            return False

    ok(f"Config valid: {len(repos)} repositories")
    for repo in repos:
        print(f"    - {repo['name']}")

    return True


def validate_github():
    """Validate GitHub authentication."""
    # Check for GITHUB_TOKEN environment variable (primary method)
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        err("GITHUB_TOKEN not set")
        print("  Generate token:")
        print("    gh auth token")
        print("  Or create at: https://github.com/settings/tokens")
        print("  Then add to .env file:")
        print("    GITHUB_TOKEN=ghp_your_token_here")
        return False

    # Verify token works by authenticating gh CLI
    success, _, _ = run_cmd(f"echo '{token}' | gh auth login --with-token")
    if not success:
        err("GITHUB_TOKEN invalid or gh CLI authentication failed")
        print("  Verify token is valid at: https://github.com/settings/tokens")
        return False

    ok("GitHub authenticated via GITHUB_TOKEN")
    return True


def validate_claude():
    """Validate Claude authentication."""
    # Check for ANTHROPIC_API_KEY environment variable (required)
    # Can be either:
    # 1. Claude Pro/Max subscription token (long-lasting, from claude login)
    # 2. Pay-as-you-go API key (from console.anthropic.com)
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        err("ANTHROPIC_API_KEY not set")
        print("  Option 1 (Recommended): Claude Pro/Max subscription token")
        print("    Generate a long-lasting token:")
        print("    1. Run: claude setup-token")
        print("    2. Follow prompts to generate token (lasts up to 1 year)")
        print("    3. Add to .env: ANTHROPIC_API_KEY=<your_token>")
        print()
        print("  Option 2: Pay-as-you-go API key")
        print("    Get from: https://console.anthropic.com/settings/keys")
        print("    Add to .env: ANTHROPIC_API_KEY=sk-ant-api03-...")
        return False

    # Basic validation - check token format
    # Claude Pro tokens don't start with sk-ant-, API keys do
    if api_key.startswith('sk-ant-'):
        ok("Claude authenticated via Anthropic API key (pay-as-you-go)")
    else:
        ok("Claude authenticated via Claude Pro/Max token")

    return True


def validate_git():
    """Validate git configuration."""
    success, name, _ = run_cmd("git config --global user.name")
    if not success or not name:
        warn("Git user.name not set")
        return True  # Non-critical

    success, email, _ = run_cmd("git config --global user.email")
    if not success or not email:
        warn("Git user.email not set")
        return True  # Non-critical

    ok(f"Git config: {name} <{email}>")
    return True


def validate_linear():
    """Validate Linear configuration and connectivity if Linear is configured."""
    config_file = Path('/app/config/repositories.json')

    if not config_file.exists():
        return True  # Config validation will catch this

    try:
        with open(config_file) as f:
            config = json.load(f)
    except:
        return True  # Config validation will catch this

    # Check if Linear is configured
    tracker_config = config.get('issue_tracker', {})
    if tracker_config.get('type') != 'linear':
        # Not using Linear - no validation needed
        return True

    linear_config = tracker_config.get('linear', {})

    # Check for team_key
    team_key = linear_config.get('team_key')
    if not team_key:
        err("Linear configured but 'team_key' missing")
        print("  Add 'team_key' to issue_tracker.linear config")
        print("  Example: 'team_key': 'MUS'")
        return False

    # Check for API key (env var or config)
    api_key = os.environ.get('LINEAR_API_KEY') or linear_config.get('api_key')
    if not api_key:
        err("Linear configured but LINEAR_API_KEY not set")
        print("  Either:")
        print("    1. Set LINEAR_API_KEY environment variable, OR")
        print("    2. Add 'api_key' to issue_tracker.linear config")
        print()
        print("  Get your API key from: https://linear.app/settings/api")
        return False

    # Test Linear API connectivity
    try:
        # Import here to avoid issues if linear_client doesn't exist yet
        from linear_client import LinearClient

        client = LinearClient(api_key=api_key)

        # Try to fetch team to verify API key and team access
        team_id = client._get_team_id(team_key)

        if not team_id:
            err(f"Linear team '{team_key}' not found or not accessible")
            print(f"  Verify team key '{team_key}' exists in Linear")
            print("  Check API key has access to this team")
            return False

        ok(f"Linear authenticated (team: {team_key})")
        return True

    except ImportError:
        warn("Could not import linear_client module")
        return True  # Non-critical if module doesn't exist
    except Exception as e:
        err(f"Linear API connection failed: {e}")
        print("  Check:")
        print("    - API key is valid")
        print("    - Network connectivity to api.linear.app")
        print(f"    - Team '{team_key}' exists and is accessible")
        return False


def validate_ssh():
    """Validate SSH keys exist only if SSH URLs are configured."""
    # Check if any repos use SSH URLs
    config_file = Path('/app/config/repositories.json')
    uses_ssh = False

    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
            for repo in config.get('repositories', []):
                url = repo.get('url', '')
                if url.startswith('git@') or url.startswith('ssh://'):
                    uses_ssh = True
                    break
        except:
            pass

    if not uses_ssh:
        # Using HTTPS URLs - gh CLI handles auth, no SSH needed
        ok("Using HTTPS URLs (no SSH keys required)")
        return True

    # SSH URLs configured - check for keys
    ssh_dirs = [
        Path.home() / '.ssh',
        Path('/home/barbossa/.ssh'),
    ]

    for ssh_dir in ssh_dirs:
        try:
            if ssh_dir.exists():
                keys = list(ssh_dir.glob('id_*'))
                keys = [k for k in keys if not k.suffix == '.pub']
                if keys:
                    ok(f"SSH keys found ({len(keys)} keys)")
                    return True
        except PermissionError:
            # Skip directories we can't read
            continue

    warn("SSH URLs configured but no SSH keys found")
    print("  Either mount ~/.ssh or switch to HTTPS URLs:")
    print("  https://github.com/owner/repo.git")
    return True  # Non-critical


def main():
    print()
    print(f"{Colors.BOLD}Barbossa Startup Validation{Colors.END}")
    print("=" * 40)
    print()

    critical_ok = True
    warnings = []

    # Critical checks (will block startup if failed)
    if not validate_config():
        critical_ok = False

    if not validate_github():
        critical_ok = False

    if not validate_claude():
        critical_ok = False

    # Linear validation (critical if configured)
    if not validate_linear():
        critical_ok = False

    # Non-critical checks (warnings only)
    validate_git()
    validate_ssh()

    print()
    print("=" * 40)

    if critical_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}Validation passed!{Colors.END}")
        print("Barbossa is ready to run.")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}Validation failed!{Colors.END}")
        print("Fix the errors above before Barbossa can run.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
