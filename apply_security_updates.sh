#!/bin/bash
# Security updates check and application script
# Run with --check to only check, or --apply to apply updates

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-check}"

echo "================================================"
echo "SECURITY UPDATES MANAGER"
echo "Started: $(date)"
echo "Mode: $MODE"
echo "================================================"

# Check for security updates
echo "Checking for available security updates..."
SECURITY_UPDATES=$(apt list --upgradable 2>/dev/null | grep -i security)
UPDATE_COUNT=$(echo "$SECURITY_UPDATES" | grep -c security)

if [ "$UPDATE_COUNT" -eq 0 ]; then
    echo "✓ No security updates available - system is up to date!"
else
    echo "⚠️  Found $UPDATE_COUNT security updates:"
    echo "$SECURITY_UPDATES" | head -20
    
    if [ "$MODE" == "--apply" ]; then
        echo ""
        echo "NOTE: Applying security updates requires sudo privileges."
        echo "To apply updates manually, run:"
        echo ""
        echo "  sudo apt update"
        echo "  sudo apt upgrade -y"
        echo ""
        echo "Or for security updates only:"
        echo "  sudo apt-get install --only-upgrade \$(apt list --upgradable 2>/dev/null | grep -i security | cut -d'/' -f1)"
        echo ""
        echo "[$(date)] Security updates available: $UPDATE_COUNT packages" >> logs/infrastructure_alerts.log
    else
        echo ""
        echo "Run this script with --apply to see instructions for applying updates"
    fi
fi

echo ""
echo "Security check completed: $(date)"
echo "================================================"