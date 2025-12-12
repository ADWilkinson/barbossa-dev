FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    cron \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code

# Install Python dependencies
RUN pip install --no-cache-dir flask

# Set working directory
WORKDIR /app

# Copy application files
COPY barbossa_simple.py .
COPY run.sh .
COPY config/ config/
COPY web_portal/app_simple.py web_portal/

# Create directories
RUN mkdir -p logs changelogs projects

# Copy entrypoint and cron
COPY entrypoint.sh /entrypoint.sh
COPY crontab /etc/cron.d/barbossa-cron
RUN chmod +x /entrypoint.sh run.sh \
    && chmod 0644 /etc/cron.d/barbossa-cron \
    && crontab /etc/cron.d/barbossa-cron

# Expose web portal port
EXPOSE 8080

# Environment variables (set via docker-compose or runtime)
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/entrypoint.sh"]
