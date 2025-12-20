# Troubleshooting

Common issues and how to fix them.

---

## Claude CLI Issues

### "Claude CLI not authenticated"

**Symptom:** Logs show authentication errors.

**Fix:**
```bash
# Re-authenticate
claude login

# Verify authentication works
claude --version

# Restart Barbossa
docker compose restart
```

### "Rate limit exceeded"

**Symptom:** Claude CLI returns rate limit errors.

**Cause:** Claude Max has usage limits during peak hours.

**Fix:**
- Wait 15-30 minutes and retry
- Barbossa will automatically retry on next cycle
- Consider adjusting schedule to off-peak hours

### "Token refresh failed"

**Symptom:** Authentication stops working after some time.

**Fix:**
```bash
# Re-authenticate
claude login

# Ensure ~/.claude is mounted writable (not :ro)
# Check docker-compose.yml:
#   - ~/.claude:/root/.claude  (correct)
#   - ~/.claude:/root/.claude:ro  (wrong - read only)

docker compose restart
```

---

## GitHub Issues

### "Permission denied" on push

**Symptom:** Git push fails with 403 or permission denied.

**Possible causes:**

1. **Token lacks permissions:**
   ```bash
   # Token needs 'repo' scope
   # Generate new token at: github.com/settings/tokens
   ```

2. **Token expired:**
   ```bash
   # Update .env with new token
   echo "GITHUB_TOKEN=ghp_newtoken..." > .env
   docker compose restart
   ```

3. **SSH key issues:**
   ```bash
   # Test SSH access
   ssh -T git@github.com

   # Ensure keys are mounted
   # Check docker-compose.yml has:
   #   - ~/.ssh:/root/.ssh:ro
   ```

### "Repository not found"

**Symptom:** Git clone fails inside container.

**Fix:**
```bash
# Verify repo URL in config/repositories.json
# For private repos, use SSH URL:
#   "url": "git@github.com:username/repo.git"

# For public repos, HTTPS works:
#   "url": "https://github.com/username/repo.git"

# Test access from container
docker exec barbossa git ls-remote git@github.com:username/repo.git
```

### PRs not being created

**Symptom:** Engineer runs but no PRs appear.

**Check:**
```bash
# View engineer logs
docker exec barbossa cat /app/logs/barbossa_engineer.log

# Common causes:
# 1. No issues labeled 'backlog' exist
# 2. All backlog issues already have PRs
# 3. Implementation failed (check logs for errors)
```

---

## Docker Issues

### Container keeps restarting

**Symptom:** Container restarts in a loop.

**Debug:**
```bash
# Check logs
docker compose logs barbossa

# Common causes:
# 1. Missing config file
# 2. Invalid JSON in repositories.json
# 3. Missing environment variables
```

### "File not found" errors

**Symptom:** Scripts can't find config files.

**Fix:**
```bash
# Ensure config exists
ls -la config/repositories.json

# If missing, create from example
cp config/repositories.json.example config/repositories.json
# Edit with your repos
```

### Volume mount issues

**Symptom:** Changes to config don't take effect, or logs are empty.

**Fix:**
```bash
# Rebuild container
docker compose down
docker compose build --no-cache
docker compose up -d

# Verify mounts
docker exec barbossa ls -la /app/config/
docker exec barbossa ls -la /root/.claude/
```

---

## Agent-Specific Issues

### Engineer produces low-quality PRs

**Possible causes:**
1. Missing context in CLAUDE.md or README.md
2. Vague issue descriptions
3. Missing `focus_areas` in config

**Fix:**
- Add a comprehensive CLAUDE.md to your repo
- Improve issue descriptions with acceptance criteria
- Add specific guidance in `focus_areas`

### Tech Lead rejects everything

**Check the review criteria:**
- CI must be passing
- Tests required for >50 lines of changes
- Max 15 files per PR

**If PRs are legitimately good but rejected:**
```bash
# Check tech lead logs
docker exec barbossa cat /app/logs/barbossa_tech_lead.log

# Adjust thresholds in config if needed
```

### Discovery creates too many issues

**Fix:**
```json
{
  "settings": {
    "discovery": {
      "max_backlog_issues": 10
    }
  }
}
```

### Product Manager suggests irrelevant features

**Fix:**
- Improve your README.md or CLAUDE.md with product context
- Add clear `focus_areas` in repository config
- Disable if not needed:
  ```json
  {
    "settings": {
      "product_manager": {
        "enabled": false
      }
    }
  }
  ```

---

## Cron / Scheduling Issues

### Agents not running on schedule

**Check cron is running:**
```bash
docker exec barbossa ps aux | grep cron
docker exec barbossa crontab -l
```

**Check timezone:**
```bash
# Set timezone in .env
TZ=America/New_York

# Or in docker-compose.yml
environment:
  - TZ=America/New_York
```

### Want to change schedule

**Edit crontab:**
```bash
# View current schedule
docker exec barbossa crontab -l

# Edit (requires rebuilding image or exec into container)
# Or modify crontab file and rebuild:
docker compose build
docker compose up -d
```

---

## Logs and Debugging

### View all logs

```bash
# Stream all logs
docker compose logs -f

# View specific agent log
docker exec barbossa cat /app/logs/barbossa_engineer.log
docker exec barbossa cat /app/logs/barbossa_tech_lead.log

# Tail logs
docker exec barbossa tail -f /app/logs/barbossa_engineer.log
```

### Run agent manually with verbose output

```bash
# Engineer
docker exec barbossa python3 barbossa_engineer.py

# Tech Lead
docker exec barbossa python3 barbossa_tech_lead.py

# Discovery
docker exec barbossa python3 barbossa_discovery.py
```

### Check container status

```bash
docker compose ps
docker inspect barbossa
```

---

## Getting Help

If you're still stuck:

1. **Check existing issues:** [GitHub Issues](https://github.com/ADWilkinson/barbossa/issues)
2. **Ask the community:** [GitHub Discussions](https://github.com/ADWilkinson/barbossa/discussions)
3. **Include in your report:**
   - Docker logs (`docker compose logs`)
   - Your config (redact tokens)
   - Steps to reproduce
