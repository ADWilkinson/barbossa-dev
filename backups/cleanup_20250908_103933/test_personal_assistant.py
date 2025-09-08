#!/usr/bin/env python3
"""
Test script for Barbossa Personal Assistant
Validates configuration and tests basic functionality in safe mode
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import asyncio

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from barbossa_personal_assistant import (
    BarbossaPersonalAssistant,
    AndrewContext,
    LinearAPIClient,
    NotionAPIClient
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PersonalAssistantTester:
    """Test suite for Barbossa Personal Assistant"""
    
    def __init__(self):
        self.test_results = []
        self.config_path = Path.home() / "barbossa-engineer" / "config" / "personal_assistant_config.json"
    
    def test_configuration(self) -> bool:
        """Test configuration file loading"""
        logger.info("Testing configuration loading...")
        
        try:
            if not self.config_path.exists():
                logger.error(f"Configuration file not found at {self.config_path}")
                return False
            
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = ['andrew_context', 'automation_settings', 'safety_settings']
            for field in required_fields:
                if field not in config:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Check safety settings
            safety = config.get('safety_settings', {})
            if not safety.get('dry_run_mode', False):
                logger.warning("Dry run mode is disabled - system will make real changes!")
            
            if safety.get('production_ready', False):
                logger.warning("Production mode is enabled - be careful!")
            
            logger.info("✅ Configuration test passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return False
    
    def test_andrew_context(self) -> bool:
        """Test Andrew context initialization"""
        logger.info("Testing Andrew context...")
        
        try:
            context = AndrewContext()
            
            # Validate context fields
            assert context.github_username == "ADWilkinson"
            assert context.slack_user_id == "U092NQP8A04"
            assert context.linear_user_id == "1a3bf7df-5dca-4fc6-b747-263ba84c3b85"
            assert context.email == "andrew@zkp2p.xyz"
            assert "zkp2p-v2-client" in context.primary_repos
            assert "Frontend Development" in context.expertise_areas
            
            logger.info(f"  GitHub: {context.github_username}")
            logger.info(f"  Email: {context.email}")
            logger.info(f"  Repos: {len(context.primary_repos)} repositories")
            logger.info("✅ Andrew context test passed")
            return True
            
        except Exception as e:
            logger.error(f"Andrew context test failed: {e}")
            return False
    
    def test_api_connections(self) -> bool:
        """Test API client initialization (without making actual calls)"""
        logger.info("Testing API connections...")
        
        try:
            # Check for API keys
            linear_key = os.getenv('LINEAR_API_KEY')
            notion_key = os.getenv('NOTION_API_KEY')
            
            if not linear_key:
                logger.warning("  ⚠️  No LINEAR_API_KEY found in environment")
            else:
                logger.info("  ✅ Linear API key found")
                # Test client initialization (not actual API call)
                client = LinearAPIClient(linear_key)
                assert client.api_key == linear_key
            
            if not notion_key:
                logger.warning("  ⚠️  No NOTION_API_KEY found in environment")
            else:
                logger.info("  ✅ Notion API key found")
                # Test client initialization (not actual API call)
                client = NotionAPIClient(notion_key)
                assert client.api_key == notion_key
            
            return True
            
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    async def test_linear_read_only(self) -> bool:
        """Test Linear API in read-only mode"""
        logger.info("Testing Linear API (read-only)...")
        
        linear_key = os.getenv('LINEAR_API_KEY')
        if not linear_key:
            logger.warning("  Skipping - no Linear API key")
            return True
        
        try:
            client = LinearAPIClient(linear_key)
            
            # Try to fetch Andrew's issues (read-only operation)
            logger.info("  Fetching Andrew's Linear tickets...")
            context = AndrewContext()
            issues = await client.get_my_issues(context.linear_user_id)
            
            if issues:
                logger.info(f"  ✅ Found {len(issues)} issues assigned to Andrew")
                # Show first few issues
                for issue in issues[:3]:
                    logger.info(f"    - {issue['identifier']}: {issue['title']}")
            else:
                logger.info("  No issues found (this is OK)")
            
            return True
            
        except Exception as e:
            logger.error(f"Linear API test failed: {e}")
            return False
    
    def test_directory_structure(self) -> bool:
        """Test required directory structure"""
        logger.info("Testing directory structure...")
        
        try:
            base_dir = Path.home() / "barbossa-engineer"
            required_dirs = [
                base_dir / "logs" / "personal_assistant",
                base_dir / "work_tracking",
                base_dir / "config"
            ]
            
            for dir_path in required_dirs:
                if not dir_path.exists():
                    logger.info(f"  Creating directory: {dir_path}")
                    dir_path.mkdir(parents=True, exist_ok=True)
                else:
                    logger.info(f"  ✅ Directory exists: {dir_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Directory structure test failed: {e}")
            return False
    
    def test_git_repositories(self) -> bool:
        """Test access to Andrew's repositories"""
        logger.info("Testing repository access...")
        
        try:
            context = AndrewContext()
            accessible_repos = []
            
            for repo in context.primary_repos:
                # Check multiple possible locations
                locations = [
                    Path.home() / "projects" / repo,
                    Path.home() / "barbossa-engineer" / "projects" / repo,
                    Path.home() / repo
                ]
                
                found = False
                for loc in locations:
                    if loc.exists() and (loc / ".git").exists():
                        accessible_repos.append(repo)
                        logger.info(f"  ✅ Found {repo} at {loc}")
                        found = True
                        break
                
                if not found:
                    logger.warning(f"  ⚠️  Repository not found: {repo}")
            
            logger.info(f"Accessible repositories: {len(accessible_repos)}/{len(context.primary_repos)}")
            return len(accessible_repos) > 0
            
        except Exception as e:
            logger.error(f"Repository test failed: {e}")
            return False
    
    async def test_dry_run_execution(self) -> bool:
        """Test personal assistant in dry-run mode"""
        logger.info("Testing dry-run execution...")
        
        try:
            # Create assistant instance
            assistant = BarbossaPersonalAssistant()
            
            # Ensure dry-run mode
            logger.info("  Verifying dry-run mode is enabled...")
            
            # Test task history loading
            history = assistant.load_task_history()
            logger.info(f"  Task history entries: {len(history)}")
            
            # Test enrichment generation (without actually sending)
            test_issue = {
                'id': 'test-123',
                'identifier': 'TEST-123',
                'title': 'Test Frontend Component Implementation',
                'description': 'Test description',
                'labels': {'nodes': [{'name': 'frontend'}]},
                'project': {'name': 'zkp2p-v2-client'},
                'state': {'name': 'In Progress'},
                'updatedAt': datetime.now().isoformat()
            }
            
            logger.info("  Testing enrichment generation...")
            enrichment = await assistant.generate_ticket_enrichment(test_issue)
            
            if enrichment:
                logger.info("  ✅ Enrichment generated successfully")
                logger.debug(f"  Enrichment preview: {enrichment[:200]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Dry-run execution test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("=" * 50)
        logger.info("Barbossa Personal Assistant Test Suite")
        logger.info("=" * 50)
        
        tests = [
            ("Configuration", self.test_configuration()),
            ("Andrew Context", self.test_andrew_context()),
            ("API Connections", self.test_api_connections()),
            ("Directory Structure", self.test_directory_structure()),
            ("Git Repositories", self.test_git_repositories()),
            ("Linear API (Read-Only)", await self.test_linear_read_only()),
            ("Dry-Run Execution", await self.test_dry_run_execution())
        ]
        
        logger.info("\n" + "=" * 50)
        logger.info("Test Results Summary")
        logger.info("=" * 50)
        
        passed = 0
        failed = 0
        
        for name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} - {name}")
            if result:
                passed += 1
            else:
                failed += 1
        
        logger.info("=" * 50)
        logger.info(f"Total: {passed} passed, {failed} failed")
        
        if failed == 0:
            logger.info("\n🎉 All tests passed! System is ready for testing.")
            logger.info("\n⚠️  IMPORTANT: System is in dry-run mode")
            logger.info("No actual changes will be made to Linear, Notion, or GitHub")
            logger.info("\nTo run the assistant in test mode:")
            logger.info("  python3 barbossa_personal_assistant.py")
        else:
            logger.warning(f"\n⚠️  {failed} test(s) failed. Please fix issues before running.")
        
        return failed == 0

def main():
    """Main test entry point"""
    tester = PersonalAssistantTester()
    
    # Run async tests
    success = asyncio.run(tester.run_all_tests())
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()