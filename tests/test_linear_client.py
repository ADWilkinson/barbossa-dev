#!/usr/bin/env python3
"""
Tests for Linear API Client

Tests cover API calls, error handling, GraphQL queries, retry logic, and security.
Uses mocking to avoid actual API calls during testing.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import requests
from linear_client import LinearClient, LinearIssue, retry_on_rate_limit


class TestLinearClient(unittest.TestCase):
    """Test suite for LinearClient"""

    def setUp(self):
        """Set up test client with mock API key"""
        self.api_key = "lin_api_test_key_123"
        with patch.dict('os.environ', {'LINEAR_API_KEY': self.api_key}):
            self.client = LinearClient()

    def test_initialization_with_api_key(self):
        """Test client initialization with provided API key"""
        client = LinearClient(api_key="custom_key")
        self.assertEqual(client.api_key, "custom_key")

    def test_initialization_from_env_var(self):
        """Test client initialization from environment variable"""
        with patch.dict('os.environ', {'LINEAR_API_KEY': 'env_key'}):
            client = LinearClient()
            self.assertEqual(client.api_key, 'env_key')

    def test_initialization_without_api_key_raises_error(self):
        """Test that missing API key raises ValueError"""
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError) as context:
                LinearClient()
            self.assertIn("Linear API key required", str(context.exception))

    @patch('linear_client.requests.post')
    def test_graphql_success(self, mock_post):
        """Test successful GraphQL query"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {'teams': {'nodes': [{'id': '123', 'key': 'TEST'}]}}
        }
        mock_post.return_value = mock_response

        result = self.client._graphql("query { teams { nodes { id } } }")

        self.assertEqual(result, {'teams': {'nodes': [{'id': '123', 'key': 'TEST'}]}})
        mock_post.assert_called_once()

    @patch('linear_client.requests.post')
    def test_graphql_errors_raise_exception(self, mock_post):
        """Test that GraphQL errors raise ValueError"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'errors': [{'message': 'Invalid query'}]
        }
        mock_post.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            self.client._graphql("invalid query")

        self.assertIn("GraphQL errors", str(context.exception))

    @patch('linear_client.requests.post')
    def test_graphql_http_error_raises(self, mock_post):
        """Test that HTTP errors are raised"""
        mock_post.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with self.assertRaises(requests.exceptions.HTTPError):
            self.client._graphql("query { teams }")

    @patch('linear_client.requests.post')
    def test_get_team_id_success(self, mock_post):
        """Test successful team ID retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'teams': {
                    'nodes': [{'id': 'team-uuid-123', 'key': 'MUS', 'name': 'Music Team'}]
                }
            }
        }
        mock_post.return_value = mock_response

        team_id = self.client._get_team_id('MUS')

        self.assertEqual(team_id, 'team-uuid-123')
        # Verify caching
        self.assertEqual(self.client._team_cache['MUS'], 'team-uuid-123')

    @patch('linear_client.requests.post')
    def test_get_team_id_not_found(self, mock_post):
        """Test team ID retrieval when team doesn't exist"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'teams': {'nodes': []}}}
        mock_post.return_value = mock_response

        team_id = self.client._get_team_id('INVALID')

        self.assertIsNone(team_id)

    @patch('linear_client.requests.post')
    def test_get_team_id_uses_cache(self, mock_post):
        """Test that team ID lookup uses cache"""
        self.client._team_cache['CACHED'] = 'cached-id-123'

        team_id = self.client._get_team_id('CACHED')

        self.assertEqual(team_id, 'cached-id-123')
        # Should not make API call
        mock_post.assert_not_called()

    @patch('linear_client.requests.post')
    def test_list_issues_success(self, mock_post):
        """Test listing issues successfully"""
        mock_response = Mock()
        mock_response.status_code = 200

        # Mock team ID query
        team_response = {'data': {'teams': {'nodes': [{'id': 'team-123', 'key': 'MUS'}]}}}
        # Mock issues query
        issues_response = {
            'data': {
                'issues': {
                    'nodes': [
                        {
                            'id': 'issue-1',
                            'identifier': 'MUS-14',
                            'title': 'Fix bug',
                            'description': 'Bug description',
                            'state': {'name': 'Todo'},
                            'labels': {'nodes': [{'name': 'bug'}]},
                            'url': 'https://linear.app/issue/MUS-14',
                            'createdAt': '2024-01-01T00:00:00Z'
                        }
                    ]
                }
            }
        }

        mock_post.return_value = mock_response
        mock_response.json.side_effect = [team_response, issues_response]

        issues = self.client.list_issues('MUS', limit=10)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].identifier, 'MUS-14')
        self.assertEqual(issues[0].title, 'Fix bug')
        self.assertEqual(issues[0].state, 'Todo')
        self.assertEqual(issues[0].labels, ['bug'])

    @patch('linear_client.requests.post')
    def test_create_issue_success(self, mock_post):
        """Test creating an issue successfully"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Mock team ID query
        team_response = {'data': {'teams': {'nodes': [{'id': 'team-123', 'key': 'MUS'}]}}}
        # Mock states query (for state ID lookup)
        states_response = {
            'data': {
                'workflowStates': {
                    'nodes': [
                        {'id': 'state-123', 'name': 'Backlog', 'type': 'backlog', 'team': {'key': 'MUS'}}
                    ]
                }
            }
        }
        # Mock create mutation
        create_response = {
            'data': {
                'issueCreate': {
                    'success': True,
                    'issue': {
                        'id': 'new-issue-id',
                        'identifier': 'MUS-15',
                        'title': 'New feature',
                        'description': 'Feature description',
                        'state': {'name': 'Backlog'},
                        'labels': {'nodes': []},
                        'url': 'https://linear.app/issue/MUS-15',
                        'createdAt': '2024-01-01T00:00:00Z'
                    }
                }
            }
        }

        mock_post.return_value = mock_response
        mock_response.json.side_effect = [team_response, states_response, create_response]

        issue = self.client.create_issue(
            team_key='MUS',
            title='New feature',
            description='Feature description',
            state='Backlog'
        )

        self.assertIsNotNone(issue)
        self.assertEqual(issue.identifier, 'MUS-15')
        self.assertEqual(issue.title, 'New feature')

    @patch('linear_client.requests.post')
    def test_create_issue_prevents_injection(self, mock_post):
        """Test that create_issue uses GraphQL variables (prevents injection)"""
        mock_response = Mock()
        mock_response.status_code = 200

        # Mock team ID
        team_response = {'data': {'teams': {'nodes': [{'id': 'team-123', 'key': 'MUS'}]}}}
        create_response = {
            'data': {
                'issueCreate': {
                    'success': True,
                    'issue': {
                        'id': 'id', 'identifier': 'MUS-1', 'title': 'Test',
                        'description': '', 'state': {'name': 'Todo'},
                        'labels': {'nodes': []}, 'url': 'https://linear.app',
                        'createdAt': '2024-01-01T00:00:00Z'
                    }
                }
            }
        }

        mock_post.return_value = mock_response
        mock_response.json.side_effect = [team_response, create_response]

        # Try to inject malicious content
        malicious_title = '"; } } mutation { deleteAllData { success } } query { teams { nodes {'
        self.client.create_issue('MUS', title=malicious_title)

        # Verify that the request used variables (not string formatting)
        calls = mock_post.call_args_list
        create_call = calls[1]  # Second call is create mutation
        payload = create_call[1]['json']

        # Check that variables are used
        self.assertIn('variables', payload)
        self.assertIn('input', payload['variables'])
        # Title should be in variables, not interpolated into query string
        self.assertEqual(payload['variables']['input']['title'], malicious_title)

    @patch('linear_client.requests.post')
    @patch('linear_client.time.sleep')  # Mock sleep to speed up tests
    def test_retry_on_rate_limit(self, mock_sleep, mock_post):
        """Test retry logic on 429 rate limit"""
        # First call: rate limited
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=rate_limit_response)

        # Second call: success
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {'data': {'teams': {'nodes': []}}}

        mock_post.side_effect = [
            requests.exceptions.HTTPError(response=rate_limit_response),
            success_response
        ]

        result = self.client._graphql("query { teams }")

        # Verify retry happened
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)

    @patch('linear_client.requests.post')
    @patch('linear_client.time.sleep')
    def test_retry_exhaustion(self, mock_sleep, mock_post):
        """Test that retries are exhausted after max attempts"""
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=rate_limit_response)

        mock_post.side_effect = requests.exceptions.HTTPError(response=rate_limit_response)

        with self.assertRaises(requests.exceptions.HTTPError):
            self.client._graphql("query { teams }")

        # Should retry 3 times then fail
        self.assertEqual(mock_post.call_count, 4)  # Initial + 3 retries

    @patch('linear_client.requests.post')
    def test_count_issues(self, mock_post):
        """Test counting issues"""
        mock_response = Mock()
        mock_response.status_code = 200

        team_response = {'data': {'teams': {'nodes': [{'id': 'team-123', 'key': 'MUS'}]}}}
        issues_response = {
            'data': {'issues': {'nodes': [
                {'id': '1', 'identifier': 'MUS-1', 'title': 'A', 'state': {'name': 'Todo'},
                 'labels': {'nodes': []}, 'url': 'https://linear.app', 'createdAt': '2024-01-01T00:00:00Z'},
                {'id': '2', 'identifier': 'MUS-2', 'title': 'B', 'state': {'name': 'Todo'},
                 'labels': {'nodes': []}, 'url': 'https://linear.app', 'createdAt': '2024-01-01T00:00:00Z'}
            ]}}
        }

        mock_post.return_value = mock_response
        mock_response.json.side_effect = [team_response, issues_response]

        count = self.client.count_issues('MUS')

        self.assertEqual(count, 2)


class TestLinearIssue(unittest.TestCase):
    """Test LinearIssue dataclass"""

    def test_to_dict(self):
        """Test converting issue to dictionary"""
        issue = LinearIssue(
            id='issue-123',
            identifier='MUS-14',
            title='Test issue',
            description='Description',
            state='Todo',
            labels=['bug', 'frontend'],
            url='https://linear.app/issue/MUS-14',
            created_at='2024-01-01T00:00:00Z'
        )

        result = issue.to_dict()

        self.assertEqual(result['identifier'], 'MUS-14')
        self.assertEqual(result['title'], 'Test issue')
        self.assertEqual(result['labels'], ['bug', 'frontend'])


if __name__ == '__main__':
    unittest.main()
