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

# Copy GitHub CLI auth to barbossa user
if [ -d /root/.config/gh ]; then
    cp -r /root/.config/gh/* /home/barbossa/.config/gh/ 2>/dev/null || true
    chown -R barbossa:barbossa /home/barbossa/.config/gh 2>/dev/null || true
fi

# Copy Claude config to barbossa user
if [ -d /root/.claude ]; then
    shopt -s dotglob
    cp -r /root/.claude/* /home/barbossa/.claude/ 2>/dev/null || true
    shopt -u dotglob
    chown -R barbossa:barbossa /home/barbossa/.claude 2>/dev/null || true
fi

# Ensure app directory is writable by barbossa
chown -R barbossa:barbossa /app 2>/dev/null || true

# Authenticate GitHub CLI if token provided
if [ -n "$GITHUB_TOKEN" ]; then
    su - barbossa -c "echo '$GITHUB_TOKEN' | gh auth login --with-token 2>/dev/null" || true
fi

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
# START CRON
# ========================================

# Export environment for cron jobs
printenv | grep -E '^(ANTHROPIC|GITHUB|PATH|HOME|TZ)' >> /etc/environment 2>/dev/null || true

# Start cron daemon
echo "Starting scheduler..."
cron

echo ""
echo "Active schedule:"
crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" | head -5
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
