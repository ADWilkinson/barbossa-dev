# Architecture

How Barbossa works under the hood.

---

## System Overview

Barbossa is a team of five AI agents running in a Docker container. Each agent has a specific role and runs on a schedule.

```
+--------------------------------------------------+
|               DOCKER CONTAINER                    |
|                                                   |
|   +------------------------------------------+   |
|   |           Cron Scheduler                 |   |
|   |      (supercronic - runs on schedule)    |   |
|   +------------------------------------------+   |
|                       |                          |
|       +-------+-------+-------+-------+          |
|       |       |       |       |       |          |
|       v       v       v       v       v          |
|   +-------+-------+-------+-------+-------+      |
|   |Discov-|Product|Engine-| Tech |Auditor|      |
|   |  ery  |  Mgr  |  er   | Lead |       |      |
|   +-------+-------+-------+-------+-------+      |
|                       |                          |
|                       v                          |
|              +----------------+                  |
|              |   Claude CLI   |                  |
|              +----------------+                  |
|                       |                          |
+--------------------------------------------------+
                        |
        +---------------+---------------+
        |               |               |
        v               v               v
   +--------+      +--------+      +--------+
   | GitHub |      | Claude |      | Linear |
   |  API   |      |  API   |      |  API   |
   +--------+      +--------+      +--------+
                        |
                        v
                   +--------+
                   |Discord |
                   |Webhook |
                   +--------+
```

---

## Agent Pipeline

Agents work together in a continuous pipeline:

```
+------------------------------------------+
|          1. DISCOVERY PHASE              |
|                                          |
|  Discovery        Product Manager        |
|  - Scans code     - Analyzes docs        |
|  - Finds TODOs    - Proposes features    |
|  - Missing tests  - User value focus     |
|           \            /                 |
|            v          v                  |
|          GitHub Issues                   |
|        (labeled "backlog")               |
+------------------------------------------+
                    |
                    v
+------------------------------------------+
|        2. IMPLEMENTATION PHASE           |
|                                          |
|            Engineer Agent                |
|  - Picks highest priority issue          |
|  - Reads CLAUDE.md for context           |
|  - Implements fix/feature                |
|  - Creates PR with "Closes #XX"          |
|                   |                      |
|                   v                      |
|            Pull Request                  |
+------------------------------------------+
                    |
                    v
+------------------------------------------+
|           3. REVIEW PHASE                |
|                                          |
|            Tech Lead Agent               |
|  - Waits for CI to pass                  |
|  - 8-dimension quality review            |
|  - Security, performance, tests          |
|                   |                      |
|          +-------+-------+               |
|          v               v               |
|       APPROVE         REJECT             |
|     (auto-merge)  (request changes)      |
|          |               |               |
|          |               v               |
|          |      Engineer fixes PR        |
|          |      (up to 3 attempts)       |
+------------------------------------------+
```

---

## Agent Details

### Engineer

The workhorse. Picks issues and implements them.

**Workflow:**
1. Fetches issues labeled `backlog` from GitHub/Linear
2. Sorts by priority (explicit priority labels or creation date)
3. Creates feature branch: `barbossa/{issue-id}-{slug}`
4. Invokes Claude CLI with issue context + CLAUDE.md
5. Claude implements the fix/feature
6. Creates PR linking to the issue

**Key behaviors:**
- One issue at a time per repository
- Won't pick up new issues if PR is pending review
- Responds to Tech Lead feedback by pushing fixes

### Tech Lead

Quality gatekeeper. Reviews PRs against strict criteria.

**8 Quality Dimensions:**
1. **Code Quality** - Clean, readable, follows patterns
2. **Feature Bloat** - No unnecessary additions
3. **Integration** - Works with existing features
4. **UI/UX** - Accessible, responsive, polished
5. **Tests** - Adequate coverage for changes
6. **Security** - No vulnerabilities introduced
7. **Performance** - No regressions
8. **Complexity** - Appropriate abstraction level

**Decisions:**
- `MERGE` - Meets all criteria, auto-merges
- `REQUEST_CHANGES` - Issues found, Engineer must fix
- `CLOSE` - After 3 failed attempts (3-strikes rule)

### Discovery

Finds technical debt and creates issues.

**What it looks for:**
- `TODO` and `FIXME` comments in code
- Missing test coverage
- Accessibility issues (WCAG violations)
- Console.log statements in production code
- Outdated dependencies

