#!/bin/bash

# Barbossa Setup Script
# Initializes the Barbossa autonomous software engineer with security checks

set -e

echo "==========================================="
echo "BARBOSSA SETUP - Autonomous Software Engineer"
echo "==========================================="
echo ""
echo "SECURITY: ZKP2P organization access is BLOCKED"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as appropriate user
echo -e "${YELLOW}Checking environment...${NC}"

# Install Python dependencies if needed
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install --user requests --break-system-packages 2>/dev/null || echo "Dependencies may already be installed"

# Test security system
echo -e "${YELLOW}Testing security system...${NC}"
cd /home/dappnode/barbossa-engineer
python3 barbossa.py --test-security

if [ $? -ne 0 ]; then
    echo -e "${RED}Security test failed! Setup aborted.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Security system validated${NC}"

# Initialize work directories
echo -e "${YELLOW}Initializing work directories...${NC}"
mkdir -p projects
mkdir -p logs
mkdir -p changelogs
mkdir -p work_tracking
mkdir -p security

# Set up Git configuration
echo -e "${YELLOW}Configuring Git...${NC}"
git config --global user.name "Barbossa"
git config --global user.email "barbossa@eastindiaonchaincompany.xyz"

# Create GitHub repository setup script
cat > create_github_repo.sh << 'EOF'
#!/bin/bash
# This script should be run manually to create the GitHub repository

echo "Creating GitHub repository for Barbossa..."
echo "Please ensure you have GitHub CLI (gh) installed and authenticated"
echo ""

# Create repository
gh repo create barbossa-engineer \
  --private \
  --description "Autonomous software engineer with strict security controls" \
  --homepage "https://eastindiaonchaincompany.xyz"

# Add remote
git remote add origin https://github.com/ADWilkinson/barbossa-engineer.git

# Push initial commit
git add .
git commit -m "Initial commit: Barbossa autonomous software engineer

- Implemented strict security guards to prevent ZKP2P org access
- Created work area selection system with balanced coverage
- Set up changelog and audit logging
- Configured repository whitelist for ADWilkinson repos only"

git push -u origin main

echo "Repository created and pushed successfully!"
EOF

chmod +x create_github_repo.sh

# Create cron job setup script
cat > setup_cron.sh << 'EOF'
#!/bin/bash
# Sets up cron job for Barbossa execution every 4 hours

BARBOSSA_DIR="/home/dappnode/barbossa-engineer"
CLAUDE_CMD="claude --dangerously-skip-permissions"

# Create the cron execution script
cat > $BARBOSSA_DIR/run_barbossa.sh << 'SCRIPT'
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
SCRIPT

chmod +x $BARBOSSA_DIR/run_barbossa.sh

# Add to crontab (every 4 hours)
echo "Adding cron job for Barbossa (every 4 hours)..."
(crontab -l 2>/dev/null; echo "0 */4 * * * $BARBOSSA_DIR/run_barbossa.sh") | crontab -

echo "Cron job added successfully!"
echo "Barbossa will run every 4 hours"
crontab -l | grep barbossa
EOF

chmod +x setup_cron.sh

# Create test runner script
cat > test_barbossa.sh << 'EOF'
#!/bin/bash
# Test Barbossa execution

echo "Testing Barbossa execution..."
cd /home/dappnode/barbossa-engineer

# Run with test parameters
python3 barbossa.py --tally '{"infrastructure": 1, "personal_projects": 2, "davy_jones": 0}'

echo ""
echo "Test complete! Check logs in ./logs/ for details"
EOF

chmod +x test_barbossa.sh

# Summary
echo ""
echo -e "${GREEN}==========================================="
echo "BARBOSSA SETUP COMPLETE!"
echo "==========================================="
echo ""
echo "Security Status: ACTIVE - ZKP2P access BLOCKED"
echo ""
echo "Next steps:"
echo "1. Run ./create_github_repo.sh to create GitHub repository"
echo "2. Run ./setup_cron.sh to enable scheduled execution"
echo "3. Run ./test_barbossa.sh to test the system"
echo ""
echo "Manual execution:"
echo "  python3 barbossa.py [--area AREA] [--tally JSON]"
echo ""
echo "Check status:"
echo "  python3 barbossa.py --status"
echo ""
echo "Logs location: ./logs/"
echo "Changelogs location: ./changelogs/"
echo "Security audit: ./security/audit.log"
echo "===========================================${NC}"