#!/usr/bin/env python3
"""
Barbossa - Autonomous Software Engineer
Main program that performs scheduled development tasks with strict security controls.
"""

import argparse
import json
import logging
import os
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import security guard - this is CRITICAL
from security_guard import security_guard, SecurityViolationError


class Barbossa:
    """
    Main Barbossa autonomous engineer class.
    Executes development tasks while enforcing strict security policies.
    """
    
    WORK_AREAS = {
        'infrastructure': {
            'name': 'Server Infrastructure Improvements',
            'description': 'Enhance server infrastructure, security, and optimization',
            'weight': 1.0
        },
        'personal_projects': {
            'name': 'Personal Project Feature Development',
            'description': 'Develop features for ADWilkinson repositories',
            'repositories': [
                'ADWilkinson/_save',
                'ADWilkinson/chordcraft-app',
                'ADWilkinson/piggyonchain',
                'ADWilkinson/personal-website',  # Fixed: was persona-website
                'ADWilkinson/saylormemes',  # Fixed: was saylor-memes
                'ADWilkinson/the-flying-dutchman-theme'
            ],
            'weight': 2.0
        },
        'davy_jones': {
            'name': 'Davy Jones Intern Development',
            'description': 'Improve the Davy Jones Intern bot (without affecting production)',
            'repository': 'ADWilkinson/davy-jones-intern',
            'weight': 1.5,
            'warning': 'DO NOT redeploy or affect running production instance'
        }
    }
    
    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize Barbossa with working directory and configuration"""
        self.work_dir = work_dir or Path.home() / 'barbossa-engineer'
        self.logs_dir = self.work_dir / 'logs'
        self.changelogs_dir = self.work_dir / 'changelogs'
        self.work_tracking_dir = self.work_dir / 'work_tracking'
        
        # Ensure directories exist
        for dir_path in [self.logs_dir, self.changelogs_dir, self.work_tracking_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self._setup_logging()
        
        # Load work tally
        self.work_tally = self._load_work_tally()
        
        self.logger.info("=" * 60)
        self.logger.info("BARBOSSA INITIALIZED - Autonomous Software Engineer")
        self.logger.info(f"Working directory: {self.work_dir}")
        self.logger.info("Security guard: ACTIVE - ZKP2P access BLOCKED")
        self.logger.info("=" * 60)
    
    def _setup_logging(self):
        """Configure logging for Barbossa operations"""
        log_file = self.logs_dir / f"barbossa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('barbossa')
        self.logger.info(f"Logging to: {log_file}")
    
    def _load_work_tally(self) -> Dict[str, int]:
        """Load the work tally from JSON file"""
        tally_file = self.work_tracking_dir / 'work_tally.json'
        if tally_file.exists():
            with open(tally_file, 'r') as f:
                return json.load(f)
        return {area: 0 for area in self.WORK_AREAS.keys()}
    
    def _save_work_tally(self):
        """Save the updated work tally to JSON file"""
        tally_file = self.work_tracking_dir / 'work_tally.json'
        with open(tally_file, 'w') as f:
            json.dump(self.work_tally, f, indent=2)
        self.logger.info(f"Work tally saved: {self.work_tally}")
    
    def select_work_area(self, provided_tally: Optional[Dict] = None) -> str:
        """
        Select a work area based on weighted random selection and work history.
        Favors areas that have been worked on less.
        """
        if provided_tally:
            self.work_tally.update(provided_tally)
        
        # Calculate selection weights (inverse of work count)
        weights = {}
        for area, config in self.WORK_AREAS.items():
            base_weight = config['weight']
            work_count = self.work_tally.get(area, 0)
            # Inverse weight: less worked areas get higher weight
            adjusted_weight = base_weight * (1.0 / (work_count + 1))
            weights[area] = adjusted_weight
        
        # Normalize weights
        total_weight = sum(weights.values())
        probabilities = {k: v/total_weight for k, v in weights.items()}
        
        self.logger.info("Work area selection probabilities:")
        for area, prob in probabilities.items():
            self.logger.info(f"  {area}: {prob:.2%} (worked {self.work_tally.get(area, 0)} times)")
        
        # Select area based on weighted random
        selected = random.choices(
            list(probabilities.keys()),
            weights=list(probabilities.values()),
            k=1
        )[0]
        
        self.logger.info(f"SELECTED WORK AREA: {selected}")
        return selected
    
    def validate_repository_access(self, repo_url: str) -> bool:
        """
        Validate repository access through security guard.
        This is a CRITICAL security checkpoint.
        """
        try:
            self.logger.info(f"Security check for repository: {repo_url}")
            security_guard.validate_operation('repository_access', repo_url)
            self.logger.info("✓ Security check PASSED")
            return True
        except SecurityViolationError as e:
            self.logger.error(f"✗ SECURITY VIOLATION: {e}")
            self.logger.error("Operation ABORTED - attempting to access forbidden repository")
            # Log to changelog
            self._log_security_violation(repo_url, str(e))
            return False
        except Exception as e:
            self.logger.error(f"Security check failed: {e}")
            return False
    
    def _log_security_violation(self, target: str, reason: str):
        """Log security violations to changelog"""
        violation_log = self.changelogs_dir / 'security_violations.log'
        with open(violation_log, 'a') as f:
            f.write(f"\n{datetime.now().isoformat()} - VIOLATION\n")
            f.write(f"Target: {target}\n")
            f.write(f"Reason: {reason}\n")
            f.write("-" * 40 + "\n")
    
    def execute_infrastructure_improvements(self):
        """Execute server infrastructure improvement tasks using Claude CLI"""
        self.logger.info("Executing infrastructure improvements...")
        
        # Create prompt for Claude
        prompt = f"""You are Barbossa, an autonomous software engineer working on server infrastructure.

