# Examples

Real-world usage scenarios and configurations.

---

## Basic Setup

### Single Repository

The simplest configuration - one repository with defaults:

```json
{
  "owner": "yourname",
  "repositories": [
    {
      "name": "my-app",
      "url": "https://github.com/yourname/my-app.git"
    }
  ]
}
```

This enables all agents with default schedules. Barbossa will:
- Find issues and create backlog items
- Implement fixes and features
- Review and merge PRs automatically

---

## Team Configurations

### Solo Developer

Run during work hours, review manually:

```json
{
  "owner": "yourname",
  "repositories": [
    {
      "name": "side-project",
      "url": "https://github.com/yourname/side-project.git",
      "package_manager": "pnpm"
    }
  ],
  "settings": {
    "tech_lead": {
      "auto_merge": false
    },
    "schedule": {
      "engineer": "0 9,12,15,18 * * 1-5",
      "tech_lead": "30 9,12,15,18 * * 1-5",
      "discovery": "0 10 * * 1-5",
      "product_manager": "0 11 * * 1"
    }
  }
}
```

**Note:** With `auto_merge: false`, Tech Lead will post approval comments but you merge manually.

### Small Team

Multiple repos, aggressive schedule, protected files:

```json
{
  "owner": "startup-inc",
  "repositories": [
    {
      "name": "frontend",
      "url": "https://github.com/startup-inc/frontend.git",
      "package_manager": "yarn",
      "do_not_touch": ["src/lib/analytics.ts"]
    },
    {
      "name": "backend",
      "url": "https://github.com/startup-inc/backend.git",
      "package_manager": "npm",
      "do_not_touch": ["src/auth/**", "prisma/migrations/"]
    }
  ],
  "settings": {
    "tech_lead": {
      "auto_merge": true,
      "min_lines_for_tests_required": 30,
      "max_files_per_pr": 10
    },
    "schedule": {
      "engineer": "every_2_hours",
      "tech_lead": "every_2_hours",
      "discovery": "4x_daily",
      "product_manager": "2x_daily"
    }
  }
}
```

---

## Framework-Specific

### Next.js App

```json
{
  "owner": "yourname",
  "repositories": [
    {
      "name": "nextjs-app",
      "url": "https://github.com/yourname/nextjs-app.git",
      "package_manager": "pnpm",
      "do_not_touch": [
        ".env*",
        "next.config.js",
        "middleware.ts"
      ]
    }
  ]
}
```

**Tip:** Add a `CLAUDE.md` to your repo with Next.js-specific context:

```markdown
# NextJS App

## Stack
- Next.js 14 with App Router
- TypeScript strict mode
- Tailwind CSS
- Prisma + PostgreSQL

## Conventions
- Server components by default
- Client components prefixed with 'use client'
- API routes in app/api/

## Do Not Touch
- Auth handled by NextAuth.js in middleware.ts
- Environment variables managed externally
```

### Python/FastAPI

```json
{
  "owner": "yourname",
  "repositories": [
    {
      "name": "api-service",
      "url": "https://github.com/yourname/api-service.git",
      "package_manager": "pip",
      "do_not_touch": [
        ".env*",
        "alembic/versions/"
      ]
    }
  ]
}
```

### Monorepo

```json
{
  "owner": "yourname",
  "repositories": [
    {
      "name": "monorepo",
      "url": "https://github.com/yourname/monorepo.git",
      "package_manager": "pnpm",
      "do_not_touch": [
        "packages/auth/**",
        "packages/database/migrations/**",
        "turbo.json"
      ]
    }
  ]
}
```

---

## Issue Tracking

### GitHub Issues (Default)

No configuration needed. Issues are created and tracked in GitHub.

### Linear Integration

```json
{
  "owner": "yourname",
  "issue_tracker": {
    "type": "linear",
    "linear": {
      "team_key": "ENG",
      "backlog_state": "Backlog"
    }
  },
  "repositories": [
    {
      "name": "app",
      "url": "https://github.com/yourname/app.git"
    }
  ]
}
```

