# Changelog

All notable changes to Barbossa are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.4] - 2025-12-30

### Fixed
- **macOS Home Directory Access** 🔧
  - Fixed container unable to access /home/barbossa when running as macOS host UID
  - Changed /home/barbossa permissions from 700 to 750 (group-accessible)
  - Now UID 501 (macOS) with GID 1000 can access mounted credentials
  - Completes the macOS credentials fix from v1.5.3

### Technical
- Dockerfile: Added `chmod 750 /home/barbossa` after user creation
- Permissions: drwxr-x--- (owner full, group read+execute, other none)

## [1.5.3] - 2025-12-30

### Fixed
- **macOS Credential Access** 🔧
  - Fixed "Permission denied" errors when accessing ~/.config/gh and ~/.claude on macOS
  - Container now runs as host UID with GID=1000 instead of fixed 1000:1000
  - install.sh automatically detects macOS and creates .env with UID=$(id -u)
  - /app directories made group-writable (775) for cross-UID access
  - Linux behavior unchanged (defaults to 1000:1000)

### Changed
- **Dockerfile:** /app is now group-writable (chmod g+w) for macOS compatibility
- **docker-compose.prod.yml:** Added `user: "${UID:-1000}:1000"` for dynamic UID
- **docker-compose.dev.yml:** Added `user: "${UID:-1000}:1000"` for dynamic UID
- **install.sh:** Auto-detects macOS and creates .env file with host UID
- **CLAUDE.md:** Added macOS Permissions Fix section with troubleshooting

### How It Works
- **Linux:** Runs as 1000:1000 (default) - no changes needed
- **macOS:** Runs as host UID (e.g., 501) with GID 1000
  - Can read host credentials (same UID as host user)
  - Can write to /app (member of group 1000, directories are group-writable)

## [1.5.2] - 2025-12-30

### Added
- **macOS Platform Support** 🍎
  - Added `platform: linux/amd64` to docker-compose.prod.yml and docker-compose.dev.yml
  - Works on macOS Intel (native) and Apple Silicon (via Rosetta 2 emulation)
  - Docker transparently handles emulation on Apple Silicon
  - Updated README.md with platform support section
  - Updated CLAUDE.md with platform architecture documentation
  - Updated docs/firebase.md with version 1.5.2 and platform info

### Changed
- **Documentation Updates**
  - README now explicitly lists Linux x86_64, macOS Intel, and macOS Apple Silicon as supported
  - CLAUDE.md documents platform architecture and design rationale
  - Firebase docs updated to v1.5.2 across all version references

### Technical
- All agents bumped to v1.5.2
- Firebase CLIENT_VERSION updated to 1.5.2
- No code changes - purely platform configuration

## [1.4.0] - 2025-12-28

### Added
- **Linear Issue Tracker Integration** 🎉
  - Full support for Linear as an alternative to GitHub Issues
  - Unified `IssueTracker` abstraction layer works with both GitHub and Linear
  - All agents (Engineer, Discovery, Product, Auditor) support Linear seamlessly
  - Auto-linking to Linear issues via branch naming: `barbossa/MUS-14-description`
  - Configuration via `issue_tracker` in `config/repositories.json`
  - New files: `linear_client.py`, `issue_tracker.py`

- **Comprehensive Test Suite** ✅
  - `test_linear_client.py`: 15+ tests covering API calls, security, error handling
  - `test_issue_tracker.py`: Tests for both GitHub and Linear implementations
  - Tests prevent GraphQL injection, verify retry logic, validate abstraction layer
  - All tests use mocking to avoid actual API calls

- **Startup Validation for Linear**
  - `validate.py` now checks Linear configuration on startup
  - Verifies `LINEAR_API_KEY` environment variable is set
  - Tests API connectivity to `api.linear.app`
  - Confirms team exists and user has access
  - Prevents silent failures with Linear misconfiguration

