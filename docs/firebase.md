# Firebase & Analytics

Optional telemetry for version checking and anonymous usage statistics.

---

## Overview

Barbossa uses Google Analytics 4 and Firebase Cloud Functions for:
- Version update notifications
- Anonymous usage statistics
- Community aggregate stats

**All telemetry is optional.** Barbossa works perfectly without it.

---

## What's Collected

**Collected (anonymous):**
- SHA256 hash ID (not reversible to you)
- Version number
- Agent run counts and success rates
- Repository count (number only)

**NOT collected:**
- Repository names, URLs, code, or any identifying information
- GitHub usernames, PR titles, issue content
- Your configuration or secrets

---

## Opting Out

In `config/repositories.json`:

```json
{
  "settings": {
    "telemetry": false
  }
}
```

Or via environment:

```bash
export BARBOSSA_ANALYTICS_OPT_OUT=true
```

---

## Version Checking

On startup, Barbossa checks for updates via Firebase. If a newer version exists, you'll see a warning in logs. This never blocks execution.

Disable version checking by opting out of telemetry.

---

## FAQ

**Is Firebase required?**
No. Barbossa works fine without any external connectivity.

**Does telemetry slow things down?**
No. All calls are fire-and-forget with 5-second timeouts.

**Can I verify what's sent?**
Yes. Review `src/barbossa/agents/firebase.py` - it's open source.

---

## For Maintainers

Update version when releasing:

```bash
# In functions/index.js
const LATEST_VERSION = "1.7.2";

# In src/barbossa/agents/firebase.py
CLIENT_VERSION = "1.7.2"

# Deploy
firebase deploy --only functions
```
