# Configuration Reference

Complete reference for `config/repositories.json`.

---

## Quick Start - Minimal Config

You only need **3 fields** to get started:

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

That's it! Barbossa will figure out the rest.

---

## Configuration Tiers

### Tier 1: Minimal (Required)

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

### Tier 2: Recommended (Better Results)

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "git@github.com:your-github-username/my-app.git",
      "package_manager": "pnpm",
      "description": "My SaaS application for X",
      "do_not_touch": ["src/lib/auth.ts", "prisma/migrations/"],
      "focus_areas": ["Improve test coverage", "Add loading states"]
    }
  ]
}
```

### Tier 3: Full Control

See `config/repositories.advanced.json.example` for all options.

---

## Field Reference

### Required Fields

| Field | Description |
|-------|-------------|
| `owner` | Your GitHub username or organization |
| `repositories` | Array of repository configurations |
| `repositories[].name` | Repository name |
| `repositories[].url` | Git clone URL (SSH or HTTPS) |

### Recommended Fields

| Field | Default | Description |
|-------|---------|-------------|
| `package_manager` | `npm` | Package manager: `npm`, `yarn`, `pnpm`, `bun` |
| `description` | - | Brief project description for context |
| `do_not_touch` | `[]` | Files/directories agents should never modify |
| `focus_areas` | `[]` | What improvements to prioritize |

### Advanced Fields

| Field | Description |
|-------|-------------|
| `env_file` | Environment file name (default: `.env`) |
| `tech_stack` | Object describing framework, language, styling |
| `architecture` | Object with `data_flow` and `key_dirs` |
| `design_system` | Object with `aesthetic` and `brand_rules` |
| `example_good_prs` | Examples of desired PR types |

---

## Protected Files (do_not_touch)

**Critical for safety.** Files listed here will never be modified:

```json
{
  "do_not_touch": [
    "src/lib/auth.ts",
    "src/lib/stripe.ts",
    "prisma/migrations/",
    ".env*"
  ]
}
```

Use this for:
- Authentication logic
- Payment processing
- Database migrations
- Sensitive configuration

---

## Focus Areas

Guide what improvements agents should prioritize:

```json
{
  "focus_areas": [
    "Improve test coverage for components",
    "Add loading and error states",
    "Fix accessibility issues",
    "Remove console.log statements"
  ]
}
```

---

## Tech Stack

Help agents understand your project:

```json
{
  "tech_stack": {
    "framework": "Next.js 14 (App Router)",
    "language": "TypeScript",
    "styling": "Tailwind CSS",
    "database": "Prisma + PostgreSQL",
    "testing": "Vitest + Playwright"
  }
}
```

---

## Design System

Enforce design consistency:

```json
{
  "design_system": {
    "aesthetic": "Modern minimal with subtle shadows",
    "brand_rules": [
      "Use shadcn/ui components",
      "No inline styles",
      "Consistent spacing with Tailwind"
    ]
  }
}
```

For strict enforcement:

```json
{
  "design_system": {
    "brand_rules": [
      "NEVER use border-radius (square corners only)",
      "ONLY use colors from tokens/colors.css",
      "ALL buttons must use Button component"
    ]
  }
}
```

---

## Architecture

Help agents navigate your codebase:

```json
{
  "architecture": {
    "data_flow": "Client -> Server Actions -> Prisma -> PostgreSQL",
    "key_dirs": [
      "src/app/ - Next.js routes",
      "src/components/ - React components",
      "src/lib/ - Shared utilities"
    ]
  }
}
```

---

## Multiple Repositories

Configure multiple repos:

```json
{
  "owner": "your-username",
  "repositories": [
    { "name": "frontend", "url": "git@github.com:you/frontend.git" },
    { "name": "backend", "url": "git@github.com:you/backend.git" },
    { "name": "mobile", "url": "git@github.com:you/mobile.git" }
  ]
}
```

Barbossa works on each in sequence.

---

## Schedule Settings

Customize when agents run:

```json
{
  "settings": {
    "schedule": {
      "engineer": "every_2_hours",
      "tech_lead": "35 0,2,4,6,8,10,12,14,16,18,20,22 * * *",
      "discovery": "4x_daily",
      "product_manager": "3x_daily",
      "auditor": "30 6 * * *"
    }
  }
}
```

### Schedule Presets

Use these presets or raw cron expressions:

| Preset | Cron | Description |
|--------|------|-------------|
| `every_hour` | `0 * * * *` | Every hour at :00 |
| `every_2_hours` | `0 0,2,4,...22 * * *` | Every 2 hours |
| `every_3_hours` | `0 0,3,6,...21 * * *` | Every 3 hours |
| `every_4_hours` | `0 0,4,8,...20 * * *` | Every 4 hours |
| `every_6_hours` | `0 0,6,12,18 * * *` | 4x daily |
| `2x_daily` | `0 9,18 * * *` | Twice daily (9am, 6pm) |
| `3x_daily` | `0 7,15,23 * * *` | Three times daily |
| `4x_daily` | `0 0,6,12,18 * * *` | Four times daily |
| `daily_morning` | `0 9 * * *` | Daily at 9am |
| `daily_evening` | `0 18 * * *` | Daily at 6pm |
| `disabled` | - | Don't run this agent |

Or use raw cron: `"30 9 * * *"` = daily at 09:30

### Default Schedule

| Agent | Default | Description |
|-------|---------|-------------|
| Engineer | `every_2_hours` | Every 2 hours at :00 |
| Tech Lead | 35 min after engineer | Every 2 hours at :35 |
| Discovery | `4x_daily` | 00:00, 06:00, 12:00, 18:00 |
| Product Manager | `3x_daily` | 07:00, 15:00, 23:00 |
| Auditor | `30 6 * * *` | Daily at 06:30 |

---

## Agent Settings

Control agent behavior:

```json
{
  "settings": {
    "engineer": {
      "enabled": true
    },

    "tech_lead": {
      "enabled": true,
      "auto_merge": true,
      "min_lines_for_tests": 50,
      "min_lines_for_ui_tests": 30,
      "max_files_per_pr": 15,
      "stale_days": 5
    },

    "discovery": {
      "enabled": true,
      "max_backlog_issues": 20
    },

    "product_manager": {
      "enabled": true,
      "max_issues_per_run": 3,
      "max_feature_issues": 20
    },

    "auditor": {
      "enabled": true,
      "analysis_days": 7
    }
  }
}
```

### Tech Lead Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable the tech lead agent |
| `auto_merge` | `true` | Auto-merge approved PRs |
| `min_lines_for_tests` | `50` | Require tests for PRs with more lines |
| `min_lines_for_ui_tests` | `30` | Require tests for UI changes with more lines |
| `max_files_per_pr` | `15` | Reject PRs touching more files (scope creep) |
| `stale_days` | `5` | Auto-close PRs older than this many days |

### Discovery Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable discovery agent |
| `max_backlog_issues` | `20` | Stop creating issues when backlog is full |

### Product Manager Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable product manager agent |
| `max_issues_per_run` | `3` | Max feature issues to create per run |
| `max_feature_issues` | `20` | Stop when this many feature issues exist |

Disable agents you don't need by setting `enabled: false`.

---

## Environment Variables

Set in `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token |
| `TZ` | No | Timezone (default: `UTC`) |

---

## Example Files

- `config/repositories.json.example` - Minimal config
- `config/repositories.advanced.json.example` - Full config with all options

---

## Tips

1. **Start minimal** - Add fields only as needed
2. **Protect critical files** - Always set `do_not_touch`
3. **Be specific with focus areas** - Vague guidance = vague PRs
4. **Use SSH URLs for private repos** - HTTPS may have auth issues
