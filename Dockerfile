FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    cron \
    nodejs \
    npm \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI and package managers globally
RUN npm install -g @anthropic-ai/claude-code pnpm yarn

# Create non-root user for Claude CLI
RUN useradd -m -s /bin/bash -u 1000 barbossa \
    && echo "barbossa ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set working directory
WORKDIR /app

# Copy application files - all agents
COPY barbossa_engineer.py .
COPY barbossa_tech_lead.py .
COPY barbossa_discovery.py .
COPY barbossa_product.py .
COPY barbossa_auditor.py .

# Copy CLI and utilities
COPY barbossa .
COPY validate.py .
COPY generate_crontab.py .
COPY run.sh .
COPY config/ config/

# Make CLI executable and add to PATH
RUN chmod +x barbossa && ln -s /app/barbossa /usr/local/bin/barbossa

# Create directories with proper ownership
RUN mkdir -p logs changelogs projects \
    && chown -R barbossa:barbossa /app

# Copy entrypoint (crontab is generated at runtime from config)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh run.sh

# Create home directory for barbossa user with proper structure
RUN mkdir -p /home/barbossa/.config/gh \
    && mkdir -p /home/barbossa/.claude \
    && mkdir -p /home/barbossa/.ssh \
    && chown -R barbossa:barbossa /home/barbossa

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/barbossa

ENTRYPOINT ["/entrypoint.sh"]
