#!/bin/bash
set -e

echo ""
echo "========================================"
echo "  Barbossa - Autonomous AI Dev Team"
echo "========================================"
echo ""

# Authenticate GitHub CLI if token provided
if [ -n "$GITHUB_TOKEN" ]; then
    echo "$GITHUB_TOKEN" | gh auth login --with-token 2>/dev/null || true
fi

# Configure git to use gh CLI for HTTPS authentication
gh auth setup-git 2>/dev/null || true

# ========================================
# VALIDATE CONFIGURATION
# ========================================
echo "Running validation..."
echo ""

if ! python3 /app/scripts/validate.py; then
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
python3 /app/scripts/generate_crontab.py > /app/crontab
echo ""

echo "Active schedule:"
cat /app/crontab | grep -v "^#" | grep -v "^$" | grep -v "^SHELL" | grep -v "^PATH" | head -6
echo ""

# Start supercronic in background
echo "Starting scheduler..."
supercronic /app/crontab &

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