CRITICAL SECURITY RULE: You must NEVER access, clone, modify, or interact with ANY repositories under the Z-K-P-2-P organizations. This is strictly forbidden.
        
Your task is to improve the server infrastructure at {Path.home()}. Choose ONE of these tasks and execute it completely:

1. Check and update system packages (apt update, upgrade safe packages)
2. Review and improve security configurations (UFW rules, SSH settings)
3. Optimize Docker containers (prune unused images, check resource usage)
4. Clean up large log files (find and rotate/compress logs over 100MB)
5. Update project dependencies (check npm/pip packages for security updates)

IMPORTANT:
- Execute REAL commands and make ACTUAL improvements
- Be careful with system-critical operations
- Document what you did in detail
- Run appropriate test commands to verify your work
- Create a detailed changelog of your actions

System Info:
- OS: Ubuntu 24.04 LTS
- User: {os.getenv('USER')}
- Home: {Path.home()}
- Server IP: 192.168.1.138

Available tools: apt, docker, npm, pip, systemctl, ufw, git
You have sudo access with password: Ableton6242

Complete the task fully and report what was accomplished."""

        # Save prompt to file
        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        # Execute with Claude CLI in background
        self.logger.info("Calling Claude CLI for infrastructure work...")
        
        # Create output file for Claude's results
        output_file = self.logs_dir / f"claude_infrastructure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Launch Claude in background, redirecting output to file
        cmd = f"nohup claude --dangerously-skip-permissions < {prompt_file} > {output_file} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        
        self.logger.info(f"Claude launched in background. Output will be saved to: {output_file}")
        
        # Save initial changelog noting the task was started
        changelog = []
        changelog.append(f"# Infrastructure Improvements - {datetime.now().isoformat()}\n")
        changelog.append("## Task Started\n")
        changelog.append(f"Claude CLI launched in background for infrastructure improvements.\n")
        changelog.append(f"Output file: {output_file}\n")
        changelog.append(f"Prompt file: {prompt_file}\n")
        changelog.append("\n### Selected Tasks:\n")
        changelog.append("- Check and update system packages\n")
        changelog.append("- Review security configurations\n")
        changelog.append("- Optimize Docker containers\n")
        changelog.append("- Clean up large log files\n")
        changelog.append("- Update project dependencies\n")
        
        self._save_changelog('infrastructure', changelog)
        
        self.logger.info("Infrastructure improvements completed")
    
    def execute_personal_project_development(self):
        """Execute personal project feature development using Claude CLI"""
        self.logger.info("Executing personal project development...")
        
        # Select a repository
        repos = self.WORK_AREAS['personal_projects']['repositories']
        selected_repo = random.choice(repos)
        
        repo_url = f"https://github.com/{selected_repo}"
        
        # CRITICAL: Validate repository access
        if not self.validate_repository_access(repo_url):
            self.logger.error("Repository access denied by security guard")
            return
        
        self.logger.info(f"Working on repository: {selected_repo}")
        
        # Create prompt for Claude
        prompt = f"""You are Barbossa, an autonomous software engineer working on personal projects.

