# Firebase Integration

Barbossa uses Firebase Cloud Functions for optional cloud infrastructure that enhances the system without being required.

---

## Overview

Firebase provides these optional features:
- **Version compatibility checking** - warns about updates (never blocks)
- **Anonymous telemetry** - aggregate usage stats for improvements
- **State tracking** - agent run coordination (future features)
- **Installation tracking** - count active Barbossa installations

**Key principle:** All Firebase endpoints are optional enhancements. Barbossa works perfectly fine without them - clients gracefully degrade if Firebase is unavailable.

---

## Current Status (v1.5.2)

- **Latest Version:** v1.5.2
- **Minimum Supported:** v1.0.0
- **Cloud Functions:** Deployed and operational
- **Privacy:** Fully transparent, no personal data collected
- **Platform Support:** Linux (x86_64/amd64), macOS (Intel + Apple Silicon)

---

## What Firebase Collects (Privacy-First)

### ✅ What IS Collected
- **Anonymous installation ID**: SHA256 hash (not reversible to any identifying info)
- **Version number**: e.g., "1.3.0"
- **Agent run counts**: How many times each agent has run
- **Success rates**: Whether runs completed successfully
- **Timestamps**: When installations were last active

### ❌ What is NOT Collected
- Repository names or URLs
- Code content or diffs
- GitHub usernames
- File paths or names
- PR titles or descriptions
- Any personally identifiable information
- Your configuration settings

---

## Firebase Cloud Functions

### Endpoints

| Endpoint | Purpose | Privacy Level |
|----------|---------|---------------|
| `checkVersion` | Version compatibility check | No data stored |
| `registerInstallation` | Count active installations | Anonymous ID only |
| `trackRunStart` | Track agent run starts | Anonymous ID + agent name |
| `trackRunEnd` | Track agent run completion | Anonymous success/fail only |
| `heartbeat` | Keep installation active count | Anonymous ID only |
| `getStats` | Public aggregate stats | Fully aggregated, no individual data |
| `getActiveInstallations` | Count of active users (24h) | Count only |
| `health` | Health check | No data collected |

### Data Retention

- **Agent runs**: 30 days
- **Installations**: Active installations only (pruned after 7 days of inactivity)
- **Stats**: Aggregated permanently (anonymous)

---

## Opting Out

### Complete Opt-Out

Disable all Firebase/telemetry in `config/repositories.json`:

```json
{
  "settings": {
    "telemetry": false
  }
}
```

Or via environment variable:

```bash
BARBOSSA_ANALYTICS_OPT_OUT=true
```

