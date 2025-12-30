# Troubleshooting

### Authentication failures

**Check tokens in .env file:**
```bash
cat .env  # Verify GITHUB_TOKEN and ANTHROPIC_API_KEY are set
```

**Generate new GitHub token:**
```bash
gh auth token  # OR create at https://github.com/settings/tokens
# Add to .env: GITHUB_TOKEN=ghp_your_token_here
```

**Generate new Claude token:**
```bash
# Option 1: Claude Pro/Max subscription token (recommended)
claude setup-token  # Follow prompts to generate long-lived token
# Add to .env: ANTHROPIC_API_KEY=<your_token>

# Option 2: Pay-as-you-go API key
# Get from: https://console.anthropic.com/settings/keys
# Add to .env: ANTHROPIC_API_KEY=sk-ant-api03-your_key_here
```

**Apply changes:**
```bash
vim .env  # Edit tokens
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
