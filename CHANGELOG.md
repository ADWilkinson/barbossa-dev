# Changelog

All notable changes to Barbossa are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
