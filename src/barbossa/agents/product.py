#!/usr/bin/env python3
"""
Barbossa Product Manager v2.1.0 - Autonomous Feature Discovery Agent
Runs daily to analyze products and create feature Issues for the backlog.

Part of the Pipeline:
- Product Manager (daily 07:00) → creates feature Issues  <-- THIS AGENT
- Discovery (3x daily) → creates technical debt Issues
- Engineer (:00) → implements from backlog, creates PRs
- Tech Lead (:35) → reviews PRs, merges or requests changes
- Auditor (daily 06:30) → system health analysis

The Product Manager focuses on:
1. Feature opportunities - New functionality that adds user value
2. UX improvements - Better flows, interactions, accessibility
3. Competitive features - What similar products offer
4. User pain points - Common friction areas

Prompts loaded locally from prompts/ directory.
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import uuid

# Local prompt loading and optional analytics/state tracking
from barbossa.utils.prompts import get_system_prompt
from barbossa.agents.firebase import (
    get_client,
    check_version,
    track_run_start,
    track_run_end
)
from barbossa.utils.issue_tracker import (
    get_issue_tracker,
    GitHubIssueTracker,
    get_last_curation_timestamp,
    update_curation_marker,
    Issue
)
from barbossa.utils.notifications import (
    notify_agent_run_complete,
    notify_error,
    wait_for_pending,
    process_retry_queue
)


class BarbossaProduct:
    """Product Manager agent that creates feature Issues for the pipeline."""

    VERSION = "2.2.0"
    DEFAULT_MAX_ISSUES_PER_RUN = 3
    DEFAULT_FEATURE_BACKLOG_THRESHOLD = 20
    DEFAULT_ITERATION_RATIO = 0.7
    DEFAULT_MIN_HOURS_SINCE_CURATION = 48

    def __init__(self, work_dir: Optional[Path] = None):
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-dev'

        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.projects_dir = self.work_dir / 'projects'
        self.config_file = self.work_dir / 'config' / 'repositories.json'

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

        # Firebase client (analytics + state tracking, never blocks)
        self.firebase = get_client()

        # Soft version check - warn but never block
        update_msg = check_version()
        if update_msg:
            self.logger.info(f"UPDATE AVAILABLE: {update_msg}")

        self.config = self._load_config()
        self.repositories = self.config.get('repositories', [])
        self.owner = self.config.get('owner')
        if not self.owner:
            raise ValueError("'owner' is required in config/repositories.json")

        # Load settings from config
        settings = self.config.get('settings', {}).get('product_manager', {})
        self.enabled = settings.get('enabled', True)
        self.MAX_ISSUES_PER_RUN = settings.get('max_issues_per_run', self.DEFAULT_MAX_ISSUES_PER_RUN)
        self.FEATURE_BACKLOG_THRESHOLD = settings.get('max_feature_issues', self.DEFAULT_FEATURE_BACKLOG_THRESHOLD)
        self.iteration_ratio = settings.get('iteration_ratio', self.DEFAULT_ITERATION_RATIO)
        self.min_hours_since_curation = settings.get('min_hours_since_curation', self.DEFAULT_MIN_HOURS_SINCE_CURATION)

        self.logger.info("=" * 60)
        self.logger.info(f"BARBOSSA PRODUCT MANAGER v{self.VERSION}")
        self.logger.info(f"Repositories: {len(self.repositories)}")
        self.logger.info(f"Settings: max_issues_per_run={self.MAX_ISSUES_PER_RUN}, max_feature_issues={self.FEATURE_BACKLOG_THRESHOLD}")
        self.logger.info(f"Curation: iteration_ratio={self.iteration_ratio}, min_hours={self.min_hours_since_curation}")
        self.logger.info("=" * 60)

    def _setup_logging(self):
        log_file = self.logs_dir / f"product_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('product')

    def _load_config(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in config file {self.config_file}: {e}")
                return {'repositories': []}
        return {'repositories': []}

    def _run_cmd(self, cmd: str, cwd: str = None, timeout: int = 60) -> Optional[str]:
        """Run a shell command and return output."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                self.logger.warning(f"Command failed (exit {result.returncode}): {cmd[:100]}")
                if result.stderr:
                    self.logger.warning(f"Stderr: {result.stderr[:500]}")
            return None
        except Exception as e:
            self.logger.warning(f"Command failed: {cmd[:100]} - {e}")
            return None

    def _get_issue_tracker(self, repo_name: str) -> GitHubIssueTracker:
        """Get the issue tracker for a repository."""
        return get_issue_tracker(self.config, repo_name, self.logger)

    def _get_feature_backlog_count(self, repo_name: str) -> int:
        """Count open feature issues for a repo."""
        try:
            tracker = self._get_issue_tracker(repo_name)
            return tracker.get_backlog_count(label="feature")
        except Exception as e:
            self.logger.warning(f"Failed to get feature backlog count: {e}")
            return 0

    def _get_existing_issue_titles(self, repo_name: str) -> List[str]:
        """Get titles of existing open issues to avoid duplicates."""
        try:
            tracker = self._get_issue_tracker(repo_name)
            return tracker.get_existing_titles(limit=100)
        except Exception as e:
            self.logger.warning(f"Failed to get existing titles: {e}")
            return []

    def _get_existing_issue_details(self, repo_name: str) -> List[Dict]:
        """Get full details of existing open issues for better deduplication."""
        try:
            tracker = self._get_issue_tracker(repo_name)
            issues = tracker.list_issues(limit=100)
            return [{'title': i.title, 'body': i.body, 'labels': i.labels} for i in issues]
        except Exception as e:
            self.logger.warning(f"Failed to get issue details: {e}")
            return []

    def _get_recent_prs(self, repo_name: str) -> List[str]:
        """Get recent PR titles to avoid suggesting already-implemented features."""
        result = self._run_cmd(
            f"gh pr list --repo {self.owner}/{repo_name} --state all --limit 50 --json title"
        )
        if result:
            try:
                prs = json.loads(result)
                return [p['title'].lower() for p in prs]
            except json.JSONDecodeError as e:
                self.logger.warning(f"Could not parse PR list: {e}")
        return []

    def _clone_or_update_repo(self, repo: Dict) -> Optional[Path]:
        """Ensure repo is cloned and up to date.

        Tries 'main' branch first, falls back to 'master' for older repos.
        """
        repo_name = repo['name']
        repo_path = self.projects_dir / repo_name

        if repo_path.exists():
            # Try main branch first, fall back to master
            result = self._run_cmd("git fetch origin && git checkout main && git pull origin main", cwd=str(repo_path))
            if result is None:
                # Try master branch as fallback for older repos
                self._run_cmd("git fetch origin && git checkout master && git pull origin master", cwd=str(repo_path))
        else:
            self.projects_dir.mkdir(parents=True, exist_ok=True)
            result = self._run_cmd(f"git clone {repo['url']} {repo_name}", cwd=str(self.projects_dir))
            if result is None:
                self.logger.error(f"Failed to clone repository: {repo['url']}")
                return None

        if repo_path.exists():
            return repo_path
        return None

    def _read_claude_md(self, repo_path: Path) -> str:
        """Read CLAUDE.md for project context.

        Uses explicit UTF-8 encoding to handle files with emoji, unicode quotes,
        and international characters. Falls back gracefully on encoding errors.
        """
        claude_md = repo_path / 'CLAUDE.md'
        if claude_md.exists():
            try:
                with open(claude_md, 'r', encoding='utf-8') as f:
                    return f.read()[:15000]  # Limit size
            except UnicodeDecodeError as e:
                self.logger.warning(f"Could not decode CLAUDE.md (encoding error): {e}")
                # Try with error handling to salvage what we can
                try:
                    with open(claude_md, 'r', encoding='utf-8', errors='replace') as f:
                        return f.read()[:15000]
                except Exception:
                    pass
            except IOError as e:
                self.logger.warning(f"Could not read CLAUDE.md: {e}")
        return ""

    def _create_issue(self, repo_name: str, title: str, body: str, labels: List[str] = None) -> bool:
        """Create an issue using the configured tracker."""
        labels = labels or ['backlog', 'feature', 'product']
        try:
            tracker = self._get_issue_tracker(repo_name)
            self.logger.info(f"Creating issue: {title}")
            issue = tracker.create_issue(title=title, body=body, labels=labels)
            if issue:
                self.logger.info(f"Created feature issue: {title}")
                self.logger.info(f"  URL: {issue.url}")
                return True
            else:
                self.logger.warning(f"Failed to create issue: {title}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to create issue: {e}")
            return False

    def _get_product_prompt(self, repo: Dict, claude_md: str) -> str:
        """Generate the product analysis prompt for Claude - loaded from local file."""
        repo_name = repo['name']

        # Product-specific context - prefer config fields, fallback to hardcoded
        product_context = self._get_product_context_from_config(repo)
        if not product_context:
            product_context = self._get_product_context(repo_name)

        # Load template from local file
        template = get_system_prompt("product_manager")
        if not template:
            self.logger.error("Failed to load product_manager prompt from prompts/product_manager.txt")
            raise RuntimeError("Product manager prompt file not found. Check prompts/ directory.")

        self.logger.info("Using local prompt template")
        # Replace template variables
        prompt = template
        prompt = prompt.replace("{{repo_name}}", repo_name)
        prompt = prompt.replace("{{claude_md}}", claude_md[:8000])
        prompt = prompt.replace("{{product_context}}", product_context)
        return prompt

    def _get_product_context_from_config(self, repo: Dict) -> str:
        """Build product context from config fields (focus and known_gaps)."""
        context_parts = []

        if 'focus' in repo:
            context_parts.append(f"DEVELOPMENT FOCUS:\n{repo['focus']}")

        if 'known_gaps' in repo and repo['known_gaps']:
            gaps_list = "\n".join([f"  - {gap}" for gap in repo['known_gaps']])
            context_parts.append(f"KNOWN GAPS (PRIORITY OPPORTUNITIES):\n{gaps_list}")

        return "\n\n".join(context_parts) if context_parts else ""

    def _get_product_context(self, repo_name: str) -> str:
        """Get product-specific context for each repository."""

        if repo_name == 'peerlytics':
            return """
PEERLYTICS - ZKP2P Analytics Dashboard

WHAT IT DOES:
- Analytics dashboard for ZKP2P protocol (peer-to-peer USDC-to-fiat)
- Tracks liquidity, volume, participants, intent fulfillment
- Supports multiple payment methods (Venmo, Revolut, PayPal, etc.)

CURRENT FEATURES (DO NOT SUGGEST THESE):
- Dashboard tabs: Overview, Markets, Liquidity, Leaderboard, Live Events
- Network pulse chart, currency/platform breakdowns
- Maker/taker leaderboards with tier system
- Explorer: address/deposit/intent detail pages
- User profiles with Privy authentication
- Real-time WebSocket events from V3 contract
- Firebase caching with Envio fallback

KNOWN GAPS (GOOD OPPORTUNITIES):
- No custom date range picker (only fixed periods: MTD, 3MTD, YTD, ALL)
- No maker profitability metrics (realized vs unrealized profit)
- No intent fulfillment time analysis (avg/median/p95 fill times)
- No alerts/notifications system
- No cohort analysis (deposits by creation month)
- No export/download functionality
- Limited mobile responsiveness on charts

TECH STACK:
- Next.js 15, React 19, TypeScript
- ECharts for complex charts, Nivo for Sankey
- React Query for data fetching
- Firebase Firestore (cache), Envio GraphQL (source)
- Tailwind CSS, Radix UI primitives

KEY FILES:
- src/components/dashboard/Dashboard.tsx - main orchestrator
- src/components/dashboard/tabs/*.tsx - each dashboard tab
- src/hooks/useDashboardData.ts - data fetching
- src/lib/indexer/aggregators.ts - data transformation
"""

        elif repo_name == 'usdctofiat':
            return """
USDCTOFIAT - USDC Off-Ramp Application

WHAT IT DOES:
- Web3 off-ramp for converting USDC to fiat on Base
- Makers create deposits, set rates, receive fiat payments
- Peer-to-peer matching via ZKP2P protocol
- Non-custodial (funds in smart contract escrow)

CURRENT FEATURES (DO NOT SUGGEST THESE):
- Multi-step deposit creation wizard (platform, currency, rate)
- 8 payment platforms (Venmo, PayPal, Revolut, Wise, etc.)
- 25+ currencies supported
- Market intelligence with percentile ranking
- Rate suggestions based on active deposits
- Quick repeat for last deposit settings
- Deposit management (add funds, withdraw, update rates, pause)
- Relay bridge integration for cross-chain USDC
- Optional 0.25% tip system
- Privy smart wallets + EOA support

KNOWN GAPS (GOOD OPPORTUNITIES):
- No real-time FX rate streaming (30s cached rates)
- No rate alerts (notify when rate drops below threshold)
- No batch operations (update rates on multiple deposits)
- No fill velocity predictions (expected time to fill)
- No maker analytics dashboard (volume, revenue, fill rates)
- No rate scheduling (auto-adjust by time of day)
- No deposit templates (save multiple preset configs)
- Limited intent lifecycle visibility

TECH STACK:
- React 18, Vite, TypeScript
- Tailwind CSS 4, Radix UI
- Privy SDK for authentication
- ZKP2P SDK for contract interactions
- Viem for Ethereum utilities

KEY FILES:
- src/components/DepositCalculator.tsx - main deposit creation (1200+ lines)
- src/components/ManageDeposits.tsx - deposit dashboard
- src/services/marketIntel.ts - rate suggestions
- src/services/fiatPrices.ts - FX rate fetching
- src/lib/zkp2pClient.ts - SDK singleton
"""

        return ""

    def _analyze_with_claude(self, repo: Dict, claude_md: str) -> Optional[str]:
        """Use Claude to analyze product and create a feature issue via gh CLI.

        Returns the issue URL if Claude created one, None otherwise.
        Claude handles duplicate checking and value assessment directly.
        """
        import re
        prompt = self._get_product_prompt(repo, claude_md)

        # Write prompt to temp file
        prompt_file = self.work_dir / 'temp_product_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        # Call Claude CLI with permissions to run gh commands (15 minute timeout)
        result = self._run_cmd(
            f'cat {prompt_file} | claude --dangerously-skip-permissions -p',
            timeout=900
        )

        prompt_file.unlink(missing_ok=True)

        if not result:
            return None

        # Extract the actual response text
        response_text = result
        try:
            wrapper = json.loads(result)
            if 'result' in wrapper:
                response_text = wrapper['result']
        except json.JSONDecodeError:
            pass

        # Check for explicit "NO SUGGESTION" response
        if "NO SUGGESTION" in response_text.upper():
            self.logger.info("Claude explicitly declined to suggest a feature (NO SUGGESTION)")
            return None

        # Look for GitHub issue URL in response (Claude created issue via gh CLI)
        repo_name = repo.get('name', '')
        owner = self.config.get('owner', '')

        # Match issue URLs like https://github.com/owner/repo/issues/123
        url_pattern = rf'https://github\.com/{owner}/{repo_name}/issues/(\d+)'
        url_match = re.search(url_pattern, response_text)

        if url_match:
            issue_url = url_match.group(0)
            issue_number = url_match.group(1)
            self.logger.info(f"Claude created issue #{issue_number}: {issue_url}")
            return issue_url

        # Fallback: check if any github issue URL was created
        generic_url_match = re.search(r'https://github\.com/[^/]+/[^/]+/issues/\d+', response_text)
        if generic_url_match:
            issue_url = generic_url_match.group(0)
            self.logger.info(f"Claude created issue: {issue_url}")
            return issue_url

        self.logger.warning("No issue URL found in Claude response")
        return None

    def _extract_keywords(self, text: str) -> set:
        """Extract meaningful keywords from text for similarity comparison."""
        # Remove common prefixes and noise words
        text = text.lower()
        for prefix in ['feat:', 'feature:', 'feat(', 'add ', 'implement ', 'create ']:
            text = text.replace(prefix, '')

        # Common words to ignore
        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'new'}

        # Split into words and filter
        words = text.split()
        keywords = {w.strip('.,!?()[]{}:;-') for w in words if len(w) > 3 and w not in stop_words}
        return keywords

    def _is_semantically_similar(self, new_title: str, existing_issues: List[Dict]) -> bool:
        """Check if a new feature is semantically similar to existing issues."""
        new_keywords = self._extract_keywords(new_title)

        for issue in existing_issues:
            # Only check feature/product issues
            # Labels can be strings or dicts depending on source
            raw_labels = issue.get('labels', [])
            labels = [l if isinstance(l, str) else l.get('name', '') for l in raw_labels]
            if 'feature' not in labels and 'product' not in labels:
                continue

            existing_title = issue.get('title', '')
            existing_keywords = self._extract_keywords(existing_title)

            # Calculate keyword overlap
            if not new_keywords or not existing_keywords:
                continue

            overlap = new_keywords & existing_keywords
            overlap_ratio = len(overlap) / min(len(new_keywords), len(existing_keywords))

            # If more than 50% keyword overlap, consider it similar
            if overlap_ratio > 0.5:
                self.logger.info(f"Similar issue found: '{existing_title}' (overlap: {overlap_ratio:.2%})")
                self.logger.info(f"  Overlapping keywords: {', '.join(sorted(overlap))}")
                return True

        return False

    def _generate_issue_body(self, feature: Dict, repo_name: str) -> str:
        """Generate the Issue body from feature analysis."""
        acceptance = '\n'.join([f"- [ ] {c}" for c in feature.get('acceptance_criteria', [])])

        return f"""## Problem
{feature.get('problem', 'No problem statement provided.')}

## Proposed Solution
{feature.get('solution', 'No solution provided.')}

## Acceptance Criteria
{acceptance}

## Technical Approach
{feature.get('technical_approach', 'Use existing patterns in the codebase.')}

## Metadata
- **Value Score:** {feature.get('value_score', '?')}/10
- **Effort Estimate:** {feature.get('effort_estimate', 'medium')}

---
*Created by Barbossa Product Manager v{self.VERSION}*
"""

    def _get_issues_needing_curation(self, repo_name: str) -> List[Issue]:
        """Find product/feature issues that haven't been curated recently."""
        tracker = self._get_issue_tracker(repo_name)
        issues = tracker.list_issues(labels=['product'], state='open', limit=50)

        now = datetime.now(timezone.utc)
        needs_curation = []

        for issue in issues:
            # Skip if recently updated by humans (within 24h)
            if issue.updated_at:
                try:
                    updated = datetime.fromisoformat(issue.updated_at.replace('Z', '+00:00'))
                    hours_since_update = (now - updated).total_seconds() / 3600
                    if hours_since_update < 24:
                        self.logger.debug(f"Skipping #{issue.id}: recently updated ({hours_since_update:.1f}h ago)")
                        continue
                except ValueError:
                    pass

            # Check curation marker
            last_curated = get_last_curation_timestamp(issue.body or '')
            if last_curated:
                hours_since_curation = (now - last_curated).total_seconds() / 3600
                if hours_since_curation < self.min_hours_since_curation:
                    self.logger.debug(f"Skipping #{issue.id}: curated {hours_since_curation:.1f}h ago")
                    continue

            needs_curation.append(issue)

        self.logger.info(f"Found {len(needs_curation)} issues needing curation")
        return needs_curation

    def _get_iteration_prompt(self, repo: Dict, issue: Issue) -> str:
        """Generate prompt for iterating on an existing issue."""
        repo_name = repo['name']

        return f"""You are Barbossa Product Manager reviewing an existing GitHub issue.

================================================================================
ISSUE TO REVIEW
================================================================================
Repository: {self.owner}/{repo_name}
Issue: #{issue.id}
Title: {issue.title}
Labels: {', '.join(issue.labels)}

Body:
{issue.body or '(empty)'}

================================================================================
TASK
================================================================================
Review this issue and decide:
1. CLOSE - The problem is no longer relevant, was already solved, or is a duplicate
2. EDIT - The issue needs improvement (clearer scope, better acceptance criteria, updated context)
3. KEEP - The issue is good as-is, just update the curation timestamp

================================================================================
OUTPUT FORMAT
================================================================================
Output valid JSON only:

For CLOSE:
{{"action": "CLOSE", "reason": "Brief explanation why this should be closed"}}

For EDIT:
{{"action": "EDIT", "new_title": "Updated title if needed or null", "new_body": "Complete updated body"}}

For KEEP:
{{"action": "KEEP"}}

================================================================================
GUIDELINES
================================================================================
- CLOSE if: issue duplicates another, problem was fixed, feature already exists, scope too large
- EDIT if: unclear acceptance criteria, missing technical approach, outdated context, vague problem statement
- KEEP if: issue is well-written, actionable, and still relevant

Be aggressive about closing stale or low-value issues. Quality over quantity.

Output JSON only, no other text.
"""

    def _iterate_on_issue(self, repo: Dict, issue: Issue) -> str:
        """Use Claude to review and improve an existing issue. Returns action taken."""
        import re

        prompt = self._get_iteration_prompt(repo, issue)
        prompt_file = self.work_dir / 'temp_iteration_prompt.txt'

        with open(prompt_file, 'w') as f:
            f.write(prompt)

        result = self._run_cmd(
            f'cat {prompt_file} | claude --dangerously-skip-permissions -p',
            timeout=300
        )

        prompt_file.unlink(missing_ok=True)

        if not result:
            self.logger.warning(f"No response from Claude for issue #{issue.id}")
            return "error"

        # Parse JSON response
        try:
            # Extract JSON from response (might have wrapper)
            response_text = result
            try:
                wrapper = json.loads(result)
                if 'result' in wrapper:
                    response_text = wrapper['result']
            except json.JSONDecodeError:
                pass

            # Find JSON object in response
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if not json_match:
                self.logger.warning(f"No JSON found in response for issue #{issue.id}")
                return "error"

            decision = json.loads(json_match.group())
            action = decision.get('action', '').upper()

            tracker = self._get_issue_tracker(repo['name'])

            if action == 'CLOSE':
                reason = decision.get('reason', 'Closed by Barbossa Product Manager during curation.')
                tracker.close_issue(int(issue.id), reason)
                self.logger.info(f"CLOSED issue #{issue.id}: {reason}")
                return "closed"

            elif action == 'EDIT':
                new_title = decision.get('new_title')
                new_body = decision.get('new_body')

                if new_body:
                    new_body = update_curation_marker(new_body, datetime.now(timezone.utc), "Barbossa Product Manager", self.VERSION)
                else:
                    # Just update curation marker on existing body
                    new_body = update_curation_marker(issue.body or '', datetime.now(timezone.utc), "Barbossa Product Manager", self.VERSION)

                tracker.update_issue(
                    int(issue.id),
                    title=new_title,
                    body=new_body
                )
                self.logger.info(f"EDITED issue #{issue.id}")
                return "edited"

            elif action == 'KEEP':
                # Update curation marker only
                new_body = update_curation_marker(issue.body or '', datetime.now(timezone.utc), "Barbossa Product Manager", self.VERSION)
                tracker.update_issue(int(issue.id), body=new_body)
                self.logger.info(f"KEPT issue #{issue.id} (updated curation timestamp)")
                return "kept"

            else:
                self.logger.warning(f"Unknown action '{action}' for issue #{issue.id}")
                return "error"

        except json.JSONDecodeError as e:
            self.logger.warning(f"Could not parse Claude response for issue #{issue.id}: {e}")
            return "error"

    def discover_for_repo(self, repo: Dict) -> int:
        """Run product analysis for a single repository.

        Curation Mode (v2.2.0):
        1. First: iterate on existing issues (based on iteration_ratio)
        2. Then: create new issues if backlog allows
        """
        repo_name = repo['name']
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ANALYZING: {repo_name}")
        self.logger.info(f"{'='*60}")

        # Check feature backlog size
        feature_count = self._get_feature_backlog_count(repo_name)
        self.logger.info(f"Current feature backlog: {feature_count} issues")

        issues_curated = 0
        issues_created = 0

        # Phase 1: Iterate on existing issues (based on iteration_ratio)
        max_iterations = max(1, int(self.MAX_ISSUES_PER_RUN * self.iteration_ratio))
        self.logger.info(f"\n--- PHASE 1: Curating existing issues (max {max_iterations}) ---")

        issues_needing_curation = self._get_issues_needing_curation(repo_name)

        for issue in issues_needing_curation[:max_iterations]:
            self.logger.info(f"Reviewing issue #{issue.id}: {issue.title}")
            action = self._iterate_on_issue(repo, issue)
            if action in ['closed', 'edited', 'kept']:
                issues_curated += 1

        self.logger.info(f"Curated {issues_curated} existing issues")

        # Phase 2: Create new issues if backlog allows
        if feature_count >= self.FEATURE_BACKLOG_THRESHOLD:
            self.logger.info(f"Feature backlog full (>= {self.FEATURE_BACKLOG_THRESHOLD}), skipping new issue creation")
            return issues_curated

        max_new = max(1, int(self.MAX_ISSUES_PER_RUN * (1 - self.iteration_ratio)))
        self.logger.info(f"\n--- PHASE 2: Creating new issues (max {max_new}) ---")

        # Clone/update repo for context
        repo_path = self._clone_or_update_repo(repo)
        if not repo_path:
            self.logger.error(f"Could not access repo: {repo_name}")
            return issues_curated

        # Read project context
        claude_md = self._read_claude_md(repo_path)
        if not claude_md:
            self.logger.warning(f"No CLAUDE.md found for {repo_name}")

        # Analyze with Claude - Claude creates the issue directly via gh CLI
        self.logger.info("Analyzing product with Claude...")
        issue_url = self._analyze_with_claude(repo, claude_md)

        if not issue_url:
            self.logger.info("No new feature suggestion from Claude")
        else:
            self.logger.info(f"Feature issue created: {issue_url}")
            issues_created = 1

        total = issues_curated + issues_created
        self.logger.info(f"\nTotal actions: {issues_curated} curated, {issues_created} created")
        return total

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + str(uuid.uuid4())[:8]

    def run(self):
        """Run product analysis for all repositories."""
        run_session_id = self._generate_session_id()

        if not self.enabled:
            self.logger.info("Product Manager is disabled in config. Skipping.")
            return 0

        self.logger.info(f"\n{'#'*60}")
        self.logger.info("BARBOSSA PRODUCT MANAGER RUN")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'#'*60}\n")

        # Process any pending webhook retries from previous runs
        process_retry_queue()

        # Track run start (fire-and-forget, never blocks)
        track_run_start("product_manager", run_session_id, len(self.repositories))

        total_issues = 0
        errors = 0
        for repo in self.repositories:
            try:
                issues = self.discover_for_repo(repo)
                total_issues += issues
            except Exception as e:
                self.logger.error(f"Error analyzing {repo['name']}: {e}")
                errors += 1
                notify_error(
                    agent='product',
                    error_message=str(e),
                    context="Analyzing repository for feature opportunities",
                    repo_name=repo['name']
                )

        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"PRODUCT ANALYSIS COMPLETE: {total_issues} feature issues created")
        self.logger.info(f"{'#'*60}\n")

        # Track run end (fire-and-forget)
        track_run_end("product_manager", run_session_id, success=True, pr_created=False)

        # Send run summary notification (only if something happened)
        if total_issues > 0 or errors > 0:
            notify_agent_run_complete(
                agent='product',
                success=(errors == 0),
                summary=f"Created {total_issues} feature suggestion(s) across {len(self.repositories)} repositories",
                details={
                    'Features Suggested': total_issues,
                    'Repositories': len(self.repositories),
                    'Errors': errors
                }
            )

        # Ensure all notifications complete before process exits
        wait_for_pending()
        return total_issues


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Barbossa Product Manager')
    parser.add_argument('--repo', help='Run for specific repo only')
    args = parser.parse_args()

    product = BarbossaProduct()

    if args.repo:
        repo = next((r for r in product.repositories if r['name'] == args.repo), None)
        if repo:
            product.discover_for_repo(repo)
        else:
            print(f"Repo not found: {args.repo}")
    else:
        product.run()


if __name__ == "__main__":
    main()
