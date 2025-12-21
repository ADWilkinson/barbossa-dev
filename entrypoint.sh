#!/bin/bash
set -e

echo ""
echo "========================================"
echo "  Barbossa - Autonomous AI Dev Team"
echo "========================================"
echo ""

# Git config is mounted from host - copy to barbossa user
if [ -f /root/.gitconfig ]; then
    cp /root/.gitconfig /home/barbossa/.gitconfig 2>/dev/null || true
    chown barbossa:barbossa /home/barbossa/.gitconfig 2>/dev/null || true
fi

# Copy SSH keys to barbossa user
if [ -d /root/.ssh ]; then
    cp -r /root/.ssh/* /home/barbossa/.ssh/ 2>/dev/null || true
    chown -R barbossa:barbossa /home/barbossa/.ssh 2>/dev/null || true
    chmod 700 /home/barbossa/.ssh 2>/dev/null || true
    chmod 600 /home/barbossa/.ssh/* 2>/dev/null || true
fi

# Symlink GitHub CLI auth to barbossa user (so host changes are reflected live)
if [ -d /root/.config/gh ]; then
    rm -rf /home/barbossa/.config/gh 2>/dev/null || true
    ln -sf /root/.config/gh /home/barbossa/.config/gh
fi

# Symlink Claude config to barbossa user (so host changes are reflected live)
if [ -d /root/.claude ]; then
    rm -rf /home/barbossa/.claude 2>/dev/null || true
    ln -sf /root/.claude /home/barbossa/.claude
fi

# Ensure app directory is writable by barbossa
chown -R barbossa:barbossa /app 2>/dev/null || true

# Authenticate GitHub CLI if token provided
if [ -n "$GITHUB_TOKEN" ]; then
    su - barbossa -c "echo '$GITHUB_TOKEN' | gh auth login --with-token 2>/dev/null" || true
fi

# Configure git to use gh CLI for HTTPS authentication
# This allows cloning private repos without SSH keys
su - barbossa -c "gh auth setup-git 2>/dev/null" || true

# ========================================
# VALIDATE CONFIGURATION
# ========================================
echo "Running validation..."
echo ""

if ! python3 /app/validate.py; then
    echo ""
    echo "========================================"
    echo "  STARTUP BLOCKED - Fix errors above"
    echo "========================================"
    echo ""
    echo "Container will keep running so you can"
    echo "exec in and fix the issues:"
    echo ""
    echo "  docker exec -it barbossa bash"
    echo ""
    # Keep container alive but don't start agents
    exec tail -f /dev/null
fi

echo ""

# ========================================
# GENERATE CRONTAB FROM CONFIG
# ========================================

echo "Generating schedule from config..."
python3 /app/generate_crontab.py > /tmp/barbossa-crontab
crontab /tmp/barbossa-crontab
rm /tmp/barbossa-crontab

# Export environment for cron jobs
printenv | grep -E '^(ANTHROPIC|GITHUB|PATH|HOME|TZ)' >> /etc/environment 2>/dev/null || true

# Start cron daemon
echo "Starting scheduler..."
cron

echo ""
echo "Active schedule:"
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" | grep -v "^SHELL" | grep -v "^PATH" | head -6
echo ""

echo "========================================"
echo "  Barbossa is running!"
echo "========================================"
echo ""
echo "Commands:"
echo "  barbossa health     - Check system status"
echo "  barbossa run agent  - Run agent manually"
echo "  barbossa status     - View recent activity"
echo "  barbossa logs       - View logs"
echo ""
echo "Or use docker:"
echo "  docker logs -f barbossa"
echo ""

# Keep container running - tail logs if they exist
exec tail -f /app/logs/*.log 2>/dev/null || exec tail -f /dev/null
