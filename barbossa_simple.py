#!/usr/bin/env python3
"""
Barbossa v3.0 - Personal Development Assistant
Simple autonomous developer that creates PRs on your repositories every 4 hours.
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


class Barbossa:
    """
    Simple personal dev assistant that creates PRs on configured repositories.
    """

    VERSION = "3.0.0"

    def __init__(self, work_dir: Optional[Path] = None):
        # Support Docker (/app) and local paths
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-engineer'
        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.changelogs_dir = self.work_dir / 'changelogs'
        self.projects_dir = self.work_dir / 'projects'
        self.config_file = self.work_dir / 'config' / 'repositories.json'

        # Ensure directories exist
        for dir_path in [self.logs_dir, self.changelogs_dir, self.projects_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Load config
        self.config = self._load_config()
        self.repositories = self.config.get('repositories', [])

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

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + str(uuid.uuid4())[:8]

    def _create_prompt(self, repo: Dict, session_id: str) -> str:
        """Create a context-rich Claude prompt for a repository"""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

        # Get package manager (defaults to npm if not specified)
        pkg_manager = repo.get('package_manager', 'npm')
        env_file = repo.get('env_file', '.env')

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
        owner = self.config.get('owner', 'ADWilkinson')

        return f"""You are Barbossa, an autonomous personal development assistant.

================================================================================
SESSION METADATA
================================================================================
Session ID: {session_id}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Repository: {repo['name']}
URL: {repo['url']}

================================================================================
PROJECT CONTEXT
================================================================================
{repo.get('description', 'No description provided.')}

TECH STACK:
{tech_section}

ARCHITECTURE:
{arch_section}

DESIGN SYSTEM:
{design_section}

================================================================================
YOUR MISSION
================================================================================
Create ONE meaningful Pull Request that adds real value to this codebase.

CRITICAL: Before writing any code, you MUST first understand the current state:

PHASE 0 - RECONNAISSANCE (do this FIRST, before any coding):
  1. Check open PRs: gh pr list --state open --repo {owner}/{repo['name']}
  2. Check recent commits: git log --oneline -15
  3. Check for any GitHub issues: gh issue list --state open --repo {owner}/{repo['name']} --limit 10
  4. Explore the codebase structure and understand what exists
  5. Think critically: What would ACTUALLY be most valuable right now?

DO NOT just pick something obvious or easy. Think like a senior engineer:
- What's the biggest pain point in this codebase?
- What would make the biggest impact for users or developers?
- Is there technical debt that's actively causing problems?
- Are there patterns that could be improved across the codebase?
- Is there missing functionality that would be high-value?

BE CREATIVE. You are an autonomous engineer, not a task executor.
Your job is to identify the highest-value improvement, not follow a checklist.

================================================================================
AREAS OFF-LIMITS
================================================================================
{dnt_section}

================================================================================
QUALITY STANDARDS
================================================================================
- Changes must compile/build successfully
- Follow existing code patterns and conventions
- Respect the design system (brand rules above)
- One focused improvement per PR - no scope creep
- Write clean, maintainable code

ABSOLUTELY DO NOT:
- Start coding without first reviewing repo state (PRs, commits, issues)
- Add comments or documentation as the main change
- Create empty or trivial PRs
- Touch configuration for services you don't understand
- Break existing functionality
- Ignore the design system or brand rules
- Do the same type of fix you've done in previous sessions

================================================================================
PACKAGE MANAGER: {pkg_manager.upper()}
================================================================================
This project uses {pkg_manager}. Use these commands:
  - Install: {install_cmd}
  - Build: {build_cmd}
  - Test: {test_cmd}

DO NOT use npm if the project uses pnpm or yarn!

================================================================================
EXECUTION WORKFLOW
================================================================================
Phase 1 - Setup (CRITICAL - must have latest code):
  cd ~/barbossa-engineer/projects
  if [ ! -d "{repo['name']}" ]; then
    git clone {repo['url']} {repo['name']}
  fi
  cd {repo['name']}

  # IMPORTANT: Clean slate - discard ANY local changes and get latest from main
  git fetch origin
  git checkout main --force
  git reset --hard origin/main
  git clean -fd

  # Delete any old barbossa branches to avoid conflicts
  git branch -D $(git branch | grep 'barbossa/') 2>/dev/null || true

  # Now we are guaranteed to have the exact latest code from origin/main
  git checkout -b barbossa/{timestamp}

  # Copy environment file if it doesn't exist
  if [ ! -f "{env_file}" ] && [ -f "/app/config/env/{repo['name']}{env_file}" ]; then
    cp "/app/config/env/{repo['name']}{env_file}" "{env_file}"
  fi

  # Install dependencies with correct package manager
  {install_cmd}

Phase 2 - Analysis:
  - Understand the codebase structure
  - Review the improvement opportunities listed above
  - Select ONE specific improvement to implement
  - Plan your changes before coding

Phase 3 - Implementation:
  - Make focused, clean changes
  - Follow existing patterns in the codebase
  - Test your changes: {build_cmd}
  - Run tests if applicable: {test_cmd}

