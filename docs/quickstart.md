# Quick Start Guide

Get Barbossa running in 5 minutes.

## Prerequisites

Before you begin, make sure you have:

1. **Docker** installed and running
2. **Claude Max subscription** ($100/month from Anthropic)
3. **GitHub account** with a Personal Access Token
4. **SSH keys** added to GitHub (for private repos)

## Step 1: Clone the Repository

```bash
git clone https://github.com/ADWilkinson/barbossa.git
cd barbossa
```

## Step 2: Authenticate Claude CLI

Barbossa uses Claude CLI with your Max subscription:

```bash
# Install Claude CLI (if not already installed)
npm install -g @anthropic-ai/claude-code

# Login to Claude
claude login
```

Follow the prompts to authenticate with your Anthropic account.

## Step 3: Create GitHub Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "Barbossa"
4. Select scopes:
   - `repo` (full control of private repositories)
   - `workflow` (update GitHub Action workflows)
5. Generate and copy the token

## Step 4: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your GitHub token
# GITHUB_TOKEN=ghp_your_token_here
```

## Step 5: Configure Repositories

```bash
# Copy the example config
cp config/repositories.json.example config/repositories.json
```

Edit `config/repositories.json`:

```json
{
  "owner": "your-github-username",
  "repositories": [
    {
      "name": "your-repo-name",
      "url": "git@github.com:your-username/your-repo.git",
      "package_manager": "npm",
      "description": "Brief description of your project",
      "tech_stack": {
        "framework": "Next.js 14",
        "language": "TypeScript"
      },
      "do_not_touch": [
        "src/lib/auth.ts"
      ]
    }
  ]
}
```

## Step 6: Start Barbossa

```bash
# Build and start the container
docker compose up -d

# Watch the logs
docker compose logs -f
```

## Step 7: Verify It's Working

```bash
# Check the container is running
docker ps | grep barbossa

# Check cron jobs are scheduled
docker exec barbossa crontab -l

# View logs
docker compose logs -f
```

## What Happens Next

1. **Within 2 hours**: The Engineer agent will run, analyze your codebase, and create a PR
2. **35 minutes later**: The Tech Lead agent reviews the PR
3. **Daily**: Product Manager and Discovery agents find new work

## First PR

Your first PR should appear within 2 hours. It will:
- Be linked to a GitHub Issue (if one exists in backlog)
- Include a clear description of changes
- Follow your project's patterns

## Troubleshooting

### Container won't start

```bash
# Check for errors
docker compose logs

# Rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Claude authentication issues

```bash
# Re-authenticate Claude
docker exec -it barbossa claude login
```

### No PRs appearing

1. Check the logs: `docker compose logs -f`
2. Verify GitHub token has correct permissions
3. Ensure SSH keys are mounted correctly

See [Troubleshooting](troubleshooting.md) for more help.

## Next Steps

- [Configuration Reference](configuration.md) - Customize agent behavior
- [Agent Documentation](agents.md) - Understand each agent
- [FAQ](faq.md) - Common questions
