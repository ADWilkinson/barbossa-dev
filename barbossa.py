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
                'ADWilkinson/persona-website',
                'ADWilkinson/saylor-memes',
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
        """Execute server infrastructure improvement tasks"""
        self.logger.info("Executing infrastructure improvements...")
        
        changelog = []
        changelog.append(f"# Infrastructure Improvements - {datetime.now().isoformat()}\n")
        
        tasks = [
            "Check and update system packages",
            "Review security configurations",
            "Optimize Docker containers",
            "Clean up log files",
            "Update Barbossa dependencies"
        ]
        
        selected_task = random.choice(tasks)
        self.logger.info(f"Selected task: {selected_task}")
        changelog.append(f"## Task: {selected_task}\n")
        
        # Simulate task execution (in production, this would run actual commands)
        if selected_task == "Check and update system packages":
            # Check for updates (read-only)
            result = subprocess.run(
                ["apt", "list", "--upgradable"],
                capture_output=True,
                text=True
            )
            changelog.append(f"### Package check results:\n```\n{result.stdout[:500]}\n```\n")
        
        elif selected_task == "Clean up log files":
            # Find large log files
            result = subprocess.run(
                ["find", str(Path.home()), "-name", "*.log", "-size", "+10M", "-type", "f"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                changelog.append(f"### Large log files found:\n```\n{result.stdout[:500]}\n```\n")
            else:
                changelog.append("### No large log files found\n")
        
        # Save changelog
        self._save_changelog('infrastructure', changelog)
        self.logger.info("Infrastructure improvements completed")
    
    def execute_personal_project_development(self):
        """Execute personal project feature development"""
        self.logger.info("Executing personal project development...")
        
        # Select a repository
        repos = self.WORK_AREAS['personal_projects']['repositories']
        selected_repo = random.choice(repos)
        
        repo_url = f"https://github.com/{selected_repo}"
        
        # CRITICAL: Validate repository access
        if not self.validate_repository_access(repo_url):
            self.logger.error("Repository access denied by security guard")
            return
        
        changelog = []
        changelog.append(f"# Personal Project Development - {datetime.now().isoformat()}\n")
        changelog.append(f"## Repository: {selected_repo}\n")
        
        # Clone or update repository
        repo_name = selected_repo.split('/')[-1]
        repo_path = self.work_dir / 'projects' / repo_name
        
        if repo_path.exists():
            self.logger.info(f"Updating existing repository: {repo_path}")
            # Pull latest changes
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            changelog.append(f"### Repository updated\n```\n{result.stdout}\n```\n")
        else:
            self.logger.info(f"Cloning repository: {repo_url}")
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "clone", repo_url, str(repo_path)],
                capture_output=True,
                text=True
            )
            changelog.append(f"### Repository cloned\n```\n{result.stdout}\n```\n")
        
        # Analyze repository for improvements
        changelog.append("### Analysis Tasks:\n")
        changelog.append("- [ ] Check for outdated dependencies\n")
        changelog.append("- [ ] Review code structure\n")
        changelog.append("- [ ] Identify refactoring opportunities\n")
        changelog.append("- [ ] Look for missing tests\n")
        changelog.append("- [ ] Check documentation completeness\n")
        
        # Save changelog
        self._save_changelog('personal_projects', changelog)
        self.logger.info("Personal project development completed")
    
    def execute_davy_jones_development(self):
        """Execute Davy Jones Intern development (without affecting production)"""
        self.logger.info("Executing Davy Jones Intern development...")
        self.logger.warning("REMINDER: Do not redeploy or affect production instance!")
        
        repo_url = "https://github.com/ADWilkinson/davy-jones-intern"
        
        # CRITICAL: Validate repository access
        if not self.validate_repository_access(repo_url):
            self.logger.error("Repository access denied by security guard")
            return
        
        changelog = []
        changelog.append(f"# Davy Jones Intern Development - {datetime.now().isoformat()}\n")
        changelog.append("## ⚠️ PRODUCTION SAFETY: No deployment, only feature development\n")
        
        # Work with repository
        repo_path = self.work_dir / 'projects' / 'davy-jones-intern'
        
        if repo_path.exists():
            # Update repository
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            changelog.append(f"### Repository updated\n```\n{result.stdout}\n```\n")
        else:
            # Clone repository
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "clone", repo_url, str(repo_path)],
                capture_output=True,
                text=True
            )
            changelog.append(f"### Repository cloned\n```\n{result.stdout}\n```\n")
        
        # Development tasks (safe, non-production affecting)
        changelog.append("### Development Tasks:\n")
        changelog.append("- [ ] Review code for optimization opportunities\n")
        changelog.append("- [ ] Add unit tests for uncovered functions\n")
        changelog.append("- [ ] Improve error handling\n")
        changelog.append("- [ ] Enhance logging capabilities\n")
        changelog.append("- [ ] Document new features\n")
        changelog.append("- [ ] Create feature branch for improvements\n")
        
        # Save changelog
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