# Frequently Asked Questions

---

## General

### What is Barbossa?

Barbossa is an autonomous AI development team that continuously improves your codebase. It runs five specialized agents on a schedule:

- **Product Manager** - Discovers valuable features
- **Discovery** - Finds technical debt and improvements
- **Engineer** - Implements changes and creates PRs
- **Tech Lead** - Reviews PRs with strict quality gates
- **Auditor** - Monitors system health

You sleep, Barbossa works, you wake up to PRs.

### Is Barbossa free?

Yes. Barbossa is free and open source under the MIT license.

However, you need a **Claude Max subscription** from Anthropic to provide the AI. Barbossa uses Claude CLI with your subscription.

### What's the catch?

No catch. You bring your own Claude subscription, run Barbossa yourself, and keep full control. The code is open source - inspect it, modify it, self-host it.

If you find it valuable, consider [sponsoring the project](https://github.com/sponsors/ADWilkinson).

---

## Requirements

### What do I need to run Barbossa?

1. **Docker** - To run the container
2. **Claude Max subscription** - from Anthropic
3. **GitHub account** - With a Personal Access Token
4. **SSH keys** - For private repository access

### Why Claude Max specifically?

Barbossa uses Claude CLI, which requires a Claude Max subscription for the extended context and usage limits needed for code generation. The Pro plan doesn't support CLI usage.

### Can I use a different AI model?

Currently, Barbossa is built around Claude CLI. Supporting other models (GPT-4, Gemini, local models) would require significant changes to the prompting and integration.

### Does it work with GitLab/Bitbucket?

Not yet. Barbossa currently supports GitHub only. GitLab and Bitbucket support are on the roadmap.

---

## Setup

### How long does setup take?

About 5 minutes if you already have Docker, Claude CLI, and GitHub CLI set up. See the [Quick Start Guide](quickstart.md).

### Can I run it on my laptop?

Yes, but it's designed to run continuously on a server. Your laptop sleeping would interrupt the schedule.

For best results, run on:
- A cloud VM (DigitalOcean, AWS, etc.)
- A home server or Raspberry Pi
- Any always-on machine

### What ports does it need?

None. Barbossa doesn't expose any ports. It only makes outbound connections to GitHub and Anthropic.

### Can I run multiple instances for different projects?

Yes. Each instance needs its own `config/repositories.json`. You can run multiple Docker containers with different configs.

---

## Operation

### How often does it create PRs?

The Engineer agent runs every 2 hours. If there's work in the backlog (GitHub Issues labeled `backlog`), it will create a PR.

Realistically, expect 2-6 PRs per day depending on your backlog size and complexity.

### Will it break my code?

Barbossa creates PRs, not direct commits. You always review before merging. The Tech Lead agent also reviews with strict criteria:

- CI must pass
- Tests required for significant changes
- Limited file changes per PR

### Can I trust it with my private repos?

Your code stays on your machine and GitHub. Barbossa:
- Runs locally in Docker
- Uses your GitHub token (never leaves your machine)
- Sends code to Claude for analysis (same as using Claude directly)

Review Anthropic's [privacy policy](https://www.anthropic.com/privacy) for how Claude handles data.

### What if it creates a bad PR?

Close it. The Tech Lead agent often catches issues, but you're the final reviewer. Bad PRs happen - just close them and Barbossa moves on.

### Can I pause it?

```bash
docker compose stop    # Pause
docker compose start   # Resume
```

Or disable specific agents in config:
```json
{
  "settings": {
    "discovery": { "enabled": false },
    "product_manager": { "enabled": false }
  }
}
```

---

## Quality

### How good are the PRs?

Quality depends on:
1. **Your codebase context** - Good README/CLAUDE.md helps
2. **Issue clarity** - Clear acceptance criteria = better PRs
3. **Tech stack** - Works best with common frameworks

Expect some PRs to need tweaks. Think of it as a junior developer that never sleeps - helpful, but needs guidance.

### Does it write tests?

Yes, when required. The Tech Lead rejects PRs with >50 lines of changes and no tests. The Engineer learns to include tests.

### Can I improve the quality?

1. Add a comprehensive `CLAUDE.md` to your repo
2. Write clear issue descriptions with acceptance criteria
3. Use `focus_areas` in config to guide priorities
4. Add `design_system` rules for consistent styling

---

## Costs

### What will this cost me?

| Item | Cost |
|------|------|
| Barbossa | Free |
| Claude Max | See [Anthropic pricing](https://claude.ai) |
| Server (optional) | $5-20/month |

### Is Claude Max usage unlimited?

Claude Max has generous limits but not unlimited. Barbossa is designed to work within these limits with its scheduled approach (every 2 hours, not continuous).

### Will it use all my Claude credits?

Barbossa makes several Claude calls per cycle (every 2 hours). With 12 cycles per day across 5 agents, usage is moderate. Most users stay well within Max limits.

---

## Security

### Is my code safe?

- Code stays on your machine and GitHub
- Claude sees code for analysis (standard Claude usage)
- Firebase used for prompts and anonymous user counting (see README for transparency details)
- Open source - audit the code yourself

### What permissions does the GitHub token need?

The `repo` scope - this allows creating branches, commits, PRs, and reading issues.

### Can I restrict what files it touches?

Yes, use `do_not_touch` in config:
```json
{
  "do_not_touch": [
    "src/lib/auth.ts",
    "prisma/migrations/",
    ".env*"
  ]
}
```

---

## Troubleshooting

### It's not creating any PRs

1. Check if issues exist with `backlog` label
2. View logs: `docker compose logs -f`
3. Run manually: `docker exec barbossa python3 barbossa_engineer.py`

See [Troubleshooting Guide](troubleshooting.md) for more.

### The Tech Lead rejects everything

Check the criteria:
- CI must pass
- Tests required for >50 lines
- Max 15 files changed

If your PRs are being wrongly rejected, check the logs and consider adjusting thresholds.

### Claude CLI authentication fails

```bash
claude login
docker compose restart
```

---

## Contributing

### How can I contribute?

See [CONTRIBUTING.md](../CONTRIBUTING.md). We welcome:
- Bug fixes
- Documentation improvements
- New integrations
- Performance optimizations

### Can I add support for [X]?

Probably! Open an issue to discuss first. Popular requests:
- GitLab support
- Slack notifications
- Linear integration
- Custom agent schedules

---

## More Questions?

- [GitHub Issues](https://github.com/ADWilkinson/barbossa-engineer/issues) - Bug reports
- [GitHub Discussions](https://github.com/ADWilkinson/barbossa-engineer/discussions) - Questions and ideas
