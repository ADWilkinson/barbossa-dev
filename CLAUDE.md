# Barbossa Engineer - Claude Context

**Last Updated:** 2026-01-03
**Version:** v1.8.3

## Project Overview

Barbossa is an autonomous AI development team powered by Claude that manages GitHub repositories automatically. It consists of multiple specialized agents that work together to maintain codebases, review PRs, discover improvements, manage issues, and more.

## Project Structure

```
barbossa-engineer/
├── src/
│   └── barbossa/            # Python package
│       ├── agents/          # AI agent modules
│       │   ├── engineer.py  # Main engineer - implements features from backlog
│       │   ├── tech_lead.py # Tech lead - reviews and merges PRs
│       │   ├── discovery.py # Discovery - finds code improvements
│       │   ├── product.py   # Product manager - creates feature issues
│       │   ├── auditor.py   # Auditor - system health checks
│       │   ├── spec_generator.py  # Spec Generator - cross-repo product specs
│       │   └── firebase.py  # Firebase sync (future)
│       ├── utils/           # Shared utilities
│       │   ├── prompts.py   # Prompt templates loader
│       │   ├── issue_tracker.py  # GitHub/Linear abstraction
│       │   ├── linear_client.py  # Linear API client
│       │   └── notifications.py  # Discord/Slack webhook notifications
│       └── cli/
│           └── barbossa     # CLI tool for manual operations
├── scripts/                 # Build and deployment scripts
│   ├── validate.py          # Startup validation
│   ├── generate_crontab.py  # Crontab generator from config
│   ├── run.sh               # Agent runner script
│   └── install.sh           # Installation script
├── tests/                   # Test suite
│   ├── test_issue_tracker.py
│   └── test_linear_client.py
├── config/                  # Configuration files
│   ├── repositories.json    # Repository configuration
│   ├── repositories.json.example
│   └── crontab              # Generated crontab
├── prompts/                 # Local prompt templates
├── logs/                    # Agent execution logs
├── changelogs/              # Generated changelogs
├── projects/                # Cloned repositories
├── pyproject.toml           # Python package metadata
├── Dockerfile               # Container definition (runs as non-root)
├── docker-compose.prod.yml  # Production orchestration
├── docker-compose.dev.yml   # Development orchestration
└── entrypoint.sh            # Docker entrypoint
```

## Current System State

### Active Configuration
- **Repositories:** 1 (scallywag-br-io)
- **Owner:** ADWilkinson
- **Schedule (Optimized):**
  - Engineer: 12x daily at :00 (0,2,4,6,8,10,12,14,16,18,20,22 UTC)
  - Tech Lead: 12x daily at :00 (1,3,5,7,9,11,13,15,17,19,21,23 UTC), 1h after engineer
  - Discovery: 6x daily offset (1,5,9,13,17,21 UTC); keeps backlog stocked
  - Product Manager: 3x daily offset (3,11,19 UTC); prioritizes quality over quantity
  - Auditor: Daily at 06:30 UTC
- **Schedule Philosophy:** Agents offset to avoid resource contention, ensure fresh PRs are reviewed in next cycle, and keep backlog healthy

### Tech Lead Settings
- Auto-merge: Enabled
- Min lines for tests required: 50
- Max files per PR: 15
- Stale PR threshold: 5 days

### System Health
- ✅ GitHub CLI: Authenticated
- ✅ Claude CLI: Authenticated (valid for 8597h)
- ✅ Git Config: Andy Wilkinson <andywilkinson1993@gmail.com>
- ⚠️ SSH Keys: Not configured (using HTTPS URLs)

## Issue Tracking

### Supported Systems
Barbossa supports both **GitHub Issues** (default) and **Linear** for issue tracking. All agents work with either system through a unified abstraction layer.

### GitHub Issues (Default)
- No configuration needed; works out of the box
- Uses `gh` CLI for issue operations
- Agents reference issues as `#123`
- PRs linked via "Closes #123" in PR description

### Linear Integration
Configure Linear in `config/repositories.json`:

```json
{
  "owner": "your-github-username",
  "issue_tracker": {
    "type": "linear",
    "linear": {
      "team_key": "MUS",
      "backlog_state": "Backlog",
      "api_key": "lin_api_xxx"  // Optional - prefer LINEAR_API_KEY env var
    }
  },
  "repositories": [...]
}
```

**Environment Variable (Recommended):**
```bash
export LINEAR_API_KEY="lin_api_xxx"
# Get your API key from: https://linear.app/settings/api
```

**Linear Features:**
- ✅ Discovery/Product agents create issues in Linear team
- ✅ Engineer agent fetches backlog from Linear
- ✅ Auto-linking via branch naming: `barbossa/MUS-14-description`
- ✅ All agents use unified Issue abstraction (no code changes needed)
- ✅ Validation on startup checks Linear connectivity

**Behavioral Differences:**
- **GitHub:** Engineer uses `gh issue list` at runtime (real-time state)
- **Linear:** Issues pre-fetched and injected into prompt (snapshot)

