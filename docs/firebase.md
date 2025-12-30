# Firebase & Analytics

Barbossa uses a hybrid telemetry architecture combining Google Analytics 4 and Firebase Cloud Functions to provide optional enhancements without ever blocking or requiring external services.

---

## Overview

Barbossa's telemetry is built on two complementary systems:

**Google Analytics 4 (GA4)**
- Simple event tracking (installs, agent runs)
- Industry-standard analytics platform
- Zero infrastructure maintenance

**Firebase Cloud Functions**
- Version compatibility checking
- Agent run coordination and state tracking
- Aggregate statistics for community insights
- Firestore database for installation tracking

**Key principle:** All telemetry is optional and gracefully degrades. Barbossa works perfectly without connectivity to either service.

---

## Current Status (v1.6.3)

- **Latest Version:** v1.6.3
- **Minimum Supported:** v1.0.0
- **Cloud Functions:** Deployed to `barbossa-dev` Firebase project
- **GA4 Measurement ID:** `G-XNTRF7ZYQ5`
- **Privacy:** Fully transparent, no personal data collected
- **Platform Support:** Linux (x86_64/amd64), macOS (Intel + Apple Silicon)

---

## What Gets Collected (Privacy-First)

### ✅ What IS Collected

**Via Google Analytics 4:**
- **Anonymous client ID**: SHA256 hash of hostname + home directory (not reversible)
- **Event types**: Installation events, agent run events
- **Agent types**: Which agents ran (engineer, tech-lead, etc.)
- **Engagement metrics**: Minimal engagement time tracking

**Via Firebase Cloud Functions:**
- **Anonymous installation ID**: Same SHA256 hash as GA4
- **Version number**: e.g., "1.6.3"
- **Agent run metadata**: Session IDs, start/end timestamps, success/failure
- **Repository counts**: How many repos managed (number only)
- **Success rates**: Whether runs completed successfully
- **PR creation**: Whether PR was created (boolean only)

### ❌ What is NOT Collected

- Repository names, URLs, or any identifying information
- Code content, diffs, or file contents
- GitHub usernames or organization names
- File paths, directory structures, or project names
- PR titles, descriptions, or commit messages
- Issue content or labels
- Any personally identifiable information
- Your configuration settings or secrets
- Network requests or external API calls
- Command-line arguments or environment variables

---

## Hybrid Architecture

### Google Analytics 4 (Event Tracking)

**Purpose:** Simple, fire-and-forget event tracking for basic usage metrics.

**Events Tracked:**
1. **Install Event** - When `register_installation()` is called
2. **Agent Run Event** - When any agent executes

**Implementation:**
```python
# Uses GA4 Measurement Protocol
GA4_CONFIG = {
    "measurement_id": "G-XNTRF7ZYQ5",
    "api_secret": os.environ.get("GA4_API_SECRET", ""),
    "endpoint": "https://www.google-analytics.com/mp/collect"
}
```

**Why GA4:**
- Industry standard analytics platform
- No infrastructure to maintain
- Simple HTTP API
- Free tier sufficient for all needs
- Built-in anomaly detection and reporting

### Firebase Cloud Functions (Coordination & Stats)

**Purpose:** Advanced features like version checking, run coordination, and community statistics.

**Endpoints:**

| Endpoint | Purpose | Method | Privacy Level |
|----------|---------|--------|---------------|
| `checkVersion` | Version compatibility check | GET | No data stored |
| `registerInstallation` | Track active installations | POST | Anonymous ID only |
| `trackRunStart` | Record agent run start | POST | Anonymous ID + metadata |
| `trackRunEnd` | Record agent run completion | POST | Anonymous success/fail |
| `heartbeat` | Keep installation active count accurate | POST | Anonymous ID + timestamp |
| `getStats` | Public aggregate statistics | GET | Fully aggregated |
| `getActiveInstallations` | Count of active users (24h) | GET | Count only |
| `health` | Health check | GET | No data collected |