### Security
- **Fixed GraphQL Injection Vulnerability** (Critical) 🔒
  - `linear_client.py` now uses proper GraphQL variables instead of string formatting
  - Prevents injection attacks via malicious titles/descriptions
  - Mutation queries use `$input` variables with type validation
  - Removed unsafe `_escape_string()` method

### Changed
- **Rate Limiting & Retry Logic** 🔄
  - Added `@retry_on_rate_limit` decorator for all Linear API calls
  - Exponential backoff with jitter for 429 rate limit responses
  - Retries transient failures (timeouts, connection errors)
  - Max 3 retries before raising exception

- **Improved Error Handling**
  - All Linear API methods now have try/except with detailed error messages
  - Better error context propagation (no more silent failures)
  - GraphQL errors raise `ValueError` with error messages
  - Logging includes full error context for debugging

- **Agent Version Bumps**
  - All agents bumped to v1.4.0 for Linear support
  - `barbossa_engineer.py`: Injects Linear issues into prompts
  - `barbossa_discovery.py`: Uses abstraction for issue creation
  - `barbossa_product.py`: Creates feature issues in Linear
  - `barbossa_auditor.py`: Uses abstraction for quality issues

### Documentation
- **Updated CLAUDE.md**
  - New "Issue Tracking" section with Linear setup guide
  - Documented GitHub vs Linear behavioral differences
  - Added validation requirements and troubleshooting

- **Updated README.md** (contributor: @puniaviision)
  - Linear configuration examples
  - Environment variable setup instructions
  - Team key and backlog state configuration

## [1.0.3] - 2024-12-21

### Fixed
- **Permission errors**: Removed unnecessary `barbossa` user inside container. All processes now run as root, eliminating permission denied errors for `gh` and `claude` CLI tools.

### Changed
- Simplified container architecture - no more user switching or symlink chains
- Smaller Docker image (removed sudo package)

## [1.0.2] - 2024-12-21

### Changed
- Local prompts: System prompts now loaded from local `prompts/` directory instead of Firebase
- Simplified `barbossa_firebase.py` to analytics-only (optional)
- Agents work fully offline

## [1.0.1] - 2024-12-21

### Changed
- Improved README and setup instructions

## [1.0.0] - 2024-12-16

### Added
- **Five-agent autonomous pipeline**: Engineer, Tech Lead, Discovery, Product Manager, Auditor
- **Docker-based deployment** with automatic crash recovery
- **CLI tool** (`barbossa`) for health checks, manual runs, and status
- **Configurable schedules** for all agents
- **Firebase integration** for cloud infrastructure and auditor insights
- **llms.txt** for AI-assisted configuration
- **Comprehensive documentation site** at barbossa.dev
- **GitHub Actions workflows** for CI and releases
- **JSON Schema validation** for configuration

### Features by Agent
- **Engineer**: Picks tasks from GitHub Issues backlog, implements changes, creates PRs
- **Tech Lead**: Reviews PRs with value/quality scoring, auto-merges or requests changes
- **Discovery**: Finds TODOs, FIXMEs, missing tests, accessibility issues
- **Product Manager**: Proposes high-value features based on codebase analysis
- **Auditor**: Daily health monitoring and pattern identification

### Configuration Options
- Multiple repository support
- Package manager detection (npm, yarn, pnpm, bun)
- Protected files/directories (`do_not_touch`)
- Tech stack hints for better AI context
- Focus areas for prioritization
- Auto-merge toggle for Tech Lead

### Infrastructure
- Docker Compose orchestration
- Cron-based scheduling
- Session logging
- Health check endpoints
- GitHub Container Registry publishing

---

## Migration Notes

### From Pre-1.0 Versions
1. Configuration moved to `config/repositories.json`
2. CLI commands changed to `docker exec barbossa barbossa <command>`
3. Web portal replaced by Firebase-hosted docs
4. Simplified authentication flow using `gh` and `claude` CLIs

[Unreleased]: https://github.com/ADWilkinson/barbossa-dev/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ADWilkinson/barbossa-dev/releases/tag/v1.0.0
