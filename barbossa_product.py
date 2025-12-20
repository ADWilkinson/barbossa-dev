#!/usr/bin/env python3
"""
Barbossa Product Manager v5.1 - Autonomous Feature Discovery Agent
Runs daily to analyze products and create feature Issues for the backlog.

Part of the v5.1 Pipeline:
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
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class BarbossaProduct:
    """Product Manager agent that creates feature Issues for the pipeline."""

    VERSION = "5.2.0"
    DEFAULT_MAX_ISSUES_PER_RUN = 3
    DEFAULT_FEATURE_BACKLOG_THRESHOLD = 20

    def __init__(self, work_dir: Optional[Path] = None):
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-engineer'

        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.projects_dir = self.work_dir / 'projects'
        self.config_file = self.work_dir / 'config' / 'repositories.json'

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

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

        self.logger.info("=" * 60)
        self.logger.info(f"BARBOSSA PRODUCT MANAGER v{self.VERSION}")
        self.logger.info(f"Repositories: {len(self.repositories)}")
        self.logger.info(f"Settings: max_issues_per_run={self.MAX_ISSUES_PER_RUN}, max_feature_issues={self.FEATURE_BACKLOG_THRESHOLD}")
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
            with open(self.config_file, 'r') as f:
                return json.load(f)
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

    def _get_feature_backlog_count(self, repo_name: str) -> int:
        """Count open feature issues for a repo."""
        result = self._run_cmd(
            f"gh issue list --repo {self.owner}/{repo_name} --label feature --state open --json number"
        )
        if result:
            try:
                issues = json.loads(result)
                return len(issues)
            except:
                pass
        return 0

    def _get_existing_issue_titles(self, repo_name: str) -> List[str]:
        """Get titles of existing open issues to avoid duplicates."""
        result = self._run_cmd(
            f"gh issue list --repo {self.owner}/{repo_name} --state open --limit 100 --json title"
        )
        if result:
            try:
                issues = json.loads(result)
                return [i['title'].lower() for i in issues]
            except:
                pass
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
            except:
                pass
        return []

    def _clone_or_update_repo(self, repo: Dict) -> Optional[Path]:
        """Ensure repo is cloned and up to date."""
        repo_name = repo['name']
        repo_path = self.projects_dir / repo_name

        if repo_path.exists():
            self._run_cmd("git fetch origin && git checkout main && git pull origin main", cwd=str(repo_path))
        else:
            self._run_cmd(f"git clone {repo['url']} {repo_name}", cwd=str(self.projects_dir))

        if repo_path.exists():
            return repo_path
        return None

    def _read_claude_md(self, repo_path: Path) -> str:
        """Read CLAUDE.md for project context."""
        claude_md = repo_path / 'CLAUDE.md'
        if claude_md.exists():
            with open(claude_md, 'r') as f:
                return f.read()[:15000]  # Limit size
        return ""

    def _create_issue(self, repo_name: str, title: str, body: str, labels: List[str] = None) -> bool:
        """Create a GitHub Issue."""
        labels = labels or ['backlog', 'feature', 'product']
        label_str = ','.join(labels)

        # Write body to temp file to handle special characters
        body_file = self.work_dir / 'temp_product_issue.md'
        with open(body_file, 'w') as f:
            f.write(body)

        # Escape title for shell
        escaped_title = title.replace('"', '\\"')
        cmd = f'gh issue create --repo {self.owner}/{repo_name} --title "{escaped_title}" --body-file {body_file} --label "{label_str}"'
        self.logger.info(f"Creating issue: {escaped_title}")

        result = self._run_cmd(cmd, timeout=30)

        # Clean up temp file
        body_file.unlink(missing_ok=True)

        if result:
            self.logger.info(f"Created feature issue: {title}")
            self.logger.info(f"  URL: {result}")
            return True
        else:
            self.logger.warning(f"Failed to create issue: {title}")
        return False

    def _get_product_prompt(self, repo: Dict, claude_md: str) -> str:
        """Generate the product analysis prompt for Claude."""
        repo_name = repo['name']

        # Product-specific context
        product_context = self._get_product_context(repo_name)

        return f"""You are a Product Manager analyzing {repo_name} to identify valuable feature opportunities.

