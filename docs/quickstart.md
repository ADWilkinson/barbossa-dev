# Quick Start

Get Barbossa running in 5 minutes.

---

## Requirements

- **Docker** - [Install](https://docs.docker.com/get-docker/)
- **GitHub account** with personal access token
- **Claude authentication** (choose one):
  - [Claude Pro/Max subscription](https://claude.ai) (recommended - long-lasting tokens)
  - [Anthropic API account](https://console.anthropic.com) (pay-as-you-go)
- **Platform:** Linux (x86_64), macOS (Intel/Apple Silicon), Windows (WSL2)

---

## Setup

```bash
# 1. Generate authentication tokens

# GitHub token
gh auth token  # OR create at https://github.com/settings/tokens

# Claude token (Option 1 - Recommended)
claude login   # Then extract token from ~/.claude/.credentials.json
# Claude API key (Option 2)
# Get from: https://console.anthropic.com/settings/keys

# 2. Run install script (will prompt for tokens)
curl -fsSL https://raw.githubusercontent.com/ADWilkinson/barbossa-dev/main/install.sh | bash

# 3. Start
cd barbossa && docker compose up -d

# 4. Verify
docker exec barbossa barbossa health
```

The install script will:
- Prompt for your GitHub username and repository
- Ask for your GitHub token
- Ask for your Claude token/API key
- Create a `.env` file with your authentication
- Configure everything automatically

To add more repositories later, edit `config/repositories.json`. See [Configuration](configuration.html) for all options.

**Tip:** Use Claude to help configure! Give it [llms.txt](https://github.com/ADWilkinson/barbossa-dev/blob/main/llms.txt) for context.

---

## Commands

```bash
docker exec barbossa barbossa health          # Check status
docker exec barbossa barbossa run engineer    # Run now
docker exec barbossa barbossa status          # Activity
docker compose logs -f                        # Logs
```

---

## What Happens Next

Barbossa runs automatically:
- **Discovery** finds issues and adds them to backlog
- **Engineer** picks from backlog and creates PRs
- **Tech Lead** reviews PRs and merges good ones

You wake up to PRs already merged. Set `auto_merge: false` in config if you prefer to merge manually.

---

## Next Steps

- [Configuration](configuration.html) - All config options
- [Agents](agents.html) - How agents work
- [Troubleshooting](troubleshooting.html) - Common issues
