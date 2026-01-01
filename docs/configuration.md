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
      "min_lines_for_tests_required": 50,
      "max_files_per_pr": 15,
      "stale_pr_threshold": 5
    },
    "discovery": { "enabled": true },
    "product_manager": { "enabled": true }
  }
}
```

| Field | Description |
|-------|-------------|
| `package_manager` | `npm`, `yarn`, `pnpm`, or `bun` (auto-detected if omitted) |
| `do_not_touch` | Files/directories agents should never modify |
| `telemetry` | `true` (default) or `false` to disable anonymous usage tracking |
| `auto_merge` | Enabled by default. Set to `false` for manual merge control |
| `min_lines_for_tests_required` | Minimum lines changed to require tests (default: 50) |
| `max_files_per_pr` | Maximum files allowed in a PR (default: 15) |
| `stale_pr_threshold` | Days before PR considered stale (default: 5) |
| `enabled` | Enable/disable individual agents |

---

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

### How It Works

**`focus` (string):**
- Injected into Engineer and Product Manager prompts
- Guides agents toward quality/polish vs new features
- Product Manager respects focus and may decline feature suggestions
- Engineer prioritizes work aligned with focus

**`known_gaps` (array):**
- List of specific known issues and priority areas
- Shown to Engineer as high-priority opportunities
- Product Manager uses these to inform feature suggestions
- Discovery agent may also reference these areas

### Examples

**Production hardening:**
```json
{
  "focus": "QUALITY & RESILIENCE ONLY - bug fixes, testing, security, polish",
  "known_gaps": [
    "Missing error boundaries",
    "No retry logic for network failures",
    "Insufficient test coverage"
  ]
}
```

**Exploration phase:**
```json
{
  "focus": "FEATURE EXPLORATION - Rapidly experiment with new features and UX improvements. Focus on shipping MVPs quickly.",
  "known_gaps": [
    "No analytics dashboard",
    "Missing admin panel",
    "No user preferences system"
  ]
}
```

**Balanced approach:**
```json
{
  "focus": "Small incremental improvements - Focus on polish, bug fixes, and minor features. Keep PRs focused and well-tested.",
  "known_gaps": [
    "Export functionality incomplete",
    "Mobile responsiveness issues on tablets",
    "Performance bottlenecks on large datasets"
  ]
}
```

### When to Use

- **Quality focus:** Production apps needing stability and polish
- **Feature focus:** New projects or prototypes in exploration phase
- **Known gaps:** Clear list of issues you want agents to prioritize

### Backward Compatibility

Both fields are **optional**. Repositories without `focus` or `known_gaps` work normally with default agent behavior.

---

## Protected Files

**Warning:** Always protect auth, migrations, and config files from AI modification.

Always protect sensitive code:

```json
{
  "do_not_touch": [
    ".env*",
    "src/lib/auth.ts",
    "prisma/migrations/"
  ]
}
```

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

### What You'll See

**Agent Run Summaries:**
- Engineer: "Created 2 PR(s) across 3 repositories"
- Tech Lead: "Reviewed 4 PR(s): 2 merged, 1 needs changes"
- Discovery: "Created 5 backlog issue(s)"
- Auditor: "System health: 85/100 (healthy)"

**PR Events:**
- New PR created with link and title
- PR merged with value/quality scores
- PR closed with reason

**Error Alerts:**
- Agent name and error context
- Repository name
- Error message

### Design Principles

- **Never blocks:** Notifications run in background threads and never slow down agents
- **Graceful degradation:** If Discord is unreachable, agents continue working
- **Not spammy:** Only meaningful events are sent (not every action)
- **Rich formatting:** Discord embeds with agent-specific colors and emojis

### Agent Colors

Each agent has a distinctive color in Discord embeds:
- **Engineer:** Blue
- **Tech Lead:** Purple
- **Discovery:** Orange
- **Product Manager:** Pink
- **Auditor:** Yellow

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

Barbossa uses a hybrid telemetry system (Google Analytics 4 + Firebase Cloud Functions) to improve the project while respecting your privacy.

**What's collected:**
- Anonymous installation ID (SHA256 hash, not reversible)
- Agent run counts and success rates
- Version number and agent types
- Run metadata (timestamps, success/failure booleans)

**What's NOT collected:**
- Repository names, URLs, or any identifying information
- Code content, diffs, or file contents
- GitHub usernames or organization names
- PR/issue titles, descriptions, or any repository data
- Your configuration settings or secrets

All telemetry is optional and has 5-second timeouts to ensure it never blocks execution.

### Opting Out

Set `telemetry` to `false` in your config:

```json
{
  "settings": {
    "telemetry": false
  }
}
```

Or via environment variable:

```bash
export BARBOSSA_ANALYTICS_OPT_OUT=true
```

**Full details:** See [Firebase & Analytics](firebase.html) for complete technical documentation.
