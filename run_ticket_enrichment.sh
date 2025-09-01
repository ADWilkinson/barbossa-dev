#!/bin/bash
# Run ticket enrichment for GitHub issues

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "BARBOSSA TICKET ENRICHMENT"
echo "Started: $(date)"
echo "================================================"

# Load environment variables
if [ -f "$HOME/.barbossa_env" ]; then
    source "$HOME/.barbossa_env"
fi

# Activate virtual environment if it exists
if [ -d "venv/bin" ]; then
    source venv/bin/activate
elif [ -d "../venv/bin" ]; then
    source ../venv/bin/activate
fi

# Run ticket enrichment
python3 ticket_enrichment.py

echo ""
echo "Ticket enrichment completed: $(date)"
echo "================================================"