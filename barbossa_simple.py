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

        # Build improvement opportunities section
        improvements = repo.get('improvement_opportunities', [])
        if improvements:
            imp_lines = [f"  {i+1}. {imp}" for i, imp in enumerate(improvements)]
            improvements_section = "\n".join(imp_lines)
        else:
            improvements_section = "  (explore codebase to identify opportunities)"

        # Build do not touch section
        do_not_touch = repo.get('do_not_touch', [])
        if do_not_touch:
            dnt_lines = [f"  - {item}" for item in do_not_touch]
            dnt_section = "\n".join(dnt_lines)
        else:
            dnt_section = "  (no restrictions)"

        # Build example PRs section
        example_prs = repo.get('example_good_prs', [])
        if example_prs:
            ex_lines = [f"  - {ex}" for ex in example_prs]
            examples_section = "\n".join(ex_lines)
        else:
            examples_section = "  (use your judgment)"

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
Create ONE meaningful Pull Request that improves this codebase.

KNOWN IMPROVEMENT OPPORTUNITIES (pick ONE):
{improvements_section}

EXAMPLE GOOD PRs FOR THIS REPO:
{examples_section}

================================================================================
CRITICAL CONSTRAINTS
================================================================================
DO NOT TOUCH (these areas are off-limits):
{dnt_section}

QUALITY STANDARDS:
- Changes must compile/build successfully
- Follow existing code patterns and conventions
- Respect the design system (brand rules above)
- One focused improvement per PR - no scope creep
- Write clean, maintainable code

ABSOLUTELY DO NOT:
- Add comments or documentation as the main change
- Create empty or trivial PRs
- Touch configuration for services you don't understand
- Break existing functionality
- Ignore the design system or brand rules

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

        if repo_name:
            # Run for specific repo
            repo = next((r for r in self.repositories if r['name'] == repo_name), None)
            if repo:
                self.execute_for_repo(repo)
            else:
                self.logger.error(f"Repository not found: {repo_name}")
                self.logger.info(f"Available: {[r['name'] for r in self.repositories]}")
        else:
            # Run for all repos
            results = []
            for repo in self.repositories:
                success = self.execute_for_repo(repo)
                results.append((repo['name'], success))

            # Summary
            self.logger.info(f"\n{'#'*60}")
            self.logger.info("RUN SUMMARY")
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
