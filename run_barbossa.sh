#!/bin/bash

# Barbossa Cron Execution Script
BARBOSSA_DIR="/home/dappnode/barbossa-engineer"
LOG_FILE="$BARBOSSA_DIR/logs/cron_$(date +%Y%m%d_%H%M%S).log"

echo "Starting Barbossa at $(date)" >> $LOG_FILE

# Load current work tally
cd $BARBOSSA_DIR
TALLY=$(cat work_tracking/work_tally.json)

# Generate prompt with current data
DATE=$(date +%Y-%m-%d)
SESSION_ID=$(date +%s)
INFRASTRUCTURE_COUNT=$(echo $TALLY | jq -r '.infrastructure')
PERSONAL_PROJECTS_COUNT=$(echo $TALLY | jq -r '.personal_projects')
DAVY_JONES_COUNT=$(echo $TALLY | jq -r '.davy_jones')

# Create dynamic prompt
sed -e "s/{DATE}/$DATE/g" \
    -e "s/{SESSION_ID}/$SESSION_ID/g" \
    -e "s/{INFRASTRUCTURE_COUNT}/$INFRASTRUCTURE_COUNT/g" \
    -e "s/{PERSONAL_PROJECTS_COUNT}/$PERSONAL_PROJECTS_COUNT/g" \
    -e "s/{DAVY_JONES_COUNT}/$DAVY_JONES_COUNT/g" \
    barbossa_prompt.txt > /tmp/barbossa_prompt_$SESSION_ID.txt

# Execute with Claude
claude --dangerously-skip-permissions < /tmp/barbossa_prompt_$SESSION_ID.txt >> $LOG_FILE 2>&1

# Clean up
rm /tmp/barbossa_prompt_$SESSION_ID.txt

echo "Barbossa completed at $(date)" >> $LOG_FILE
