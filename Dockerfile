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

# Install Python dependencies
RUN pip install --no-cache-dir flask

# Create non-root user for Claude CLI
# (--dangerously-skip-permissions cannot be used with root)
RUN useradd -m -s /bin/bash -u 1000 barbossa \
    && echo "barbossa ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set working directory
WORKDIR /app

# Copy application files
COPY barbossa_simple.py .
COPY barbossa_tech_lead.py .
COPY run.sh .
COPY config/ config/
COPY web_portal/app_simple.py web_portal/

# Copy environment files for projects
COPY config/env/ config/env/

# Create directories with proper ownership
RUN mkdir -p logs changelogs projects \
    && chown -R barbossa:barbossa /app

# Copy entrypoint and cron
COPY entrypoint.sh /entrypoint.sh
COPY crontab /etc/cron.d/barbossa-cron
RUN chmod +x /entrypoint.sh run.sh \
    && chmod 0644 /etc/cron.d/barbossa-cron \
    && crontab /etc/cron.d/barbossa-cron

# Create home directory for barbossa user with proper structure
RUN mkdir -p /home/barbossa/.config/gh \
    && mkdir -p /home/barbossa/.claude \
    && mkdir -p /home/barbossa/.ssh \
    && chown -R barbossa:barbossa /home/barbossa

# Expose web portal port
EXPOSE 8080

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV HOME=/home/barbossa

ENTRYPOINT ["/entrypoint.sh"]
