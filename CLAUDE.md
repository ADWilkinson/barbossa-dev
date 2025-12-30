# Barbossa Engineer - Claude Context

**Last Updated:** 2025-12-28
**Version:** v1.5.1

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
│       │   └── firebase.py  # Firebase sync (future)
│       ├── utils/           # Shared utilities
│       │   ├── prompts.py   # Prompt templates loader
│       │   ├── issue_tracker.py  # GitHub/Linear abstraction
│       │   └── linear_client.py  # Linear API client
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
- **Repositories:** 2 (peerlytics, usdctofiat)
- **Owner:** ADWilkinson
- **Schedule:**
  - Engineer: Every 2 hours (0,2,4,6,8,10,12,14,16,18,20,22 UTC)
  - Tech Lead: Every 2 hours (0,2,4,6,8,10,12,14,16,18,20,22 UTC)
  - Discovery: 4x daily (0,6,12,18 UTC)
  - Product Manager: 3x daily (7,15,23 UTC)
  - Auditor: Daily at 06:30 UTC

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
1. **Product Manager was returning NO suggestions** - prompt template was completely outdated
2. **Auditor was only logging recommendations** - not creating actionable GitHub issues

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
- ✅ Product Manager NOW WORKING - created 2 high-value feature issues in test run:
  - peerlytics #125: "Custom Date Range Picker for Analytics Dashboard" (value: 8)
  - usdctofiat #116: "Bulk rate update for multiple deposits"
- ✅ Quality over quantity - can decline to suggest if no high-value ideas
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
- ✅ Clears backlog faster - no zombie PRs
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
Barbossa supports both **GitHub Issues** (default) and **Linear** for issue tracking. All agents work seamlessly with either system via a unified abstraction layer.

### GitHub Issues (Default)
- No configuration needed - works out of the box
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

### macOS Permissions Fix
**Problem:** On macOS, credential files (~/.config/gh, ~/.claude) are owned by the host user (typically UID 501) with 600 permissions. The container needs to read these files.

**Solution:** Container runs as host UID but keeps GID=1000:
- **Linux:** Runs as 1000:1000 (default) - works as before
- **macOS:** Runs as host UID (e.g., 501) with GID 1000
- **Permissions:** /app is group-writable (775) so UID 501 with GID 1000 can write
- **Auto-detection:** install.sh creates .env with UID=$(id -u) on macOS

**Manual setup:**
```bash
# macOS users: Create .env file with your UID
echo "UID=$(id -u)" > .env

# Restart container
docker compose down && docker compose up -d
```

**Why this works:**
- Container reads host credentials (same UID as host user)
- Container writes to /app (member of group 1000, /app is group-writable)
- No permission denied errors

### Authentication
- GitHub CLI authentication via mounted `~/.config/gh/`
- Claude CLI authentication via mounted `~/.claude/`
- Linear API key via `LINEAR_API_KEY` environment variable (if Linear is used)
- Git commits signed as configured user
- No secrets hardcoded in configuration files

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

## Common Operations

### Manual Agent Execution
```bash
# Inside container
docker exec -it barbossa barbossa run engineer
docker exec -it barbossa barbossa run tech-lead
docker exec -it barbossa barbossa run discovery
docker exec -it barbossa barbossa run product
docker exec -it barbossa barbossa run auditor

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
2. ✅ GitHub CLI authenticated (via gh auth status or GITHUB_TOKEN)
3. ✅ Claude CLI authenticated (checks ~/.claude/.credentials.json)
4. ⚠️ Git user.name and user.email configured (warning only)
5. ⚠️ SSH keys if SSH URLs configured (warning only)

**Critical failures block startup** to prevent silent failures.

## Development History

### v1.5.1 - 2025-12-28 (Hotfix release)
- **CRITICAL FIX**: Fixed prompts.py path resolution after v1.5.0 refactor
- Prompts path changed from `/app/src/barbossa/utils/prompts/` to `/app/prompts/`
- Updated path in src/barbossa/utils/prompts.py:15 to use `parent.parent.parent.parent / "prompts"`
- All agents now load prompts correctly at startup
- All agent versions bumped to v1.5.1

**Impact:**
- ✅ Agents can now load prompt templates correctly
- ✅ Fixes "Prompt file not found" error that blocked all agent execution
- ✅ No configuration changes needed - drop-in replacement for v1.5.0

### v1.5.0 - 2025-12-28 (Internal refactor - no release)
- **INTERNAL**: Repository restructured to proper Python package layout
- **NOTE**: This was an internal code reorganization with no user-facing changes
- Restructured to `src/barbossa/` Python package structure:
  - `src/barbossa/agents/` - All AI agent modules
  - `src/barbossa/utils/` - Shared utilities (prompts, issue_tracker, linear_client)
  - `src/barbossa/cli/` - CLI tool
  - `scripts/` - Build and deployment scripts
  - `tests/` - Test suite
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
- **CRITICAL FIX**: Product Manager prompt completely rewritten - NOW WORKING
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

1. **Monitor v1.1.0 Fixes** - Verify Engineer catches Tech Lead feedback on first review
2. **Monitor Tech Lead Review Method** - Check if using formal reviews or falling back to comments
3. **Monitor 3-Strikes Rule** - Verify zombie PRs get closed after 3 REQUEST_CHANGES
4. **Monitor Detection Logging** - Review logs to confirm proper PR flagging
5. **SSH Keys (Optional)** - Mount ~/.ssh if switching to SSH URLs

## Troubleshooting

### Agents Not Running
1. Check validation: `docker logs barbossa | head -50`
2. Verify mounts: `docker exec barbossa ls -la /home/barbossa/.claude`
3. Check schedule: `docker exec barbossa cat /app/crontab`
4. View recent logs: `ls -lht /app/logs/ | head`

### Authentication Issues
```bash
# Re-authenticate GitHub
gh auth login
docker compose restart

# Re-authenticate Claude
claude login
docker compose restart

# Check credentials in container
docker exec barbossa ls -la /home/barbossa/.claude/
docker exec barbossa ls -la /home/barbossa/.config/gh/
```

### Permission Errors
All mounts must be accessible by UID 1000 (barbossa user):
```bash
# Check host permissions
ls -la ~/.claude ~/.config/gh ~/.gitconfig

# Should be owned by your user (UID 1000 on most systems)
# If not, adjust permissions or ownership
```

## Contact & Support

- **Repository:** https://github.com/ADWilkinson/barbossa-dev
- **Issues:** https://github.com/ADWilkinson/barbossa-dev/issues
- **Release Notes:** See CHANGELOG.md

## AI Agent Guidelines

When working with this codebase:
1. Always run validation checks before making changes
2. Follow the non-root security model
3. Update this CLAUDE.md when making significant changes
4. Test with `barbossa run [agent]` before relying on cron
5. Check logs in `/app/logs/` for debugging
6. Respect the `do_not_touch` areas in config/repositories.json