**Base URL:**
```
https://us-central1-barbossa-450802.cloudfunctions.net
```

**Why Cloud Functions:**
- Soft version checking (warns of updates)
- Enables future coordination features
- Community statistics for social proof
- Serverless architecture (scales automatically)
- 5-second timeout ensures never blocks execution

---

## How Telemetry Works

### On Agent Startup

```python
# 1. Initialize Firebase client
from barbossa.agents.firebase import get_client, check_version

# 2. Check for updates (soft - never blocks)
update_msg = check_version()
if update_msg:
    logger.warning(f"UPDATE AVAILABLE: {update_msg}")

# 3. Register installation (GA4)
firebase.register_installation()
```

### During Agent Execution

```python
# 1. Track run start (Cloud Functions, fire-and-forget)
track_run_start(agent="engineer", session_id="eng-20251230-123456", repo_count=3)

# 2. Send heartbeat periodically (Cloud Functions, fire-and-forget)
heartbeat()

# 3. Track agent run (GA4, fire-and-forget)
track_agent_run(agent="engineer")

# 4. Track run end (Cloud Functions, fire-and-forget)
track_run_end(agent="engineer", session_id="eng-20251230-123456", success=True, pr_created=True)
```

**Key Design Principles:**
- All calls have 5-second timeout
- All calls are non-blocking (fire-and-forget or background threads)
- Errors are logged but never crash the system
- Graceful degradation if Firebase/GA4 is unavailable

---

## Data Retention

**Google Analytics 4:**
- Event data: 2 months (GA4 free tier standard)
- Aggregate reports: Indefinitely (anonymous)

**Firebase Firestore:**
- **Agent runs**: 30 days (auto-pruned)
- **Installations**: Active installations only (pruned after 7 days of inactivity)
- **Global stats**: Aggregated permanently (fully anonymous)

---

## Opting Out

### Complete Opt-Out

Disable all telemetry (GA4 + Cloud Functions) in `config/repositories.json`:

```json
{
  "settings": {
    "telemetry": false
  }
}
```

Or via environment variable:

```bash
export BARBOSSA_ANALYTICS_OPT_OUT=true
```

