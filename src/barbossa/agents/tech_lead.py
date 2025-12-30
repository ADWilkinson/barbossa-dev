#!/usr/bin/env python3
"""
Barbossa Tech Lead v5.8 - PR Review & Governance Agent
A strict, critical reviewer that manages PRs created by the Senior Engineer.
Runs hourly at :35 (after Engineer completes) for fast feedback loops.

Part of the Pipeline:
- Discovery (3x daily) → creates Issues
- Engineer (:00) → implements from backlog, creates PRs
- Tech Lead (:35) → reviews PRs, merges or requests changes
- Auditor (daily) → system health analysis

Prompts loaded locally from prompts/ directory.
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

# Local prompt loading and optional analytics/state tracking
from barbossa.utils.prompts import get_system_prompt
from barbossa.agents.firebase import (
    get_client,
    check_version,
    track_run_start,
    track_run_end
)


class BarbossaTechLead:
    """
    Tech Lead agent that reviews PRs with extreme scrutiny.
    Has authority to merge or close PRs based on objective criteria.
    Uses GitHub as the single source of truth - no file-based state.
    """

    VERSION = "1.6.3"  # Fixed auto_merge setting being ignored
    ROLE = "tech_lead"

    # Default review criteria (can be overridden in config)
    DEFAULT_MIN_LINES_FOR_TESTS = 50
    DEFAULT_AUTO_MERGE = True
    DEFAULT_STALE_DAYS = 5

    def __init__(self, work_dir: Optional[Path] = None):
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-dev'
        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.decisions_file = self.work_dir / 'tech_lead_decisions.json'
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

        # Load settings from config (with defaults)
        settings = self.config.get('settings', {}).get('tech_lead', {})
        self.enabled = settings.get('enabled', True)
        self.auto_merge = settings.get('auto_merge', self.DEFAULT_AUTO_MERGE)
        self.MIN_LINES_FOR_TESTS = settings.get('min_lines_for_tests', self.DEFAULT_MIN_LINES_FOR_TESTS)
        self.STALE_DAYS = settings.get('stale_days', self.DEFAULT_STALE_DAYS)

        self.logger.info("=" * 70)
        self.logger.info(f"BARBOSSA TECH LEAD v{self.VERSION}")
        self.logger.info("Role: PR Review & Governance")
        self.logger.info("Authority: MERGE / CLOSE / REQUEST CHANGES")
        self.logger.info(f"Repositories: {len(self.repositories)}")
        self.logger.info("Mode: GitHub as single source of truth")
        self.logger.info(f"Settings: min_lines_for_tests={self.MIN_LINES_FOR_TESTS}, stale_days={self.STALE_DAYS}")
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
        """Get all open PRs for a repository with full context"""
        try:
            result = subprocess.run(
                f"gh pr list --repo {self.owner}/{repo_name} --state open "
                f"--json number,title,headRefName,body,additions,deletions,changedFiles,author,createdAt,updatedAt,url,labels,reviews,reviewDecision,mergeable,mergeStateStatus "
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

    def _get_pr_comments(self, repo_name: str, pr_number: int) -> List[Dict]:
        """Get all comments on a PR - this is the conversation history"""
        try:
            result = subprocess.run(
                f"gh pr view {pr_number} --repo {self.owner}/{repo_name} --json comments",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return data.get('comments', [])
        except Exception as e:
            self.logger.warning(f"Could not fetch comments for PR #{pr_number}: {e}")
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
            # Use gh pr view --json statusCheckRollup instead of gh pr checks
            # because gh pr checks doesn't support --json flag
            result = subprocess.run(
                f"gh pr view {pr_number} --repo {self.owner}/{repo_name} --json statusCheckRollup",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                checks = data.get('statusCheckRollup', [])

                # Normalize check data - handle both CheckRun and StatusContext
                normalized_checks = []
                for check in checks:
                    check_type = check.get('__typename', 'Unknown')

                    if check_type == 'CheckRun':
                        # CheckRun uses 'status' and 'conclusion'
                        status = check.get('status', '').upper()
                        conclusion = check.get('conclusion', '').upper()
                        normalized_checks.append({
                            'name': check.get('name', 'Unknown'),
                            'status': status,
                            'conclusion': conclusion
                        })
                    elif check_type == 'StatusContext':
                        # StatusContext uses 'state' instead of conclusion
                        state = check.get('state', '').upper()
                        normalized_checks.append({
                            'name': check.get('context', 'Unknown'),
                            'status': 'COMPLETED' if state in ['SUCCESS', 'FAILURE', 'ERROR'] else 'PENDING',
                            'conclusion': state  # Use state as conclusion
                        })

                # Check if all passing: completed with SUCCESS, or NEUTRAL/SKIPPED are acceptable
                all_passing = all(
                    c['status'] == 'COMPLETED' and c['conclusion'] in ['SUCCESS', 'NEUTRAL', 'SKIPPED']
                    for c in normalized_checks
                ) if normalized_checks else False

                # Check if any failing: conclusion is FAILURE or ERROR
                any_failing = any(
                    c['conclusion'] in ['FAILURE', 'ERROR']
                    for c in normalized_checks
                )

                # Check if any pending: status is not COMPLETED
                pending = any(
                    c['status'] != 'COMPLETED'
                    for c in normalized_checks
                )

                return {
                    'checks': normalized_checks,
                    'all_passing': all_passing,
                    'any_failing': any_failing,
                    'pending': pending
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

    def _format_comments_for_prompt(self, comments: List[Dict]) -> str:
        """Format PR comments into a readable conversation history"""
        if not comments:
            return "(No comments on this PR)"

        formatted = []
        for comment in comments[-20:]:  # Last 20 comments max
            author = comment.get('author', {}).get('login', 'unknown')
            body = comment.get('body', '')[:1000]  # Truncate long comments
            created = comment.get('createdAt', '')[:10]  # Just the date

            # Skip Vercel deploy comments - they're noise
            if author == 'vercel' or '[vc]:' in body:
                continue

            formatted.append(f"[{created}] @{author}:\n{body}\n")

        return "\n---\n".join(formatted) if formatted else "(No relevant comments)"

    def _create_review_prompt(self, repo: Dict, pr: Dict, diff: str, checks: Dict, files: List[Dict], comments: List[Dict]) -> str:
        """Create the Claude prompt for reviewing a PR - fetched from Firebase.

        All prompts must come from Firebase cloud. No local fallback.
        """
        session_id = self._generate_session_id()

        # Truncate diff if too long
        if len(diff) > 50000:
            diff = diff[:25000] + "\n\n... [DIFF TRUNCATED - TOO LARGE] ...\n\n" + diff[-25000:]

        file_list = "\n".join([f"  - {f.get('path', 'unknown')} (+{f.get('additions', 0)}/-{f.get('deletions', 0)})" for f in files[:30]])
        if len(files) > 30:
            file_list += f"\n  ... and {len(files) - 30} more files"

        checks_status = "PASSING" if checks.get('all_passing') else ("FAILING" if checks.get('any_failing') else "PENDING")

        # Format the conversation history
        conversation = self._format_comments_for_prompt(comments)

        # Check merge status
        mergeable = pr.get('mergeable', 'UNKNOWN')
        merge_state = pr.get('mergeStateStatus', 'UNKNOWN')

        # Build do not touch section
        do_not_touch = repo.get('do_not_touch', [])
        dnt_section = "\n".join(['- ' + item for item in do_not_touch]) if do_not_touch else "(no restrictions)"

        # Load template from local file
        template = get_system_prompt("tech_lead")
        if not template:
            self.logger.error("Failed to load tech_lead prompt from prompts/tech_lead.txt")
            raise RuntimeError("Tech lead prompt file not found. Check prompts/ directory.")

        self.logger.info("Using local prompt template")
        # Replace template variables
        prompt = template
        prompt = prompt.replace("{{session_id}}", session_id)
        prompt = prompt.replace("{{timestamp}}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        prompt = prompt.replace("{{repo_name}}", repo['name'])
        prompt = prompt.replace("{{pr_number}}", str(pr['number']))
        prompt = prompt.replace("{{pr_title}}", pr['title'])
        prompt = prompt.replace("{{pr_url}}", pr['url'])
        prompt = prompt.replace("{{pr_author}}", pr.get('author', {}).get('login', 'unknown'))
        prompt = prompt.replace("{{pr_created}}", pr.get('createdAt', 'unknown'))
        prompt = prompt.replace("{{pr_updated}}", pr.get('updatedAt', 'unknown'))
        prompt = prompt.replace("{{pr_branch}}", pr.get('headRefName', 'unknown'))
        prompt = prompt.replace("{{pr_additions}}", str(pr.get('additions', 0)))
        prompt = prompt.replace("{{pr_deletions}}", str(pr.get('deletions', 0)))
        prompt = prompt.replace("{{pr_files_changed}}", str(pr.get('changedFiles', 0)))
        prompt = prompt.replace("{{checks_status}}", checks_status)
        prompt = prompt.replace("{{mergeable}}", str(mergeable))
        prompt = prompt.replace("{{merge_state}}", str(merge_state))
        prompt = prompt.replace("{{conversation}}", conversation)
        prompt = prompt.replace("{{file_list}}", file_list)
        prompt = prompt.replace("{{pr_body}}", pr.get('body', 'No description provided.'))
        prompt = prompt.replace("{{diff}}", diff)
        prompt = prompt.replace("{{repo_description}}", repo.get('description', 'No description'))
        prompt = prompt.replace("{{dnt_section}}", dnt_section)
        return prompt

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

        # Pattern 2: Look for "DECISION: MERGE" anywhere in output
        decision_patterns = [
            r'\*\*DECISION\*\*:\s*(MERGE|CLOSE|REQUEST_CHANGES)',
            r'\*\*Decision\*\*:\s*(MERGE|CLOSE|REQUEST_CHANGES)',
            r'DECISION:\s*(MERGE|CLOSE|REQUEST_CHANGES)',
            r'Decision:\s*(MERGE|CLOSE|REQUEST_CHANGES)',
            r'\bdecision\s*[=:]\s*(MERGE|CLOSE|REQUEST_CHANGES)\b',
            r'(?:will|should|recommend|going to)\s+(MERGE|CLOSE|REQUEST[_\s]?CHANGES)',
            r'\*\*(MERGE|MERGED|CLOSE|CLOSED|REQUEST_CHANGES)\*\*',  # Handle past tense too
            r'\|\s*\*\*(MERGE|MERGED|CLOSE|CLOSED|REQUEST[_\s]?CHANGES)\*\*',  # Table cell format
        ]

        for pattern in decision_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                decision = match.group(1).upper().replace(' ', '_').replace('-', '_')
                # Normalize past tense to present
                if decision == 'MERGED':
                    decision = 'MERGE'
                elif decision == 'CLOSED':
                    decision = 'CLOSE'
                if 'REQUEST' in decision and 'CHANGE' in decision:
                    decision = 'REQUEST_CHANGES'
                if decision in ['MERGE', 'CLOSE', 'REQUEST_CHANGES']:
                    result['decision'] = decision
                    break

        # Pattern 3: Natural language indicators
        if not result['decision']:
            output_lower = output.lower()

            merge_phrases = ['merging this pr', 'approve and merge', 'lgtm', 'ready to merge', 'will merge', '1 merged', 'pr merged', 'prs merged']
            close_phrases = ['closing this pr', 'should be closed', 'rejecting this pr', 'will close']
            change_phrases = ['requesting changes', 'needs changes', 'please address', 'needs to be fixed']

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

        # Extract reasoning
        reasoning_patterns = [
            r'REASONING:\s*(.+?)(?=\n[A-Z_]+:|$)',
            r'\*\*REASONING\*\*:\s*(.+?)(?=\n\*\*|\n```|$)',
            # Table format: | **MERGED** ✅ | Reason text here |
            r'\|\s*\*\*(?:MERGE|MERGED|CLOSE|CLOSED|REQUEST_CHANGES)\*\*[^|]*\|\s*([^|]+)\|',
        ]
        for pattern in reasoning_patterns:
            match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
            if match and len(match.group(1).strip()) > 10:
                result['reasoning'] = match.group(1).strip()[:500]
                break

        # Extract scores
        value_match = re.search(r'VALUE[_\s]?SCORE:\s*(\d+)', output, re.IGNORECASE)
        if value_match:
            result['value_score'] = min(10, max(1, int(value_match.group(1))))

        quality_match = re.search(r'QUALITY[_\s]?SCORE:\s*(\d+)', output, re.IGNORECASE)
        if quality_match:
            result['quality_score'] = min(10, max(1, int(quality_match.group(1))))

        bloat_match = re.search(r'BLOAT[_\s]?RISK:\s*(LOW|MEDIUM|HIGH)', output, re.IGNORECASE)
        if bloat_match:
            result['bloat_risk'] = bloat_match.group(1).upper()

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
                # Check auto_merge setting
                if not self.auto_merge:
                    # Post approval comment but don't merge
                    value_score = decision.get('value_score', '?')
                    quality_score = decision.get('quality_score', '?')
                    bloat_risk = decision.get('bloat_risk', 'UNKNOWN')
                    reasoning = decision.get('reasoning', 'No reasoning provided')[:500]

                    comment_body = f"""✅ **Tech Lead Approval - Ready to Merge**

