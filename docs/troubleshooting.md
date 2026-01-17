# Troubleshooting

## First step

Run diagnostics:

```bash
docker exec barbossa barbossa doctor
```

This checks config, auth, and recent activity.

## Auth failures

```bash
# Check tokens
cat .env

# New GitHub token
gh auth token
# Add to .env: GITHUB_TOKEN=ghp_...

# New Claude token
claude setup-token
# Add to .env: CLAUDE_CODE_OAUTH_TOKEN=...

# Restart
docker compose restart
```

## Container keeps restarting

```bash
docker compose logs barbossa
```

Usually missing config or invalid JSON.

## No PRs created

1. Check for issues labeled `backlog`
2. Run: `docker exec barbossa barbossa run engineer`
3. Logs: `docker exec barbossa barbossa logs engineer`

## Tech Lead rejects everything

- CI must pass
- Tests required for 50+ line changes
- Max 30 files per PR
- PRs close after 3 failed reviews

Logs: `docker exec barbossa barbossa logs tech-lead`

## View logs

```bash
barbossa watch                # All agent logs
barbossa logs engineer        # Specific agent
docker compose logs -f        # Container logs
```

## Notifications not working

1. Check `notifications.enabled: true` in config
2. Verify webhook URL is correct
3. Check Discord channel permissions

## Still stuck?

[Open an issue](https://github.com/ADWilkinson/barbossa-dev/issues)
