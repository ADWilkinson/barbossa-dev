#!/bin/bash
# Barbossa Install Script
# https://barbossa.dev
#
# Usage:
#   Interactive:  curl -fsSL .../install.sh | bash
#   With args:    curl -fsSL .../install.sh | bash -s -- username repo-name

set -e

echo ""
echo "  _b barbossa"
echo ""

# Check requirements
command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required. Install from https://docs.docker.com/get-docker/"; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "Error: GitHub CLI is required. Install from https://cli.github.com/"; exit 1; }

# Get GitHub username (from arg or prompt)
if [ -n "$1" ]; then
    GITHUB_USER="$1"
else
    echo "Enter your GitHub username:"
    read -r GITHUB_USER < /dev/tty
fi
if [ -z "$GITHUB_USER" ]; then
    echo "Error: GitHub username is required"
    exit 1
fi

# Get repository name (from arg or prompt)
if [ -n "$2" ]; then
    REPO_NAME="$2"
else
    echo ""
    echo "Enter repository name (e.g., my-app):"
    read -r REPO_NAME < /dev/tty
fi
if [ -z "$REPO_NAME" ]; then
    echo "Error: Repository name is required"
    exit 1
fi

# Create directory
INSTALL_DIR="${BARBOSSA_DIR:-barbossa}"
echo ""
echo "Creating $INSTALL_DIR directory..."
mkdir -p "$INSTALL_DIR/config" "$INSTALL_DIR/logs"
cd "$INSTALL_DIR"

# Download docker-compose.yml
echo "Downloading docker-compose.yml..."
curl -fsSL -o docker-compose.yml https://raw.githubusercontent.com/ADWilkinson/barbossa-dev/main/docker-compose.prod.yml

# Create config
echo "Creating config..."
cat > config/repositories.json << EOF
{
  "owner": "$GITHUB_USER",
  "repositories": [
    {
      "name": "$REPO_NAME",
      "url": "https://github.com/$GITHUB_USER/$REPO_NAME.git"
    }
  ]
}
EOF

# Get GitHub token
echo ""
echo "GitHub Authentication"
echo "---------------------"
echo "Generate a token:"
echo "  1. If you have gh CLI: gh auth token"
echo "  2. Or create at: https://github.com/settings/tokens"
echo "     (Required scopes: repo, workflow)"
echo ""
echo "Enter your GitHub token:"
read -r GITHUB_TOKEN < /dev/tty

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GitHub token is required"
    exit 1
fi

# Get Claude authentication token
echo ""
echo "Claude Authentication"
echo "---------------------"
echo "You need either:"
echo "  Option 1 (Recommended): Claude Pro/Max subscription token"
echo "    - Run: claude login (if not already logged in)"
echo "    - Extract token from: ~/.claude/.credentials.json (sessionKey field)"
echo "    - Token lasts up to 1 year"
echo ""
echo "  Option 2: Pay-as-you-go API key"
echo "    - Get from: https://console.anthropic.com/settings/keys"
echo ""
echo "Enter your Claude token or API key:"
read -r ANTHROPIC_API_KEY < /dev/tty

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: Claude token/API key is required"
    exit 1
fi

# Create .env file with tokens
echo ""
echo "Creating .env file with authentication tokens..."
cat > .env << EOF
# GitHub Authentication (REQUIRED)
GITHUB_TOKEN=$GITHUB_TOKEN

# Claude API Key (REQUIRED)
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

# Timezone (optional)
TZ=UTC
EOF

# Add UID for macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "" >> .env
    echo "# macOS: Run container as host UID for proper file permissions" >> .env
    echo "UID=$(id -u)" >> .env
    echo "Detected macOS - added UID=$(id -u) to .env"
fi

echo "Created .env with authentication tokens"

echo ""
echo "Done! Your setup is ready in ./$INSTALL_DIR"
echo ""
echo "Directory structure:"
echo "  $INSTALL_DIR/"
echo "  ├── config/"
echo "  │   └── repositories.json"
echo "  ├── .env (authentication tokens)"
echo "  ├── docker-compose.yml"
echo "  └── logs/"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start Barbossa:"
echo "     cd $INSTALL_DIR && docker compose up -d"
echo ""
echo "  2. Verify it's running:"
echo "     docker exec barbossa barbossa health"
echo ""
echo "  3. View logs:"
echo "     docker logs -f barbossa"
echo ""
echo "To add more repositories, edit config/repositories.json"
echo "To update tokens, edit .env file and restart: docker compose restart"
echo ""
echo "Docs: https://barbossa.dev"
echo ""
