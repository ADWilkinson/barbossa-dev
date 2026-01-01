# Agents

Five autonomous agents work on your codebase.

---

## Overview

| Agent | Purpose |
|-------|---------|
| **Engineer** | Picks tasks from backlog, creates PRs |
| **Tech Lead** | Reviews PRs, merges or requests changes |
| **Discovery** | Finds TODOs, missing tests, issues |
| **Product Manager** | Proposes high-value features |
| **Auditor** | Monitors system health |

---

## Pipeline

```
Discovery + Product Manager
           ↓
     GitHub Issues (backlog)
           ↓
        Engineer → Pull Request
           ↓
       Tech Lead → Merge/Reject
```

---

## How Each Agent Works

### Engineer
Picks tasks from the GitHub Issues backlog and implements them.
- Finds issues labeled `backlog`
- Implements the fix/feature
- Creates a pull request
- Links PR to issue with `Closes #XX`

### Tech Lead
Reviews pull requests with comprehensive quality analysis and decides whether to merge or request changes.
- Checks CI status (must pass)
- 8-dimension quality review: code quality, feature bloat, UI/UX, tests, security, performance, complexity, integration
- Detects bloated code, duplicate functionality, accessibility issues
- 3-strikes rule: Auto-closes PRs after 3 failed review cycles to prevent wasted effort
- Merges good PRs automatically (default behavior)
- Requests changes on weak PRs
- Set `auto_merge: false` in config to require manual merges

### Discovery
Scans the codebase for technical debt and creates GitHub Issues.
- TODO and FIXME comments
- Missing tests
- Accessibility issues

### Product Manager
Analyzes the codebase and proposes high-value features.
- Reads CLAUDE.md to understand the product
- Creates feature issues with acceptance criteria

### Auditor
Monitors system health and identifies patterns.
- Analyzes agent logs
- Tracks PR outcomes
- Detects code bloat patterns (large files, deep nesting, duplicates)
- Validates architecture consistency
- Provides actionable recommendations for quality improvements

---

## Notifications

All agents send Discord webhook notifications when enabled. Get real-time updates on:

- **Run complete** - Summary when agents finish
- **PR created** - When Engineer creates PRs
- **PR merged** - When Tech Lead merges (with scores)
- **Errors** - When something goes wrong

See [Configuration](configuration.html#webhook-notifications) for setup.

---

## Run Manually

```bash
docker exec barbossa barbossa run engineer
docker exec barbossa barbossa run tech-lead
docker exec barbossa barbossa run discovery
```
