#!/usr/bin/env python3
"""
Barbossa Ticket Enrichment Module
Automatically enriches GitHub issues and Linear tickets with context, analysis, and suggestions
"""

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

# Import security guard for repository validation
from security_guard import security_guard, SecurityViolationError

class TicketEnrichmentEngine:
    """
    Automated ticket enrichment for GitHub and Linear issues
    """
    
    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize the ticket enrichment engine"""
        self.work_dir = work_dir or Path.home() / 'barbossa-engineer'
        self.cache_dir = self.work_dir / 'cache' / 'tickets'
        self.logs_dir = self.work_dir / 'logs' / 'ticket_enrichment'
        self.state_file = self.work_dir / 'state' / 'ticket_enrichment.json'
        
        # Create directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Load state
        self.state = self._load_state()
        
        # GitHub token from environment
        self.github_token = os.environ.get('GITHUB_TOKEN', '')
        
        # Linear API key from environment
        self.linear_api_key = os.environ.get('LINEAR_API_KEY', '')
        
        # Allowed repositories (ADWilkinson only)
        self.allowed_repos = self._load_allowed_repos()
        
        self.logger.info("Ticket Enrichment Engine initialized")
    
    def _setup_logging(self):
        """Configure logging for ticket enrichment"""
        log_file = self.logs_dir / f"enrichment_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('ticket_enrichment')
    
    def _load_state(self) -> Dict:
        """Load enrichment state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'last_run': None,
            'enriched_tickets': {},
            'statistics': {
                'total_enriched': 0,
                'github_issues': 0,
                'linear_tickets': 0,
                'failed': 0
            }
        }
    
    def _save_state(self):
        """Save enrichment state"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _load_allowed_repos(self) -> List[str]:
        """Load allowed repositories from whitelist"""
        whitelist_file = self.work_dir / 'config' / 'repository_whitelist.json'
        if whitelist_file.exists():
            try:
                with open(whitelist_file, 'r') as f:
                    data = json.load(f)
                    return data.get('allowed_repositories', [])
            except:
                pass
        
        # Default ADWilkinson repositories - currently empty as no active development
        return []
    
    def fetch_github_issues(self, repo: str) -> List[Dict]:
        """Fetch open issues from a GitHub repository"""
        # Validate repository
        is_valid, reason = security_guard.validate_repository_url(f"https://github.com/{repo}")
        if not is_valid:
            self.logger.warning(f"Repository {repo} not allowed: {reason}")
            return []
        
        try:
            cmd = [
                'curl', '-s',
                '-H', f'Authorization: token {self.github_token}',
                '-H', 'Accept: application/vnd.github.v3+json',
                f'https://api.github.com/repos/{repo}/issues?state=open&per_page=100'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                response = json.loads(result.stdout)
                # Handle both list of issues and error responses
                if isinstance(response, list):
                    return [issue for issue in response if not issue.get('pull_request')]
                else:
                    self.logger.warning(f"Unexpected API response for {repo}: {response}")
                    return []
            
        except Exception as e:
            self.logger.error(f"Error fetching issues from {repo}: {e}")
        
        return []
    
    def analyze_issue_context(self, issue: Dict) -> Dict:
        """Analyze issue to determine context and suggestions"""
        analysis = {
            'priority': 'medium',
            'category': 'feature',
            'complexity': 'medium',
            'estimated_hours': 2,
            'suggested_approach': [],
            'related_files': [],
            'dependencies': [],
            'test_requirements': []
        }
        
        title = issue.get('title', '').lower()
        body = issue.get('body', '').lower()
        labels = [label['name'].lower() for label in issue.get('labels', [])]
        
        # Determine priority
        if 'urgent' in title or 'critical' in body or 'bug' in labels:
            analysis['priority'] = 'high'
        elif 'low' in title or 'minor' in body:
            analysis['priority'] = 'low'
        
        # Determine category
        if 'bug' in labels or 'fix' in title:
            analysis['category'] = 'bug'
        elif 'feature' in labels or 'add' in title or 'implement' in title:
            analysis['category'] = 'feature'
        elif 'refactor' in title or 'improve' in title:
            analysis['category'] = 'refactor'
        elif 'test' in title or 'testing' in body:
            analysis['category'] = 'testing'
        elif 'docs' in labels or 'documentation' in title:
            analysis['category'] = 'documentation'
        
        # Determine complexity
        if 'simple' in body or 'easy' in labels:
            analysis['complexity'] = 'low'
            analysis['estimated_hours'] = 1
        elif 'complex' in body or 'hard' in labels or 'architecture' in title:
            analysis['complexity'] = 'high'
            analysis['estimated_hours'] = 8
        
        # Extract file references
        file_pattern = r'[`\'"]([^`\'"]+\.[a-zA-Z]+)[`\'"]'
        files = re.findall(file_pattern, issue.get('body', ''))
        analysis['related_files'] = list(set(files))
        
        # Generate suggested approach based on category
        if analysis['category'] == 'bug':
            analysis['suggested_approach'] = [
                "1. Reproduce the issue locally",
                "2. Identify root cause through debugging",
                "3. Implement fix with minimal side effects",
                "4. Add regression test",
                "5. Verify fix resolves issue"
            ]
        elif analysis['category'] == 'feature':
            analysis['suggested_approach'] = [
                "1. Design feature architecture",
                "2. Create necessary components/modules",
                "3. Implement core functionality",
                "4. Add comprehensive tests",
                "5. Update documentation"
            ]
        elif analysis['category'] == 'refactor':
            analysis['suggested_approach'] = [
                "1. Analyze current implementation",
                "2. Identify improvement areas",
                "3. Refactor incrementally",
                "4. Ensure tests still pass",
                "5. Measure performance impact"
            ]
        
        # Test requirements
        if analysis['category'] in ['bug', 'feature']:
            analysis['test_requirements'] = [
                "Unit tests for new/modified functions",
                "Integration tests for workflows",
                "Edge case validation"
            ]
        
        return analysis
    
    def enrich_github_issue(self, repo: str, issue_number: int, analysis: Dict) -> bool:
        """Add enrichment comment to GitHub issue"""
        try:
            # Create enrichment comment
            comment = self._format_enrichment_comment(analysis)
            
            # Post comment to issue
            cmd = [
                'curl', '-s', '-X', 'POST',
                '-H', f'Authorization: token {self.github_token}',
                '-H', 'Accept: application/vnd.github.v3+json',
                f'https://api.github.com/repos/{repo}/issues/{issue_number}/comments',
                '-d', json.dumps({'body': comment})
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info(f"Enriched issue #{issue_number} in {repo}")
                return True
            
        except Exception as e:
            self.logger.error(f"Error enriching issue #{issue_number}: {e}")
        
        return False
    
    def _format_enrichment_comment(self, analysis: Dict) -> str:
        """Format analysis into a comment"""
        comment = "## 🤖 Barbossa Ticket Analysis\n\n"
        
        # Priority and metadata
        priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
        comment += f"**Priority:** {priority_emoji.get(analysis['priority'], '⚪')} {analysis['priority'].title()}\n"
        comment += f"**Category:** {analysis['category'].title()}\n"
        comment += f"**Complexity:** {analysis['complexity'].title()}\n"
        comment += f"**Estimated Time:** {analysis['estimated_hours']} hours\n\n"
        
        # Suggested approach
        if analysis['suggested_approach']:
            comment += "### 📋 Suggested Approach\n"
            for step in analysis['suggested_approach']:
                comment += f"{step}\n"
            comment += "\n"
        
        # Related files
        if analysis['related_files']:
            comment += "### 📁 Related Files\n"
            for file in analysis['related_files']:
                comment += f"- `{file}`\n"
            comment += "\n"
        
        # Test requirements
        if analysis['test_requirements']:
            comment += "### 🧪 Test Requirements\n"
            for req in analysis['test_requirements']:
                comment += f"- {req}\n"
            comment += "\n"
        
        # Dependencies
        if analysis['dependencies']:
            comment += "### 🔗 Dependencies\n"
            for dep in analysis['dependencies']:
                comment += f"- {dep}\n"
            comment += "\n"
        
        comment += f"*Analysis generated by Barbossa v2.2.0 on {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC*"
        
        return comment
    
    def run_daily_enrichment(self) -> Dict:
        """Run daily ticket enrichment for all repositories"""
        self.logger.info("Starting daily ticket enrichment")
        
        results = {
            'enriched': [],
            'failed': [],
            'skipped': [],
            'total_processed': 0
        }
        
        for repo in self.allowed_repos:
            repo_name = repo.replace('ADWilkinson/', '')
            self.logger.info(f"Processing repository: {repo}")
            
            # Fetch issues
            issues = self.fetch_github_issues(repo)
            
            for issue in issues:
                issue_id = f"{repo}#{issue['number']}"
                
                # Check if already enriched recently (within 7 days)
                if issue_id in self.state['enriched_tickets']:
                    last_enriched = datetime.fromisoformat(self.state['enriched_tickets'][issue_id])
                    if datetime.now() - last_enriched < timedelta(days=7):
                        results['skipped'].append(issue_id)
                        continue
                
                # Analyze issue
                analysis = self.analyze_issue_context(issue)
                
                # Enrich issue
                if self.enrich_github_issue(repo, issue['number'], analysis):
                    results['enriched'].append({
                        'id': issue_id,
                        'title': issue['title'],
                        'analysis': analysis
                    })
                    
                    # Update state
                    self.state['enriched_tickets'][issue_id] = datetime.now().isoformat()
                    self.state['statistics']['github_issues'] += 1
                    self.state['statistics']['total_enriched'] += 1
                else:
                    results['failed'].append(issue_id)
                    self.state['statistics']['failed'] += 1
                
                results['total_processed'] += 1
                
                # Rate limiting
                time.sleep(2)
        
        # Update state
        self.state['last_run'] = datetime.now().isoformat()
        self._save_state()
        
        # Generate summary
        self.logger.info(f"Enrichment complete: {len(results['enriched'])} enriched, "
                        f"{len(results['failed'])} failed, {len(results['skipped'])} skipped")
        
        return results
    
    def get_enrichment_stats(self) -> Dict:
        """Get enrichment statistics"""
        return {
            'last_run': self.state['last_run'],
            'statistics': self.state['statistics'],
            'recent_enrichments': list(self.state['enriched_tickets'].keys())[-10:]
        }


def main():
    """Main entry point for ticket enrichment"""
    engine = TicketEnrichmentEngine()
    
    # Run daily enrichment
    results = engine.run_daily_enrichment()
    
    # Print summary
    print("\n" + "="*50)
    print("TICKET ENRICHMENT SUMMARY")
    print("="*50)
    print(f"Total Processed: {results['total_processed']}")
    print(f"Enriched: {len(results['enriched'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Skipped (recent): {len(results['skipped'])}")
    
    if results['enriched']:
        print("\nEnriched Issues:")
        for item in results['enriched']:
            print(f"  - {item['id']}: {item['title'][:50]}...")
            print(f"    Priority: {item['analysis']['priority']}, "
                  f"Category: {item['analysis']['category']}, "
                  f"Est: {item['analysis']['estimated_hours']}h")


if __name__ == "__main__":
    main()