**Startup Validation:**
When Linear is configured, `validate.py` checks:
- ✅ `team_key` is set in config
- ✅ `LINEAR_API_KEY` environment variable is set
- ✅ API connectivity to `api.linear.app`
- ✅ Team exists and user has access

## Webhook Notifications

### Overview
Barbossa can send real-time notifications to Discord (Slack support coming soon) about agent activities. Notifications are fire-and-forget and never block agent execution.

### Configuration
Add to `config/repositories.json`:

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
- **run_complete**: Summary when any agent finishes a run
- **pr_created**: When Engineer creates a new PR
- **pr_merged**: When Tech Lead merges a PR
- **pr_closed**: When Tech Lead closes a PR (off by default)
- **error**: When any agent encounters an error (always recommended)

### Getting a Discord Webhook URL
1. Open Discord and go to the channel where you want notifications
2. Click the gear icon (Edit Channel) → Integrations → Webhooks
3. Click "New Webhook" and copy the webhook URL
4. Paste the URL in your `repositories.json` config

### Design Principles
- **Never blocks**: Webhooks run in background threads
- **Graceful degradation**: If Discord is down, agents continue working
- **Not spammy**: Only sends meaningful insights, not every action
- **Rich formatting**: Uses Discord embeds with colors and emojis per agent

## Security Model

### Non-Root Container Execution
- Container runs as user `barbossa` (UID 1000, GID 1000)
- Created via: `useradd -m -u 1000 -s /bin/bash barbossa`
- Working directory `/app` owned by `barbossa:barbossa`
- Enhances security by preventing root-level container breakouts

### Platform Support
- **Docker Platform:** `linux/amd64` (specified in docker-compose files)
- **Works on:** Linux x86_64 (native), macOS Intel (native), macOS Apple Silicon (via Rosetta 2)
- **Why amd64:** Dockerfile uses linux-amd64 binaries (supercronic), so we're explicit about platform
- **Performance:** Negligible overhead on Apple Silicon due to emulation for cron-based workloads

### macOS Compatibility
**How it works across platforms:**
- **Linux:** Container runs as 1000:1000 (default)
- **macOS:** Container runs as host UID (e.g., 501) with GID 1000
- **Permissions:**
  - /app is group-writable (775) so any host UID with GID 1000 can write
  - Only ~/.gitconfig is mounted (read-only) for git user config
- **Auto-detection:** install.sh creates .env with UID=$(id -u) on macOS

**Why token-based auth solves macOS issues:**
- No credential files mounted (no permission issues)
- No macOS Keychain dependency (tokens stored in .env)
- Works identically on Linux and macOS
- Tokens are platform-independent

### Authentication
**Token-based authentication (v1.6.0+):**
- **GitHub:** `GITHUB_TOKEN` environment variable (from `gh auth token` or personal access token)
- **Claude:** `ANTHROPIC_API_KEY` environment variable (supports both):
  - Option 1 (Recommended): Claude Pro/Max subscription token (long-lasting, up to 1 year)
  - Option 2: Pay-as-you-go Anthropic API key
- **Linear:** `LINEAR_API_KEY` environment variable (optional, only if using Linear)
- **Git:** User name/email from mounted `~/.gitconfig` (read-only)
- All tokens configured in `.env` file
- No credential files mounted (resolves macOS Keychain issues)

## Agent Workflows

### Engineer Agent (`barbossa_engineer.py`)
1. Checks for PRs needing attention (conflicts, failing checks)
2. Scans all repositories for `backlog` labeled issues
3. Picks highest priority issue per repo
4. Implements feature/fix following best practices
5. Creates PR with comprehensive description
6. All checks must pass before marking complete

### Tech Lead Agent (`barbossa_tech_lead.py`)
1. Reviews all open PRs across repositories
2. Analyzes code quality, test coverage, security
3. Leaves review comments if issues found
4. Auto-merges PRs that meet quality standards
5. Logs decisions and rationale

### Discovery Agent (`barbossa_discovery.py`)
1. Scans codebase for improvements
2. Checks for: missing tests, console.logs, TODO comments, accessibility issues
3. Creates backlog issues for discovered work
4. Avoids duplicates via semantic matching
5. Caps total backlog issues to prevent overload

### Product Manager Agent (`barbossa_product.py`)
1. Analyzes codebase and existing features
2. Generates feature suggestions aligned with project goals
3. Creates product-labeled issues with detailed specs
4. Uses semantic deduplication to prevent duplicates
5. Caps feature backlog to focus on quality over quantity

### Auditor Agent (`barbossa_auditor.py`)
1. Weekly health check of the entire system
2. Analyzes error logs, failed attempts, patterns
3. Calculates health score (0-100)
4. Generates recommendations for improvements

### Spec Generator Agent (`spec_generator.py`)
**Only runs when spec_mode.enabled=true** (all other agents disabled)
1. Operates on "products" (groups of linked repositories)
2. Aggregates context from all linked repos' CLAUDE.md files
3. Uses product context (vision, constraints, strategy notes) from config
4. Generates detailed, prompt-ready cross-repo specifications
5. Creates distributed tickets:
   - Parent spec ticket in primary_repo with `spec` label
   - Child implementation tickets in each affected repo with `backlog` label
