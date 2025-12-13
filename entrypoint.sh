#!/bin/bash
set -e

echo "========================================"
echo "Barbossa v3.0 - Docker Container"
echo "========================================"
echo "Time: $(date)"
echo ""

# Git config is mounted from host - copy to barbossa user
if [ -f /root/.gitconfig ]; then
    echo "Git config: copying to barbossa user"
    cp /root/.gitconfig /home/barbossa/.gitconfig
    chown barbossa:barbossa /home/barbossa/.gitconfig
else
    echo "Warning: No git config found"
fi

# Copy SSH keys to barbossa user
if [ -d /root/.ssh ]; then
    echo "SSH keys: copying to barbossa user"
    cp -r /root/.ssh/* /home/barbossa/.ssh/ 2>/dev/null || true
    chown -R barbossa:barbossa /home/barbossa/.ssh
    chmod 700 /home/barbossa/.ssh
    chmod 600 /home/barbossa/.ssh/* 2>/dev/null || true
fi

# Copy GitHub CLI auth to barbossa user
if [ -d /root/.config/gh ]; then
    echo "GitHub CLI: copying auth to barbossa user"
    cp -r /root/.config/gh/* /home/barbossa/.config/gh/ 2>/dev/null || true
    chown -R barbossa:barbossa /home/barbossa/.config/gh
fi

# Copy Claude config to barbossa user (including hidden files like .credentials.json)
if [ -d /root/.claude ]; then
    echo "Claude config: copying to barbossa user (including credentials)"
    # Use shopt to include hidden files
    shopt -s dotglob
    cp -r /root/.claude/* /home/barbossa/.claude/ 2>/dev/null || true
    shopt -u dotglob
    chown -R barbossa:barbossa /home/barbossa/.claude
fi

# Authenticate GitHub CLI if token provided
if [ -n "$GITHUB_TOKEN" ]; then
    echo "Configuring GitHub CLI for barbossa user..."
    su - barbossa -c "echo '$GITHUB_TOKEN' | gh auth login --with-token 2>/dev/null" || true
fi

# Ensure app directory is writable by barbossa
chown -R barbossa:barbossa /app

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
