# Quickstart

## Requirements

- Docker
- GitHub CLI (`gh`)
- Claude Pro/Max or Anthropic API key

## Install

```bash
# Install
curl -fsSL https://raw.githubusercontent.com/ADWilkinson/barbossa-dev/main/install.sh | bash

# Start
cd barbossa && docker compose up -d

# Verify
docker exec barbossa barbossa doctor
```

The installer prompts for GitHub username, repo, and tokens.

## Commands

```bash
barbossa doctor       # Full diagnostics
barbossa watch        # Tail all logs
barbossa engineer     # Run engineer now
barbossa tl           # Run tech lead now
barbossa status       # Current activity
barbossa metrics      # Cost and performance
```

Run inside container: `docker exec barbossa <command>`

## What happens next

1. **Discovery** scans code, creates `backlog` issues
2. **Engineer** picks issues, creates PRs
3. **Tech Lead** reviews and merges

First PR typically appears within 2 hours.

Set `auto_merge: false` to review PRs manually.

## Tips

Add `CLAUDE.md` to your repo with project context. Dramatically improves code quality.

## Next

- [Configuration](configuration.md) — All options
- [How It Works](how-it-works.md) — Agent details
- [Examples](examples.md) — Sample configs
