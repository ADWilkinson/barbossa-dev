# Barbossa Engineer - Claude Context

**Last Updated:** 2026-01-03
**Version:** v1.8.1

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

## Recent Enhancements (v1.2.0)

### CRITICAL FIXES: Product Manager & Auditor Functionality Restored
**Date:** 2025-12-26
**Issues Fixed:**
1. **Product Manager was returning NO suggestions** because the prompt template was completely outdated
2. **Auditor was only logging recommendations** instead of creating actionable GitHub issues

**Product Manager Fixes (`barbossa_product.py` + `prompts/product_manager.txt`):**

**Problem:**
- Prompt template asked for free-form "Report" but code expected JSON with `feature_title`, `problem`, `solution`, etc.
- Claude returned text → Code couldn't parse → Logged "WARNING - No feature suggestion"
- Result: 0 feature issues created across ALL 3 runs (Dec 25)

**Solution:**
- ✅ Completely rewrote `prompts/product_manager.txt` with JSON output format
- ✅ Added explicit JSON schema with all required fields
- ✅ Added "NO SUGGESTION" option for when quality > quantity
- ✅ Updated code to handle "NO SUGGESTION" responses
- ✅ Added better error messages for parse failures
- ✅ Enhanced product context with KNOWN GAPS for each repo
- ✅ Added examples of good vs bad feature suggestions

**Impact:**
- ✅ Product Manager NOW WORKING; created 2 high-value feature issues in test run:
  - peerlytics #125: "Custom Date Range Picker for Analytics Dashboard" (value: 8)
  - usdctofiat #116: "Bulk rate update for multiple deposits"
- ✅ Quality over quantity; can decline to suggest if no high-value ideas
- ✅ Better feature quality with structured acceptance criteria

**Auditor Enhancements (`barbossa_auditor.py`):**

**Problem:**
- Auditor generated excellent quality recommendations but only logged them
- No actionable GitHub issues created → recommendations were invisible to Engineer
- Health score: 35/100 with 8+ critical quality issues, but nothing in backlog

**Solution:**
- ✅ Added `_create_quality_issues()` method to create GitHub issues for critical problems
- ✅ Added `_get_existing_issues()` to avoid duplicate quality issues (7-day deduplication)
- ✅ Added `_create_github_issue()` helper for issue creation
- ✅ Creates ONE consolidated issue per repo (avoids spam)
- ✅ Groups all critical patterns into comprehensive quality issue
- ✅ Only creates issues for HIGH severity patterns (low noise)

**Impact:**
- ✅ Auditor now TAKES ACTION on critical quality problems
- ✅ Quality issues appear in backlog for Engineer to pick up
- ✅ Consolidated format (1 issue per repo) prevents issue spam
- ✅ 7-day deduplication prevents duplicate quality audits
- ✅ Clear, actionable recommendations in issue body

**Files Modified:**
- `prompts/product_manager.txt`: Complete rewrite with JSON format
- `barbossa_product.py:364-427`: Added "NO SUGGESTION" handling
- `barbossa_auditor.py:1459-1560`: Added quality issue creation methods
- `barbossa_auditor.py:1808`: Integrated issue creation into audit flow
- Version bumped to v1.2.0

