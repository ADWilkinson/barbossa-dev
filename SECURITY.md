# Security Policy

## Overview

Barbossa runs AI agents that have access to your codebase and can create commits and pull requests. This document outlines security considerations and best practices.

## Security Model

### What Barbossa Can Access

- **GitHub repositories** you configure (read/write via SSH)
- **Claude API** through your subscription
- **Local filesystem** within the Docker container

### What Barbossa Does NOT Have

- Access to repositories not in your config
- Your GitHub password or OAuth tokens (uses SSH keys)
- Access to other services on your machine (isolated in Docker)

## Configuration Best Practices

### 1. Protect Sensitive Files

Always configure `do_not_touch` for sensitive files:

```json
{
  "repositories": [{
    "do_not_touch": [
      ".env*",
      "*.pem",
      "*.key",
      "src/lib/auth.ts",
      "src/lib/stripe.ts",
      "prisma/migrations/",
      "secrets/",
      "config/credentials*"
    ]
  }]
}
```

### 2. Use Separate SSH Keys

Consider using a deploy key with limited permissions instead of your personal SSH key:

```bash
# Generate a deploy key for Barbossa
ssh-keygen -t ed25519 -f ~/.ssh/barbossa_deploy -N ""

# Add as deploy key to your repo (with write access)
# GitHub > Repository > Settings > Deploy keys
```

### 3. Disable Auto-Merge Initially

Start with manual review of all PRs:

```json
{
  "settings": {
    "tech_lead": {
      "auto_merge": false
    }
  }
}
```

### 4. Review PRs Before Merging

Even with `auto_merge: true`, periodically review merged PRs to ensure quality.

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** create a public GitHub issue
2. Open a private GitHub Security Advisory:
   https://github.com/ADWilkinson/barbossa-dev/security/advisories/new
3. Alternatively, email security concerns to the maintainers at
   gm@andrewwilkinson.io
4. Include steps to reproduce if possible

We aim to respond within 48 hours and patch critical issues quickly.

## Docker Security

Barbossa runs in an isolated Docker container with:

- No privileged access
- Limited network access
- Volume mounts only for config and logs

### Container Verification

Verify the container image signature:

```bash
docker pull ghcr.io/adwilkinson/barbossa-dev:latest
docker inspect ghcr.io/adwilkinson/barbossa-dev:latest
```

## Authentication

### GitHub CLI (`gh`)

Barbossa uses the GitHub CLI for repository operations. Your credentials are stored securely by `gh`:

```bash
# View current auth status
gh auth status

# Refresh if needed
gh auth refresh
```

### Claude CLI

Claude credentials are managed by the Claude CLI and stored in your user profile, not in the container.

## Updates

Keep Barbossa updated to receive security patches:

```bash
docker pull ghcr.io/adwilkinson/barbossa-dev:latest
docker compose down && docker compose up -d
```

## Audit Logs

All agent sessions are logged in `logs/`. Review periodically:

```bash
ls -la logs/
cat logs/$(ls -t logs/ | head -1)
```

## Scope of Changes

Barbossa agents are designed to make small, focused changes. The Tech Lead agent rejects:

- PRs touching more than 15 files
- PRs to protected files
- PRs without tests (for significant changes)

This limits the blast radius of any single change.
