#!/bin/bash
# Quick update script for fast portal changes
# Usage: ./quick-update.sh "commit message"

set -e

PORTAL_DIR="$HOME/barbossa-engineer/web_portal"
cd "$PORTAL_DIR"

echo "🚀 Quick Portal Update"
echo "======================"

# Check for changes
if [ -z "$(git status --porcelain 2>/dev/null)" ] && [ "$1" != "--force" ]; then
    echo "No changes detected in portal files"
    echo "Use --force to redeploy anyway"
    exit 0
fi

# Quick syntax check
echo "Checking syntax..."
python3 -m py_compile app.py || exit 1

# Deploy
echo "Deploying..."
./deploy.sh

# Optional: Commit changes if in git
if [ -d .git ] && [ ! -z "$1" ] && [ "$1" != "--force" ]; then
    echo ""
    echo "Committing changes..."
    git add -A
    git commit -m "Portal update: $1" || true
    echo "✅ Changes committed"
fi

echo ""
echo "✅ Quick update complete!"