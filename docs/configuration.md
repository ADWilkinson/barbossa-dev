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

## Protected Files

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

Barbossa collects anonymous usage data to improve the project:

**What's collected:**
- Anonymous installation ID (SHA256 hash, not reversible)
- Agent run counts and success rates
- Version number

**What's NOT collected:**
- Repository names or URLs
- Code content or diffs
- Usernames or any identifying information

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
BARBOSSA_ANALYTICS_OPT_OUT=true
```
