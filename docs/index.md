# Barbossa

AI engineers that ship code while you sleep.

```bash
docker pull ghcr.io/adwilkinson/barbossa-dev:latest
```

---

## What it does

Barbossa is self-hosted and runs AI agents on a schedule. They find issues, implement fixes, create PRs, and review each other's work. You wake up to merged PRs.

**Autonomous Mode** — Agents implement, review, and merge code automatically.

**Spec Mode** — Generate cross-repo feature specifications without touching code.

---

## The pipeline

```
  ┌───────────┐   ┌─────────┐
  │ Discovery │   │ Product │
  └─────┬─────┘   └────┬────┘
        │              │
        └──────┬───────┘
               ▼
         ┌──────────┐
         │ Backlog  │  GitHub Issues
         └────┬─────┘
              ▼
         ┌──────────┐
         │ Engineer │  implements, creates PR
         └────┬─────┘
              ▼
         ┌──────────┐
         │Tech Lead │  reviews, merges
         └──────────┘
```

---

## Agents

| Agent | Role |
|-------|------|
| Engineer | Implements features from backlog |
| Tech Lead | Reviews PRs, merges or requests changes |
| Discovery | Finds TODOs, missing tests, tech debt |
| Product | Suggests high-value features |
| Auditor | Weekly health check |

---

## Get started

```bash
curl -fsSL https://raw.githubusercontent.com/ADWilkinson/barbossa-dev/main/install.sh | bash
cd barbossa && docker compose up -d
```

[Quickstart](quickstart.md){ .md-button .md-button--primary }
[GitHub](https://github.com/ADWilkinson/barbossa-dev){ .md-button }
