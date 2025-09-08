#!/usr/bin/env python3
"""
Barbossa Personal Assistant v3 - Development-Focused Automation
Enriches Linear tickets with development context and contributes to projects
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
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AndrewContext:
    """Andrew's context and project information"""
    name: str = "Andrew Wilkinson"
    github_username: str = "ADWilkinson"
    linear_user_id: str = "1a3bf7df-5dca-4fc6-b747-263ba84c3b85"
    email: str = "andrew@zkp2p.xyz"
    
    # Project repositories with actual paths
    projects: Dict[str, str] = None
    
    def __post_init__(self):
        if self.projects is None:
            self.projects = {
                "zkp2p-v2-client": "~/projects/zkp2p/zkp2p-v2-client",
                "zkp2p-v2-extension": "~/projects/zkp2p/zkp2p-v2-extension",
                "zkp2p-v2-contracts": "~/projects/zkp2p/zkp2p-v2-contracts",
                "barbossa-engineer": "~/barbossa-engineer",
                "davy-jones-intern": "~/projects/davy-jones-intern",
            }

class SafetyManager:
    """Manages safety checks and dry-run mode"""
    
    def __init__(self):
        self.dry_run = os.getenv('DRY_RUN_MODE', 'true').lower() == 'true'
        self.test_environment = os.getenv('TEST_ENVIRONMENT', 'true').lower() == 'true'
        
        if self.dry_run:
            logger.info("🛡️ DRY RUN MODE - No changes will be made")
        else:
            logger.warning("⚠️ LIVE MODE - Real changes will be made!")
    
    def can_modify(self, operation: str, target: str = None) -> bool:
        """Check if modification is allowed"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would: {operation} on {target or 'system'}")
            return False
        return True

class LinearAPIClient:
    """Linear API client for ticket enrichment"""
    
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
    
    async def get_todo_tickets(self, user_id: str) -> List[Dict]:
        """Get only tickets in Todo/Backlog state for Andrew"""
        try:
            # Get ALL assigned issues first, then filter by state
            query = """
            query GetAssignedIssues($userId: String!) {
                user(id: $userId) {
                    assignedIssues(first: 100) {
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
                            team {
                                key
                            }
                            createdAt
                            updatedAt
                        }
                    }
                }
            }
            """
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            variables = {"userId": user_id}
            
            async with self.session.post(
                self.base_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    user_data = data.get("data", {}).get("user", {})
                    if user_data:
                        all_issues = user_data.get("assignedIssues", {}).get("nodes", [])
                        
                        # Filter for Todo/Backlog states
                        todo_issues = [
                            issue for issue in all_issues
                            if issue.get('state', {}).get('type') in ['backlog', 'unstarted'] or
                               issue.get('state', {}).get('name', '').lower() in ['todo', 'to do', 'backlog']
                        ]
                        
                        logger.info(f"Found {len(todo_issues)} Todo/Backlog tickets (from {len(all_issues)} total)")
                        return todo_issues
                    return []
                else:
                    logger.error(f"Linear API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching Todo tickets: {e}")
            return []
    
    async def update_ticket_description(self, issue_id: str, identifier: str, new_description: str) -> bool:
        """Update ticket description with enrichment"""
        if not self.safety.can_modify("update_ticket_description", identifier):
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
                "input": {"description": new_description}
            }
            
            async with self.session.post(
                self.base_url,
                json={"query": mutation, "variables": variables},
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    success = data.get("data", {}).get("issueUpdate", {}).get("success", False)
                    if success:
                        logger.info(f"✅ Updated {identifier} description")
                    return success
                else:
                    logger.error(f"Failed to update {identifier}: Status {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating {identifier}: {e}")
            return False

class DevelopmentEnrichmentService:
    """Generate development-specific enrichment using Claude"""
    
    def __init__(self, anthropic_key: str, github_token: str, context: AndrewContext):
        self.anthropic_key = anthropic_key
        self.github_token = github_token
        self.context = context
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        } if anthropic_key else None
    
    async def analyze_codebase_for_ticket(self, ticket: Dict) -> Dict:
        """Analyze codebase to find relevant files and dependencies"""
        title = ticket.get('title', '')
        project = ticket.get('project', {}).get('name', '')
        labels = [l['name'] for l in ticket.get('labels', {}).get('nodes', [])]
        
        # Determine which repository to analyze
        repo_path = None
        if 'client' in project.lower() or 'frontend' in ' '.join(labels).lower():
            repo_path = self.context.projects.get('zkp2p-v2-client')
        elif 'extension' in project.lower():
            repo_path = self.context.projects.get('zkp2p-v2-extension')
        elif 'contract' in project.lower():
            repo_path = self.context.projects.get('zkp2p-v2-contracts')
        
        analysis = {
            'relevant_files': [],
            'dependencies': [],
            'documentation': [],
            'related_tickets': []
        }
        
        if repo_path:
            expanded_path = os.path.expanduser(repo_path)
            if os.path.exists(expanded_path):
                # Search for relevant files based on ticket title
                keywords = title.lower().split()
                
                try:
                    # Search for files containing keywords
                    for keyword in keywords[:3]:  # Limit to first 3 keywords
                        if len(keyword) > 3:  # Skip short words
                            result = subprocess.run(
                                ["find", expanded_path, "-name", f"*{keyword}*.{'{ts,tsx,js,jsx}'}", "-type", "f"],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            if result.stdout:
                                files = result.stdout.strip().split('\n')[:5]  # Limit to 5 files
                                for f in files:
                                    relative_path = f.replace(expanded_path, '').lstrip('/')
                                    if relative_path and relative_path not in analysis['relevant_files']:
                                        analysis['relevant_files'].append(relative_path)
                except Exception as e:
                    logger.debug(f"Error searching files: {e}")
        
        return analysis
    
    async def generate_development_context(self, ticket: Dict) -> str:
        """Generate specific development context for the ticket"""
        title = ticket.get('title', '')
        description = ticket.get('description', '')
        project = ticket.get('project', {}).get('name', '')
        labels = [l['name'] for l in ticket.get('labels', {}).get('nodes', [])]
        
        # Analyze codebase
        analysis = await self.analyze_codebase_for_ticket(ticket)
        
        # If we have Claude API, use it for intelligent analysis
        if self.headers:
            prompt = f"""Analyze this Linear ticket and provide ONLY specific development context.
            
