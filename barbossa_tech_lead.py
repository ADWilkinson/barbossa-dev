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

    VERSION = "1.0.0"
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

    def _get_open_prs(self, repo_name: str) -> List[Dict]:
        """Get all open PRs for a repository"""
        try:
            result = subprocess.run(
                f"gh pr list --repo {self.owner}/{repo_name} --state open "
                f"--json number,title,headRefName,body,additions,deletions,changedFiles,author,createdAt,url,labels,reviews,reviewDecision "
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

MANDATORY REJECTION CRITERIA (auto-close if ANY are true):
1. CI checks are FAILING - never merge broken code
2. No tests added for code changes >50 lines that affect logic
3. PR touches >15 files - likely scope creep, needs to be split
4. Changes do not match PR title/description - unclear intent
5. Introduces obvious bugs, security issues, or anti-patterns
6. Only adds comments/docs without meaningful code changes
7. Duplicate of existing functionality
8. Changes "do not touch" areas without strong justification

VALUE ASSESSMENT (be brutally honest):
- Does this add GENUINE user or developer value?
- Is this solving a real problem or just busywork?
- Is this the SIMPLEST solution to the problem?
- Could this be done better with less code?
- Does this follow existing patterns in the codebase?
- Is there unnecessary complexity or over-engineering?

BLOAT DETECTION:
- Are there unnecessary abstractions?
- Are there files/functions that shouldn't exist?
- Is there dead code or commented-out code?
- Are there excessive dependencies added?
- Is the PR doing more than one thing?

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

If MERGE: Execute `gh pr merge {pr['number']} --repo {self.owner}/{repo['name']} --squash --delete-branch`
If CLOSE: Execute `gh pr close {pr['number']} --repo {self.owner}/{repo['name']} --comment "Closed by Tech Lead: [reason]"`
If REQUEST_CHANGES: Execute `gh pr review {pr['number']} --repo {self.owner}/{repo['name']} --request-changes --body "[specific feedback]"`

Be decisive. Be critical. Protect the codebase.
Begin your review now."""

    def _parse_decision(self, output: str) -> Optional[Dict]:
        """Parse the decision from Claude's output"""
        import re

        # Look for decision block
        decision_match = re.search(r'```decision\s*(.*?)\s*```', output, re.DOTALL)
        if not decision_match:
            # Try without code block
            decision_match = re.search(r'DECISION:\s*(MERGE|CLOSE|REQUEST_CHANGES)', output, re.IGNORECASE)
            if decision_match:
                decision = decision_match.group(1).upper()
                return {
                    'decision': decision,
                    'reasoning': 'Parsed from output',
                    'value_score': 5,
                    'quality_score': 5,
                    'bloat_risk': 'MEDIUM'
                }
            return None

        block = decision_match.group(1)

        decision = re.search(r'DECISION:\s*(MERGE|CLOSE|REQUEST_CHANGES)', block, re.IGNORECASE)
        reasoning = re.search(r'REASONING:\s*(.+?)(?=\n[A-Z_]+:|$)', block, re.DOTALL)
        value_score = re.search(r'VALUE_SCORE:\s*(\d+)', block)
        quality_score = re.search(r'QUALITY_SCORE:\s*(\d+)', block)
        bloat_risk = re.search(r'BLOAT_RISK:\s*(LOW|MEDIUM|HIGH)', block, re.IGNORECASE)

        if not decision:
            return None

        return {
            'decision': decision.group(1).upper(),
            'reasoning': reasoning.group(1).strip() if reasoning else 'No reasoning provided',
            'value_score': int(value_score.group(1)) if value_score else 5,
            'quality_score': int(quality_score.group(1)) if quality_score else 5,
            'bloat_risk': bloat_risk.group(1).upper() if bloat_risk else 'MEDIUM'
        }

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
                    else:
                        self.logger.error(f"Merge failed: {result.stderr}")
                else:
                    self.logger.info(f"Successfully merged PR #{pr_number}")
                return success

            elif action == 'CLOSE':
                # Close with comment
                reason = decision['reasoning'][:500]  # Limit comment length
                cmd = f'gh pr close {pr_number} --repo {self.owner}/{repo_name} --comment "Closed by Tech Lead Review: {reason}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                success = result.returncode == 0
                if not success:
                    self.logger.error(f"Close failed: {result.stderr}")
                return success

            elif action == 'REQUEST_CHANGES':
                # Use PR comment instead of review (GitHub doesn't allow requesting changes on own PRs)
                feedback = decision['reasoning'][:1000]
                value_score = decision.get('value_score', '?')
                quality_score = decision.get('quality_score', '?')
                bloat_risk = decision.get('bloat_risk', '?')

                comment_body = f"""**Tech Lead Review - Changes Requested**

**Scores:** Value {value_score}/10 | Quality {quality_score}/10 | Bloat Risk: {bloat_risk}

**Feedback:**
{feedback}

---
_Senior Engineer: Please address the above feedback and push updates._"""

                # Use gh pr comment instead of gh pr review (which fails on own PRs)
                cmd = f'gh pr comment {pr_number} --repo {self.owner}/{repo_name} --body "{comment_body}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                success = result.returncode == 0
                if not success:
                    self.logger.error(f"Comment failed: {result.stderr}")
                else:
                    self.logger.info(f"Posted feedback comment on PR #{pr_number}")
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
        cmd = f"claude --dangerously-skip-permissions --model opus < {prompt_file} > {output_file} 2>&1"

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

            self.logger.info(f"Found {len(open_prs)} open PRs")

            # Review each PR
            for pr in open_prs:
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
