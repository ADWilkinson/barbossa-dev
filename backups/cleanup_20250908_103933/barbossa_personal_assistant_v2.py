#!/usr/bin/env python3
"""
Barbossa Personal Assistant v2 - Andrew's Workflow Automation System
Fixed version with proper API integration, error handling, and safety checks
"""

import os
import json
import logging
import asyncio
import subprocess
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AndrewContext:
    """Andrew's personal context and identifiers"""
    name: str = "Andrew Wilkinson"
    github_username: str = "ADWilkinson"
    slack_user_id: str = "U092NQP8A04"
    linear_user_id: str = "1a3bf7df-5dca-4fc6-b747-263ba84c3b85"
    email: str = "andrew@zkp2p.xyz"
    primary_repos: List[Tuple[str, str]] = None  # (name, path)
    expertise_areas: List[str] = None
    
    def __post_init__(self):
        if self.primary_repos is None:
            self.primary_repos = [
                ("zkp2p-v2-client", "~/projects/zkp2p/zkp2p-v2-client"),
                ("zkp2p-v2-extension", "~/projects/zkp2p/zkp2p-v2-extension"),
                ("barbossa-engineer", "~/barbossa-engineer"),
                ("davy-jones-intern", "~/projects/davy-jones-intern"),
                ("saylormemes", "~/projects/saylormemes"),
                ("the-flying-dutchman-theme", "~/projects/the-flying-dutchman-theme"),
                ("adw", "~/projects/adw")
            ]
        if self.expertise_areas is None:
            self.expertise_areas = [
                "Frontend Development",
                "React/TypeScript", 
                "Browser Extensions",
                "UI/UX Design",
                "Web3 Integration",
                "Vite Configuration"
            ]

