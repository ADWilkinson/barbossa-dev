#!/bin/bash
# Barbossa v3.0 - Run Script
# Creates PRs for configured repositories

cd /home/dappnode/barbossa-engineer

echo "=========================================="
echo "Barbossa v3.0 - Starting Run"
echo "Time: $(date)"
echo "=========================================="

# Run Barbossa
python3 barbossa_simple.py "$@"

echo ""
echo "=========================================="
echo "Barbossa Run Complete"
echo "Time: $(date)"
echo "=========================================="
