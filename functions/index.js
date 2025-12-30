/**
 * Barbossa Firebase Cloud Functions
 *
 * Cloud infrastructure for Barbossa:
 * - Version compatibility checking (soft - warns, never blocks)
 * - State tracking for agent coordination
 * - Installation tracking (anonymous)
 * - Health monitoring
 *
 * Design principles:
 * - All endpoints are optional enhancements, never required
 * - Clients gracefully degrade if these are unavailable
 * - No blocking operations - everything is fire-and-forget from client side
 */

const functions = require('firebase-functions');
const admin = require('firebase-admin');
const cors = require('cors')({ origin: true });

admin.initializeApp();
const db = admin.firestore();

// ============================================================================
// VERSION CHECKING
// ============================================================================

const MINIMUM_VERSION = "1.0.0";
const LATEST_VERSION = "1.6.3";

/**
 * Check if client version is compatible
 */
exports.checkVersion = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    try {
      const { version } = req.query;

      if (!version) {
        return res.status(400).json({ error: 'Version required' });
      }

      const isCompatible = compareVersions(version, MINIMUM_VERSION) >= 0;
      const isLatest = version === LATEST_VERSION;

      res.json({
        compatible: isCompatible,
        latest: isLatest,
        minimumVersion: MINIMUM_VERSION,
        latestVersion: LATEST_VERSION,
        message: !isCompatible
          ? `Your version ${version} is no longer supported. Please upgrade to ${MINIMUM_VERSION} or later.`
          : !isLatest
            ? `A new version ${LATEST_VERSION} is available.`
            : 'You are running the latest version.'
      });
    } catch (error) {
      console.error('Error checking version:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
});

/**
 * Compare semantic versions
 */
function compareVersions(v1, v2) {
  const parts1 = v1.split('.').map(Number);
  const parts2 = v2.split('.').map(Number);

  for (let i = 0; i < 3; i++) {
    if (parts1[i] > parts2[i]) return 1;
    if (parts1[i] < parts2[i]) return -1;
  }
  return 0;
}

// ============================================================================
// UNIQUE USER TRACKING (Transparent)
// ============================================================================

/**
 * Register an installation for unique user counting
 *
 * This is transparent and privacy-respecting:
 * - Only stores an anonymous installation ID (hash)
 * - Only stores version number
 * - No personal information, no usage tracking
 * - Used only to count unique installations
 */
exports.registerInstallation = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      if (req.method !== 'POST') {
        return res.status(405).json({ error: 'POST required' });
      }

      const { installation_id, version } = req.body;

      if (!installation_id) {
        return res.status(400).json({ error: 'Installation ID required' });
      }

      // Upsert installation - only store ID, version, and last seen
      await db.collection('installations').doc(installation_id).set({
        version: version || 'unknown',
        last_seen: admin.firestore.FieldValue.serverTimestamp()
      }, { merge: true });

      res.json({ success: true });
    } catch (error) {
      console.error('Error registering installation:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
});

// ============================================================================
// CONFIGURATION
// ============================================================================

/**
 * Get default configuration template
 */
exports.getDefaultConfig = functions.https.onRequest((req, res) => {
  cors(req, res, () => {
    res.json({
      version: LATEST_VERSION,
      config: {
        owner: "your-github-username",
        repositories: [
          {
            name: "my-app",
            url: "git@github.com:your-github-username/my-app.git"
          }
        ],
        settings: {
          schedule: {
            engineer: "every_2_hours",
            tech_lead: "every_2_hours",
            discovery: "3x_daily",
            product_manager: "2x_daily"
          },
          tech_lead: {
            auto_merge: true,
            min_lines_for_tests: 50,
            stale_days: 7
          },
          discovery: {
            max_backlog_issues: 10
          },
          product_manager: {
            max_feature_issues: 5
          }
        }
      }
    });
  });
});

// ============================================================================
// HEALTH CHECK
// ============================================================================

/**
 * Simple health check endpoint
 */
exports.health = functions.https.onRequest((req, res) => {
  res.json({
    status: 'healthy',
    version: LATEST_VERSION,
    timestamp: new Date().toISOString()
  });
});

// ============================================================================
// STATE TRACKING (for agent coordination and analytics)
// ============================================================================

