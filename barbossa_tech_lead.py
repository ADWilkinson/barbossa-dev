#!/usr/bin/env python3
"""
Barbossa Tech Lead v1.0 - PR Review & Governance Agent
A strict, critical reviewer that manages PRs created by the Senior Engineer.
Runs every 5 hours to review, merge, or close PRs with full authority.
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid


class BarbossaTechLead:
    """
    Tech Lead agent that reviews PRs with extreme scrutiny.
    Has authority to merge or close PRs based on objective criteria.
    """

    VERSION = "1.1.0"
    ROLE = "tech_lead"

    # Review criteria thresholds
    MIN_LINES_FOR_TESTS = 50  # PRs with >50 lines changed should have tests
    MAX_FILES_PER_PR = 15     # More than this is likely scope creep

    def __init__(self, work_dir: Optional[Path] = None):
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-engineer'
        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.decisions_file = self.work_dir / 'tech_lead_decisions.json'
        self.config_file = self.work_dir / 'config' / 'repositories.json'
        self.pending_feedback_file = self.work_dir / 'pending_feedback.json'

        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self._setup_logging()
        self.config = self._load_config()
        self.repositories = self.config.get('repositories', [])
        self.owner = self.config.get('owner', 'ADWilkinson')

        self.logger.info("=" * 70)
        self.logger.info(f"BARBOSSA TECH LEAD v{self.VERSION}")
        self.logger.info("Role: PR Review & Governance")
        self.logger.info("Authority: MERGE / CLOSE / REQUEST CHANGES")
        self.logger.info(f"Repositories: {len(self.repositories)}")
        self.logger.info("=" * 70)

    def _setup_logging(self):
        """Configure logging"""
        log_file = self.logs_dir / f"tech_lead_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger('tech_lead')
        self.logger.info(f"Logging to: {log_file}")

    def _load_config(self) -> Dict:
        """Load repository configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        self.logger.error(f"Config file not found: {self.config_file}")
        return {'repositories': []}

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"tl-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"

    def _save_decision(self, decision: Dict):
        """Save a decision to the decisions file"""
        decisions = []
        if self.decisions_file.exists():
            try:
                with open(self.decisions_file, 'r') as f:
                    decisions = json.load(f)
            except:
                decisions = []

        decisions.insert(0, decision)
        decisions = decisions[:200]  # Keep last 200 decisions

        with open(self.decisions_file, 'w') as f:
            json.dump(decisions, f, indent=2)

    def _add_pending_feedback(self, repo_name: str, pr_number: int, feedback: str):
        """Track a PR that needs Senior Engineer attention"""
        pending = {}
        if self.pending_feedback_file.exists():
            try:
                with open(self.pending_feedback_file, 'r') as f:
                    pending = json.load(f)
            except:
                pending = {}

        key = f"{repo_name}/{pr_number}"
        pending[key] = {
            'repo': repo_name,
            'pr_number': pr_number,
            'feedback': feedback,
            'timestamp': datetime.now().isoformat(),
            'addressed': False
        }

        with open(self.pending_feedback_file, 'w') as f:
            json.dump(pending, f, indent=2)
        self.logger.info(f"Saved pending feedback for {key}")

    def _remove_pending_feedback(self, repo_name: str, pr_number: int):
        """Remove a PR from pending feedback (after merge/close)"""
        if not self.pending_feedback_file.exists():
            return

        try:
            with open(self.pending_feedback_file, 'r') as f:
                pending = json.load(f)

            key = f"{repo_name}/{pr_number}"
            if key in pending:
                del pending[key]
                with open(self.pending_feedback_file, 'w') as f:
                    json.dump(pending, f, indent=2)
                self.logger.info(f"Removed pending feedback for {key}")
        except Exception as e:
            self.logger.warning(f"Could not remove pending feedback: {e}")

    def _get_open_prs(self, repo_name: str) -> List[Dict]:
        """Get all open PRs for a repository"""
        try:
            result = subprocess.run(
                f"gh pr list --repo {self.owner}/{repo_name} --state open "
                f"--json number,title,headRefName,body,additions,deletions,changedFiles,author,createdAt,updatedAt,url,labels,reviews,reviewDecision "
                f"--limit 50",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except Exception as e:
            self.logger.warning(f"Could not fetch PRs for {repo_name}: {e}")
        return []

    def _get_pr_diff(self, repo_name: str, pr_number: int) -> str:
        """Get the diff for a PR"""
        try:
            result = subprocess.run(
                f"gh pr diff {pr_number} --repo {self.owner}/{repo_name}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return result.stdout
        except Exception as e:
            self.logger.warning(f"Could not get diff for PR #{pr_number}: {e}")
        return ""

    def _get_pr_checks(self, repo_name: str, pr_number: int) -> Dict:
        """Get CI check status for a PR"""
        try:
            result = subprocess.run(
                f"gh pr checks {pr_number} --repo {self.owner}/{repo_name} --json name,status,conclusion",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                checks = json.loads(result.stdout)
                return {
                    'checks': checks,
                    'all_passing': all(c.get('conclusion') == 'success' for c in checks if c.get('status') == 'completed'),
                    'any_failing': any(c.get('conclusion') == 'failure' for c in checks),
                    'pending': any(c.get('status') != 'completed' for c in checks)
                }
        except Exception as e:
            self.logger.warning(f"Could not get checks for PR #{pr_number}: {e}")
        return {'checks': [], 'all_passing': False, 'any_failing': False, 'pending': True}

    def _get_pr_files(self, repo_name: str, pr_number: int) -> List[Dict]:
        """Get list of files changed in a PR"""
        try:
            result = subprocess.run(
                f"gh pr view {pr_number} --repo {self.owner}/{repo_name} --json files",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return data.get('files', [])
        except Exception as e:
            self.logger.warning(f"Could not get files for PR #{pr_number}: {e}")
        return []

    def _create_review_prompt(self, repo: Dict, pr: Dict, diff: str, checks: Dict, files: List[Dict]) -> str:
        """Create the Claude prompt for reviewing a PR"""
        session_id = self._generate_session_id()

        # Truncate diff if too long
        if len(diff) > 50000:
            diff = diff[:25000] + "\n\n... [DIFF TRUNCATED - TOO LARGE] ...\n\n" + diff[-25000:]

        file_list = "\n".join([f"  - {f.get('path', 'unknown')} (+{f.get('additions', 0)}/-{f.get('deletions', 0)})" for f in files[:30]])
        if len(files) > 30:
            file_list += f"\n  ... and {len(files) - 30} more files"

        checks_status = "PASSING" if checks.get('all_passing') else ("FAILING" if checks.get('any_failing') else "PENDING")

        return f"""You are the Barbossa Tech Lead - a strict, critical code reviewer with full authority to MERGE or CLOSE pull requests.

================================================================================
SESSION METADATA
================================================================================
Session ID: {session_id}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Repository: {repo['name']}
Role: TECH LEAD - PR Governance

================================================================================
PULL REQUEST DETAILS
================================================================================
PR #{pr['number']}: {pr['title']}
URL: {pr['url']}
Author: {pr.get('author', {}).get('login', 'unknown')}
Created: {pr.get('createdAt', 'unknown')}
Branch: {pr.get('headRefName', 'unknown')}

Lines Added: {pr.get('additions', 0)}
Lines Deleted: {pr.get('deletions', 0)}
Files Changed: {pr.get('changedFiles', 0)}

CI Status: {checks_status}

================================================================================
FILES CHANGED
================================================================================
{file_list}

================================================================================
PR DESCRIPTION
================================================================================
{pr.get('body', 'No description provided.')}

================================================================================
DIFF (CODE CHANGES)
================================================================================
{diff}

================================================================================
YOUR CRITICAL REVIEW CRITERIA
================================================================================
You must evaluate this PR with EXTREME SCRUTINY. Be harsh but fair.
Your job is to PROTECT the codebase from bloat, low-value changes, and bad UX.
When in doubt, CLOSE. It's better to reject 10 mediocre PRs than merge 1 bad one.

MANDATORY REJECTION CRITERIA (auto-close if ANY are true):
1. CI checks are FAILING - never merge broken code
2. No tests added for code changes >50 lines that affect logic
3. PR touches >15 files - likely scope creep, needs to be split
4. Changes do not match PR title/description - unclear intent
5. Introduces obvious bugs, security issues, or anti-patterns
6. Only adds comments/docs without meaningful code changes
7. Duplicate of existing functionality
8. Changes "do not touch" areas without strong justification
9. TEST-ONLY PR that doesn't accompany a feature or fix (LOW VALUE)
10. Tests for dead code (code that isn't imported/used anywhere)

TEST-ONLY PR POLICY (STRICT - CLOSE these PRs):
- PRs that ONLY add tests with no feature/fix = CLOSE (not request changes)
- Tests for code that isn't imported/used anywhere = CLOSE immediately
- "Comprehensive test coverage" PRs are busywork = CLOSE
- The codebase has enough tests - we need features and fixes

When you see a test-only PR, your decision should be CLOSE with reasoning:
"Closing: Test-only PRs do not add user value. Focus on features and fixes."

================================================================================
FEATURE VALUE ASSESSMENT (BE BRUTALLY CRITICAL)
================================================================================
Ask yourself: "Would a REAL USER actually benefit from this?"

CLOSE if the feature:
- Is something nobody asked for or needs
- Adds complexity without clear user benefit
- Is a "nice to have" that clutters the interface
- Solves a problem that doesn't really exist
- Is over-engineered for the use case
- Adds configuration/options most users won't use
- Is developer-focused busy work disguised as a feature

Features must pass the "so what?" test:
- "Added a loading spinner" - So what? Does it improve UX significantly?
- "Added error handling" - So what? Were errors actually happening?
- "Refactored X for cleanliness" - So what? Was it actually a problem?
- "Added accessibility" - Good, but is it done well or just checkbox compliance?

Be especially skeptical of:
- "Polish" PRs that touch many small things
- Features that add UI elements without clear purpose
- Abstractions that don't simplify anything
- "Improvements" that are really just changes

================================================================================
UI/UX QUALITY GATE (STRICT - DESIGN MATTERS)
================================================================================
These apps have carefully designed UIs. PRs that harm the visual design = CLOSE.

CLOSE immediately if the PR:
- Makes the UI look CRAMPED or cluttered
- Breaks the established visual rhythm/spacing
- Uses colors that don't match the design system
- Adds elements that feel out of place or jarring
- Creates inconsistent styling vs existing components
- Ignores the brand rules (see project context below)
- Adds too many UI elements to one view
- Makes the interface feel "busy" or overwhelming

For peerlytics (terminal aesthetic):
- Square corners ONLY - any border-radius = CLOSE
- Dark mode must use exact brand colors
- Monospace/terminal feel must be preserved

For usdctofiat (Davy Jones nautical theme):
- Canvas/charcoal color palette only
- Morion serif for headings, Wigrum sans for body
- Warm, minimal, nautical feel must be preserved

If a feature adds value but harms UI quality = REQUEST_CHANGES or CLOSE.
Never sacrifice design quality for functionality.

================================================================================
BLOAT DETECTION (ZERO TOLERANCE)
================================================================================
Code bloat kills projects. Be ruthless.

CLOSE if:
- Unnecessary abstractions (wrapper for wrapper's sake)
- Helper functions that are used once
- Config options nobody will change
- "Future-proofing" for scenarios that won't happen
- Dead code or commented-out code
- Excessive dependencies for simple tasks
- PR does more than ONE focused thing
- Code that could be 50% shorter with same functionality

The best code is code that doesn't exist.
If something can be removed, it should be.

================================================================================
BACKEND/API FEATURE REQUIREMENTS
================================================================================
Backend features (API endpoints, services, data processing) require PROOF of testing.

REQUEST_CHANGES or CLOSE if backend PR:
- Has no evidence of local testing (curl commands, test output, logs)
- Adds an endpoint without showing it actually works
- Modifies data logic without demonstrating correctness
- Has no error handling for realistic failure scenarios
- Doesn't show what happens with edge cases (empty data, nulls, etc.)

The PR description or commits MUST show:
- Actual curl/httpie commands that were run
- Response output proving the feature works
- Error responses for invalid inputs
- Performance is acceptable (no obvious N+1 queries, etc.)

"Trust me, it works" is NOT acceptable. Show the receipts.

================================================================================
PROJECT CONTEXT
================================================================================
{repo.get('description', 'No description')}

DO NOT TOUCH areas:
{chr(10).join(['- ' + item for item in repo.get('do_not_touch', [])])}

================================================================================
YOUR DECISION
================================================================================
After careful analysis, you MUST make ONE of these decisions:

1. **MERGE** - Only if:
   - CI passes
   - Adds clear, genuine value
   - Code quality is high
   - Changes are focused and appropriate
   - Tests exist for non-trivial changes

2. **CLOSE** - If:
   - PR is fundamentally flawed
   - Adds bloat without value
   - Duplicates existing work
   - Violates core architecture
   - Cannot be salvaged with minor fixes

3. **REQUEST_CHANGES** - If:
   - PR has potential but needs fixes
   - Missing tests for significant changes
   - Minor issues that author should address
   - Needs better documentation/description

================================================================================
OUTPUT FORMAT (REQUIRED)
================================================================================
You MUST output your decision in this EXACT format at the end:

```decision
DECISION: [MERGE|CLOSE|REQUEST_CHANGES]
REASONING: [2-3 sentence summary of why]
VALUE_SCORE: [1-10, where 10 is exceptional value]
QUALITY_SCORE: [1-10, where 10 is excellent quality]
BLOAT_RISK: [LOW|MEDIUM|HIGH]
```

IMPORTANT: Do NOT execute any gh commands yourself. Just provide your decision in the format above.
The system will handle executing the merge/close/comment commands automatically.

Be decisive. Be critical. Protect the codebase.
Begin your review now."""

    def _parse_decision(self, output: str) -> Optional[Dict]:
        """Parse the decision from Claude's output with robust pattern matching"""
        import re

        result = {
            'decision': None,
            'reasoning': 'No reasoning provided',
            'value_score': 5,
            'quality_score': 5,
            'bloat_risk': 'MEDIUM'
        }

        # Try multiple patterns to find the decision

        # Pattern 0: Try to find JSON block first (most reliable)
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{[^`]*"decision"[^`]*\})\s*```',
        ]
        for pattern in json_patterns:
            match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if 'decision' in data:
                        decision = data['decision'].upper().replace(' ', '_').replace('-', '_')
                        if decision in ['MERGE', 'CLOSE', 'REQUEST_CHANGES']:
                            result['decision'] = decision
                            result['reasoning'] = data.get('reasoning', data.get('reason', result['reasoning']))[:500]
                            if 'value_score' in data or 'value' in data:
                                result['value_score'] = min(10, max(1, int(data.get('value_score', data.get('value', 5)))))
                            if 'quality_score' in data or 'quality' in data:
                                result['quality_score'] = min(10, max(1, int(data.get('quality_score', data.get('quality', 5)))))
                            if 'bloat_risk' in data or 'bloat' in data:
                                risk = str(data.get('bloat_risk', data.get('bloat', 'MEDIUM'))).upper()
                                if risk in ['LOW', 'MEDIUM', 'HIGH']:
                                    result['bloat_risk'] = risk
                            return result
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

        # Pattern 1: ```decision block
        decision_match = re.search(r'```decision\s*(.*?)\s*```', output, re.DOTALL)
        if decision_match:
            block = decision_match.group(1)
            decision = re.search(r'DECISION:\s*(MERGE|CLOSE|REQUEST_CHANGES)', block, re.IGNORECASE)
            if decision:
                result['decision'] = decision.group(1).upper()

                reasoning = re.search(r'REASONING:\s*(.+?)(?=\n[A-Z_]+:|$)', block, re.DOTALL)
                if reasoning:
                    result['reasoning'] = reasoning.group(1).strip()

                value_score = re.search(r'VALUE_SCORE:\s*(\d+)', block)
                if value_score:
                    result['value_score'] = min(10, max(1, int(value_score.group(1))))

                quality_score = re.search(r'QUALITY_SCORE:\s*(\d+)', block)
                if quality_score:
                    result['quality_score'] = min(10, max(1, int(quality_score.group(1))))

                bloat_risk = re.search(r'BLOAT_RISK:\s*(LOW|MEDIUM|HIGH)', block, re.IGNORECASE)
                if bloat_risk:
                    result['bloat_risk'] = bloat_risk.group(1).upper()

                return result

        # Pattern 2: Look for "DECISION: MERGE" anywhere in output with many variations
        decision_patterns = [
            r'\*\*DECISION\*\*:\s*(MERGE|CLOSE|REQUEST_CHANGES)',  # **DECISION**: MERGE
            r'\*\*Decision\*\*:\s*(MERGE|CLOSE|REQUEST_CHANGES)',  # **Decision**: MERGE
            r'DECISION:\s*(MERGE|CLOSE|REQUEST_CHANGES)',          # DECISION: MERGE
            r'Decision:\s*(MERGE|CLOSE|REQUEST_CHANGES)',          # Decision: MERGE
            r'\bdecision\s*[=:]\s*(MERGE|CLOSE|REQUEST_CHANGES)\b',  # decision = MERGE
            r'\bdecision\s+(?:is\s+)?(?:to\s+)?(MERGE|CLOSE|REQUEST_CHANGES)\b',  # decision is to MERGE
            r'(?:will|should|recommend|going to)\s+(MERGE|CLOSE|REQUEST[_\s]?CHANGES)',  # will MERGE
            r'I(?:\'m| am| will)\s+(?:going to\s+)?(MERGE|CLOSE|REQUEST[_\s]?CHANGES)',  # I'm going to MERGE
            r'(?:verdict|action|outcome)[:\s]+\**(MERGE|CLOSE|REQUEST_CHANGES)\**',  # verdict: MERGE
            r'\*\*(MERGE|CLOSE|REQUEST_CHANGES)\*\*',  # **MERGE**
        ]

        for pattern in decision_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                decision = match.group(1).upper().replace(' ', '_').replace('-', '_')
                # Normalize REQUEST CHANGES variations
                if 'REQUEST' in decision and 'CHANGE' in decision:
                    decision = 'REQUEST_CHANGES'
                if decision in ['MERGE', 'CLOSE', 'REQUEST_CHANGES']:
                    result['decision'] = decision
                    break

        # Pattern 3: Look at the end of output for clear commands executed
        if not result['decision']:
            # Look for gh commands that were executed
            gh_patterns = [
                (r'gh pr merge', 'MERGE'),
                (r'gh pr close', 'CLOSE'),
                (r'gh pr review.*--request-changes', 'REQUEST_CHANGES'),
                (r'gh pr comment', 'REQUEST_CHANGES'),  # comments typically mean feedback
            ]
            for pattern, action in gh_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    result['decision'] = action
                    break

        # Pattern 4: Look for clear natural language indicators
        if not result['decision']:
            output_lower = output.lower()

            # Strong merge indicators
            merge_phrases = [
                'merging this pr', 'approve and merge', 'lgtm', 'looks good to merge',
                'ready to merge', 'approved for merge', 'this pr is approved',
                'merged successfully', 'proceeding to merge', 'will merge this'
            ]

            # Strong close indicators
            close_phrases = [
                'closing this pr', 'should be closed', 'recommend closing',
                'this pr should be rejected', 'rejecting this pr', 'will close',
                'does not add value', 'closing without merge'
            ]

            # Strong request changes indicators
            change_phrases = [
                'requesting changes', 'needs changes', 'changes requested',
                'please address', 'needs to be fixed', 'requires changes',
                'before this can be merged', 'cannot be merged as-is',
                'needs work', 'needs improvement'
            ]

            for phrase in merge_phrases:
                if phrase in output_lower:
                    result['decision'] = 'MERGE'
                    break

            if not result['decision']:
                for phrase in close_phrases:
                    if phrase in output_lower:
                        result['decision'] = 'CLOSE'
                        break

            if not result['decision']:
                for phrase in change_phrases:
                    if phrase in output_lower:
                        result['decision'] = 'REQUEST_CHANGES'
                        break

        # Extract reasoning from common patterns
        reasoning_patterns = [
            r'\*\*REASONING\*\*:\s*(.+?)(?=\n\*\*|\n```|$)',
            r'\*\*Reasoning\*\*:\s*(.+?)(?=\n\*\*|\n```|$)',
            r'REASONING:\s*(.+?)(?=\n[A-Z_]+:|$)',
            r'Reasoning:\s*(.+?)(?=\n[A-Z_]+:|$)',
            r'(?:^|\n)(?:because|reason|rationale|summary)[:\s]+(.+?)(?:\n\n|\n[A-Z]|$)',
            r'##\s*(?:Summary|Reasoning|Verdict)\s*\n(.+?)(?=\n##|\n```|$)',
        ]

        for pattern in reasoning_patterns:
            match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
            if match and len(match.group(1).strip()) > 10:
                result['reasoning'] = match.group(1).strip()[:500]
                break

        # If no reasoning found, try to extract a meaningful summary
        if result['reasoning'] == 'No reasoning provided' and result['decision']:
            # Look for any substantial paragraph that explains the decision
            paragraphs = re.split(r'\n\n+', output)
            for para in paragraphs:
                # Skip code blocks and short lines
                if '```' in para or len(para.strip()) < 50:
                    continue
                # Look for paragraphs that discuss the PR
                if any(word in para.lower() for word in ['pr ', 'pull request', 'code', 'changes', 'value', 'quality']):
                    result['reasoning'] = para.strip()[:500]
                    break

        # Extract scores with more patterns
        value_patterns = [
            r'VALUE[_\s]?SCORE:\s*(\d+)',
            r'\*\*Value[_\s]?Score\*\*:\s*(\d+)',
            r'value:\s*(\d+)\s*/\s*10',
            r'value\s+(\d+)/10',
            r'value[:\s]+(\d+)\s*(?:/10|out of 10)?',
        ]
        for pattern in value_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                result['value_score'] = min(10, max(1, int(match.group(1))))
                break

        quality_patterns = [
            r'QUALITY[_\s]?SCORE:\s*(\d+)',
            r'\*\*Quality[_\s]?Score\*\*:\s*(\d+)',
            r'quality:\s*(\d+)\s*/\s*10',
            r'quality\s+(\d+)/10',
            r'quality[:\s]+(\d+)\s*(?:/10|out of 10)?',
        ]
        for pattern in quality_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                result['quality_score'] = min(10, max(1, int(match.group(1))))
                break

        bloat_patterns = [
            r'BLOAT[_\s]?RISK:\s*(LOW|MEDIUM|HIGH)',
            r'\*\*Bloat[_\s]?Risk\*\*:\s*(LOW|MEDIUM|HIGH)',
            r'bloat[_\s]?risk[:\s]+(LOW|MEDIUM|HIGH)',
        ]
        for pattern in bloat_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                result['bloat_risk'] = match.group(1).upper()
                break

        if result['decision']:
            return result
        return None

    def _execute_decision(self, repo_name: str, pr: Dict, decision: Dict) -> bool:
        """Execute the merge/close/request-changes decision"""
        pr_number = pr['number']
        action = decision['decision']

        self.logger.info(f"Executing decision: {action} for PR #{pr_number}")

        try:
            if action == 'MERGE':
                # Try to squash merge and delete branch
                # If it fails due to conflicts, that's fine - Senior Engineer will fix them
                cmd = f"gh pr merge {pr_number} --repo {self.owner}/{repo_name} --squash --delete-branch"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                success = result.returncode == 0
                if not success:
                    stderr = result.stderr.lower()
                    if 'merge conflict' in stderr or 'not mergeable' in stderr:
                        self.logger.warning(f"Merge blocked by conflicts - Senior Engineer will fix: {result.stderr}")
                        # Add a comment so we know we tried
                        comment_cmd = f'gh pr comment {pr_number} --repo {self.owner}/{repo_name} --body "Tech Lead approved for merge (Value: {decision.get("value_score", "?")}/10, Quality: {decision.get("quality_score", "?")}/10). Waiting for conflict resolution."'
                        subprocess.run(comment_cmd, shell=True, capture_output=True, text=True, timeout=30)
                        # Track this so Senior Engineer knows to fix conflicts
                        self._add_pending_feedback(repo_name, pr_number, "Approved but has merge conflicts - please rebase against main")
                    else:
                        self.logger.error(f"Merge failed: {result.stderr}")
                else:
                    self.logger.info(f"Successfully merged PR #{pr_number}")
                    # Remove from pending feedback tracking
                    self._remove_pending_feedback(repo_name, pr_number)
                return success

            elif action == 'CLOSE':
                # Close with comment
                reason = decision['reasoning'][:500]  # Limit comment length
                cmd = f'gh pr close {pr_number} --repo {self.owner}/{repo_name} --comment "Closed by Tech Lead Review: {reason}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                success = result.returncode == 0
                if not success:
                    self.logger.error(f"Close failed: {result.stderr}")
                else:
                    # Remove from pending feedback tracking
                    self._remove_pending_feedback(repo_name, pr_number)
                return success

            elif action == 'REQUEST_CHANGES':
                # Use PR comment instead of review (GitHub doesn't allow requesting changes on own PRs)
                feedback = decision['reasoning'][:1000].replace('"', "'").replace('`', "'")
                value_score = decision.get('value_score', '?')
                quality_score = decision.get('quality_score', '?')
                bloat_risk = decision.get('bloat_risk', '?')

                comment_body = f"""**Tech Lead Review - Changes Requested**

**Scores:** Value {value_score}/10 | Quality {quality_score}/10 | Bloat Risk: {bloat_risk}

**Feedback:**
{feedback}

---
_Senior Engineer: Please address the above feedback and push updates._"""

                # Write comment to temp file to avoid shell escaping issues
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                    f.write(comment_body)
                    temp_file = f.name

                try:
                    cmd = f'gh pr comment {pr_number} --repo {self.owner}/{repo_name} --body-file "{temp_file}"'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                    success = result.returncode == 0
                    if not success:
                        self.logger.error(f"Comment failed: {result.stderr}")
                    else:
                        self.logger.info(f"Posted feedback comment on PR #{pr_number}")
                        # Track this so Senior Engineer knows to address it
                        self._add_pending_feedback(repo_name, pr_number, feedback)
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                return success

        except Exception as e:
            self.logger.error(f"Error executing decision: {e}")
            return False

        return False

    def review_pr(self, repo: Dict, pr: Dict) -> Dict:
        """Review a single PR and return the decision"""
        repo_name = repo['name']
        pr_number = pr['number']
        session_id = self._generate_session_id()

        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"REVIEWING: {repo_name} PR #{pr_number}")
        self.logger.info(f"Title: {pr['title']}")
        self.logger.info(f"Session: {session_id}")
        self.logger.info(f"{'='*70}\n")

        # Gather PR data
        diff = self._get_pr_diff(repo_name, pr_number)
        checks = self._get_pr_checks(repo_name, pr_number)
        files = self._get_pr_files(repo_name, pr_number)

        # Quick rejection checks (before Claude review)
        quick_reject = None

        if checks.get('any_failing'):
            quick_reject = {
                'decision': 'REQUEST_CHANGES',
                'reasoning': 'CI checks are failing. Fix the failing checks before this PR can be reviewed.',
                'value_score': 0,
                'quality_score': 0,
                'bloat_risk': 'HIGH',
                'auto_rejected': True
            }
            self.logger.info("AUTO: Requesting changes - CI failing")

        if not quick_reject and pr.get('changedFiles', 0) > self.MAX_FILES_PER_PR:
            quick_reject = {
                'decision': 'REQUEST_CHANGES',
                'reasoning': f'PR touches {pr.get("changedFiles")} files which exceeds the limit of {self.MAX_FILES_PER_PR}. Please split this into smaller, focused PRs.',
                'value_score': 3,
                'quality_score': 2,
                'bloat_risk': 'HIGH',
                'auto_rejected': True
            }
            self.logger.info(f"AUTO: Requesting changes - Too many files ({pr.get('changedFiles')})")

        # Auto-close test-only PRs (they don't add user value)
        if not quick_reject:
            pr_title = pr.get('title', '').lower().strip()
            is_test_only = (
                pr_title.startswith('test:') or
                pr_title.startswith('test(') or
                'add test' in pr_title and 'feat' not in pr_title and 'fix' not in pr_title
            )
            if is_test_only:
                quick_reject = {
                    'decision': 'CLOSE',
                    'reasoning': 'Test-only PRs are deprioritized per policy. Tests should accompany features or fixes, not be standalone. Focus engineering effort on user-facing improvements.',
                    'value_score': 2,
                    'quality_score': 5,
                    'bloat_risk': 'LOW',
                    'auto_rejected': True
                }
                self.logger.info(f"AUTO: Closing test-only PR - '{pr.get('title')}'")

        if quick_reject:
            # Execute the auto-decision
            self._execute_decision(repo_name, pr, quick_reject)

            decision_record = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'repository': repo_name,
                'pr_number': pr_number,
                'pr_title': pr['title'],
                'pr_url': pr['url'],
                'pr_author': pr.get('author', {}).get('login', 'unknown'),
                'decision': quick_reject['decision'],
                'reasoning': quick_reject['reasoning'],
                'value_score': quick_reject['value_score'],
                'quality_score': quick_reject['quality_score'],
                'bloat_risk': quick_reject['bloat_risk'],
                'auto_rejected': True,
                'executed': True
            }
            self._save_decision(decision_record)
            return decision_record

        # Create prompt for Claude
        prompt = self._create_review_prompt(repo, pr, diff, checks, files)

        # Save prompt
        prompt_file = self.work_dir / f'prompt_tech_lead_{repo_name}_{pr_number}.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        # Output file
        output_file = self.logs_dir / f"tech_lead_{repo_name}_{pr_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        self.logger.info(f"Invoking Claude for review...")

        # Run Claude
        cmd = f"cat {prompt_file} | claude --dangerously-skip-permissions -p --model opus > {output_file} 2>&1"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.work_dir),
                timeout=900  # 15 minute timeout per PR review
            )

            # Read output and parse decision
            output = ""
            if output_file.exists():
                output = output_file.read_text()

            decision = self._parse_decision(output)

            if not decision:
                self.logger.warning("Could not parse decision from Claude output")
                decision = {
                    'decision': 'REQUEST_CHANGES',
                    'reasoning': 'Tech Lead review was inconclusive. Manual review required.',
                    'value_score': 5,
                    'quality_score': 5,
                    'bloat_risk': 'MEDIUM'
                }

            # Execute the decision
            executed = self._execute_decision(repo_name, pr, decision)

            decision_record = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'repository': repo_name,
                'pr_number': pr_number,
                'pr_title': pr['title'],
                'pr_url': pr['url'],
                'pr_author': pr.get('author', {}).get('login', 'unknown'),
                'additions': pr.get('additions', 0),
                'deletions': pr.get('deletions', 0),
                'files_changed': pr.get('changedFiles', 0),
                'decision': decision['decision'],
                'reasoning': decision['reasoning'],
                'value_score': decision['value_score'],
                'quality_score': decision['quality_score'],
                'bloat_risk': decision['bloat_risk'],
                'auto_rejected': False,
                'executed': executed,
                'output_file': str(output_file)
            }

            self._save_decision(decision_record)

            self.logger.info(f"DECISION: {decision['decision']}")
            self.logger.info(f"REASONING: {decision['reasoning']}")
            self.logger.info(f"VALUE: {decision['value_score']}/10, QUALITY: {decision['quality_score']}/10")
            self.logger.info(f"EXECUTED: {executed}")

            return decision_record

        except subprocess.TimeoutExpired:
            self.logger.error("Claude timed out during review")
            return {
                'session_id': session_id,
                'repository': repo_name,
                'pr_number': pr_number,
                'decision': 'TIMEOUT',
                'executed': False
            }
        except Exception as e:
            self.logger.error(f"Error during review: {e}")
            return {
                'session_id': session_id,
                'repository': repo_name,
                'pr_number': pr_number,
                'decision': 'ERROR',
                'error': str(e),
                'executed': False
            }

    def _cleanup_stale_prs(self, repo_name: str, prs: List[Dict]) -> List[Dict]:
        """Auto-close PRs that have been stale (in conflict) for too long"""
        from datetime import timedelta
        STALE_DAYS = 5  # Close PRs that have been in conflict for 5+ days

        cleaned = []
        remaining = []

        for pr in prs:
            created_at = pr.get('createdAt', '')
            try:
                # Parse ISO date
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                age_days = (datetime.now(created_date.tzinfo) - created_date).days
            except:
                age_days = 0

            # Check if PR is barbossa-created and old
            branch = pr.get('headRefName', '')
            is_barbossa_pr = branch.startswith('barbossa/')

            if is_barbossa_pr and age_days >= STALE_DAYS:
                # Auto-close stale barbossa PRs
                self.logger.info(f"AUTO-CLOSING stale PR #{pr['number']} ({age_days} days old): {pr['title']}")
                try:
                    cmd = f'gh pr close {pr["number"]} --repo {self.owner}/{repo_name} --comment "Auto-closed by Tech Lead: PR has been stale for {age_days} days. If this work is still needed, please create a fresh PR from the latest main branch."'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        cleaned.append(pr)
                        self._save_decision({
                            'timestamp': datetime.now().isoformat(),
                            'repository': repo_name,
                            'pr_number': pr['number'],
                            'pr_title': pr['title'],
                            'decision': 'CLOSE',
                            'reasoning': f'Auto-closed: PR stale for {age_days} days',
                            'auto_closed': True,
                            'executed': True
                        })
                        continue
                except Exception as e:
                    self.logger.error(f"Failed to auto-close PR #{pr['number']}: {e}")

            remaining.append(pr)

        if cleaned:
            self.logger.info(f"Auto-closed {len(cleaned)} stale PRs")

        return remaining

    def run(self):
        """Run the Tech Lead review process"""
        self.logger.info(f"\n{'#'*70}")
        self.logger.info("BARBOSSA TECH LEAD - PR REVIEW SESSION")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'#'*70}\n")

        all_results = []

        for repo in self.repositories:
            repo_name = repo['name']
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Repository: {repo_name}")
            self.logger.info(f"{'='*50}")

            open_prs = self._get_open_prs(repo_name)

            if not open_prs:
                self.logger.info(f"No open PRs in {repo_name}")
                continue

            # First, clean up any stale PRs
            open_prs = self._cleanup_stale_prs(repo_name, open_prs)

            if not open_prs:
                self.logger.info(f"No remaining open PRs in {repo_name} after cleanup")
                continue

            self.logger.info(f"Found {len(open_prs)} open PRs")

            # Load pending feedback to skip PRs already awaiting fixes
            pending_feedback = {}
            if self.pending_feedback_file.exists():
                try:
                    with open(self.pending_feedback_file, 'r') as f:
                        pending_feedback = json.load(f)
                except:
                    pending_feedback = {}

            # Review each PR (skip those with pending feedback unless updated)
            for pr in open_prs:
                pr_key = f"{repo_name}/{pr['number']}"

                # Check if we already requested changes
                if pr_key in pending_feedback and not pending_feedback[pr_key].get('addressed', False):
                    feedback_time = pending_feedback[pr_key].get('timestamp', '')
                    pr_updated = pr.get('updatedAt', '')

                    # If PR was updated AFTER feedback was posted, Senior Engineer likely addressed it
                    # Re-review in that case
                    if feedback_time and pr_updated and pr_updated > feedback_time:
                        self.logger.info(f"RE-REVIEW PR #{pr['number']} - updated since feedback was posted")
                        # Clear the pending feedback since we're re-reviewing
                        self._remove_pending_feedback(repo_name, pr['number'])
                    else:
                        self.logger.info(f"SKIP PR #{pr['number']} - pending feedback, waiting for Senior Engineer")
                        continue

                result = self.review_pr(repo, pr)
                all_results.append(result)
                self.logger.info(f"Completed review of PR #{pr['number']}")

        # Summary
        self.logger.info(f"\n{'#'*70}")
        self.logger.info("TECH LEAD SESSION SUMMARY")
        self.logger.info(f"{'#'*70}")

        merged = sum(1 for r in all_results if r.get('decision') == 'MERGE' and r.get('executed'))
        closed = sum(1 for r in all_results if r.get('decision') == 'CLOSE' and r.get('executed'))
        changes_requested = sum(1 for r in all_results if r.get('decision') == 'REQUEST_CHANGES' and r.get('executed'))

        self.logger.info(f"PRs Reviewed: {len(all_results)}")
        self.logger.info(f"Merged: {merged}")
        self.logger.info(f"Closed: {closed}")
        self.logger.info(f"Changes Requested: {changes_requested}")
        self.logger.info(f"{'#'*70}\n")

        return all_results

    def status(self):
        """Show current status and recent decisions"""
        print(f"\nBarbossa Tech Lead v{self.VERSION} - Status")
        print("=" * 50)

        print(f"\nRepositories ({len(self.repositories)}):")
        for repo in self.repositories:
            prs = self._get_open_prs(repo['name'])
            print(f"  - {repo['name']}: {len(prs)} open PRs")

        # Show recent decisions
        if self.decisions_file.exists():
            with open(self.decisions_file, 'r') as f:
                decisions = json.load(f)

            print(f"\nRecent Decisions (last 10):")
            for d in decisions[:10]:
                icon = {'MERGE': 'MERGED', 'CLOSE': 'CLOSED', 'REQUEST_CHANGES': 'CHANGES'}.get(d.get('decision', '?'), '?')
                print(f"  [{icon}] {d.get('repository')}/#{d.get('pr_number')} - {d.get('pr_title', 'Unknown')[:40]}")
                print(f"         Value: {d.get('value_score', '?')}/10, Quality: {d.get('quality_score', '?')}/10")

        print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Barbossa Tech Lead v1.0 - PR Review & Governance'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show status and recent decisions'
    )
    parser.add_argument(
        '--repo',
        help='Review PRs for specific repository only'
    )

    args = parser.parse_args()

    tech_lead = BarbossaTechLead()

    if args.status:
        tech_lead.status()
    else:
        tech_lead.run()


if __name__ == "__main__":
    main()
