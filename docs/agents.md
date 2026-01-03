# Agents

Barbossa has two operating modes with different agent configurations.

---

## Operating Modes

### Autonomous Mode (Default)
Five agents work together in a continuous development pipeline:

| Agent | Purpose |
|-------|---------|
| **Engineer** | Picks tasks from backlog, creates PRs |
| **Tech Lead** | Reviews PRs, merges or requests changes |
| **Discovery** | Finds TODOs, missing tests, issues |
| **Product Manager** | Proposes high-value features |
| **Auditor** | Monitors system health |

### Spec Mode
When `settings.spec_mode.enabled = true`, all autonomous agents are disabled and only the Spec Generator runs:

| Agent | Purpose |
|-------|---------|
| **Spec Generator** | Creates detailed cross-repo product specifications |

---

## Autonomous Mode Pipeline

```
Discovery + Product Manager
           ↓
     GitHub Issues (backlog)
           ↓
        Engineer → Pull Request
           ↓
       Tech Lead → Merge/Reject
```

## Spec Mode Pipeline

```
     Product Configuration
   (linked repos, context)
           ↓
      Spec Generator
           ↓
  Parent Spec (primary repo)
     + Child Tickets
   (per affected repo)
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
- Defers review while CI is pending, and requires evidence + lockfile disclosure
- Skips automated review for oversized diffs and requests manual review

### Discovery
Scans the codebase for technical debt and creates GitHub Issues.
- TODO and FIXME comments
- Loading/error state gaps (balanced mode)
- Accessibility and cleanup heuristics (experimental mode)
- High-precision mode (default) only creates issues with concrete evidence

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

### Spec Generator (Spec Mode Only)
Generates detailed, cross-repo product specifications.
- **Only runs when spec_mode.enabled = true** (disables all other agents)
- Operates on "products" (groups of linked repositories)
- Aggregates context from all repos' CLAUDE.md files
- Uses product context (vision, constraints, strategy notes)
- Creates distributed tickets:
  - Parent spec in `primary_repo` with `spec` label
  - Child implementation tickets in affected repos with `backlog` label
- Semantic deduplication prevents duplicate specs
- Each child ticket is prompt-ready for AI implementation

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
# Autonomous mode agents
docker exec barbossa barbossa run engineer
docker exec barbossa barbossa run tech-lead
docker exec barbossa barbossa run discovery
docker exec barbossa barbossa run product
docker exec barbossa barbossa run auditor

# Spec mode agent
docker exec barbossa barbossa run spec                        # All products
docker exec barbossa barbossa run spec --product my-platform  # Specific product
```
