# Configuration

All configuration is in `config/repositories.json`.

---

## Minimal Config

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "https://github.com/your-github-username/my-app.git"
    }
  ]
}
```

That's it. Barbossa auto-detects everything else.

---

## Common Options

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "https://github.com/your-github-username/my-app.git",
      "package_manager": "pnpm",
      "do_not_touch": ["src/lib/auth.ts", "prisma/migrations/"]
    }
  ],
  "settings": {
    "telemetry": true,
    "tech_lead": {
      "auto_merge": true,
      "min_lines_for_tests": 50,
      "max_files_for_auto_review": 30,
      "stale_days": 5,
      "block_on_pending_checks": true,
      "pending_checks_timeout_hours": 6,
      "require_evidence": true,
      "require_lockfile_disclosure": true
    },
    "discovery": { "enabled": true, "precision_mode": "high" },
    "product_manager": { "enabled": true },
    "auditor": {
      "stale_issue_days": 0,
      "stale_issue_labels": ["discovery", "product", "feature"]
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `package_manager` | `npm`, `yarn`, `pnpm`, or `bun` (auto-detected if omitted) |
| `do_not_touch` | Files/directories agents should never modify |
| `telemetry` | `true` (default) or `false` to disable anonymous usage tracking |
| `auto_merge` | Enabled by default. Set to `false` for manual merge control |
| `min_lines_for_tests` | Minimum lines changed to require tests (default: 50) |
| `max_files_for_auto_review` | Maximum files for automated review (default: 30) |
| `stale_days` | Days before PR considered stale (default: 5) |
| `block_on_pending_checks` | Defer review while CI is pending (default: true) |
| `pending_checks_timeout_hours` | If CI stays pending longer than this, request changes instead of waiting (default: 6; set 0 to disable) |
| `require_evidence` | Require evidence in PR description (default: true) |
| `require_lockfile_disclosure` | Require lockfile disclosure in PR body (default: true) |
| `precision_mode` | Discovery signal quality: `high`, `balanced`, `experimental` (default: high) |
| `stale_issue_days` | Auto-close stale issues older than this many days (default: 0 = disabled) |
| `stale_issue_labels` | Only close stale issues that have one of these labels |
| `enabled` | Enable/disable individual agents |

---

Legacy keys (still supported): `min_lines_for_tests_required`, `max_files_per_pr`, `stale_pr_threshold`

---

## Failure Analyzer (Backoff)

Barbossa tracks repeated PR failures and can back off on retrying the same issue.

```json
{
  "settings": {
    "failure_analyzer": {
      "enabled": true,
      "retention_days": 90,
      "backoff_policy": {
        "skip_runs_after_failures": 1,
        "consecutive_failures_threshold": 2
      }
    }
  }
}
```

- `enabled`: Toggle failure tracking and backoff logic.
- `retention_days`: How long to keep failure history.
- `backoff_policy.skip_runs_after_failures`: Base skip period after consecutive failures (hours, exponential).
- `backoff_policy.consecutive_failures_threshold`: Failures required to activate backoff.

---

## Stale Issue Cleanup (Optional)

The Auditor can close stale issues to keep the backlog tidy. It only applies to issues
with labels in `stale_issue_labels`, so you can keep scope narrow (e.g., only Barbossa-created issues).
Currently supported for GitHub Issues only (skipped when using Linear).

```json
{
  "settings": {
    "auditor": {
      "stale_issue_days": 30,
      "stale_issue_labels": ["discovery", "product", "feature"]
    }
  }
}
```

## Repository-Specific Guidance

**New in v1.6.4:** Steer agent behavior per-repository using `focus` and `known_gaps` fields.

### Quality vs Feature Focus

Use the `focus` field to define the development philosophy for a repository:

```json
{
  "repositories": [
    {
      "name": "my-production-app",
      "url": "https://github.com/you/my-production-app.git",
      "focus": "QUALITY & RESILIENCE ONLY - Focus exclusively on: (1) Bug fixes and edge case handling, (2) Error handling and resilience, (3) Test coverage expansion, (4) Security improvements, (5) UI/UX polish, (6) Performance optimization. DO NOT implement large new features or major architectural changes.",
      "known_gaps": [
        "Missing error boundaries in React components - app crashes on unhandled errors",
        "Insufficient loading states - users see blank screens during data fetching",
        "Weak network error handling - transactions fail silently without retry logic",
        "Limited test coverage - critical payment flows lack E2E tests",
        "Accessibility issues - missing ARIA labels, poor keyboard navigation"
      ]
    }
  ]
}
```

Both fields are optional. Use `focus` to steer agents toward quality vs features, and `known_gaps` to list specific priorities.

---

## Scheduling

Agents run on optimized schedules to avoid resource contention and ensure fresh work is processed efficiently.

### Default Schedule

```json
{
  "settings": {
    "schedule": {
      "engineer": "every_2_hours",
      "tech_lead": "0 1,3,5,7,9,11,13,15,17,19,21,23 * * *",
      "discovery": "0 1,5,9,13,17,21 * * *",
      "product_manager": "0 3,11,19 * * *"
    }
  }
}
```

**What runs when:**

| Agent | Frequency | Times (UTC) | Purpose |
|-------|-----------|-------------|---------|
| **Engineer** | 12x daily | 00:00, 02:00, 04:00... | Implements features from backlog |
| **Tech Lead** | 12x daily | 01:00, 03:00, 05:00... | Reviews PRs (1h after engineer) |
| **Discovery** | 6x daily | 01:00, 05:00, 09:00, 13:00, 17:00, 21:00 | Finds issues & technical debt |
| **Product** | 3x daily | 03:00, 11:00, 19:00 | Suggests new features |
| **Auditor** | Daily | 06:30 | System health check |

### Why Offset Schedules?

1. **Avoids API rate limits** - agents don't hit Claude API simultaneously
2. **Fresh PR reviews** - Tech Lead runs after Engineer creates PRs
3. **Healthy backlog** - Discovery runs frequently to keep work queue stocked
4. **Resource efficiency** - No CPU/memory contention from parallel execution

### Custom Schedules

Use **presets**:

```json
{
  "schedule": {
    "engineer": "every_3_hours",
    "tech_lead": "every_3_hours",
    "discovery": "4x_daily",
    "product_manager": "2x_daily"
  }
}
```

Available presets:
- `every_hour`, `every_2_hours`, `every_3_hours`, `every_4_hours`, `every_6_hours`
- `4x_daily`, `3x_daily`, `2x_daily`
- `daily_morning`, `daily_evening`, `daily_night`

Or use **custom cron expressions**:

```json
{
  "schedule": {
    "engineer": "0 9,17 * * *",  // 9am and 5pm only
    "tech_lead": "30 9,17 * * *", // 30 min after engineer
    "discovery": "0 12 * * *",    // Noon daily
    "product_manager": "0 18 * * 1"  // 6pm Monday only
  }
}
```

### Disable Agents

```json
{
  "schedule": {
    "product_manager": "disabled"
  }
}
```

---

## Issue Tracking

Barbossa supports both **GitHub Issues** (default) and **Linear** for issue tracking.

### GitHub Issues (Default)

No configuration needed. Works out of the box with your GitHub repositories.

### Linear Integration

Use Linear instead of GitHub Issues for managing backlog and feature requests:

```json
{
  "owner": "your-github-username",
  "issue_tracker": {
    "type": "linear",
    "linear": {
      "team_key": "MUS",
      "backlog_state": "Backlog"
    }
  },
  "repositories": [...]
}
```

Set your Linear API key as an environment variable:

```bash
export LINEAR_API_KEY="lin_api_xxx"
```

Get your API key from [Linear Settings → API](https://linear.app/settings/api).

**What happens with Linear:**
- Discovery agent creates issues in your Linear team
- Product Manager proposes features in Linear
- Engineer pulls backlog from Linear workspace
- PRs auto-link to Linear issues via branch naming: `barbossa/MUS-14-feature`

| Field | Description |
|-------|-------------|
| `team_key` | Your Linear team key (e.g., "MUS", "ENG") |
| `backlog_state` | Workflow state name for backlog (default: "Backlog") |

**Startup validation:** Barbossa verifies Linear connectivity on startup and will fail fast if:
- `LINEAR_API_KEY` is not set
- Team doesn't exist
- API is unreachable

---

## Webhook Notifications

**New in v1.7.0:** Get real-time insights into Barbossa's operations via Discord webhooks (Slack support coming soon).

### Basic Setup

```json
{
  "settings": {
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/your-webhook-url"
    }
  }
}
```

### Getting a Discord Webhook URL

1. Open Discord and go to the channel where you want notifications
2. Click the gear icon (Edit Channel) → **Integrations** → **Webhooks**
3. Click **New Webhook** and copy the webhook URL
4. Paste the URL in your `repositories.json` config

### Customizing Notifications

Control which events trigger notifications:

```json
{
  "settings": {
    "notifications": {
      "enabled": true,
      "discord_webhook": "https://discord.com/api/webhooks/...",
      "notify_on": {
        "run_complete": true,
        "pr_created": true,
        "pr_merged": true,
        "pr_closed": false,
        "error": true
      }
    }
  }
}
```

### Notification Types

| Event | Default | Description |
|-------|---------|-------------|
| `run_complete` | `true` | Summary when any agent finishes a run |
| `pr_created` | `true` | When Engineer creates a new PR |
| `pr_merged` | `true` | When Tech Lead merges a PR (includes scores) |
| `pr_closed` | `false` | When Tech Lead closes a PR |
| `error` | `true` | When any agent encounters an error |

---

## Multiple Repos

```json
{
  "owner": "your-username",
  "repositories": [
    { "name": "frontend", "url": "https://github.com/you/frontend.git" },
    { "name": "backend", "url": "https://github.com/you/backend.git" }
  ]
}
```

---

## Spec Mode (Product Specifications)

**New in v1.8.0:** Spec Mode transforms Barbossa from autonomous development into a Product AI that generates detailed feature specifications.

### How It Works

When `spec_mode.enabled = true`:
- All autonomous agents are **disabled** (Engineer, Tech Lead, Discovery, Product, Auditor)
- Only the **Spec Generator** runs
- Generates cross-repo specifications for linked repository groups ("products")
- Creates distributed tickets: parent spec + child implementation tickets

### Configuration

```json
{
  "settings": {
    "spec_mode": {
      "enabled": true,
      "schedule": "0 9 * * *",
      "max_specs_per_run": 2,
      "deduplication_days": 14,
      "min_value_score": 7,
      "spec_label": "spec",
      "implementation_label": "backlog"
    }
  },
  "products": [
    {
      "name": "my-platform",
      "description": "Full-stack platform with API and web frontend",
      "repositories": ["backend-api", "frontend-web"],
      "primary_repo": "frontend-web",
      "context": {
        "vision": "Become the leading platform for X",
        "current_phase": "MVP hardening - focus on reliability",
        "target_users": "Small business owners",
        "constraints": [
          "Must support mobile browsers",
          "API response time < 200ms"
        ],
        "strategy_notes": [
          "BD feedback: Users want faster onboarding",
          "Q1 focus is enterprise features"
        ],
        "known_integrations": {
          "backend-api": "REST API - user management, data storage",
          "frontend-web": "React SPA - dashboard and settings"
        }
      }
    }
  ]
}
```

### Spec Mode Settings

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | **Global switch** - when true, disables all other agents |
| `schedule` | `0 9 * * *` | Cron schedule for spec generation |
| `max_specs_per_run` | `2` | Maximum specs to generate per run |
| `deduplication_days` | `14` | Days to check for duplicate specs |
| `min_value_score` | `7` | Minimum value score (1-10) to create a spec |
| `spec_label` | `spec` | Label for parent spec tickets |
| `implementation_label` | `backlog` | Label for child implementation tickets |

### Product Configuration

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Product identifier |
| `description` | No | Human-readable description |
| `repositories` | Yes | List of linked repository names |
| `primary_repo` | Yes | Where parent spec tickets are created |
| `context.vision` | No | Product vision statement |
| `context.current_phase` | No | Current development phase |
| `context.target_users` | No | Target user description |
| `context.constraints` | No | Technical/business constraints |
| `context.strategy_notes` | No | Strategic context (BD feedback, etc.) |
| `context.known_integrations` | No | How each repo fits in the system |

### Switching Modes

```json
// Autonomous Mode (default)
"spec_mode": { "enabled": false }

// Spec Mode
"spec_mode": { "enabled": true }
```

Restart Barbossa after changing modes to regenerate the crontab.

---

## Timezone

Set the `TZ` environment variable in docker-compose.yml to control when agents run. Default is `UTC`.

```yaml
environment:
  - TZ=Europe/London
```

### Common Timezones

| Region | Timezone |
|--------|----------|
| US Pacific | `America/Los_Angeles` |
| US Mountain | `America/Denver` |
| US Central | `America/Chicago` |
| US Eastern | `America/New_York` |
| UK | `Europe/London` |
| Central Europe | `Europe/Berlin` |
| Eastern Europe | `Europe/Kiev` |
| India | `Asia/Kolkata` |
| Singapore | `Asia/Singapore` |
| Japan | `Asia/Tokyo` |
| Australia East | `Australia/Sydney` |
| New Zealand | `Pacific/Auckland` |

Full list: [IANA Time Zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

---

## Privacy & Telemetry

Anonymous usage statistics are collected by default. No identifying information is ever sent.

Opt out in config:

```json
{
  "settings": {
    "telemetry": false
  }
}
```

Or via environment: `export BARBOSSA_ANALYTICS_OPT_OUT=true`

See [Firebase & Analytics](firebase.html) for details.
