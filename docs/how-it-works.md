# How It Works

Barbossa runs AI agents in Docker. Each agent has a role and runs on a schedule.

## Pipeline

```
  ┌───────────┐   ┌─────────┐
  │ Discovery │   │ Product │
  │ finds debt│   │suggests │
  └─────┬─────┘   └────┬────┘
        │              │
        └──────┬───────┘
               ▼
         ┌──────────┐
         │ Backlog  │  GitHub Issues
         └────┬─────┘
              ▼
         ┌──────────┐
         │ Engineer │  implements
         └────┬─────┘
              ▼
         ┌──────────┐
         │   PR     │  Pull Request
         └────┬─────┘
              ▼
         ┌──────────┐
         │Tech Lead │  reviews
         └────┬─────┘
              ▼
        Merge or Reject
```

## Agents

### Engineer

Implements issues labeled `backlog`.

- Branch: `barbossa/{issue-id}-{slug}`
- Uses issue context + `CLAUDE.md`
- One issue at a time per repo

### Tech Lead

Reviews PRs.

- Waits for CI to pass
- 8 dimensions: quality, tests, security, performance, complexity, UI/UX, integration, bloat
- 3-strikes: closes after 3 failed reviews
- Merges approved PRs

### Discovery

Finds technical debt.

- TODO/FIXME comments
- Missing tests
- Console.logs
- Creates issues with evidence

### Product Manager

Suggests features.

- Reads `CLAUDE.md`
- Creates issues with acceptance criteria

### Auditor

Weekly health check.

- Success rates
- PR outcomes
- Creates issues for problems

### Spec Generator

Cross-repo specs (Spec Mode only).

- Groups repos into products
- Creates parent spec + child tickets

## Security

Container runs as non-root (`barbossa`, UID 1000).

| Action | Allowed |
|--------|---------|
| Read code | Yes |
| Create branches | Yes (`barbossa/` prefix) |
| Create/merge PRs | Yes (own only) |
| Create issues | Yes |
| Force push | No |
| Other repos | No |

Protected files:

```json
{ "do_not_touch": [".env*", "src/auth/**"] }
```

## Schedule

Agents offset to avoid contention:

| Agent | When | Purpose |
|-------|------|---------|
| Engineer | :00 | Creates PRs |
| Tech Lead | +1h | Reviews PRs |
| Discovery | 6x/day | Stocks backlog |
| Product | 3x/day | Suggests features |
| Auditor | Daily | Health check |

## Manual run

```bash
docker exec barbossa barbossa run engineer
docker exec barbossa barbossa run tech-lead
docker exec barbossa barbossa run discovery
docker exec barbossa barbossa run product
docker exec barbossa barbossa run auditor
docker exec barbossa barbossa run spec
```
