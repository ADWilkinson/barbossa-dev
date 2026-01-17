# FAQ

**What is Barbossa?**
AI agents that work on your code while you sleep. They find issues, implement fixes, create PRs, and review each other's work.

**Is it free?**
Yes. You need a Claude Pro/Max subscription or Anthropic API account.

**Will it break my code?**
PRs are merged automatically by default. Set `auto_merge: false` to review manually.

**Can I trust it with private repos?**
Code stays on your machine and GitHub. Claude sees code for analysis (same as using Claude directly).

**What if it creates a bad PR?**
Close it. Barbossa moves on.

**How do I improve quality?**
Add a `CLAUDE.md` file to your repo root with project context (stack, conventions, what to avoid). Agents read this before working.

**What goes in CLAUDE.md?**
Tech stack, coding conventions, architecture notes, things to avoid. Example: "Next.js 14 with App Router. Use server components. Don't touch auth."

**Can I pause it?**
```bash
docker compose stop   # Pause
docker compose start  # Resume
```

**No PRs being created?**
1. Check for issues with `backlog` label
2. Run: `docker exec barbossa barbossa run engineer`
3. Check: `docker exec barbossa barbossa logs engineer`

**Still stuck?**
[Open an issue](https://github.com/ADWilkinson/barbossa-dev/issues)
