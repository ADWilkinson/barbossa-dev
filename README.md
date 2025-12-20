# Barbossa

**Your autonomous AI development team that never sleeps.**

Barbossa is a five-agent system that continuously improves your codebase. It discovers features, finds technical debt, implements changes, reviews code, and monitors system health - all running autonomously on a schedule.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/ADWilkinson?style=flat-square)](https://github.com/sponsors/ADWilkinson)

---

## What It Does

```
You sleep.
Barbossa works.
You wake up to PRs.
```

Every 2 hours, Barbossa:
1. **Discovers** work from your backlog or finds improvements
2. **Implements** changes and creates a PR
3. **Reviews** with strict quality gates
4. **Merges** or requests changes

You review the PRs, merge the good ones, and your codebase improves continuously.

---

## Quick Start (5 minutes)

### Prerequisites

- Docker
- Claude Max subscription
- GitHub account

### 1. Clone and Configure

```bash
git clone https://github.com/ADWilkinson/barbossa.git
cd barbossa

# Create minimal config (just 3 fields!)
cat > config/repositories.json << 'EOF'
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "git@github.com:your-github-username/my-app.git"
    }
  ]
}
EOF
```

### 2. Set Up Authentication

```bash
# GitHub token
echo "GITHUB_TOKEN=ghp_your_token_here" > .env

# Claude CLI (on your host machine)
claude login
```

### 3. Start Barbossa

```bash
docker compose up -d
```

### 4. Verify It's Working

```bash
# Check health
docker exec barbossa barbossa health

# Run engineer manually (don't wait 2 hours)
docker exec barbossa barbossa run engineer

# Watch logs
docker compose logs -f
```

Your first PR should appear within minutes!

---

## The Five Agents

| Agent | Default Schedule | Purpose |
|-------|------------------|---------|
| **Product Manager** | 3x daily | Analyzes your product, suggests valuable features |
| **Discovery** | 4x daily | Finds TODOs, missing tests, accessibility gaps |
| **Engineer** | Every 2 hours | Implements issues, creates PRs |
| **Tech Lead** | Every 2 hours | Reviews PRs with strict criteria, auto-merges |
| **Auditor** | Daily | Monitors health, identifies patterns, suggests improvements |

All schedules are configurable. See [Configuration](docs/configuration.md).

---

## Configuration

### Minimal (just get it running)

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "git@github.com:your-github-username/my-app.git"
    }
  ]
}
```

### With Options

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "git@github.com:your-github-username/my-app.git",
      "package_manager": "pnpm",
      "do_not_touch": ["src/lib/auth.ts", "prisma/migrations/"],
      "focus_areas": ["Improve test coverage", "Add loading states"]
    }
  ]
}
```

See [config/repositories.advanced.json.example](config/repositories.advanced.json.example) for all options.

### Customize Schedule

```json
{
  "settings": {
    "schedule": {
      "engineer": "every_hour",
      "discovery": "2x_daily",
      "product_manager": "disabled"
    }
  }
}
```

Presets: `every_hour`, `every_2_hours`, `every_4_hours`, `2x_daily`, `3x_daily`, `4x_daily`, `daily_morning`, `disabled`

Or use cron: `"0 9 * * *"` = daily at 9am

---

## CLI Commands

Barbossa includes a CLI for easy management:

```bash
# Inside Docker
docker exec barbossa barbossa health     # Check system status
docker exec barbossa barbossa run engineer   # Run engineer now
docker exec barbossa barbossa status     # View recent activity
docker exec barbossa barbossa logs       # View logs

# Or locally (if installed)
barbossa init      # Interactive setup wizard
barbossa health    # Check everything works
```

---

## Docker Commands

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f

# Restart
docker compose restart

# Stop
docker compose down

# Rebuild after changes
docker compose build && docker compose up -d
```

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **Claude Max** | $100/month to Anthropic - provides the AI |
| **GitHub Token** | Personal access token with `repo` scope |
| **Docker** | To run the container |
| **SSH Keys** | For private repo access (optional for public repos) |

Barbossa uses Claude CLI with your Max subscription. You pay Anthropic directly - Barbossa is free and open source.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Product Manager        Discovers valuable features        │
│         ↓                                                   │
│  Discovery              Finds technical debt, TODOs        │
│         ↓                                                   │
│  GitHub Issues          Backlog of work                    │
│         ↓                                                   │
│  Engineer               Implements, creates PRs            │
│         ↓                                                   │
│  Tech Lead              Reviews, merges or rejects         │
│         ↓                                                   │
│  Your Codebase          Continuously improving             │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Validation Failed on Startup

If Barbossa shows validation errors:

```bash
# Check what's wrong
docker exec barbossa barbossa health

# Fix the issues, then restart
docker compose restart
```

### No PRs Being Created

```bash
# Check if there are issues in backlog
docker exec barbossa gh issue list --label backlog

# Run engineer manually and watch output
docker exec barbossa barbossa run engineer
```

### Claude Authentication Issues

```bash
# Re-authenticate on your host machine
claude login

# Restart container to pick up new credentials
docker compose restart
```

See [docs/troubleshooting.md](docs/troubleshooting.md) for more.

---

## Documentation

- [Quick Start Guide](docs/quickstart.md)
- [Configuration Reference](docs/configuration.md)
- [Agent Documentation](docs/agents.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

---

## Cloud Infrastructure

Barbossa uses Firebase for cloud services:

- **System Prompts** - Agent prompts are fetched from the cloud and cached at startup
- **Version Checking** - Ensures your installation is compatible with latest features
- **Unique User Counting** - We track anonymous installation count (transparent, see below)

### Transparency About Data Collection

Barbossa collects minimal, anonymous data to help us understand usage:

- **Installation ID** - A hash of your machine info (no actual machine info transmitted)
- **Version Number** - Which version you're running

**What we DON'T collect:**
- Your code or repository names
- Your GitHub username or tokens
- Usage patterns or analytics
- Any personal information

This helps us know how many unique users are using Barbossa. That's it.

---

## Project Structure

```
barbossa/
├── barbossa                  # CLI tool
├── barbossa_engineer.py      # Implements PRs
├── barbossa_tech_lead.py     # Reviews PRs
├── barbossa_discovery.py     # Finds tech debt
├── barbossa_product.py       # Discovers features
├── barbossa_auditor.py       # Monitors health
├── barbossa_firebase.py      # Cloud integration
├── validate.py               # Startup validation
├── generate_crontab.py       # Dynamic schedule generator
├── functions/                # Firebase Cloud Functions
├── docs-site/                # Hosted documentation
├── config/
│   ├── repositories.json.example          # Minimal config
│   └── repositories.advanced.json.example # Full config
├── docker-compose.yml
├── Dockerfile
└── entrypoint.sh
```

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Support

- **Issues:** [GitHub Issues](https://github.com/ADWilkinson/barbossa/issues)
- **Discussions:** [GitHub Discussions](https://github.com/ADWilkinson/barbossa/discussions)

If Barbossa helps you ship faster, consider [sponsoring](https://github.com/sponsors/ADWilkinson).

---

## License

MIT - see [LICENSE](LICENSE)

---

*Built with Claude by [@ADWilkinson](https://github.com/ADWilkinson)*
