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

## Agent Settings

Control agent behavior:

```json
{
  "settings": {
    "max_open_prs": 5,

    "engineer": {
      "enabled": true
    },

    "tech_lead": {
      "enabled": true,
      "auto_merge": false,
      "min_lines_for_tests": 50,
      "max_files_per_pr": 15
    },

    "discovery": {
      "enabled": true,
      "max_backlog_issues": 20
    },

    "product_manager": {
      "enabled": false
    },

    "auditor": {
      "enabled": true,
      "analysis_days": 7
    }
  }
}
```

Disable agents you don't need.

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
