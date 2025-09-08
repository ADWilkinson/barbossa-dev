#!/bin/bash
"""
Startup script for Barbossa Personal Assistant
Runs in safe/test mode for Andrew's workflow automation
"""

echo "=================================================="
echo "Barbossa Personal Assistant - Andrew's Automation"
echo "=================================================="
echo ""

# Change to Barbossa directory
cd ~/barbossa-engineer

# Check if virtual environment exists
if [ ! -d "venv_personal_assistant" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv_personal_assistant
    source venv_personal_assistant/bin/activate
    pip install schedule requests psutil
else
    source venv_personal_assistant/bin/activate
fi

# Load environment variables
if [ -f ".env.personal_assistant" ]; then
    echo "Loading environment variables..."
    set -a
    source .env.personal_assistant
    set +a
else
    echo "ERROR: .env.personal_assistant not found!"
    echo "Please ensure API keys are configured."
    exit 1
fi

# Safety check
if [ "$DRY_RUN_MODE" != "true" ]; then
    echo ""
    echo "⚠️  WARNING: Dry run mode is disabled!"
    echo "The system will make REAL changes to Linear, Notion, and repositories."
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
fi

# Run tests first
echo ""
echo "Running system tests..."
python3 test_personal_assistant.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Tests failed! Please fix issues before running."
    exit 1
fi

echo ""
echo "✅ All tests passed!"
echo ""
echo "Starting Barbossa Personal Assistant..."
echo "Mode: ${TEST_ENVIRONMENT:-PRODUCTION}"
echo "Dry Run: ${DRY_RUN_MODE:-false}"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================================="
echo ""

# Run the personal assistant
python3 barbossa_personal_assistant.py