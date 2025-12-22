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
    # Check gh CLI
    success, stdout, stderr = run_cmd("gh auth status")

    if success:
        ok("GitHub CLI authenticated")
        return True

    # Try to authenticate with token if available
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        success, _, _ = run_cmd(f"echo '{token}' | gh auth login --with-token")
        if success:
            ok("GitHub CLI authenticated via GITHUB_TOKEN")
            return True

    err("GitHub CLI not authenticated")
    print("  Run: gh auth login")
    print("  Or set GITHUB_TOKEN environment variable")
    return False


def validate_claude():
    """Validate Claude CLI authentication."""
    # Check credentials file
    creds_paths = [
        Path.home() / '.claude' / '.credentials.json',
        Path('/home/barbossa/.claude/.credentials.json'),
        Path('/root/.claude/.credentials.json'),
    ]

    for creds_file in creds_paths:
        if creds_file.exists():
            try:
                with open(creds_file) as f:
                    creds = json.load(f)

                oauth = creds.get('claudeAiOauth', {})
                expires_at = oauth.get('expiresAt', 0)

                if expires_at:
                    expires_ts = expires_at / 1000 if expires_at > 1e12 else expires_at
                    expires_dt = datetime.fromtimestamp(expires_ts)
                    now = datetime.now()

                    hours_left = (expires_dt - now).total_seconds() / 3600

                    if hours_left < 0:
                        err("Claude token expired")
                        print("  Run: claude login")
                        return False
                    elif hours_left < 24:
                        warn(f"Claude token expires in {hours_left:.0f} hours")
                        print("  Consider running: claude login")
                        return True
                    else:
                        ok(f"Claude CLI authenticated (valid for {hours_left:.0f}h)")
                        return True
            except Exception as e:
                pass

    err("Claude CLI not authenticated")
    print("  Run: claude login")
    print("  Then restart the container")
    return False


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
        Path('/root/.ssh'),
    ]

    for ssh_dir in ssh_dirs:
        if ssh_dir.exists():
            keys = list(ssh_dir.glob('id_*'))
            keys = [k for k in keys if not k.suffix == '.pub']
            if keys:
                ok(f"SSH keys found ({len(keys)} keys)")
                return True

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
