#!/bin/bash
set -e

echo "========================================"
echo "Barbossa v3.0 - Docker Container"
echo "========================================"
echo "Time: $(date)"
echo ""

# Configure git
git config --global user.email "barbossa@eastindiaonchaincompany.xyz"
git config --global user.name "Barbossa"
git config --global init.defaultBranch main

# Authenticate GitHub CLI if token provided
if [ -n "$GITHUB_TOKEN" ]; then
    echo "Configuring GitHub CLI..."
    echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null || true
fi

# Export environment for cron
printenv | grep -E '^(ANTHROPIC|GITHUB|PATH|HOME)' >> /etc/environment

# Start cron daemon
echo "Starting cron daemon..."
cron

# Log cron status
echo "Cron jobs:"
crontab -l

echo ""
echo "Starting web portal on port 8080..."
echo "========================================"

# Start web portal (foreground)
cd /app
exec python3 web_portal/app_simple.py
