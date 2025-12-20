#!/bin/bash
# Start Barbossa Web Portal

# Use BARBOSSA_DIR if set, otherwise use script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BARBOSSA_DIR="${BARBOSSA_DIR:-$SCRIPT_DIR}"

cd "$BARBOSSA_DIR/web_portal"

echo "Starting Barbossa Web Portal..."
echo "Dashboard: http://localhost:8443"

python3 app_simple.py
