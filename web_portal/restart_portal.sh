#!/bin/bash
# Restart the Barbossa Web Portal

echo "Stopping existing portal..."
pkill -f "web_portal/app.py" 2>/dev/null
sleep 2

echo "Starting new portal..."
cd ~/barbossa-engineer/web_portal
nohup python3 app.py > /tmp/portal.log 2>&1 &
echo "Portal started with PID: $!"

echo "Waiting for portal to be ready..."
sleep 3

# Test if it's responding
if curl -k https://localhost:8443/health 2>/dev/null | grep -q "healthy"; then
    echo "✅ Portal is running and healthy!"
    echo "Access at: https://eastindiaonchaincompany.xyz"
else
    echo "⚠️ Portal may not be responding yet. Check /tmp/portal.log for errors."
fi