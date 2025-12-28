FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    nodejs \
    npm \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic (cron for containers)
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=cd48d45c4b10f3f0bfdd3a57d054cd05ac96812b
RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI and package managers globally
RUN npm install -g @anthropic-ai/claude-code pnpm yarn

# Create non-root user for running agents
RUN useradd -m -u 1000 -s /bin/bash barbossa

# Set working directory
WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ src/
COPY scripts/ scripts/
COPY prompts/ prompts/
COPY config/ config/
COPY tests/ tests/

# Make CLI executable and add to PATH
RUN chmod +x src/barbossa/cli/barbossa && ln -s /app/src/barbossa/cli/barbossa /usr/local/bin/barbossa

# Create directories
RUN mkdir -p logs changelogs projects

# Set ownership to barbossa user
RUN chown -R barbossa:barbossa /app

# Copy entrypoint (crontab is generated at runtime from config)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh scripts/run.sh scripts/validate.py scripts/generate_crontab.py

# Switch to non-root user
USER barbossa

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

ENTRYPOINT ["/entrypoint.sh"]
