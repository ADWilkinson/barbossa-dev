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
import functools
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import random
import shutil
import psutil

# Import components
from security_guard import security_guard, SecurityViolationError
from server_manager import BarbossaServerManager
from ticket_enrichment import TicketEnrichmentEngine
from health_monitor import HealthMonitor
from cleanup_manager import CleanupManager

class PerformanceProfiler:
    """Performance profiling and monitoring for Barbossa operations"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self.lock = threading.Lock()
    
    def start_operation(self, operation_name: str):
        """Start timing an operation"""
        with self.lock:
            self.start_times[operation_name] = time.time()
    
    def end_operation(self, operation_name: str):
        """End timing an operation and store metrics"""
        with self.lock:
            if operation_name in self.start_times:
                duration = time.time() - self.start_times[operation_name]
                if operation_name not in self.metrics:
                    self.metrics[operation_name] = []
                self.metrics[operation_name].append({
                    'duration': duration,
                    'timestamp': datetime.now().isoformat(),
                    'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024
                })
                # Keep only last 100 measurements
                self.metrics[operation_name] = self.metrics[operation_name][-100:]
                del self.start_times[operation_name]
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        with self.lock:
            summary = {}
            for operation, measurements in self.metrics.items():
                if measurements:
                    durations = [m['duration'] for m in measurements]
                    summary[operation] = {
                        'count': len(measurements),
                        'avg_duration': sum(durations) / len(durations),
                        'max_duration': max(durations),
                        'min_duration': min(durations),
                        'last_run': measurements[-1]['timestamp']
                    }
            return summary

def performance_monitor(operation_name: str = None):
    """Decorator for performance monitoring"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'profiler'):
                op_name = operation_name or f"{func.__name__}"
                self.profiler.start_operation(op_name)
                try:
                    result = func(self, *args, **kwargs)
                    return result
                finally:
                    self.profiler.end_operation(op_name)
            else:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator

