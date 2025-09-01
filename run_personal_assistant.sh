#!/bin/bash
"""
Run Barbossa Personal Assistant for Andrew
Properly configured with all API keys and safety features
"""

set -e  # Exit on error

echo "======================================================"
echo "🏴‍☠️ Barbossa Personal Assistant v2 - Andrew Wilkinson"
echo "======================================================"
echo ""

# Navigate to Barbossa directory
cd ~/barbossa-engineer

# Activate virtual environment
if [ ! -d "venv_personal_assistant" ]; then
    echo "⚠️ Virtual environment not found. Creating..."
    python3 -m venv venv_personal_assistant
    source venv_personal_assistant/bin/activate
    pip install aiohttp anthropic requests psutil schedule
else
    source venv_personal_assistant/bin/activate
fi

# Load environment variables
if [ -f ".env.personal_assistant" ]; then
    echo "✅ Loading environment variables..."
    set -a
    source .env.personal_assistant
    set +a
else
    echo "❌ ERROR: .env.personal_assistant not found!"
    exit 1
fi

# Display current mode
echo ""
echo "Current Configuration:"
echo "----------------------"
echo "  Mode: ${TEST_ENVIRONMENT:-PRODUCTION}"
echo "  Dry Run: ${DRY_RUN_MODE:-false}"
echo "  Approval Required: ${REQUIRE_APPROVAL:-false}"
echo "  Linear User: Andrew (andrew@zkp2p.xyz)"
echo "  GitHub: ADWilkinson"
echo ""

# Safety check for production mode
if [ "$DRY_RUN_MODE" != "true" ]; then
    echo "⚠️  WARNING: DRY RUN MODE IS DISABLED!"
    echo "The assistant will make REAL changes to:"
    echo "  - Linear tickets (enrichment)"
    echo "  - Documentation files"
    echo "  - GitHub repositories"
    echo ""
    read -p "Are you SURE you want to continue? Type 'yes' to proceed: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted. Set DRY_RUN_MODE=true in .env.personal_assistant for safe testing."
        exit 0
    fi
fi

# Check API keys
echo "Checking API keys..."
if [ -z "$LINEAR_API_KEY" ]; then
    echo "⚠️ Warning: LINEAR_API_KEY not set"
fi
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️ Warning: ANTHROPIC_API_KEY not set (will use static enrichment)"
fi
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️ Warning: GITHUB_TOKEN not set (GitHub features disabled)"
fi
if [ -z "$NOTION_API_KEY" ]; then
    echo "⚠️ Warning: NOTION_API_KEY not set (Notion features disabled)"
fi

echo ""
echo "======================================================"
echo "Starting Personal Assistant..."
echo "Press Ctrl+C to stop"
echo "======================================================"
echo ""

# Run the assistant
python3 barbossa_personal_assistant_v2.py

echo ""
echo "======================================================"
echo "✅ Personal Assistant execution complete"
echo "Check logs at: logs/personal_assistant/"
echo "======================================================" 