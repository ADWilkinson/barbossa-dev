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

# Detect macOS and create .env file for proper permissions
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo "Detected macOS - configuring permissions..."
    cat > .env << EOF
# macOS: Run container as host UID to access mounted credentials
# This allows the container to read ~/.config/gh and ~/.claude
UID=$(id -u)
EOF
    echo "Created .env with UID=$(id -u)"
fi

echo ""
echo "Done! Your setup is ready in ./$INSTALL_DIR"
echo ""
echo "Directory structure:"
echo "  $INSTALL_DIR/"
echo "  ├── config/"
echo "  │   └── repositories.json"
echo "  ├── docker-compose.yml"
if [[ "$OSTYPE" == "darwin"* ]]; then
echo "  ├── .env (macOS permissions config)"
fi
echo "  └── logs/"
echo ""
echo "Next steps:"
echo ""
echo "  1. Make sure you're authenticated:"
echo "     gh auth login"
echo "     claude login"
echo ""
echo "  2. Start Barbossa:"
echo "     cd $INSTALL_DIR && docker compose up -d"
echo ""
echo "  3. Verify it's running:"
echo "     docker exec barbossa barbossa health"
echo ""
echo "To add more repositories, edit config/repositories.json"
echo ""
echo "Docs: https://barbossa.dev"
echo ""