class BarbossaEnhanced:
    """
    Enhanced Barbossa system with integrated server management capabilities
    """
    
    VERSION = "2.2.0"
    
    WORK_AREAS = {
        'infrastructure': {
            'name': 'Server Infrastructure Management',
            'description': 'Comprehensive server monitoring, optimization, and maintenance',
            'weight': 0.1,  # MINIMAL - Only for critical issues
            'tasks': [
                'Critical security patches only',
                'Emergency system fixes',
                'Critical service failures'
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
            'weight': 7.0  # HIGH - 70% weight (multiple projects)
        },
        'davy_jones': {
            'name': 'Davy Jones Intern Enhancement',
            'description': 'Bot improvements without affecting production',
            'repository': 'ADWilkinson/davy-jones-intern',
            'weight': 3.0  # MODERATE - 30% weight (single project)
        },
        'barbossa_self': {
            'name': 'Barbossa Self-Improvement',
            'description': 'Enhance Barbossa capabilities and features',
            'weight': 0.2,  # LOW - Minimal priority
            'tasks': [
                'Critical bug fixes only',
                'Essential feature updates'
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
        
        # Initialize performance profiler
        self.profiler = PerformanceProfiler()
        
        # Initialize caching system for expensive operations
        self._cache = {}
        self._cache_expiry = {}
        self._cache_lock = threading.Lock()
        
        # Initialize optimized thread pool executor
        cpu_count = os.cpu_count() or 2
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=min(cpu_count, 4), 
            thread_name_prefix="BarbossaAsync"
        )
        
        # Ensure directories exist
        for dir_path in [self.logs_dir, self.changelogs_dir, self.work_tracking_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Set up logging early for other components
        self._setup_logging()
        
        # Initialize server manager
        self.server_manager = None
        try:
            self.server_manager = BarbossaServerManager()
            self.server_manager.start_monitoring()
        except Exception as e:
            print(f"Warning: Could not initialize server manager: {e}")
        
        # Initialize ticket enrichment engine
        self.ticket_engine = None
        try:
            self.ticket_engine = TicketEnrichmentEngine(self.work_dir)
        except Exception as e:
            print(f"Warning: Could not initialize ticket enrichment: {e}")
        
        # Initialize health monitor
        self.health_monitor = None
        try:
            self.health_monitor = HealthMonitor(self.work_dir)
            self.logger.info("Health monitor initialized successfully")
        except Exception as e:
            print(f"Warning: Could not initialize health monitor: {e}")
        
        # Initialize cleanup manager
        self.cleanup_manager = None
        try:
            self.cleanup_manager = CleanupManager(self.work_dir)
            # Schedule automatic cleanup every 24 hours
            self.cleanup_manager.schedule_cleanup(interval_hours=24)
            self.logger.info("Cleanup manager initialized with 24-hour schedule")
        except Exception as e:
            print(f"Warning: Could not initialize cleanup manager: {e}")
        
        # Load work tally
        self.work_tally = self._load_work_tally()
        
        # System info
        self.system_info = self._get_system_info()
        
        # Initialize API client for new portal features
        self.portal_api_base = "https://localhost:8443"
        self.api_available = self._check_api_availability()
        
        self.logger.info("=" * 70)
        self.logger.info(f"BARBOSSA ENHANCED v{self.VERSION} - Comprehensive Server Management")
        self.logger.info(f"Working directory: {self.work_dir}")
        self.logger.info(f"Platform: {self.system_info['platform']}")
        self.logger.info(f"Server Manager: {'Active' if self.server_manager else 'Inactive'}")
        self.logger.info(f"Portal APIs: {'Available' if self.api_available else 'Not Available'}")
        self.logger.info("Security: MAXIMUM - ZKP2P access BLOCKED")
        self.logger.info("=" * 70)
    
    def _check_api_availability(self):
        """Check if the new portal APIs are available"""
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Test if advanced API v3 is available
            response = requests.get(f"{self.portal_api_base}/api/v3/health", 
                                   verify=False, timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        return False
    
    def get_performance_score(self):
        """Get system performance score from the new API"""
        if not self.api_available:
            return None
        
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.get(f"{self.portal_api_base}/api/v3/analytics/performance-score",
                                   verify=False, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.warning(f"Could not get performance score: {e}")
        return None
    
    def create_backup(self, backup_type="config"):
        """Create a backup using the new API"""
        if not self.api_available:
            return None
        
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.post(f"{self.portal_api_base}/api/v3/backup/create",
                                    json={"backup_type": backup_type, "compress": True},
                                    verify=False, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.warning(f"Could not create backup: {e}")
        return None
    
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
    
    def _get_cached(self, key: str, ttl: int = 300) -> Optional[Any]:
        """Get cached value if not expired"""
        with self._cache_lock:
            if key in self._cache and key in self._cache_expiry:
                if time.time() < self._cache_expiry[key]:
                    return self._cache[key]
                else:
                    # Clean expired cache
                    del self._cache[key]
                    del self._cache_expiry[key]
            return None
    
    def _set_cache(self, key: str, value: Any, ttl: int = 300):
        """Set cached value with TTL"""
        with self._cache_lock:
            self._cache[key] = value
            self._cache_expiry[key] = time.time() + ttl
            # Cleanup old entries periodically
            if len(self._cache) > 100:
                self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, expiry_time in self._cache_expiry.items()
            if current_time >= expiry_time
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_expiry.pop(key, None)
    
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
    
    @performance_monitor("system_health_check")
    def perform_system_health_check(self) -> Dict:
        """Perform comprehensive system health check with caching"""
        # Check cache first
        cache_key = 'system_health'
        cached_health = self._get_cached(cache_key, ttl=30)  # Cache for 30 seconds
        if cached_health:
            return cached_health
        
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
        
        # Cache the result
        self._set_cache(cache_key, health, ttl=30)
        
        return health
    
    @performance_monitor("infrastructure_management")
    def execute_infrastructure_management(self):
        """Execute advanced infrastructure management tasks"""
        self.logger.info("Executing infrastructure management...")
        
        # Use new API features if available
        if self.api_available:
            perf_score = self.get_performance_score()
            if perf_score:
                self.logger.info(f"API Performance Score: {perf_score['overall_score']}/100 - {perf_score['overall_status']}")
                
                # Log recommendations if any
                if perf_score.get('recommendations'):
                    for rec in perf_score['recommendations']:
                        self.logger.info(f"  Recommendation: {rec}")
                
                # Auto-backup on good health
                if perf_score['overall_score'] > 85 and datetime.now().hour == 3:  # 3 AM backups
                    self.logger.info("Creating automated backup...")
                    backup = self.create_backup("config")
                    if backup and backup.get('success'):
                        self.logger.info(f"Backup created: {backup['backup']['name']}")
        
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
        
        cmd = f"nohup claude --dangerously-skip-permissions --model sonnet < {prompt_file} > {output_file} 2>&1 &"
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
- Add new monitoring capabilities (Now available via Portal APIs!)
- Enhance dashboard visualizations
- Implement new API endpoints (Advanced API v3 now available!)
- Optimize performance (Performance scoring now available!)
- Add automation features (Workflow automation now available!)
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
        
        cmd = f"nohup claude --dangerously-skip-permissions --model sonnet < {prompt_file} > {output_file} 2>&1 &"
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
7. Choose ONE significant improvement (PRIORITIZE IN THIS ORDER):
   - Implement new feature (HIGHEST PRIORITY)
   - Refactor for better architecture and code quality
   - Optimize performance and efficiency
   - Fix critical bugs and issues
   - Update critical dependencies
   - Improve inline code documentation (minimal)
   - Add tests ONLY if absolutely necessary (LOWEST PRIORITY)

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
        
        cmd = f"nohup claude --dangerously-skip-permissions --model sonnet < {prompt_file} > {output_file} 2>&1 &"
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
        
        cmd = f"nohup claude --dangerously-skip-permissions --model sonnet < {prompt_file} > {output_file} 2>&1 &"
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
        """Intelligently select work area using multi-factor scoring with performance metrics"""
        # Get recent work history and performance data
        recent_history = self._analyze_recent_work_history()
        performance_data = self.profiler.get_performance_summary() if hasattr(self, 'profiler') else {}
        
        weights = {}
        area_analysis = {}
        
        for area, config in self.WORK_AREAS.items():
            # Initialize scoring factors
            factors = {
                'base_priority': config['weight'],
                'work_balance': 1.0,
                'time_factor': 1.0,
                'success_rate': 1.0,
                'performance': 1.0,
                'system_needs': 1.0
            }
            
            # 1. Work balance factor (inverse of work count)
            work_count = self.work_tally.get(area, 0)
            factors['work_balance'] = 1.0 / (work_count + 1) ** 1.5
            
            # 2. Time since last work factor
            if area in recent_history:
                hours_since = recent_history[area].get('hours_since_last', 48)
                factors['time_factor'] = min(hours_since / 24, 3.0)  # Cap at 3x for 72+ hours
                factors['success_rate'] = recent_history[area].get('success_rate', 1.0)
            
            # 3. Performance factor (from profiler metrics)
            area_perf_key = f"work_{area}"
            if area_perf_key in performance_data:
                avg_duration = performance_data[area_perf_key].get('avg_duration', 60)
                # Faster completion = higher score (inverse relationship)
                factors['performance'] = min(60 / max(avg_duration, 1), 2.0)
            
            # 4. System needs factor (special conditions)
            if area == 'infrastructure':
                # Check system health for infrastructure priority
                if self.server_manager:
                    health = self.perform_system_health_check()
                    if health['status'] != 'healthy':
                        factors['system_needs'] = 3.0  # Triple priority for unhealthy system
                    elif any(m['status'] != 'healthy' for m in health.get('monitors', [])):
                        factors['system_needs'] = 2.0  # Double priority for partial issues
                
                # Skip during business hours unless critical
                if self._is_business_hours() and factors['system_needs'] < 2.0:
                    factors['system_needs'] = 0.1  # Heavily reduce non-critical infrastructure work
            
            elif area == 'barbossa_self':
                # Boost self-improvement if errors detected in recent runs
                if recent_history.get('barbossa_self', {}).get('error_rate', 0) > 0.2:
                    factors['system_needs'] = 2.0
            
            # Calculate composite score with weighted factors
            composite_score = (
                factors['base_priority'] * 0.35 +  # Base configuration weight
                factors['work_balance'] * 0.25 +   # Balance across areas
                factors['time_factor'] * 0.15 +    # Time since last work
                factors['success_rate'] * 0.10 +   # Historical success
                factors['performance'] * 0.05 +    # Performance efficiency
                factors['system_needs'] * 0.10     # System requirements
            ) * factors['base_priority']  # Apply base multiplier
            
            weights[area] = max(composite_score, 0.01)  # Ensure minimum weight
            area_analysis[area] = {
                'composite_score': composite_score,
                'factors': factors,
                'work_count': work_count
            }
        
        # Normalize weights and calculate probabilities
        total_weight = sum(weights.values())
        probabilities = {k: v/total_weight for k, v in weights.items()}
        
        # Log detailed analysis
        self.logger.info("=" * 70)
        self.logger.info("INTELLIGENT WORK AREA SELECTION ANALYSIS")
        self.logger.info("=" * 70)
        
        for area, prob in sorted(probabilities.items(), key=lambda x: x[1], reverse=True):
            analysis = area_analysis[area]
            self.logger.info(f"\n{area.upper()}:")
            self.logger.info(f"  Selection Probability: {prob:.1%}")
            self.logger.info(f"  Work Count: {analysis['work_count']}")
            self.logger.info(f"  Composite Score: {analysis['composite_score']:.3f}")
            self.logger.info("  Factors:")
            for factor_name, value in analysis['factors'].items():
                self.logger.info(f"    - {factor_name}: {value:.2f}")
        
        # Select area based on probabilities
        selected = random.choices(
            list(probabilities.keys()),
            weights=list(probabilities.values()),
            k=1
        )[0]
        
        self.logger.info("\n" + "=" * 70)
        self.logger.info(f"SELECTED WORK AREA: {selected.upper()}")
        self.logger.info("=" * 70)
        
        return selected
    
    def _analyze_recent_work_history(self) -> Dict:
        """Analyze recent work history for performance metrics"""
        history = {}
        
        try:
            # Check recent changelogs
            changelogs = sorted(self.changelogs_dir.glob("*.md"), 
                              key=lambda x: x.stat().st_mtime, reverse=True)[:20]
            
            now = datetime.now()
            
            for changelog in changelogs:
                content = changelog.read_text().lower()
                file_time = datetime.fromtimestamp(changelog.stat().st_mtime)
                
                # Extract work area from content
                for area in self.WORK_AREAS.keys():
                    if area in content:
                        if area not in history:
                            history[area] = {
                                'count': 0,
                                'success': 0,
                                'errors': 0,
                                'last_work': file_time
                            }
                        
                        history[area]['count'] += 1
                        
                        # Analyze success/failure
                        success_indicators = ['completed', 'success', 'fixed', 'implemented', 'enhanced']
                        error_indicators = ['error', 'failed', 'exception', 'issue', 'problem']
                        
                        if any(ind in content for ind in success_indicators):
                            history[area]['success'] += 1
                        if any(ind in content for ind in error_indicators):
                            history[area]['errors'] += 1
                        
                        # Update last work time
                        if file_time > history[area]['last_work']:
                            history[area]['last_work'] = file_time
            
            # Calculate metrics
            for area, data in history.items():
                if data['count'] > 0:
                    data['success_rate'] = data['success'] / data['count']
                    data['error_rate'] = data['errors'] / data['count']
                    data['hours_since_last'] = (now - data['last_work']).total_seconds() / 3600
                else:
                    data['success_rate'] = 1.0
                    data['error_rate'] = 0.0
                    data['hours_since_last'] = 168  # Default to 1 week
                    
        except Exception as e:
            self.logger.warning(f"Could not analyze work history: {e}")
        
        return history
    
    def _is_business_hours(self) -> bool:
        """Check if current time is during business hours (9 AM - 6 PM weekdays)"""
        now = datetime.now()
        # Business hours: Monday-Friday, 9 AM - 6 PM
        is_weekday = now.weekday() < 5  # Monday = 0, Sunday = 6
        is_business_time = 9 <= now.hour < 18
        return is_weekday and is_business_time
    
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
    
    @performance_monitor("comprehensive_status")
    def run_comprehensive_diagnostics(self):
        """Run comprehensive system diagnostics and generate report"""
        print("=" * 80)
        print("BARBOSSA COMPREHENSIVE SYSTEM DIAGNOSTICS")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Version: {self.VERSION}")
        print("")
        
        diagnostics_results = {
            'timestamp': datetime.now().isoformat(),
            'version': self.VERSION,
            'checks': {}
        }
        
        # 1. System Information
        print("1. SYSTEM INFORMATION")
        print("-" * 40)
        for key, value in self.system_info.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")
        print("")
        
        # 2. Health Check
        print("2. HEALTH CHECK")
        print("-" * 40)
        if self.health_monitor:
            health_summary = self.health_monitor.get_health_summary()
            print(health_summary)
            diagnostics_results['checks']['health'] = self.health_monitor.perform_full_health_check()
        else:
            print("  Health monitor not available")
        print("")
        
        # 3. Performance Metrics
        print("3. PERFORMANCE METRICS")
        print("-" * 40)
        perf_summary = self.profiler.get_performance_summary()
        if perf_summary:
            for operation, metrics in perf_summary.items():
                print(f"  {operation}:")
                print(f"    Runs: {metrics['count']}")
                print(f"    Avg Duration: {metrics['avg_duration']:.2f}s")
                print(f"    Last Run: {metrics['last_run']}")
        else:
            print("  No performance data available yet")
        diagnostics_results['checks']['performance'] = perf_summary
        print("")
        
        # 4. Work Area Analysis
        print("4. WORK AREA ANALYSIS")
        print("-" * 40)
        print("  Current Work Tally:")
        for area, count in self.work_tally.items():
            print(f"    {area}: {count} sessions")
        
        recent_history = self._analyze_recent_work_history()
        if recent_history:
            print("\n  Recent Work History:")
            for area, data in recent_history.items():
                print(f"    {area}:")
                print(f"      Success Rate: {data.get('success_rate', 0):.1%}")
                print(f"      Hours Since Last: {data.get('hours_since_last', 0):.1f}")
        diagnostics_results['checks']['work_areas'] = {
            'tally': self.work_tally,
            'history': recent_history
        }
        print("")
        
        # 5. Security Status
        print("5. SECURITY STATUS")
        print("-" * 40)
        try:
            # Test security with safe repository
            test_url = "https://github.com/ADWilkinson/barbossa-engineer"
            is_valid, _ = security_guard.validate_repository_url(test_url)
            print(f"  Security Guard: {'Active' if is_valid else 'Error'}")
            
            # Check violations log
            violations_log = self.work_dir / 'security' / 'security_violations.log'
            if violations_log.exists():
                violation_count = sum(1 for line in open(violations_log) if 'VIOLATION' in line)
                print(f"  Total Violations: {violation_count}")
            else:
                print("  Total Violations: 0")
                
            print("  Repository Access: ADWilkinson only (ZKP2P BLOCKED)")
            diagnostics_results['checks']['security'] = {'status': 'active', 'violations': violation_count if violations_log.exists() else 0}
        except Exception as e:
            print(f"  Security check error: {e}")
            diagnostics_results['checks']['security'] = {'status': 'error', 'error': str(e)}
        print("")
        
        # 6. Service Status
        print("6. SERVICE STATUS")
        print("-" * 40)
        services = {
            'Server Manager': self.server_manager is not None,
            'Ticket Engine': self.ticket_engine is not None,
            'Health Monitor': self.health_monitor is not None,
            'Portal API': self.api_available
        }
        for service, status in services.items():
            status_str = "Active" if status else "Inactive"
            print(f"  {service}: {status_str}")
        diagnostics_results['checks']['services'] = services
        print("")
        
        # 7. Storage Analysis
        print("7. STORAGE ANALYSIS")
        print("-" * 40)
        storage_dirs = {
            'Logs': self.logs_dir,
            'Changelogs': self.changelogs_dir,
            'Work Tracking': self.work_tracking_dir,
            'Backups': self.work_dir / 'backups',
            'Metrics': self.work_dir / 'metrics'
        }
        
        for name, path in storage_dirs.items():
            if path.exists():
                if path.is_dir():
                    file_count = len(list(path.glob('*')))
                    size_mb = sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) / (1024 * 1024)
                    print(f"  {name}:")
                    print(f"    Files: {file_count}")
                    print(f"    Size: {size_mb:.1f} MB")
                else:
                    size_mb = path.stat().st_size / (1024 * 1024)
                    print(f"  {name}: {size_mb:.1f} MB")
            else:
                print(f"  {name}: Not found")
        print("")
        
        # 8. Recent Errors
        print("8. RECENT ERRORS")
        print("-" * 40)
        error_count = 0
        recent_logs = sorted(self.logs_dir.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
        for log_file in recent_logs:
            try:
                with open(log_file, 'r') as f:
                    errors = [line for line in f if 'ERROR' in line or 'CRITICAL' in line]
                    if errors:
                        print(f"  {log_file.name}: {len(errors)} errors")
                        error_count += len(errors)
                        # Show last error
                        if errors:
                            last_error = errors[-1].strip()
                            if len(last_error) > 100:
                                last_error = last_error[:100] + "..."
                            print(f"    Last: {last_error}")
            except:
                pass
        
        if error_count == 0:
            print("  No recent errors found")
        diagnostics_results['checks']['errors'] = error_count
        print("")
        
        # Save diagnostics report
        report_file = self.work_dir / 'diagnostics' / f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(diagnostics_results, f, indent=2)
        
        print("=" * 80)
        print(f"Diagnostics complete. Report saved to: {report_file}")
        print("=" * 80)
    
    def get_comprehensive_status(self) -> Dict:
        """Get comprehensive system and Barbossa status with optimized caching"""
        # Check cache for non-critical status components
        cache_key = 'comprehensive_status'
        cached_status = self._get_cached(cache_key, ttl=15)  # Cache for 15 seconds
        
        if cached_status:
            # Update only timestamp and dynamic data
            cached_status['timestamp'] = datetime.now().isoformat()
            cached_status['performance'] = self.profiler.get_performance_summary()
            return cached_status
        
        status = {
            'version': self.VERSION,
            'timestamp': datetime.now().isoformat(),
            'work_tally': self.work_tally,
            'system_info': self.system_info,
            'health': self.perform_system_health_check() if self.server_manager else None,
            'server_manager': 'active' if self.server_manager else 'inactive',
            'security': 'MAXIMUM - ZKP2P blocked',
            'performance': self.profiler.get_performance_summary()
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
        
        # Cache the status
        self._set_cache(cache_key, status, ttl=15)
        
        return status
    
    def cleanup(self):
        """Cleanup resources on shutdown"""
        if self.server_manager:
            self.server_manager.stop_monitoring()
            self.logger.info("Server monitoring stopped")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        self.logger.info("Thread pool executor shutdown")
        
        # Clear cache
        with self._cache_lock:
            cache_size = len(self._cache)
            self._cache.clear()
            self._cache_expiry.clear()
            if cache_size > 0:
                self.logger.info(f"Cleared {cache_size} cached entries")
        
        # Log final performance summary
        performance_summary = self.profiler.get_performance_summary()
        if performance_summary:
            self.logger.info("Performance Summary:")
            for operation, stats in performance_summary.items():
                self.logger.info(f"  {operation}: avg={stats['avg_duration']:.3f}s, max={stats['max_duration']:.3f}s, count={stats['count']}")


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
        '--diagnostics',
        action='store_true',
        help='Run comprehensive system diagnostics'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Run storage cleanup to free disk space'
    )
    parser.add_argument(
        '--cleanup-dry-run',
        action='store_true',
        help='Simulate cleanup without deleting files'
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
            # Perform comprehensive health check
            if barbossa.health_monitor:
                print(barbossa.health_monitor.get_health_summary())
            else:
                # Fallback to basic health check
                health = barbossa.perform_system_health_check()
                print(json.dumps(health, indent=2))
        
        elif args.diagnostics:
            # Run comprehensive system diagnostics
            barbossa.run_comprehensive_diagnostics()
        
        elif args.cleanup or args.cleanup_dry_run:
            # Run storage cleanup
            if barbossa.cleanup_manager:
                dry_run = args.cleanup_dry_run
                print(f"Running storage cleanup {'(DRY RUN)' if dry_run else ''}...")
                results = barbossa.cleanup_manager.perform_cleanup(dry_run=dry_run)
                print("\n" + results['summary'])
                
                # Show storage report
                print("\nCurrent Storage Report:")
                report = barbossa.cleanup_manager.get_storage_report()
                for name, info in report['directories'].items():
                    print(f"  {name}: {info['size_mb']:.1f} MB ({info['file_count']} files)")
                print(f"\nTotal: {report['total_size_mb']:.1f} MB")
                
                if report['recommendations']:
                    print("\nRecommendations:")
                    for rec in report['recommendations']:
                        print(f"  - {rec}")
            else:
                print("Cleanup manager not available")
            
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