class SafetyManager:
    """Manages safety checks and dry-run mode"""
    
    def __init__(self):
        self.dry_run = os.getenv('DRY_RUN_MODE', 'true').lower() == 'true'
        self.require_approval = os.getenv('REQUIRE_APPROVAL', 'true').lower() == 'true'
        self.test_environment = os.getenv('TEST_ENVIRONMENT', 'true').lower() == 'true'
        
        if self.dry_run:
            logger.info("🛡️ DRY RUN MODE ENABLED - No actual changes will be made")
        else:
            logger.warning("⚠️ DRY RUN MODE DISABLED - Real changes will be made!")
    
    def check_operation(self, operation: str, target: str = None) -> bool:
        """Check if an operation should proceed"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would perform: {operation} on {target or 'system'}")
            return False
        
        if self.require_approval:
            logger.info(f"Operation requires approval: {operation} on {target or 'system'}")
            # In production, would implement approval mechanism
            return False
        
        return True
    
    def log_operation(self, operation: str, success: bool, details: str = None):
        """Log operation result"""
        status = "SUCCESS" if success else "FAILED"
        msg = f"[{status}] {operation}"
        if details:
            msg += f" - {details}"
        logger.info(msg)

class LinearAPIClient:
    """Improved Linear API client with proper async and error handling"""
    
    def __init__(self, api_key: str, safety_manager: SafetyManager):
        self.api_key = api_key
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        self.safety = safety_manager
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_my_issues(self, user_id: str = None) -> List[Dict]:
        """Get issues for Andrew and optionally the intern"""
        try:
            # Query for Andrew's issues using the provided user_id
            # The intern's API key can query other users' issues
            andrew_id = user_id or self.safety.context.linear_user_id if hasattr(self.safety, 'context') else "1a3bf7df-5dca-4fc6-b747-263ba84c3b85"
            
            query = """
            query GetUserIssues($userId: String!) {
                user(id: $userId) {
                    id
                    email
                    name
                    assignedIssues(filter: {
                        state: { type: { nin: ["completed", "canceled"] } }
                    }) {
                        nodes {
                            id
                            identifier
                            title
                            description
                            priority
                            state {
                                name
                                type
                            }
                            assignee {
                                id
                                email
                                name
                            }
                            labels {
                                nodes {
                                    name
                                }
                            }
                            project {
                                name
                            }
                            createdAt
                            updatedAt
                            dueDate
                        }
                    }
                }
                viewer {
                    id
                    email
                    assignedIssues(filter: {
                        state: { type: { nin: ["completed", "canceled"] } }
                    }) {
                        nodes {
                            id
                            identifier
                            title
                            description
                            priority
                            state {
                                name
                                type
                            }
                            assignee {
                                id
                                email
                                name
                            }
                            labels {
                                nodes {
                                    name
                                }
                            }
                            project {
                                name
                            }
                            createdAt
                            updatedAt
                            dueDate
                        }
                    }
                }
            }
            """
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            variables = {"userId": andrew_id}
            
            async with self.session.post(
                self.base_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Get Andrew's issues
                    andrew_user = data.get("data", {}).get("user", {})
                    andrew_issues = []
                    if andrew_user:
                        andrew_email = andrew_user.get("email", "unknown")
                        logger.info(f"Fetching Andrew's issues: {andrew_email}")
                        andrew_issues = andrew_user.get("assignedIssues", {}).get("nodes", [])
                    
                    # Also get intern's issues 
                    viewer = data.get("data", {}).get("viewer", {})
                    intern_issues = []
                    if viewer:
                        intern_email = viewer.get("email", "unknown")
                        logger.info(f"Also checking intern's issues: {intern_email}")
                        intern_issues = viewer.get("assignedIssues", {}).get("nodes", [])
                    
                    # Combine both lists, removing duplicates by ID
                    all_issues = {}
                    for issue in andrew_issues:
                        all_issues[issue['id']] = issue
                    for issue in intern_issues:
                        # Only add intern issues that might be Andrew-related
                        if ('andrew' in issue.get('title', '').lower() or
                            'frontend' in ' '.join([l['name'] for l in issue.get('labels', {}).get('nodes', [])])):
                            all_issues[issue['id']] = issue
                    
                    combined_issues = list(all_issues.values())
                    logger.info(f"Total issues found: {len(andrew_issues)} Andrew's + {len([i for i in intern_issues if i['id'] in all_issues])} intern's = {len(combined_issues)} total")
                    
                    return combined_issues
                else:
                    logger.error(f"Linear API error: {response.status}")
                    return []
                    
        except asyncio.TimeoutError:
            logger.error("Linear API timeout")
            return []
        except Exception as e:
            logger.error(f"Error fetching issues: {e}")
            return []
    
    async def enrich_issue(self, issue_id: str, enrichment: Dict) -> bool:
        """Enrich a Linear issue with additional information"""
        if not self.safety.check_operation("enrich_linear_issue", issue_id):
            return True  # Return True in dry-run to continue flow
        
        try:
            mutation = """
            mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    success
                    issue {
                        id
                        description
                    }
                }
            }
            """
            
            variables = {
                "id": issue_id,
                "input": enrichment
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.post(
                self.base_url,
                json={"query": mutation, "variables": variables},
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    success = data.get("data", {}).get("issueUpdate", {}).get("success", False)
                    self.safety.log_operation("enrich_linear_issue", success, issue_id)
                    return success
                else:
                    self.safety.log_operation("enrich_linear_issue", False, f"Status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to enrich issue {issue_id}: {e}")
            return False

class ClaudeEnrichmentService:
    """Claude-powered enrichment service for intelligent ticket analysis"""
    
    def __init__(self, api_key: str, safety_manager: SafetyManager):
        self.api_key = api_key
        self.safety = safety_manager
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    async def generate_enrichment(self, issue: Dict, context: AndrewContext) -> str:
        """Generate intelligent enrichment using Claude"""
        try:
            # Build context-aware prompt
            prompt = f"""You are helping Andrew Wilkinson, a frontend engineer, with a Linear ticket.
            
Andrew's expertise: {', '.join(context.expertise_areas)}
Ticket: {issue.get('identifier')} - {issue.get('title')}
Current Description: {issue.get('description', 'No description')}
Project: {issue.get('project', {}).get('name', 'Unknown')}
Labels: {', '.join([l['name'] for l in issue.get('labels', {}).get('nodes', [])])}

Please provide enrichment that includes:
1. Implementation approach specific to the technology stack
2. Testing strategy (unit, integration, e2e as applicable)
3. Documentation requirements
4. Definition of done checklist
5. Potential gotchas or considerations
6. Related files/components likely to be affected