**When opted out:**
- ✅ No data sent to Firebase
- ✅ No network calls to cloud functions
- ✅ No version checking (you won't be notified of updates)
- ✅ System works exactly the same locally

---

## Version Checking

Firebase tracks the latest Barbossa version and warns you if updates are available.

**How it works:**
1. On startup, Barbossa checks Firebase for latest version
2. If a newer version exists, you see a log message: `UPDATE AVAILABLE: v1.5.2 is available`
3. This is a **soft warning** - never blocks execution
4. If Firebase is unavailable, version check is silently skipped

**Benefits:**
- Stay informed about bug fixes and new features
- Optional - if disabled, you won't get update notifications

---

## Technical Implementation

### Client Side (`barbossa_firebase.py`)

The Python client handles all Firebase interactions:

```python
CLIENT_VERSION = "1.5.2"
FIREBASE_TIMEOUT = 5  # seconds - short timeout, never blocks
```

**Key design principles:**
- All Firebase calls have 5-second timeout
- All calls are fire-and-forget (non-blocking)
- Errors are logged but never crash the system
- Graceful degradation if Firebase is unavailable

### Cloud Functions (`functions/index.js`)

Node.js functions deployed to Firebase Cloud Functions:

```javascript
const MINIMUM_VERSION = "1.0.0";
const LATEST_VERSION = "1.5.2";
```

**Deployment:**
- Hosted on Google Cloud (Firebase)
- Auto-scales to handle load
- Global CDN for low latency
- 99.95% uptime SLA

---

## Aggregate Stats (Public)

Firebase collects anonymous aggregate stats that benefit the community:

**What you can see:**
- Total PRs created by all Barbossa installations
- Overall success rates
- Most-used agents
- Active installations count (last 24h)

**Access stats:**
```bash
curl https://us-central1-barbossa-dev.cloudfunctions.net/getStats
```

Example response:
```json
{
  "total_runs": 15234,
  "successful_runs": 14102,
  "prs_created": 3421,
  "success_rate": 92,
  "runs_by_agent": {
    "engineer": 5234,
    "tech_lead": 5123,
    "discovery": 3201,
    "product": 1234,
    "auditor": 442
  }
}
```

**Use cases:**
- Community insights
- Social proof for new users
- Identify popular features
- Track system health across all installations

---

## Future Features (Planned)

Firebase state tracking enables future coordination features:

### Agent Coordination
- **Priority queuing**: High-value work gets scheduled first
- **Load balancing**: Distribute work across time zones
- **Rate limiting**: Prevent API abuse across installations

### Community Features
- **Shared knowledge base**: Learn from other installations
- **Best practices**: Discover what works well
- **Benchmarking**: Compare your results to community averages

### Enhanced Monitoring
- **Real-time dashboards**: See your agent activity
- **Performance tracking**: Identify bottlenecks
- **Anomaly detection**: Alert on unusual patterns

**Timeline:** TBD based on community feedback

---

## Firestore Schema

### Collections

**installations**
```javascript
{
  installation_id: "sha256_hash",
  version: "1.5.2",
  last_seen: Timestamp,
  last_agent: "engineer",
  last_heartbeat: Timestamp
}
```

**agent_runs**
```javascript
{
  session_id: "eng-20251226-123456-abc123",
  installation_id: "sha256_hash",
  agent: "engineer",
  repo_count: 3,
  version: "1.5.2",
  status: "completed",
  success: true,
  pr_created: true,
  started_at: "2025-12-26T12:34:56Z",
  ended_at: "2025-12-26T12:38:23Z"
}
```

**stats** (global document)
```javascript
{
  total_runs: 15234,
  successful_runs: 14102,
  prs_created: 3421,
  runs_by_agent: {
    engineer: 5234,
    tech_lead: 5123,
    discovery: 3201,
    product: 1234,
    auditor: 442
  },
  last_updated: Timestamp
}
```

---

## Deploying Functions (Maintainers Only)

If you're contributing to Barbossa's Firebase functions:

### Prerequisites
```bash
npm install -g firebase-tools
firebase login
```

### Deploy
```bash
cd functions
npm install
firebase deploy --only functions
```

### Update Version
When releasing a new version, update `functions/index.js`:

```javascript
const LATEST_VERSION = "1.5.2";  // Update this
```

Then redeploy functions.

---

## Troubleshooting

### Firebase Connection Issues

**Symptom:** Logs show `Failed to check version` or `Failed to track run`

**Causes:**
- Network connectivity issues
- Firebase API temporarily unavailable
- Firewall blocking Firebase domains

**Resolution:**
- ✅ **No action needed** - Barbossa continues working fine
- Errors are logged but don't affect functionality
- Optionally: Check network/firewall settings
- Optionally: Disable telemetry to stop seeing these logs

### Version Check Failed

**Symptom:** No update notifications even when new version exists

**Causes:**
- Telemetry disabled
- Firebase timeout (5 seconds)
- Network issues

**Resolution:**
- Check `telemetry: true` in config
- Check network connectivity
- Manually check GitHub releases for updates

### Privacy Concerns

**Symptom:** Worried about what Firebase collects

**Resolution:**
- Review this document's "What Firebase Collects" section
- Inspect `barbossa_firebase.py` source code
- Inspect `functions/index.js` source code
- Opt out completely: `telemetry: false`

---

## FAQ

### Is Firebase required?

**No.** Barbossa works perfectly without Firebase. All cloud functions are optional enhancements.

### What happens if Firebase is down?

Barbossa continues working normally. All Firebase calls have 5-second timeouts and fail gracefully.

### Can I self-host the Firebase functions?

Yes, but it requires setting up your own Firebase project. The functions code is open source in `functions/index.js`.

### Why not use a different analytics provider?

Firebase provides:
- Free tier (sufficient for Barbossa's needs)
- Excellent uptime and global CDN
- Simple deployment (no server management)
- Built-in Firestore for state tracking

### How do I verify what data is sent?

1. Review `barbossa_firebase.py` source code
2. Enable verbose logging to see all network calls
3. Use a network proxy to inspect traffic
4. All code is open source - verify yourself

### Can I see my own installation's data?

No. Data is anonymous by design. Even we (maintainers) cannot link an installation_id hash back to a specific user or repository.

---

## Contact & Support

- **Issues:** https://github.com/ADWilkinson/barbossa-dev/issues
- **Privacy Questions:** Open an issue with "Privacy" label
- **Firebase Issues:** Open an issue with "Firebase" label

---

**Last Updated:** 2025-12-30 (v1.5.2)
