# Quickstart

## Requirements

- Docker
- GitHub account + token
- Claude Pro/Max subscription or Anthropic API key

## Install

```bash
# Get tokens ready
gh auth token                    # GitHub token
claude setup-token               # Claude token (recommended)
# Or use Anthropic API key from console.anthropic.com

# Install
curl -fsSL https://raw.githubusercontent.com/ADWilkinson/barbossa-dev/main/install.sh | bash

# Start
cd barbossa && docker compose up -d

# Verify
docker exec barbossa barbossa health
```

The installer prompts for your GitHub username, repository, and tokens.

## Commands

```bash
docker exec barbossa barbossa health         # Status
docker exec barbossa barbossa run engineer   # Run agent manually
docker exec barbossa barbossa logs           # View logs
docker compose logs -f                       # Container logs
```

## What happens next

Agents run on schedule:

1. **Discovery** scans your code, creates issues labeled `backlog`
2. **Engineer** picks issues, implements fixes, creates PRs
3. **Tech Lead** reviews PRs, merges good ones

Set `auto_merge: false` in config if you want to merge manually.

## Tips

Add a `CLAUDE.md` file to your repository with project context. This dramatically improves code quality.

## Next

- [Configuration](configuration.md) — All options
- [How It Works](how-it-works.md) — Agent details
- [Examples](examples.md) — Sample configs
