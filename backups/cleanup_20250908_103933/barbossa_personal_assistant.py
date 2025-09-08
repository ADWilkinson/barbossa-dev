#!/usr/bin/env python3
"""
Barbossa Personal Assistant - Andrew's Workflow Automation System
Focused on automating daily development tasks for ADWilkinson
"""

import os
import json
import logging
import asyncio
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass, asdict
import schedule
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
    primary_repos: List[str] = None
    expertise_areas: List[str] = None
    
    def __post_init__(self):
        if self.primary_repos is None:
            self.primary_repos = [
                "zkp2p-v2-client",
                "zkp2p-v2-extension",
                "barbossa-engineer",
                "davy-jones-intern",
                "saylormemes",
                "the-flying-dutchman-theme"
            ]
        if self.expertise_areas is None:
            self.expertise_areas = [
                "Frontend Development",
                "React/TypeScript",
                "Browser Extensions",
                "UI/UX Design",
                "Web3 Integration"
            ]

class LinearAPIClient:
    """Linear API client for managing Andrew's tickets"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
    
    async def get_my_issues(self, user_id: str) -> List[Dict]:
        """Get all issues assigned to Andrew"""
        query = """
        query MyIssues($userId: String!) {
            issues(filter: {
                assignee: { id: { eq: $userId } }
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
        """
        
        variables = {"userId": user_id}
        response = requests.post(
            self.base_url,
            json={"query": query, "variables": variables},
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("issues", {}).get("nodes", [])
        else:
            logger.error(f"Linear API error: {response.status_code}")
            return []
    
    async def enrich_issue(self, issue_id: str, enrichment: Dict) -> bool:
        """Enrich a Linear issue with additional information"""
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
        
        response = requests.post(
            self.base_url,
            json={"query": mutation, "variables": variables},
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("issueUpdate", {}).get("success", False)
        else:
            logger.error(f"Failed to enrich issue {issue_id}: {response.status_code}")
            return False
    
    async def create_documentation_issue(self, title: str, description: str, project_id: str = None) -> Dict:
        """Create a documentation issue for Andrew"""
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                }
            }
        }
        """
        
        input_data = {
            "title": f"[Docs] {title}",
            "description": description,
            "assigneeId": AndrewContext().linear_user_id,
            "priority": 3,  # Medium priority
            "labelIds": []  # Add documentation label if exists
        }
        
        if project_id:
            input_data["projectId"] = project_id
        
        variables = {"input": input_data}
        
        response = requests.post(
            self.base_url,
            json={"query": mutation, "variables": variables},
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("issueCreate", {}).get("issue", {})
        else:
            logger.error(f"Failed to create documentation issue: {response.status_code}")
            return {}

class NotionAPIClient:
    """Notion API client for documentation management"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    async def create_documentation_page(self, title: str, content: str, parent_id: str = None) -> Dict:
        """Create a documentation page in Notion"""
        # Implementation for creating Notion pages
        # This would require knowing the specific database/page structure
        pass
    
    async def update_knowledge_base(self, updates: Dict) -> bool:
        """Update the knowledge base with new information"""
        # Implementation for updating Notion knowledge base
        pass

class BarbossaPersonalAssistant:
    """Main orchestrator for Andrew's personal workflow automation"""
    
    def __init__(self):
        self.context = AndrewContext()
        self.working_dir = Path.home() / "barbossa-engineer"
        self.logs_dir = self.working_dir / "logs" / "personal_assistant"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize API clients
        self.linear_client = None
        self.notion_client = None
        self.initialize_api_clients()
        
        # Work areas focused on Andrew's needs
        self.work_areas = {
            'linear_enrichment': {
                'description': 'Enrich Linear tickets assigned to Andrew',
                'priority': 1,
                'schedule': 'daily'
            },
            'documentation_generation': {
                'description': 'Generate documentation for Andrew\'s work',
                'priority': 2,
                'schedule': 'daily'
            },
            'davy_jones_improvement': {
                'description': 'Improve Davy Jones Intern bot capabilities',
                'priority': 3,
                'schedule': 'weekly'
            },
            'server_infrastructure': {
                'description': 'Optimize server infrastructure',
                'priority': 4,
                'schedule': 'weekly'
            },
            'barbossa_enhancement': {
                'description': 'Enhance Barbossa automation capabilities',
                'priority': 5,
                'schedule': 'weekly'
            }
        }
        
        # Task tracking
        self.task_history = self.load_task_history()
    
    def initialize_api_clients(self):
        """Initialize API clients with credentials"""
        # Load from environment or config
        linear_key = os.getenv('LINEAR_API_KEY')
        notion_key = os.getenv('NOTION_API_KEY')
        
        if linear_key:
            self.linear_client = LinearAPIClient(linear_key)
            logger.info("Linear API client initialized")
        else:
            logger.warning("No Linear API key found")
        
        if notion_key:
            self.notion_client = NotionAPIClient(notion_key)
            logger.info("Notion API client initialized")
        else:
            logger.warning("No Notion API key found")
    
    def load_task_history(self) -> Dict:
        """Load task execution history"""
        history_file = self.working_dir / "work_tracking" / "personal_assistant_history.json"
        if history_file.exists():
            with open(history_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_task_history(self):
        """Save task execution history"""
        history_file = self.working_dir / "work_tracking" / "personal_assistant_history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(self.task_history, f, indent=2)
    
    async def enrich_linear_tickets(self):
        """Enrich Andrew's Linear tickets with additional context"""
        if not self.linear_client:
            logger.warning("Linear client not initialized")
            return
        
        logger.info("Starting Linear ticket enrichment for Andrew")
        
        # Get Andrew's assigned issues
        issues = await self.linear_client.get_my_issues(self.context.linear_user_id)
        
        for issue in issues:
            issue_id = issue['id']
            identifier = issue['identifier']
            title = issue['title']
            description = issue.get('description', '')
            
            # Skip if already enriched (check for enrichment marker)
            if '[Auto-Enriched]' in description:
                continue
            
            logger.info(f"Enriching issue {identifier}: {title}")
            
            # Generate enrichment based on issue context
            enrichment = await self.generate_ticket_enrichment(issue)
            
            if enrichment:
                # Add enrichment to description
                new_description = f"{description}\n\n---\n[Auto-Enriched by Barbossa - {datetime.now().strftime('%Y-%m-%d')}]\n\n{enrichment}"
                
                success = await self.linear_client.enrich_issue(
                    issue_id,
                    {"description": new_description}
                )
                
                if success:
                    logger.info(f"Successfully enriched {identifier}")
                else:
                    logger.error(f"Failed to enrich {identifier}")
    
    async def generate_ticket_enrichment(self, issue: Dict) -> str:
        """Generate enrichment content for a Linear ticket"""
        title = issue['title']
        description = issue.get('description', '')
        labels = [label['name'] for label in issue.get('labels', {}).get('nodes', [])]
        project = issue.get('project', {}).get('name', 'Unknown')
        
        # Determine the type of ticket and generate appropriate enrichment
        enrichment_parts = []
        
        # Add implementation suggestions based on ticket type
        if 'frontend' in title.lower() or 'ui' in title.lower() or 'react' in title.lower():
            enrichment_parts.append("## Implementation Approach")
            enrichment_parts.append("- Component structure: Consider using compound components pattern")
            enrichment_parts.append("- State management: Evaluate if Context API or Redux is needed")
            enrichment_parts.append("- Performance: Implement React.memo for expensive components")
            enrichment_parts.append("- Testing: Add unit tests with Jest and RTL")
        
        if 'api' in title.lower() or 'endpoint' in title.lower():
            enrichment_parts.append("## API Design Considerations")
            enrichment_parts.append("- RESTful design principles")
            enrichment_parts.append("- Error handling and status codes")
            enrichment_parts.append("- Input validation and sanitization")
            enrichment_parts.append("- Rate limiting if needed")
        
        # Add relevant documentation links
        enrichment_parts.append("\n## Relevant Resources")
        if project == "zkp2p-v2-client":
            enrichment_parts.append("- [Frontend Architecture](../docs/frontend-architecture.md)")
            enrichment_parts.append("- [Component Guidelines](../docs/component-guidelines.md)")
        
        # Add testing checklist
        enrichment_parts.append("\n## Testing Checklist")
        enrichment_parts.append("- [ ] Unit tests written")
        enrichment_parts.append("- [ ] Integration tests if applicable")
        enrichment_parts.append("- [ ] Manual testing completed")
        enrichment_parts.append("- [ ] Cross-browser testing")
        
        # Add definition of done
        enrichment_parts.append("\n## Definition of Done")
        enrichment_parts.append("- [ ] Code reviewed")
        enrichment_parts.append("- [ ] Tests passing")
        enrichment_parts.append("- [ ] Documentation updated")
        enrichment_parts.append("- [ ] Deployed to staging")
        
        return "\n".join(enrichment_parts)
    
    async def generate_daily_documentation(self):
        """Generate daily documentation for Andrew's work"""
        logger.info("Generating daily documentation")
        
        timestamp = datetime.now().strftime("%Y-%m-%d")
        doc_content = []
        
        doc_content.append(f"# Daily Work Summary - {timestamp}")
        doc_content.append(f"\n## Developer: {self.context.name}")
        
        # Get today's Linear tickets
        if self.linear_client:
            issues = await self.linear_client.get_my_issues(self.context.linear_user_id)
            
            # Filter for recently updated
            today = datetime.now().date()
            recent_issues = [
                issue for issue in issues
                if datetime.fromisoformat(issue['updatedAt'].replace('Z', '+00:00')).date() == today
            ]
            
            if recent_issues:
                doc_content.append("\n## Linear Tickets Worked On")
                for issue in recent_issues:
                    doc_content.append(f"- [{issue['identifier']}] {issue['title']}")
                    doc_content.append(f"  - Status: {issue['state']['name']}")
        
        # Check git commits in Andrew's repos
        doc_content.append("\n## Repository Activity")
        for repo in self.context.primary_repos:
            repo_path = Path.home() / "projects" / repo
            if not repo_path.exists():
                repo_path = Path.home() / "barbossa-engineer" / "projects" / repo
            
            if repo_path.exists():
                try:
                    os.chdir(repo_path)
                    # Get today's commits
                    result = subprocess.run(
                        ["git", "log", "--since=midnight", "--author=Andrew", "--oneline"],
                        capture_output=True,
                        text=True
                    )
                    if result.stdout:
                        doc_content.append(f"\n### {repo}")
                        for line in result.stdout.strip().split('\n'):
                            doc_content.append(f"  - {line}")
                except Exception as e:
                    logger.error(f"Error checking repo {repo}: {e}")
        
        # Save documentation
        doc_file = self.logs_dir / f"daily_summary_{timestamp}.md"
        with open(doc_file, 'w') as f:
            f.write('\n'.join(doc_content))
        
        logger.info(f"Daily documentation saved to {doc_file}")
        
        # Optionally create Linear documentation ticket
        if self.linear_client:
            await self.linear_client.create_documentation_issue(
                f"Daily Summary - {timestamp}",
                '\n'.join(doc_content)
            )
    
    async def improve_davy_jones(self):
        """Analyze and improve Davy Jones Intern bot"""
        logger.info("Analyzing Davy Jones Intern for improvements")
        
        davy_path = Path.home() / "barbossa-engineer" / "projects" / "davy-jones-intern"
        
        improvements = []
        
        # Check for common issues
        if davy_path.exists():
            # Check error logs
            log_file = davy_path / "logs" / "error.log"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    recent_errors = f.readlines()[-100:]  # Last 100 errors
                    
                # Analyze error patterns
                error_types = {}
                for error in recent_errors:
                    if 'TypeError' in error:
                        error_types['TypeError'] = error_types.get('TypeError', 0) + 1
                    elif 'NetworkError' in error:
                        error_types['NetworkError'] = error_types.get('NetworkError', 0) + 1
                
                if error_types:
                    improvements.append(f"Error patterns detected: {error_types}")
            
            # Check for TODO comments
            result = subprocess.run(
                ["grep", "-r", "TODO", str(davy_path / "src"), "--include=*.ts"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                todo_count = len(result.stdout.strip().split('\n'))
                improvements.append(f"Found {todo_count} TODO items to address")
        
        # Log improvements
        if improvements:
            logger.info(f"Davy Jones improvements identified: {improvements}")
            
            # Create improvement ticket
            if self.linear_client:
                await self.linear_client.create_documentation_issue(
                    "Davy Jones Improvements",
                    '\n'.join(improvements)
                )
    
    async def optimize_server_infrastructure(self):
        """Optimize server infrastructure"""
        logger.info("Analyzing server infrastructure")
        
        # Check system resources
        result = subprocess.run(["df", "-h"], capture_output=True, text=True)
        disk_usage = result.stdout
        
        result = subprocess.run(["free", "-h"], capture_output=True, text=True)
        memory_usage = result.stdout
        
        # Check for large log files
        result = subprocess.run(
            ["find", str(Path.home()), "-type", "f", "-size", "+100M", "-name", "*.log"],
            capture_output=True,
            text=True
        )
        large_logs = result.stdout.strip().split('\n') if result.stdout else []
        
        if large_logs:
            logger.info(f"Found {len(large_logs)} large log files for cleanup")
            # Could implement log rotation here
    
    async def run_daily_tasks(self):
        """Run all daily tasks for Andrew"""
        logger.info("Starting daily automation tasks for Andrew")
        
        # Run tasks in sequence
        await self.enrich_linear_tickets()
        await self.generate_daily_documentation()
        
        # Update task history
        self.task_history[datetime.now().isoformat()] = {
            'tasks_completed': ['linear_enrichment', 'documentation_generation'],
            'status': 'success'
        }
        self.save_task_history()
        
        logger.info("Daily automation tasks completed")
    
    async def run_weekly_tasks(self):
        """Run weekly maintenance tasks"""
        logger.info("Starting weekly automation tasks")
        
        await self.improve_davy_jones()
        await self.optimize_server_infrastructure()
        
        logger.info("Weekly automation tasks completed")
    
    def schedule_tasks(self):
        """Schedule automated tasks"""
        # Daily tasks at 9 AM
        schedule.every().day.at("09:00").do(lambda: asyncio.run(self.run_daily_tasks()))
        
        # Weekly tasks on Monday at 10 AM
        schedule.every().monday.at("10:00").do(lambda: asyncio.run(self.run_weekly_tasks()))
        
        logger.info("Tasks scheduled - Daily at 9 AM, Weekly on Mondays at 10 AM")
    
    def run(self):
        """Main execution loop"""
        logger.info(f"Barbossa Personal Assistant starting for {self.context.name}")
        logger.info(f"GitHub: {self.context.github_username}")
        logger.info(f"Primary repos: {', '.join(self.context.primary_repos)}")
        
        # Run initial tasks
        asyncio.run(self.run_daily_tasks())
        
        # Schedule future tasks
        self.schedule_tasks()
        
        # Keep running and check schedule
        logger.info("Personal Assistant is running. Press Ctrl+C to stop.")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Personal Assistant stopped by user")

def main():
    """Main entry point"""
    assistant = BarbossaPersonalAssistant()
    assistant.run()

if __name__ == "__main__":
    main()