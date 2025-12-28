#!/bin/bash
# Barbossa - Run Script
# Creates PRs for configured repositories

# Use BARBOSSA_DIR if set, otherwise use project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BARBOSSA_DIR="${BARBOSSA_DIR:-$(dirname "$SCRIPT_DIR")}"

cd "$BARBOSSA_DIR"
export PYTHONPATH="${BARBOSSA_DIR}/src:${PYTHONPATH}"

echo "=========================================="
echo "Barbossa - Starting Run"
echo "Time: $(date)"
echo "Directory: $BARBOSSA_DIR"
echo "=========================================="

# Run Barbossa Engineer
python3 -m barbossa.agents.engineer "$@"

echo ""
echo "=========================================="
echo "Barbossa Run Complete"
echo "Time: $(date)"
echo "=========================================="
