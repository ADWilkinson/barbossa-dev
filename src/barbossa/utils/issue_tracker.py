#!/usr/bin/env python3
"""
Issue Tracker Abstraction for Barbossa

Provides a unified interface for issue tracking systems (GitHub Issues, Linear).
Allows Barbossa to work with either system based on configuration.

Usage:
    from issue_tracker import get_issue_tracker

    # Config determines which tracker to use
    tracker = get_issue_tracker(config)

    # Same API regardless of backend
    count = tracker.get_backlog_count()
    tracker.create_issue(title="Fix bug", body="Details...")
"""

import json
import logging
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from barbossa.utils.linear_client import LinearClient, LinearIssue


@dataclass
class Issue:
    """Unified issue representation across trackers."""
    id: str
    identifier: str  # "MUS-14" for Linear, "#123" for GitHub
    title: str
    body: Optional[str]
    state: str
    labels: List[str]
    url: str

    @classmethod
    def from_linear(cls, linear_issue: LinearIssue) -> 'Issue':
        return cls(
            id=linear_issue.id,
            identifier=linear_issue.identifier,
            title=linear_issue.title,
            body=linear_issue.description,
            state=linear_issue.state,
            labels=linear_issue.labels,
            url=linear_issue.url
        )

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


class IssueTracker(ABC):
    """Abstract base class for issue trackers."""

    @abstractmethod
    def get_backlog_count(self, label: str = "backlog") -> int:
        """Count open issues with the given label."""
        pass

    @abstractmethod
    def get_existing_titles(self, limit: int = 50) -> List[str]:
        """Get lowercased titles of existing open issues."""
        pass

    @abstractmethod
    def list_issues(
        self,
        labels: Optional[List[str]] = None,
        state: Optional[str] = None,
        limit: int = 50
    ) -> List[Issue]:
        """List issues with optional filters."""
        pass

    @abstractmethod
    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> Optional[Issue]:
        """Create a new issue. Returns created issue or None on failure."""
        pass

    @abstractmethod
    def get_issue_list_command(self, labels: Optional[List[str]] = None, limit: int = 10) -> str:
        """
        Get a CLI command string that Claude can use to list issues.
        Returns the appropriate command for the tracker type.
        """
        pass

    @abstractmethod
    def get_pr_link_instruction(self, issue_id: str) -> str:
        """
        Get instruction text for linking a PR to an issue.
        For GitHub: "Closes #123" in PR description
        For Linear: Branch naming or description format
        """
        pass


class GitHubIssueTracker(IssueTracker):
    """GitHub Issues implementation."""

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
                pass  # Invalid JSON from gh command
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
                pass  # Invalid JSON from gh command
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
            return []  # Invalid JSON from gh command

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> Optional[Issue]:
        import tempfile

        labels = labels or ['backlog']
        label_str = ','.join(labels)

        # Write body to temp file to handle special characters
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
                # Parse the URL to get issue number
                # URL format: https://github.com/owner/repo/issues/123
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
            import os
            os.unlink(body_file)

    def get_issue_list_command(self, labels: Optional[List[str]] = None, limit: int = 10) -> str:
        cmd = f"gh issue list --repo {self.owner}/{self.repo} --state open --limit {limit}"
        if labels:
            cmd += f" --label {','.join(labels)}"
        return cmd

    def get_pr_link_instruction(self, issue_id: str) -> str:
        return f'Include "Closes #{issue_id}" in your PR description to automatically close the issue when merged.'


