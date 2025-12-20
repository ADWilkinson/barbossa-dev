# Agent Documentation

Barbossa consists of five specialized agents that work together autonomously.

## Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     BARBOSSA PIPELINE                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Product Manager ──→ Discovery ──→ GitHub Issues            │
│       (3x daily)      (4x daily)      (backlog)             │
│                                          │                   │
│                                          ▼                   │
│                     Engineer ──→ Pull Request                │
│                    (every 2h)                                │
│                                          │                   │
│                                          ▼                   │
│                     Tech Lead ──→ Merge/Reject               │
│                    (every 2h)                                │
│                                          │                   │
│                                          ▼                   │
│                      Auditor ──→ Health Report               │
│                      (daily)                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Product Manager Agent

**File:** `barbossa_product.py`
**Schedule:** 3x daily (07:00, 15:00, 23:00)

### Purpose

Discovers valuable features by analyzing your product, competitive landscape, and user needs.

### What It Does

1. Reads your project's `CLAUDE.md` or `README.md` for context
2. Analyzes the current feature set
3. Identifies gaps and opportunities
4. Creates detailed feature specs as GitHub Issues

### Output

Creates GitHub Issues labeled `feature` and `backlog`:

```markdown
## Feature: Dark Mode Toggle

**Value Score:** 8/10
**Effort:** Medium

### Description
Add a dark mode toggle to the settings page...

### Acceptance Criteria
- [ ] Toggle persists across sessions
- [ ] Respects system preference by default
- [ ] Smooth transition animation
```

### Configuration

Controlled by `product_manager` settings:

```json
{
  "settings": {
    "product_manager": {
      "enabled": true,
      "max_issues_per_run": 3,
      "max_feature_issues": 20
    }
  }
}
```

---

## Discovery Agent

**File:** `barbossa_discovery.py`
**Schedule:** 4x daily (00:00, 06:00, 12:00, 18:00)

### Purpose

Finds technical debt, code smells, and improvement opportunities.

### What It Finds

- `TODO`, `FIXME`, `HACK` comments
- Missing loading states
- Missing error handling
- Accessibility gaps (missing alt text, aria-labels)
- Console.log statements
- Dead code patterns
- Inconsistent patterns

### Output

Creates GitHub Issues labeled `backlog`:

```markdown
## Technical Debt: Add loading state to UserList

**Location:** src/components/UserList.tsx:45

### Problem
Component renders empty state while data is loading.

### Suggested Fix
Add loading skeleton using existing Skeleton component.

### Files to Modify
- src/components/UserList.tsx
```

### Configuration

```json
{
  "settings": {
    "discovery": {
      "enabled": true,
      "max_backlog_issues": 20
    }
  }
}
```

---

## Engineer Agent

**File:** `barbossa_engineer.py`
**Schedule:** Every 2 hours at :00

### Purpose

Implements changes and creates pull requests.

### Workflow

1. **Check Backlog:** Looks for Issues labeled `backlog`
2. **Select Work:** Picks the first available issue
3. **Implement:** Makes code changes
4. **Create PR:** Opens a pull request linked to the issue

### PR Format

```markdown
## Summary
Added loading skeleton to UserList component.

Closes #42

## Changes
- Added Skeleton component import
- Implemented loading state check
- Added loading skeleton UI

## Testing
- Verified loading state appears
- Confirmed data renders after load
```

### Timeout

Each run has a 30-minute timeout. If implementation takes longer, it will retry next cycle.

### Configuration

```json
{
  "settings": {
    "engineer": {
      "enabled": true
    }
  }
}
```

Schedule is configured separately in `settings.schedule.engineer`.

---

## Tech Lead Agent

**File:** `barbossa_tech_lead.py`
**Schedule:** Every 2 hours at :35 (35 min after Engineer)

### Purpose

Reviews pull requests with strict quality criteria.

### Review Criteria

| Criteria | Action |
|----------|--------|
| CI checks failing | Auto-reject |
| >50 lines without tests | Auto-reject |
| >15 files changed | Auto-reject (scope creep) |
| Test-only PRs | Auto-reject (low value) |
| UI changes without tests | Request changes |

### Scoring

Each PR is scored on:
- **Value Score (1-10):** Impact on users/codebase
- **Quality Score (1-10):** Code quality, patterns, tests
- **Bloat Risk:** LOW / MEDIUM / HIGH

### Decisions

| Decision | When |
|----------|------|
| **MERGE** | Value ≥7, Quality ≥7, Bloat LOW, CI passing |
| **REQUEST_CHANGES** | Fixable issues identified |
| **CLOSE** | Low value or unfixable issues |

### Configuration

```json
{
  "settings": {
    "tech_lead": {
      "enabled": true,
      "auto_merge": true,
      "min_lines_for_tests": 50,
      "max_files_per_pr": 15,
      "stale_days": 5
    }
  }
}
```

### Auto-Merge

When `auto_merge: true` (the default), PRs passing quality checks are automatically merged.

---

## Auditor Agent

**File:** `barbossa_auditor.py`
**Schedule:** Daily at 06:30

### Purpose

Monitors system health and identifies improvement opportunities.

### What It Analyzes

- PR merge rate
- Common rejection reasons
- Agent performance patterns
- OAuth token status
- Test coverage trends
- Session failure rates

### Output

Generates `system_insights.json` with recommendations:

```json
{
  "insights": [
    {
      "type": "pattern",
      "finding": "UI components frequently rejected for missing tests",
      "recommendation": "Focus on components in src/components/"
    }
  ],
  "health_score": 85,
  "merge_rate": 87.5
}
```

### Self-Healing Actions

- Validates OAuth tokens
- Cleans stale sessions
- Rotates logs (keeps 14 days)

### Configuration

```json
{
  "settings": {
    "auditor": {
      "enabled": true,
      "analysis_days": 7
    }
  }
}
```

---

## Agent Coordination

### Timing

The schedule ensures agents don't conflict:

```
:00  Engineer starts (has 35 min)
:35  Tech Lead reviews (Engineer's PR exists)
:00  Next cycle begins
```

### GitHub as Source of Truth

All agents use GitHub as the single source of truth:
- Issues for backlog
- PRs for work in progress
- Comments for feedback

No local state files are needed between runs.

### Backlog Management

- Discovery and Product Manager create Issues
- Maximum backlog size is configurable
- When backlog is full, discovery pauses
- Engineer works through backlog in order

---

## Manual Triggers

Run any agent manually:

```bash
# Engineer
docker exec barbossa python3 barbossa_engineer.py

# Tech Lead
docker exec barbossa python3 barbossa_tech_lead.py

# Discovery
docker exec barbossa python3 barbossa_discovery.py

# Product Manager
docker exec barbossa python3 barbossa_product.py

# Auditor
docker exec barbossa python3 barbossa_auditor.py --days 7
```

---

## Disabling Agents

Disable specific agents in configuration:

```json
{
  "settings": {
    "discovery": { "enabled": false },
    "product_manager": { "enabled": false }
  }
}
```

Or set the schedule to `"disabled"` in `settings.schedule`.
