#!/bin/bash
# Barbossa - Run Script
# Creates PRs for configured repositories

# Use BARBOSSA_DIR if set, otherwise use script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BARBOSSA_DIR="${BARBOSSA_DIR:-$SCRIPT_DIR}"

cd "$BARBOSSA_DIR"

echo "=========================================="
echo "Barbossa - Starting Run"
echo "Time: $(date)"
echo "Directory: $BARBOSSA_DIR"
echo "=========================================="

# Run Barbossa Engineer
python3 barbossa_simple.py "$@"

echo ""
echo "=========================================="
echo "Barbossa Run Complete"
echo "Time: $(date)"
echo "=========================================="
