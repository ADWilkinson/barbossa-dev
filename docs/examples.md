# Examples

## Solo developer

Work hours only, manual merge:

```json
{
  "owner": "yourname",
  "repositories": [
    {
      "name": "side-project",
      "url": "https://github.com/yourname/side-project.git"
    }
  ],
  "settings": {
    "tech_lead": { "auto_merge": false },
    "schedule": {
      "engineer": "0 9,12,15,18 * * 1-5",
      "tech_lead": "30 9,12,15,18 * * 1-5",
      "discovery": "0 10 * * 1-5",
      "product_manager": "disabled"
    }
  }
}
```

## Startup team

Multiple repos, aggressive schedule:

```json
{
  "owner": "startup-inc",
  "repositories": [
    {
      "name": "frontend",
      "url": "https://github.com/startup-inc/frontend.git",
      "do_not_touch": ["src/lib/analytics.ts"]
    },
    {
      "name": "backend",
      "url": "https://github.com/startup-inc/backend.git",
      "do_not_touch": ["src/auth/**", "prisma/migrations/"]
    }
  ],
  "settings": {
    "schedule": {
      "engineer": "every_2_hours",
      "tech_lead": "every_2_hours",
      "discovery": "4x_daily",
      "product_manager": "2x_daily"
    },
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/..."
    }
  }
}
```

## Overnight processing

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

## Quality focus

Steer agents toward bug fixes, not new features:

```json
{
  "repositories": [
    {
      "name": "production-app",
      "url": "https://github.com/you/production-app.git",
      "focus": "Bug fixes and resilience only. No new features."
    }
  ]
}
```

## Cross-repo specs

Generate feature specs across multiple repos:

```json
{
  "repositories": [
    { "name": "backend", "url": "https://github.com/you/backend.git" },
    { "name": "frontend", "url": "https://github.com/you/frontend.git" }
  ],
  "products": [
    {
      "name": "my-platform",
      "repositories": ["backend", "frontend"],
      "primary_repo": "frontend",
      "context": {
        "vision": "Best-in-class platform for X",
        "constraints": ["Mobile support required", "API < 200ms"]
      }
    }
  ],
  "settings": {
    "spec_mode": { "enabled": true }
  }
}
```

## Commands

```bash
# Manual runs
docker exec barbossa barbossa run engineer
docker exec barbossa barbossa run tech-lead
docker exec barbossa barbossa run discovery

# Status
docker exec barbossa barbossa health
docker exec barbossa barbossa status
docker exec barbossa barbossa logs engineer

# Pause/resume
docker compose stop
docker compose start
```
