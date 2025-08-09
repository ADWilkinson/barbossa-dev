#!/bin/bash
# Start Barbossa Web Portal in tmux session

SESSION_NAME="barbossa-portal"

echo "Stopping any existing portal..."
pkill -f "web_portal/app.py" 2>/dev/null
sleep 2

# Kill existing tmux session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

echo "Starting Barbossa portal in tmux session: $SESSION_NAME"
cd ~/barbossa-engineer/web_portal

# Create new tmux session and run the portal
tmux new-session -d -s $SESSION_NAME "python3 app.py"

echo "Portal started in tmux session: $SESSION_NAME"
echo "To attach: tmux attach-session -t $SESSION_NAME"
echo "To detach: Ctrl+B, then D"

# Wait for portal to be ready
sleep 3

# Test if it's responding
if curl -k https://localhost:8443/health 2>/dev/null | grep -q "healthy"; then
    echo "✅ Portal is running and healthy!"
    echo "Access at: https://eastindiaonchaincompany.xyz"
    echo ""
    echo "Tmux commands:"
    echo "  View session: tmux attach -t $SESSION_NAME"
    echo "  List sessions: tmux ls"
    echo "  Detach: Ctrl+B, then D"
else
    echo "⚠️ Portal may not be responding yet. Check tmux session:"
    echo "  tmux attach -t $SESSION_NAME"
fi