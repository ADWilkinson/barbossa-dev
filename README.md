# Barbossa

[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fadwilkinson%2Fbarbossa--dev-blue?logo=docker)](https://ghcr.io/adwilkinson/barbossa-dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-barbossa.dev-green)](https://barbossa.dev)

**AI engineers that ship code while you sleep.**

Barbossa is an autonomous development pipeline powered by Claude. Two modes: autonomous coding or product specification generation.

```bash
docker pull ghcr.io/adwilkinson/barbossa-dev:1.8.1
```

[Documentation](https://barbossa.dev) · [Quick Start](https://barbossa.dev/quickstart.html)

---

## Two Modes

| Mode | What It Does |
|------|--------------|
| **Autonomous** (default) | AI implements code from backlog, reviews PRs, merges |
| **Spec Mode** | AI generates cross-repo feature specs, no code changes |

---

## Autonomous Mode

Five agents work in a continuous pipeline:

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
| **Engineer** | Picks backlog tasks, creates PRs, addresses review feedback |
| **Tech Lead** | 8-dimension quality review, auto-merge or request changes, 3-strikes close |
| **Discovery** | Finds TODOs, missing tests, accessibility issues, tech debt |
| **Product Manager** | Proposes features with acceptance criteria |
| **Auditor** | Health scoring, creates issues for critical problems |

---

## Spec Mode

When `spec_mode.enabled = true`, all autonomous agents are disabled. Only the Spec Generator runs.

**Use when:** You want detailed feature specifications spanning multiple repos instead of autonomous code changes.

**Output:** Parent spec ticket + child implementation tickets in each affected repo.

```
     Product Configuration
   (linked repos, context)
           ↓
      Spec Generator
           ↓
  Parent Spec (primary repo)
     + Child Tickets
   (per affected repo)
```

---

## Quick Start

### Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [GitHub account](https://github.com) with personal access token
- **Claude authentication** (choose one):
  - [Claude Pro/Max subscription](https://claude.ai) (recommended - long-lasting tokens)
  - [Anthropic API account](https://console.anthropic.com) (pay-as-you-go)

### Setup

```bash
# 1. Generate authentication tokens
gh auth token                # GitHub token
claude setup-token           # Claude token (recommended)

# 2. Run install script
curl -fsSL https://raw.githubusercontent.com/ADWilkinson/barbossa-dev/main/install.sh | bash

# 3. Start
cd barbossa && docker compose up -d

# 4. Verify
docker exec barbossa barbossa health
```

---

## Configuration

### Autonomous Mode (default)

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

### Spec Mode

```json
{
  "owner": "your-github-username",
  "repositories": [
    { "name": "backend-api", "url": "https://github.com/you/backend-api.git" },
    { "name": "frontend-web", "url": "https://github.com/you/frontend-web.git" }
  ],
  "products": [
    {
      "name": "my-platform",
      "repositories": ["backend-api", "frontend-web"],
      "primary_repo": "frontend-web",
      "context": {
        "vision": "Leading platform for X",
        "current_phase": "MVP hardening",
        "constraints": ["API < 200ms", "Mobile support"],
        "strategy_notes": ["Users want faster onboarding"]
      }
    }
  ],
  "settings": {
    "spec_mode": {
      "enabled": true,
      "max_specs_per_run": 2,
      "min_value_score": 7
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `products` | Groups of linked repos forming a system |
| `primary_repo` | Where parent spec tickets are created |
| `context` | Vision, constraints, strategy notes for Claude |
| `spec_mode.enabled` | Global switch - disables all other agents |

### Common Options

| Field | Description |
|-------|-------------|
| `package_manager` | `npm`, `yarn`, `pnpm`, or `bun` |
| `do_not_touch` | Files agents should never modify |
| `focus` | Development priority (e.g., "Quality and resilience") |
| `known_gaps` | Priority issues for agents to address |
| `auto_merge` | `true` = merge automatically, `false` = approval only |

---

## Commands

```bash
docker exec barbossa barbossa health          # Check status
docker exec barbossa barbossa run engineer    # Run engineer now
docker exec barbossa barbossa run tech-lead   # Run tech lead now
docker exec barbossa barbossa run spec        # Run spec generator
docker exec barbossa barbossa status          # View activity
```

---

## Linear Integration

```json
{
  "issue_tracker": {
    "type": "linear",
    "linear": { "team_key": "ENG", "backlog_state": "Backlog" }
  }
}
```

Set `LINEAR_API_KEY` environment variable.

---

## Notifications

```json
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
```

---

## Authentication

### GitHub Token

```bash
gh auth token  # OR create at https://github.com/settings/tokens (scopes: repo, workflow)
```

### Claude Token

```bash
# Option 1: Claude Pro/Max (recommended)
claude setup-token
# Add to .env: CLAUDE_CODE_OAUTH_TOKEN=<token>

# Option 2: API key
# Get from: https://console.anthropic.com/settings/keys
# Add to .env: ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

## Troubleshooting

```bash
# Check validation
docker logs barbossa | head -50

# Verify tokens
cat .env

# Update and restart
vim .env && docker compose restart
```

See [troubleshooting docs](https://barbossa.dev/troubleshooting.html) for more.

---

## Privacy

Anonymous telemetry (run counts, success rates). No code or identifying info collected.

Opt out: `"settings": { "telemetry": false }`

---

## License

[MIT](LICENSE)
