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
echo "  Option 1 (Recommended): Claude Pro/Max OAuth token"
echo "    - Run in a separate terminal: claude setup-token"
echo "    - Follow prompts to generate a long-lived token (lasts up to 1 year)"
echo "    - The token will start with: sk-ant-oat01-..."
echo ""
echo "  Option 2: Pay-as-you-go API key"
echo "    - Get from: https://console.anthropic.com/settings/keys"
echo "    - The key will start with: sk-ant-api03-..."
echo ""
echo "Enter your Claude OAuth token OR API key:"
read -r CLAUDE_TOKEN < /dev/tty

if [ -z "$CLAUDE_TOKEN" ]; then
    echo "Error: Claude authentication is required"
    exit 1
fi

# Detect token type and set appropriate variable
if [[ "$CLAUDE_TOKEN" == sk-ant-oat* ]]; then
    CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_TOKEN"
    ANTHROPIC_API_KEY=""
    echo "Detected Claude Pro/Max OAuth token"
elif [[ "$CLAUDE_TOKEN" == sk-ant-api* ]]; then
    ANTHROPIC_API_KEY="$CLAUDE_TOKEN"
    CLAUDE_CODE_OAUTH_TOKEN=""
    echo "Detected Anthropic API key"
else
    echo "Warning: Token format not recognized, setting as OAuth token"
    CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_TOKEN"
    ANTHROPIC_API_KEY=""
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
echo "Done! Your setup is ready."
echo ""
echo "Next steps:"
echo ""
echo "  1. Start Barbossa:"
echo "     cd $INSTALL_DIR && docker compose up -d"
echo ""
echo "  2. Verify it's working:"
echo "     docker exec barbossa barbossa doctor"
echo ""
echo "What happens next:"
echo "  - Discovery agent scans your code, creates issues labeled 'backlog'"
echo "  - Engineer picks issues and creates PRs"
echo "  - Tech Lead reviews and merges"
echo "  - Your first PR should appear within ~2 hours"
echo ""
echo "Useful commands:"
echo "  barbossa doctor     Full diagnostics"
echo "  barbossa watch      Tail all logs"
echo "  barbossa engineer   Run engineer now"
echo ""
echo "Docs: https://barbossa.dev"
echo ""
