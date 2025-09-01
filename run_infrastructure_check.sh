#!/bin/bash
# Quick infrastructure check - only critical issues

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "BARBOSSA INFRASTRUCTURE CHECK"
echo "Started: $(date)"
echo "================================================"

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "⚠️  CRITICAL: Disk usage at ${DISK_USAGE}%"
    # Log the issue for manual review
    echo "[$(date)] CRITICAL: Disk usage at ${DISK_USAGE}%. Needs cleanup" >> logs/infrastructure_alerts.log
else
    echo "✓ Disk usage: ${DISK_USAGE}% (OK)"
fi

# Check memory usage
MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "⚠️  CRITICAL: Memory usage at ${MEM_USAGE}%"
    echo "[$(date)] CRITICAL: Memory usage at ${MEM_USAGE}%. Investigate memory issues" >> logs/infrastructure_alerts.log
else
    echo "✓ Memory usage: ${MEM_USAGE}% (OK)"
fi

# Check critical services and processes
echo "Checking critical services..."

# Check Docker service
if systemctl is-active --quiet docker; then
    echo "✓ Service docker: Active"
else
    echo "⚠️  CRITICAL: Docker service is not running!"
    echo "[$(date)] CRITICAL: Docker service is down" >> logs/infrastructure_alerts.log
fi

# Check Cloudflared tunnel (runs in tmux, not as systemd service)
if pgrep -f "cloudflared tunnel" > /dev/null; then
    echo "✓ Cloudflared tunnel: Running"
else
    echo "⚠️  CRITICAL: Cloudflared tunnel is not running!"
    echo "[$(date)] CRITICAL: Cloudflared tunnel is down" >> logs/infrastructure_alerts.log
    # Try to restart in tmux
    echo "Attempting to restart cloudflared tunnel..."
    tmux new-session -d -s tunnel "cloudflared tunnel run eastindia" 2>/dev/null
    sleep 3
    if pgrep -f "cloudflared tunnel" > /dev/null; then
        echo "✓ Successfully restarted cloudflared tunnel"
        echo "[$(date)] Cloudflared tunnel was down but successfully restarted" >> logs/infrastructure_alerts.log
    else
        echo "✗ Failed to restart cloudflared - manual intervention required"
        echo "[$(date)] FAILED to restart cloudflared - needs manual intervention" >> logs/infrastructure_alerts.log
    fi
fi

# Check for PostgreSQL (multiple possible service names)
PG_RUNNING=false
for pg_service in postgresql postgresql@14-main postgresql@15-main postgres; do
    if systemctl is-active --quiet $pg_service 2>/dev/null; then
        echo "✓ PostgreSQL service ($pg_service): Active"
        PG_RUNNING=true
        break
    fi
done

if [ "$PG_RUNNING" = false ]; then
    # Check if postgres is running as a process
    if pgrep -f "postgres" > /dev/null; then
        echo "✓ PostgreSQL: Running (non-systemd)"
    else
        echo "⚠️  WARNING: PostgreSQL service not found or not running"
        echo "[$(date)] WARNING: PostgreSQL not detected" >> logs/infrastructure_alerts.log
    fi
fi

# Check for security updates
SECURITY_UPDATES=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
if [ "$SECURITY_UPDATES" -gt 0 ]; then
    echo "⚠️  Security updates available: $SECURITY_UPDATES"
    # Don't auto-apply, just log for manual review
fi

echo ""
echo "Infrastructure check completed: $(date)"
echo "================================================"