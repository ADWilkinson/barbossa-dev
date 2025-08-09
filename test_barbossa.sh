#!/bin/bash
# Test Barbossa execution

echo "Testing Barbossa execution..."
cd /home/dappnode/barbossa-engineer

# Run with test parameters
python3 barbossa.py --tally '{"infrastructure": 1, "personal_projects": 2, "davy_jones": 0}'

echo ""
echo "Test complete! Check logs in ./logs/ for details"
