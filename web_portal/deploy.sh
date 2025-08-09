#!/bin/bash
# Barbossa Web Portal Deployment Script
# Automates updating and restarting the portal after changes

set -e  # Exit on error

echo "======================================"
echo "🚀 Barbossa Portal Deployment Script"
echo "======================================"

# Configuration
PORTAL_DIR="$HOME/barbossa-engineer/web_portal"
TMUX_SESSION="barbossa-portal"
BACKUP_DIR="$HOME/barbossa-engineer/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Function to check if portal is healthy
check_health() {
    sleep 3
    if curl -k https://localhost:8443/health 2>/dev/null | grep -q "healthy"; then
        return 0
    else
        return 1
    fi
}

# Function to rollback on failure
rollback() {
    echo "❌ Deployment failed! Rolling back..."
    if [ -f "$BACKUP_DIR/app_$TIMESTAMP.py" ]; then
        cp "$BACKUP_DIR/app_$TIMESTAMP.py" "$PORTAL_DIR/app.py"
        cp "$BACKUP_DIR/dashboard_$TIMESTAMP.html" "$PORTAL_DIR/templates/dashboard.html"
        echo "✅ Rollback completed"
    fi
    exit 1
}

# Step 1: Pre-deployment checks
echo ""
echo "📋 Step 1: Pre-deployment checks"
echo "---------------------------------"

# Check if we're in the right directory
if [ ! -f "$PORTAL_DIR/app.py" ]; then
    echo "❌ Error: Portal files not found at $PORTAL_DIR"
    exit 1
fi

# Check Python syntax
echo "Checking Python syntax..."
python3 -m py_compile "$PORTAL_DIR/app.py" 2>/dev/null || {
    echo "❌ Python syntax error in app.py"
    exit 1
}
echo "✅ Python syntax OK"

# Check if required modules are installed
echo "Checking dependencies..."
python3 -c "import flask, flask_httpauth, secrets" 2>/dev/null || {
    echo "❌ Missing required Python modules"
    echo "Run: pip install flask flask-httpauth"
    exit 1
}
echo "✅ Dependencies OK"

# Step 2: Backup current version
echo ""
echo "💾 Step 2: Creating backup"
echo "--------------------------"
mkdir -p "$BACKUP_DIR"

# Backup main files
cp "$PORTAL_DIR/app.py" "$BACKUP_DIR/app_$TIMESTAMP.py"
cp "$PORTAL_DIR/templates/dashboard.html" "$BACKUP_DIR/dashboard_$TIMESTAMP.html"

# Keep only last 10 backups
ls -t "$BACKUP_DIR"/app_*.py 2>/dev/null | tail -n +11 | xargs -r rm
ls -t "$BACKUP_DIR"/dashboard_*.html 2>/dev/null | tail -n +11 | xargs -r rm

echo "✅ Backup created: $BACKUP_DIR/*_$TIMESTAMP.*"

# Step 3: Stop current portal
echo ""
echo "🛑 Step 3: Stopping current portal"
echo "-----------------------------------"

# Kill any running portal processes
pkill -f "web_portal/app.py" 2>/dev/null || true

# Kill tmux session if exists
tmux kill-session -t "$TMUX_SESSION" 2>/dev/null || true

# Make sure port is free
PORTAL_PID=$(lsof -t -i:8443 2>/dev/null || true)
if [ ! -z "$PORTAL_PID" ]; then
    echo "Killing process on port 8443 (PID: $PORTAL_PID)"
    kill -9 $PORTAL_PID 2>/dev/null || true
    sleep 2
fi

echo "✅ Old portal stopped"

# Step 4: Generate new self-signed certificate (optional)
echo ""
echo "🔐 Step 4: Certificate check"
echo "-----------------------------"

if [ ! -f "$PORTAL_DIR/cert.pem" ] || [ ! -f "$PORTAL_DIR/key.pem" ]; then
    echo "Generating new self-signed certificate..."
    cd "$PORTAL_DIR"
    openssl req -x509 -newkey rsa:4096 \
        -keyout key.pem -out cert.pem \
        -days 365 -nodes -subj \
        '/C=US/ST=State/L=City/O=Barbossa/CN=localhost' 2>/dev/null
    echo "✅ Certificate generated"
else
    echo "✅ Certificate exists"
fi

# Step 5: Start new portal in tmux
echo ""
echo "🚀 Step 5: Starting new portal"
echo "-------------------------------"

cd "$PORTAL_DIR"
tmux new-session -d -s "$TMUX_SESSION" "python3 app.py 2>&1 | tee -a /tmp/portal.log"

echo "✅ Portal started in tmux session: $TMUX_SESSION"

# Step 6: Health check
echo ""
echo "❤️  Step 6: Health check"
echo "------------------------"

if check_health; then
    echo "✅ Portal is healthy and responding!"
else
    echo "⚠️  Portal may not be ready yet. Retrying..."
    sleep 5
    if check_health; then
        echo "✅ Portal is healthy after retry!"
    else
        rollback
    fi
fi

# Step 7: Verify Cloudflare tunnel
echo ""
echo "☁️  Step 7: Cloudflare tunnel check"
echo "------------------------------------"

if pgrep -f cloudflared > /dev/null; then
    echo "✅ Cloudflare tunnel is running"
else
    echo "⚠️  Cloudflare tunnel not running!"
    echo "   Start with: cloudflared tunnel run eastindiaonchaincompany"
fi

# Step 8: Summary
echo ""
echo "======================================"
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "======================================"
echo ""
echo "📊 Portal Status:"
echo "  - Local:  https://localhost:8443"
echo "  - Remote: https://eastindiaonchaincompany.xyz"
echo "  - Session: tmux attach -t $TMUX_SESSION"
echo ""
echo "📝 Logs:"
echo "  - Portal: /tmp/portal.log"
echo "  - Tmux: tmux attach -t $TMUX_SESSION"
echo ""
echo "🔧 Commands:"
echo "  - View: tmux attach -t $TMUX_SESSION"
echo "  - Detach: Ctrl+B, then D"
echo "  - Logs: tail -f /tmp/portal.log"
echo "  - Stop: tmux kill-session -t $TMUX_SESSION"
echo ""

# Optional: Run tests if available
if [ -f "$PORTAL_DIR/test_portal.py" ]; then
    echo "🧪 Running tests..."
    python3 "$PORTAL_DIR/test_portal.py" && echo "✅ Tests passed" || echo "⚠️  Some tests failed"
fi

echo "Deployment complete at $(date)"