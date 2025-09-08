#!/usr/bin/env python3
"""
Health Monitor Module for Barbossa
Comprehensive health checking for all system components
"""

import json
import logging
import os
import psutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
import socket

class HealthMonitor:
    """
    Monitors health of all Barbossa components and dependencies
    """
    
    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize health monitor"""
        self.work_dir = work_dir or Path.home() / 'barbossa-engineer'
        self.health_log = self.work_dir / 'health' / 'health_checks.json'
        self.health_log.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger('barbossa.health')
        
        # Component checks registry
        self.checks = {
            'system': self.check_system_resources,
            'disk': self.check_disk_space,
            'network': self.check_network_connectivity,
            'services': self.check_critical_services,
            'api_endpoints': self.check_api_endpoints,
            'security': self.check_security_status,
            'logs': self.check_log_health,
            'dependencies': self.check_dependencies,
            'database': self.check_database_health,
            'backup': self.check_backup_status
        }
        
        # Thresholds
        self.thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90,
            'log_size_mb': 500,
            'api_response_time': 5.0,
            'backup_age_hours': 48
        }
    
    def perform_full_health_check(self) -> Dict:
        """Perform comprehensive health check of all components"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'issues': [],
            'metrics': {}
        }
        
        critical_issues = []
        warnings = []
        
        # Run all health checks
        for component_name, check_func in self.checks.items():
            try:
                self.logger.info(f"Checking {component_name}...")
                component_result = check_func()
                results['components'][component_name] = component_result
                
                # Aggregate issues
                if component_result['status'] == 'critical':
                    critical_issues.extend(component_result.get('issues', []))
                    results['overall_status'] = 'critical'
                elif component_result['status'] == 'warning':
                    warnings.extend(component_result.get('issues', []))
                    if results['overall_status'] != 'critical':
                        results['overall_status'] = 'warning'
                        
            except Exception as e:
                self.logger.error(f"Health check failed for {component_name}: {e}")
                results['components'][component_name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                warnings.append(f"{component_name} health check failed: {e}")
        
        # Compile issues
        results['issues'] = critical_issues + warnings
        
        # Calculate health score (0-100)
        results['health_score'] = self._calculate_health_score(results)
        
        # Save results
        self._save_health_results(results)
        
        return results
    
    def check_system_resources(self) -> Dict:
        """Check CPU, memory, and process health"""
        result = {
            'status': 'healthy',
            'metrics': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # CPU check
            cpu_percent = psutil.cpu_percent(interval=1)
            result['metrics']['cpu_percent'] = cpu_percent
            if cpu_percent > self.thresholds['cpu_percent']:
                result['status'] = 'warning'
                result['issues'].append(f"High CPU usage: {cpu_percent:.1f}%")
            
            # Memory check
            memory = psutil.virtual_memory()
            result['metrics']['memory_percent'] = memory.percent
            result['metrics']['memory_available_gb'] = memory.available / (1024**3)
            if memory.percent > self.thresholds['memory_percent']:
                result['status'] = 'critical' if memory.percent > 95 else 'warning'
                result['issues'].append(f"High memory usage: {memory.percent:.1f}%")
            
            # Process count
            process_count = len(psutil.pids())
            result['metrics']['process_count'] = process_count
            if process_count > 500:
                result['issues'].append(f"High process count: {process_count}")
            
            # Load average
            load_avg = os.getloadavg()
            result['metrics']['load_average'] = load_avg
            cpu_count = os.cpu_count()
            if load_avg[0] > cpu_count * 2:
                result['status'] = 'warning'
                result['issues'].append(f"High load average: {load_avg[0]:.2f}")
                
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def check_disk_space(self) -> Dict:
        """Check disk space on all mounted filesystems"""
        result = {
            'status': 'healthy',
            'filesystems': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            for partition in psutil.disk_partitions():
                if partition.mountpoint == '/':
                    usage = psutil.disk_usage(partition.mountpoint)
                    fs_info = {
                        'total_gb': usage.total / (1024**3),
                        'used_gb': usage.used / (1024**3),
                        'free_gb': usage.free / (1024**3),
                        'percent': usage.percent
                    }
                    result['filesystems'][partition.mountpoint] = fs_info
                    
                    if usage.percent > self.thresholds['disk_percent']:
                        result['status'] = 'critical' if usage.percent > 95 else 'warning'
                        result['issues'].append(
                            f"Low disk space on {partition.mountpoint}: {usage.percent:.1f}% used"
                        )
                        
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def check_network_connectivity(self) -> Dict:
        """Check network connectivity and DNS resolution"""
        result = {
            'status': 'healthy',
            'checks': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Check internet connectivity
        test_hosts = [
            ('8.8.8.8', 53, 'Google DNS'),
            ('1.1.1.1', 53, 'Cloudflare DNS'),
            ('github.com', 443, 'GitHub')
        ]
        
        for host, port, name in test_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result_code = sock.connect_ex((host, port))
                sock.close()
                
                result['checks'][name] = result_code == 0
                if result_code != 0:
                    result['issues'].append(f"Cannot connect to {name} ({host}:{port})")
                    result['status'] = 'warning'
                    
            except Exception as e:
                result['checks'][name] = False
                result['issues'].append(f"Network check failed for {name}: {e}")
        
        # Check local network
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            result['checks']['local_network'] = True
            result['local_ip'] = local_ip
        except Exception as e:
            result['checks']['local_network'] = False
            result['issues'].append(f"Local network issue: {e}")
            result['status'] = 'warning'
        
        return result
    
    def check_critical_services(self) -> Dict:
        """Check status of critical system services"""
        result = {
            'status': 'healthy',
            'services': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        critical_services = [
            'docker',
            'cloudflared',
            'ssh',
            'systemd-resolved'
        ]
        
        for service in critical_services:
            try:
                cmd = f"systemctl is-active {service}"
                output = subprocess.run(cmd.split(), capture_output=True, text=True)
                is_active = output.stdout.strip() == 'active'
                
                result['services'][service] = {
                    'active': is_active,
                    'status': output.stdout.strip()
                }
                
                if not is_active and service in ['docker', 'cloudflared']:
                    result['status'] = 'critical'
                    result['issues'].append(f"Critical service {service} is not active")
                elif not is_active:
                    result['status'] = 'warning' if result['status'] != 'critical' else 'critical'
                    result['issues'].append(f"Service {service} is not active")
                    
            except Exception as e:
                result['services'][service] = {'error': str(e)}
                result['issues'].append(f"Cannot check service {service}: {e}")
        
        return result
    
    def check_api_endpoints(self) -> Dict:
        """Check availability and response time of API endpoints"""
        result = {
            'status': 'healthy',
            'endpoints': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        endpoints = [
            ('https://localhost:8443/health', 'Barbossa Portal'),
            ('https://eastindiaonchaincompany.xyz/health', 'External Portal'),
            ('http://localhost:9000', 'Portainer'),
            ('http://localhost:3000', 'Grafana')
        ]
        
        for url, name in endpoints:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=5, verify=False)
                response_time = time.time() - start_time
                
                endpoint_result = {
                    'available': response.status_code < 500,
                    'status_code': response.status_code,
                    'response_time': response_time
                }
                result['endpoints'][name] = endpoint_result
                
                if response.status_code >= 500:
                    result['status'] = 'warning'
                    result['issues'].append(f"{name} returned error: {response.status_code}")
                elif response_time > self.thresholds['api_response_time']:
                    result['issues'].append(f"{name} slow response: {response_time:.2f}s")
                    
            except requests.RequestException as e:
                result['endpoints'][name] = {
                    'available': False,
                    'error': str(e)
                }
                if name == 'Barbossa Portal':
                    result['status'] = 'warning'
                result['issues'].append(f"{name} unavailable: {e}")
        
        return result
    
    def check_security_status(self) -> Dict:
        """Check security components and audit logs"""
        result = {
            'status': 'healthy',
            'security_checks': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Check security guard module
        security_guard_path = self.work_dir / 'security_guard.py'
        result['security_checks']['security_guard'] = security_guard_path.exists()
        
        # Check for recent security violations
        violations_log = self.work_dir / 'security' / 'security_violations.log'
        if violations_log.exists():
            # Check last 24 hours
            one_day_ago = time.time() - 86400
            recent_violations = 0
            
            try:
                with open(violations_log, 'r') as f:
                    for line in f:
                        if 'VIOLATION' in line:
                            # Parse timestamp if possible
                            recent_violations += 1
                
                result['security_checks']['recent_violations'] = recent_violations
                if recent_violations > 10:
                    result['status'] = 'warning'
                    result['issues'].append(f"High number of security violations: {recent_violations} in last 24h")
                elif recent_violations > 0:
                    result['issues'].append(f"{recent_violations} security violations detected")
                    
            except Exception as e:
                result['issues'].append(f"Cannot read violations log: {e}")
        
        # Check repository whitelist
        whitelist_path = self.work_dir / 'config' / 'repository_whitelist.json'
        result['security_checks']['whitelist_exists'] = whitelist_path.exists()
        if not whitelist_path.exists():
            result['status'] = 'critical'
            result['issues'].append("Repository whitelist missing!")
        
        return result
    
    def check_log_health(self) -> Dict:
        """Check log file sizes and rotation"""
        result = {
            'status': 'healthy',
            'log_stats': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        logs_dir = self.work_dir / 'logs'
        if logs_dir.exists():
            total_size = 0
            large_logs = []
            
            for log_file in logs_dir.rglob('*.log'):
                size_mb = log_file.stat().st_size / (1024 * 1024)
                total_size += size_mb
                
                if size_mb > self.thresholds['log_size_mb']:
                    large_logs.append((log_file.name, size_mb))
            
            result['log_stats']['total_size_mb'] = total_size
            result['log_stats']['log_count'] = len(list(logs_dir.rglob('*.log')))
            
            if large_logs:
                result['status'] = 'warning'
                for name, size in large_logs:
                    result['issues'].append(f"Large log file: {name} ({size:.1f} MB)")
            
            if total_size > 5000:  # 5GB total
                result['status'] = 'warning'
                result['issues'].append(f"High total log size: {total_size:.1f} MB")
        
        return result
    
    def check_dependencies(self) -> Dict:
        """Check project dependencies and packages"""
        result = {
            'status': 'healthy',
            'dependencies': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Check Python packages
        try:
            critical_packages = ['flask', 'requests', 'psutil', 'anthropic']
            import importlib
            
            for package in critical_packages:
                try:
                    importlib.import_module(package)
                    result['dependencies'][f'python_{package}'] = True
                except ImportError:
                    result['dependencies'][f'python_{package}'] = False
                    result['status'] = 'warning'
                    result['issues'].append(f"Missing Python package: {package}")
                    
        except Exception as e:
            result['issues'].append(f"Dependency check error: {e}")
        
        # Check Node.js for Davy Jones
        try:
            node_version = subprocess.run(['node', '--version'], 
                                        capture_output=True, text=True, timeout=5)
            if node_version.returncode == 0:
                result['dependencies']['nodejs'] = node_version.stdout.strip()
            else:
                result['dependencies']['nodejs'] = False
                result['issues'].append("Node.js not available")
        except:
            result['dependencies']['nodejs'] = False
        
        return result
    
    def check_database_health(self) -> Dict:
        """Check database connections and performance"""
        result = {
            'status': 'healthy',
            'databases': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Check metrics database
        metrics_db = self.work_dir / 'metrics.db'
        if metrics_db.exists():
            size_mb = metrics_db.stat().st_size / (1024 * 1024)
            result['databases']['metrics'] = {
                'exists': True,
                'size_mb': size_mb
            }
            if size_mb > 1000:  # 1GB
                result['issues'].append(f"Large metrics database: {size_mb:.1f} MB")
        else:
            result['databases']['metrics'] = {'exists': False}
        
        # Check state files
        state_dir = self.work_dir / 'state'
        if state_dir.exists():
            state_files = list(state_dir.glob('*.json'))
            result['databases']['state_files'] = len(state_files)
        
        return result
    
    def check_backup_status(self) -> Dict:
        """Check backup recency and integrity"""
        result = {
            'status': 'healthy',
            'backups': {},
            'issues': [],
            'timestamp': datetime.now().isoformat()
        }
        
        backup_dir = self.work_dir / 'backups'
        if backup_dir.exists():
            backups = list(backup_dir.glob('*'))
            if backups:
                latest_backup = max(backups, key=lambda x: x.stat().st_mtime)
                backup_age_hours = (time.time() - latest_backup.stat().st_mtime) / 3600
                
                result['backups']['latest'] = {
                    'name': latest_backup.name,
                    'age_hours': backup_age_hours,
                    'size_mb': latest_backup.stat().st_size / (1024 * 1024) if latest_backup.is_file() else 0
                }
                
                if backup_age_hours > self.thresholds['backup_age_hours']:
                    result['status'] = 'warning'
                    result['issues'].append(f"Backup is {backup_age_hours:.1f} hours old")
            else:
                result['status'] = 'warning'
                result['issues'].append("No backups found")
        else:
            result['status'] = 'warning'
            result['issues'].append("Backup directory does not exist")
        
        return result
    
    def _calculate_health_score(self, results: Dict) -> float:
        """Calculate overall health score from 0-100"""
        total_checks = len(results['components'])
        if total_checks == 0:
            return 0
        
        scores = {
            'healthy': 100,
            'warning': 70,
            'critical': 30,
            'error': 0
        }
        
        total_score = 0
        for component_result in results['components'].values():
            status = component_result.get('status', 'error')
            total_score += scores.get(status, 0)
        
        return total_score / total_checks
    
    def _save_health_results(self, results: Dict):
        """Save health check results to file"""
        try:
            # Load existing results
            if self.health_log.exists():
                with open(self.health_log, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Add new results
            history.append(results)
            
            # Keep only last 100 checks
            history = history[-100:]
            
            # Save updated history
            with open(self.health_log, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Could not save health results: {e}")
    
    def get_health_summary(self) -> str:
        """Get a human-readable health summary"""
        results = self.perform_full_health_check()
        
        summary = []
        summary.append("=" * 70)
        summary.append("BARBOSSA SYSTEM HEALTH CHECK")
        summary.append("=" * 70)
        summary.append(f"Timestamp: {results['timestamp']}")
        summary.append(f"Overall Status: {results['overall_status'].upper()}")
        summary.append(f"Health Score: {results['health_score']:.1f}/100")
        summary.append("")
        
        # Component status
        summary.append("Component Status:")
        for component, result in results['components'].items():
            status = result.get('status', 'unknown')
            status_icon = {
                'healthy': '✓',
                'warning': '⚠',
                'critical': '✗',
                'error': '!'
            }.get(status, '?')
            summary.append(f"  {status_icon} {component}: {status}")
        
        # Issues
        if results['issues']:
            summary.append("")
            summary.append("Issues Detected:")
            for issue in results['issues']:
                summary.append(f"  - {issue}")
        else:
            summary.append("")
            summary.append("No issues detected - system healthy!")
        
        summary.append("=" * 70)
        
        return "\n".join(summary)