Set the API key:

```bash
export LINEAR_API_KEY="lin_api_xxxx"
```

Linear issues automatically link to PRs via branch naming: `barbossa/ENG-42-fix-login-bug`

---

## Scheduling Patterns

### Business Hours Only

```json
{
  "settings": {
    "schedule": {
      "engineer": "0 9,11,14,16 * * 1-5",
      "tech_lead": "30 9,11,14,16 * * 1-5",
      "discovery": "0 10 * * 1,3,5",
      "product_manager": "0 15 * * 2"
    }
  }
}
```

Set timezone in docker-compose.yml:

```yaml
environment:
  - TZ=America/New_York
```

### Overnight Processing

Run when nobody's working:

```json
{
  "settings": {
    "schedule": {
      "engineer": "0 22,0,2,4,6 * * *",
      "tech_lead": "30 22,0,2,4,6 * * *",
      "discovery": "0 21 * * *",
      "product_manager": "0 20 * * 0"
    }
  }
}
```

### Minimal (Cost-Conscious)

```json
{
  "settings": {
    "schedule": {
      "engineer": "daily_morning",
      "tech_lead": "daily_morning",
      "discovery": "0 12 * * 1",
      "product_manager": "disabled"
    }
  }
}
```

---

## Quality Tuning

### Strict Mode

Higher bar for PR quality:

```json
{
  "settings": {
    "tech_lead": {
      "auto_merge": true,
      "min_lines_for_tests_required": 20,
      "max_files_per_pr": 8,
      "stale_pr_threshold": 3
    }
  }
}
```

### Relaxed Mode

For rapid prototyping:

```json
{
  "settings": {
    "tech_lead": {
      "auto_merge": true,
      "min_lines_for_tests_required": 100,
      "max_files_per_pr": 25,
      "stale_pr_threshold": 7
    }
  }
}
```

---

## Privacy Options

### Telemetry Disabled

```json
{
  "settings": {
    "telemetry": false
  }
}
```

Or via environment:

```bash
export BARBOSSA_ANALYTICS_OPT_OUT=true
```

---

## Common Workflows

### Adding Barbossa to Existing Project

1. Create `config/repositories.json` with your repo
2. Add `CLAUDE.md` to your repository root with project context
3. Create `backlog` label in GitHub (or use Linear)
4. Start Barbossa

Initial issues will be created by Discovery agent. Engineer picks them up automatically.

### Manual Triggering

Run any agent immediately:

```bash
# Create issues
docker exec barbossa barbossa run discovery

# Implement from backlog
docker exec barbossa barbossa run engineer

# Review pending PRs
docker exec barbossa barbossa run tech-lead

# Propose features
docker exec barbossa barbossa run product

# Health check
docker exec barbossa barbossa run auditor
```

### Checking Status

```bash
# Overall health
docker exec barbossa barbossa health

# Recent activity
docker exec barbossa barbossa status

# Agent logs
docker exec barbossa barbossa logs engineer
docker exec barbossa barbossa logs tech-lead
```

### Pausing Operations

```bash
# Stop all agents
docker compose stop

# Resume
docker compose start
```

---

## Troubleshooting Examples

### No PRs Being Created

Check for backlog issues:

```bash
# View pending issues
gh issue list --label backlog --repo yourname/repo

# Manual run with logs
docker exec barbossa barbossa run engineer
docker exec barbossa barbossa logs engineer
```

### PRs Keep Getting Rejected

Review the criteria:

```bash
# Check recent Tech Lead feedback
docker exec barbossa barbossa logs tech-lead
```

Common reasons:
- Missing tests (configure `min_lines_for_tests_required`)
- Too many files (configure `max_files_per_pr`)
- CI failures (fix your CI pipeline)

### Agents Not Running

```bash
# Check schedule
docker exec barbossa cat /app/crontab

# Check container logs
docker compose logs -f

# Validate configuration
docker exec barbossa python scripts/validate.py
```