================================================================================
PROJECT CONTEXT
================================================================================
{claude_md[:8000]}

================================================================================
PRODUCT-SPECIFIC KNOWLEDGE
================================================================================
{product_context}

================================================================================
YOUR TASK
================================================================================
Analyze this product and suggest ONE high-value feature that:

1. ADDS GENUINE USER VALUE - solves a real problem or improves experience
2. IS IMPLEMENTABLE - can be built by a senior engineer in 1-3 days
3. FITS THE ARCHITECTURE - uses existing patterns and tech stack
4. ISN'T ALREADY DONE - check the context for existing features

================================================================================
FEATURE CATEGORIES TO CONSIDER
================================================================================

FOR ANALYTICS DASHBOARDS (peerlytics):
- Data visualization improvements (new chart types, better insights)
- Filtering and exploration (custom date ranges, advanced filters)
- Performance metrics (new KPIs, trend analysis)
- User engagement (alerts, saved views, exports)
- Mobile/responsive improvements
- Accessibility enhancements

FOR FINANCIAL APPS (usdctofiat):
- Transaction flow improvements (faster, clearer UX)
- Rate optimization tools (better market intelligence)
- Portfolio management (batch operations, analytics)
- Notifications and alerts (rate changes, fill events)
- Mobile experience (PWA, responsive)
- Error handling and recovery

================================================================================
OUTPUT FORMAT
================================================================================
Respond with ONLY a JSON object (no markdown, no explanation):

{{
  "feature_title": "feat: <concise title under 60 chars>",
  "problem": "<1-2 sentences: what user problem does this solve?>",
  "solution": "<2-3 sentences: what should be built?>",
  "acceptance_criteria": [
    "<specific testable criterion 1>",
    "<specific testable criterion 2>",
    "<specific testable criterion 3>"
  ],
  "technical_approach": "<1-2 sentences: how to implement using existing patterns>",
  "value_score": <1-10 how valuable to users>,
  "effort_estimate": "<small|medium|large>"
}}