**When opted out:**
- ✅ No data sent to GA4
- ✅ No data sent to Firebase Cloud Functions
- ✅ No network calls to external services
- ✅ No version checking (you won't be notified of updates)
- ✅ System works exactly the same locally

### Verify Opt-Out

```bash
docker exec barbossa python3 -m barbossa.agents.firebase
```

Output will show: `Telemetry enabled: False`

---

## Version Checking

Firebase Cloud Functions track the latest Barbossa version and warn you if updates are available.

**How it works:**
1. On startup, Barbossa calls `checkVersion` Cloud Function
2. Function compares your version to `LATEST_VERSION` (currently 1.6.3)
3. If newer version exists, you see: `UPDATE AVAILABLE: v1.6.3 is available`
4. This is a **soft warning** - never blocks execution
5. If Firebase is unavailable, version check is silently skipped

**Response Format:**
```json
{
  "compatible": true,
  "latest": false,
  "minimumVersion": "1.0.0",
  "latestVersion": "1.6.3",
  "message": "A new version 1.6.3 is available."
}
```

**Benefits:**
- Stay informed about bug fixes and new features
- Know when you're running an outdated version
- Optional - disabled if telemetry is off

---

## Firestore Schema

### Collections

**installations**
```javascript
{
  installation_id: "sha256_hash",      // Anonymous ID
  version: "1.6.3",                    // Client version
  last_seen: Timestamp,                 // Last activity
  last_agent: "engineer",               // Last agent run
  last_heartbeat: Timestamp            // Last heartbeat
}
```

**agent_runs**
```javascript
{
  session_id: "eng-20251230-123456",   // Unique session ID
  installation_id: "sha256_hash",       // Anonymous installation
  agent: "engineer",                    // Agent type
  repo_count: 3,                        // Number of repos (count only)
  version: "1.6.3",                     // Client version
  status: "completed",                  // running | completed | failed
  success: true,                        // Boolean success
  pr_created: true,                     // Boolean PR creation
  started_at: "2025-12-30T12:34:56Z",  // ISO timestamp
  ended_at: "2025-12-30T12:38:23Z",    // ISO timestamp
  updated_at: Timestamp                 // Firestore server timestamp
}
```

**stats** (global aggregates document)
```javascript
{
  total_runs: 15234,                    // Total agent runs across all installations
  successful_runs: 14102,               // Successful completions
  prs_created: 3421,                    // Total PRs created
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

## Aggregate Stats (Public)

Firebase collects anonymous aggregate stats that benefit the community.

**Access stats API:**
```bash
curl https://us-central1-barbossa-450802.cloudfunctions.net/getStats
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
- Community insights: See how Barbossa is being used
- Social proof: Show active installations for new users
- Feature prioritization: Identify most-used agents
- System health: Track overall success rates

**Active installations:**
```bash
curl https://us-central1-barbossa-450802.cloudfunctions.net/getActiveInstallations
```

Returns count of installations active in last 24 hours.

---

## Future Features (Planned)

Firebase state tracking enables future coordination features:

### Agent Coordination
- **Priority queuing**: High-value work gets scheduled first across installations
- **Load balancing**: Distribute work across time zones to reduce API load
- **Rate limiting**: Prevent API abuse and quota exhaustion
- **Conflict detection**: Avoid simultaneous work on same issues

### Community Features
- **Shared knowledge base**: Learn from other installations' successful patterns
- **Best practices**: Discover what works well across the community
- **Benchmarking**: Compare your results to community averages
- **Success patterns**: Identify which agent combinations work best

### Enhanced Monitoring
- **Real-time dashboards**: See your agent activity at barbossa.dev
- **Performance tracking**: Identify bottlenecks in your setup
- **Anomaly detection**: Alert on unusual patterns or failures
- **Health scores**: Compare your installation health to community baseline

**Timeline:** TBD based on community feedback and demand

---

## Technical Implementation

### Client Side (`src/barbossa/agents/firebase.py`)

**Constants:**
```python
CLIENT_VERSION = "1.6.3"
FIREBASE_TIMEOUT = 5  # seconds - short timeout, never blocks
FIREBASE_BASE_URL = "https://us-central1-barbossa-450802.cloudfunctions.net"
GA4_CONFIG = {
    "measurement_id": "G-XNTRF7ZYQ5",
    "api_secret": os.environ.get("GA4_API_SECRET", ""),
    "endpoint": "https://www.google-analytics.com/mp/collect"
}
```

**Key design principles:**
- All Firebase calls have 5-second timeout
- All GA4 calls have 5-second timeout
- All calls are fire-and-forget (non-blocking via threads)
- Errors are logged but never crash the system
- Graceful degradation if Firebase/GA4 is unavailable
- Telemetry can be disabled via config or environment variable

### Server Side (`functions/index.js`)

**Deployment:**
- Firebase Project: `barbossa-dev`
- Cloud Functions Region: `us-central1`
- Hosting: `barbossa.dev` (docs site)
- Firestore: Multi-region for high availability
- Auto-scales to handle load
- Global CDN for low latency
- 99.95% uptime SLA (Google Cloud)

**Version Configuration:**
```javascript
const MINIMUM_VERSION = "1.0.0";
const LATEST_VERSION = "1.6.3";
```

**CORS Enabled:**
All endpoints support CORS for future web dashboard at barbossa.dev.

---

## Deploying Functions (Maintainers Only)

If you're contributing to Barbossa's Firebase infrastructure:

### Prerequisites
```bash
npm install -g firebase-tools
firebase login
```

### Deploy Cloud Functions
```bash
cd functions
npm install
firebase deploy --only functions
```

### Deploy Hosting (Docs Site)
```bash
firebase deploy --only hosting
```

### Update Version
When releasing a new version:

1. **Update Cloud Functions** (`functions/index.js`):
```javascript
const LATEST_VERSION = "1.6.3";  // Update this
```

2. **Update Python Client** (`src/barbossa/agents/firebase.py`):
```python
CLIENT_VERSION = "1.6.3"  # Update this
```

3. **Redeploy:**
```bash
firebase deploy --only functions
```

---

## Troubleshooting

### Firebase Connection Issues

**Symptom:** Logs show `Failed to check version` or `Failed to track run`

**Causes:**
- Network connectivity issues
- Firebase API temporarily unavailable
- Firewall blocking Firebase/GA4 domains
- Corporate proxy interfering

**Resolution:**
- ✅ **No action needed** - Barbossa continues working fine
- Errors are logged but don't affect functionality
- Check network/firewall settings if you want version updates
- Whitelist domains: `cloudfunctions.net`, `google-analytics.com`, `firebaseio.com`
- Or disable telemetry to stop seeing these logs

### Version Check Failed

**Symptom:** No update notifications even when new version exists

**Causes:**
- Telemetry disabled (`telemetry: false`)
- Firebase timeout (5 seconds)
- Network issues or corporate firewall

**Resolution:**
- Verify `telemetry: true` in `config/repositories.json`
- Check network connectivity to `cloudfunctions.net`
- Manually check [GitHub releases](https://github.com/ADWilkinson/barbossa-dev/releases) for updates
- Check [barbossa.dev](https://barbossa.dev) for latest version

### GA4 Events Not Appearing

**Symptom:** GA4 dashboard shows no events

**Causes:**
- GA4 API secret not configured (optional, only needed for maintainers)
- GA4 has 24-48 hour processing delay
- Telemetry disabled

**Resolution:**
- GA4 secret is optional - events may not appear in GA4 dashboard but system works fine
- Wait 24-48 hours for GA4 processing
- This doesn't affect Barbossa functionality

### Privacy Concerns

**Symptom:** Worried about what telemetry collects

**Resolution:**
- Review "What Gets Collected" section above
- Inspect `src/barbossa/agents/firebase.py` source code
- Inspect `functions/index.js` source code (all endpoints)
- All code is open source - verify yourself
- Opt out completely: `telemetry: false`
- Use network monitoring to inspect actual traffic

---

## FAQ

### Is Firebase required?

**No.** Barbossa works perfectly without Firebase or GA4. All telemetry is optional.

### What happens if Firebase is down?

Barbossa continues working normally. All calls have 5-second timeouts and fail gracefully.

### Can I self-host the Firebase functions?

Yes, but requires your own Firebase project:
1. Clone the repo
2. `firebase init` with your project
3. Update `FIREBASE_BASE_URL` in `.env` to point to your functions
4. Deploy: `firebase deploy`

### Why hybrid GA4 + Cloud Functions?

- **GA4**: Simple events, no infrastructure, industry standard
- **Cloud Functions**: Advanced features like version checking, coordination, custom logic
- **Together**: Best of both worlds - simplicity + power

### How do I verify what data is sent?

1. Review source code: `src/barbossa/agents/firebase.py`
2. Enable verbose logging: `docker logs -f barbossa`
3. Use network proxy: Inspect HTTP requests to `cloudfunctions.net` and `google-analytics.com`
4. All code is open source - audit yourself

### Can I see my own installation's data?

No. Data is anonymous by design. Even maintainers cannot link an `installation_id` hash back to a specific user, repository, or machine.

### Does telemetry slow down Barbossa?

No. All telemetry calls are:
- Fire-and-forget (non-blocking background threads)
- 5-second timeout maximum
- Errors are swallowed
- Zero impact on agent execution

---

## Contact & Support

- **Website:** [barbossa.dev](https://barbossa.dev)
- **Issues:** [GitHub Issues](https://github.com/ADWilkinson/barbossa-dev/issues)
- **Privacy Questions:** Open issue with "Privacy" label
- **Firebase Issues:** Open issue with "Firebase" label

---

**Last Updated:** 2025-12-30 (v1.6.3)
