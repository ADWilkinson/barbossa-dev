#!/bin/bash
# Development Workflow Helper for Barbossa Portal
# Helps with editing, testing, and deploying changes

echo "======================================"
echo "🛠️  Barbossa Portal Dev Workflow"
echo "======================================"

PORTAL_DIR="$HOME/barbossa-engineer/web_portal"
TMUX_SESSION="barbossa-portal"

# Function to show menu
show_menu() {
    echo ""
    echo "What would you like to do?"
    echo "1) Edit portal code (app.py)"
    echo "2) Edit dashboard HTML"
    echo "3) View current logs"
    echo "4) Test changes locally"
    echo "5) Deploy changes"
    echo "6) Rollback to previous version"
    echo "7) View portal in tmux"
    echo "8) Stop portal"
    echo "9) Exit"
    echo ""
    read -p "Select option (1-9): " choice
}

# Main loop
while true; do
    show_menu
    
    case $choice in
        1)
            echo "Opening app.py in editor..."
            ${EDITOR:-nano} "$PORTAL_DIR/app.py"
            ;;
            
        2)
            echo "Opening dashboard.html in editor..."
            ${EDITOR:-nano} "$PORTAL_DIR/templates/dashboard.html"
            ;;
            
        3)
            echo "Showing last 50 lines of portal log..."
            tail -n 50 /tmp/portal.log
            echo ""
            read -p "Press Enter to continue..."
            ;;
            
        4)
            echo "Testing Python syntax..."
            python3 -m py_compile "$PORTAL_DIR/app.py" && echo "✅ Syntax OK" || echo "❌ Syntax error"
            echo ""
            read -p "Press Enter to continue..."
            ;;
            
        5)
            echo "Deploying changes..."
            "$PORTAL_DIR/deploy.sh"
            read -p "Press Enter to continue..."
            ;;
            
        6)
            echo "Available backups:"
            ls -lt "$HOME/barbossa-engineer/backups"/app_*.py 2>/dev/null | head -5
            echo ""
            read -p "Enter backup timestamp (YYYYMMDD_HHMMSS) or 'cancel': " timestamp
            if [ "$timestamp" != "cancel" ] && [ -f "$HOME/barbossa-engineer/backups/app_$timestamp.py" ]; then
                cp "$HOME/barbossa-engineer/backups/app_$timestamp.py" "$PORTAL_DIR/app.py"
                cp "$HOME/barbossa-engineer/backups/dashboard_$timestamp.html" "$PORTAL_DIR/templates/dashboard.html"
                echo "✅ Restored backup from $timestamp"
                echo "Run option 5 to deploy the restored version"
            else
                echo "Cancelled or backup not found"
            fi
            read -p "Press Enter to continue..."
            ;;
            
        7)
            echo "Attaching to tmux session..."
            tmux attach -t "$TMUX_SESSION"
            ;;
            
        8)
            echo "Stopping portal..."
            tmux kill-session -t "$TMUX_SESSION" 2>/dev/null || echo "Session not running"
            pkill -f "web_portal/app.py" 2>/dev/null || true
            echo "✅ Portal stopped"
            read -p "Press Enter to continue..."
            ;;
            
        9)
            echo "Exiting..."
            exit 0
            ;;
            
        *)
            echo "Invalid option"
            ;;
    esac
done