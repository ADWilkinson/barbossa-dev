#!/bin/bash
# Barbossa v4 Daily Run Script

cd /home/dappnode/barbossa-engineer

# Set up environment
source venv_personal_assistant/bin/activate
set -a
source .env.personal_assistant
set +a

# Add timestamp to log
echo "=====================================" >> logs/barbossa/cron.log
echo "Starting Barbossa - $(date)" >> logs/barbossa/cron.log
echo "=====================================" >> logs/barbossa/cron.log

# Run Barbossa v4
python3 barbossa_personal_assistant_v4.py >> logs/barbossa/cron.log 2>&1

# Log completion
echo "Completed - $(date)" >> logs/barbossa/cron.log
echo "" >> logs/barbossa/cron.log
