# Barbossa - Autonomous AI Development Team

A five-agent autonomous development system that discovers features, finds technical debt, implements changes, reviews code, and audits system health.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## How It Works

```
Product Manager (daily)     → Discovers valuable features
         ↓
Discovery (4x daily)        → Finds technical debt, TODOs, missing tests
         ↓
   GitHub Issues            → Backlog of work
         ↓
Engineer (every 2 hours)    → Implements issues, creates PRs
         ↓
Tech Lead (every 2 hours)   → Reviews PRs, merges or requests changes
         ↓
Auditor (daily)             → Monitors health, suggests improvements
```

## Agents

| Agent | Schedule | What It Does |
|-------|----------|--------------|
| **Product Manager** | Daily | AI analyzes products, suggests features |
| **Discovery** | 4x daily | Finds TODOs, missing tests, a11y gaps |
| **Engineer** | Every 2 hours | Implements from backlog, creates PRs |
| **Tech Lead** | Every 2 hours | Reviews PRs with strict criteria |
| **Auditor** | Daily | System health and improvement insights |

## Prerequisites

- Docker
- Claude Max subscription (`claude login` to authenticate)
- GitHub Personal Access Token
- SSH keys for private repo access

## Quick Start

```bash
# Clone
git clone https://github.com/your-username/barbossa.git
cd barbossa

# Configure your repositories
cp config/repositories.json.example config/repositories.json
# Edit config/repositories.json with your repos

# Set up environment
cp .env.example .env
# Edit .env with your GITHUB_TOKEN

# Start
docker compose up -d

# View logs
docker compose logs -f
```

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
        "language": "TypeScript"
      },
      "do_not_touch": [
        "src/lib/auth.ts",
        "prisma/migrations/"
      ]
    }
  ]
}
```

## File Structure

```
barbossa/
├── barbossa_engineer.py     # Engineer agent (implements PRs)
├── barbossa_tech_lead.py    # Tech Lead agent (reviews PRs)
├── barbossa_discovery.py    # Discovery agent (finds tech debt)
├── barbossa_product.py      # Product Manager (feature discovery)
├── barbossa_auditor.py      # Auditor (health monitoring)
├── config/
│   └── repositories.json    # Your repo configurations
├── docker-compose.yml
├── Dockerfile
└── crontab                  # Agent schedules
```

## Manual Triggers

```bash
# Run engineer manually
docker exec barbossa python3 barbossa_engineer.py

# Run tech lead manually
docker exec barbossa python3 barbossa_tech_lead.py

# Run discovery manually
docker exec barbossa python3 barbossa_discovery.py
```

## Troubleshooting

```bash
# Check container status
docker ps | grep barbossa

# View logs
docker compose logs -f

# Check cron jobs
docker exec barbossa crontab -l

# Restart
docker compose restart
```

## License

MIT - see [LICENSE](LICENSE)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
