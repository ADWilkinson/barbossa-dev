#!/usr/bin/env python3
"""
GitHub Issue Tracker for Barbossa

Provides issue tracking via GitHub Issues using the gh CLI.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional


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

    @classmethod
    def from_github(cls, gh_data: Dict) -> 'Issue':
        return cls(
            id=str(gh_data.get('number', '')),
            identifier=f"#{gh_data.get('number', '')}",
            title=gh_data.get('title', ''),
            body=gh_data.get('body', ''),
            state=gh_data.get('state', ''),
            labels=[l.get('name', '') for l in gh_data.get('labels', [])],
            url=gh_data.get('url', '')
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
        cmd = f"gh issue list --repo {self.owner}/{self.repo} --limit {limit} --json number,title,body,state,labels,url"
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


def get_issue_tracker(config: Dict, repo_name: str, logger: Optional[logging.Logger] = None) -> GitHubIssueTracker:
    """Create a GitHub issue tracker from config."""
    owner = config.get('owner', '')
    return GitHubIssueTracker(owner=owner, repo=repo_name, logger=logger)
