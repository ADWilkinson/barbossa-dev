# Barbossa

[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fadwilkinson%2Fbarbossa--dev-blue?logo=docker)](https://ghcr.io/adwilkinson/barbossa-dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-barbossa.dev-green)](https://barbossa.dev)

**AI engineers that ship code while you sleep.**

Five AI agents discover features, find technical debt, implement changes, review code, and merge PRs—automatically.

```bash
docker pull ghcr.io/adwilkinson/barbossa-dev:latest
```

[Documentation](https://barbossa.dev) · [Quick Start](https://barbossa.dev/quickstart.html)

---

## How It Works

```
Discovery + Product Manager
           ↓
     Issues (GitHub or Linear)
           ↓
        Engineer → Pull Request
           ↓
       Tech Lead → Merge/Reject
```

| Agent | Purpose |
|-------|---------|
| **Engineer** | Picks tasks from backlog, creates PRs |
| **Tech Lead** | Reviews PRs, merges or requests changes |
| **Discovery** | Finds TODOs, missing tests, issues |
| **Product Manager** | Proposes high-value features |
| **Auditor** | Monitors system health |

---

## Quick Start

### Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [GitHub account](https://github.com) with personal access token
- **Claude authentication** (choose one):
  - [Claude Pro/Max subscription](https://claude.ai) (recommended - long-lasting tokens)
  - [Anthropic API account](https://console.anthropic.com) (pay-as-you-go)

**Platform Support:**
- Linux (x86_64, amd64)
- macOS (Intel and Apple Silicon via Rosetta 2 emulation)

### Setup

```bash
# 1. Generate authentication tokens
# GitHub token
gh auth token  # OR create at https://github.com/settings/tokens

# Claude token (Option 1 - Recommended)
claude setup-token   # Follow prompts to generate long-lived token
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

To add more repositories later, edit `config/repositories.json`.

---

## Configuration

Minimal config (`config/repositories.json`):

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "https://github.com/your-github-username/my-app.git"
    }
  ]
}
```

With options:

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "https://github.com/your-github-username/my-app.git",
      "package_manager": "pnpm",
      "do_not_touch": ["src/lib/auth.ts", "prisma/migrations/"]
    }
  ],
  "settings": {
    "telemetry": true,
    "tech_lead": { "auto_merge": true },
    "discovery": { "enabled": true },
    "product_manager": { "enabled": true }
  }
}
```

| Field | Description |
|-------|-------------|
| `package_manager` | `npm`, `yarn`, `pnpm`, or `bun` |
| `do_not_touch` | Files agents should never modify |
| `telemetry` | `true` (default) or `false` to disable analytics |
| `auto_merge` | `true` = merge automatically, `false` = manual review |
| `enabled` | Enable/disable individual agents |

### Scheduling

Agents run on optimized schedules to avoid resource contention:

```json
{
  "settings": {
    "schedule": {
      "engineer": "every_2_hours",
      "tech_lead": "0 1,3,5,7,9,11,13,15,17,19,21,23 * * *",
      "discovery": "0 1,5,9,13,17,21 * * *",
      "product_manager": "0 3,11,19 * * *"
    }
  }
}
```

**Default Schedule:**
- **Engineer:** 12x daily (00:00, 02:00, 04:00...) - implements features
- **Tech Lead:** 12x daily (01:00, 03:00, 05:00...) - reviews PRs 1h after engineer
- **Discovery:** 6x daily (01:00, 05:00, 09:00, 13:00, 17:00, 21:00) - finds issues
- **Product:** 3x daily (03:00, 11:00, 19:00) - suggests features

**Why Offset?**
- Avoids simultaneous API calls and resource contention
- Tech Lead reviews PRs created in previous hour
- Discovery keeps backlog fresh for next Engineer run
- Ensures smooth operation across all agents

Available presets: `every_hour`, `every_2_hours`, `every_3_hours`, `4x_daily`, `3x_daily`, `2x_daily`, `daily_morning`, or use custom cron expressions.

---

## Linear Integration

Use Linear instead of GitHub Issues for issue tracking:

```json
{
  "owner": "your-github-username",
  "issue_tracker": {
    "type": "linear",
    "linear": {
      "team_key": "MUS",
      "backlog_state": "Backlog"
    }
  },
  "repositories": [...]
}
```

Set `LINEAR_API_KEY` environment variable or add `api_key` to config.

| Field | Description |
|-------|-------------|
| `type` | `github` (default) or `linear` |
| `team_key` | Linear team key (e.g., "MUS", "ENG") |
| `backlog_state` | State name for backlog (default: "Backlog") |

With Linear, agents:
- Create issues in your Linear team
- Fetch backlog items for the Engineer
- Link branches to Linear issues automatically

---

## Authentication

### GitHub Token

Generate a token with `repo` and `workflow` scopes:

```bash
# Option 1: Via GitHub CLI
gh auth token

# Option 2: Manual creation
# Visit: https://github.com/settings/tokens
# Scopes: repo, workflow
```

Add to `.env`:
```bash
GITHUB_TOKEN=ghp_your_token_here
```

### Claude Token

**Option 1: Claude Pro/Max Subscription Token (Recommended)**

Long-lasting token (up to 1 year) from your Claude subscription:

```bash
# 1. Run setup-token command
claude setup-token

# 2. Follow the prompts to generate a long-lived token

# 3. Add to .env
CLAUDE_CODE_OAUTH_TOKEN=<your_token_from_setup>
```

**Option 2: Pay-as-you-go API Key**

For users preferring API billing:

```bash
# Get from: https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-api03-your_key_here
```

---

## Commands

```bash
docker exec barbossa barbossa health          # Check status
docker exec barbossa barbossa run engineer    # Run now
docker exec barbossa barbossa status          # Activity
docker compose logs -f                        # Logs
```

---

## Troubleshooting

### Authentication failures

```bash
# Verify tokens in .env file
cat .env

# Update tokens
vim .env  # Edit GITHUB_TOKEN and CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY
docker compose restart
```

### Validation errors on startup

```bash
# Check validation output
docker logs barbossa | head -50

# Common fixes:
# - GITHUB_TOKEN not set or invalid
# - CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY not set or invalid
# - Config file malformed
```

See [troubleshooting docs](https://barbossa.dev/troubleshooting.html) for more.

---

## Privacy & Telemetry

Barbossa collects anonymous usage data to improve the project:

- **What's collected:** Anonymous installation ID, agent run counts, success rates, version
- **What's NOT collected:** Repository names, code, usernames, or any identifying information

**To opt out**, set in your config:

```json
{
  "settings": {
    "telemetry": false
  }
}
```

Or via environment variable:

```bash
BARBOSSA_ANALYTICS_OPT_OUT=true
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[MIT](LICENSE)
