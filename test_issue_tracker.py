#!/usr/bin/env python3
"""
Tests for Issue Tracker Abstraction

Tests both GitHub Issues and Linear implementations of the IssueTracker interface.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from issue_tracker import (
    Issue,
    IssueTracker,
    GitHubIssueTracker,
    LinearIssueTracker,
    get_issue_tracker
)
from linear_client import LinearIssue


class TestIssueDataclass(unittest.TestCase):
    """Test the Issue dataclass and conversion methods"""

    def test_from_linear(self):
        """Test converting LinearIssue to Issue"""
        linear_issue = LinearIssue(
            id='linear-id-123',
            identifier='MUS-14',
            title='Test issue',
            description='Test description',
            state='Todo',
            labels=['bug', 'frontend'],
            url='https://linear.app/issue/MUS-14',
            created_at='2024-01-01T00:00:00Z'
        )

        issue = Issue.from_linear(linear_issue)

        self.assertEqual(issue.identifier, 'MUS-14')
        self.assertEqual(issue.title, 'Test issue')
        self.assertEqual(issue.body, 'Test description')
        self.assertEqual(issue.state, 'Todo')
        self.assertEqual(issue.labels, ['bug', 'frontend'])

    def test_from_github(self):
        """Test converting GitHub issue data to Issue"""
        gh_data = {
            'number': 42,
            'title': 'GitHub issue',
            'body': 'Issue body',
            'state': 'open',
            'labels': [{'name': 'bug'}, {'name': 'enhancement'}],
            'url': 'https://github.com/owner/repo/issues/42'
        }

        issue = Issue.from_github(gh_data)

        self.assertEqual(issue.identifier, '#42')
        self.assertEqual(issue.title, 'GitHub issue')
        self.assertEqual(issue.body, 'Issue body')
        self.assertEqual(issue.state, 'open')
        self.assertEqual(issue.labels, ['bug', 'enhancement'])


class TestGitHubIssueTracker(unittest.TestCase):
    """Test GitHub Issues implementation"""

    def setUp(self):
        """Set up test tracker"""
        self.tracker = GitHubIssueTracker('testowner', 'testrepo')

    @patch('issue_tracker.subprocess.run')
    def test_get_backlog_count(self, mock_run):
        """Test counting backlog issues"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"number": 1}, {"number": 2}, {"number": 3}]'
        )

        count = self.tracker.get_backlog_count()

        self.assertEqual(count, 3)
        # Verify correct command
        cmd = mock_run.call_args[0][0]
        self.assertIn('--label backlog', cmd)
        self.assertIn('--state open', cmd)

    @patch('issue_tracker.subprocess.run')
    def test_get_existing_titles(self, mock_run):
        """Test getting existing issue titles"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"title": "Fix Bug"}, {"title": "Add Feature"}]'
        )

        titles = self.tracker.get_existing_titles(limit=10)

        self.assertEqual(titles, ['fix bug', 'add feature'])  # Lowercased

    @patch('issue_tracker.subprocess.run')
    def test_list_issues(self, mock_run):
        """Test listing issues"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([{
                'number': 42,
                'title': 'Test issue',
                'body': 'Description',
                'state': 'open',
                'labels': [{'name': 'bug'}],
                'url': 'https://github.com/owner/repo/issues/42'
            }])
        )

        issues = self.tracker.list_issues(labels=['bug'], limit=5)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].identifier, '#42')
        self.assertEqual(issues[0].title, 'Test issue')

    @patch('issue_tracker.subprocess.run')
    def test_create_issue(self, mock_run):
        """Test creating an issue"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='https://github.com/owner/repo/issues/43'
        )

        issue = self.tracker.create_issue(
            title='New issue',
            body='Issue description',
            labels=['enhancement']
        )

        self.assertIsNotNone(issue)
        # Verify command includes title, body, labels
        cmd = mock_run.call_args[0][0]
        self.assertIn('gh issue create', cmd)

    @patch('issue_tracker.subprocess.run')
    def test_create_issue_failure(self, mock_run):
        """Test create_issue returns None on failure"""
        mock_run.return_value = Mock(returncode=1, stdout='')

        issue = self.tracker.create_issue('Title', 'Body')

        self.assertIsNone(issue)

    def test_get_issue_list_command(self):
        """Test generating issue list command"""
        cmd = self.tracker.get_issue_list_command(labels=['bug'], limit=10)

        self.assertIn('gh issue list', cmd)
        self.assertIn('--label bug', cmd)
        self.assertIn('--limit 10', cmd)

    def test_get_pr_link_instruction(self):
        """Test generating PR link instruction"""
        instruction = self.tracker.get_pr_link_instruction('42')

        self.assertIn('Closes #42', instruction)


class TestLinearIssueTracker(unittest.TestCase):
    """Test Linear implementation"""

    def setUp(self):
        """Set up test tracker with mocked Linear client"""
        with patch('issue_tracker.LinearClient') as MockClient:
            self.mock_client = Mock()
            MockClient.return_value = self.mock_client
            self.tracker = LinearIssueTracker(
                api_key='test-key',
                team_key='TEST',
                backlog_state='Backlog'
            )

    def test_get_backlog_count(self):
        """Test counting backlog issues"""
        self.mock_client.count_issues.return_value = 5

        count = self.tracker.get_backlog_count()

        self.assertEqual(count, 5)
        self.mock_client.count_issues.assert_called_with(
            'TEST',
            state='Backlog',
            labels=['backlog']
        )

    def test_get_existing_titles(self):
        """Test getting existing titles"""
        self.mock_client.get_issue_titles.return_value = ['fix bug', 'add feature']

        titles = self.tracker.get_existing_titles(limit=10)

        self.assertEqual(titles, ['fix bug', 'add feature'])
        self.mock_client.get_issue_titles.assert_called_with('TEST', state=None, limit=10)

    def test_list_issues(self):
        """Test listing issues"""
        linear_issue = LinearIssue(
            id='id-123',
            identifier='TEST-14',
            title='Test issue',
            description='Description',
            state='Todo',
            labels=['bug'],
            url='https://linear.app/issue/TEST-14',
            created_at='2024-01-01T00:00:00Z'
        )
        self.mock_client.list_issues.return_value = [linear_issue]

        issues = self.tracker.list_issues(labels=['bug'], limit=10)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].identifier, 'TEST-14')
        self.assertEqual(issues[0].title, 'Test issue')

    def test_create_issue(self):
        """Test creating an issue"""
        linear_issue = LinearIssue(
            id='new-id',
            identifier='TEST-15',
            title='New issue',
            description='Body',
            state='Backlog',
            labels=['enhancement'],
            url='https://linear.app/issue/TEST-15',
            created_at='2024-01-01T00:00:00Z'
        )
        self.mock_client.create_issue.return_value = linear_issue

        issue = self.tracker.create_issue(
            title='New issue',
            body='Body',
            labels=['enhancement']
        )

        self.assertIsNotNone(issue)
        self.assertEqual(issue.identifier, 'TEST-15')
        self.mock_client.create_issue.assert_called_with(
            team_key='TEST',
            title='New issue',
            description='Body',
            state='Backlog',
            labels=['enhancement']
        )

    def test_create_issue_failure(self):
        """Test create_issue returns None on failure"""
        self.mock_client.create_issue.return_value = None

        issue = self.tracker.create_issue('Title', 'Body')

        self.assertIsNone(issue)

    def test_get_issues_context(self):
        """Test generating issues context for prompts"""
        linear_issue = LinearIssue(
            id='id-1',
            identifier='TEST-1',
            title='First issue',
            description='Description',
            state='Todo',
            labels=['bug'],
            url='https://linear.app/issue/TEST-1',
            created_at='2024-01-01T00:00:00Z'
        )
        self.mock_client.list_issues.return_value = [linear_issue]

        context = self.tracker.get_issues_context(limit=5)

        self.assertIn('TEST-1', context)
        self.assertIn('First issue', context)
        self.assertIn('[Todo]', context)


class TestGetIssueTracker(unittest.TestCase):
    """Test the get_issue_tracker factory function"""

    def test_get_github_tracker(self):
        """Test getting GitHub tracker (default)"""
        config = {
            'owner': 'testowner',
            'issue_tracker': {'type': 'github'}
        }

        tracker = get_issue_tracker(config, 'testrepo', Mock())

        self.assertIsInstance(tracker, GitHubIssueTracker)
        self.assertEqual(tracker.owner, 'testowner')
        self.assertEqual(tracker.repo, 'testrepo')

    def test_get_github_tracker_no_config(self):
        """Test GitHub is default when no tracker config"""
        config = {'owner': 'testowner'}

        tracker = get_issue_tracker(config, 'testrepo', Mock())

        self.assertIsInstance(tracker, GitHubIssueTracker)

    @patch('issue_tracker.LinearClient')
    def test_get_linear_tracker(self, MockClient):
        """Test getting Linear tracker"""
        config = {
            'owner': 'testowner',
            'issue_tracker': {
                'type': 'linear',
                'linear': {
                    'team_key': 'TEST',
                    'backlog_state': 'Backlog'
                }
            }
        }

        with patch.dict('os.environ', {'LINEAR_API_KEY': 'test-key'}):
            tracker = get_issue_tracker(config, 'testrepo', Mock())

        self.assertIsInstance(tracker, LinearIssueTracker)
        self.assertEqual(tracker.team_key, 'TEST')

    @patch('issue_tracker.LinearClient')
    def test_get_linear_tracker_with_api_key_in_config(self, MockClient):
        """Test Linear tracker with API key in config"""
        config = {
            'owner': 'testowner',
            'issue_tracker': {
                'type': 'linear',
                'linear': {
                    'team_key': 'TEST',
                    'api_key': 'config-api-key'
                }
            }
        }

        tracker = get_issue_tracker(config, 'testrepo', Mock())

        self.assertIsInstance(tracker, LinearIssueTracker)

    def test_get_linear_tracker_missing_team_key(self):
        """Test Linear tracker fails without team_key"""
        config = {
            'owner': 'testowner',
            'issue_tracker': {
                'type': 'linear',
                'linear': {}
            }
        }

        with self.assertRaises(ValueError):
            get_issue_tracker(config, 'testrepo', Mock())


if __name__ == '__main__':
    unittest.main()
