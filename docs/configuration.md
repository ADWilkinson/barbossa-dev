# Configuration Reference

Complete reference for `config/repositories.json`.

## Overview

Barbossa reads its configuration from `config/repositories.json`. This file defines:
- Which repositories to work on
- How each repository is structured
- What areas to focus on or avoid
- Agent behavior settings

## Basic Structure

```json
{
  "owner": "github-username",
  "repositories": [...],
  "schedule": "every_2_hours",
  "version": "3.0.0"
}
```

## Top-Level Fields

| Field | Required | Description |
|-------|----------|-------------|
| `owner` | Yes | Your GitHub username or organization |
| `repositories` | Yes | Array of repository configurations |
| `schedule` | No | Default schedule (default: `every_2_hours`) |
| `version` | No | Config version for compatibility |

## Repository Configuration

Each repository in the `repositories` array can have:

### Required Fields

```json
{
  "name": "my-app",
  "url": "git@github.com:username/my-app.git"
}
```

| Field | Description |
|-------|-------------|
| `name` | Repository name (used for identification) |
| `url` | Git clone URL (SSH or HTTPS) |

### Package Manager

```json
{
  "package_manager": "npm",
  "env_file": ".env.local"
}
```

| Field | Options | Description |
|-------|---------|-------------|
| `package_manager` | `npm`, `yarn`, `pnpm`, `bun` | Package manager to use |
| `env_file` | String | Environment file name (default: `.env`) |

### Project Description

```json
{
  "description": "SaaS application for project management",
  "tech_stack": {
    "framework": "Next.js 14 (App Router)",
    "language": "TypeScript",
    "styling": "Tailwind CSS",
    "database": "Prisma + PostgreSQL",
    "testing": "Vitest + Playwright"
  }
}
```

The `description` and `tech_stack` help agents understand your project context.

### Architecture

```json
{
  "architecture": {
    "data_flow": "API routes → Services → Database",
    "key_dirs": [
      "src/components/ - UI components",
      "src/lib/ - Shared utilities",
      "src/app/ - Next.js routes"
    ]
  }
}
```

Helps agents navigate your codebase effectively.

### Design System

```json
{
  "design_system": {
    "aesthetic": "Modern minimal with subtle shadows",
    "component_library": "shadcn/ui",
    "rules": [
      "Use shadcn/ui components where possible",
      "No inline styles - use Tailwind classes",
      "Consistent spacing: p-4 for cards, gap-4 for layouts"
    ]
  }
}
```

Ensures agents follow your design patterns.

### Protected Areas

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

Files or directories agents should never modify. Critical for:
- Authentication logic
- Payment processing
- Database migrations
- Sensitive configuration

### Focus Areas

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

Guides what improvements agents should prioritize.

### Example PRs

```json
{
  "example_good_prs": [
    "Add unit tests for a component",
    "Improve mobile responsiveness",
    "Add error handling to API routes"
  ]
}
```

Shows agents what kind of PRs you want.

## Complete Example

```json
{
  "owner": "your-username",
  "repositories": [
    {
      "name": "my-saas-app",
      "url": "git@github.com:your-username/my-saas-app.git",
      "package_manager": "npm",
      "env_file": ".env.local",
      "description": "SaaS application for project management with team collaboration features",
      "tech_stack": {
        "framework": "Next.js 14 (App Router)",
        "language": "TypeScript",
        "styling": "Tailwind CSS",
        "database": "Prisma + PostgreSQL",
        "testing": "Vitest + Playwright"
      },
      "architecture": {
        "data_flow": "Client → API Routes → Services → Database",
        "key_dirs": [
          "src/components/ - React components",
          "src/lib/ - Shared utilities and services",
          "src/app/ - Next.js App Router pages",
          "src/app/api/ - API routes"
        ]
      },
      "design_system": {
        "aesthetic": "Modern minimal with subtle shadows",
        "component_library": "shadcn/ui",
        "rules": [
          "Use shadcn/ui components",
          "No inline styles",
          "Consistent spacing with Tailwind"
        ]
      },
      "do_not_touch": [
        "src/lib/auth.ts",
        "src/lib/stripe.ts",
        "prisma/migrations/",
        ".env*",
        "package-lock.json"
      ],
      "focus_areas": [
        "Improve test coverage",
        "Add loading states to async operations",
        "Fix accessibility issues",
        "Remove console.log statements"
      ],
      "example_good_prs": [
        "Add unit tests for UserProfile component",
        "Add loading skeleton to dashboard",
        "Improve mobile responsiveness of sidebar"
      ]
    }
  ],
  "schedule": "every_2_hours",
  "version": "3.0.0"
}
```

## Environment Variables

Set in `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token |
| `TZ` | No | Timezone (default: `UTC`) |

## JSON Schema

A JSON Schema is available at `config/repositories.schema.json` for validation and IDE autocomplete.

## Tips

### Multiple Repositories

You can configure multiple repositories:

```json
{
  "owner": "your-username",
  "repositories": [
    { "name": "frontend", "url": "..." },
    { "name": "backend", "url": "..." },
    { "name": "mobile", "url": "..." }
  ]
}
```

Barbossa will work on each in sequence.

### Monorepo Support

For monorepos, configure the root and specify key directories:

```json
{
  "name": "monorepo",
  "url": "git@github.com:org/monorepo.git",
  "architecture": {
    "key_dirs": [
      "packages/web/ - Web application",
      "packages/api/ - API server",
      "packages/shared/ - Shared utilities"
    ]
  }
}
```

### Strict Design Enforcement

For strict design systems, be explicit:

```json
{
  "design_system": {
    "rules": [
      "NEVER use border-radius (square corners only)",
      "ONLY use colors from tokens/colors.css",
      "ALL buttons must use Button component from ui/"
    ]
  }
}
```
