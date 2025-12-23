# Barbossa Engineer - Claude Context

**Last Updated:** 2025-12-23
**Version:** v1.0.7 (pending release)

## Project Overview

Barbossa is an autonomous AI development team powered by Claude that manages GitHub repositories automatically. It consists of multiple specialized agents that work together to maintain codebases, review PRs, discover improvements, manage issues, and more.

## Project Structure

```
barbossa-engineer/
├── barbossa_engineer.py      # Main engineer agent - implements features from backlog
├── barbossa_tech_lead.py     # Tech lead agent - reviews and merges PRs
├── barbossa_discovery.py     # Discovery agent - finds code improvements
├── barbossa_product.py       # Product manager - creates feature issues
├── barbossa_auditor.py       # Auditor - system health checks
├── barbossa_firebase.py      # Firebase sync (future)
├── barbossa_prompts.py       # Shared prompt templates
├── barbossa                  # CLI tool for manual operations
├── validate.py               # Startup validation script
├── generate_crontab.py       # Crontab generator from config
├── entrypoint.sh             # Docker entrypoint
├── Dockerfile                # Container definition (runs as non-root)
├── docker-compose.yml        # Service orchestration
├── config/
│   └── repositories.json     # Repository configuration
├── prompts/                  # Local prompt templates
├── logs/                     # Agent execution logs
├── changelogs/               # Generated changelogs
└── projects/                 # Cloned repositories
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

## Recent Enhancements (v1.0.8)

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

## Security Model

### Non-Root Container Execution
- Container runs as user `barbossa` (UID 1000, GID 1000)
- Created via: `useradd -m -u 1000 -s /bin/bash barbossa`
- Working directory `/app` owned by `barbossa:barbossa`
- Enhances security by preventing root-level container breakouts

### Authentication
- GitHub CLI authentication via mounted `~/.config/gh/`
- Claude CLI authentication via mounted `~/.claude/`
- Git commits signed as configured user
- No secrets stored in environment variables

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

### v1.0.8 (pending) - 2025-12-23
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

1. **Release v1.0.8** - Tag and release with enhanced quality checks
2. **Monitor Tech Lead Reviews** - Verify deeper quality analysis in PR reviews
3. **Monitor Auditor Reports** - Check for bloat and architecture warnings
4. **SSH Keys (Optional)** - Mount ~/.ssh if switching to SSH URLs

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