6. Links parent ↔ children for traceability
7. Semantic deduplication prevents duplicate specs

## Common Operations

### Manual Agent Execution
```bash
# Inside container
docker exec -it barbossa barbossa run engineer
docker exec -it barbossa barbossa run tech-lead
docker exec -it barbossa barbossa run discovery
docker exec -it barbossa barbossa run product
docker exec -it barbossa barbossa run auditor
docker exec -it barbossa barbossa run spec                        # All products
docker exec -it barbossa barbossa run spec --product my-platform  # Specific product

# Health check
docker exec -it barbossa barbossa health

# View status
docker exec -it barbossa barbossa status

# View logs
docker exec -it barbossa barbossa logs
```

### Container Management
```bash
# Rebuild with latest code
docker compose build --no-cache
docker compose up -d

# View logs
docker logs -f barbossa

# Check schedule
docker exec -it barbossa cat /app/crontab
```

### Configuration Updates
```bash
# Edit repository config
vim config/repositories.json

# Restart to apply changes
docker compose restart
```

## Known Issues & Limitations

### Current Warnings
- SSH URLs configured but no SSH keys mounted (non-critical)
  - Using HTTPS URLs with gh CLI auth instead
  - SSH keys only needed if switching to `git@github.com` URLs

### Validation Process
On container startup, `validate.py` checks:
1. ✅ Config file exists and valid JSON
2. ✅ `GITHUB_TOKEN` environment variable set and valid
3. ✅ `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` environment variable set
4. ✅ `LINEAR_API_KEY` set and valid (if Linear is configured)
5. ✅ Spec mode configuration valid (if enabled)
   - Products array must exist with at least one product
   - All product repositories exist in `repositories` array
   - Each product has `primary_repo` set
6. ⚠️ Git user.name and user.email configured (warning only)
7. ⚠️ SSH keys if SSH URLs configured (warning only; HTTPS recommended)

**Critical failures block startup** to prevent silent failures.

## Version History

**Current Version:** v2.0.1 (2026-01-11)

For detailed release notes, see [CHANGELOG.md](CHANGELOG.md).

**Key capabilities by version:**
- v1.8.x: Spec Mode (cross-repo feature specifications)
- v1.7.x: Discord webhook notifications, PR ownership filtering
- v1.6.x: Repository focus/known_gaps config, auto_merge enforcement
- v1.5.x: Python package restructure (`src/barbossa/`)
- v1.3.x: Enhanced Tech Lead review (8 dimensions, external deps)
- v1.2.x: Product Manager and Auditor fixes
- v1.1.x: Engineer detects Tech Lead feedback properly
- v1.0.x: Initial release with core pipeline

## Troubleshooting

### Agents Not Running
1. Check validation: `docker logs barbossa | head -50`
2. Verify environment variables: `docker exec barbossa env | grep -E "GITHUB_TOKEN|CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY"`
3. Check schedule: `docker exec barbossa cat /app/crontab`
4. View recent logs: `ls -lht /app/logs/ | head`

### Authentication Issues
```bash
# Verify tokens in .env file
cat .env

# Generate new GitHub token
gh auth token

# Generate Claude OAuth token (recommended)
claude setup-token  # Follow prompts to generate long-lived token
# Sets CLAUDE_CODE_OAUTH_TOKEN in .env

# Update .env with new tokens
vim .env  # Edit GITHUB_TOKEN and CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY

# Restart container
docker compose restart

# Check validation
docker logs barbossa | head -50
```

### Token Validation Failures
```bash
# GITHUB_TOKEN not set or invalid
# Fix: Generate token with 'gh auth token' or create at https://github.com/settings/tokens
# Scopes needed: repo, workflow

# ANTHROPIC_API_KEY not set
# Fix Option 1 (Recommended): Generate Claude Pro token
#   claude setup-token  # Follow prompts
# Fix Option 2: Get API key from https://console.anthropic.com/settings/keys

# LINEAR_API_KEY invalid (if using Linear)
# Fix: Get from https://linear.app/settings/api
```

## Contact & Support

- **Repository:** https://github.com/ADWilkinson/barbossa-dev
- **Issues:** https://github.com/ADWilkinson/barbossa-dev/issues
- **Release Notes:** See CHANGELOG.md

## Verification

After making changes, run:
```bash
# Run tests
pytest tests/ -v

# Type check (if mypy installed)
mypy src/barbossa --ignore-missing-imports

# Validate configuration
python scripts/validate.py
```

For agent changes, also test manually:
```bash
docker exec -it barbossa barbossa run [agent-name]
```

## AI Agent Guidelines

When working with this codebase:
1. Always run validation checks before making changes
2. Follow the non-root security model
3. Update this CLAUDE.md when making significant changes
4. Test with `barbossa run [agent]` before relying on cron
5. Check logs in `/app/logs/` for debugging
6. Respect the `do_not_touch` areas in config/repositories.json
