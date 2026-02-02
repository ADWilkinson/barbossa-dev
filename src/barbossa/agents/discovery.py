#!/usr/bin/env python3
"""
Barbossa Discovery v2.2.0 - Autonomous Feature Discovery Agent
Runs 6x daily to find improvements and curate Issues.
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


class BarbossaDiscovery:
    """Autonomous discovery agent that creates issues for the pipeline."""

    VERSION = "2.2.0"
    DEFAULT_BACKLOG_THRESHOLD = 20
    DEFAULT_PRECISION_MODE = "high"
    DEFAULT_ITERATION_RATIO = 0.5
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
        settings = self.config.get('settings', {}).get('discovery', {})
        self.enabled = settings.get('enabled', True)
        self.BACKLOG_THRESHOLD = settings.get('max_backlog_issues', self.DEFAULT_BACKLOG_THRESHOLD)
        self.precision_mode = settings.get('precision_mode', self.DEFAULT_PRECISION_MODE)
        self.iteration_ratio = settings.get('iteration_ratio', self.DEFAULT_ITERATION_RATIO)
        self.min_hours_since_curation = settings.get('min_hours_since_curation', self.DEFAULT_MIN_HOURS_SINCE_CURATION)

        # Issue tracker type for logging
        tracker_type = self.config.get('issue_tracker', {}).get('type', 'github')

        self.logger.info("=" * 60)
        self.logger.info(f"BARBOSSA DISCOVERY v{self.VERSION}")
        self.logger.info(f"Repositories: {len(self.repositories)}")
        self.logger.info(f"Issue Tracker: {tracker_type}")
        self.logger.info(f"Settings: max_backlog_issues={self.BACKLOG_THRESHOLD}, precision_mode={self.precision_mode}")
        self.logger.info(f"Curation: iteration_ratio={self.iteration_ratio}, min_hours={self.min_hours_since_curation}")
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
            return None
        except Exception as e:
            self.logger.warning(f"Command failed: {cmd} - {e}")
            return None

    def _get_issue_tracker(self, repo_name: str) -> GitHubIssueTracker:
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
                        parts = line.split(':', 2)
                        file_path = parts[0] if len(parts) > 0 else 'unknown'
                        line_no = parts[1] if len(parts) > 1 else '?'
                        content = parts[2].strip() if len(parts) > 2 else line
                        findings.append({
                            'type': 'todo',
                            'pattern': pattern,
                            'file': file_path,
                            'line': line_no,
                            'content': content
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
                    parts = line.split(':', 2)
                    file_path = parts[0] if len(parts) > 0 else 'unknown'
                    line_no = parts[1] if len(parts) > 1 else '?'
                    content = parts[2].strip() if len(parts) > 2 else line
                    findings.append({
                        'type': 'a11y',
                        'issue': 'Image missing alt attribute',
                        'file': file_path,
                        'line': line_no,
                        'content': content
                    })

        # Buttons without aria-label (icon buttons)
        result = self._run_cmd(
            "grep -rn '<button' --include='*.tsx' --exclude-dir=node_modules --exclude-dir=.next . | grep -v 'aria-label' | grep -v '>' | head -5",
            cwd=str(repo_path)
        )
        if result:
            for line in result.split('\n'):
                if line.strip() and 'Icon' in line:
                    parts = line.split(':', 2)
                    file_path = parts[0] if len(parts) > 0 else 'unknown'
                    line_no = parts[1] if len(parts) > 1 else '?'
                    content = parts[2].strip() if len(parts) > 2 else line
                    findings.append({
                        'type': 'a11y',
                        'issue': 'Icon button missing aria-label',
                        'file': file_path,
                        'line': line_no,
                        'content': content
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

## Evidence
"""
            for f in findings:
                file_path = f.get('file', 'unknown')
                line_no = f.get('line', '?')
                content = f.get('content', '').strip()
                body += f"- `{file_path}:{line_no}` — {content}\n"

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

## Evidence (Heuristic - verify before coding)
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

## Evidence (Heuristic - verify before coding)
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