CRITICAL SECURITY RULE: You must NEVER access, clone, modify, or interact with ANY repositories under the Z-K-P-2-P organizations. Only work on ADWilkinson repositories.

Your task is to improve the repository: {selected_repo}

Repository URL: {repo_url}

INSTRUCTIONS:
1. Clone or update the repository to ~/barbossa-engineer/projects/
2. Analyze the codebase thoroughly
3. Choose ONE meaningful improvement:
   - Add missing tests for critical functions
   - Refactor complex code for better readability
   - Fix any obvious bugs or issues
   - Add missing documentation
   - Improve error handling
   - Optimize performance bottlenecks
   - Update outdated dependencies (if safe)

4. Implement the improvement completely
5. If the project has build/test scripts, run them (check package.json or README)
6. Create a new branch for your changes
7. Commit with a clear message
8. Create a PR to the main branch

IMPORTANT:
- Make REAL, meaningful improvements to the code
- If tests exist, ensure they pass before committing
- Write clean, well-documented code
- Follow the project's existing code style
- Create a detailed PR description

GitHub is configured with token access. You can push branches and create PRs.

Complete the task fully and create a PR for review."""

        # Save prompt to file
        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        # Execute with Claude CLI in background
        self.logger.info("Calling Claude CLI for personal project work...")
        
        # Create output file for Claude's results
        output_file = self.logs_dir / f"claude_personal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Launch Claude in background
        cmd = f"nohup claude --dangerously-skip-permissions < {prompt_file} > {output_file} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        
        self.logger.info(f"Claude launched in background. Output will be saved to: {output_file}")
        
        # Save initial changelog
        changelog = []
        changelog.append(f"# Personal Project Development - {datetime.now().isoformat()}\n")
        changelog.append(f"## Repository: {selected_repo}\n")
        changelog.append("## Task Started\n")
        changelog.append(f"Claude CLI launched in background for repository improvements.\n")
        changelog.append(f"Output file: {output_file}\n")
        changelog.append(f"Repository URL: {repo_url}\n")
        changelog.append("\n### Potential Improvements:\n")
        changelog.append("- Add missing tests\n")
        changelog.append("- Refactor complex code\n")
        changelog.append("- Fix bugs\n")
        changelog.append("- Add documentation\n")
        changelog.append("- Improve error handling\n")
        
        self._save_changelog('personal_projects', changelog)
        
        self.logger.info("Personal project development completed")
    
    def execute_davy_jones_development(self):
        """Execute Davy Jones Intern development using Claude CLI (without affecting production)"""
        self.logger.info("Executing Davy Jones Intern development...")
        self.logger.warning("REMINDER: Do not redeploy or affect production instance!")
        
        repo_url = "https://github.com/ADWilkinson/davy-jones-intern"
        
        # CRITICAL: Validate repository access
        if not self.validate_repository_access(repo_url):
            self.logger.error("Repository access denied by security guard")
            return
        
        # Create prompt for Claude
        prompt = f"""You are Barbossa, an autonomous software engineer working on the Davy Jones Intern bot.

