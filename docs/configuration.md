# Configuration

All config lives in `config/repositories.json`.

## Minimal

```json
{
  "owner": "your-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "https://github.com/your-username/my-app.git"
    }
  ]
}
```

## Full example

```json
{
  "owner": "your-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "https://github.com/your-username/my-app.git",
      "package_manager": "pnpm",
      "do_not_touch": ["src/auth/**", "prisma/migrations/"]
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
      "product_manager": "2x_daily"
    },
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/..."
    }
  }
}
```

## Repository options

| Field | Description |
|-------|-------------|
| `name` | Repository identifier |
| `url` | Git clone URL |
| `package_manager` | `npm`, `yarn`, `pnpm`, `bun` (auto-detected) |
| `do_not_touch` | Paths agents won't modify |
| `focus` | Steering prompt (e.g., "quality only, no new features") |

## Tech Lead options

| Field | Default | Description |
|-------|---------|-------------|
| `auto_merge` | `true` | Merge approved PRs automatically |
| `min_lines_for_tests` | `50` | Lines changed before tests required |
| `max_files_for_auto_review` | `30` | Max files for automated review |
| `stale_days` | `5` | Days before PR marked stale |

## Disable agents

```json
{
  "settings": {
    "discovery": { "enabled": false },
    "product_manager": { "enabled": false }
  }
}
```

Or use schedule: `"product_manager": "disabled"`

## Schedule presets

```
every_hour, every_2_hours, every_3_hours, every_4_hours, every_6_hours
4x_daily, 3x_daily, 2x_daily
daily_morning, daily_evening
disabled
```

Or use cron: `"0 9,17 * * *"` (9am and 5pm)

## Notifications

Discord webhooks for PR events:

```json
{
  "settings": {
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/...",
      "notify_on": {
        "pr_created": true,
        "pr_merged": true,
        "pr_closed": false,
        "error": true
      }
    }
  }
}
```

Get webhook URL: Discord channel → Edit → Integrations → Webhooks → New Webhook

## Stale issue cleanup

Auditor can auto-close old Barbossa-created issues:

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

Only closes issues with matching labels. Set `stale_issue_days: 0` to disable.

## Spec Mode

Generate feature specs instead of code:

```json
{
  "products": [
    {
      "name": "my-platform",
      "repositories": ["backend", "frontend"],
      "primary_repo": "frontend",
      "context": {
        "vision": "Leading platform for X",
        "constraints": ["Mobile support", "API < 200ms"]
      }
    }
  ],
  "settings": {
    "spec_mode": { "enabled": true }
  }
}
```

When enabled, all other agents stop. Only Spec Generator runs.

## Timezone

Set `TZ` in docker-compose.yml:

```yaml
environment:
  - TZ=America/New_York
```

## Telemetry

Opt out:

```json
{ "settings": { "telemetry": false } }
```

Or: `export BARBOSSA_ANALYTICS_OPT_OUT=true`
