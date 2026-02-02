#!/usr/bin/env python3
"""
GitHub Issue Tracker for Barbossa

Provides issue tracking via GitHub Issues using the gh CLI.
"""

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


# Curation marker pattern for parsing/updating issue footers
CURATION_MARKER_PATTERN = r'\*Last Curated: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\*'
BARBOSSA_FOOTER_PATTERN = r'---\s*\n\*Created by Barbossa .+\*'


@dataclass
class Issue:
    """GitHub issue representation."""
    id: str
    identifier: str  # "#123"
    title: str
    body: Optional[str]
    state: str
    labels: List[str]
    url: str
    updated_at: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_github(cls, gh_data: Dict) -> 'Issue':
        return cls(
            id=str(gh_data.get('number', '')),
            identifier=f"#{gh_data.get('number', '')}",
            title=gh_data.get('title', ''),
            body=gh_data.get('body', ''),
            state=gh_data.get('state', ''),
            labels=[l.get('name', '') for l in gh_data.get('labels', [])],
            url=gh_data.get('url', ''),
            updated_at=gh_data.get('updatedAt'),
            created_at=gh_data.get('createdAt')
        )


class GitHubIssueTracker:
    """GitHub Issues implementation using gh CLI."""

    def __init__(self, owner: str, repo: str, logger: Optional[logging.Logger] = None):
        self.owner = owner
        self.repo = repo
        self.logger = logger or logging.getLogger('github_tracker')

    def _run_cmd(self, cmd: str, timeout: int = 60) -> Optional[str]:
        """Run a shell command and return output."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout.strip()
            if result.stderr:
                self.logger.warning(f"Command failed (exit {result.returncode}): {result.stderr.strip()}")
            return None
        except Exception as e:
            self.logger.warning(f"Command failed: {cmd} - {e}")
            return None

    def get_backlog_count(self, label: str = "backlog") -> int:
        result = self._run_cmd(
            f"gh issue list --repo {self.owner}/{self.repo} --label {label} --state open --json number"
        )
        if result:
            try:
                issues = json.loads(result)
                return len(issues)
            except json.JSONDecodeError:
                pass
        return 0

    def get_existing_titles(self, limit: int = 50) -> List[str]:
        result = self._run_cmd(
            f"gh issue list --repo {self.owner}/{self.repo} --state open --limit {limit} --json title"
        )
        if result:
            try:
                issues = json.loads(result)
                return [i['title'].lower() for i in issues]
            except json.JSONDecodeError:
                pass
        return []

    def list_issues(
        self,
        labels: Optional[List[str]] = None,
        state: Optional[str] = None,
        limit: int = 50
    ) -> List[Issue]:
        cmd = f"gh issue list --repo {self.owner}/{self.repo} --limit {limit} --json number,title,body,state,labels,url,updatedAt,createdAt"
        if labels:
            cmd += f" --label {','.join(labels)}"
        if state:
            cmd += f" --state {state}"
        else:
            cmd += " --state open"

        result = self._run_cmd(cmd)
        if not result:
            return []

        try:
            issues_data = json.loads(result)
            return [Issue.from_github(d) for d in issues_data]
        except json.JSONDecodeError:
            return []

    def _ensure_label_exists(self, label: str) -> bool:
        """Create label if it doesn't exist."""
        check_cmd = f'gh label list --repo {self.owner}/{self.repo} --search "{label}" --json name'
        result = self._run_cmd(check_cmd, timeout=15)

        if result:
            try:
                existing = json.loads(result)
                if any(l.get('name', '').lower() == label.lower() for l in existing):
                    return True
            except json.JSONDecodeError:
                pass

        colors = {
            'quality': 'd93f0b',
            'backlog': '0e8a16',
            'discovery': '1d76db',
            'feature': 'a2eeef',
            'product': 'f9d0c4',
        }
        color = colors.get(label, 'ededed')

        create_cmd = f'gh label create "{label}" --repo {self.owner}/{self.repo} --color "{color}" --force 2>/dev/null || true'
        self._run_cmd(create_cmd, timeout=15)
        self.logger.info(f"Created label '{label}' on {self.owner}/{self.repo}")
        return True

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> Optional[Issue]:
        import tempfile

        labels = labels or ['backlog']

        for label in labels:
            self._ensure_label_exists(label)

        label_str = ','.join(labels)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(body)
            body_file = f.name

        try:
            escaped_title = title.replace('"', '\\"')
            cmd = f'gh issue create --repo {self.owner}/{self.repo} --title "{escaped_title}" --body-file {body_file} --label "{label_str}"'
            result = self._run_cmd(cmd, timeout=30)

            if result:
                self.logger.info(f"Created issue: {title}")
                self.logger.info(f"  URL: {result}")
                if '/issues/' in result:
                    number = result.split('/issues/')[-1]
                    return Issue(
                        id=number,
                        identifier=f"#{number}",
                        title=title,
                        body=body,
                        state='open',
                        labels=labels,
                        url=result
                    )
            return None
        finally:
            os.unlink(body_file)

    def get_issue_list_command(self, labels: Optional[List[str]] = None, limit: int = 10) -> str:
        cmd = f"gh issue list --repo {self.owner}/{self.repo} --state open --limit {limit}"
        if labels:
            cmd += f" --label {','.join(labels)}"
        return cmd

    def get_pr_link_instruction(self, issue_id: str) -> str:
        return f'Include "Closes #{issue_id}" in your PR description to automatically close the issue when merged.'

    def get_issue_details(self, issue_number: int) -> Optional[Issue]:
        """Fetch a single issue with full body and timestamps."""
        result = self._run_cmd(
            f"gh issue view {issue_number} --repo {self.owner}/{self.repo} --json number,title,body,state,labels,url,updatedAt,createdAt"
        )
        if not result:
            return None
        try:
            data = json.loads(result)
            return Issue.from_github(data)
        except json.JSONDecodeError:
            return None

    def update_issue(
        self,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None
    ) -> bool:
        """Edit an existing issue via gh issue edit."""
        import tempfile

        cmd_parts = [f"gh issue edit {issue_number} --repo {self.owner}/{self.repo}"]

        if title:
            escaped_title = title.replace('"', '\\"')
            cmd_parts.append(f'--title "{escaped_title}"')

        body_file = None
        if body is not None:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(body)
                body_file = f.name
            cmd_parts.append(f"--body-file {body_file}")

        if add_labels:
            for label in add_labels:
                self._ensure_label_exists(label)
            cmd_parts.append(f"--add-label \"{','.join(add_labels)}\"")

        if remove_labels:
            cmd_parts.append(f"--remove-label \"{','.join(remove_labels)}\"")

        cmd = " ".join(cmd_parts)
        try:
            result = self._run_cmd(cmd, timeout=30)
            if result is not None or self._run_cmd(f"gh issue view {issue_number} --repo {self.owner}/{self.repo} --json number", timeout=10):
                self.logger.info(f"Updated issue #{issue_number}")
                return True
            return False
        finally:
            if body_file:
                os.unlink(body_file)

    def close_issue(self, issue_number: int, reason: Optional[str] = None) -> bool:
        """Close an issue with an optional comment."""
        if reason:
            comment_cmd = f'gh issue comment {issue_number} --repo {self.owner}/{self.repo} --body "{reason}"'
            self._run_cmd(comment_cmd, timeout=15)

        result = self._run_cmd(
            f"gh issue close {issue_number} --repo {self.owner}/{self.repo}",
            timeout=15
        )
        if result is not None:
            self.logger.info(f"Closed issue #{issue_number}")
            return True
        return False