Ticket: {title}
Description: {description}
Project: {project}
Labels: {', '.join(labels)}

Based on this being a {project} ticket, provide ONLY:
1. Specific files that will need to be modified (be specific about component names)
2. Key dependencies or imports needed
3. Related documentation or examples to reference
4. Any gotchas or things to watch out for

Be extremely concise and specific. No boilerplate about testing or security.
Focus only on what will help the developer start coding immediately."""

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.base_url,
                        json={
                            "model": "claude-3-sonnet-20240229",
                            "max_tokens": 500,
                            "messages": [{"role": "user", "content": prompt}]
                        },
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=20)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("content", [{}])[0].get("text", "")
            except Exception as e:
                logger.debug(f"Claude API error: {e}")
        
        # Fallback to pattern-based enrichment
        return self._generate_static_context(ticket, analysis)
    
    def _generate_static_context(self, ticket: Dict, analysis: Dict) -> str:
        """Generate context without Claude API"""
        title = ticket.get('title', '')
        project = ticket.get('project', {}).get('name', '')
        labels = [l['name'] for l in ticket.get('labels', {}).get('nodes', [])]
        
        context_parts = []
        
        # Add found files if any
        if analysis['relevant_files']:
            context_parts.append(f"**Potentially related files:**")
            for f in analysis['relevant_files'][:5]:
                context_parts.append(f"- `{f}`")
        
        # Pattern-based suggestions
        title_lower = title.lower()
        
        if 'modal' in title_lower or 'dialog' in title_lower:
            context_parts.append("\n**Key files:** `src/components/modals/`, `src/hooks/useModal.ts`")
            context_parts.append("**Dependencies:** MUI Dialog, useCallback, useState")
            
        elif 'deposit' in title_lower:
            context_parts.append("\n**Key files:** `src/components/Deposit/`, `src/hooks/useDeposit.ts`")
            context_parts.append("**Related:** DepositContext, deposit validation logic")
            
        elif 'swap' in title_lower:
            context_parts.append("\n**Key files:** `src/components/Swap/`, `src/contexts/SwapContext.tsx`")
            context_parts.append("**Dependencies:** Swap hooks, rate calculations")
            
        elif 'relay' in title_lower:
            context_parts.append("\n**Key files:** `src/services/relay/`, `src/hooks/useRelay.ts`")
            context_parts.append("**Dependencies:** Relay API client, WebSocket connections")
            
        elif 'proof' in title_lower:
            context_parts.append("\n**Key files:** `src/services/proof/`, `src/workers/proofWorker.ts`")
            context_parts.append("**Note:** Check proof generation worker and validation")
        
        # Add project-specific hints
        if 'zkp2p-v2-client' in project.lower():
            context_parts.append("\n**Docs:** See `/docs/frontend-architecture.md`")
        elif 'extension' in project.lower():
            context_parts.append("\n**Manifest:** Check `manifest.json` for permissions")
        
        return '\n'.join(context_parts) if context_parts else "No specific context generated"

class AutonomousDevelopmentService:
    """Service for autonomous development on projects"""
    
    def __init__(self, context: AndrewContext, safety: SafetyManager):
        self.context = context
        self.safety = safety
        self.improvements = {
            'davy-jones': [],
            'barbossa': [],
            'infrastructure': []
        }
    
    async def analyze_davy_jones(self) -> List[str]:
        """Analyze Davy Jones Intern for improvements"""
        improvements = []
        davy_path = os.path.expanduser("~/projects/davy-jones-intern")
        
        if os.path.exists(davy_path):
            # Check for TODO comments
            try:
                result = subprocess.run(
                    ["grep", "-r", "TODO", f"{davy_path}/src", "--include=*.ts"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout:
                    todo_count = len(result.stdout.strip().split('\n'))
                    improvements.append(f"Found {todo_count} TODO items in code")
            except:
                pass
            
            # Check for error patterns in logs
            log_path = f"{davy_path}/logs/error.log"
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r') as f:
                        lines = f.readlines()[-100:]  # Last 100 lines
                        error_types = {}
                        for line in lines:
                            if 'Error' in line:
                                error_type = line.split(':')[0] if ':' in line else 'Unknown'
                                error_types[error_type] = error_types.get(error_type, 0) + 1
                        
                        if error_types:
                            top_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:3]
                            for error, count in top_errors:
                                improvements.append(f"Fix recurring error: {error} ({count} occurrences)")
                except:
                    pass
        
        self.improvements['davy-jones'] = improvements
        return improvements
    
    async def analyze_barbossa(self) -> List[str]:
        """Analyze Barbossa for self-improvements"""
        improvements = []
        
        # Check for enhancement opportunities
        improvements.append("Add rate limiting for API calls")
        improvements.append("Implement caching for repeated Linear queries")
        improvements.append("Add webhook support for real-time ticket updates")
        
        self.improvements['barbossa'] = improvements
        return improvements
    
    async def analyze_infrastructure(self) -> List[str]:
        """Analyze server infrastructure for improvements"""
        improvements = []
        
        # Check disk usage
        try:
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    usage = lines[1].split()[4].replace('%', '')
                    if int(usage) > 80:
                        improvements.append(f"Clean disk space (currently {usage}% used)")
        except:
            pass
        
        # Check for large log files
        try:
            result = subprocess.run(
                ["find", os.path.expanduser("~"), "-name", "*.log", "-size", "+100M", "-type", "f"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                large_logs = result.stdout.strip().split('\n')
                if large_logs:
                    improvements.append(f"Rotate {len(large_logs)} large log files")
        except:
            pass
        
        self.improvements['infrastructure'] = improvements
        return improvements
    
    async def create_improvement_task(self, improvement: str, project: str) -> Optional[str]:
        """Create a development task for an improvement"""
        if not self.safety.can_modify("create_improvement_task", project):
            return None
        
        # In production, this would create actual PRs or issues
        logger.info(f"Would create task for {project}: {improvement}")
        return f"Task created: {improvement}"

class BarbossaPersonalAssistant:
    """Main orchestrator for development automation"""
    
    def __init__(self):
        self.context = AndrewContext()
        self.safety = SafetyManager()
        self.working_dir = Path.home() / "barbossa-engineer"
        self.logs_dir = self.working_dir / "logs" / "barbossa"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.linear_client = None
        self.enrichment_service = None
        self.dev_service = None
        self.initialize_services()
        
        # Track operations
        self.operations_log = []
    
    def initialize_services(self):
        """Initialize all services"""
        linear_key = os.getenv('LINEAR_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        github_token = os.getenv('GITHUB_TOKEN')
        
        if linear_key:
            self.linear_client = LinearAPIClient(linear_key, self.safety)
            logger.info("✅ Linear client initialized")
        
        if anthropic_key or github_token:
            self.enrichment_service = DevelopmentEnrichmentService(
                anthropic_key, github_token, self.context
            )
            logger.info("✅ Enrichment service initialized")
        
        self.dev_service = AutonomousDevelopmentService(self.context, self.safety)
        logger.info("✅ Development service initialized")
    
    async def enrich_todo_tickets(self):
        """Enrich only Todo tickets with development context"""
        if not self.linear_client or not self.enrichment_service:
            logger.warning("Required services not initialized")
            return
        
        logger.info("🎯 Enriching Todo tickets for Andrew")
        
        try:
            async with self.linear_client:
                # Get only Todo tickets
                tickets = await self.linear_client.get_todo_tickets(self.context.linear_user_id)
                
                if not tickets:
                    logger.info("No Todo tickets found")
                    self.operations_log.append("No Todo tickets to enrich")
                    return
                
                enriched_count = 0
                for ticket in tickets[:10]:  # Limit to 10 tickets per run
                    identifier = ticket['identifier']
                    title = ticket['title']
                    description = ticket.get('description', '')
                    
                    # Skip if already enriched
                    if description and '## Development Context' in description:
                        logger.info(f"Skipping {identifier} - already enriched")
                        continue
                    
                    logger.info(f"Enriching {identifier}: {title}")
                    
                    # Generate development context
                    context = await self.enrichment_service.generate_development_context(ticket)
                    
                    if context:
                        # Add context to the END of description
                        new_description = f"{description}\n\n---\n## Development Context\n{context}"
                        
                        # Update ticket
                        success = await self.linear_client.update_ticket_description(
                            ticket['id'],
                            identifier,
                            new_description
                        )
                        
                        if success:
                            enriched_count += 1
                            self.operations_log.append(f"Enriched {identifier}")
                
                logger.info(f"✅ Enriched {enriched_count} tickets")
                self.operations_log.append(f"Enriched {enriched_count} Todo tickets")
                
        except Exception as e:
            logger.error(f"Error enriching tickets: {e}")
            self.operations_log.append(f"Error: {str(e)}")
    
    async def develop_improvements(self):
        """Analyze and develop improvements for projects"""
        logger.info("🔧 Analyzing projects for improvements")
        
        # Analyze each project
        davy_improvements = await self.dev_service.analyze_davy_jones()
        barbossa_improvements = await self.dev_service.analyze_barbossa()
        infra_improvements = await self.dev_service.analyze_infrastructure()
        
        # Log findings
        if davy_improvements:
            logger.info(f"Davy Jones: {len(davy_improvements)} improvements found")
            self.operations_log.append(f"Davy Jones: {davy_improvements[0] if davy_improvements else 'None'}")
        
        if barbossa_improvements:
            logger.info(f"Barbossa: {len(barbossa_improvements)} improvements found")
            self.operations_log.append(f"Barbossa: {barbossa_improvements[0] if barbossa_improvements else 'None'}")
        
        if infra_improvements:
            logger.info(f"Infrastructure: {len(infra_improvements)} improvements found")
            self.operations_log.append(f"Infrastructure: {infra_improvements[0] if infra_improvements else 'None'}")
        
        # In production, would create PRs or tasks for improvements
        total_improvements = len(davy_improvements) + len(barbossa_improvements) + len(infra_improvements)
        logger.info(f"✅ Found {total_improvements} total improvements")
    
    def save_operations_log(self):
        """Save log of what Barbossa did"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        log_file = self.logs_dir / f"barbossa_operations_{timestamp}.log"
        
        log_content = [
            f"# Barbossa Operations Log - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Mode: {'DRY RUN' if self.safety.dry_run else 'LIVE'}",
            "",
            "## Operations Performed:",
        ]
        
        for op in self.operations_log:
            log_content.append(f"- {op}")
        
        try:
            with open(log_file, 'w') as f:
                f.write('\n'.join(log_content))
            logger.info(f"Operations log saved to {log_file}")
        except Exception as e:
            logger.error(f"Error saving log: {e}")
    
    async def run(self):
        """Main execution"""
        logger.info("=" * 50)
        logger.info("🏴‍☠️ Barbossa Personal Assistant v3")
        logger.info(f"Mode: {'DRY RUN' if self.safety.dry_run else 'LIVE'}")
        logger.info("=" * 50)
        
        # Run main tasks
        await self.enrich_todo_tickets()
        await self.develop_improvements()
        
        # Save operations log
        self.save_operations_log()
        
        logger.info("\n✅ Execution complete")

def main():
    """Main entry point"""
    assistant = BarbossaPersonalAssistant()
    asyncio.run(assistant.run())

if __name__ == "__main__":
    main()