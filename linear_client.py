#!/usr/bin/env python3
"""
Linear API Client for Barbossa

Provides issue tracking functionality via Linear's GraphQL API.
Alternative to GitHub Issues for teams using Linear.

Usage:
    from linear_client import LinearClient

    client = LinearClient(api_key="lin_api_xxx")
    issues = client.list_issues(team_key="MUS", state="backlog")
    client.create_issue(team_key="MUS", title="Fix bug", body="Details...")
"""

import json
import logging
import os
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LinearIssue:
    """Represents a Linear issue."""
    id: str
    identifier: str  # e.g., "MUS-14"
    title: str
    description: Optional[str]
    state: str
    labels: List[str]
    url: str
    created_at: str

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'identifier': self.identifier,
            'title': self.title,
            'description': self.description,
            'state': self.state,
            'labels': self.labels,
            'url': self.url,
            'created_at': self.created_at
        }


class LinearClient:
    """Client for Linear's GraphQL API."""

    API_URL = "https://api.linear.app/graphql"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Linear client.

        Args:
            api_key: Linear API key. If not provided, reads from LINEAR_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get('LINEAR_API_KEY')
        if not self.api_key:
            raise ValueError("Linear API key required. Set LINEAR_API_KEY env var or pass api_key.")

        self.logger = logging.getLogger('linear_client')
        self._team_cache: Dict[str, str] = {}  # team_key -> team_id

    def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query against Linear API."""
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }

        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        try:
            response = requests.post(self.API_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            if 'errors' in result:
                self.logger.error(f"GraphQL errors: {result['errors']}")
                return {}

            return result.get('data', {})
        except Exception as e:
            self.logger.error(f"Linear API error: {e}")
            return {}

    def _get_team_id(self, team_key: str) -> Optional[str]:
        """Get team ID from team key (e.g., 'MUS' -> 'uuid')."""
        if team_key in self._team_cache:
            return self._team_cache[team_key]

        query = """
        query GetTeam($key: String!) {
            team(key: $key) {
                id
                key
                name
            }
        }
        """

        result = self._graphql(query, {'key': team_key})
        team = result.get('team')
        if team:
            self._team_cache[team_key] = team['id']
            return team['id']
        return None

    def _get_state_id(self, team_key: str, state_name: str) -> Optional[str]:
        """Get workflow state ID by name (e.g., 'Backlog' -> 'uuid')."""
        team_id = self._get_team_id(team_key)
        if not team_id:
            return None

        query = """
        query GetStates($teamId: String!) {
            workflowStates(filter: { team: { id: { eq: $teamId } } }) {
                nodes {
                    id
                    name
                    type
                }
            }
        }
        """

        result = self._graphql(query, {'teamId': team_id})
        states = result.get('workflowStates', {}).get('nodes', [])

        # Try exact match first, then case-insensitive
        for state in states:
            if state['name'] == state_name:
                return state['id']
        for state in states:
            if state['name'].lower() == state_name.lower():
                return state['id']

        # Also try matching state type (backlog, started, completed, canceled)
        for state in states:
            if state['type'].lower() == state_name.lower():
                return state['id']

        return None

    def _get_label_ids(self, team_key: str, label_names: List[str]) -> List[str]:
        """Get label IDs from label names."""
        team_id = self._get_team_id(team_key)
        if not team_id:
            return []

        query = """
        query GetLabels($teamId: String!) {
            issueLabels(filter: { team: { id: { eq: $teamId } } }) {
                nodes {
                    id
                    name
                }
            }
        }
        """

        result = self._graphql(query, {'teamId': team_id})
        labels = result.get('issueLabels', {}).get('nodes', [])

        label_ids = []
        for name in label_names:
            for label in labels:
                if label['name'].lower() == name.lower():
                    label_ids.append(label['id'])
                    break

        return label_ids

    def list_issues(
        self,
        team_key: str,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[LinearIssue]:
        """
        List issues from Linear.

        Args:
            team_key: Team key (e.g., 'MUS')
            state: Filter by state name (e.g., 'Backlog', 'Todo', 'In Progress')
            labels: Filter by label names
            limit: Max issues to return

        Returns:
            List of LinearIssue objects
        """
        team_id = self._get_team_id(team_key)
        if not team_id:
            self.logger.error(f"Team not found: {team_key}")
            return []

        # Build filter
        filter_parts = [f'team: {{ id: {{ eq: "{team_id}" }} }}']

        if state:
            state_id = self._get_state_id(team_key, state)
            if state_id:
                filter_parts.append(f'state: {{ id: {{ eq: "{state_id}" }} }}')

        if labels:
            label_ids = self._get_label_ids(team_key, labels)
            if label_ids:
                # Filter issues that have any of these labels
                label_filter = ', '.join([f'{{ id: {{ eq: "{lid}" }} }}' for lid in label_ids])
                filter_parts.append(f'labels: {{ some: {{ or: [{label_filter}] }} }}')

        filter_str = ', '.join(filter_parts)

        query = f"""
        query ListIssues {{
            issues(
                filter: {{ {filter_str} }}
                first: {limit}
                orderBy: createdAt
            ) {{
                nodes {{
                    id
                    identifier
                    title
                    description
                    state {{
                        name
                    }}
                    labels {{
                        nodes {{
                            name
                        }}
                    }}
                    url
                    createdAt
                }}
            }}
        }}
        """

        result = self._graphql(query)
        issues_data = result.get('issues', {}).get('nodes', [])

        issues = []
        for data in issues_data:
            issues.append(LinearIssue(
                id=data['id'],
                identifier=data['identifier'],
                title=data['title'],
                description=data.get('description'),
                state=data['state']['name'] if data.get('state') else 'Unknown',
                labels=[l['name'] for l in data.get('labels', {}).get('nodes', [])],
                url=data['url'],
                created_at=data['createdAt']
            ))

        return issues

    def get_issue(self, identifier: str) -> Optional[LinearIssue]:
        """Get a single issue by identifier (e.g., 'MUS-14')."""
        query = """
        query GetIssue($identifier: String!) {
            issue(id: $identifier) {
                id
                identifier
                title
                description
                state {
                    name
                }
                labels {
                    nodes {
                        name
                    }
                }
                url
                createdAt
            }
        }
        """

        result = self._graphql(query, {'identifier': identifier})
        data = result.get('issue')

        if not data:
            return None

        return LinearIssue(
            id=data['id'],
            identifier=data['identifier'],
            title=data['title'],
            description=data.get('description'),
            state=data['state']['name'] if data.get('state') else 'Unknown',
            labels=[l['name'] for l in data.get('labels', {}).get('nodes', [])],
            url=data['url'],
            created_at=data['createdAt']
        )

    def create_issue(
        self,
        team_key: str,
        title: str,
        description: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Optional[LinearIssue]:
        """
        Create a new issue in Linear.

        Args:
            team_key: Team key (e.g., 'MUS')
            title: Issue title
            description: Issue description (markdown)
            state: Initial state name (e.g., 'Backlog')
            labels: Label names to apply

        Returns:
            Created LinearIssue or None on failure
        """
        team_id = self._get_team_id(team_key)
        if not team_id:
            self.logger.error(f"Team not found: {team_key}")
            return None

        # Build input
        input_parts = [f'teamId: "{team_id}"', f'title: "{self._escape_string(title)}"']

        if description:
            input_parts.append(f'description: "{self._escape_string(description)}"')

        if state:
            state_id = self._get_state_id(team_key, state)
            if state_id:
                input_parts.append(f'stateId: "{state_id}"')

        if labels:
            label_ids = self._get_label_ids(team_key, labels)
            if label_ids:
                labels_str = ', '.join([f'"{lid}"' for lid in label_ids])
                input_parts.append(f'labelIds: [{labels_str}]')

        input_str = ', '.join(input_parts)

        query = f"""
        mutation CreateIssue {{
            issueCreate(input: {{ {input_str} }}) {{
                success
                issue {{
                    id
                    identifier
                    title
                    description
                    state {{
                        name
                    }}
                    labels {{
                        nodes {{
                            name
                        }}
                    }}
                    url
                    createdAt
                }}
            }}
        }}
        """

        result = self._graphql(query)
        create_result = result.get('issueCreate', {})

        if not create_result.get('success'):
            self.logger.error(f"Failed to create issue: {title}")
            return None

        data = create_result.get('issue')
        if not data:
            return None

        self.logger.info(f"Created issue: {data['identifier']} - {title}")

        return LinearIssue(
            id=data['id'],
            identifier=data['identifier'],
            title=data['title'],
            description=data.get('description'),
            state=data['state']['name'] if data.get('state') else 'Unknown',
            labels=[l['name'] for l in data.get('labels', {}).get('nodes', [])],
            url=data['url'],
            created_at=data['createdAt']
        )

    def update_issue_state(self, issue_id: str, state_name: str, team_key: str) -> bool:
        """Update an issue's state."""
        state_id = self._get_state_id(team_key, state_name)
        if not state_id:
            self.logger.error(f"State not found: {state_name}")
            return False

        query = """
        mutation UpdateIssue($id: String!, $stateId: String!) {
            issueUpdate(id: $id, input: { stateId: $stateId }) {
                success
            }
        }
        """

        result = self._graphql(query, {'id': issue_id, 'stateId': state_id})
        return result.get('issueUpdate', {}).get('success', False)

    def count_issues(
        self,
        team_key: str,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> int:
        """Count issues matching criteria."""
        issues = self.list_issues(team_key, state=state, labels=labels, limit=100)
        return len(issues)

    def get_issue_titles(
        self,
        team_key: str,
        state: Optional[str] = None,
        limit: int = 50
    ) -> List[str]:
        """Get just the titles of issues (for deduplication)."""
        issues = self.list_issues(team_key, state=state, limit=limit)
        return [issue.title.lower() for issue in issues]

    def _escape_string(self, s: str) -> str:
        """Escape a string for GraphQL."""
        return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


# Convenience function for simple usage
def get_linear_client() -> Optional[LinearClient]:
    """Get a Linear client using env var for API key."""
    try:
        return LinearClient()
    except ValueError:
        return None


if __name__ == "__main__":
    # Quick test
    import sys

    client = get_linear_client()
    if not client:
        print("LINEAR_API_KEY not set")
        sys.exit(1)

    # Test listing issues
    if len(sys.argv) > 1:
        team = sys.argv[1]
        issues = client.list_issues(team, limit=5)
        for issue in issues:
            print(f"{issue.identifier}: {issue.title} [{issue.state}]")
    else:
        print("Usage: python linear_client.py <team_key>")
        print("Example: python linear_client.py MUS")