## Evidence
"""
            for f in findings:
                file_path = f.get('file', 'unknown')
                line_no = f.get('line', '?')
                content = f.get('content', '').strip()
                body += f"- `{file_path}:{line_no}` — {f['issue']} — {content}\n"

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

## Evidence (Heuristic - verify before coding)
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

    def _get_issues_needing_validation(self, repo_name: str) -> List[Issue]:
        """Find discovery issues that need validation (haven't been curated recently)."""
        tracker = self._get_issue_tracker(repo_name)
        issues = tracker.list_issues(labels=['discovery'], state='open', limit=50)

        now = datetime.now(timezone.utc)
        needs_validation = []

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

            needs_validation.append(issue)

        self.logger.info(f"Found {len(needs_validation)} discovery issues needing validation")
        return needs_validation

    def _validate_issue_evidence(self, repo_path: Path, issue: Issue) -> Dict:
        """Check if the evidence in a discovery issue still exists in the code.

        Returns dict with:
        - still_valid: bool - whether evidence still exists
        - evidence_count: int - number of matching items found
        - details: str - what was found
        """
        body = issue.body or ''
        title = issue.title.lower()

        # Determine issue type and validate
        if 'todo' in title or 'fixme' in title:
            return self._validate_todo_evidence(repo_path, body)
        elif 'console.log' in title:
            return self._validate_console_log_evidence(repo_path)
        elif 'loading' in title:
            return self._validate_loading_evidence(repo_path, body)
        elif 'error handling' in title:
            return self._validate_error_evidence(repo_path, body)
        elif 'a11y' in title or 'accessibility' in title:
            return self._validate_a11y_evidence(repo_path, body)

        # Unknown type - assume still valid
        return {'still_valid': True, 'evidence_count': 0, 'details': 'Could not validate (unknown issue type)'}

    def _validate_todo_evidence(self, repo_path: Path, body: str) -> Dict:
        """Check if TODO/FIXME comments mentioned in issue still exist."""
        import re

        # Extract file references from body
        file_refs = re.findall(r'`([^`]+\.(ts|tsx|js|jsx)):(\d+)`', body)

        if not file_refs:
            # No specific files, do general check
            result = self._run_cmd(
                "grep -rn 'TODO\\|FIXME\\|HACK\\|XXX' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=dist . | wc -l",
                cwd=str(repo_path)
            )
            count = int(result.strip()) if result and result.strip().isdigit() else 0
            return {
                'still_valid': count > 0,
                'evidence_count': count,
                'details': f'{count} TODO/FIXME comments found in codebase'
            }

        # Check specific files
        found_count = 0
        for file_path, ext, line_no in file_refs:
            full_path = repo_path / file_path.lstrip('./')
            if full_path.exists():
                result = self._run_cmd(f"grep -n 'TODO\\|FIXME\\|HACK\\|XXX' '{full_path}'", cwd=str(repo_path))
                if result:
                    found_count += len(result.strip().split('\n'))

        return {
            'still_valid': found_count > 0,
            'evidence_count': found_count,
            'details': f'{found_count} TODO/FIXME comments still found in referenced files'
        }

    def _validate_console_log_evidence(self, repo_path: Path) -> Dict:
        """Check if console.log statements still exist."""
        result = self._run_cmd(
            "grep -rn 'console\\.log' --include='*.ts' --include='*.tsx' --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=dist . | grep -v '.test.' | wc -l",
            cwd=str(repo_path)
        )
        count = int(result.strip()) if result and result.strip().isdigit() else 0
        return {
            'still_valid': count > 0,
            'evidence_count': count,
            'details': f'{count} console.log statements found'
        }

    def _validate_loading_evidence(self, repo_path: Path, body: str) -> Dict:
        """Check if files without loading states still exist."""
        import re
        file_refs = re.findall(r'`([^`]+\.tsx?)`', body)

        if not file_refs:
            return {'still_valid': True, 'evidence_count': 0, 'details': 'No files to validate'}

        still_missing = 0
        for file_path in file_refs:
            full_path = repo_path / file_path.lstrip('./')
            if full_path.exists():
                has_loading = self._run_cmd(
                    f"grep -l 'isLoading\\|loading\\|Skeleton\\|Spinner' '{full_path}'",
                    cwd=str(repo_path)
                )
                if not has_loading:
                    still_missing += 1

        return {
            'still_valid': still_missing > 0,
            'evidence_count': still_missing,
            'details': f'{still_missing} files still missing loading states'
        }

    def _validate_error_evidence(self, repo_path: Path, body: str) -> Dict:
        """Check if files without error handling still exist."""
        import re
        file_refs = re.findall(r'`([^`]+\.tsx?)`', body)

        if not file_refs:
            return {'still_valid': True, 'evidence_count': 0, 'details': 'No files to validate'}

        still_missing = 0
        for file_path in file_refs:
            full_path = repo_path / file_path.lstrip('./')
            if full_path.exists():
                has_error = self._run_cmd(
                    f"grep -l 'isError\\|error\\|catch\\|ErrorBoundary' '{full_path}'",
                    cwd=str(repo_path)
                )
                if not has_error:
                    still_missing += 1

        return {
            'still_valid': still_missing > 0,
            'evidence_count': still_missing,
            'details': f'{still_missing} files still missing error handling'
        }

    def _validate_a11y_evidence(self, repo_path: Path, body: str) -> Dict:
        """Check if accessibility issues still exist."""
        # Check for images without alt
        result = self._run_cmd(
            "grep -rn '<img' --include='*.tsx' --include='*.jsx' --exclude-dir=node_modules --exclude-dir=.next . | grep -v 'alt=' | wc -l",
            cwd=str(repo_path)
        )
        count = int(result.strip()) if result and result.strip().isdigit() else 0
        return {
            'still_valid': count > 0,
            'evidence_count': count,
            'details': f'{count} images without alt attributes found'
        }

    def _iterate_on_discovery_issue(self, repo_path: Path, issue: Issue, repo_name: str) -> str:
        """Validate and update a discovery issue. Returns action taken."""
        tracker = self._get_issue_tracker(repo_name)

        # Validate evidence
        validation = self._validate_issue_evidence(repo_path, issue)

        if not validation['still_valid']:
            # Close the issue - problem has been fixed
            reason = f"Automatically closed: Evidence no longer found in codebase. {validation['details']}"
            tracker.close_issue(int(issue.id), reason)
            self.logger.info(f"CLOSED issue #{issue.id}: evidence no longer exists")
            return "closed"

        # Evidence still exists - update with current count and curation marker
        updated_body = issue.body or ''

        # Add validation note if evidence count changed significantly
        if validation['evidence_count'] > 0:
            validation_note = f"\n\n**Last Validation:** {validation['details']}"
            # Remove old validation note if present
            import re
            updated_body = re.sub(r'\n\n\*\*Last Validation:\*\*[^\n]*', '', updated_body)
            # Add before footer
            if '---' in updated_body:
                parts = updated_body.rsplit('---', 1)
                updated_body = parts[0].rstrip() + validation_note + '\n\n---' + parts[1]
            else:
                updated_body += validation_note

        # Update curation marker
        updated_body = update_curation_marker(updated_body, datetime.now(timezone.utc), "Barbossa Discovery Agent", self.VERSION)

        tracker.update_issue(int(issue.id), body=updated_body)
        self.logger.info(f"VALIDATED issue #{issue.id}: {validation['details']}")
        return "validated"

    def discover_for_repo(self, repo: Dict) -> int:
        """Run discovery for a single repository.

        Curation Mode (v2.2.0):
        1. First: validate existing issues (close if fixed, update if still valid)
        2. Then: create new issues from fresh analysis
        """
        repo_name = repo['name']
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"DISCOVERING: {repo_name}")
        self.logger.info(f"{'='*60}")

        # Check backlog size
        backlog_count = self._get_backlog_count(repo_name)
        self.logger.info(f"Current backlog: {backlog_count} issues")

        # Clone/update repo first (needed for validation)
        repo_path = self._clone_or_update_repo(repo)
        if not repo_path:
            self.logger.error(f"Could not access repo: {repo_name}")
            return 0

        issues_validated = 0
        issues_closed = 0
        issues_created = 0

        # Phase 1: Validate existing discovery issues
        max_validations = max(1, int(5 * self.iteration_ratio))  # Cap at 5 * ratio
        self.logger.info(f"\n--- PHASE 1: Validating existing issues (max {max_validations}) ---")

        issues_needing_validation = self._get_issues_needing_validation(repo_name)

        for issue in issues_needing_validation[:max_validations]:
            self.logger.info(f"Validating issue #{issue.id}: {issue.title}")
            action = self._iterate_on_discovery_issue(repo_path, issue, repo_name)
            if action == 'closed':
                issues_closed += 1
            elif action == 'validated':
                issues_validated += 1

        self.logger.info(f"Validated {issues_validated}, closed {issues_closed} issues")

        # Refresh backlog count after closures
        if issues_closed > 0:
            backlog_count = self._get_backlog_count(repo_name)
            self.logger.info(f"Updated backlog count: {backlog_count} issues")

        # Phase 2: Create new issues if backlog allows
        if backlog_count >= self.BACKLOG_THRESHOLD:
            self.logger.info(f"Backlog full (>= {self.BACKLOG_THRESHOLD}), skipping new issue creation")
            return issues_validated + issues_closed

        self.logger.info(f"\n--- PHASE 2: Creating new issues ---")

        # Get existing issues to avoid duplicates
        existing_titles = self._get_existing_issue_titles(repo_name)

        issues_needed = self.BACKLOG_THRESHOLD - backlog_count

        # Run analyses (precision mode controls signal quality)
        precision = (self.precision_mode or "").lower()
        if precision not in ["high", "balanced", "experimental"]:
            self.logger.warning(f"Unknown precision_mode '{self.precision_mode}', defaulting to high")
            precision = "high"

        analyses = [
            ('todo', self._analyze_todos(repo_path)),
        ]

        if precision in ["balanced", "experimental"]:
            analyses.extend([
                ('loading', self._analyze_missing_loading_states(repo_path)),
                ('error', self._analyze_missing_error_handling(repo_path)),
            ])

        if precision == "experimental":
            analyses.extend([
                ('a11y', self._analyze_accessibility(repo_path)),
                ('cleanup', self._analyze_console_logs(repo_path)),
            ])

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

        total = issues_validated + issues_closed + issues_created
        self.logger.info(f"\nTotal actions: {issues_validated} validated, {issues_closed} closed, {issues_created} created")
        return total

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

        # Process any pending webhook retries from previous runs
        process_retry_queue()

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
