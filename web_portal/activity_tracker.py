#!/usr/bin/env python3
"""
Enhanced Activity Tracker for Barbossa Web Portal
Provides detailed insights into what Barbossa has been working on
"""

import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class BarbossaActivityTracker:
    """Track and analyze Barbossa's development activities"""
    
    def __init__(self, work_dir: Path = None):
        self.work_dir = work_dir or Path.home() / 'barbossa-engineer'
        self.logs_dir = self.work_dir / 'logs'
        self.changelogs_dir = self.work_dir / 'changelogs'
        self.state_dir = self.work_dir / 'state'
        
    def get_detailed_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive activity details for the past N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        activity = {
            'summary': {
                'total_executions': 0,
                'files_modified': 0,
                'commits_made': 0,
                'tickets_enriched': 0,
                'tests_run': 0,
                'errors_fixed': 0
            },
            'recent_work': [],
            'code_changes': [],
            'git_activity': [],
            'test_results': [],
            'improvements': [],
            'current_focus': None,
            'timeline': []
        }
        
        # Parse recent Claude execution logs
        activity['recent_work'] = self._parse_claude_logs(cutoff_time)
        
        # Parse changelogs for detailed work
        activity['code_changes'] = self._parse_changelogs(cutoff_time)
        
        # Get git activity
        activity['git_activity'] = self._get_git_activity(cutoff_time)
        
        # Parse test results
        activity['test_results'] = self._parse_test_results(cutoff_time)
        
        # Get improvements and suggestions
        activity['improvements'] = self._parse_improvements(cutoff_time)
        
        # Determine current focus area
        activity['current_focus'] = self._determine_focus()
        
        # Build timeline of activities
        activity['timeline'] = self._build_timeline(activity)
        
        # Update summary stats
        activity['summary'] = self._calculate_summary(activity)
        
        return activity
    
    def _parse_claude_logs(self, cutoff_time: datetime) -> List[Dict]:
        """Parse Claude execution logs for work details"""
        work_items = []
        
        claude_logs = sorted(self.logs_dir.glob('claude_*.log'), 
                           key=lambda x: x.stat().st_mtime, reverse=True)
        
        for log_file in claude_logs:
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_time:
                break
                
            try:
                content = log_file.read_text()
                
                # Extract work performed
                work_item = {
                    'timestamp': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                    'log_file': log_file.name,
                    'actions': []
                }
                
                # Look for specific action patterns
                patterns = {
                    'file_edit': r'Edited file: ([^\n]+)',
                    'file_create': r'Created file: ([^\n]+)',
                    'test_run': r'Running tests for: ([^\n]+)',
                    'bug_fix': r'Fixed bug in: ([^\n]+)',
                    'feature_add': r'Added feature: ([^\n]+)',
                    'refactor': r'Refactored: ([^\n]+)',
                    'commit': r'Committed changes: ([^\n]+)',
                    'pr_create': r'Created PR: ([^\n]+)',
                    'dependency': r'Updated dependency: ([^\n]+)'
                }
                
                for action_type, pattern in patterns.items():
                    matches = re.findall(pattern, content)
                    for match in matches:
                        work_item['actions'].append({
                            'type': action_type,
                            'detail': match
                        })
                
                # Extract task completion messages
                if 'Task completed' in content or 'Successfully' in content:
                    success_pattern = r'(Successfully [^\.]+|Task completed: [^\.]+)'
                    successes = re.findall(success_pattern, content)
                    for success in successes:
                        work_item['actions'].append({
                            'type': 'completion',
                            'detail': success
                        })
                
                if work_item['actions']:
                    work_items.append(work_item)
                    
            except Exception as e:
                logger.debug(f"Error parsing log {log_file}: {e}")
        
        return work_items
    
    def _parse_changelogs(self, cutoff_time: datetime) -> List[Dict]:
        """Parse changelogs for code changes"""
        changes = []
        
        if not self.changelogs_dir.exists():
            return changes
            
        changelog_files = sorted(self.changelogs_dir.glob('*.md'), 
                                key=lambda x: x.stat().st_mtime, reverse=True)
        
        for changelog in changelog_files:
            if datetime.fromtimestamp(changelog.stat().st_mtime) < cutoff_time:
                break
                
            try:
                content = changelog.read_text()
                
                change_entry = {
                    'timestamp': datetime.fromtimestamp(changelog.stat().st_mtime).isoformat(),
                    'file': changelog.name,
                    'changes': []
                }
                
                # Extract changes from markdown
                change_patterns = [
                    r'- (Added|Fixed|Updated|Improved|Refactored): ([^\n]+)',
                    r'\* (Added|Fixed|Updated|Improved|Refactored): ([^\n]+)',
                    r'### ([\w\s]+)\n([^#]+)'
                ]
                
                for pattern in change_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if isinstance(match, tuple) and len(match) >= 2:
                            change_entry['changes'].append({
                                'type': match[0].lower(),
                                'description': match[1].strip()
                            })
                
                if change_entry['changes']:
                    changes.append(change_entry)
                    
            except Exception as e:
                logger.debug(f"Error parsing changelog {changelog}: {e}")
        
        return changes
    
    def _get_git_activity(self, cutoff_time: datetime) -> List[Dict]:
        """Get git commits and changes"""
        git_activity = []
        
        try:
            # Get recent commits from allowed repos
            allowed_repos = [
                self.work_dir / 'projects' / 'davy-jones-intern',
                self.work_dir / 'projects' / 'saylormemes',
                self.work_dir / 'projects' / 'the-flying-dutchman-theme',
                self.work_dir / 'projects' / 'adw'
            ]
            
            for repo_path in allowed_repos:
                if not repo_path.exists():
                    continue
                    
                # Get commits from this repo
                since_date = cutoff_time.strftime('%Y-%m-%d')
                cmd = [
                    'git', '-C', str(repo_path), 'log',
                    f'--since={since_date}',
                    '--pretty=format:%H|%ai|%s|%an',
                    '--name-status'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout:
                    lines = result.stdout.strip().split('\n')
                    
                    for line in lines:
                        if '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 4:
                                commit_hash, timestamp, message, author = parts[:4]
                                
                                # Only include Barbossa's commits
                                if 'barbossa' in author.lower() or 'automated' in message.lower():
                                    git_activity.append({
                                        'repo': repo_path.name,
                                        'hash': commit_hash[:8],
                                        'timestamp': timestamp,
                                        'message': message,
                                        'author': author
                                    })
                        
        except Exception as e:
            logger.debug(f"Error getting git activity: {e}")
        
        return git_activity
    
    def _parse_test_results(self, cutoff_time: datetime) -> List[Dict]:
        """Parse test execution results"""
        test_results = []
        
        # Look for test-related logs
        test_patterns = [
            r'(\d+) tests? passed',
            r'(\d+) tests? failed',
            r'Test suite: ([^\n]+)',
            r'Coverage: ([\d.]+%)'
        ]
        
        logs = sorted(self.logs_dir.glob('*.log'), 
                     key=lambda x: x.stat().st_mtime, reverse=True)
        
        for log_file in logs:
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff_time:
                break
                
            try:
                content = log_file.read_text()
                
                for pattern in test_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        test_results.append({
                            'timestamp': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                            'file': log_file.name,
                            'results': matches
                        })
                        break
                        
            except Exception as e:
                logger.debug(f"Error parsing test results from {log_file}: {e}")
        
        return test_results
    
    def _parse_improvements(self, cutoff_time: datetime) -> List[Dict]:
        """Parse improvements and suggestions made"""
        improvements = []
        
        # Check state files for improvements
        state_files = [
            self.state_dir / 'barbossa_state.json',
            self.state_dir / 'personal_assistant_state.json'
        ]
        
        for state_file in state_files:
            if not state_file.exists():
                continue
                
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                if 'improvements' in state:
                    for improvement in state['improvements']:
                        if isinstance(improvement, dict):
                            timestamp = improvement.get('timestamp')
                            if timestamp:
                                imp_time = datetime.fromisoformat(timestamp)
                                if imp_time >= cutoff_time:
                                    improvements.append(improvement)
                                    
            except Exception as e:
                logger.debug(f"Error parsing improvements from {state_file}: {e}")
        
        return improvements
    
    def _determine_focus(self) -> Optional[str]:
        """Determine current focus area based on recent activity"""
        # Check most recent work tracking
        work_tracking_file = self.work_dir / 'work_tracking' / 'current_work.json'
        
        if work_tracking_file.exists():
            try:
                with open(work_tracking_file, 'r') as f:
                    current_work = json.load(f)
                    return current_work.get('area', 'General Development')
            except:
                pass
        
        return 'General Development'
    
    def _build_timeline(self, activity: Dict) -> List[Dict]:
        """Build a chronological timeline of activities"""
        timeline = []
        
        # Combine all timestamped events
        for work in activity['recent_work']:
            for action in work['actions']:
                timeline.append({
                    'timestamp': work['timestamp'],
                    'type': 'work',
                    'category': action['type'],
                    'description': action['detail']
                })
        
        for change in activity['code_changes']:
            for ch in change['changes']:
                timeline.append({
                    'timestamp': change['timestamp'],
                    'type': 'code_change',
                    'category': ch['type'],
                    'description': ch['description']
                })
        
        for commit in activity['git_activity']:
            timeline.append({
                'timestamp': commit['timestamp'],
                'type': 'git',
                'category': 'commit',
                'description': f"{commit['repo']}: {commit['message']}"
            })
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Limit to most recent 50 items
        return timeline[:50]
    
    def _calculate_summary(self, activity: Dict) -> Dict:
        """Calculate summary statistics"""
        summary = {
            'total_executions': len(activity['recent_work']),
            'files_modified': 0,
            'commits_made': len(activity['git_activity']),
            'tickets_enriched': 0,
            'tests_run': len(activity['test_results']),
            'errors_fixed': 0
        }
        
        # Count unique files modified
        modified_files = set()
        for work in activity['recent_work']:
            for action in work['actions']:
                if action['type'] in ['file_edit', 'file_create']:
                    modified_files.add(action['detail'])
        
        summary['files_modified'] = len(modified_files)
        
        # Count bug fixes
        for work in activity['recent_work']:
            for action in work['actions']:
                if action['type'] == 'bug_fix':
                    summary['errors_fixed'] += 1
        
        # Count ticket enrichments
        for work in activity['recent_work']:
            for action in work['actions']:
                if 'ticket' in action['detail'].lower() or 'enriched' in action['detail'].lower():
                    summary['tickets_enriched'] += 1
        
        return summary
    
    def get_activity_report(self, hours: int = 24) -> str:
        """Generate a human-readable activity report"""
        activity = self.get_detailed_activity(hours)
        
        report = []
        report.append(f"# Barbossa Activity Report - Last {hours} Hours")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Summary
        report.append("## Summary")
        summary = activity['summary']
        report.append(f"- **Total Executions**: {summary['total_executions']}")
        report.append(f"- **Files Modified**: {summary['files_modified']}")
        report.append(f"- **Commits Made**: {summary['commits_made']}")
        report.append(f"- **Tests Run**: {summary['tests_run']}")
        report.append(f"- **Errors Fixed**: {summary['errors_fixed']}")
        report.append(f"- **Tickets Enriched**: {summary['tickets_enriched']}\n")
        
        # Current Focus
        if activity['current_focus']:
            report.append(f"## Current Focus: {activity['current_focus']}\n")
        
        # Recent Timeline
        if activity['timeline']:
            report.append("## Recent Activity Timeline")
            for event in activity['timeline'][:20]:
                timestamp = datetime.fromisoformat(event['timestamp']).strftime('%H:%M')
                icon = {
                    'work': '🔧',
                    'code_change': '📝',
                    'git': '📦',
                    'test': '🧪'
                }.get(event['type'], '•')
                
                report.append(f"{icon} **{timestamp}** - {event['description'][:100]}")
        
        return '\n'.join(report)