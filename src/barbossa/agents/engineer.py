#!/usr/bin/env python3
"""
Barbossa Engineer v5.8 - Autonomous Development Agent
Creates PRs from the backlog every hour at :00.
Picks from GitHub Issues first, invents work only if backlog empty.

Part of the Pipeline:
- Discovery (3x daily) → creates Issues in backlog
- Engineer (:00) → implements from backlog, creates PRs  <-- THIS AGENT
- Tech Lead (:35) → reviews PRs, merges or requests changes
- Auditor (daily 06:30) → system health analysis

Prompts loaded locally from prompts/ directory.
"""

import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from barbossa.utils.issue_tracker import get_issue_tracker, IssueTracker, LinearIssueTracker


class Barbossa:
    """
    Simple personal dev assistant that creates PRs on configured repositories.
    Uses GitHub as the single source of truth - no file-based state.
    Supports both GitHub Issues and Linear for issue tracking.
    """

    VERSION = "1.5.2"  # macOS platform support (linux/amd64)

    def __init__(self, work_dir: Optional[Path] = None):
        # Support Docker (/app) and local paths
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-dev'
        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.changelogs_dir = self.work_dir / 'changelogs'
        self.projects_dir = self.work_dir / 'projects'
        self.config_file = self.work_dir / 'config' / 'repositories.json'
        self.pr_history_file = self.work_dir / 'pr_history.json'

        # Ensure directories exist
        for dir_path in [self.logs_dir, self.changelogs_dir, self.projects_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Firebase client (analytics + state tracking, never blocks)
        self.firebase = get_client()

        # Soft version check - warn but never block
        update_msg = check_version()
        if update_msg:
            self.logger.info(f"UPDATE AVAILABLE: {update_msg}")

        # Load config and PR history
        self.config = self._load_config()
        self.repositories = self.config.get('repositories', [])
        self.owner = self.config.get('owner')
        if not self.owner:
            raise ValueError("'owner' is required in config/repositories.json")
        self.pr_history = self._load_pr_history()

        self.logger.info("=" * 60)
        self.logger.info(f"BARBOSSA v{self.VERSION} - Personal Dev Assistant")
        self.logger.info(f"Repositories: {len(self.repositories)}")
        for repo in self.repositories:
            self.logger.info(f"  - {repo['name']}: {repo['url']}")
        self.logger.info("=" * 60)


    def _setup_logging(self):
        """Configure logging"""
        log_file = self.logs_dir / f"barbossa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger('barbossa')
        self.logger.info(f"Logging to: {log_file}")

    def _load_config(self) -> Dict:
        """Load repository configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)

        self.logger.error(f"Config file not found: {self.config_file}")
        return {'repositories': []}

    def _load_pr_history(self) -> Dict:
        """Load PR history to track what was already attempted"""
        if self.pr_history_file.exists():
            try:
                with open(self.pr_history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'closed_prs': [], 'merged_prs': [], 'failed_attempts': {}}

    def _save_pr_history(self):
        """Save PR history"""
        try:
            with open(self.pr_history_file, 'w') as f:
                json.dump(self.pr_history, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save PR history: {e}")

    def _get_recent_closed_prs(self, repo: Dict) -> List[str]:
        """Get titles of recently closed PRs to avoid repeating failed attempts"""
        owner = self.owner
        repo_name = repo['name']

        try:
            result = subprocess.run(
                f"gh pr list --repo {owner}/{repo_name} --state closed --limit 20 --json title,closedAt,mergedAt",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                prs = json.loads(result.stdout)
                # Get titles of PRs that were closed (not merged)
                closed_titles = [pr['title'] for pr in prs if not pr.get('mergedAt')]
                return closed_titles
        except Exception as e:
            self.logger.warning(f"Could not fetch closed PRs for {repo_name}: {e}")
        return []

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + str(uuid.uuid4())[:8]

    def _create_prompt(self, repo: Dict, session_id: str, closed_pr_titles: List[str] = None) -> str:
        """Create a context-rich Claude prompt for a repository.

        First attempts to fetch the prompt template from Firebase cloud.
        Falls back to local template if cloud is unavailable.
        """
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

        # Get package manager (defaults to npm if not specified)
        pkg_manager = repo.get('package_manager', 'npm')
        env_file = repo.get('env_file', '.env')

        # Get settings for test requirements
        settings = self.config.get('settings', {}).get('tech_lead', {})
        min_lines_for_tests = settings.get('min_lines_for_tests', 50)

        # Build closed PRs section to avoid repetition
        if closed_pr_titles:
            closed_pr_section = "RECENTLY CLOSED PRs (DO NOT REPEAT THESE):\n"
            for title in closed_pr_titles[:10]:
                closed_pr_section += f"  - {title}\n"
            closed_pr_section += "\n  These PRs were closed without merging. DO NOT attempt similar work.\n"
        else:
            closed_pr_section = "(no recently closed PRs)"

        # Build install/build commands based on package manager
        if pkg_manager == 'pnpm':
            install_cmd = 'pnpm install'
            build_cmd = 'pnpm run build'
            test_cmd = 'pnpm run test'
        elif pkg_manager == 'yarn':
            install_cmd = 'yarn install'
            build_cmd = 'yarn build'
            test_cmd = 'yarn test'
        else:
            install_cmd = 'npm install'
            build_cmd = 'npm run build'
            test_cmd = 'npm test'

        # Build tech stack section
        tech_stack = repo.get('tech_stack', {})
        tech_lines = []
        for key, value in tech_stack.items():
            tech_lines.append(f"  - {key.replace('_', ' ').title()}: {value}")
        tech_section = "\n".join(tech_lines) if tech_lines else "  (not specified)"

        # Build architecture section
        arch = repo.get('architecture', {})
        arch_lines = []
        if arch.get('data_flow'):
            arch_lines.append(f"  Data Flow: {arch['data_flow']}")
        if arch.get('key_dirs'):
            arch_lines.append("  Key Directories:")
            for d in arch['key_dirs']:
                arch_lines.append(f"    - {d}")
        arch_section = "\n".join(arch_lines) if arch_lines else "  (explore codebase to understand)"

        # Build design system section
        design = repo.get('design_system', {})
        design_lines = []
        if design.get('aesthetic'):
            design_lines.append(f"  Aesthetic: {design['aesthetic']}")
        if design.get('brand_rules'):
            design_lines.append("  Brand Rules (MUST FOLLOW):")
            for rule in design['brand_rules']:
                design_lines.append(f"    - {rule}")
        design_section = "\n".join(design_lines) if design_lines else "  (no specific design system)"

        # Build do not touch section
        do_not_touch = repo.get('do_not_touch', [])
        if do_not_touch:
            dnt_lines = [f"  - {item}" for item in do_not_touch]
            dnt_section = "\n".join(dnt_lines)
        else:
            dnt_section = "  (no restrictions)"

        # Get owner for gh commands
        owner = self.owner

        # Load template from local file
        template = get_system_prompt("engineer")
        if not template:
            self.logger.error("Failed to load engineer prompt from prompts/engineer.txt")
            raise RuntimeError("Engineer prompt file not found. Check prompts/ directory.")

        self.logger.info("Using local prompt template")

        # Build issue tracker sections based on config
        tracker_type = self.config.get('issue_tracker', {}).get('type', 'github')
        repo_name = repo['name']

        if tracker_type == 'linear':
            # For Linear, we inject issues directly into the prompt
            try:
                tracker = get_issue_tracker(self.config, repo_name, self.logger)
                if isinstance(tracker, LinearIssueTracker):
                    # Get Linear issues and inject them
                    issue_list_command = f"  [Linear Issues for team {tracker.team_key}]\n"
                    issues_context = tracker.get_issues_context(limit=10)
                    issue_list_command += issues_context

                    # Backlog section with actual issues
                    backlog_section = f"""Before inventing work, check if there are Issues ready to implement:

{tracker.get_issues_context(state="Backlog", limit=5)}

If there ARE backlog issues above:
  1. Pick the FIRST one (already prioritized)
  2. Implement exactly what's requested
  3. Name your branch: barbossa/<issue-identifier>-description
  4. The branch name auto-links to the Linear issue
"""
                else:
                    # Fallback to GitHub commands
                    issue_list_command = f"  gh issue list --state open --repo {owner}/{repo_name} --limit 10"
                    backlog_section = self._get_github_backlog_section(owner, repo_name)
            except Exception as e:
                self.logger.warning(f"Failed to get Linear issues, falling back to GitHub: {e}")
                issue_list_command = f"  gh issue list --state open --repo {owner}/{repo_name} --limit 10"
                backlog_section = self._get_github_backlog_section(owner, repo_name)
        else:
            # GitHub - use CLI commands
            issue_list_command = f"  gh issue list --state open --repo {owner}/{repo_name} --limit 10"
            backlog_section = self._get_github_backlog_section(owner, repo_name)

        # Replace template variables
        prompt = template
        prompt = prompt.replace("{{session_id}}", session_id)
        prompt = prompt.replace("{{timestamp}}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        prompt = prompt.replace("{{repo_name}}", repo_name)
        prompt = prompt.replace("{{repo_url}}", repo['url'])
        prompt = prompt.replace("{{owner}}", owner)
        prompt = prompt.replace("{{description}}", repo.get('description', 'No description provided.'))
        prompt = prompt.replace("{{tech_section}}", tech_section)
        prompt = prompt.replace("{{arch_section}}", arch_section)
        prompt = prompt.replace("{{design_section}}", design_section)
        prompt = prompt.replace("{{dnt_section}}", dnt_section)
        prompt = prompt.replace("{{closed_pr_section}}", closed_pr_section)
        prompt = prompt.replace("{{issue_list_command}}", issue_list_command)
        prompt = prompt.replace("{{backlog_section}}", backlog_section)
        prompt = prompt.replace("{{pkg_manager}}", pkg_manager.upper())
        prompt = prompt.replace("{{install_cmd}}", install_cmd)
        prompt = prompt.replace("{{build_cmd}}", build_cmd)
        prompt = prompt.replace("{{test_cmd}}", test_cmd)
        prompt = prompt.replace("{{env_file}}", env_file)
        prompt = prompt.replace("{{min_lines_for_tests}}", str(min_lines_for_tests))
        return prompt

    def _get_github_backlog_section(self, owner: str, repo_name: str) -> str:
        """Generate the backlog section for GitHub Issues."""
        return f"""Before inventing work, check if there are Issues ready to implement:

  gh issue list --repo {owner}/{repo_name} --label backlog --state open --limit 5

If there ARE issues labeled "backlog":
  1. Pick the FIRST one (already prioritized)
  2. Read the issue description carefully
  3. Implement exactly what's requested
  4. Link your PR to the issue: "Closes #XX" in PR description
"""

    def _save_session(self, repo_name: str, session_id: str, prompt: str, output_file: Path):
        """Save session details for web portal"""
        sessions_file = self.work_dir / 'sessions.json'

        sessions = []
        if sessions_file.exists():
            try:
                with open(sessions_file, 'r') as f:
                    sessions = json.load(f)
            except:
                sessions = []

        # Add new session
        sessions.insert(0, {
            'session_id': session_id,
            'repository': repo_name,
            'started': datetime.now().isoformat(),
            'status': 'running',
            'output_file': str(output_file),
            'prompt_preview': prompt[:200] + '...'
        })

        # Keep only last 50 sessions
        sessions = sessions[:50]

        with open(sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2)

    def _update_session_status(self, session_id: str, status: str, pr_url: str = None, summary: str = None):
        """Update session status"""
        sessions_file = self.work_dir / 'sessions.json'

        if not sessions_file.exists():
            return

        try:
            with open(sessions_file, 'r') as f:
                sessions = json.load(f)

            for session in sessions:
                if session['session_id'] == session_id:
                    session['status'] = status
                    session['completed'] = datetime.now().isoformat()
                    if pr_url:
                        session['pr_url'] = pr_url
                    if summary:
                        session['summary'] = summary
                    break

            with open(sessions_file, 'w') as f:
                json.dump(sessions, f, indent=2)
        except:
            pass

    def _cleanup_stale_sessions(self):
        """Mark sessions that have been running for too long as timeout"""
        sessions_file = self.work_dir / 'sessions.json'

        if not sessions_file.exists():
            return

        try:
            with open(sessions_file, 'r') as f:
                sessions = json.load(f)

            modified = False
            now = datetime.now()

            for session in sessions:
                if session.get('status') == 'running':
                    started_str = session.get('started', '')
                    try:
                        started = datetime.fromisoformat(started_str)
                        age_hours = (now - started).total_seconds() / 3600

                        # Mark sessions older than 2 hours as timeout
                        if age_hours > 2:
                            session['status'] = 'timeout'
                            session['completed'] = now.isoformat()
                            session['timeout_reason'] = f'Session exceeded 2 hour limit (ran for {age_hours:.1f}h)'
                            modified = True
                            self.logger.info(f"Marked stale session as timeout: {session.get('session_id')} ({age_hours:.1f}h old)")
                    except (ValueError, TypeError):
                        pass

            if modified:
                with open(sessions_file, 'w') as f:
                    json.dump(sessions, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Could not cleanup stale sessions: {e}")

    def _extract_pr_url(self, log_file: Path) -> Optional[str]:
        """Extract PR URL from Claude's output"""
        if not log_file.exists():
            return None

        try:
            content = log_file.read_text()
            # Look for GitHub PR URLs
            import re
            pr_pattern = r'https://github\.com/[^/]+/[^/]+/pull/\d+'
            matches = re.findall(pr_pattern, content)
            if matches:
                return matches[-1]  # Return the last PR URL found
        except:
            pass
        return None

    def _extract_summary(self, log_file: Path) -> Optional[str]:
        """Extract summary from Claude's output"""
        if not log_file.exists():
            return None

        try:
            content = log_file.read_text()
            # Look for WHAT section or Summary
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '**WHAT:**' in line or 'WHAT:' in line:
                    # Get the content after WHAT:
                    summary = line.split(':', 1)[-1].strip()
                    if summary:
                        return summary[:200]  # Limit to 200 chars
            # Fallback: get first non-empty line
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and len(line) > 20:
                    return line[:200]
        except:
            pass
        return None

    def _create_changelog(self, repo_name: str, session_id: str, output_file: Path):
        """Create changelog entry"""
        changelog_file = self.changelogs_dir / f"{repo_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        content = f"""# Barbossa Session: {repo_name}

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Session ID**: {session_id}
**Repository**: {repo_name}
**Version**: Barbossa v{self.VERSION}

## Status
Session started. Claude is working on creating a PR.

## Output
See: {output_file}

---
*Generated by Barbossa Personal Dev Assistant*
"""

        with open(changelog_file, 'w') as f:
            f.write(content)

        self.logger.info(f"Changelog: {changelog_file}")

    def _get_open_prs(self, repo: Dict) -> List[Dict]:
        """Get open PRs for a repository with full context"""
        owner = self.owner
        repo_name = repo['name']

        try:
            result = subprocess.run(
                f"gh pr list --repo {owner}/{repo_name} --state open "
                f"--json number,title,headRefName,statusCheckRollup,reviewDecision,url,mergeable,mergeStateStatus,updatedAt "
                f"--limit 20",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            else:
                self.logger.warning(f"gh pr list failed for {repo_name}: {result.stderr}")
        except Exception as e:
            self.logger.warning(f"Could not fetch PRs for {repo_name}: {e}")
        return []

    def _get_pr_comments(self, repo_name: str, pr_number: int) -> List[Dict]:
        """Get all comments on a PR - this is the conversation history"""
        owner = self.owner
        try:
            result = subprocess.run(
                f"gh pr view {pr_number} --repo {owner}/{repo_name} --json comments",
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

    def _count_total_open_prs(self) -> int:
        """Count total open PRs across all repositories"""
        total = 0
        for repo in self.repositories:
            prs = self._get_open_prs(repo)
            total += len(prs)
            self.logger.info(f"  {repo['name']}: {len(prs)} open PRs")
        return total

    def _get_prs_needing_attention(self, repo: Dict) -> List[Dict]:
        """Get PRs that need attention - uses GitHub as source of truth"""
        prs = self._get_open_prs(repo)
        needs_attention = []
        repo_name = repo['name']
        owner = self.owner

        for pr in prs:
            pr_number = pr.get('number')

            # Fetch comments to understand conversation context
            comments = self._get_pr_comments(repo_name, pr_number)

            # PRIORITY 1: Look for Tech Lead feedback in comments (most important)
            has_tech_lead_feedback = False
            latest_tech_lead_feedback = None
            latest_tech_lead_timestamp = None
            feedback_addressed = False

            for comment in comments:
                body = comment.get('body', '')
                author = comment.get('author', {}).get('login', '')
                created_at = comment.get('createdAt', '')

                # Check for Tech Lead feedback marker
                if '**Tech Lead Review - Changes Requested**' in body:
                    has_tech_lead_feedback = True
                    # Track the LATEST Tech Lead feedback
                    if not latest_tech_lead_timestamp or created_at > latest_tech_lead_timestamp:
                        latest_tech_lead_timestamp = created_at
                        # Extract the feedback section
                        if '**Feedback:**' in body:
                            latest_tech_lead_feedback = body.split('**Feedback:**')[1].split('---')[0].strip()
                        else:
                            latest_tech_lead_feedback = body

            # Check if feedback was addressed: look for Engineer updates AFTER latest Tech Lead comment
            if has_tech_lead_feedback and latest_tech_lead_timestamp:
                for comment in comments:
                    created_at = comment.get('createdAt', '')
                    author = comment.get('author', {}).get('login', '')
                    body = comment.get('body', '')

                    # Look for Engineer/bot responses AFTER the latest Tech Lead feedback
                    if created_at > latest_tech_lead_timestamp:
                        # Engineer commented after Tech Lead - check if it's addressing feedback
                        if 'Feedback Addressed' in body or 'feedback addressed' in body.lower():
                            feedback_addressed = True
                            break
                        # Also check for automated "pushed" notifications which indicate work was done
                        if author in ['github-actions[bot]', 'vercel[bot]'] and 'commit' in body.lower():
                            feedback_addressed = True
                            break

            # If Tech Lead gave feedback and it wasn't addressed, THIS IS TOP PRIORITY
            if has_tech_lead_feedback and not feedback_addressed:
                self.logger.info(f"  PR #{pr_number}: Tech Lead feedback detected (not addressed)")
                pr['attention_reason'] = 'tech_lead_feedback'
                pr['tech_lead_feedback'] = latest_tech_lead_feedback[:500] if latest_tech_lead_feedback else 'Please address Tech Lead feedback'
                pr['comments'] = comments
                needs_attention.append(pr)
                continue

            # PRIORITY 2: Check if PR has formal GitHub review decision
            if pr.get('reviewDecision') == 'CHANGES_REQUESTED':
                self.logger.info(f"  PR #{pr_number}: GitHub review requests changes")
                pr['attention_reason'] = 'changes_requested'
                pr['comments'] = comments
                needs_attention.append(pr)
                continue

            # PRIORITY 3: Check if PR has merge conflicts
            if pr.get('mergeable') == 'CONFLICTING' or pr.get('mergeStateStatus') == 'DIRTY':
                self.logger.info(f"  PR #{pr_number}: Merge conflicts detected")
                pr['attention_reason'] = 'merge_conflicts'
                pr['comments'] = comments
                needs_attention.append(pr)
                continue

            # PRIORITY 4: Check if PR has failing checks
            checks = pr.get('statusCheckRollup', [])
            has_failure = False
            for check in (checks or []):
                conclusion = check.get('conclusion', '')
                state = check.get('state', '')
                if conclusion == 'FAILURE' or state == 'FAILURE':
                    has_failure = True
                    break

            if has_failure:
                self.logger.info(f"  PR #{pr_number}: Failing CI checks")
                pr['attention_reason'] = 'failing_checks'
                pr['comments'] = comments
                needs_attention.append(pr)

        return needs_attention

    def _format_comments_for_prompt(self, comments: List[Dict]) -> str:
        """Format PR comments into a readable conversation history"""
        if not comments:
            return "(No comments on this PR)"

        formatted = []
        for comment in comments[-15:]:  # Last 15 comments max
            author = comment.get('author', {}).get('login', 'unknown')
            body = comment.get('body', '')[:800]  # Truncate long comments
            created = comment.get('createdAt', '')[:10]  # Just the date

            # Skip Vercel deploy comments
            if author == 'vercel' or '[vc]:' in body:
                continue

            formatted.append(f"[{created}] @{author}:\n{body}\n")

        return "\n---\n".join(formatted) if formatted else "(No relevant comments)"

    def _create_review_prompt(self, repo: Dict, pr: Dict, session_id: str) -> str:
        """Create a prompt for reviewing and fixing an existing PR - includes full comment context"""
        owner = self.owner
        repo_name = repo['name']
        pr_number = pr['number']
        pr_branch = pr['headRefName']
        attention_reason = pr.get('attention_reason', 'needs_review')

        pkg_manager = repo.get('package_manager', 'npm')
        if pkg_manager == 'pnpm':
            install_cmd, build_cmd, test_cmd = 'pnpm install', 'pnpm run build', 'pnpm run test'
        elif pkg_manager == 'yarn':
            install_cmd, build_cmd, test_cmd = 'yarn install', 'yarn build', 'yarn test'
        else:
            install_cmd, build_cmd, test_cmd = 'npm install', 'npm run build', 'npm test'

        # Format comment history
        comments = pr.get('comments', [])
        conversation = self._format_comments_for_prompt(comments)

        # Build issue-specific instructions
        if attention_reason == 'merge_conflicts':
            issue_instructions = f"""
ISSUE TYPE: MERGE CONFLICTS
The PR has merge conflicts with main branch that must be resolved.

Phase 2 - Resolve Conflicts:
  # First, rebase onto latest main
  git fetch origin
  git rebase origin/main

  # If conflicts occur during rebase:
  # 1. Identify conflicting files: git status
  # 2. Open each conflicting file and resolve conflicts
  # 3. Stage resolved files: git add <file>
  # 4. Continue rebase: git rebase --continue
  # 5. Repeat until rebase completes

  # After resolving conflicts, reinstall dependencies
  {install_cmd}

Phase 3 - Verify:
  # Run build and tests to ensure nothing broke
  {build_cmd}
  {test_cmd}

Phase 4 - Update PR:
  # Force push the rebased branch
  git push origin {pr_branch} --force-with-lease"""

        elif attention_reason == 'tech_lead_feedback':
            tech_lead_feedback = pr.get('tech_lead_feedback', 'Please address the feedback')
            issue_instructions = f"""
ISSUE TYPE: TECH LEAD FEEDBACK
The Tech Lead has requested changes on this PR.

TECH LEAD FEEDBACK:
{tech_lead_feedback}

IMPORTANT: Read the full conversation history below to understand:
1. What exactly was requested
2. If any previous attempts were made to address it
3. What specifically needs to be done

Phase 2 - Address Feedback:
  # Carefully read the feedback and conversation
  # Make the specific changes requested
  # If feedback asks for verification (curl output, test results), provide it

Phase 3 - Verify:
  {build_cmd}
  {test_cmd}

Phase 4 - Update PR:
  git add -A
  git commit -m "fix: address Tech Lead feedback"
  git push origin {pr_branch}

  # Post a comment explaining what you fixed
  gh pr comment {pr_number} --repo {owner}/{repo_name} --body "## Feedback Addressed

<Explain what you changed to address the feedback>"
"""
        else:
            issue_instructions = f"""
Phase 2 - Investigate:
  # Check what's failing
  gh pr checks {pr_number} --repo {owner}/{repo_name}

  # View any review comments
  gh pr view {pr_number} --repo {owner}/{repo_name} --comments

  # Run tests/build locally to see the errors
  {build_cmd}
  {test_cmd}

Phase 3 - Fix:
  - Identify the root cause of failures
  - Make targeted fixes to address the issues
  - Run build and tests again to verify fixes
  - Keep changes minimal and focused

Phase 4 - Update PR:
  git add -A
  git commit -m "fix: address CI failures / review comments"
  git push origin {pr_branch}"""

        return f"""You are Barbossa, an autonomous personal development assistant.

================================================================================
SESSION METADATA
================================================================================
Session ID: {session_id}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Repository: {repo_name}
MODE: PR REVIEW AND FIX

================================================================================
YOUR MISSION
================================================================================
Review and fix an existing Pull Request that needs attention.

PR Details:
- PR #{pr_number}: {pr['title']}
- Branch: {pr_branch}
- URL: {pr['url']}
- Issue: {attention_reason.replace('_', ' ').title()}

================================================================================
PR CONVERSATION HISTORY (IMPORTANT - READ THIS CAREFULLY)
================================================================================
This is the comment history on this PR. Use this to understand:
- What feedback was given
- What has been tried before
- What exactly needs to be done

{conversation}

================================================================================
WORKFLOW
================================================================================
Phase 1 - Setup:
  cd /app/projects
  if [ ! -d "{repo_name}" ]; then
    git clone {repo['url']} {repo_name}
  fi
  cd {repo_name}

  # Fetch and checkout the PR branch
  git fetch origin
  git checkout {pr_branch}
  git pull origin {pr_branch} || true  # May fail if conflicts exist

  {install_cmd}
{issue_instructions}

================================================================================
OUTPUT REQUIRED
================================================================================
When complete, provide:
1. ISSUE: What was failing / what feedback needed addressing
2. FIX: What you changed to fix it
3. RESULT: Confirmation that build/tests now pass
4. PR URL: {pr['url']}

Begin your work now."""

    def execute_pr_review(self, repo: Dict, pr: Dict) -> bool:
        """Execute PR review and fix session"""
        repo_name = repo['name']
        session_id = self._generate_session_id()

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"REVIEW MODE: {repo_name} PR #{pr['number']}")
        self.logger.info(f"Issue: {pr.get('attention_reason', 'unknown')}")
        self.logger.info(f"Session ID: {session_id}")
        self.logger.info(f"{'='*60}\n")

        prompt = self._create_review_prompt(repo, pr, session_id)

        prompt_file = self.work_dir / f'prompt_{repo_name}_review.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        output_file = self.logs_dir / f"claude_{repo_name}_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        self._save_session(repo_name, session_id, prompt, output_file)

        self.logger.info(f"Launching Claude to fix PR #{pr['number']}...")

        cmd = f"cat {prompt_file} | claude --dangerously-skip-permissions -p --model opus > {output_file} 2>&1"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.work_dir),
                timeout=1800
            )

            if result.returncode == 0:
                self.logger.info(f"Claude completed review for {repo_name} PR #{pr['number']}")
                self._update_session_status(session_id, 'completed', pr_url=pr['url'])
                return True
            else:
                self.logger.error(f"Claude failed review for {repo_name}")
                self._update_session_status(session_id, 'failed')
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Claude timed out during review")
            self._update_session_status(session_id, 'timeout')
            return False
        except Exception as e:
            self.logger.error(f"Error during review: {e}")
            self._update_session_status(session_id, 'error')
            return False

    def execute_for_repo(self, repo: Dict) -> bool:
        """Execute development session for a single repository"""
        repo_name = repo['name']
        session_id = self._generate_session_id()

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Starting session for: {repo_name}")
        self.logger.info(f"Session ID: {session_id}")
        self.logger.info(f"{'='*60}\n")

        # Get recently closed PRs to avoid repeating failed attempts
        closed_pr_titles = self._get_recent_closed_prs(repo)
        if closed_pr_titles:
            self.logger.info(f"Found {len(closed_pr_titles)} recently closed PRs to avoid")

        # Create prompt with closed PR context
        prompt = self._create_prompt(repo, session_id, closed_pr_titles)

        # Save prompt to file
        prompt_file = self.work_dir / f'prompt_{repo_name}.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        # Output file for Claude's work
        output_file = self.logs_dir / f"claude_{repo_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # Save session for web portal
        self._save_session(repo_name, session_id, prompt, output_file)

        # Create changelog
        self._create_changelog(repo_name, session_id, output_file)

        # Execute Claude
        self.logger.info(f"Launching Claude for {repo_name}...")
        self.logger.info(f"Output: {output_file}")

        cmd = f"cat {prompt_file} | claude --dangerously-skip-permissions -p --model opus > {output_file} 2>&1"

        try:
            # Run Claude (this will take a while)
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.work_dir),
                timeout=1800  # 30 minute timeout per repo
            )

            # Extract PR URL and summary from output
            pr_url = self._extract_pr_url(output_file)
            summary = self._extract_summary(output_file)

            if result.returncode == 0:
                self.logger.info(f"Claude completed for {repo_name}")
                if pr_url:
                    self.logger.info(f"PR created: {pr_url}")
                self._update_session_status(session_id, 'completed', pr_url=pr_url, summary=summary)
                return True
            else:
                self.logger.error(f"Claude failed for {repo_name} with code {result.returncode}")
                self._update_session_status(session_id, 'failed', summary=summary)
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Claude timed out for {repo_name}")
            self._update_session_status(session_id, 'timeout')
            return False
        except Exception as e:
            self.logger.error(f"Error executing Claude for {repo_name}: {e}")
            self._update_session_status(session_id, 'error')
            return False

    def run(self, repo_name: Optional[str] = None):
        """Run Barbossa for all repositories or a specific one"""
        run_session_id = self._generate_session_id()

        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"BARBOSSA RUN STARTED")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'#'*60}\n")

        # Track run start (fire-and-forget, never blocks)
        track_run_start("engineer", run_session_id, len(self.repositories))

        # Cleanup stale sessions before starting
        self._cleanup_stale_sessions()

        # PRIORITY 1: Check for PRs needing attention (uses GitHub as source of truth)
        self.logger.info("Checking for PRs needing attention...")

        prs_needing_attention = []
        for repo in self.repositories:
            repo_prs = self._get_prs_needing_attention(repo)
            for pr in repo_prs:
                prs_needing_attention.append((repo, pr))

        if prs_needing_attention:
            self.logger.info(f"\n{'!'*60}")
            self.logger.info(f"REVISION MODE: {len(prs_needing_attention)} PRs need attention")
            for repo, pr in prs_needing_attention:
                self.logger.info(f"  - {repo['name']} #{pr['number']}: {pr.get('attention_reason', 'unknown')}")
            self.logger.info("Addressing ALL feedback before creating new PRs")
            self.logger.info(f"{'!'*60}\n")

            # Process ALL PRs needing attention (up to 5 per run to avoid timeout)
            results = []
            for repo, pr in prs_needing_attention[:5]:
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"Processing: {repo['name']} #{pr['number']} ({pr.get('attention_reason', 'unknown')})")
                self.logger.info(f"{'='*60}")

                success = self.execute_pr_review(repo, pr)
                results.append((repo['name'], pr['number'], success))

            self.logger.info(f"\n{'#'*60}")
            self.logger.info("REVISION SUMMARY")
            self.logger.info(f"{'#'*60}")
            for r_name, pr_num, success in results:
                status = "ADDRESSED" if success else "FAILED"
                self.logger.info(f"  {r_name} PR #{pr_num}: {status}")
            self.logger.info(f"{'#'*60}\n")

            # Track run end (fire-and-forget)
            any_success = any(s for _, _, s in results)
            track_run_end("engineer", run_session_id, any_success, pr_created=False)
            return

        self.logger.info("No PRs need attention - all clear!")

        # PRIORITY 2: Check total open PRs to avoid PR sprawl
        self.logger.info("Checking open PRs across repositories...")
        total_open_prs = self._count_total_open_prs()
        self.logger.info(f"Total open PRs: {total_open_prs}")

        if total_open_prs > 5:
            self.logger.info(f"\n{'!'*60}")
            self.logger.info("PAUSE MODE: >5 open PRs detected")
            self.logger.info("Waiting for PRs to be reviewed and merged before creating new ones.")
            self.logger.info(f"{'!'*60}\n")

            # Track run end - paused, not a failure
            track_run_end("engineer", run_session_id, success=True, pr_created=False)
            return

        # PRIORITY 3: Create new PRs (only if no PRs need attention and count is low)
        if repo_name:
            # Run for specific repo
            repo = next((r for r in self.repositories if r['name'] == repo_name), None)
            if repo:
                success = self.execute_for_repo(repo)
                track_run_end("engineer", run_session_id, success, pr_created=success)
            else:
                self.logger.error(f"Repository not found: {repo_name}")
                self.logger.info(f"Available: {[r['name'] for r in self.repositories]}")
                track_run_end("engineer", run_session_id, success=False, pr_created=False)
        else:
            # Run for all repos IN PARALLEL
            self.logger.info(f"Starting parallel execution for {len(self.repositories)} repositories...")
            results = []

            with ThreadPoolExecutor(max_workers=len(self.repositories)) as executor:
                # Submit all repos for parallel execution
                future_to_repo = {
                    executor.submit(self.execute_for_repo, repo): repo
                    for repo in self.repositories
                }

                # Collect results as they complete
                for future in as_completed(future_to_repo):
                    repo = future_to_repo[future]
                    try:
                        success = future.result()
                        results.append((repo['name'], success))
                    except Exception as e:
                        self.logger.error(f"Exception for {repo['name']}: {e}")
                        results.append((repo['name'], False))

            # Summary
            self.logger.info(f"\n{'#'*60}")
            self.logger.info("RUN SUMMARY (parallel execution)")
            self.logger.info(f"{'#'*60}")
            for name, success in results:
                status = "SUCCESS" if success else "FAILED"
                self.logger.info(f"  {name}: {status}")
            self.logger.info(f"{'#'*60}\n")

            # Track run end (fire-and-forget)
            any_success = any(s for _, s in results)
            track_run_end("engineer", run_session_id, any_success, pr_created=any_success)

    def status(self):
        """Show current status"""
        print(f"\nBarbossa v{self.VERSION} - Status")
        print("=" * 40)

        print(f"\nRepositories ({len(self.repositories)}):")
        for repo in self.repositories:
            print(f"  - {repo['name']}: {repo['url']}")

        # Show recent sessions
        sessions_file = self.work_dir / 'sessions.json'
        if sessions_file.exists():
            with open(sessions_file, 'r') as f:
                sessions = json.load(f)

            print(f"\nRecent Sessions (last 5):")
            for session in sessions[:5]:
                status_icon = {
                    'running': '...',
                    'completed': 'OK',
                    'failed': 'ERR',
                    'timeout': 'TO',
                    'error': 'ERR'
                }.get(session.get('status', 'unknown'), '?')

                print(f"  [{status_icon}] {session['repository']} - {session['started'][:16]}")
                if session.get('pr_url'):
                    print(f"       PR: {session['pr_url']}")

        # Show recent changelogs
        changelogs = sorted(self.changelogs_dir.glob('*.md'),
                          key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        if changelogs:
            print(f"\nRecent Changelogs:")
            for cl in changelogs:
                print(f"  - {cl.name}")

        print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Barbossa v4.0 - Personal Development Assistant'
    )
    parser.add_argument(
        '--repo',
        help='Run for specific repository only'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show status and exit'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List configured repositories'
    )

    args = parser.parse_args()

    barbossa = Barbossa()

    if args.status:
        barbossa.status()
    elif args.list:
        for repo in barbossa.repositories:
            print(f"{repo['name']}: {repo['url']}")
    else:
        barbossa.run(args.repo)


if __name__ == "__main__":
    main()
