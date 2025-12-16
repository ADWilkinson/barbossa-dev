#!/bin/bash
# Barbossa v5.1 - Run Script
# Creates PRs for configured repositories

cd /home/dappnode/barbossa-engineer

echo "=========================================="
echo "Barbossa v5.1 - Starting Run"
echo "Time: $(date)"
echo "=========================================="

# Run Barbossa Engineer
python3 barbossa_simple.py "$@"

echo ""
echo "=========================================="
echo "Barbossa Run Complete"
echo "Time: $(date)"
echo "=========================================="
