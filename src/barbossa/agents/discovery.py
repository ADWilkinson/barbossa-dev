#!/usr/bin/env python3
"""
Barbossa Discovery v5.8 - Autonomous Feature Discovery Agent
Runs 3x daily (06:00, 14:00, 22:00) to find improvements and create Issues.
Keeps the backlog fed so Engineers always have work to pick from.

Part of the Pipeline:
- Discovery (3x daily) → creates Issues in backlog  <-- THIS AGENT
- Engineer (:00) → implements from backlog, creates PRs
- Tech Lead (:35) → reviews PRs, merges or requests changes
- Auditor (daily 06:30) → system health analysis

Discovery Types:
1. Code Analysis - TODOs, FIXMEs, missing tests, accessibility gaps
2. UX Improvements - Loading states, error handling, empty states
3. Cleanup - Console.logs, dead code, inconsistencies

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
from barbossa.utils.issue_tracker import get_issue_tracker, IssueTracker
from barbossa.utils.notifications import (
    notify_agent_run_complete,
    notify_error,
    wait_for_pending
)


class BarbossaDiscovery:
    """Autonomous discovery agent that creates issues for the pipeline."""

    VERSION = "1.7.2"  # Fix: wait for webhook notifications before process exit
    DEFAULT_BACKLOG_THRESHOLD = 20

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
        settings = self.config.get('settings', {}).get('discovery', {})
        self.enabled = settings.get('enabled', True)
        self.BACKLOG_THRESHOLD = settings.get('max_backlog_issues', self.DEFAULT_BACKLOG_THRESHOLD)

        # Issue tracker type for logging
        tracker_type = self.config.get('issue_tracker', {}).get('type', 'github')

        self.logger.info("=" * 60)
        self.logger.info(f"BARBOSSA DISCOVERY v{self.VERSION}")
        self.logger.info(f"Repositories: {len(self.repositories)}")
        self.logger.info(f"Issue Tracker: {tracker_type}")
        self.logger.info(f"Settings: max_backlog_issues={self.BACKLOG_THRESHOLD}")
        self.logger.info("=" * 60)

    def _setup_logging(self):
        log_file = self.logs_dir / f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('discovery')

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
            return None
        except Exception as e:
            self.logger.warning(f"Command failed: {cmd} - {e}")
            return None

    def _get_issue_tracker(self, repo_name: str) -> IssueTracker:
        """Get the issue tracker for a repository."""
        return get_issue_tracker(self.config, repo_name, self.logger)

    def _get_backlog_count(self, repo_name: str) -> int:
        """Count open issues labeled 'backlog' for a repo."""
        try:
            tracker = self._get_issue_tracker(repo_name)
            return tracker.get_backlog_count(label="backlog")
        except Exception as e:
            self.logger.warning(f"Failed to get backlog count: {e}")
            return 0

    def _get_existing_issue_titles(self, repo_name: str) -> List[str]:
        """Get titles of existing open issues to avoid duplicates."""
        try:
            tracker = self._get_issue_tracker(repo_name)
            return tracker.get_existing_titles(limit=50)
        except Exception as e:
            self.logger.warning(f"Failed to get existing titles: {e}")
            return []

    def _create_issue(self, repo_name: str, title: str, body: str, labels: List[str] = None) -> bool:
        """Create an issue using the configured tracker."""
        labels = labels or ['backlog', 'discovery']
        try:
            tracker = self._get_issue_tracker(repo_name)
            issue = tracker.create_issue(title=title, body=body, labels=labels)
            if issue:
                self.logger.info(f"Created issue: {title}")
                self.logger.info(f"  URL: {issue.url}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to create issue: {e}")
            return False

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

    def _analyze_todos(self, repo_path: Path) -> List[Dict]:
        """Find TODO, FIXME, HACK, XXX comments."""
        findings = []
        patterns = ['TODO', 'FIXME', 'HACK', 'XXX']

        for pattern in patterns:
            result = self._run_cmd(
                f"grep -rn '{pattern}' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=dist . | head -20",
                cwd=str(repo_path)
            )
            if result:
                for line in result.split('\n')[:5]:  # Limit to 5 per pattern
                    if line.strip():
                        findings.append({
                            'type': 'todo',
                            'pattern': pattern,
                            'location': line.split(':')[0] if ':' in line else 'unknown',
                            'content': line
                        })

        return findings[:10]  # Max 10 findings

    def _analyze_missing_loading_states(self, repo_path: Path) -> List[Dict]:
        """Find components that fetch data but have no loading state."""
        findings = []

        # Find files with fetch/useQuery but no loading/isLoading
        result = self._run_cmd(
            "grep -rl 'useQuery\\|useFetch\\|fetch(' --include='*.tsx' --exclude-dir=node_modules --exclude-dir=.next . | head -10",
            cwd=str(repo_path)
        )

        if result:
            for file in result.split('\n'):
                if not file.strip():
                    continue
                # Check if file has loading state handling
                has_loading = self._run_cmd(
                    f"grep -l 'isLoading\\|loading\\|Skeleton\\|Spinner' '{file}'",
                    cwd=str(repo_path)
                )
                if not has_loading:
                    findings.append({
                        'type': 'missing_loading',
                        'file': file,
                        'suggestion': 'Add loading skeleton or spinner'
                    })

        return findings[:5]

    def _analyze_missing_error_handling(self, repo_path: Path) -> List[Dict]:
        """Find components that fetch data but have no error handling."""
        findings = []

        result = self._run_cmd(
            "grep -rl 'useQuery\\|useFetch\\|fetch(' --include='*.tsx' --exclude-dir=node_modules --exclude-dir=.next . | head -10",
            cwd=str(repo_path)
        )

        if result:
            for file in result.split('\n'):
                if not file.strip():
                    continue
                has_error = self._run_cmd(
                    f"grep -l 'isError\\|error\\|catch\\|ErrorBoundary' '{file}'",
                    cwd=str(repo_path)
                )
                if not has_error:
                    findings.append({
                        'type': 'missing_error_handling',
                        'file': file,
                        'suggestion': 'Add error state handling'
                    })

        return findings[:5]

    def _analyze_accessibility(self, repo_path: Path) -> List[Dict]:
        """Find accessibility issues - missing alt, aria labels, etc."""
        findings = []

        # Images without alt
        result = self._run_cmd(
            "grep -rn '<img' --include='*.tsx' --include='*.jsx' --exclude-dir=node_modules --exclude-dir=.next . | grep -v 'alt=' | head -5",
            cwd=str(repo_path)
        )
        if result:
            for line in result.split('\n'):
                if line.strip():
                    findings.append({
                        'type': 'a11y',
                        'issue': 'Image missing alt attribute',
                        'location': line.split(':')[0]
                    })

        # Buttons without aria-label (icon buttons)
        result = self._run_cmd(
            "grep -rn '<button' --include='*.tsx' --exclude-dir=node_modules --exclude-dir=.next . | grep -v 'aria-label' | grep -v '>' | head -5",
            cwd=str(repo_path)
        )
        if result:
            for line in result.split('\n'):
                if line.strip() and 'Icon' in line:
                    findings.append({
                        'type': 'a11y',
                        'issue': 'Icon button missing aria-label',
                        'location': line.split(':')[0]
                    })

        return findings[:5]

    def _analyze_console_logs(self, repo_path: Path) -> List[Dict]:
        """Find console.log statements that should be removed."""
        findings = []

        result = self._run_cmd(
            "grep -rn 'console\\.log' --include='*.ts' --include='*.tsx' --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=dist . | grep -v '.test.' | head -10",
            cwd=str(repo_path)
        )

        if result:
            files_with_logs = set()
            for line in result.split('\n'):
                if line.strip():
                    file = line.split(':')[0]
                    files_with_logs.add(file)

            if files_with_logs:
                findings.append({
                    'type': 'cleanup',
                    'issue': 'Console.log statements in production code',
                    'files': list(files_with_logs)[:5]
                })

        return findings

    def _generate_issue_from_findings(self, repo_name: str, findings: List[Dict], category: str) -> Optional[Dict]:
        """Generate a GitHub Issue from findings."""
        if not findings:
            return None

        if category == 'todo':
            title = f"fix: address {len(findings)} TODO/FIXME comments"
            body = """## Summary