CRITICAL SECURITY RULE: You must NEVER access, clone, modify, or interact with ANY repositories under the Z-K-P-2-P organizations. Only work on ADWilkinson/davy-jones-intern.

CRITICAL WARNING: The bot is currently RUNNING IN PRODUCTION. DO NOT:
- Stop or restart the production service
- Run docker-compose down or docker-compose restart
- Modify any running containers
- Change production configuration files
- Deploy or redeploy anything

Your task is to improve the Davy Jones Intern codebase at: {repo_url}

SAFE INSTRUCTIONS:
1. Clone or update the repository to ~/barbossa-engineer/projects/davy-jones-intern
2. Analyze the codebase for improvements
3. Choose ONE meaningful improvement:
   - Add comprehensive tests for untested functions
   - Improve error handling and resilience
   - Refactor complex code for maintainability
   - Add better logging and debugging capabilities
   - Optimize performance in bot responses
   - Enhance Slack interaction features
   - Improve Claude integration efficiency

4. Implement the improvement in a NEW FEATURE BRANCH
5. If available, run tests and linting (check package.json for scripts)
6. Verify your changes work correctly
7. Create a detailed PR to main branch for review

PRODUCTION SAFETY:
- Work ONLY in the cloned repository at ~/barbossa-engineer/projects/
- Do NOT touch the running Docker container (davy-jones-intern)
- Do NOT modify .env files in the production directory ~/projects/davy-jones-intern
- Create all changes in a feature branch
- The PR will be manually reviewed before any production deployment

The bot is accessible at https://webhook.eastindiaonchaincompany.xyz
Current production directory: ~/projects/davy-jones-intern (DO NOT MODIFY)
Your work directory: ~/barbossa-engineer/projects/davy-jones-intern