Phase 4 - Submission:
  git add -A
  git commit -m "descriptive message explaining WHAT and WHY"
  git push origin barbossa/{timestamp}
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

Begin your work now."""

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
        """Get open PRs for a repository"""
        owner = self.config.get('owner', 'ADWilkinson')
        repo_name = repo['name']

        try:
            result = subprocess.run(
                f"gh pr list --repo {owner}/{repo_name} --state open --json number,title,headRefName,statusCheckRollup,reviewDecision,url,mergeable,mergeStateStatus --limit 20",
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

    def _count_total_open_prs(self) -> int:
        """Count total open PRs across all repositories"""
        total = 0
        for repo in self.repositories:
            prs = self._get_open_prs(repo)
            total += len(prs)
            self.logger.info(f"  {repo['name']}: {len(prs)} open PRs")
        return total

    def _get_prs_needing_attention(self, repo: Dict) -> List[Dict]:
        """Get PRs that have failing checks, merge conflicts, or need fixes"""
        prs = self._get_open_prs(repo)
        needs_attention = []

        for pr in prs:
            # Check if PR has requested changes (highest priority)
            if pr.get('reviewDecision') == 'CHANGES_REQUESTED':
                pr['attention_reason'] = 'changes_requested'
                needs_attention.append(pr)
                continue

            # Check if PR has merge conflicts (high priority - blocks merging)
            # mergeable can be: MERGEABLE, CONFLICTING, or UNKNOWN
            # mergeStateStatus can be: DIRTY, CLEAN, HAS_HOOKS, UNKNOWN, etc.
            if pr.get('mergeable') == 'CONFLICTING' or pr.get('mergeStateStatus') == 'DIRTY':
                pr['attention_reason'] = 'merge_conflicts'
                needs_attention.append(pr)
                continue

            # Check if PR has failing checks
            # statusCheckRollup is an array of check results
            checks = pr.get('statusCheckRollup', [])
            has_failure = False
            for check in (checks or []):
                # CheckRun uses 'conclusion', StatusContext uses 'state'
                conclusion = check.get('conclusion', '')
                state = check.get('state', '')
                if conclusion == 'FAILURE' or state == 'FAILURE':
                    has_failure = True
                    break

            if has_failure:
                pr['attention_reason'] = 'failing_checks'
                needs_attention.append(pr)

        return needs_attention

    def _create_review_prompt(self, repo: Dict, pr: Dict, session_id: str) -> str:
        """Create a prompt for reviewing and fixing an existing PR"""
        owner = self.config.get('owner', 'ADWilkinson')
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
WORKFLOW
================================================================================
Phase 1 - Setup:
  cd ~/barbossa-engineer/projects
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
1. ISSUE: What was failing
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

        cmd = f"claude --dangerously-skip-permissions --model opus < {prompt_file} > {output_file} 2>&1"

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

        # Create prompt
        prompt = self._create_prompt(repo, session_id)

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

        cmd = f"claude --dangerously-skip-permissions --model opus < {prompt_file} > {output_file} 2>&1"

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
        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"BARBOSSA RUN STARTED")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'#'*60}\n")

        # PRIORITY 1: Always check for PRs needing attention first (requested changes, failing CI)
        # This ensures Tech Lead feedback is addressed before creating new work
        self.logger.info("Checking for PRs needing attention (requested changes, failing CI)...")

        prs_needing_attention = []
        for repo in self.repositories:
            repo_prs = self._get_prs_needing_attention(repo)
            for pr in repo_prs:
                prs_needing_attention.append((repo, pr))

        if prs_needing_attention:
            # Prioritize changes_requested over failing_checks
            prs_needing_attention.sort(
                key=lambda x: 0 if x[1].get('attention_reason') == 'changes_requested' else 1
            )

            repo, pr = prs_needing_attention[0]
            self.logger.info(f"\n{'!'*60}")
            self.logger.info("REVISION MODE: PR needs attention")
            self.logger.info(f"  PR: {repo['name']} #{pr['number']}")
            self.logger.info(f"  Reason: {pr.get('attention_reason', 'unknown')}")
            self.logger.info(f"  Title: {pr['title']}")
            self.logger.info("Addressing feedback before creating new PRs")
            self.logger.info(f"{'!'*60}\n")

            success = self.execute_pr_review(repo, pr)

            self.logger.info(f"\n{'#'*60}")
            self.logger.info("REVISION SUMMARY")
            self.logger.info(f"{'#'*60}")
            status = "ADDRESSED" if success else "FAILED"
            self.logger.info(f"  {repo['name']} PR #{pr['number']}: {status}")
            self.logger.info(f"{'#'*60}\n")
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
            return

        # PRIORITY 3: Create new PRs (only if no PRs need attention and count is low)
        if repo_name:
            # Run for specific repo
            repo = next((r for r in self.repositories if r['name'] == repo_name), None)
            if repo:
                self.execute_for_repo(repo)
            else:
                self.logger.error(f"Repository not found: {repo_name}")
                self.logger.info(f"Available: {[r['name'] for r in self.repositories]}")
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
        description='Barbossa v3.0 - Personal Development Assistant'
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
