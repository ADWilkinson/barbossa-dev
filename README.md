# Barbossa v5.1 - Autonomous Development Pipeline

A five-agent autonomous development system that discovers features, finds technical debt, implements changes, reviews code, and audits system health.

## Architecture

```
Product Manager (daily)  AI-powered feature discovery
         |
         v
Discovery (3x daily)     Technical debt analysis (TODOs, tests, a11y)
         |
         v
   GitHub Issues         Backlog: features + improvements
         |
         v
Engineer (hourly :00)    Picks from backlog, implements, creates PRs
         |
         v
   Pull Requests         Code ready for review
         |
         v
Tech Lead (hourly :35)   Reviews PRs, merges or requests changes
         |
         v
Auditor (daily 06:30)    Analyzes system health, identifies patterns
```

## Agents

| Agent | Schedule | Purpose |
|-------|----------|---------|
| **Product Manager** | Daily at 07:00 | AI analyzes products, suggests features |
| **Discovery** | 06:00, 14:00, 22:00 | Finds TODOs, missing tests, a11y gaps |
| **Engineer** | Every hour at :00 | Implements from backlog, creates PRs |
| **Tech Lead** | Every hour at :35 | Reviews PRs with strict criteria |
| **Auditor** | Daily at 06:30 | System health and improvement insights |

## Pipeline Timing

The schedule respects dependency chains:

```
:00  Engineer starts (has 35 min to complete)
:35  Tech Lead reviews (PR now exists)
:00  Next cycle - Engineer responds to feedback OR picks new issue
```

## Quick Start

```bash
# Clone and configure
git clone https://github.com/ADWilkinson/barbossa-engineer.git
cd barbossa-engineer
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Configure repositories
# Edit config/repositories.json

# Start the system
docker compose up -d

# View logs
docker compose logs -f

# Access web portal
open http://localhost:8443
# Auth: barbossa / Galleon6242
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GITHUB_TOKEN` | GitHub personal access token (via gh auth) |

### Repository Configuration

Edit `config/repositories.json`:

```json
{
  "owner": "YourGitHubUsername",
  "repositories": [
    {
      "name": "your-repo",
      "url": "git@github.com:YourUsername/your-repo.git",
      "package_manager": "npm|yarn|pnpm",
      "description": "What this project does",
      "tech_stack": {
        "framework": "React/Next.js/etc",
        "language": "TypeScript"
      },
      "do_not_touch": [
        "paths/to/avoid"
      ]
    }
  ]
}
```

## Web Portal

Access at `http://localhost:8443` (or via Cloudflare Tunnel)

Features:
- Dashboard with session history
- Tech Lead decisions panel
- Real-time status
- Manual trigger buttons
- Log viewer

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | System status |
| `/api/sessions` | GET | All sessions |
| `/api/prs` | GET | Open PRs per repo |
| `/api/tech-lead/decisions` | GET | Review decisions |
| `/api/trigger/<repo>` | POST | Trigger Engineer |
| `/api/tech-lead/trigger` | POST | Trigger Tech Lead |

## Agent Details

### Product Manager Agent

AI-powered feature discovery:
- Reads CLAUDE.md and understands each product deeply
- Analyzes competitive landscape and industry trends
- Identifies high-value feature opportunities
- Creates detailed feature specs with acceptance criteria
- Scores features by value (1-10) and effort (small/medium/large)

Creates GitHub Issues labeled `feature` and `backlog` for Engineers.

### Discovery Agent

Analyzes codebases to find technical debt:
- TODOs, FIXMEs, HACK comments
- Missing loading states
- Missing error handling
- Accessibility gaps (alt text, aria-labels)
- Console.log statements

Creates GitHub Issues labeled `backlog` for Engineers to pick from.

### Engineer Agent

1. Checks for Issues labeled `backlog` first
2. If backlog exists: implements the first issue
3. If backlog empty: discovers own work
4. Creates PR linked to issue (`Closes #XX`)

### Tech Lead Agent

Reviews PRs with strict criteria:
- Value score (1-10)
- Quality score (1-10)
- Bloat risk assessment
- Auto-rejects: failing CI, >15 files, test-only PRs

Actions: MERGE, REQUEST_CHANGES, or CLOSE

### Auditor Agent

Daily analysis:
- PR merge rate
- Common rejection reasons
- Agent performance patterns
- Generates insights for other agents

## File Structure

```
barbossa-engineer/
├── barbossa_product.py      # Product Manager agent (feature discovery)
├── barbossa_discovery.py    # Discovery agent (technical debt)
├── barbossa_simple.py       # Engineer agent
├── barbossa_tech_lead.py    # Tech Lead agent
├── barbossa_auditor.py      # Auditor agent
├── web_portal/
│   └── app_simple.py        # Flask web portal
├── config/
│   └── repositories.json    # Repo configurations
├── logs/                    # All session logs
├── sessions.json            # Session tracking
├── tech_lead_decisions.json # Review history
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Container image
├── entrypoint.sh            # Container startup
└── crontab                  # Cron schedule
```

## Troubleshooting

```bash
# Check container status
docker ps | grep barbossa

# View live logs
docker compose logs -f

# Check cron is running
docker exec barbossa crontab -l

# View recent session logs
ls -lt logs/ | head

# Test web portal
curl -u barbossa:Galleon6242 http://localhost:8443/api/status

# Restart
docker compose restart

# Full rebuild
docker compose down && docker compose build --no-cache && docker compose up -d
```

## License

MIT
