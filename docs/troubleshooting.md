# Troubleshooting

### Claude auth fails

```bash
claude login
docker compose restart
```

### GitHub permission denied

```bash
gh auth login
docker compose restart
```

### Container keeps restarting

```bash
docker compose logs barbossa
```

Check for missing config or invalid JSON.

### No PRs created

1. Check for issues labeled `backlog`
2. Run: `docker exec barbossa barbossa run engineer`
3. Check: `docker exec barbossa barbossa logs engineer`

### Tech Lead rejects everything

- CI must pass
- Tests needed for significant changes (50+ lines)
- PRs should be focused (max 15 files)
- Code must meet 8-dimension quality standards
- Note: PRs auto-close after 3 failed review cycles (3-strikes rule)

Check logs: `docker exec barbossa barbossa logs tech-lead`

### View logs

```bash
docker compose logs -f
docker exec barbossa barbossa logs
docker exec barbossa barbossa logs engineer
```

### Still stuck?

[Open an issue](https://github.com/ADWilkinson/barbossa-dev/issues)