/**
 * Track when an agent run starts
 *
 * This enables:
 * - Visibility into active runs across installations
 * - Future coordination features (e.g., rate limiting, prioritization)
 * - Usage patterns for improvement
 *
 * Privacy: Only stores anonymous installation_id, no user/repo info
 */
exports.trackRunStart = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      if (req.method !== 'POST') {
        return res.status(405).json({ error: 'POST required' });
      }

      const { installation_id, agent, session_id, repo_count, version, started_at } = req.body;

      if (!installation_id || !agent || !session_id) {
        return res.status(400).json({ error: 'Missing required fields' });
      }

      // Store run state
      await db.collection('agent_runs').doc(session_id).set({
        installation_id,
        agent,
        repo_count: repo_count || 1,
        version: version || 'unknown',
        status: 'running',
        started_at: started_at || new Date().toISOString(),
        updated_at: admin.firestore.FieldValue.serverTimestamp()
      });

      // Update installation last seen
      await db.collection('installations').doc(installation_id).set({
        version: version || 'unknown',
        last_agent: agent,
        last_seen: admin.firestore.FieldValue.serverTimestamp()
      }, { merge: true });

      res.json({ success: true });
    } catch (error) {
      console.error('Error tracking run start:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
});

/**
 * Track when an agent run ends
 */
exports.trackRunEnd = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      if (req.method !== 'POST') {
        return res.status(405).json({ error: 'POST required' });
      }

      const { installation_id, agent, session_id, success, pr_created, version, ended_at } = req.body;

      if (!session_id) {
        return res.status(400).json({ error: 'session_id required' });
      }

      // Update run state
      await db.collection('agent_runs').doc(session_id).set({
        status: success ? 'completed' : 'failed',
        success: !!success,
        pr_created: !!pr_created,
        ended_at: ended_at || new Date().toISOString(),
        updated_at: admin.firestore.FieldValue.serverTimestamp()
      }, { merge: true });

      // Update aggregate stats (anonymous)
      const statsRef = db.collection('stats').doc('global');
      await statsRef.set({
        total_runs: admin.firestore.FieldValue.increment(1),
        successful_runs: admin.firestore.FieldValue.increment(success ? 1 : 0),
        prs_created: admin.firestore.FieldValue.increment(pr_created ? 1 : 0),
        [`runs_by_agent.${agent}`]: admin.firestore.FieldValue.increment(1),
        last_updated: admin.firestore.FieldValue.serverTimestamp()
      }, { merge: true });

      res.json({ success: true });
    } catch (error) {
      console.error('Error tracking run end:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
});

/**
 * Heartbeat endpoint for long-running processes
 */
exports.heartbeat = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      if (req.method !== 'POST') {
        return res.status(405).json({ error: 'POST required' });
      }

      const { installation_id, version } = req.body;

      if (!installation_id) {
        return res.status(400).json({ error: 'installation_id required' });
      }

      await db.collection('installations').doc(installation_id).set({
        version: version || 'unknown',
        last_heartbeat: admin.firestore.FieldValue.serverTimestamp()
      }, { merge: true });

      res.json({ success: true });
    } catch (error) {
      console.error('Error processing heartbeat:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
});

/**
 * Get aggregate stats (public, anonymous)
 *
 * Returns things like:
 * - Total PRs created by all Barbossa installations
 * - Success rates
 * - Most used agents
 *
 * This enables community features and social proof.
 */
exports.getStats = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      const statsDoc = await db.collection('stats').doc('global').get();

      if (!statsDoc.exists) {
        return res.json({
          total_runs: 0,
          successful_runs: 0,
          prs_created: 0,
          success_rate: 0
        });
      }

      const data = statsDoc.data();
      const successRate = data.total_runs > 0
        ? Math.round((data.successful_runs / data.total_runs) * 100)
        : 0;

      res.json({
        total_runs: data.total_runs || 0,
        successful_runs: data.successful_runs || 0,
        prs_created: data.prs_created || 0,
        success_rate: successRate,
        runs_by_agent: data.runs_by_agent || {}
      });
    } catch (error) {
      console.error('Error getting stats:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
});

/**
 * Get active installations count (for social proof)
 */
exports.getActiveInstallations = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      // Count installations active in last 24 hours
      const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);

      const snapshot = await db.collection('installations')
        .where('last_seen', '>', oneDayAgo)
        .count()
        .get();

      res.json({
        active_24h: snapshot.data().count,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Error getting active installations:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
});
