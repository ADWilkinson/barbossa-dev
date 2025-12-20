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

## The Five Agents

| Agent | Schedule | Purpose |
|-------|----------|---------|
| **Product Manager** | Daily | Analyzes your product, suggests valuable features |
| **Discovery** | 4x daily | Finds TODOs, missing tests, accessibility gaps |
| **Engineer** | Every 2 hours | Implements issues, creates PRs |
| **Tech Lead** | Every 2 hours | Reviews PRs with strict criteria, merges or rejects |
| **Auditor** | Daily | Monitors health, identifies patterns, suggests improvements |

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

## Quick Start

### Prerequisites

- Docker
- Claude Max subscription (`claude login`)
- GitHub Personal Access Token
- SSH keys for your repos

### Setup

```bash
# Clone
git clone https://github.com/ADWilkinson/barbossa.git
cd barbossa

# Configure your repositories
cp config/repositories.json.example config/repositories.json
# Edit config/repositories.json with your repos

# Set environment
cp .env.example .env
# Add your GITHUB_TOKEN to .env

# Authenticate Claude CLI
claude login

# Start Barbossa
docker compose up -d

# Watch logs
docker compose logs -f
```

Your first PR should appear within 2 hours.

---

## Configuration

Edit `config/repositories.json`:

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "git@github.com:your-username/my-app.git",
      "package_manager": "npm",
      "description": "My SaaS application",
      "tech_stack": {
        "framework": "Next.js 14",
        "language": "TypeScript",
        "styling": "Tailwind CSS"
      },
      "design_system": {
        "aesthetic": "Modern minimal",
        "rules": ["Use shadcn/ui", "No inline styles"]
      },
      "do_not_touch": [
        "src/lib/auth.ts",
        "prisma/migrations/"
      ],
      "focus_areas": [
        "Improve test coverage",
        "Add loading states",
        "Fix accessibility issues"
      ]
    }
  ]
}
```

See [Configuration Reference](docs/configuration.md) for all options.

---

## Documentation

- [Quick Start Guide](docs/quickstart.md)
- [Configuration Reference](docs/configuration.md)
- [Agent Documentation](docs/agents.md)
- [Troubleshooting](docs/troubleshooting.md)
- [FAQ](docs/faq.md)

---

## Commands

```bash
# Start
docker compose up -d

# View logs
docker compose logs -f

# Run engineer manually
docker exec barbossa python3 barbossa_engineer.py

# Run tech lead manually
docker exec barbossa python3 barbossa_tech_lead.py

# Check cron schedule
docker exec barbossa crontab -l

# Restart
docker compose restart

# Stop
docker compose down
```

---

## Requirements

| Requirement | Details |
|-------------|---------|
| **Claude Max** | $100/month to Anthropic - provides the AI |
| **GitHub Token** | Personal access token with `repo` scope |
| **Docker** | To run the container |
| **SSH Keys** | For private repo access |

Barbossa uses Claude CLI with your Max subscription. You pay Anthropic directly - Barbossa is free and open source.

---

## Project Structure

```
barbossa/
├── barbossa_engineer.py      # Implements PRs
├── barbossa_tech_lead.py     # Reviews PRs
├── barbossa_discovery.py     # Finds tech debt
├── barbossa_product.py       # Discovers features
├── barbossa_auditor.py       # Monitors health
├── config/
│   ├── repositories.json.example
│   └── repositories.schema.json
├── docker-compose.yml
├── Dockerfile
├── crontab
└── entrypoint.sh
```

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

Areas where help is appreciated:
- Bug fixes
- Documentation improvements
- New integrations (Slack, Linear, GitLab)
- Performance optimizations
- Test coverage

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