Found several TODO/FIXME/HACK comments that should be addressed.

## Findings
"""
            for f in findings:
                body += f"- `{f['location']}`: {f['pattern']}\n"

            body += """
## Acceptance Criteria
- [ ] Address each TODO/FIXME comment
- [ ] Either implement the fix or remove if no longer relevant
- [ ] Run build and tests to verify

---
*Created by Barbossa Discovery Agent*
"""

        elif category == 'loading':
            title = f"feat: add loading states to {len(findings)} components"
            body = """## Summary
Found components that fetch data but don't show loading states.

## Files Missing Loading States
"""
            for f in findings:
                body += f"- `{f['file']}`\n"

            body += """
## Acceptance Criteria
- [ ] Add loading skeletons or spinners to each component
- [ ] Match existing loading patterns in codebase
- [ ] Test loading state appears before data loads

---
*Created by Barbossa Discovery Agent*
"""

        elif category == 'error':
            title = f"feat: add error handling to {len(findings)} components"
            body = """## Summary
Found components that fetch data but don't handle errors gracefully.

## Files Missing Error Handling
"""
            for f in findings:
                body += f"- `{f['file']}`\n"

            body += """
## Acceptance Criteria
- [ ] Add error state UI to each component
- [ ] Show user-friendly error message
- [ ] Add retry functionality where appropriate

---
*Created by Barbossa Discovery Agent*
"""

        elif category == 'a11y':
            title = f"a11y: fix {len(findings)} accessibility issues"
            body = """## Summary
Found accessibility issues that should be fixed for better UX.