**Deduplication:**
- Checks existing issues before creating
- Uses semantic matching to avoid duplicates

### Product Manager

Proposes high-value features based on codebase analysis.

**Process:**
1. Reads CLAUDE.md to understand product context
2. Analyzes existing features and patterns
3. Identifies gaps and opportunities
4. Creates feature issues with acceptance criteria

**Output format:**
- Clear problem statement
- Proposed solution
- Acceptance criteria
- User value score (1-10)

### Auditor

Weekly health check of the entire system.

**What it monitors:**
- Agent success/failure rates
- PR outcomes (merged vs closed)
- Common failure patterns
- Code quality trends

**Output:**
- Health score (0-100)
- Actionable recommendations
- Creates GitHub issues for critical problems

---

## File Structure

```
barbossa-engineer/
├── src/barbossa/
│   ├── agents/
│   │   ├── engineer.py      # Main engineer agent
│   │   ├── tech_lead.py     # PR reviewer agent
│   │   ├── discovery.py     # Tech debt finder
│   │   ├── product.py       # Feature suggester
│   │   └── auditor.py       # Health monitor
│   ├── utils/
│   │   ├── prompts.py       # Prompt template loader
│   │   ├── issue_tracker.py # GitHub/Linear abstraction
│   │   ├── linear_client.py # Linear API wrapper
│   │   └── notifications.py # Discord webhook notifications
│   └── cli/
│       └── barbossa         # CLI entrypoint
├── prompts/                  # Prompt templates
├── config/
│   └── repositories.json    # Your configuration
├── scripts/
│   ├── validate.py          # Startup validation
│   ├── generate_crontab.py  # Schedule generator
│   └── run.sh               # Agent runner
└── logs/                    # Agent logs
```

---

## Security Model

### Container Isolation

- Runs as non-root user (`barbossa`, UID 1000)
- Limited to configured repositories only
- No shell access to host system

### Authentication

- GitHub token: `GITHUB_TOKEN` (repo, workflow scopes)
- Claude token: `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`
- Linear token: `LINEAR_API_KEY` (optional)

### What Agents Can Do

| Action | Allowed | Notes |
|--------|---------|-------|
| Read repository code | Yes | Via git clone |
| Create branches | Yes | Prefixed with `barbossa/` |
| Create PRs | Yes | One at a time per repo |
| Merge PRs | Yes | Only own PRs, if auto_merge enabled |
| Create issues | Yes | Discovery + Product agents |
| Delete branches | No | Only cleans up after merge |
| Force push | No | Never |
| Access other repos | No | Only configured repos |

### Protected Files

Configure `do_not_touch` in repositories.json:

```json
{
  "do_not_touch": [
    ".env*",
    "src/auth/**",
    "prisma/migrations/"
  ]
}
```

Agents will never modify these paths.

---

## Scheduling Philosophy

Agents are offset to avoid contention:

| Time | Agent | Why |
|------|-------|-----|
| :00 | Engineer | Creates PRs |
| :30 | - | Buffer |
| +1h | Tech Lead | Reviews PRs created in previous hour |
| Spread | Discovery | Keeps backlog stocked |
| 3x/day | Product | Quality over quantity |
| Daily | Auditor | Health check |

This ensures:
- No simultaneous Claude API calls
- Fresh PRs get reviewed quickly
- Backlog never runs empty
- CPU/memory not overloaded

---

## Extending Barbossa

### Custom Prompts

Override default prompts by creating files in `prompts/`:

- `engineer.txt` - Engineer's system prompt
- `tech_lead.txt` - Review criteria
- `discovery.txt` - What to look for
- `product_manager.txt` - Feature ideation

### Adding Repositories

Edit `config/repositories.json`:

```json
{
  "repositories": [
    { "name": "app-1", "url": "https://github.com/you/app-1.git" },
    { "name": "app-2", "url": "https://github.com/you/app-2.git" }
  ]
}
```

Restart the container to apply changes.

### Linear Integration

Replace GitHub Issues with Linear:

```json
{
  "issue_tracker": {
    "type": "linear",
    "linear": {
      "team_key": "ENG",
      "backlog_state": "Backlog"
    }
  }
}
```

Set `LINEAR_API_KEY` environment variable.
