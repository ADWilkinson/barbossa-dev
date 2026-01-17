# Examples

## Full autonomous setup

All agents running, Discord notifications, protected files:

```json
{
  "owner": "yourname",
  "repositories": [
    {
      "name": "my-app",
      "url": "https://github.com/yourname/my-app.git",
      "do_not_touch": ["src/auth/**", ".env*", "prisma/migrations/"]
    }
  ],
  "settings": {
    "tech_lead": {
      "auto_merge": true,
      "min_lines_for_tests": 50
    },
    "schedule": {
      "engineer": "every_2_hours",
      "tech_lead": "every_2_hours",
      "discovery": "4x_daily",
      "product_manager": "3x_daily"
    },
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/...",
      "notify_on": {
        "pr_created": true,
        "pr_merged": true,
        "error": true
      }
    }
  }
}
```

## Manual review mode

Review PRs yourself before merging:

```json
{
  "settings": {
    "tech_lead": { "auto_merge": false }
  }
}
```

## Work hours only

Agents run 9-6 on weekdays:

```json
{
  "settings": {
    "schedule": {
      "engineer": "0 9,12,15,18 * * 1-5",
      "tech_lead": "30 9,12,15,18 * * 1-5",
      "discovery": "0 10 * * 1,3,5",
      "product_manager": "0 14 * * 2,4"
    }
  }
}
```

## Bug fixes only

Steer agents away from new features:

```json
{
  "repositories": [{
    "name": "production-app",
    "url": "https://github.com/you/production-app.git",
    "focus": "Bug fixes and resilience only. No new features or refactoring."
  }]
}
```

## Disable specific agents

Turn off Product Manager, keep others:

```json
{
  "settings": {
    "product_manager": { "enabled": false }
  }
}
```

## Multiple repos

Frontend and backend with different protections:

```json
{
  "owner": "company",
  "repositories": [
    {
      "name": "frontend",
      "url": "https://github.com/company/frontend.git",
      "do_not_touch": ["src/analytics/**"]
    },
    {
      "name": "backend",
      "url": "https://github.com/company/backend.git",
      "do_not_touch": ["src/auth/**", "migrations/"]
    }
  ]
}
```

## Spec Mode

Generate cross-repo feature specs instead of code:

```json
{
  "owner": "company",
  "repositories": [
    { "name": "api", "url": "https://github.com/company/api.git" },
    { "name": "web", "url": "https://github.com/company/web.git" },
    { "name": "mobile", "url": "https://github.com/company/mobile.git" }
  ],
  "products": [{
    "name": "platform",
    "repositories": ["api", "web", "mobile"],
    "primary_repo": "web",
    "context": {
      "vision": "Best-in-class platform for X",
      "current_phase": "MVP hardening",
      "constraints": ["API < 200ms", "Mobile-first"],
      "strategy_notes": ["Users want faster onboarding"]
    }
  }],
  "settings": {
    "spec_mode": { "enabled": true }
  }
}
```

## Stale issue cleanup

Auto-close old Barbossa-created issues:

```json
{
  "settings": {
    "auditor": {
      "stale_issue_days": 30,
      "stale_issue_labels": ["discovery", "product"]
    }
  }
}
```
