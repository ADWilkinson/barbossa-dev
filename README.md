# Barbossa

[![CI](https://github.com/ADWilkinson/barbossa-dev/actions/workflows/ci.yml/badge.svg)](https://github.com/ADWilkinson/barbossa-dev/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/ADWilkinson/barbossa-dev?style=social)](https://github.com/ADWilkinson/barbossa-dev)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fadwilkinson%2Fbarbossa--dev-blue?logo=docker)](https://ghcr.io/adwilkinson/barbossa-dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-barbossa.dev-green)](https://barbossa.dev)

**AI engineers that ship code while you sleep.**

Your backlog grows faster than you can ship. Claude is powerful, but running it manually on every issue is tedious. Barbossa turns your GitHub backlog into merged PRs automatically.

[Documentation](https://barbossa.dev) · [Quick Start](#quick-start) · [Changelog](CHANGELOG.md)

---

## What It Does

Barbossa runs on a schedule, picks issues from your backlog, implements them, creates PRs, reviews them, and merges. You wake up to shipped code.

```
Backlog Issue → Engineer creates PR → Tech Lead reviews → Merged
```

Self-hosted via Docker. Your code stays in your repos.

---

## Quick Start

```bash
# 1. Generate tokens
gh auth token                # GitHub token
claude setup-token           # Claude token (follow prompts)

# 2. Install
curl -fsSL https://raw.githubusercontent.com/ADWilkinson/barbossa-dev/main/install.sh | bash

# 3. Configure (edit config/repositories.json with your repos)

# 4. Run
cd barbossa && docker compose up -d

# 5. Verify
docker exec barbossa barbossa health
```

**Requirements:** Docker, GitHub account, Claude Pro/Max or Anthropic API key.

---

## Two Modes

| Mode | What It Does |
|------|--------------|
| **Autonomous** (default) | AI implements code from backlog, reviews PRs, merges |
| **Spec Mode** | AI generates cross-repo feature specs, no code changes |

---

## Agents

| Agent | Purpose |
|-------|---------|
| **Engineer** | Picks backlog tasks, creates PRs, addresses review feedback |
| **Tech Lead** | Reviews PRs (8 dimensions), auto-merges or requests changes |
| **Discovery** | Finds TODOs, missing tests, tech debt → creates backlog issues |
| **Product Manager** | Proposes features with acceptance criteria |
| **Auditor** | Weekly health checks, cleanup tasks |
| **Spec Generator** | Cross-repo feature specs (Spec Mode only) |

---

## Configuration

Minimal config:

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

### Options

| Field | Description |
|-------|-------------|
| `package_manager` | `npm`, `yarn`, `pnpm`, or `bun` |
| `do_not_touch` | Files agents should never modify |
| `focus` | Development priority guidance |
| `auto_merge` | `true` = merge automatically, `false` = approval only |

See [configuration docs](https://barbossa.dev/configuration.html) for all options.

---

## Commands

```bash
barbossa doctor       # Full diagnostics
barbossa watch        # Tail all logs
barbossa engineer     # Run engineer now
barbossa tl           # Run tech lead now
barbossa metrics      # Cost and performance
```

Run inside container: `docker exec barbossa <command>`

---

## Notifications

Get Discord alerts for PRs, merges, and errors:

```json
{
  "settings": {
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/..."
    }
  }
}
```

---

## Privacy

Anonymous telemetry (run counts, success rates). No code collected.

Opt out: `"settings": { "telemetry": false }`

---

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
