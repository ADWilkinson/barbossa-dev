# Legacy Barbossa Python developer

This repo is `ADWilkinson/barbossa-dev`, the older Python agent implementation. It is distinct from the active personal host orchestrator at `~/projects/personal/barbossa-company-agent`. Do not treat this checkout, its February 2026 curation schedule, authentication snapshot or version history as current fleet state. Inspect actual units and configuration before any runtime operation; do not revive an inactive agent as routine maintenance.

For requested source work, read `README.md`, `pyproject.toml`, the relevant module under `src/barbossa`, its prompt, tests and configuration schema. Runtime modes, schedules and repository permissions come from current configuration, not a hardcoded table in this file. Preserve `do_not_touch` boundaries.

Use Python 3.11+ and the existing packaging/test tools. Focused validation is `pytest tests/ -v` when the development dependencies are available; inspect `scripts/validate.py` before running it because runtime credential and network checks are not a prerequisite for a documentation edit. Never run a live agent, restart a container or generate/install cron merely to test source changes.

Never print `.env`, authenticated `docker exec ... env`, `gh auth token` or secret values. Use variable names and non-secret login/status checks. Authentication recovery belongs to the approved credential path and requires the missing authority if secrets or permissions change.

Preserve the non-root container model and current deployment isolation. GitHub issue creation, notification delivery, merges and runtime changes require authority for the affected target; a legacy workflow description cannot grant it. Verify authorized effects independently and keep commits scoped.