IMPORTANT:
- Be SPECIFIC, not vague ("add loading skeleton to DepositCard" not "improve UX")
- Reference ACTUAL components/files from the codebase
- Don't suggest features that clearly already exist
- Focus on quick wins (small/medium effort, high value)
"""

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

    def _analyze_with_claude(self, repo: Dict, claude_md: str) -> Optional[Dict]:
        """Use Claude to analyze the product and suggest a feature."""
        import re
        prompt = self._get_product_prompt(repo, claude_md)

        # Write prompt to temp file
        prompt_file = self.work_dir / 'temp_product_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        # Call Claude CLI (15 minute timeout - matches Tech Lead complexity)
        result = self._run_cmd(
            f'cat {prompt_file} | claude -p --output-format json',
            timeout=900
        )

        prompt_file.unlink(missing_ok=True)

        if not result:
            return None

        try:
            # Claude CLI returns wrapper JSON with result field
            wrapper = json.loads(result)
            if 'result' in wrapper:
                inner_result = wrapper['result']

                # Extract JSON from markdown code block if present
                json_block_match = re.search(r'```json\s*\n([\s\S]*?)\n```', inner_result)
                if json_block_match:
                    json_str = json_block_match.group(1).strip()
                    self.logger.info(f"Extracted JSON from code block: {json_str[:300]}...")
                    data = json.loads(json_str)
                    if 'feature_title' in data:
                        return data

                # Fallback: try to find JSON object directly
                json_obj_match = re.search(r'\{[^{}]*"feature_title"[^{}]*("acceptance_criteria"\s*:\s*\[[^\]]*\])?[^{}]*\}', inner_result, re.DOTALL)
                if json_obj_match:
                    json_str = json_obj_match.group()
                    self.logger.info(f"Extracted JSON object: {json_str[:300]}...")
                    data = json.loads(json_str)
                    if 'feature_title' in data:
                        return data

            # Fallback: check if wrapper itself has feature_title
            if 'feature_title' in wrapper:
                return wrapper

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parse error: {e}")
            # Last resort: try to extract any valid JSON with feature_title
            try:
                # Find the start of JSON object
                start = result.find('"feature_title"')
                if start > 0:
                    # Find opening brace before feature_title
                    brace_start = result.rfind('{', 0, start)
                    if brace_start >= 0:
                        # Find matching closing brace
                        depth = 0
                        for i, c in enumerate(result[brace_start:]):
                            if c == '{':
                                depth += 1
                            elif c == '}':
                                depth -= 1
                                if depth == 0:
                                    json_str = result[brace_start:brace_start + i + 1]
                                    self.logger.info(f"Extracted JSON via brace matching: {json_str[:300]}...")
                                    return json.loads(json_str)
            except Exception as ex:
                self.logger.warning(f"Failed fallback JSON extraction: {ex}")

        return None

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

    def discover_for_repo(self, repo: Dict) -> int:
        """Run product analysis for a single repository."""
        repo_name = repo['name']
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"ANALYZING: {repo_name}")
        self.logger.info(f"{'='*60}")

        # Check feature backlog size
        feature_count = self._get_feature_backlog_count(repo_name)
        self.logger.info(f"Current feature backlog: {feature_count} issues")

        if feature_count >= self.FEATURE_BACKLOG_THRESHOLD:
            self.logger.info(f"Feature backlog full (>= {self.FEATURE_BACKLOG_THRESHOLD}), skipping")
            return 0

        # Clone/update repo
        repo_path = self._clone_or_update_repo(repo)
        if not repo_path:
            self.logger.error(f"Could not access repo: {repo_name}")
            return 0

        # Read project context
        claude_md = self._read_claude_md(repo_path)
        if not claude_md:
            self.logger.warning(f"No CLAUDE.md found for {repo_name}")

        # Get existing issues and PRs to avoid duplicates
        existing_titles = self._get_existing_issue_titles(repo_name)
        recent_prs = self._get_recent_prs(repo_name)
        all_existing = existing_titles + recent_prs

        issues_created = 0

        # Analyze with Claude
        self.logger.info("Analyzing product with Claude...")
        feature = self._analyze_with_claude(repo, claude_md)

        if not feature:
            self.logger.warning("No feature suggestion from Claude")
            return 0

        self.logger.info(f"Feature parsed: {json.dumps(feature, indent=2)[:500]}")

        title = feature.get('feature_title', '')
        if not title:
            self.logger.warning("No feature title in response")
            return 0

        self.logger.info(f"Feature title: {title}")

        # Check for duplicate
        title_lower = title.lower()
        is_duplicate = any(
            existing in title_lower or title_lower in existing
            for existing in all_existing
        )

        if is_duplicate:
            self.logger.info(f"Skipping potential duplicate: {title}")
            return 0

        # Check value score
        value_score = feature.get('value_score', 5)
        self.logger.info(f"Value score: {value_score}")
        if value_score < 6:
            self.logger.info(f"Skipping low-value feature (score {value_score}): {title}")
            return 0

        # Create the issue
        body = self._generate_issue_body(feature, repo_name)
        if self._create_issue(repo_name, title, body):
            issues_created += 1

        self.logger.info(f"Created {issues_created} feature issues for {repo_name}")
        return issues_created

    def run(self):
        """Run product analysis for all repositories."""
        if not self.enabled:
            self.logger.info("Product Manager is disabled in config. Skipping.")
            return 0

        self.logger.info(f"\n{'#'*60}")
        self.logger.info("BARBOSSA PRODUCT MANAGER RUN")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'#'*60}\n")

        total_issues = 0
        for repo in self.repositories:
            try:
                issues = self.discover_for_repo(repo)
                total_issues += issues
            except Exception as e:
                self.logger.error(f"Error analyzing {repo['name']}: {e}")

        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"PRODUCT ANALYSIS COMPLETE: {total_issues} feature issues created")
        self.logger.info(f"{'#'*60}\n")


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
