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
