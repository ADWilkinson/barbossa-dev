#!/usr/bin/env python3
"""
Barbossa Enhanced - Comprehensive Server Management & Autonomous Engineering System
Integrates server monitoring, project management, and autonomous development capabilities
"""

import argparse
import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import random
import shutil

# Import components
from security_guard import security_guard, SecurityViolationError
from server_manager import BarbossaServerManager

class BarbossaEnhanced:
    """
    Enhanced Barbossa system with integrated server management capabilities
    """
    
    VERSION = "2.0.0"
    
    WORK_AREAS = {
        'infrastructure': {
            'name': 'Server Infrastructure Management',
            'description': 'Comprehensive server monitoring, optimization, and maintenance',
            'weight': 2.0,
            'tasks': [
                'System performance optimization',
                'Docker container management',
                'Service health monitoring',
                'Security hardening',
                'Backup management',
                'Log rotation and cleanup',
                'Network optimization',
                'Resource usage analysis'
            ]
        },
        'personal_projects': {
            'name': 'Personal Project Development',
            'description': 'Feature development for ADWilkinson repositories',
            'repositories': [
                'ADWilkinson/_save',
                'ADWilkinson/chordcraft-app',
                'ADWilkinson/piggyonchain',
                'ADWilkinson/personal-website',
                'ADWilkinson/saylormemes',
                'ADWilkinson/the-flying-dutchman-theme'
            ],
            'weight': 1.5
        },
        'davy_jones': {
            'name': 'Davy Jones Intern Enhancement',
            'description': 'Bot improvements without affecting production',
            'repository': 'ADWilkinson/davy-jones-intern',
            'weight': 1.0
        },
        'barbossa_self': {
            'name': 'Barbossa Self-Improvement',
            'description': 'Enhance Barbossa capabilities and features',
            'weight': 1.5,
            'tasks': [
                'Add new monitoring metrics',
                'Improve dashboard UI/UX',
                'Enhance security features',
                'Add automation workflows',
                'Implement new API endpoints',
                'Optimize performance'
            ]
        }
    }
    
    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize Enhanced Barbossa with all subsystems"""
        self.work_dir = work_dir or Path.home() / 'barbossa-engineer'
        self.logs_dir = self.work_dir / 'logs'
        self.changelogs_dir = self.work_dir / 'changelogs'
        self.work_tracking_dir = self.work_dir / 'work_tracking'
        self.metrics_db = self.work_dir / 'metrics.db'
        
        # Ensure directories exist
        for dir_path in [self.logs_dir, self.changelogs_dir, self.work_tracking_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize server manager
        self.server_manager = None
        try:
            self.server_manager = BarbossaServerManager()
            self.server_manager.start_monitoring()
        except Exception as e:
            print(f"Warning: Could not initialize server manager: {e}")
        
        # Set up logging
        self._setup_logging()
        
        # Load work tally
        self.work_tally = self._load_work_tally()
        
        # System info
        self.system_info = self._get_system_info()
        
        self.logger.info("=" * 70)
        self.logger.info(f"BARBOSSA ENHANCED v{self.VERSION} - Comprehensive Server Management")
        self.logger.info(f"Working directory: {self.work_dir}")
        self.logger.info(f"Platform: {self.system_info['platform']}")
        self.logger.info(f"Server Manager: {'Active' if self.server_manager else 'Inactive'}")
        self.logger.info("Security: MAXIMUM - ZKP2P access BLOCKED")
        self.logger.info("=" * 70)
    
    def _setup_logging(self):
        """Configure comprehensive logging"""
        log_file = self.logs_dir / f"barbossa_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('barbossa_enhanced')
        self.logger.info(f"Logging to: {log_file}")
    
    def _get_system_info(self) -> Dict:
        """Gather comprehensive system information"""
        info = {
            'hostname': platform.node(),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': os.cpu_count(),
            'home_dir': str(Path.home()),
            'server_ip': '192.168.1.138'
        }
        
        # Get disk usage
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                info['disk_usage'] = {
                    'total': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'percent': parts[4]
                }
        except:
            pass
        
        return info
    
    def _load_work_tally(self) -> Dict[str, int]:
        """Load work tally from JSON file"""
        tally_file = self.work_tracking_dir / 'work_tally.json'
        if tally_file.exists():
            with open(tally_file, 'r') as f:
                tally = json.load(f)
                # Add new work areas if not present
                for area in self.WORK_AREAS.keys():
                    if area not in tally:
                        tally[area] = 0
                return tally
        return {area: 0 for area in self.WORK_AREAS.keys()}
    
    def _save_work_tally(self):
        """Save updated work tally"""
        tally_file = self.work_tracking_dir / 'work_tally.json'
        with open(tally_file, 'w') as f:
            json.dump(self.work_tally, f, indent=2)
        self.logger.info(f"Work tally saved: {self.work_tally}")
    
    def perform_system_health_check(self) -> Dict:
        """Perform comprehensive system health check"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'issues': [],
            'metrics': {}
        }
        
        if self.server_manager:
            # Get current metrics
            metrics = self.server_manager.metrics_collector.collect_metrics()
            health['metrics'] = metrics
            
            # Check for issues
            if metrics.get('cpu_percent', 0) > 90:
                health['issues'].append(f"High CPU usage: {metrics['cpu_percent']:.1f}%")
                health['status'] = 'warning'
            
            if metrics.get('memory_percent', 0) > 90:
                health['issues'].append(f"High memory usage: {metrics['memory_percent']:.1f}%")
                health['status'] = 'warning'
            
            if metrics.get('disk_percent', 0) > 85:
                health['issues'].append(f"Low disk space: {metrics['disk_percent']:.1f}% used")
                health['status'] = 'critical' if metrics['disk_percent'] > 95 else 'warning'
            
            # Check services
            self.server_manager.service_manager._update_services()
            critical_services = ['docker', 'cloudflared']
            for service in critical_services:
                if service in self.server_manager.service_manager.services:
                    if not self.server_manager.service_manager.services[service].get('active'):
                        health['issues'].append(f"Service {service} is down")
                        health['status'] = 'critical'
        
        return health
    
    def execute_infrastructure_management(self):
        """Execute advanced infrastructure management tasks"""
        self.logger.info("Executing infrastructure management...")
        
        # Perform health check first
        health = self.perform_system_health_check()
        self.logger.info(f"System health: {health['status']}")
        
        if health['issues']:
            self.logger.warning(f"Health issues detected: {health['issues']}")
        
        # Create enhanced prompt for Claude
        prompt = f"""You are Barbossa Enhanced, an advanced server management system.

CRITICAL SECURITY: Never access ZKP2P repositories. Only work with allowed repositories.

SYSTEM STATUS:
- Health: {health['status']}
- Issues: {', '.join(health['issues']) if health['issues'] else 'None'}
- CPU: {health['metrics'].get('cpu_percent', 0):.1f}%
- Memory: {health['metrics'].get('memory_percent', 0):.1f}%
- Disk: {health['metrics'].get('disk_percent', 0):.1f}%

Your task is to perform ONE comprehensive infrastructure management task:

1. If health issues exist, prioritize fixing them
2. Otherwise, choose from:
   - Optimize Docker containers (cleanup, resource limits)
   - Analyze and rotate large log files
   - Update system packages and security patches
   - Monitor and optimize network connections
   - Clean up old backups and archives
   - Review and enhance security configurations
   - Optimize database performance (if applicable)
   - Check and update SSL certificates

AVAILABLE TOOLS:
- Server Manager at ~/barbossa-engineer/server_manager.py
- Docker, systemctl, apt, ufw, netstat, ss
- Python scripts for automation
- Sudo password: Ableton6242

REQUIREMENTS:
- Execute REAL improvements
- Document all changes made
- Test changes before finalizing
- Create detailed changelog
- Consider system impact

System Info:
{json.dumps(self.system_info, indent=2)}

Complete the task and report results."""

        # Save and execute
        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        output_file = self.logs_dir / f"claude_infrastructure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        cmd = f"nohup claude --dangerously-skip-permissions < {prompt_file} > {output_file} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        
        self.logger.info(f"Infrastructure management launched. Output: {output_file}")
        
        # Create changelog
        self._create_changelog('infrastructure', {
            'health_status': health['status'],
            'issues_found': health['issues'],
            'prompt_file': str(prompt_file),
            'output_file': str(output_file)
        })
    
    def execute_barbossa_self_improvement(self):
        """Execute self-improvement tasks for Barbossa"""
        self.logger.info("Executing Barbossa self-improvement...")
        
        # Select improvement task
        tasks = self.WORK_AREAS['barbossa_self']['tasks']
        selected_task = random.choice(tasks)
        
        prompt = f"""You are improving the Barbossa Enhanced system itself.

TASK: {selected_task}

BARBOSSA COMPONENTS:
1. Main System: ~/barbossa-engineer/barbossa_enhanced.py
2. Server Manager: ~/barbossa-engineer/server_manager.py
3. Web Portal: ~/barbossa-engineer/web_portal/enhanced_app.py
4. Dashboard: ~/barbossa-engineer/web_portal/templates/enhanced_dashboard.html
5. Security Guard: ~/barbossa-engineer/security_guard.py

IMPROVEMENT AREAS:
- Add new monitoring capabilities
- Enhance dashboard visualizations
- Implement new API endpoints
- Optimize performance
- Add automation features
- Improve error handling
- Enhance security measures

REQUIREMENTS:
1. Analyze current implementation
2. Identify specific improvements for: {selected_task}
3. Implement enhancements
4. Test thoroughly
5. Document changes

IMPORTANT:
- Maintain backward compatibility
- Follow existing code patterns
- Add comprehensive error handling
- Create unit tests if applicable
- Update documentation

Complete the improvement and create a detailed report."""

        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        output_file = self.logs_dir / f"claude_self_improvement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        cmd = f"nohup claude --dangerously-skip-permissions < {prompt_file} > {output_file} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        
        self.logger.info(f"Self-improvement launched for: {selected_task}")
        
        self._create_changelog('barbossa_self', {
            'task': selected_task,
            'output_file': str(output_file)
        })
    
    def execute_personal_project_development(self):
        """Execute personal project development (inherited from original)"""
        self.logger.info("Executing personal project development...")
        
        repos = self.WORK_AREAS['personal_projects']['repositories']
        selected_repo = random.choice(repos)
        repo_url = f"https://github.com/{selected_repo}"
        
        # Validate repository access
        if not self.validate_repository_access(repo_url):
            self.logger.error("Repository access denied by security guard")
            return
        
        self.logger.info(f"Working on repository: {selected_repo}")
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        prompt = f"""You are Barbossa Enhanced, working on personal project improvements.

REPOSITORY: {selected_repo}
URL: {repo_url}

INSTRUCTIONS:
1. Clone repository to ~/barbossa-engineer/projects/ if not present, or navigate to existing clone
2. Fetch latest changes: git fetch origin
3. Checkout main/master branch: git checkout main (or master)
4. Pull latest changes: git pull origin main (or master)
5. Create new feature branch from updated main: git checkout -b feature/barbossa-improvement-{timestamp}
6. Analyze codebase comprehensively
7. Choose ONE significant improvement:
   - Add comprehensive test coverage
   - Implement new feature
   - Refactor for better architecture
   - Fix bugs and issues
   - Optimize performance
   - Update dependencies
   - Improve documentation

8. Implement the improvement completely
9. Run tests if available
10. Commit with clear message
11. Push feature branch to origin
12. Create detailed PR

REQUIREMENTS:
- Make meaningful improvements
- Follow project conventions
- Ensure tests pass
- Write clean code
- Create comprehensive PR description

Complete the task and create a PR."""

        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        output_file = self.logs_dir / f"claude_personal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        cmd = f"nohup claude --dangerously-skip-permissions < {prompt_file} > {output_file} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        
        self.logger.info(f"Personal project development launched for: {selected_repo}")
        
        self._create_changelog('personal_projects', {
            'repository': selected_repo,
            'output_file': str(output_file)
        })
    
    def execute_davy_jones_development(self):
        """Execute Davy Jones development (inherited from original)"""
        self.logger.info("Executing Davy Jones Intern development...")
        
        repo_url = "https://github.com/ADWilkinson/davy-jones-intern"
        
        if not self.validate_repository_access(repo_url):
            self.logger.error("Repository access denied")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        prompt = f"""You are Barbossa Enhanced, improving the Davy Jones Intern bot.

CRITICAL: Production bot is running. DO NOT affect it.

REPOSITORY: {repo_url}
WORK DIR: ~/barbossa-engineer/projects/davy-jones-intern

INSTRUCTIONS:
1. Navigate to ~/barbossa-engineer/projects/davy-jones-intern (clone if not present)
2. Fetch latest changes: git fetch origin
3. Checkout main branch: git checkout main
4. Pull latest changes: git pull origin main
5. Create new feature branch: git checkout -b feature/davy-jones-improvement-{timestamp}

IMPROVEMENT AREAS:
1. Add comprehensive test coverage
2. Enhance error handling
3. Improve Claude integration
4. Add new Slack commands
5. Optimize performance
6. Enhance logging
7. Improve GitHub integration

REQUIREMENTS:
- Work in feature branch only
- Do not touch production
- Run tests locally
- Create detailed PR
- Document all changes

Select and implement ONE improvement completely."""

        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        output_file = self.logs_dir / f"claude_davy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        cmd = f"nohup claude --dangerously-skip-permissions < {prompt_file} > {output_file} 2>&1 &"
        subprocess.Popen(cmd, shell=True, cwd=self.work_dir)
        
        self.logger.info("Davy Jones development launched")
        
        self._create_changelog('davy_jones', {
            'repository': repo_url,
            'output_file': str(output_file)
        })
    
    def validate_repository_access(self, repo_url: str) -> bool:
        """Validate repository access through security guard"""
        try:
            self.logger.info(f"Security check for: {repo_url}")
            security_guard.validate_operation('repository_access', repo_url)
            self.logger.info("✓ Security check PASSED")
            return True
        except SecurityViolationError as e:
            self.logger.error(f"✗ SECURITY VIOLATION: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Security check failed: {e}")
            return False
    
    def _create_changelog(self, area: str, details: Dict):
        """Create detailed changelog"""
        timestamp = datetime.now()
        changelog_file = self.changelogs_dir / f"{area}_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        
        content = [
            f"# {self.WORK_AREAS[area]['name']}\n",
            f"**Date**: {timestamp.isoformat()}\n",
            f"**Version**: Barbossa Enhanced v{self.VERSION}\n",
            f"\n## Details\n"
        ]
        
        for key, value in details.items():
            content.append(f"- **{key.replace('_', ' ').title()}**: {value}\n")
        
        content.append(f"\n## Status\n")
        content.append(f"Task initiated and running in background.\n")
        
        with open(changelog_file, 'w') as f:
            f.writelines(content)
        
        self.logger.info(f"Changelog created: {changelog_file}")
    
    def select_work_area(self) -> str:
        """Select work area with enhanced weighting"""
        # Calculate weights based on work history and current system state
        weights = {}
        
        for area, config in self.WORK_AREAS.items():
            base_weight = config['weight']
            work_count = self.work_tally.get(area, 0)
            
            # Inverse weight for balance
            adjusted_weight = base_weight * (1.0 / (work_count + 1))
            
            # Boost infrastructure if health issues exist
            if area == 'infrastructure' and self.server_manager:
                health = self.perform_system_health_check()
                if health['status'] != 'healthy':
                    adjusted_weight *= 2.0
            
            weights[area] = adjusted_weight
        
        # Normalize and select
        total_weight = sum(weights.values())
        probabilities = {k: v/total_weight for k, v in weights.items()}
        
        self.logger.info("Work area selection probabilities:")
        for area, prob in probabilities.items():
            self.logger.info(f"  {area}: {prob:.2%} (count: {self.work_tally.get(area, 0)})")
        
        selected = random.choices(
            list(probabilities.keys()),
            weights=list(probabilities.values()),
            k=1
        )[0]
        
        self.logger.info(f"SELECTED: {selected}")
        return selected
    
    def execute_work(self, area: Optional[str] = None):
        """Execute work for selected area"""
        if not area:
            area = self.select_work_area()
        
        self.logger.info(f"Executing: {self.WORK_AREAS[area]['name']}")
        
        # Track work
        current_work = {
            'area': area,
            'started': datetime.now().isoformat(),
            'status': 'in_progress'
        }
        
        current_work_file = self.work_tracking_dir / 'current_work.json'
        with open(current_work_file, 'w') as f:
            json.dump(current_work, f, indent=2)
        
        try:
            # Execute based on area
            if area == 'infrastructure':
                self.execute_infrastructure_management()
            elif area == 'personal_projects':
                self.execute_personal_project_development()
            elif area == 'davy_jones':
                self.execute_davy_jones_development()
            elif area == 'barbossa_self':
                self.execute_barbossa_self_improvement()
            else:
                self.logger.error(f"Unknown work area: {area}")
                return
            
            # Update tally
            self.work_tally[area] = self.work_tally.get(area, 0) + 1
            self._save_work_tally()
            
            current_work['status'] = 'completed'
            current_work['completed'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error executing work: {e}")
            current_work['status'] = 'failed'
            current_work['error'] = str(e)
        
        finally:
            with open(current_work_file, 'w') as f:
                json.dump(current_work, f, indent=2)
            
            self.logger.info("Work session completed")
            self.logger.info("=" * 70)
    
    def get_comprehensive_status(self) -> Dict:
        """Get comprehensive system and Barbossa status"""
        status = {
            'version': self.VERSION,
            'timestamp': datetime.now().isoformat(),
            'work_tally': self.work_tally,
            'system_info': self.system_info,
            'health': self.perform_system_health_check() if self.server_manager else None,
            'server_manager': 'active' if self.server_manager else 'inactive',
            'security': 'MAXIMUM - ZKP2P blocked'
        }
        
        # Add current work
        current_work_file = self.work_tracking_dir / 'current_work.json'
        if current_work_file.exists():
            with open(current_work_file, 'r') as f:
                status['current_work'] = json.load(f)
        
        # Add recent logs
        if self.logs_dir.exists():
            log_files = sorted(self.logs_dir.glob('*.log'), 
                             key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            status['recent_logs'] = [
                {
                    'name': f.name,
                    'size': f"{f.stat().st_size / 1024:.1f} KB",
                    'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                }
                for f in log_files
            ]
        
        return status
    
    def cleanup(self):
        """Cleanup resources on shutdown"""
        if self.server_manager:
            self.server_manager.stop_monitoring()
            self.logger.info("Server monitoring stopped")


def main():
    """Enhanced main entry point"""
    parser = argparse.ArgumentParser(
        description='Barbossa Enhanced - Comprehensive Server Management System'
    )
    parser.add_argument(
        '--area',
        choices=['infrastructure', 'personal_projects', 'davy_jones', 'barbossa_self'],
        help='Specific work area to focus on'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show comprehensive status and exit'
    )
    parser.add_argument(
        '--health',
        action='store_true',
        help='Perform health check and exit'
    )
    parser.add_argument(
        '--test-security',
        action='store_true',
        help='Test security system and exit'
    )
    parser.add_argument(
        '--start-portal',
        action='store_true',
        help='Start the enhanced web portal'
    )
    
    args = parser.parse_args()
    
    # Initialize Enhanced Barbossa
    barbossa = BarbossaEnhanced()
    
    try:
        if args.status:
            # Show comprehensive status
            status = barbossa.get_comprehensive_status()
            print(json.dumps(status, indent=2))
            
        elif args.health:
            # Perform health check
            health = barbossa.perform_system_health_check()
            print(json.dumps(health, indent=2))
            
        elif args.test_security:
            # Test security
            print("Testing Security System...")
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
            
        elif args.start_portal:
            # Start web portal
            print("Starting Enhanced Web Portal...")
            portal_script = barbossa.work_dir / 'start_enhanced_portal.sh'
            subprocess.run(['bash', str(portal_script)])
            
        else:
            # Execute work
            barbossa.execute_work(args.area)
    
    finally:
        barbossa.cleanup()


if __name__ == "__main__":
    main()