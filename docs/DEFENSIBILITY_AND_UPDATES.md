# Barbossa: Code Protection & OTA Updates

## Overview

Two critical product defensibility concerns:
1. **Code Protection** - Prevent copying/reverse-engineering of the system
2. **OTA Updates** - Push updates to users without manual intervention

---

## Part 1: Code Protection

### Reality Check

> No obfuscation is unbreakable. The goal is to make reverse-engineering **more effort than it's worth**.

Since users run on their own infrastructure, they have full access to the container. Our strategy:
1. Make code hard to read/copy
2. Make critical functionality server-dependent
3. Make the license essential, not just a check

---

### Strategy: Multi-Layer Protection

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: Compiled Binaries (Nuitka)                           │
│  Python → C → Native binary                                     │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: Obfuscation (PyArmor)                                │
│  Encrypt bytecode, anti-debug, code virtualization             │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: Server-Side Dependencies                             │
│  Critical prompts/logic fetched from barbossa.dev              │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: License-Gated Features                               │
│  Agents won't function without valid license + server handshake │
└─────────────────────────────────────────────────────────────────┘
```

---

### Layer 1: Compile Python to Binary (Nuitka)

**Why Nuitka over PyInstaller:**
- Compiles to actual C code, then to native binary
- Much harder to decompile than PyInstaller bundles
- Better performance (30-50% faster)
- Commercial-friendly license

**Implementation:**

```dockerfile
# Dockerfile.production
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    patchelf \
    ccache \
    && rm -rf /var/lib/apt/lists/*

# Install Nuitka
RUN pip install nuitka ordered-set zstandard

WORKDIR /build
COPY . .

# Compile each agent to binary
RUN python -m nuitka \
    --standalone \
    --onefile \
    --remove-output \
    --assume-yes-for-downloads \
    --output-filename=barbossa-engineer \
    --include-data-files=./prompts/*=prompts/ \
    barbossa_simple.py

RUN python -m nuitka \
    --standalone \
    --onefile \
    --remove-output \
    --output-filename=barbossa-tech-lead \
    barbossa_tech_lead.py

RUN python -m nuitka \
    --standalone \
    --onefile \
    --remove-output \
    --output-filename=barbossa-discovery \
    barbossa_discovery.py

RUN python -m nuitka \
    --standalone \
    --onefile \
    --remove-output \
    --output-filename=barbossa-product \
    barbossa_product.py

RUN python -m nuitka \
    --standalone \
    --onefile \
    --remove-output \
    --output-filename=barbossa-auditor \
    barbossa_auditor.py

# Production image - only binaries, no Python source
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh

# Copy only compiled binaries - NO SOURCE CODE
COPY --from=builder /build/barbossa-engineer /usr/local/bin/
COPY --from=builder /build/barbossa-tech-lead /usr/local/bin/
COPY --from=builder /build/barbossa-discovery /usr/local/bin/
COPY --from=builder /build/barbossa-product /usr/local/bin/
COPY --from=builder /build/barbossa-auditor /usr/local/bin/

# Web portal (also compiled)
COPY --from=builder /build/barbossa-portal /usr/local/bin/

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

**Build command:**
```bash
docker build -f Dockerfile.production -t barbossa/agent:latest .
```

---

### Layer 2: Obfuscation (PyArmor)

For additional protection before Nuitka compilation:

```bash
# Install PyArmor
pip install pyarmor

# Obfuscate before compilation
pyarmor gen \
    --pack onefile \
    --enable-rft \
    --enable-bcc \
    --assert-call \
    --private \
    barbossa_simple.py barbossa_tech_lead.py barbossa_discovery.py
```

**PyArmor features:**
- `--enable-rft`: Rename functions/variables to meaningless names
- `--enable-bcc`: Convert Python to C extensions
- `--assert-call`: Verify call stack integrity
- `--private`: Prevent import from other scripts

---

### Layer 3: Server-Side Dependencies (Critical)

**This is the most important layer.** Keep essential components on barbossa.dev:

```python
# In the compiled binary, prompts are fetched, not stored locally

import requests
import hashlib

def get_agent_prompt(agent_type: str, license_key: str) -> str:
    """Fetch agent prompt from server. No local copy exists."""

    # Generate request signature
    timestamp = int(time.time())
    signature = hashlib.sha256(
        f"{license_key}:{agent_type}:{timestamp}:{SECRET_SALT}".encode()
    ).hexdigest()

    response = requests.post(
        "https://barbossa.dev/api/v1/prompts",
        json={
            "license_key": license_key,
            "agent": agent_type,
            "timestamp": timestamp,
            "signature": signature
        },
        timeout=30
    )

    if response.status_code != 200:
        raise LicenseError("Failed to fetch agent configuration")

    # Prompt is returned encrypted, decrypted with license-derived key
    encrypted_prompt = response.json()["prompt"]
    return decrypt_prompt(encrypted_prompt, license_key)
```

**What to keep server-side:**
- Agent system prompts (the "secret sauce")
- Quality scoring algorithms
- Review criteria thresholds
- Feature detection heuristics

**What stays local:**
- Basic orchestration (cron triggers)
- Git operations
- Claude CLI invocation
- Log management

---

### Layer 4: License-Gated Execution

Every agent execution requires server validation:

```python
# license_guard.py (compiled into binary)

import requests
import time
import hashlib
import os
import json

BARBOSSA_API = "https://barbossa.dev/api/v1"
CACHE_FILE = "/tmp/.barbossa_license_cache"
CACHE_TTL = 3600  # 1 hour

class LicenseGuard:
    def __init__(self, license_key: str):
        self.license_key = license_key
        self.machine_id = self._get_machine_id()

    def _get_machine_id(self) -> str:
        """Generate unique machine identifier."""
        factors = [
            os.environ.get("HOSTNAME", ""),
            open("/etc/machine-id").read().strip() if os.path.exists("/etc/machine-id") else "",
            os.environ.get("USER", ""),
        ]
        return hashlib.sha256(":".join(factors).encode()).hexdigest()[:32]

    def validate(self) -> dict:
        """Validate license. Required before any agent execution."""

        # Check cache first
        cached = self._check_cache()
        if cached:
            return cached

        # Call validation API
        response = requests.post(
            f"{BARBOSSA_API}/validate",
            json={
                "license_key": self.license_key,
                "machine_id": self.machine_id,
                "version": VERSION,
                "timestamp": int(time.time())
            },
            timeout=30
        )

        if response.status_code == 403:
            raise LicenseError("Invalid or expired license")

        if response.status_code == 429:
            raise LicenseError("Too many validation requests")

        if response.status_code != 200:
            raise LicenseError("License validation failed")

        result = response.json()

        # Cache valid response
        self._save_cache(result)

        return result

    def _check_cache(self) -> dict | None:
        """Check if we have a valid cached license."""
        if not os.path.exists(CACHE_FILE):
            return None

        try:
            with open(CACHE_FILE) as f:
                cached = json.load(f)

            if cached.get("cached_at", 0) + CACHE_TTL > time.time():
                return cached
        except:
            pass

        return None

    def _save_cache(self, result: dict):
        """Cache license validation result."""
        result["cached_at"] = time.time()
        with open(CACHE_FILE, "w") as f:
            json.dump(result, f)


# Usage in agent entry point
def main():
    config = load_config("/app/barbossa.json")

    # REQUIRED: Validate license before any work
    guard = LicenseGuard(config["license_key"])
    license_info = guard.validate()

    if not license_info.get("valid"):
        print("ERROR: Valid Barbossa license required")
        print("Get your license at https://barbossa.dev")
        sys.exit(1)

    # Fetch server-side prompts (also validates license)
    agent_prompt = get_agent_prompt("engineer", config["license_key"])

    # Now run the agent...
    run_engineer(config, agent_prompt)
```

---

### Anti-Tampering Measures

```python
# integrity.py (compiled into binary)

import hashlib
import os
import sys

# Embedded at build time
EXPECTED_HASHES = {
    "/usr/local/bin/barbossa-engineer": "sha256:xxxx",
    "/usr/local/bin/barbossa-tech-lead": "sha256:xxxx",
    # ... other binaries
}

def verify_integrity():
    """Check that binaries haven't been modified."""
    for path, expected in EXPECTED_HASHES.items():
        if not os.path.exists(path):
            return False

        with open(path, "rb") as f:
            actual = f"sha256:{hashlib.sha256(f.read()).hexdigest()}"

        if actual != expected:
            # Binary was modified
            return False

    return True

def check_debugger():
    """Detect if running under debugger."""
    # Linux: check TracerPid
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("TracerPid:"):
                    tracer_pid = int(line.split(":")[1].strip())
                    if tracer_pid != 0:
                        return True  # Being debugged
    except:
        pass

    return False

# Called at startup
def security_check():
    if check_debugger():
        print("Security: Debugging not permitted")
        sys.exit(1)

    if not verify_integrity():
        print("Security: Binary integrity check failed")
        sys.exit(1)
```

---

## Part 2: Over-The-Air Updates

### Update Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│  UPDATE FLOW                                                    │
├─────────────────────────────────────────────────────────────────┤
│  1. Container checks barbossa.dev/api/v1/version on startup    │
│  2. If new version available:                                  │
│     - NOTIFY: Log message + optional email                     │
│     - or AUTO: Pull new image + restart container              │
│  3. Watchtower integration for seamless auto-updates           │
└─────────────────────────────────────────────────────────────────┘
```

---

### Option A: Watchtower (Recommended for V1)

[Watchtower](https://containrrr.dev/watchtower/) automatically updates running containers.

**User setup (docker-compose.yml):**

```yaml
version: "3.8"

services:
  barbossa:
    image: ghcr.io/barbossa-dev/agent:latest
    container_name: barbossa
    restart: unless-stopped
    volumes:
      - ./barbossa.json:/app/barbossa.json:ro
      - ~/.claude:/root/.claude
      - ~/.ssh:/root/.ssh:ro
      - ~/.gitconfig:/root/.gitconfig:ro
      - ./logs:/app/logs
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - TZ=Europe/London
    ports:
      - "8443:8080"
    labels:
      - "com.centurylinklabs.watchtower.enable=true"

  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_POLL_INTERVAL=3600  # Check every hour
      - WATCHTOWER_INCLUDE_STOPPED=false
      - WATCHTOWER_LABEL_ENABLE=true   # Only update labeled containers
    command: --interval 3600
```

**How it works:**
1. Watchtower runs alongside Barbossa
2. Every hour, checks ghcr.io for new `agent:latest` image
3. If new version found, pulls it and restarts container
4. Zero user intervention required

**Pros:**
- Simple, proven solution
- User controls update frequency
- No custom code needed

**Cons:**
- Requires Watchtower container
- All-or-nothing (can't do gradual rollout)

---

### Option B: Built-in Update Checker

For more control, build update checking into Barbossa itself:

```python
# updater.py (compiled into binary)

import requests
import subprocess
import sys
import os
from packaging import version

VERSION = "1.2.0"  # Embedded at build time
UPDATE_API = "https://barbossa.dev/api/v1/version"

class Updater:
    def __init__(self, license_key: str, update_policy: str = "notify"):
        """
        update_policy: "notify" | "auto" | "disabled"
        """
        self.license_key = license_key
        self.update_policy = update_policy

    def check_for_updates(self) -> dict | None:
        """Check if a newer version is available."""
        try:
            response = requests.get(
                UPDATE_API,
                params={
                    "license_key": self.license_key,
                    "current_version": VERSION
                },
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()
            latest = data.get("latest_version")

            if latest and version.parse(latest) > version.parse(VERSION):
                return {
                    "current": VERSION,
                    "latest": latest,
                    "changelog": data.get("changelog", ""),
                    "critical": data.get("critical", False),
                    "download_url": data.get("download_url")
                }
        except Exception as e:
            print(f"Update check failed: {e}")

        return None

    def handle_update(self, update_info: dict):
        """Handle available update based on policy."""

        if self.update_policy == "disabled":
            return

        if self.update_policy == "notify":
            self._notify_update(update_info)

        elif self.update_policy == "auto":
            if update_info.get("critical"):
                self._auto_update(update_info)
            else:
                self._notify_update(update_info)

    def _notify_update(self, update_info: dict):
        """Log update availability."""
        print("=" * 60)
        print(f"UPDATE AVAILABLE: v{update_info['current']} → v{update_info['latest']}")
        if update_info.get("critical"):
            print("⚠️  CRITICAL UPDATE - Please update immediately")
        print(f"Changelog: {update_info.get('changelog', 'N/A')}")
        print("Run: docker pull ghcr.io/barbossa-dev/agent:latest")
        print("=" * 60)

        # Also send to configured notification channels
        self._send_notification(update_info)

    def _send_notification(self, update_info: dict):
        """Send email/webhook notification."""
        # Implemented based on user config
        pass

    def _auto_update(self, update_info: dict):
        """Trigger automatic update (container restart)."""
        print(f"Auto-updating to v{update_info['latest']}...")

        # Write update flag for entrypoint to handle
        with open("/tmp/.barbossa_update_required", "w") as f:
            f.write(update_info["latest"])

        # Exit with special code - entrypoint will pull and restart
        sys.exit(42)  # 42 = update requested


# In entrypoint.sh:
# if [ $? -eq 42 ]; then
#   docker pull ghcr.io/barbossa-dev/agent:latest
#   exec docker restart barbossa
# fi
```

**Configuration in barbossa.json:**

```json
{
  "license_key": "barb_live_xxxx",
  "settings": {
    "updates": {
      "policy": "notify",
      "check_interval_hours": 24,
      "notify_email": "dev@example.com",
      "auto_update_critical": true
    }
  }
}
```

---

### Option C: Self-Updating Container (Advanced)

For seamless updates, the container can update itself:

```bash
#!/bin/bash
# entrypoint.sh with self-update capability

UPDATE_FLAG="/tmp/.barbossa_needs_update"
CURRENT_IMAGE="ghcr.io/barbossa-dev/agent:latest"

# Check for pending update from previous run
if [ -f "$UPDATE_FLAG" ]; then
    echo "Applying pending update..."
    rm "$UPDATE_FLAG"

    # Pull new image
    docker pull "$CURRENT_IMAGE"

    # Get current container ID
    CONTAINER_ID=$(cat /etc/hostname)

    # Restart with new image (requires docker socket mount)
    docker stop "$CONTAINER_ID"
    docker rm "$CONTAINER_ID"

    # Re-run with same config (handled by docker-compose)
    echo "Container will restart with new image"
    exit 0
fi

# Normal startup
exec /usr/local/bin/barbossa-orchestrator "$@"
```

**Docker Compose with socket mount:**

```yaml
services:
  barbossa:
    image: ghcr.io/barbossa-dev/agent:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # For self-update
      - ./barbossa.json:/app/barbossa.json:ro
      # ... other mounts
```

---

### Version API Endpoint

**Server-side (barbossa.dev):**

```typescript
// /api/v1/version/route.ts

import { NextRequest, NextResponse } from "next/server";

const LATEST_VERSION = "1.2.0";
const CHANGELOG = `
## v1.2.0
- Improved PR quality scoring
- Fixed memory leak in auditor
- Added Slack notifications

## v1.1.0
- Added Product Manager agent
- UI test requirements
`;

export async function GET(request: NextRequest) {
  const currentVersion = request.nextUrl.searchParams.get("current_version");
  const licenseKey = request.nextUrl.searchParams.get("license_key");

  // Validate license
  const license = await validateLicense(licenseKey);
  if (!license.valid) {
    return NextResponse.json({ error: "Invalid license" }, { status: 403 });
  }

  return NextResponse.json({
    latest_version: LATEST_VERSION,
    current_version: currentVersion,
    update_available: currentVersion !== LATEST_VERSION,
    changelog: CHANGELOG,
    critical: false,  // Set true for security updates
    download_url: `ghcr.io/barbossa-dev/agent:${LATEST_VERSION}`,
    published_at: "2024-12-20T00:00:00Z"
  });
}
```

---

### Release Process

```bash
# release.sh - Automated release pipeline

VERSION=$1  # e.g., "1.2.0"

echo "Building Barbossa v${VERSION}..."

# 1. Build production image with Nuitka
docker build \
  -f Dockerfile.production \
  --build-arg VERSION=${VERSION} \
  -t ghcr.io/barbossa-dev/agent:${VERSION} \
  -t ghcr.io/barbossa-dev/agent:latest \
  .

# 2. Push to registry
docker push ghcr.io/barbossa-dev/agent:${VERSION}
docker push ghcr.io/barbossa-dev/agent:latest

# 3. Update version API
curl -X POST https://barbossa.dev/api/internal/release \
  -H "Authorization: Bearer ${DEPLOY_TOKEN}" \
  -d "{\"version\": \"${VERSION}\", \"critical\": false}"

# 4. Notify users (optional)
curl -X POST https://barbossa.dev/api/internal/notify-update \
  -H "Authorization: Bearer ${DEPLOY_TOKEN}" \
  -d "{\"version\": \"${VERSION}\"}"

echo "Released v${VERSION}!"
```

---

## Recommended Implementation

### For V1 Launch:

1. **Code Protection:**
   - Use Nuitka to compile Python to native binaries
   - Keep agent prompts server-side (fetched on each run)
   - License validation required for every agent execution
   - Multi-stage Docker build (no source in production image)

2. **Updates:**
   - Document Watchtower setup in user guide
   - Built-in version check on container startup
   - Log message when update available
   - Email notification for critical updates

### For V2:

1. **Code Protection:**
   - Add PyArmor obfuscation layer
   - Anti-debugging checks
   - Binary integrity verification
   - Hardware-locked licenses (optional)

2. **Updates:**
   - Self-updating container capability
   - Gradual rollout (canary releases)
   - Rollback capability
   - Update scheduling (maintenance windows)

---

## Summary

| Layer | Purpose | Difficulty |
|-------|---------|------------|
| Nuitka compilation | Python → native binary | Medium |
| Server-side prompts | Core logic not in image | Medium |
| License validation | Gate all functionality | Easy |
| PyArmor obfuscation | Additional code protection | Easy |
| Watchtower updates | Auto-pull new images | Easy |
| Built-in updater | Notify/auto-update | Medium |
| Self-updating | Container restarts itself | Hard |

**Bottom line:** Compile to binary + server-side prompts + license validation gives strong protection. Watchtower provides seamless updates with minimal effort.