class LinearIssueTracker(IssueTracker):
    """Linear implementation."""

    def __init__(
        self,
        team_key: str,
        api_key: Optional[str] = None,
        backlog_state: str = "Backlog",
        logger: Optional[logging.Logger] = None
    ):
        self.team_key = team_key
        self.backlog_state = backlog_state
        self.logger = logger or logging.getLogger('linear_tracker')
        self.client = LinearClient(api_key=api_key)

    def get_backlog_count(self, label: str = "backlog") -> int:
        # For Linear, we use state "Backlog" instead of label
        return self.client.count_issues(self.team_key, state=self.backlog_state)

    def get_existing_titles(self, limit: int = 50) -> List[str]:
        return self.client.get_issue_titles(self.team_key, limit=limit)

    def list_issues(
        self,
        labels: Optional[List[str]] = None,
        state: Optional[str] = None,
        limit: int = 50
    ) -> List[Issue]:
        linear_issues = self.client.list_issues(
            self.team_key,
            state=state,
            labels=labels,
            limit=limit
        )
        return [Issue.from_linear(i) for i in linear_issues]

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> Optional[Issue]:
        linear_issue = self.client.create_issue(
            self.team_key,
            title=title,
            description=body,
            state=self.backlog_state,
            labels=labels
        )
        if linear_issue:
            return Issue.from_linear(linear_issue)
        return None

    def get_issue_list_command(self, labels: Optional[List[str]] = None, limit: int = 10) -> str:
        # For Linear, we provide context instead of a CLI command since there's no Linear CLI
        # The engineer prompt will use this to understand available issues
        return f"[Linear issues for team {self.team_key} will be provided in context below]"

    def get_pr_link_instruction(self, issue_id: str) -> str:
        return f'Name your branch with the issue ID (e.g., "barbossa/{issue_id.lower()}-description") to auto-link in Linear.'

    def get_issues_context(self, state: Optional[str] = None, limit: int = 10) -> str:
        """
        Generate a formatted context string of issues for injection into prompts.
        Since Claude can't call Linear CLI, we provide the issues directly.
        """
        issues = self.list_issues(state=state, limit=limit)
        if not issues:
            return "No issues found."

        lines = [f"## Open Issues in {self.team_key}:\n"]
        for issue in issues:
            label_str = f" [{', '.join(issue.labels)}]" if issue.labels else ""
            lines.append(f"- **{issue.identifier}**: {issue.title}{label_str}")
            lines.append(f"  State: {issue.state} | URL: {issue.url}")
            if issue.body:
                # Truncate long descriptions
                body_preview = issue.body[:200] + "..." if len(issue.body) > 200 else issue.body
                body_preview = body_preview.replace('\n', ' ')
                lines.append(f"  Description: {body_preview}")
            lines.append("")

        return '\n'.join(lines)


def get_issue_tracker(config: Dict, repo_name: str, logger: Optional[logging.Logger] = None) -> IssueTracker:
    """
    Factory function to create the appropriate issue tracker based on config.

    Config structure:
    {
        "owner": "github-username",
        "issue_tracker": {
            "type": "github" | "linear",
            "linear": {
                "team_key": "MUS",
                "api_key": "lin_api_xxx",  # or use LINEAR_API_KEY env var
                "backlog_state": "Backlog"
            }
        },
        "repositories": [...]
    }

    If issue_tracker is not specified, defaults to GitHub Issues.
    """
    owner = config.get('owner', '')
    tracker_config = config.get('issue_tracker', {})
    tracker_type = tracker_config.get('type', 'github')

    if tracker_type == 'linear':
        linear_config = tracker_config.get('linear', {})
        team_key = linear_config.get('team_key')
        if not team_key:
            raise ValueError("Linear team_key is required in issue_tracker.linear config")

        return LinearIssueTracker(
            team_key=team_key,
            api_key=linear_config.get('api_key'),  # Falls back to env var if None
            backlog_state=linear_config.get('backlog_state', 'Backlog'),
            logger=logger
        )
    else:
        # Default to GitHub
        return GitHubIssueTracker(owner=owner, repo=repo_name, logger=logger)


# Example config for Linear
EXAMPLE_LINEAR_CONFIG = """
{
  "owner": "puniaviision",
  "issue_tracker": {
    "type": "linear",
    "linear": {
      "team_key": "MUS",
      "backlog_state": "Backlog"
    }
  },
  "repositories": [
    {
      "name": "muse",
      "url": "https://github.com/puniaviision/muse.git"
    }
  ]
}
"""

if __name__ == "__main__":
    print("Issue Tracker Abstraction")
    print("=" * 40)
    print("Example Linear config:")
    print(EXAMPLE_LINEAR_CONFIG)