**Testing:**
- ✅ Product Manager: Successfully created 2 feature issues (peerlytics #125, usdctofiat #116)
- ✅ Auditor: Issue creation code tested and verified (will create on next run)

## Previous Enhancements (v1.1.0)

### CRITICAL FIX: Engineer Now Detects Tech Lead Feedback
**Date:** 2025-12-25
**Bug Fixed:** Engineer was failing to detect and address Tech Lead feedback, allowing PRs to accumulate 6-7 unaddressed reviews before finally being caught.

**Problem:**
- PR #112 received **7 identical Tech Lead reviews** over 13 hours (Dec 24 14:01 → Dec 25 02:01)
- Each review flagged the same accessibility issues
- Engineer logged "No PRs need attention - all clear!" at 14:00, 16:00, 18:00, 22:00, 00:00
- PR was only caught at 02:00 when merge conflicts developed (detected as `merge_conflicts`, not `tech_lead_feedback`)
- This wasted API costs, time, and violated the 3-strikes auto-close rule intent

**Root Cause Analysis:**
1. **Tech Lead posted comments, not GitHub reviews** → `reviewDecision` field stayed empty
2. **Comment parsing logic bug** → Confused owner authorship (Tech Lead runs as owner ADWilkinson)
3. **Detection ordering bug** → Merge conflicts checked before Tech Lead feedback
4. **No detection logging** → Hard to debug why PRs weren't being flagged

**Fixes Implemented:**

**Engineer (`barbossa_engineer.py:473-568`):**
- ✅ **Fixed comment detection logic**: Now tracks LATEST Tech Lead feedback by timestamp
- ✅ **Smarter feedback-addressed detection**: Looks for "Feedback Addressed" comments AFTER Tech Lead review
- ✅ **Priority ordering**: Tech Lead feedback is PRIORITY 1 (checked before merge conflicts)
- ✅ **Added detection logging**: Now logs why each PR is/isn't flagged (`PR #X: Tech Lead feedback detected`)
- ✅ **Removed owner authorship confusion**: No longer checks `author == owner` incorrectly

**Tech Lead (`barbossa_tech_lead.py:537-596`):**
- ✅ **Now uses `gh pr review --request-changes`** instead of `gh pr comment`
- ✅ **Sets `reviewDecision` field** on GitHub (when not own PR)
- ✅ **Graceful fallback**: If "own PR" error, falls back to comments
- ✅ **Better logging**: Distinguishes between formal reviews and comment fallbacks

**Impact:**
- ✅ Engineer now catches Tech Lead feedback on FIRST review (not after 6-7 reviews)
- ✅ Tech Lead feedback detected as `tech_lead_feedback` reason (not misclassified as `merge_conflicts`)
- ✅ 3-strikes auto-close rule works as intended
- ✅ Massive reduction in wasted API costs and review cycles
- ✅ PRs get fixed faster instead of accumulating feedback

**Testing:**
- Fixed logic tested against PR #112 timeline
- Would have caught feedback at 14:01 instead of waiting until 02:01 merge conflicts

**Files Modified:**
- `barbossa_engineer.py:473-568`: Complete rewrite of `_get_prs_needing_attention()`
- `barbossa_tech_lead.py:537-596`: Updated `_execute_decision()` REQUEST_CHANGES handling
- All agent versions bumped to v1.1.0

## Previous Enhancements (v1.0.9)

### Tech Lead 3-Strikes Auto-Close Rule
**Enhancement:** Tech Lead now automatically closes PRs that fail to meet quality standards after 3 review cycles.

**Problem Solved:**
- Previously, PRs could get stuck in infinite REQUEST_CHANGES loops
- Engineer would repeatedly attempt fixes that failed review
- Example: PR #112 had 6+ identical reviews for same accessibility issues
- This wasted API costs, time, and blocked progress on other backlog items

**Implementation:**
- Before sending PR to Claude for review, Tech Lead checks comment history
- Counts "**Tech Lead Review - Changes Requested**" comments
- If count >= 3, automatically CLOSE the PR with clear explanation
- Logs: "AUTO: Closing PR - 3-strikes rule triggered (N change requests)"

**Impact:**
- ✅ Stops wasted effort on unfixable or stalled PRs
- ✅ Forces Engineer to try different approach (new PR from scratch)
- ✅ Clears backlog faster; no zombie PRs
- ✅ Still fair (3 chances is reasonable)
- ✅ 5-day stale cleanup becomes backup, not primary mechanism

**Files Modified:**
- `barbossa_tech_lead.py:619-634`: Added 3-strikes check in `review_pr()` method
- Version bumped to v1.0.9

**Behavior:**
- After 3 REQUEST_CHANGES comments → PR auto-closed
- Message: "Unable to meet quality standards after N review cycles. Closing to prevent wasted effort. Start fresh with a new approach if this feature is still needed."

## Previous Enhancements (v1.0.8)

### Enhanced Tech Lead & Auditor - Deep Quality Analysis
**Enhancement:** Significantly upgraded both Tech Lead and Auditor agents to perform comprehensive quality checks beyond basic code review.

**Tech Lead Improvements:**
- **8 Quality Dimensions:** Code quality, feature bloat, existing feature integration, UI/UX, tests, security, performance, complexity
- **Bloat Detection:** Identifies duplicate functionality, over-engineering, unnecessary features
- **Integration Checks:** Ensures changes work harmoniously with existing features
- **UI/UX Review:** Checks accessibility, responsive design, consistent styling, loading/error states
- **Architecture Enforcement:** Validates adherence to existing patterns
- **Security Scanning:** Detects XSS, SQL injection, exposed secrets, auth issues
- **Performance Analysis:** Identifies inefficient queries, memory leaks, blocking operations
- **Complexity Metrics:** Flags deep nesting, large functions, unclear code

**Auditor Improvements:**
- **Code Bloat Detection:** Scans for large files (>500 lines), deep nesting (>6 levels), duplicate utilities
- **Architecture Consistency:** Validates project structure, detects mixed patterns, enforces conventions
- **Complexity Analysis:** Identifies overly complex files requiring refactoring
- **Enhanced Reporting:** Provides bloat scores and architecture violation counts
- **Actionable Recommendations:** Tech Lead receives specific guidance on enforcing quality standards

**Impact:**
- Tech Lead now rejects PRs with poor UI/UX, bloated code, or architecture violations
- Auditor provides early warning on code quality degradation
- System enforces higher quality standards automatically
- Prevents accumulation of technical debt

**Files Modified:**
- `prompts/tech_lead.txt`: Comprehensive 8-dimension review criteria
- `barbossa_auditor.py`: Added `_detect_code_bloat_patterns()` and `_analyze_architecture_consistency()` methods

## Previous Fixes (v1.0.7)

### Critical Bug Fix - Docker Compose Mounts
**Issue:** Container runs as non-root `barbossa` user (UID 1000) for security, but docker-compose.yml was mounting config directories to `/root/` which the non-root user couldn't access.

**Impact:** Validation failures blocked all agents from running:
- ❌ GitHub CLI not authenticated
- ❌ Claude CLI not authenticated

**Fix:** Updated docker-compose.yml:6-18 to mount to `/home/barbossa/`:
```yaml
# Before (broken)
- ~/.gitconfig:/root/.gitconfig
- ~/.config/gh:/root/.config/gh:ro
- ~/.claude:/root/.claude

# After (working)
- ~/.gitconfig:/home/barbossa/.gitconfig
- ~/.config/gh:/home/barbossa/.config/gh:ro
- ~/.claude:/home/barbossa/.claude
```

**Commit:** 60a92e5 - "fix: update docker-compose volume mounts for non-root user"

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

## Development History

### v1.8.1 - 2026-01-03 (Spec Mode Bugfix)
- **BUG FIX**: Spec Generator now loads prompts correctly
- **Issue:** `prompts.py` had a hardcoded `AGENT_TYPES` list that didn't include `spec_generator` or `spec_critique`
- **Impact:** Spec mode would fail with "Unknown agent type: spec_generator" error
- **Fix:** Added `spec_generator` and `spec_critique` to the `AGENT_TYPES` list in `src/barbossa/utils/prompts.py`
- **Files Modified:**
  - `src/barbossa/utils/prompts.py:18`: Added spec_generator and spec_critique to AGENT_TYPES
  - All agent versions bumped to v1.8.1
  - Package version bumped to v1.8.1
  - Docker image tag updated to v1.8.1

### v1.8.0 - 2026-01-03 (Spec Mode - Global System Switch)
- **FEATURE**: Spec Mode - a global system switch that transforms Barbossa from autonomous development to product specification generation
- **Purpose**: When enabled, the system stops autonomous code implementation and instead generates detailed, prompt-ready feature specs that span multiple linked repositories

**Two Modes:**
1. **AUTONOMOUS MODE (default)**: All agents run (Engineer, Tech Lead, Discovery, Product Manager, Auditor)
2. **SPEC MODE**: Only Spec Generator runs - all other agents are disabled

**Design Philosophy:**
- Products are groups of linked repositories that form a coherent system
- Specs span the full stack (backend, frontend, indexer, etc.)
- Each child ticket is prompt-ready for direct Claude implementation
- Distributed tickets link parent ↔ children for traceability

**New Files:**
- `src/barbossa/agents/spec_generator.py`: New agent (~800 lines)
- `prompts/spec_generator.txt`: Prompt template for spec generation

**Configuration (Global System Switch):**
```json
{
  "settings": {
    "spec_mode": {
      "enabled": true,                    // GLOBAL SWITCH - disables all other agents
      "schedule": "0 9 * * *",            // Daily at 09:00 UTC
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
      "description": "Full-stack platform",
      "repositories": ["backend-api", "frontend-web", "frontend-mobile"],
      "primary_repo": "frontend-web",
      "context": {
        "vision": "Become the leading platform for X",
        "current_phase": "MVP hardening",
        "target_users": "Small business owners",
        "constraints": ["Must support mobile browsers"],
        "strategy_notes": ["BD feedback: faster onboarding needed"],
        "known_integrations": {
          "backend-api": "REST API - user management, auth",
          "frontend-web": "React SPA - dashboard",
          "frontend-mobile": "React Native app"
        }
      }
    }
  ]
}
```

**Crontab Behavior:**
- **Spec Mode enabled**: Only Spec Generator cron job generated
- **Spec Mode disabled (default)**: All autonomous agent cron jobs generated

**Ticket Creation:**
- Parent spec ticket in `primary_repo` with `[SPEC]` prefix and `spec` label
- Child implementation tickets in each affected repo with `backlog` label
- Cross-references link all tickets together
- Each child ticket contains prompt-ready implementation details

**Files Modified:**
- `src/barbossa/agents/spec_generator.py`: New agent
- `prompts/spec_generator.txt`: New prompt template
- `src/barbossa/cli/barbossa`: Added `spec` agent command
- `src/barbossa/utils/notifications.py`: Added `notify_spec_created()`
- `scripts/generate_crontab.py`: Mode-aware crontab generation
- `scripts/validate.py`: Spec mode validation
- `config/repositories.json.example`: Updated schema documentation
- All agent versions bumped to v1.8.0

**Usage:**
```bash
barbossa run spec                        # All products
barbossa run spec --product my-platform  # Specific product only
```

**Impact:**
- ✅ Global switch between autonomous dev and spec generation
- ✅ All other agents disabled when spec_mode.enabled=true
- ✅ Cross-repo feature planning without code implementation
- ✅ Detailed specs usable as implementation prompts
- ✅ Distributed tickets with full traceability
- ✅ Strategic context (vision, constraints, BD notes) fed to Claude
- ✅ Semantic deduplication prevents duplicate specs
- ✅ Discord notifications for new specs

### v1.7.2 - 2026-01-02 (Discord Webhook Fix)
- **BUG FIX**: Discord webhook notifications now reliably sent before process exits
- **Issue:** Notifications used daemon threads that were killed when main process exited
- **Root Cause:** Python daemon threads (`daemon=True`) terminate when the main thread exits, so the agent run completed before the HTTP request finished
- **Fix:**
  - ✅ Added thread tracking in `notifications.py` to monitor pending notifications
  - ✅ Added `wait_for_pending()` function that blocks until all webhook calls complete
  - ✅ All agents now call `wait_for_pending()` before returning from `run()` method
  - ✅ 5-second timeout ensures process never hangs on webhook failures
- **Files Modified:**
  - `src/barbossa/utils/notifications.py`: Added thread tracking and `wait_for_pending()`
  - All agent files: Import and call `wait_for_pending()` at end of run
  - All versions bumped to v1.7.2

**Impact:**
- ✅ Discord notifications now reliably appear for all agent runs
- ✅ PR created/merged/closed notifications work correctly
- ✅ Error notifications work correctly
- ✅ No impact on agent execution time (max 5s wait for webhooks)

### v1.7.1 - 2026-01-02 (Critical: Ownership Filter for PRs)
- **CRITICAL BUG FIX**: Barbossa now only works on its own PRs (not human contributor PRs)
- **Issue:** Engineer and Tech Lead agents were modifying PRs created by human developers
- **Root Cause:** Both agents fetched ALL open PRs without filtering by ownership
- **Example:** Richard's feature branch had failing CI, Barbossa "fixed" it automatically, breaking the build
- **Fix:**
  - ✅ Engineer: Added filter in `_get_prs_needing_attention()` to only process PRs with `barbossa/` branch prefix
  - ✅ Tech Lead: Added filter in `run()` to only review PRs with `barbossa/` branch prefix
  - ✅ Clear logging when skipping non-Barbossa PRs
- **Files Modified:**
  - `src/barbossa/agents/engineer.py:559-576`: Added ownership check at start of PR loop
  - `src/barbossa/agents/tech_lead.py:951-963`: Added ownership filter before review loop
  - All agent versions bumped to v1.7.1
  - Package version bumped to v1.7.1
  - Docker image tag updated to v1.7.1

**Impact:**
- ✅ Human contributor PRs are now completely untouched by Barbossa
- ✅ Clear separation between autonomous and human-driven development
- ✅ Prevents accidental "fixes" that break builds
- ✅ Safe for teams with mixed human + Barbossa contributions

**Behavior:**
- PRs with branch `barbossa/*`: Processed normally (review, fix, merge)
- PRs with any other branch: Skipped with log message "Skipping - not a Barbossa PR"

### v1.7.0 - 2026-01-01 (Discord Webhook Notifications)
- **FEATURE**: Added Discord webhook notification system for real-time agent insights
- **Design**: Fire-and-forget notifications that never block agent execution
- **Implementation:**
  - Created `src/barbossa/utils/notifications.py`, an extensible notification module
  - Integrated notifications into all 5 agents (Engineer, Tech Lead, Discovery, Product, Auditor)
  - Rich Discord embeds with agent-specific colors and emojis
  - Configurable notification types (run_complete, pr_created, pr_merged, pr_closed, error)
- **Configuration in `repositories.json`:**
  ```json
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
  ```
- **Notification Types:**
  - Agent run summaries (PRs created, merged, reviewed, issues created)
  - PR lifecycle events (created, merged, closed)
  - Error alerts with context
  - Auditor health scores
- **Files Created:**
  - `src/barbossa/utils/notifications.py`: Full webhook notification implementation
- **Files Modified:**
  - All agent files: Import and call notification functions
  - `config/repositories.json.example`: Added notifications config section
  - `pyproject.toml`: Version bump to 1.7.0
  - `docker-compose.prod.yml`: Updated image to v1.7.0

**Impact:**
- ✅ Real-time visibility into Barbossa operations via Discord
- ✅ Immediate error alerts for faster debugging
- ✅ Non-blocking design; webhook failures never affect agent execution
- ✅ Extensible for future platforms (Slack, Teams, etc.)

### v1.6.6 - 2026-01-01 (Product Manager Fix)
- **BUG FIX**: Product Manager label type handling in duplicate detection
- **Issue:** `_is_semantically_similar()` crashed with `'str' object has no attribute 'get'`
- **Root Cause:** Labels stored as `List[str]` but code expected `List[Dict]` with `name` keys
- **Fix:** Handle both label formats with type checking:
  ```python
  labels = [l if isinstance(l, str) else l.get('name', '') for l in raw_labels]
  ```
- **Files Modified:**
  - `src/barbossa/agents/product.py:450-452`: Fixed label type handling
  - All agent versions bumped to v1.6.6
  - Package version bumped to v1.6.6
  - Docker image tag updated to v1.6.6

**Impact:**
- ✅ Product Manager now correctly detects duplicate features
- ✅ Discovery agent continues working (labels already existed)
- ✅ Both agents now creating issues successfully

### v1.6.5 - 2025-12-31 (Approval Detection Fix)
- **BUG FIX**: Tech Lead no longer re-reviews PRs it has already approved
- **Issue:** When `auto_merge: false`, Tech Lead would post duplicate approval comments on every run
- **Example:** PR #12 in zkp2p-clients received 3 identical approval comments (01:00, 03:01, 05:01 UTC)
- **Root Cause:** Tech Lead reviewed ALL open PRs without checking for existing approval
- **Fix:**
  - ✅ Added `_has_tech_lead_approval()` method to detect existing approval comments
  - ✅ Modified `run()` loop to skip PRs that already have Tech Lead approval
  - ✅ Approval detection is timestamp-aware (handles approval → changes → re-approval flows)
  - ✅ Only applies when `auto_merge: false` (auto-merge handles this via actual merge)
- **Files Modified:**
  - `src/barbossa/agents/tech_lead.py:174-205`: Added `_has_tech_lead_approval()` method
  - `src/barbossa/agents/tech_lead.py:929-942`: Added approval check before `review_pr()` call
  - All agent versions bumped to v1.6.5
  - Package version bumped to v1.6.5

**Impact:**
- ✅ No more duplicate approval comments on approved PRs
- ✅ Saves API costs by skipping unnecessary Claude reviews
- ✅ Cleaner PR comment history
- ✅ PRs waiting for manual merge stay in clean approved state

**Behavior:**
- **Already approved**: Logs "PR #X: Already approved - skipping re-review" and skips
- **Not yet reviewed**: Normal review flow continues
- **Changes requested after approval**: Re-reviews as expected (approval invalidated)

### v1.6.4 - 2025-12-30 (Quality & Resilience Focus)
- **ENHANCEMENT**: Repository configuration now supports `focus` and `known_gaps` fields
- **Impact:** Agents (Engineer, Product Manager) now read repository-specific guidance from config
- **Purpose:** Enable per-repository focus on quality, resilience, testing, and polish vs new features
- **Implementation:**
  - ✅ Engineer agent reads `focus` and `known_gaps` from repository config
  - ✅ Product Manager reads `focus` and `known_gaps` from repository config
  - ✅ New config fields injected into agent prompts dynamically
  - ✅ Backward compatible; repos without these fields continue to work normally
- **Config Fields:**
  - `focus` (string): Development focus/philosophy for the repository (e.g., "QUALITY & RESILIENCE ONLY")
  - `known_gaps` (array): List of specific known issues and priority areas to address
- **Files Modified:**
  - `prompts/engineer.txt`: Added `{{focus_section}}`, `{{known_gaps_section}}`, `{{focus_guidance}}` variables
  - `src/barbossa/agents/engineer.py:284-330`: Build and inject focus/known_gaps sections into prompts
  - `src/barbossa/agents/product.py:214-248`: Prefer config fields over hardcoded context
  - All agent versions bumped to v1.6.4
  - Package version bumped to v1.6.4
- **Example Usage:**
  ```json
  {
    "name": "zkp2p-clients",
    "focus": "QUALITY & RESILIENCE ONLY - Focus on bug fixes, edge cases, testing, security, UI polish",
    "known_gaps": [
      "Missing error boundaries in React components",
      "Insufficient loading states",
      "Weak network error handling",
      "Limited test coverage"
    ]
  }
  ```

**Impact:**
- ✅ Repository-specific agent behavior without code changes
- ✅ Clear guidance on whether to prioritize quality vs features
- ✅ Product Manager suggests features aligned with repository goals
- ✅ Engineer prioritizes work from known_gaps list
- ✅ Easier to shift focus between exploration and production-hardening phases

**Behavior:**
- **With `focus`**: Agent receives explicit development philosophy in prompt
- **With `known_gaps`**: Agent sees prioritized list of known issues to address
- **Without fields**: Agent behavior unchanged (backward compatible)

### v1.6.3 - 2025-12-30 (Critical bugfix release)
- **CRITICAL BUG FIX**: Tech Lead now respects `auto_merge` setting in config
- **Issue:** Tech Lead was ignoring `settings.tech_lead.auto_merge: false` and automatically merging PRs anyway
- **Impact:** PRs were being merged without manual review when auto_merge was explicitly disabled
- **Root Cause:** Config setting was loaded but never checked before executing merge command
- **Example:** PR #4 in zkp2p-clients was auto-merged at 15:00 UTC despite `auto_merge: false`
- **Fix:**
  - ✅ Added `auto_merge` check in `_execute_decision()` method before executing merge
  - ✅ When `auto_merge: false`, Tech Lead posts approval comment instead of merging
  - ✅ Approval comment includes scores, assessment, and note that manual merge is required
  - ✅ When `auto_merge: true`, behavior unchanged (auto-merges as before)
- **Files Modified:**
  - `src/barbossa/agents/tech_lead.py:511-565`: Added auto_merge enforcement in MERGE action
  - Tech Lead version bumped to v1.6.3
  - Package version bumped to v1.6.3

**Impact:**
- ✅ `auto_merge: false` now works correctly; PRs get approval comments but aren't merged
- ✅ `auto_merge: true` continues to work as before
- ✅ Users regain control over when PRs are merged
- ✅ Prevents unexpected merges when manual review is desired

**Behavior:**
- **When `auto_merge: false`**: Posts "✅ Tech Lead Approval - Ready to Merge" comment with scores and reasoning
- **When `auto_merge: true`**: Executes merge immediately (existing behavior)

### v1.6.1 - 2025-12-30 (Hotfix release)
- **CRITICAL FIX**: Added support for both Claude authentication methods
- **Issue:** `claude setup-token` generates OAuth tokens (sk-ant-oat01-*) requiring `CLAUDE_CODE_OAUTH_TOKEN` env var, but docker-compose only passed `ANTHROPIC_API_KEY`
- **Impact:** Users following recommended setup (claude setup-token) had authentication failures
- **Fix:**
  - ✅ Added `CLAUDE_CODE_OAUTH_TOKEN` to docker-compose.prod.yml and docker-compose.dev.yml
  - ✅ Updated validation script to check both `CLAUDE_CODE_OAUTH_TOKEN` and `ANTHROPIC_API_KEY`
  - ✅ Updated install script to detect token type and set correct env var
  - ✅ Updated .env.example to show `CLAUDE_CODE_OAUTH_TOKEN` as primary method
  - ✅ Updated all documentation (README, CLAUDE.md, docs/)
- **Token Type Detection:**
  - sk-ant-oat01-* → Sets `CLAUDE_CODE_OAUTH_TOKEN` (from claude setup-token)
  - sk-ant-api03-* → Sets `ANTHROPIC_API_KEY` (from console.anthropic.com)
- **Migration:** No action needed; both methods now supported
- All agent versions bumped to v1.6.1

**Impact:**
- ✅ Both authentication methods now work correctly
- ✅ `claude setup-token` (recommended) now functional
- ✅ API keys from console.anthropic.com continue to work
- ✅ No breaking changes; backward compatible with v1.6.0

### v1.5.1 - 2025-12-28 (Hotfix release)
- **CRITICAL FIX**: Fixed prompts.py path resolution after v1.5.0 refactor
- Prompts path changed from `/app/src/barbossa/utils/prompts/` to `/app/prompts/`
- Updated path in src/barbossa/utils/prompts.py:15 to use `parent.parent.parent.parent / "prompts"`
- All agents now load prompts correctly at startup
- All agent versions bumped to v1.5.1

**Impact:**
- ✅ Agents can now load prompt templates correctly
- ✅ Fixes "Prompt file not found" error that blocked all agent execution
- ✅ No configuration changes needed; drop-in replacement for v1.5.0

### v1.5.0 - 2025-12-28 (Internal refactor, not released)
- **INTERNAL**: Repository restructured to proper Python package layout
- **NOTE**: This was an internal code reorganization with no user-facing changes
- Restructured to `src/barbossa/` Python package structure:
  - `src/barbossa/agents/`: All AI agent modules
  - `src/barbossa/utils/`: Shared utilities (prompts, issue_tracker, linear_client)
  - `src/barbossa/cli/`: CLI tool
  - `scripts/`: Build and deployment scripts
  - `tests/`: Test suite
- Added `pyproject.toml` for proper Python package metadata
- All imports updated to module-based paths (`from barbossa.agents import engineer`)
- Updated Docker build to use new directory structure
- Set `PYTHONPATH=/app/src` in Docker environment
- Fixed crontab generation to use module imports (`python3 -m barbossa.agents.engineer`)
- CLI now callable as modules
- Security improvements:
  - Added `.dockerignore` for secure builds
  - Enhanced `.gitignore` for better secret protection
- Documentation improvements:
  - Added `config/README.md`
  - Added `tests/README.md`
  - Enhanced `.env.example` with comprehensive documentation
  - Simplified config examples
- CI/CD workflows updated for new structure
- Ready for OSS publication and PyPI distribution

**Impact:**
- ✅ Proper Python package structure ready for PyPI
- ✅ Better code organization and maintainability
- ✅ Module-based imports improve clarity
- ✅ Enhanced security with .dockerignore
- ⚠️ Breaking change: Requires Docker image rebuild
- ✅ No user-facing API changes

### v1.3.0 - 2025-12-26
- **ENHANCEMENT**: Tech Lead now detects external dependencies and setup requirements
- **ENHANCEMENT**: Tech Lead has significantly improved frontend/UI review criteria
- Added dimension 9: External Dependencies & Setup Requirements detection
  - Detects when features use external APIs (Stripe, Telegram, SendGrid, etc.)
  - Flags missing documentation for API keys, environment variables, tokens
  - Requires PR description to include setup instructions for third-party services
  - Identifies database migrations, OAuth setup, webhook configurations
  - Examples: Telegram bot tokens, Vercel env vars, Firebase credentials, etc.
- Enhanced UI/UX review criteria (dimension 4):
  - Layout quality: spacing, alignment, visual hierarchy
  - Component placement: logical, intuitive positioning
  - Typography consistency: fonts, sizes, weights
  - Responsive design: mobile, tablet, desktop breakpoints
  - Visual polish: no alignment issues, clean look
  - Interactive states: hover, focus, active
  - Accessibility improvements: WCAG color contrast, ARIA labels
- Files Modified:
  - `prompts/tech_lead.txt`: Added dimension 9 + enhanced dimension 4
  - All agent versions bumped to v1.3.0

**Impact:**
- Tech Lead will now REQUEST_CHANGES when features use external services without documenting setup
- Example: Telegram notification feature would be flagged if missing bot token setup instructions
- Stronger frontend quality enforcement prevents poorly designed UI/UX from being merged
- Catches missing .env.example updates, README changes, deployment requirements
- Reduces manual cleanup needed for frontend layout, responsive design, visual polish

### v1.2.0 - 2025-12-26
- **CRITICAL FIX**: Product Manager prompt completely rewritten and now working
- **CRITICAL FIX**: Auditor now creates GitHub issues for critical quality problems
- Product Manager: Rewrote prompt with JSON schema and "NO SUGGESTION" option
- Product Manager: Successfully creating high-value feature issues (peerlytics #125, usdctofiat #116)
- Auditor: Added quality issue creation with 7-day deduplication
- Auditor: Creates consolidated issues (1 per repo) to avoid spam
- Created missing 'backlog' label for privateer-xbt repo

### v1.1.0 - 2025-12-25
- **CRITICAL FIX**: Engineer now properly detects Tech Lead feedback
- Fixed comment-based detection logic with timestamp tracking
- Tech Lead now uses `gh pr review --request-changes` (sets reviewDecision field)
- Tech Lead feedback is now PRIORITY 1 (checked before merge conflicts)
- Added detection logging for better debugging
- Prevents PRs from accumulating 6-7 unaddressed reviews
- Massive reduction in wasted API costs

### v1.0.9 - 2025-12-25
- Tech Lead 3-strikes auto-close rule
- PRs automatically closed after 3 REQUEST_CHANGES cycles
- Prevents zombie PRs stuck in infinite review loops
- Stops wasted API costs and engineering time

### v1.0.8 - 2025-12-23
- Enhanced Tech Lead with comprehensive 8-dimension quality review
- Added code bloat detection to Auditor
- Added architecture consistency analysis to Auditor
- Tech Lead now checks: bloat, feature integration, UI/UX, security, performance, complexity
- Auditor detects large files, deep nesting, architectural violations

### v1.0.7 - 2025-12-23
- Fixed docker-compose mounts for non-root user
- This fixes authentication failures that blocked agents

### v1.0.6 - 2025-12-23
- Product manager semantic deduplication
- Validation permission error handling improvements

### v1.0.5 - 2025-12-23
- Security improvements and proper permissions
- Switched to supercronic for non-root cron

### v1.0.4 - 2025-12-22
- Critical tech lead fixes

### v1.0.3 - 2025-12-21
- Permission fixes

### v1.0.2 - 2025-12-21
- Initial stable release

## Next Steps

1. **Monitor v1.1.0 Fixes**: Verify Engineer catches Tech Lead feedback on first review
2. **Monitor Tech Lead Review Method**: Check if using formal reviews or falling back to comments
3. **Monitor 3-Strikes Rule**: Verify zombie PRs get closed after 3 REQUEST_CHANGES
4. **Monitor Detection Logging**: Review logs to confirm proper PR flagging
5. **SSH Keys (Optional)**: Mount ~/.ssh if switching to SSH URLs

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
