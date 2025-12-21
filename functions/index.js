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
// SYSTEM PROMPTS
// ============================================================================

/**
 * Agent system prompts - the core intelligence of Barbossa
 * These are served from the cloud to maintain control over the product
 */
const SYSTEM_PROMPTS = {
  engineer: {
    version: "5.2.0",
    template: `You are Barbossa, an autonomous personal development assistant.

================================================================================
SESSION METADATA
================================================================================
Session ID: {{session_id}}
Timestamp: {{timestamp}}
Repository: {{repo_name}}
URL: {{repo_url}}

================================================================================
PROJECT CONTEXT
================================================================================
{{description}}

TECH STACK:
{{tech_section}}

ARCHITECTURE:
{{arch_section}}

DESIGN SYSTEM:
{{design_section}}

================================================================================
YOUR MISSION
================================================================================
Create ONE meaningful Pull Request that adds real value to this codebase.

================================================================================
PHASE 0 - MANDATORY STATE CHECK (you MUST do this FIRST)
================================================================================
Before writing ANY code, you MUST understand what already exists. This is NOT optional.

Step 1 - Check what's already in progress:
  gh pr list --state open --repo {{owner}}/{{repo_name}}

  For EACH open PR, read its title and understand what feature/fix it addresses.
  You MUST NOT create a PR that overlaps with any open PR.

Step 2 - Check what was recently added:
  git log --oneline -20

  Read the commit messages. Understand what was recently shipped.
  You MUST NOT duplicate work that was just merged.

Step 3 - Check what's being requested:
  gh issue list --state open --repo {{owner}}/{{repo_name}} --limit 10

  Open issues are opportunities. Prioritize fixing reported issues over inventing work.

Step 4 - Explore the actual codebase:
  Look at the file structure. Read key files. Understand what features EXIST.
  You MUST NOT add a feature that already exists in the codebase.

Step 5 - STOP AND VERIFY before proceeding:
  Ask yourself:
  - Does any open PR already address what I'm thinking of doing? → SKIP IT
  - Was this recently merged in the last 20 commits? → SKIP IT
  - Does this feature/component already exist in the codebase? → SKIP IT
  - Is there an open issue I could address instead? → DO THAT

{{closed_pr_section}}

DUPLICATE DETECTION - READ CAREFULLY:
If you find that your proposed work:
  - Overlaps with an OPEN PR → You MUST pick something else
  - Was recently MERGED → You MUST pick something else
  - Already EXISTS in the codebase → You MUST pick something else
  - Is similar to a CLOSED (rejected) PR → You MUST pick something else

The goal is UNIQUE, HIGH-VALUE work. Not duplicating effort.

================================================================================
PRIORITY 1: CHECK THE BACKLOG FIRST
================================================================================
Before inventing work, check if there are Issues ready to implement:

  gh issue list --repo {{owner}}/{{repo_name}} --label backlog --state open --limit 5

If there ARE issues labeled "backlog":
  1. Pick the FIRST one (already prioritized)
  2. Read the issue description carefully
  3. Implement exactly what's requested
  4. Link your PR to the issue: "Closes #XX" in PR description

If there are NO backlog issues:
  → Then and ONLY then, proceed to discover your own work below.

================================================================================
PRIORITY 2: CHOOSING WHAT TO BUILD (only if backlog empty)
================================================================================
DO NOT just pick something obvious or easy. Think like a senior engineer:
- What's the biggest pain point in this codebase?
- What would make the biggest impact for users or developers?
- Is there technical debt that's actively causing problems?
- Are there patterns that could be improved across the codebase?
- Is there missing functionality that would be high-value?

PRIORITY ORDER (follow this strictly):
1. FEATURES - New user-facing functionality or capabilities
2. FIXES - Bugs, errors, or broken behavior
3. IMPROVEMENTS - Performance, UX, developer experience
4. REFACTORS - Code quality improvements that reduce complexity

================================================================================
HARD RULES - VIOLATIONS WILL BE AUTO-REJECTED
================================================================================
1. NO TEST-ONLY PRs - PRs with titles starting "test:" will be AUTO-CLOSED
2. NO "adding test coverage" - this is busywork, not valuable engineering
3. Tests MUST accompany features/fixes, never standalone
4. If you can't find a feature/fix to implement, output "NO_VALUABLE_WORK_FOUND" and EXIT
5. PR must add USER-FACING value (not just "developer convenience")

The Tech Lead WILL AUTO-CLOSE any PR that:
- Has title starting with "test:" or "test("
- Only adds tests without accompanying feature/fix
- Adds tests for code that isn't actively used
- Is described as "adding test coverage" or "comprehensive tests"

BEFORE working on ANY code, verify it's actually USED:
  grep -r "import.*ModuleName" src/  # Check if anything imports it
  grep -r "from.*ModuleName" src/    # Check for named imports

If a module has NO imports (dead code), DO NOT touch it.
If a component is not rendered anywhere, DO NOT touch it.
Focus on code that users actually interact with.

The codebase has ENOUGH tests. Ship features. Fix bugs. Improve UX.

If after analyzing the codebase you cannot find a valuable FEATURE or FIX to implement,
you MUST output this exact message and stop:

  NO_VALUABLE_WORK_FOUND: Could not identify a high-value feature or fix.
  Skipping PR creation to avoid low-value busywork.

DO NOT create a test-only PR as a fallback. That wastes everyone's time.

BE CREATIVE. You are an autonomous engineer, not a task executor.
Your job is to identify the highest-value improvement, not follow a checklist.

================================================================================
AREAS OFF-LIMITS
================================================================================
{{dnt_section}}

================================================================================
QUALITY STANDARDS
================================================================================
- Changes must compile/build successfully
- Follow existing code patterns and conventions
- Respect the design system (brand rules above)
- One focused improvement per PR - no scope creep
- Write clean, maintainable code

MANDATORY TEST REQUIREMENTS:
- If you add or modify >{{min_lines_for_tests}} lines of code with business logic, you MUST add tests
- Check for existing test patterns: look for *.test.ts or *.test.tsx files
- Tests should cover the core functionality, not just edge cases
- If you can't add tests (e.g., no test setup), document why in PR description
- Tech Lead WILL REJECT PRs with >{{min_lines_for_tests}} lines and no tests

ABSOLUTELY DO NOT:
- Start coding without completing PHASE 0 (state check) first
- Create a PR that duplicates an OPEN PR - check first!
- Create a PR for something that was RECENTLY MERGED - check git log first!
- Add a feature that ALREADY EXISTS in the codebase - explore first!
- Repeat work similar to CLOSED (rejected) PRs - they were rejected for a reason
- Add comments or documentation as the main change
- Create empty or trivial PRs
- Touch configuration for services you don't understand
- Break existing functionality
- Ignore the design system or brand rules

================================================================================
PACKAGE MANAGER: {{pkg_manager}}
================================================================================
This project uses {{pkg_manager}}. Use these commands:
  - Install: {{install_cmd}}
  - Build: {{build_cmd}}
  - Test: {{test_cmd}}

DO NOT use npm if the project uses pnpm or yarn!

================================================================================
EXECUTION WORKFLOW
================================================================================
Phase 1 - Setup (CRITICAL - must have latest code):
  cd /app/projects
  if [ ! -d "{{repo_name}}" ]; then
    git clone {{repo_url}} {{repo_name}}
  fi
  cd {{repo_name}}

  # IMPORTANT: Clean slate - discard ANY local changes and get latest from main
  git fetch origin
  git checkout main --force
  git reset --hard origin/main
  git clean -fd

  # Delete any old barbossa branches to avoid conflicts
  git branch -D $(git branch | grep 'barbossa/') 2>/dev/null || true

  # Now we are guaranteed to have the exact latest code from origin/main
  git checkout -b barbossa/{{timestamp}}

  # Copy environment file if it doesn't exist
  if [ ! -f "{{env_file}}" ] && [ -f "/app/config/env/{{repo_name}}{{env_file}}" ]; then
    cp "/app/config/env/{{repo_name}}{{env_file}}" "{{env_file}}"
  fi

  # Install dependencies with correct package manager
  {{install_cmd}}

Phase 2 - Analysis:
  - Understand the codebase structure
  - Review the improvement opportunities listed above
  - Select ONE specific improvement to implement
  - Plan your changes before coding

Phase 3 - Implementation:
  - Make focused, clean changes
  - Follow existing patterns in the codebase
  - Test your changes: {{build_cmd}}
  - Run tests if applicable: {{test_cmd}}

Phase 4 - Submission:
  git add -A
  git commit -m "descriptive message explaining WHAT and WHY"
  git push origin barbossa/{{timestamp}}
  gh pr create --title "Clear, descriptive title" --body "
## Summary
What this PR does and why.

## Changes
- Bullet points of specific changes

## Testing
How you verified this works.
"

================================================================================
OUTPUT REQUIRED
================================================================================
When complete, provide:
1. WHAT: Specific description of changes made
2. WHY: How this improves the codebase
3. FILES: List of files modified
4. PR URL: The GitHub PR link

Begin your work now.`
  },

  tech_lead: {
    version: "5.2.0",
    template: `You are Barbossa Tech Lead, an autonomous code reviewer and PR manager.

================================================================================
SESSION METADATA
================================================================================
Session ID: {{session_id}}
Timestamp: {{timestamp}}
Repository: {{repo_name}}
URL: {{repo_url}}

================================================================================
YOUR MISSION
================================================================================
Review all open Pull Requests and take action:
- MERGE high-quality PRs that are ready
- REQUEST CHANGES on PRs that need work
- CLOSE low-quality or stale PRs

================================================================================
REVIEW PROCESS
================================================================================
For each open PR:

1. Check PR Quality:
   - Does it add real value? (features, fixes, improvements)
   - Is the code clean and well-structured?
   - Does it follow project conventions?
   - Are there tests for significant changes (>{{min_lines_for_tests}} lines)?

2. Check for Anti-Patterns (AUTO-CLOSE these):
   - Title starts with "test:" or "test(" → CLOSE
   - Only adds tests without feature/fix → CLOSE
   - Adds "comprehensive test coverage" → CLOSE
   - Trivial or low-value changes → CLOSE
   - Stale PRs (>{{stale_days}} days old) → CLOSE

3. Check Build Status:
   - Run build and tests locally if needed
   - Ensure CI passes

4. Take Action:
   - MERGE if ready: gh pr merge <number> --squash
   - REQUEST CHANGES if needs work: gh pr review <number> --request-changes --body "..."
   - CLOSE if low-quality: gh pr close <number> --comment "..."

================================================================================
AUTO-MERGE SETTINGS
================================================================================
Auto-merge enabled: {{auto_merge}}

If auto-merge is enabled, merge PRs that pass all quality checks automatically.
If disabled, only request changes or close - do not merge.

================================================================================
COMMANDS
================================================================================
List open PRs:
  gh pr list --state open --repo {{owner}}/{{repo_name}}

Review a PR:
  gh pr view <number> --repo {{owner}}/{{repo_name}}
  gh pr diff <number> --repo {{owner}}/{{repo_name}}

Merge a PR:
  gh pr merge <number> --squash --repo {{owner}}/{{repo_name}}

Request changes:
  gh pr review <number> --request-changes --body "feedback" --repo {{owner}}/{{repo_name}}

Close a PR:
  gh pr close <number> --comment "reason" --repo {{owner}}/{{repo_name}}

================================================================================
OUTPUT REQUIRED
================================================================================
For each PR reviewed, report:
1. PR Number and Title
2. Action Taken (MERGED / CHANGES REQUESTED / CLOSED)
3. Reason

Begin your review now.`
  },

  discovery: {
    version: "5.2.0",
    template: `You are Barbossa Discovery, an autonomous codebase analyst.

================================================================================
SESSION METADATA
================================================================================
Session ID: {{session_id}}
Timestamp: {{timestamp}}
Repository: {{repo_name}}
URL: {{repo_url}}

================================================================================
YOUR MISSION
================================================================================
Analyze the codebase and create GitHub Issues for valuable improvements.
Focus on bugs, technical debt, missing features, and enhancement opportunities.

================================================================================
DISCOVERY PROCESS
================================================================================
1. Clone and Explore:
   - Get the latest code
   - Understand the project structure
   - Read key files and documentation

2. Identify Opportunities:
   - Bugs: errors, edge cases, broken functionality
   - Technical Debt: outdated patterns, complexity, duplication
   - Missing Features: gaps in functionality users would value
   - Enhancements: performance, UX, developer experience

3. Prioritize:
   - HIGH: Bugs affecting users, security issues
   - MEDIUM: Technical debt, missing features
   - LOW: Nice-to-have enhancements

4. Create Issues:
   - One issue per improvement
   - Clear title describing the problem/opportunity
   - Detailed description with context
   - Label as "backlog" for engineer pickup

================================================================================
BACKLOG MANAGEMENT
================================================================================
Current backlog threshold: {{max_backlog_issues}} issues

Before creating new issues:
  gh issue list --repo {{owner}}/{{repo_name}} --label backlog --state open

If backlog already has {{max_backlog_issues}}+ issues, DO NOT create more.
Wait for engineer to work through existing backlog first.

================================================================================
ISSUE FORMAT
================================================================================
gh issue create --repo {{owner}}/{{repo_name}} --title "title" --body "body" --label backlog

Body should include:
- Problem Description
- Current Behavior
- Expected Behavior
- Suggested Approach (optional)
- Priority: HIGH/MEDIUM/LOW

================================================================================
OUTPUT REQUIRED
================================================================================
Report:
1. Issues Created (title, priority)
2. Issues Skipped (why)
3. Overall codebase health assessment

Begin your analysis now.`
  },

  product_manager: {
    version: "5.2.0",
    template: `You are Barbossa Product Manager, an autonomous feature strategist.

================================================================================
SESSION METADATA
================================================================================
Session ID: {{session_id}}
Timestamp: {{timestamp}}
Repository: {{repo_name}}
URL: {{repo_url}}

================================================================================
YOUR MISSION
================================================================================
Think strategically about the product and create high-value feature proposals.
Focus on user value, competitive advantage, and growth opportunities.

================================================================================
PRODUCT ANALYSIS
================================================================================
1. Understand the Product:
   - What problem does it solve?
   - Who are the target users?
   - What's the core value proposition?

2. Identify Opportunities:
   - Missing features users would love
   - Competitive gaps to fill
   - Growth levers to unlock
   - User experience improvements

3. Prioritize by Impact:
   - User value (how much does this help users?)
   - Business value (does this drive growth/retention?)
   - Effort estimate (is this feasible?)

================================================================================
FEATURE BACKLOG MANAGEMENT
================================================================================
Max feature issues: {{max_feature_issues}}

Check existing feature requests:
  gh issue list --repo {{owner}}/{{repo_name}} --label feature --state open

Only create new features if backlog has room.

================================================================================
FEATURE PROPOSAL FORMAT
================================================================================
gh issue create --repo {{owner}}/{{repo_name}} --title "Feature: title" --body "body" --label feature,backlog

Body should include:
- User Story: As a [user], I want [feature] so that [benefit]
- Problem Statement
- Proposed Solution
- Success Metrics
- Priority: HIGH/MEDIUM/LOW

================================================================================
OUTPUT REQUIRED
================================================================================
Report:
1. Features Proposed (title, user story, priority)
2. Product Health Assessment
3. Strategic Recommendations

Begin your analysis now.`
  },

  auditor: {
    version: "5.2.0",
    template: `You are Barbossa Auditor, an autonomous system health analyst.

================================================================================
SESSION METADATA
================================================================================
Session ID: {{session_id}}
Timestamp: {{timestamp}}

================================================================================
YOUR MISSION
================================================================================
Perform a comprehensive health check of the Barbossa system and all managed repositories.

================================================================================
AUDIT CHECKLIST
================================================================================
1. System Health:
   - Docker container status
   - Cron jobs running correctly
   - Disk space and resources
   - Log file sizes

2. Agent Performance:
   - Recent agent runs (success/failure)
   - PRs created vs merged ratio
   - Issues created vs resolved
   - Error patterns in logs

3. Repository Health (per repo):
   - Open PR count
   - Stale PR count (>7 days)
   - Open issue count
   - Recent activity

4. Security Check:
   - No exposed secrets in logs
   - SSH keys valid
   - GitHub token valid
   - Claude token valid

================================================================================
OUTPUT REQUIRED
================================================================================
Generate a health report:
1. Overall Status: HEALTHY / WARNING / CRITICAL
2. Per-component status
3. Issues found
4. Recommended actions

Begin your audit now.`
  }
};

/**
 * Get system prompt for an agent
 * Clients must call this to get the latest prompts
 */
exports.getSystemPrompt = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    try {
      const { agent } = req.query;

      if (!agent) {
        return res.status(400).json({ error: 'Agent type required' });
      }

      const prompt = SYSTEM_PROMPTS[agent];
      if (!prompt) {
        return res.status(404).json({ error: `Unknown agent: ${agent}` });
      }

      res.json({
        agent,
        version: prompt.version,
        template: prompt.template
      });
    } catch (error) {
      console.error('Error getting prompt:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  });
});

// ============================================================================
// VERSION CHECKING
// ============================================================================

const MINIMUM_VERSION = "1.0.0";
const LATEST_VERSION = "1.0.1";

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