Complete the improvement and create a PR for manual review."""

        # Save prompt to file
        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        # Execute with Claude CLI in background
        self.logger.info("Calling Claude CLI for Davy Jones development...")
        
        # Create output file for Claude's results
        output_file = self.logs_dir / f"claude_davy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Launch Claude in background
        cmd = f"nohup claude --dangerously-skip-permissions < {prompt_file} > {output_file} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        
        self.logger.info(f"Claude launched in background. Output will be saved to: {output_file}")
        
        # Save initial changelog
        changelog = []
        changelog.append(f"# Davy Jones Intern Development - {datetime.now().isoformat()}\n")
        changelog.append("## ⚠️ PRODUCTION SAFETY: Development only, no deployment\n")
        changelog.append("## Task Started\n")
        changelog.append(f"Claude CLI launched in background for Davy Jones improvements.\n")
        changelog.append(f"Output file: {output_file}\n")
        changelog.append(f"Repository: {repo_url}\n")
        changelog.append("\n### Potential Improvements:\n")
        changelog.append("- Add comprehensive tests\n")
        changelog.append("- Improve error handling\n")
        changelog.append("- Refactor for maintainability\n")
        changelog.append("- Better logging capabilities\n")
        changelog.append("- Optimize bot performance\n")
        
        self._save_changelog('davy_jones', changelog)
        
        self.logger.info("Davy Jones development completed (no production changes)")
    
    def _save_changelog(self, area: str, content: List[str]):
        """Save changelog for the work session"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        changelog_file = self.changelogs_dir / f"{area}_{timestamp}.md"
        
        with open(changelog_file, 'w') as f:
            f.writelines(content)
        
        self.logger.info(f"Changelog saved: {changelog_file}")
    
    def execute_work(self, area: Optional[str] = None):
        """
        Execute work for the selected or provided area.
        This is the main entry point for autonomous work execution.
        """
        if not area:
            area = self.select_work_area()
        
        self.logger.info(f"Starting work on: {self.WORK_AREAS[area]['name']}")
        
        # Track current work
        current_work = {
            'area': area,
            'started': datetime.now().isoformat(),
            'status': 'in_progress'
        }
        
        current_work_file = self.work_tracking_dir / 'current_work.json'
        with open(current_work_file, 'w') as f:
            json.dump(current_work, f, indent=2)
        
        try:
            # Execute work based on area
            if area == 'infrastructure':
                self.execute_infrastructure_improvements()
            elif area == 'personal_projects':
                self.execute_personal_project_development()
            elif area == 'davy_jones':
                self.execute_davy_jones_development()
            else:
                self.logger.error(f"Unknown work area: {area}")
                return
            
            # Update work tally
            self.work_tally[area] = self.work_tally.get(area, 0) + 1
            self._save_work_tally()
            
            # Update current work status
            current_work['status'] = 'completed'
            current_work['completed'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error executing work: {e}")
            current_work['status'] = 'failed'
            current_work['error'] = str(e)
        
        finally:
            # Save final work status
            with open(current_work_file, 'w') as f:
                json.dump(current_work, f, indent=2)
            
            self.logger.info("Work session completed")
            self.logger.info("=" * 60)
    
    def get_status(self) -> Dict:
        """Get current Barbossa status"""
        status = {
            'version': '1.0.0',
            'working_directory': str(self.work_dir),
            'work_tally': self.work_tally,
            'security_status': 'ACTIVE - ZKP2P access BLOCKED',
            'last_run': None,
            'current_work': None
        }
        
        # Get current work if exists
        current_work_file = self.work_tracking_dir / 'current_work.json'
        if current_work_file.exists():
            with open(current_work_file, 'r') as f:
                status['current_work'] = json.load(f)
        
        # Get last log file
        log_files = sorted(self.logs_dir.glob('*.log'))
        if log_files:
            status['last_run'] = log_files[-1].stem.split('_')[1]
        
        # Get security audit summary
        status['security_audit'] = security_guard.get_audit_summary()
        
        return status


def main():
    """Main entry point for Barbossa"""
    parser = argparse.ArgumentParser(
        description='Barbossa - Autonomous Software Engineer'
    )
    parser.add_argument(
        '--area',
        choices=['infrastructure', 'personal_projects', 'davy_jones'],
        help='Specific work area to focus on'
    )
    parser.add_argument(
        '--tally',
        type=str,
        help='JSON string of work tally (e.g., \'{"infrastructure": 2, "personal_projects": 1}\')'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show Barbossa status and exit'
    )
    parser.add_argument(
        '--test-security',
        action='store_true',
        help='Test security guards and exit'
    )
    
    args = parser.parse_args()
    
    # Initialize Barbossa
    barbossa = Barbossa()
    
    if args.status:
        # Show status and exit
        status = barbossa.get_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.test_security:
        # Test security system
        print("Testing Barbossa Security System...")
        print("=" * 60)
        
        test_repos = [
            "https://github.com/ADWilkinson/barbossa-engineer",  # Should pass
            "https://github.com/zkp2p/zkp2p-v2-contracts",  # Should fail
            "https://github.com/ADWilkinson/davy-jones-intern",  # Should pass
            "https://github.com/ZKP2P/something",  # Should fail
        ]
        
        for repo in test_repos:
            result = barbossa.validate_repository_access(repo)
            status = "✓ ALLOWED" if result else "✗ BLOCKED"
            print(f"{status}: {repo}")
        
        print("=" * 60)
        print("Security test complete")
        return
    
    # Parse work tally if provided
    work_tally = None
    if args.tally:
        try:
            work_tally = json.loads(args.tally)
        except json.JSONDecodeError:
            barbossa.logger.error(f"Invalid JSON for tally: {args.tally}")
            sys.exit(1)
    
    if work_tally:
        barbossa.work_tally.update(work_tally)
    
    # Execute work
    barbossa.execute_work(args.area)


if __name__ == "__main__":
    main()