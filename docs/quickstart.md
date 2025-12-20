# Quick Start Guide

Get Barbossa running in 5 minutes.

---

## Prerequisites

Before you start, you need:

1. **Docker** - [Install Docker](https://docs.docker.com/get-docker/)
2. **Claude Max subscription** - $100/month from [Anthropic](https://claude.ai)
3. **GitHub account** with a Personal Access Token

---

## Step 1: Clone Barbossa

```bash
git clone https://github.com/ADWilkinson/barbossa.git
cd barbossa
```

---

## Step 2: Create Config

The minimal config is just 3 fields:

```bash
cat > config/repositories.json << 'EOF'
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "my-app",
      "url": "git@github.com:your-github-username/my-app.git"
    }
  ]
}
EOF
```

Replace:
- `your-github-username` with your GitHub username
- `my-app` with your repository name

---

## Step 3: Set Up GitHub Token

Create a Personal Access Token at [github.com/settings/tokens](https://github.com/settings/tokens) with `repo` scope.

```bash
echo "GITHUB_TOKEN=ghp_your_token_here" > .env
```

---

## Step 4: Authenticate Claude CLI

On your **host machine** (not in Docker):

```bash
# Install Claude CLI if you haven't
npm install -g @anthropic-ai/claude-code

# Log in with your Claude Max account
claude login
```

This creates credentials in `~/.claude/` that Docker will mount.

---

## Step 5: Start Barbossa

```bash
docker compose up -d
```

Barbossa will:
1. Validate your configuration
2. Check authentication
3. Start the scheduler

---

## Step 6: Verify It's Working

```bash
# Check health status
docker exec barbossa barbossa health
```

You should see:
```
✓ Config valid: 1 repositories
✓ GitHub CLI authenticated
✓ Claude CLI authenticated
```

---

## Step 7: Test It

Don't wait 2 hours - run the engineer manually:

```bash
docker exec barbossa barbossa run engineer
```

Watch it work:
```bash
docker compose logs -f
```

Your first PR should appear within a few minutes!

---

## What Happens Next

Barbossa runs automatically on this schedule:

| Agent | Schedule |
|-------|----------|
| Engineer | Every 2 hours at :00 |
| Tech Lead | Every 2 hours at :35 |
| Discovery | 4x daily |
| Product Manager | 3x daily |
| Auditor | Daily at 06:30 |

You'll see:
- PRs appearing in your repo
- Issues being created (backlog)
- PRs being reviewed and merged/closed

---

## Common Commands

```bash
# Check health
docker exec barbossa barbossa health

# Run an agent manually
docker exec barbossa barbossa run engineer
docker exec barbossa barbossa run tech-lead

# View status
docker exec barbossa barbossa status

# View logs
docker exec barbossa barbossa logs
docker exec barbossa barbossa logs engineer -f

# Docker commands
docker compose logs -f      # Stream all logs
docker compose restart      # Restart after config changes
docker compose down         # Stop Barbossa
```

---

## Troubleshooting

### Validation Failed

If you see validation errors on startup:

```bash
# See what's wrong
docker exec barbossa barbossa health

# Fix issues and restart
docker compose restart
```

### Claude Auth Issues

```bash
# Re-authenticate on your host machine
claude login

# Restart container
docker compose restart
```

### No PRs Created

1. Check if there's work in the backlog:
   ```bash
   docker exec barbossa gh issue list --label backlog
   ```

2. Run engineer manually and watch:
   ```bash
   docker exec barbossa barbossa run engineer
   ```

3. Check logs for errors:
   ```bash
   docker exec barbossa barbossa logs engineer
   ```

---

## Next Steps

- [Configuration Reference](configuration.md) - Add more options
- [Agent Documentation](agents.md) - Understand each agent
- [Troubleshooting](troubleshooting.md) - Fix common issues
- [FAQ](faq.md) - Common questions
