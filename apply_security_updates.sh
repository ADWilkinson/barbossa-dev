#!/bin/bash
# Script to apply security updates
# Run with: sudo bash apply_security_updates.sh

echo "================================================"
echo "APPLYING SECURITY UPDATES"
echo "Started: $(date)"
echo "================================================"

# Update package list
echo "Updating package list..."
apt update

# List security updates
echo ""
echo "Security updates to be applied:"
apt list --upgradable 2>/dev/null | grep -i security

# Apply only security updates
echo ""
echo "Applying security updates..."
apt-get install -y --only-upgrade $(apt list --upgradable 2>/dev/null | grep -i security | cut -d/ -f1)

# Clean up
apt autoremove -y
apt autoclean

echo ""
echo "================================================"
echo "Security updates completed: $(date)"
echo "================================================"

# Log the update
echo "[$(date)] Security updates applied successfully" >> /home/dappnode/barbossa-engineer/logs/infrastructure_alerts.log
