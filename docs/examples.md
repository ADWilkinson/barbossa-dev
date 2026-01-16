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
      "min_lines_for_tests": 30,
      "max_files_for_auto_review": 10
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

## Notifications

### Discord Webhook

Get real-time updates in your Discord channel:

```json
{
  "settings": {
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/your-webhook-url",
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

To get a Discord webhook URL:
1. Discord channel → Edit Channel → Integrations → Webhooks
2. Click "New Webhook" and copy the URL

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

## Spec Mode

### Product Specification Generation

Use Spec Mode to generate detailed cross-repo feature specifications instead of autonomous development:

```json
{
  "owner": "yourname",
  "repositories": [
    {
      "name": "backend-api",
      "url": "https://github.com/yourname/backend-api.git"
    },
    {
      "name": "frontend-web",
      "url": "https://github.com/yourname/frontend-web.git"
    },
    {
      "name": "mobile-app",
      "url": "https://github.com/yourname/mobile-app.git"
    }
  ],
  "products": [
    {
      "name": "my-platform",
      "description": "Full-stack platform with web and mobile clients",
      "repositories": ["backend-api", "frontend-web", "mobile-app"],
      "primary_repo": "frontend-web",
      "context": {
        "vision": "Become the leading platform for X",
        "current_phase": "MVP hardening - focus on reliability and UX",
        "target_users": "Small business owners needing Y",
        "constraints": [
          "Must support mobile browsers",
          "API response time < 200ms",
          "Keep bundle size under 500KB"
        ],
        "strategy_notes": [
          "BD feedback: Users want faster onboarding",
          "Competitors are adding multi-language support"
        ],
        "known_integrations": {
          "backend-api": "REST API - user management, data storage, auth",
          "frontend-web": "React SPA - user dashboard and settings",
          "mobile-app": "React Native - mobile experience"
        }
      }
    }
  ],
  "settings": {
    "spec_mode": {
      "enabled": true,
      "schedule": "0 9 * * *",
      "max_specs_per_run": 2,
      "min_value_score": 7
    }
  }
}
```

**What happens:**
- Spec Generator runs daily at 09:00
- Creates parent spec tickets in `frontend-web` with `spec` label
- Creates child implementation tickets in each affected repo with `backlog` label
- Each ticket is prompt-ready for AI implementation

### Switching Between Modes

```json
// Enable Spec Mode (disables all other agents)
"spec_mode": { "enabled": true }

// Disable Spec Mode (enables all autonomous agents)
"spec_mode": { "enabled": false }
```

Restart Barbossa after changing modes.

---

## Common Workflows

### Adding Barbossa to Existing Project

1. Create `config/repositories.json` with your repo
2. Add `CLAUDE.md` to your repository root with project context
3. Create `backlog` label in GitHub
4. Start Barbossa

Initial issues will be created by Discovery agent. Engineer picks them up automatically.

### Manual Triggering

Run any agent immediately:

```bash
# Autonomous mode agents
docker exec barbossa barbossa run discovery    # Create issues
docker exec barbossa barbossa run engineer     # Implement from backlog
docker exec barbossa barbossa run tech-lead    # Review pending PRs
docker exec barbossa barbossa run product      # Propose features
docker exec barbossa barbossa run auditor      # Health check

# Spec mode agent
docker exec barbossa barbossa run spec                        # All products
docker exec barbossa barbossa run spec --product my-platform  # Specific product
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

For troubleshooting, see [Troubleshooting](troubleshooting.html).