**Scores:** Value {value_score}/10 | Quality {quality_score}/10 | Bloat Risk: {bloat_risk}

**Assessment:**
{reasoning}

---
_Auto-merge is disabled. Please merge manually when ready._"""

                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                        f.write(comment_body)
                        temp_file = f.name

                    try:
                        comment_cmd = f'gh pr comment {pr_number} --repo {self.owner}/{repo_name} --body-file "{temp_file}"'
                        result = subprocess.run(comment_cmd, shell=True, capture_output=True, text=True, timeout=60)
                        success = result.returncode == 0
                        if success:
                            self.logger.info(f"Posted approval comment on PR #{pr_number} (auto_merge=false)")
                        else:
                            self.logger.error(f"Failed to post approval comment: {result.stderr}")
                    finally:
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
                    return success

                # Auto-merge is enabled - execute the merge
                cmd = f"gh pr merge {pr_number} --repo {self.owner}/{repo_name} --squash --delete-branch"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                success = result.returncode == 0
                if not success:
                    stderr = result.stderr.lower()
                    if 'merge conflict' in stderr or 'not mergeable' in stderr:
                        self.logger.warning(f"Merge blocked by conflicts: {result.stderr}")
                        # Post a comment so the state is visible
                        comment_cmd = f'gh pr comment {pr_number} --repo {self.owner}/{repo_name} --body "Tech Lead approved for merge (Value: {decision.get("value_score", "?")}/10, Quality: {decision.get("quality_score", "?")}/10). Blocked by merge conflicts - please rebase."'
                        subprocess.run(comment_cmd, shell=True, capture_output=True, text=True, timeout=30)
                    else:
                        self.logger.error(f"Merge failed: {result.stderr}")
                else:
                    self.logger.info(f"Successfully merged PR #{pr_number}")
                return success

            elif action == 'CLOSE':
                reason = decision['reasoning'][:500]
                cmd = f'gh pr close {pr_number} --repo {self.owner}/{repo_name} --comment "Closed by Tech Lead Review: {reason}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                success = result.returncode == 0
                if not success:
                    self.logger.error(f"Close failed: {result.stderr}")
                return success

            elif action == 'REQUEST_CHANGES':
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

                # Check if we already posted a similar comment to avoid spam
                try:
                    existing_comments = self._get_pr_comments(repo_name, pr_number)
                    for existing in existing_comments[-5:]:  # Check last 5 comments
                        existing_body = existing.get('body', '')
                        # If we already posted a REQUEST_CHANGES comment with same reasoning, skip
                        if '**Tech Lead Review - Changes Requested**' in existing_body and feedback[:100] in existing_body:
                            self.logger.info(f"Skipping duplicate comment on PR #{pr_number} - already posted similar feedback")
                            return True  # Consider this a success - no need to spam
                except Exception as e:
                    self.logger.warning(f"Could not check for duplicate comments: {e}")

                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                    f.write(comment_body)
                    temp_file = f.name

                try:
                    # FIRST: Try to use formal GitHub review (sets reviewDecision field)
                    review_cmd = f'gh pr review {pr_number} --repo {self.owner}/{repo_name} --request-changes --body-file "{temp_file}"'
                    result = subprocess.run(review_cmd, shell=True, capture_output=True, text=True, timeout=60)

                    if result.returncode == 0:
                        self.logger.info(f"Posted formal review REQUEST_CHANGES on PR #{pr_number}")
                        success = True
                    elif "Can not request changes on your own pull request" in result.stderr or "own pull request" in result.stderr:
                        # FALLBACK: GitHub doesn't allow reviewing your own PR - use comment instead
                        self.logger.info(f"GitHub doesn't allow formal review on own PR - posting comment instead")
                        comment_cmd = f'gh pr comment {pr_number} --repo {self.owner}/{repo_name} --body-file "{temp_file}"'
                        result = subprocess.run(comment_cmd, shell=True, capture_output=True, text=True, timeout=60)
                        success = result.returncode == 0
                        if success:
                            self.logger.info(f"Posted feedback comment on PR #{pr_number}")
                        else:
                            self.logger.error(f"Comment failed: {result.stderr}")
                    else:
                        self.logger.error(f"Review failed: {result.stderr}")
                        success = False
                finally:
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

        # Gather ALL PR data including comments
        diff = self._get_pr_diff(repo_name, pr_number)
        checks = self._get_pr_checks(repo_name, pr_number)
        files = self._get_pr_files(repo_name, pr_number)
        comments = self._get_pr_comments(repo_name, pr_number)

        self.logger.info(f"Fetched {len(comments)} comments for context")

        # Quick rejection checks (before Claude review)
        quick_reject = None

        # Check for repeated REQUEST_CHANGES (3-strikes rule)
        tech_lead_change_requests = [
            c for c in comments
            if '**Tech Lead Review - Changes Requested**' in c.get('body', '')
        ]
        if len(tech_lead_change_requests) >= 3:
            quick_reject = {
                'decision': 'CLOSE',
                'reasoning': f'Unable to meet quality standards after {len(tech_lead_change_requests)} review cycles. Closing to prevent wasted effort. Start fresh with a new approach if this feature is still needed.',
                'value_score': 0,
                'quality_score': 0,
                'bloat_risk': 'HIGH',
                'auto_rejected': True,
                'three_strikes': True
            }
            self.logger.info(f"AUTO: Closing PR - 3-strikes rule triggered ({len(tech_lead_change_requests)} change requests)")

        if not quick_reject and checks.get('any_failing'):
            quick_reject = {
                'decision': 'REQUEST_CHANGES',
                'reasoning': 'CI checks are failing. Fix the failing checks before this PR can be reviewed.',
                'value_score': 0,
                'quality_score': 0,
                'bloat_risk': 'HIGH',
                'auto_rejected': True
            }
            self.logger.info("AUTO: Requesting changes - CI failing")

        if quick_reject:
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

        # Create prompt for Claude with full context including comments
        prompt = self._create_review_prompt(repo, pr, diff, checks, files, comments)

        prompt_file = self.work_dir / f'prompt_tech_lead_{repo_name}_{pr_number}.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        output_file = self.logs_dir / f"tech_lead_{repo_name}_{pr_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        self.logger.info(f"Invoking Claude for review (with {len(comments)} comments for context)...")

        cmd = f"cat {prompt_file} | claude --dangerously-skip-permissions -p --model opus > {output_file} 2>&1"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.work_dir),
                timeout=900
            )

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
                'comments_count': len(comments),
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
        """Auto-close PRs that have been stale for too long"""
        from datetime import timedelta
        STALE_DAYS = self.STALE_DAYS

        cleaned = []
        remaining = []

        for pr in prs:
            created_at = pr.get('createdAt', '')
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                age_days = (datetime.now(created_date.tzinfo) - created_date).days
            except:
                age_days = 0

            branch = pr.get('headRefName', '')
            is_barbossa_pr = branch.startswith('barbossa/')

            if is_barbossa_pr and age_days >= STALE_DAYS:
                self.logger.info(f"AUTO-CLOSING stale PR #{pr['number']} ({age_days} days old): {pr['title']}")
                try:
                    cmd = f'gh pr close {pr["number"]} --repo {self.owner}/{repo_name} --comment "Auto-closed by Tech Lead: PR has been stale for {age_days} days."'
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

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + str(uuid.uuid4())[:8]

    def run(self):
        """Run the Tech Lead review process - reviews ALL open PRs"""
        run_session_id = self._generate_session_id()

        if not self.enabled:
            self.logger.info("Tech Lead is disabled in config. Skipping.")
            return []

        self.logger.info(f"\n{'#'*70}")
        self.logger.info("BARBOSSA TECH LEAD v2.0 - PR REVIEW SESSION")
        self.logger.info("Mode: GitHub as single source of truth (no file-based state)")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'#'*70}\n")

        # Track run start (fire-and-forget, never blocks)
        track_run_start("tech_lead", run_session_id, len(self.repositories))

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

            # Clean up stale PRs first
            open_prs = self._cleanup_stale_prs(repo_name, open_prs)

            if not open_prs:
                self.logger.info(f"No remaining open PRs in {repo_name} after cleanup")
                continue

            self.logger.info(f"Found {len(open_prs)} open PRs - reviewing ALL with full context")

            # Review ALL PRs - Claude will read comments and understand context
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

        # Track run end (fire-and-forget)
        track_run_end("tech_lead", run_session_id, success=True, pr_created=False)

        return all_results

    def status(self):
        """Show current status and recent decisions"""
        print(f"\nBarbossa Tech Lead v{self.VERSION} - Status")
        print("=" * 50)
        print("Mode: GitHub as single source of truth")

        print(f"\nRepositories ({len(self.repositories)}):")
        for repo in self.repositories:
            prs = self._get_open_prs(repo['name'])
            print(f"  - {repo['name']}: {len(prs)} open PRs")

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
        description='Barbossa Tech Lead v2.0 - PR Review & Governance'
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