def get_last_curation_timestamp(body: str) -> Optional[datetime]:
    """Parse 'Last Curated: YYYY-MM-DDTHH:MM:SSZ' from issue body footer."""
    if not body:
        return None
    match = re.search(CURATION_MARKER_PATTERN, body)
    if match:
        try:
            return datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


def update_curation_marker(body: str, timestamp: datetime, agent_name: str = "Barbossa", version: str = "2.2.0") -> str:
    """Add or update the curation marker in the issue body footer."""
    ts_str = timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')
    new_footer = f"---\n*Created by {agent_name} v{version}*\n*Last Curated: {ts_str}*"

    # Check if there's already a Barbossa footer
    if re.search(BARBOSSA_FOOTER_PATTERN, body):
        # Update existing footer
        body = re.sub(
            BARBOSSA_FOOTER_PATTERN + r'(\s*\n\*Last Curated: [^*]+\*)?',
            new_footer,
            body
        )
    else:
        # Add new footer
        body = body.rstrip() + f"\n\n{new_footer}"

    return body


def get_issue_tracker(config: Dict, repo_name: str, logger: Optional[logging.Logger] = None) -> GitHubIssueTracker:
    """Create a GitHub issue tracker from config."""
    owner = config.get('owner', '')
    return GitHubIssueTracker(owner=owner, repo=repo_name, logger=logger)
