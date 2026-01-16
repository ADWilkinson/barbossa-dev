#!/usr/bin/env python3
"""
Tests for GitHub Issue Tracker
"""

import unittest
from unittest.mock import Mock, patch
import json
from barbossa.utils.issue_tracker import Issue, GitHubIssueTracker, get_issue_tracker


class TestIssueDataclass(unittest.TestCase):
    """Test the Issue dataclass"""

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
        self.tracker = GitHubIssueTracker('testowner', 'testrepo')

    @patch('barbossa.utils.issue_tracker.subprocess.run')
    def test_get_backlog_count(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"number": 1}, {"number": 2}, {"number": 3}]'
        )

        count = self.tracker.get_backlog_count()

        self.assertEqual(count, 3)
        cmd = mock_run.call_args[0][0]
        self.assertIn('--label backlog', cmd)
        self.assertIn('--state open', cmd)

    @patch('barbossa.utils.issue_tracker.subprocess.run')
    def test_get_existing_titles(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout='[{"title": "Fix Bug"}, {"title": "Add Feature"}]'
        )

        titles = self.tracker.get_existing_titles(limit=10)

        self.assertEqual(titles, ['fix bug', 'add feature'])

    @patch('barbossa.utils.issue_tracker.subprocess.run')
    def test_list_issues(self, mock_run):
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

    @patch('barbossa.utils.issue_tracker.subprocess.run')
    def test_create_issue(self, mock_run):
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
        cmd = mock_run.call_args[0][0]
        self.assertIn('gh issue create', cmd)

    @patch('barbossa.utils.issue_tracker.subprocess.run')
    def test_create_issue_failure(self, mock_run):
        mock_run.return_value = Mock(returncode=1, stdout='')

        issue = self.tracker.create_issue('Title', 'Body')

        self.assertIsNone(issue)

    def test_get_issue_list_command(self):
        cmd = self.tracker.get_issue_list_command(labels=['bug'], limit=10)

        self.assertIn('gh issue list', cmd)
        self.assertIn('--label bug', cmd)
        self.assertIn('--limit 10', cmd)

    def test_get_pr_link_instruction(self):
        instruction = self.tracker.get_pr_link_instruction('42')

        self.assertIn('Closes #42', instruction)


class TestGetIssueTracker(unittest.TestCase):
    """Test the get_issue_tracker factory function"""

    def test_get_github_tracker(self):
        config = {'owner': 'testowner'}

        tracker = get_issue_tracker(config, 'testrepo', Mock())

        self.assertIsInstance(tracker, GitHubIssueTracker)
        self.assertEqual(tracker.owner, 'testowner')
        self.assertEqual(tracker.repo, 'testrepo')


if __name__ == '__main__':
    unittest.main()
