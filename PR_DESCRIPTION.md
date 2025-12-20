# Barbossa Open Source Productization

## Overview

This PR transforms Barbossa from an internal tool into a production-ready open source project with cloud infrastructure for system prompts, version management, and transparent usage tracking.

**Branch:** `claude/barbossa-productization-strategy-k5pdf`
**Commits:** 20 commits
**Files Changed:** 52 files (+7,002 / -4,801 lines)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Changes](#key-changes)
3. [New Files Reference](#new-files-reference)
4. [Firebase Cloud Infrastructure](#firebase-cloud-infrastructure)
5. [Configuration System](#configuration-system)
6. [Agent System](#agent-system)
7. [Documentation](#documentation)
8. [Testing & Validation](#testing--validation)
9. [Deployment](#deployment)
10. [Known Issues & Future Work](#known-issues--future-work)
11. [Handover Checklist](#handover-checklist)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BARBOSSA ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────┐     ┌──────────────────────────────────────┐    │
│   │   Firebase   │     │           Docker Container            │    │
│   │    Cloud     │     │                                        │    │
│   ├──────────────┤     │  ┌────────────────────────────────┐  │    │
│   │ • Prompts    │────▶│  │     barbossa_firebase.py       │  │    │
│   │ • Versions   │     │  │  (fetches prompts at startup)  │  │    │
│   │ • Users      │     │  └────────────────────────────────┘  │    │
│   └──────────────┘     │              │                        │    │
│                        │              ▼                        │    │
│                        │  ┌────────────────────────────────┐  │    │
│                        │  │        5 AI Agents             │  │    │
│                        │  │  • Product Manager (3x daily)  │  │    │
│                        │  │  • Discovery (4x daily)        │  │    │
│                        │  │  • Engineer (every 2h)         │  │    │
│                        │  │  • Tech Lead (every 2h)        │  │    │
│                        │  │  • Auditor (daily)             │  │    │
│                        │  └────────────────────────────────┘  │    │
│                        │              │                        │    │
│                        │              ▼                        │    │
│                        │  ┌────────────────────────────────┐  │    │
│                        │  │     GitHub (Source of Truth)   │  │    │
│                        │  │  • Issues → Backlog            │  │    │
│                        │  │  • PRs → Work in Progress      │  │    │
│                        │  │  • Comments → Feedback         │  │    │
│                        │  └────────────────────────────────┘  │    │
│                        └────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Changes

### 1. Open Source Model
- Removed web portal (`web_portal/app_simple.py` - 1,795 lines deleted)
- Removed productization strategy docs (keeping code clean)
- Added MIT License
- Added CONTRIBUTING.md
- Created comprehensive documentation in `/docs`

### 2. Firebase Cloud Infrastructure
- **NEW:** `barbossa_firebase.py` - Central client for cloud interactions
- **NEW:** `functions/index.js` - Cloud Functions (prompts, versions, users)
- **NEW:** `firebase.json`, `firestore.rules`, `.firebaserc`
- System prompts now served from cloud (enables OTA updates)
- Anonymous unique user counting (transparent, no analytics)
- Version compatibility checking

### 3. Simplified Configuration
- **Minimal config:** Just 3 fields required (`owner`, `repositories[].name`, `repositories[].url`)
- **Advanced config:** Full customization available
- **NEW:** `generate_crontab.py` - Dynamic schedule generation from config
- **NEW:** `validate.py` - Startup validation with helpful error messages
- Schedule presets: `every_hour`, `every_2_hours`, `3x_daily`, `4x_daily`, `disabled`

### 4. CLI Tool
- **NEW:** `barbossa` CLI script
- Commands: `init`, `health`, `run [agent]`, `status`, `logs [agent]`
- Interactive setup wizard
- Health checks for config, auth, repos

### 5. Documentation Site
- **NEW:** `docs-site/` - Static site generator
- **NEW:** `docs-site/build.py` - Markdown to HTML converter
- **NEW:** `docs-site/public/` - Generated HTML files
- Designed for Firebase Hosting deployment

---

## New Files Reference

### Core Application

| File | Purpose | Key Functions |
|------|---------|---------------|
| `barbossa` | CLI tool | `cmd_init()`, `cmd_health()`, `cmd_run()`, `cmd_status()`, `cmd_logs()` |
| `barbossa_firebase.py` | Firebase client | `get_prompt()`, `check_version()`, `register_installation()` |
| `validate.py` | Startup validation | `validate_config()`, `validate_claude()`, `validate_github()` |
| `generate_crontab.py` | Cron generator | `resolve_schedule()`, `generate_crontab()` |

### Firebase Functions

| File | Purpose | Endpoints |
|------|---------|-----------|
| `functions/index.js` | Cloud Functions | `/getPrompt`, `/checkVersion`, `/registerInstallation` |

### Documentation

| File | Purpose |
|------|---------|
| `docs/quickstart.md` | 5-minute setup guide |
| `docs/configuration.md` | Full config reference |
| `docs/agents.md` | Agent behavior documentation |
| `docs/faq.md` | Frequently asked questions |
| `docs/troubleshooting.md` | Common issues and fixes |

### GitHub Actions

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | PR validation (config, Python lint) |
| `.github/workflows/release.yml` | Automated releases with Docker image |

---

## Firebase Cloud Infrastructure

### Project Details
- **Project ID:** `barbossa-dev`
- **Region:** `us-central1`
- **Functions URL:** `https://us-central1-barbossa-dev.cloudfunctions.net`

### Cloud Functions

#### 1. `getPrompt` - System Prompt Delivery
```
GET /getPrompt?agent=engineer&version=5.2.0
Response: { prompt: "...", version: "5.2.0" }
```
- Returns system prompt for specified agent
- Prompts are defined inline in `functions/index.js`
- All 5 agents have prompts: engineer, tech_lead, discovery, product_manager, auditor

#### 2. `checkVersion` - Version Compatibility
```
GET /checkVersion?version=5.2.0
Response: { compatible: true, minVersion: "5.0.0", latestVersion: "5.2.0" }
```
- Checks if client version is compatible
- Returns min/latest versions for upgrade prompts

#### 3. `registerInstallation` - Unique User Counting
```
POST /registerInstallation
Body: { installationId: "sha256hash...", version: "5.2.0" }
```
- Stores anonymous installation ID in Firestore
- Used only for counting unique users (transparent)
- Installation ID is SHA256 hash of hostname + home directory

### Firestore Collections
- `installations` - Unique user tracking
- `prompts` (future) - Could store prompts in DB instead of code

### Security Rules (`firestore.rules`)
```javascript
match /installations/{doc} {
  allow read, write: if request.auth == null; // Public write for registration
}
```

---

## Configuration System

### Minimal Config (`config/repositories.json`)
```json
{
  "owner": "github-username",
  "repositories": [
    {
      "name": "my-repo",
      "url": "git@github.com:username/my-repo.git"
    }
  ]
}
```

### Full Config Structure
```json
{
  "owner": "github-username",
  "repositories": [
    {
      "name": "repo-name",
      "url": "git@github.com:username/repo.git",
      "description": "Optional description for context",
      "tech_stack": ["typescript", "react", "postgres"],
      "architecture": "Next.js App Router with tRPC",
      "design_system": "shadcn/ui components",
      "focus_areas": ["performance", "testing"],
      "do_not_touch": ["prisma/migrations/", ".env*"]
    }
  ],
  "settings": {
    "schedule": {
      "engineer": "every_2_hours",
      "tech_lead": "every_2_hours",
      "discovery": "4x_daily",
      "product_manager": "3x_daily",
      "auditor": "daily_morning"
    },
    "engineer": { "enabled": true },
    "tech_lead": {
      "enabled": true,
      "auto_merge": true,
      "min_lines_for_tests": 50,
      "max_files_per_pr": 15,
      "stale_days": 5
    },
    "discovery": {
      "enabled": true,
      "max_backlog_issues": 20
    },
    "product_manager": {
      "enabled": true,
      "max_issues_per_run": 3,
      "max_feature_issues": 20
    },
    "auditor": {
      "enabled": true,
      "analysis_days": 7
    }
  }
}
```

### Schedule Presets
| Preset | Cron Expression | Description |
|--------|-----------------|-------------|
| `every_hour` | `0 * * * *` | Every hour |
| `every_2_hours` | `0 0,2,4,...` | Every 2 hours |
| `every_3_hours` | `0 0,3,6,...` | Every 3 hours |
| `every_4_hours` | `0 0,4,8,...` | Every 4 hours |
| `every_6_hours` | `0 0,6,12,18` | 4x daily |
| `2x_daily` | `0 9,18 * * *` | Morning + evening |
| `3x_daily` | `0 7,15,23 * * *` | 3x daily |
| `4x_daily` | `0 0,6,12,18 * * *` | 4x daily |
| `daily_morning` | `0 9 * * *` | Once daily at 9am |
| `disabled` | None | Agent disabled |

---

## Agent System

### Agent Files & Responsibilities

| Agent | File | Schedule | Purpose |
|-------|------|----------|---------|
| **Product Manager** | `barbossa_product.py` | 3x daily | Discovers valuable features, creates specs |
| **Discovery** | `barbossa_discovery.py` | 4x daily | Finds tech debt, creates issues |
| **Engineer** | `barbossa_engineer.py` | Every 2h | Implements issues, creates PRs |
| **Tech Lead** | `barbossa_tech_lead.py` | Every 2h | Reviews PRs, merges/rejects |
| **Auditor** | `barbossa_auditor.py` | Daily | System health, self-healing |

### Agent Integration with Firebase
Each agent now uses `barbossa_firebase.py`:
```python
from barbossa_firebase import BarbossaFirebase

firebase = BarbossaFirebase()
prompt = firebase.get_prompt("engineer", context)
```

### Tech Lead Review Criteria
- CI must pass → auto-reject if failing
- >50 lines without tests → auto-reject
- >15 files changed → auto-reject (scope creep)
- Test-only PRs → auto-reject (low value)
- Value Score ≥7, Quality Score ≥7, Bloat LOW → MERGE
- Otherwise → REQUEST_CHANGES or CLOSE

### Auditor Self-Healing Actions
1. OAuth token expiry check (warns if <24h)
2. Stale session cleanup (>3h running → timeout)
3. Old log cleanup (>14 days → delete)
4. Pending feedback reset (>24h → clear)

---

## Documentation

### Structure
```
docs/
├── quickstart.md      # 5-minute setup guide
├── configuration.md   # Full config reference
├── agents.md          # Agent behavior docs
├── faq.md             # Common questions
└── troubleshooting.md # Issue resolution

docs-site/
├── build.py           # MD → HTML converter
└── public/
    ├── index.html     # Landing page
    ├── quickstart.html
    ├── configuration.html
    ├── agents.html
    ├── faq.html
    └── troubleshooting.html
```

### Building Docs
```bash
python3 docs-site/build.py
# Output: docs-site/public/*.html
```

### Deploying to Firebase Hosting
```bash
firebase deploy --only hosting
```

---

## Testing & Validation

### Startup Validation (`validate.py`)
Runs automatically on container start:
1. ✓ Config file exists and valid JSON
2. ✓ Owner field present
3. ✓ At least one repository configured
4. ✓ Claude CLI authenticated
5. ✓ GitHub CLI authenticated
6. ✓ SSH keys accessible
7. ✓ Repository access verified

### Manual Health Check
```bash
barbossa health
```

### CI Pipeline (`.github/workflows/ci.yml`)
- Validates config examples are valid JSON
- Runs Python linting
- Checks that documentation builds

---

## Deployment

### Docker Compose (Production)
```yaml
services:
  barbossa:
    build: .
    container_name: barbossa
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ~/.claude:/home/barbossa/.claude
      - ~/.ssh:/home/barbossa/.ssh:ro
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - TZ=UTC
    restart: unless-stopped
```

### Quick Start
```bash
git clone https://github.com/ADWilkinson/barbossa-engineer.git
cd barbossa-engineer
cp config/repositories.json.example config/repositories.json
# Edit config with your repos
docker compose up -d
```

### Release Process (`.github/workflows/release.yml`)
1. Tag a release: `git tag v5.2.0 && git push --tags`
2. Workflow builds Docker image
3. Pushes to GitHub Container Registry
4. Creates GitHub Release with changelog

---

## Known Issues & Future Work

### Known Issues
1. **Firebase Functions not deployed** - Need to run `firebase deploy --only functions`
2. **Auditor not integrated with Firebase** - Still uses local prompts (low priority)
3. **No rate limiting on Cloud Functions** - Should add for production

### Future Work (Roadmap)
- [ ] GitLab support
- [ ] Slack notifications
- [ ] Linear integration
- [ ] Custom agent schedules per repository
- [ ] Web dashboard for monitoring
- [ ] Prompt A/B testing via Firebase Remote Config

---

## Handover Checklist

### Before Merging
- [ ] Review all 20 commits
- [ ] Test Docker build: `docker compose build`
- [ ] Test container start: `docker compose up`
- [ ] Verify config validation works
- [ ] Check Firebase project exists and is configured

### After Merging
- [ ] Deploy Firebase Functions: `cd functions && npm install && firebase deploy --only functions`
- [ ] Deploy Firebase Hosting: `firebase deploy --only hosting`
- [ ] Create first GitHub Release
- [ ] Update repository description and topics
- [ ] Enable GitHub Discussions

### Firebase Deployment
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login and select project
firebase login
firebase use barbossa-dev

# Deploy functions
cd functions
npm install
cd ..
firebase deploy --only functions

# Deploy hosting
python3 docs-site/build.py
firebase deploy --only hosting
```

### Testing the Full Pipeline
```bash
# 1. Build and start
docker compose up -d

# 2. Check health
docker exec barbossa barbossa health

# 3. Run engineer manually
docker exec barbossa python3 barbossa_engineer.py

# 4. Check logs
docker exec barbossa cat /app/logs/barbossa_engineer.log
```

---

## File Changes Summary

### Added (27 files)
- `barbossa` - CLI tool
- `barbossa_firebase.py` - Firebase client
- `validate.py` - Startup validation
- `generate_crontab.py` - Cron generator
- `functions/index.js` - Cloud Functions
- `functions/package.json`
- `firebase.json`, `firestore.rules`, `firestore.indexes.json`, `.firebaserc`
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`
- `CONTRIBUTING.md`, `LICENSE`
- `docs/*.md` (5 files)
- `docs-site/build.py`
- `docs-site/public/*.html` (6 files)
- `config/repositories.json.example`
- `config/repositories.advanced.json.example`

### Modified (13 files)
- `README.md` - Complete rewrite for open source
- `Dockerfile` - Updated for barbossa user, new scripts
- `docker-compose.yml` - Updated volume mounts
- `entrypoint.sh` - Dynamic crontab generation
- `run.sh` - Simplified
- All 5 agent files - Firebase integration

### Deleted (12 files)
- `web_portal/app_simple.py` - Removed web portal
- `start_portal.sh`
- `config/barbossa.example.json` - Replaced with simpler config
- `config/repositories.json` - Now user-created
- `docs/PRODUCTIZATION_STRATEGY.md`
- Various state files (sessions.json, tech_lead_decisions.json, etc.)

---

## Contact

For questions about this PR:
- **Author:** Claude (via Claude Code)
- **Repository Owner:** @ADWilkinson