Keep it concise but comprehensive. Format in markdown."""

            # In dry-run mode, return a sample enrichment
            if self.safety.dry_run:
                return self._generate_static_enrichment(issue, context)
            
            # Make API call to Claude
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json={
                        "model": "claude-3-sonnet-20240229",
                        "max_tokens": 1000,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("content", [{}])[0].get("text", "")
                        return content
                    else:
                        logger.error(f"Claude API error: {response.status}")
                        return self._generate_static_enrichment(issue, context)
                        
        except Exception as e:
            logger.error(f"Error generating Claude enrichment: {e}")
            return self._generate_static_enrichment(issue, context)
    
    def _generate_static_enrichment(self, issue: Dict, context: AndrewContext) -> str:
        """Fallback static enrichment"""
        title = issue.get('title', '')
        labels = [l['name'] for l in issue.get('labels', {}).get('nodes', [])]
        
        enrichment = ["## Implementation Approach"]
        
        if 'frontend' in ' '.join(labels).lower() or 'react' in title.lower():
            enrichment.extend([
                "- Component architecture: Consider compound components pattern",
                "- State management: Evaluate Context API vs Redux needs",
                "- Performance: Implement React.memo and useMemo where appropriate",
                "- Styling: Use existing Material-UI components"
            ])
        
        enrichment.extend([
            "\n## Testing Strategy",
            "- [ ] Unit tests with Jest/Vitest",
            "- [ ] Component tests with React Testing Library",
            "- [ ] Integration tests if API involved",
            "- [ ] Manual testing across browsers",
            "\n## Documentation",
            "- [ ] Update component documentation",
            "- [ ] Add JSDoc comments",
            "- [ ] Update README if needed",
            "\n## Definition of Done",
            "- [ ] Code reviewed and approved",
            "- [ ] All tests passing",
            "- [ ] No console errors",
            "- [ ] Responsive design verified",
            "- [ ] Accessibility checked"
        ])
        
        return '\n'.join(enrichment)

class GitHubService:
    """GitHub integration for repository analysis"""
    
    def __init__(self, token: str, safety_manager: SafetyManager):
        self.token = token
        self.safety = safety_manager
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    async def get_recent_commits(self, repo: str, author: str = "ADWilkinson") -> List[Dict]:
        """Get recent commits by Andrew"""
        try:
            url = f"https://api.github.com/repos/{author}/{repo}/commits"
            params = {"author": author, "per_page": 10}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"GitHub API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching commits: {e}")
            return []

class BarbossaPersonalAssistant:
    """Main orchestrator for Andrew's personal workflow automation"""
    
    def __init__(self):
        self.context = AndrewContext()
        self.working_dir = Path.home() / "barbossa-engineer"
        self.logs_dir = self.working_dir / "logs" / "personal_assistant"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize safety manager
        self.safety = SafetyManager()
        
        # Initialize services
        self.linear_client = None
        self.claude_service = None
        self.github_service = None
        self.initialize_services()
        
        # Task tracking
        self.task_history = self.load_task_history()
    
    def initialize_services(self):
        """Initialize all services with proper error handling"""
        try:
            # Linear API
            linear_key = os.getenv('LINEAR_API_KEY')
            if linear_key:
                self.linear_client = LinearAPIClient(linear_key, self.safety)
                logger.info("✅ Linear API client initialized")
            else:
                logger.warning("⚠️ No LINEAR_API_KEY found")
            
            # Claude API
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                self.claude_service = ClaudeEnrichmentService(anthropic_key, self.safety)
                logger.info("✅ Claude enrichment service initialized")
            else:
                logger.warning("⚠️ No ANTHROPIC_API_KEY found")
            
            # GitHub API
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                self.github_service = GitHubService(github_token, self.safety)
                logger.info("✅ GitHub service initialized")
            else:
                logger.warning("⚠️ No GITHUB_TOKEN found")
                
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
    
    def load_task_history(self) -> Dict:
        """Load task execution history"""
        history_file = self.working_dir / "work_tracking" / "personal_assistant_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading history: {e}")
                return {}
        return {}
    
    def save_task_history(self):
        """Save task execution history"""
        try:
            history_file = self.working_dir / "work_tracking" / "personal_assistant_history.json"
            history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(history_file, 'w') as f:
                json.dump(self.task_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    async def enrich_linear_tickets(self):
        """Enrich Andrew's Linear tickets with AI-powered insights"""
        if not self.linear_client:
            logger.warning("Linear client not initialized")
            return
        
        logger.info("🎯 Starting Linear ticket enrichment for Andrew")
        
        try:
            async with self.linear_client:
                # Get Andrew's issues (and any intern issues that are Andrew-related)
                issues = await self.linear_client.get_my_issues(self.context.linear_user_id)
                
                if not issues:
                    logger.info("No issues found to enrich")
                    return
                
                logger.info(f"Found {len(issues)} issues to process")
                
                for issue in issues[:5]:  # Limit to 5 in test mode
                    issue_id = issue['id']
                    identifier = issue['identifier']
                    title = issue['title']
                    description = issue.get('description', '')
                    
                    # Skip if already enriched
                    if '[Auto-Enriched by Barbossa]' in description:
                        logger.info(f"Skipping {identifier} - already enriched")
                        continue
                    
                    logger.info(f"Processing {identifier}: {title}")
                    
                    # Generate enrichment
                    if self.claude_service:
                        enrichment = await self.claude_service.generate_enrichment(issue, self.context)
                    else:
                        # Fallback to static enrichment
                        enrichment = self._generate_static_enrichment(issue)
                    
                    # Add enrichment to description
                    new_description = f"{description}\n\n---\n[Auto-Enriched by Barbossa - {datetime.now().strftime('%Y-%m-%d %H:%M')}]\n\n{enrichment}"
                    
                    # Update issue (respects dry-run mode)
                    success = await self.linear_client.enrich_issue(
                        issue_id,
                        {"description": new_description}
                    )
                    
                    if success:
                        logger.info(f"✅ Successfully processed {identifier}")
                    else:
                        logger.warning(f"⚠️ Could not update {identifier}")
                        
        except Exception as e:
            logger.error(f"Error in ticket enrichment: {e}")
    
    def _generate_static_enrichment(self, issue: Dict) -> str:
        """Fallback static enrichment when Claude is unavailable"""
        return """## Implementation Notes
- Review existing codebase patterns
- Follow project conventions
- Consider performance implications

## Testing Requirements  
- Unit tests required
- Integration tests if applicable
- Manual testing checklist

## Documentation
- Update relevant docs
- Add inline comments
- Update changelog"""
    
    async def generate_daily_documentation(self):
        """Generate daily documentation for Andrew's work"""
        logger.info("📝 Generating daily documentation")
        
        timestamp = datetime.now().strftime("%Y-%m-%d")
        doc_content = []
        
        doc_content.append(f"# Daily Work Summary - {timestamp}")
        doc_content.append(f"\n## Developer: {self.context.name}")
        doc_content.append(f"## Mode: {'DRY RUN' if self.safety.dry_run else 'LIVE'}\n")
        
        # Check repository activity
        doc_content.append("## Repository Activity\n")
        for repo_name, repo_path in self.context.primary_repos:
            full_path = Path(os.path.expanduser(repo_path))
            
            if full_path.exists() and (full_path / ".git").exists():
                try:
                    os.chdir(full_path)
                    # Get today's commits
                    result = subprocess.run(
                        ["git", "log", "--since=midnight", "--author=Andrew", "--author=ADWilkinson", "--oneline"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.stdout.strip():
                        doc_content.append(f"### {repo_name}")
                        for line in result.stdout.strip().split('\n'):
                            doc_content.append(f"  - {line}")
                        doc_content.append("")
                except Exception as e:
                    logger.error(f"Error checking repo {repo_name}: {e}")
        
        # Add Linear ticket summary if available
        if self.linear_client:
            doc_content.append("## Linear Tickets\n")
            doc_content.append("(Ticket enrichment in progress...)\n")
        
        # Save documentation
        doc_file = self.logs_dir / f"daily_summary_{timestamp}.md"
        try:
            with open(doc_file, 'w') as f:
                f.write('\n'.join(doc_content))
            logger.info(f"✅ Daily documentation saved to {doc_file}")
            self.safety.log_operation("generate_documentation", True, str(doc_file))
        except Exception as e:
            logger.error(f"Error saving documentation: {e}")
            self.safety.log_operation("generate_documentation", False, str(e))
    
    async def run_daily_tasks(self):
        """Run all daily tasks for Andrew"""
        logger.info("🚀 Starting daily automation tasks for Andrew")
        logger.info(f"Safety Mode: DRY_RUN={self.safety.dry_run}")
        
        try:
            # Run tasks
            await self.enrich_linear_tickets()
            await self.generate_daily_documentation()
            
            # Update task history
            self.task_history[datetime.now().isoformat()] = {
                'tasks_completed': ['linear_enrichment', 'documentation_generation'],
                'status': 'success',
                'dry_run': self.safety.dry_run
            }
            self.save_task_history()
            
            logger.info("✅ Daily automation tasks completed")
            
        except Exception as e:
            logger.error(f"Error in daily tasks: {e}")
            self.task_history[datetime.now().isoformat()] = {
                'status': 'error',
                'error': str(e)
            }
            self.save_task_history()
    
    def run(self):
        """Main execution"""
        logger.info("=" * 50)
        logger.info(f"Barbossa Personal Assistant v2 for {self.context.name}")
        logger.info(f"GitHub: {self.context.github_username}")
        logger.info(f"Mode: {'DRY RUN' if self.safety.dry_run else 'LIVE'}")
        logger.info("=" * 50)
        
        # Run daily tasks once
        asyncio.run(self.run_daily_tasks())
        
        logger.info("\n✅ Execution complete. Check logs for details.")

def main():
    """Main entry point"""
    assistant = BarbossaPersonalAssistant()
    assistant.run()

if __name__ == "__main__":
    main()