## Issues Found
"""
            for f in findings:
                body += f"- `{f['location']}`: {f['issue']}\n"

            body += """
## Acceptance Criteria
- [ ] Add missing alt attributes to images
- [ ] Add aria-labels to icon buttons
- [ ] Run accessibility audit to verify fixes

---
*Created by Barbossa Discovery Agent*
"""

        elif category == 'cleanup':
            files = findings[0].get('files', []) if findings else []
            title = "chore: remove console.log statements"
            body = """## Summary
Found console.log statements in production code that should be removed.

## Files
"""
            for f in files:
                body += f"- `{f}`\n"

            body += """
## Acceptance Criteria
- [ ] Remove or replace with proper logging
- [ ] Keep any intentional debug logs (mark with // eslint-disable-line)
- [ ] Verify build passes

---
*Created by Barbossa Discovery Agent*
"""

        else:
            return None

        return {'title': title, 'body': body}

    def discover_for_repo(self, repo: Dict) -> int:
        """Run discovery for a single repository. Returns number of issues created."""
        repo_name = repo['name']
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"DISCOVERING: {repo_name}")
        self.logger.info(f"{'='*60}")

        # Check backlog size
        backlog_count = self._get_backlog_count(repo_name)
        self.logger.info(f"Current backlog: {backlog_count} issues")

        if backlog_count >= self.BACKLOG_THRESHOLD:
            self.logger.info(f"Backlog full (>= {self.BACKLOG_THRESHOLD}), skipping discovery")
            return 0

        # Clone/update repo
        repo_path = self._clone_or_update_repo(repo)
        if not repo_path:
            self.logger.error(f"Could not access repo: {repo_name}")
            return 0

        # Get existing issues to avoid duplicates
        existing_titles = self._get_existing_issue_titles(repo_name)

        issues_created = 0
        issues_needed = self.BACKLOG_THRESHOLD - backlog_count

        # Run analyses
        analyses = [
            ('todo', self._analyze_todos(repo_path)),
            ('loading', self._analyze_missing_loading_states(repo_path)),
            ('error', self._analyze_missing_error_handling(repo_path)),
            ('a11y', self._analyze_accessibility(repo_path)),
            ('cleanup', self._analyze_console_logs(repo_path)),
        ]

        for category, findings in analyses:
            if issues_created >= issues_needed:
                break

            if not findings:
                continue

            issue = self._generate_issue_from_findings(repo_name, findings, category)
            if not issue:
                continue

            # Check for duplicate
            if issue['title'].lower() in existing_titles:
                self.logger.info(f"Skipping duplicate: {issue['title']}")
                continue

            # Create the issue
            if self._create_issue(repo_name, issue['title'], issue['body']):
                issues_created += 1
                existing_titles.append(issue['title'].lower())

        self.logger.info(f"Created {issues_created} issues for {repo_name}")
        return issues_created

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + str(uuid.uuid4())[:8]

    def run(self):
        """Run discovery for all repositories."""
        run_session_id = self._generate_session_id()

        if not self.enabled:
            self.logger.info("Discovery is disabled in config. Skipping.")
            return 0

        self.logger.info(f"\n{'#'*60}")
        self.logger.info("BARBOSSA DISCOVERY RUN")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'#'*60}\n")

        # Track run start (fire-and-forget, never blocks)
        track_run_start("discovery", run_session_id, len(self.repositories))

        total_issues = 0
        errors = 0
        for repo in self.repositories:
            try:
                issues = self.discover_for_repo(repo)
                total_issues += issues
            except Exception as e:
                self.logger.error(f"Error discovering for {repo['name']}: {e}")
                errors += 1
                notify_error(
                    agent='discovery',
                    error_message=str(e),
                    context="Scanning repository for improvements",
                    repo_name=repo['name']
                )

        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"DISCOVERY COMPLETE: {total_issues} issues created")
        self.logger.info(f"{'#'*60}\n")

        # Track run end (fire-and-forget)
        track_run_end("discovery", run_session_id, success=True, pr_created=False)

        # Send run summary notification (only if something happened)
        if total_issues > 0 or errors > 0:
            notify_agent_run_complete(
                agent='discovery',
                success=(errors == 0),
                summary=f"Created {total_issues} backlog issue(s) across {len(self.repositories)} repositories",
                details={
                    'Issues Created': total_issues,
                    'Repositories': len(self.repositories),
                    'Errors': errors
                }
            )

        # Ensure all notifications complete before process exits
        wait_for_pending()
        return total_issues


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Barbossa Discovery Agent')
    parser.add_argument('--repo', help='Run for specific repo only')
    args = parser.parse_args()

    discovery = BarbossaDiscovery()

    if args.repo:
        repo = next((r for r in discovery.repositories if r['name'] == args.repo), None)
        if repo:
            discovery.discover_for_repo(repo)
        else:
            print(f"Repo not found: {args.repo}")
    else:
        discovery.run()


if __name__ == "__main__":
    main()
