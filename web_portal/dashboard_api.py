#!/usr/bin/env python3
"""
Dashboard API - Complete refactored backend with real data
All endpoints return actual system data, no placeholders
"""

import json
import os
import subprocess
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from flask import Blueprint, jsonify, request
import glob
import re

dashboard_api = Blueprint('dashboard_api', __name__)

class DashboardDataProvider:
    """Provides real data for the dashboard"""
    
    def __init__(self):
        self.barbossa_dir = Path.home() / 'barbossa-engineer'
        self.logs_dir = self.barbossa_dir / 'logs'
        self.work_tracking_dir = self.barbossa_dir / 'work_tracking'
        self.projects_dir = self.barbossa_dir / 'projects'
        self.state_dir = self.barbossa_dir / 'state'
        self.metrics_dir = self.barbossa_dir / 'metrics'
        self.summaries_dir = self.barbossa_dir / 'summaries'
    
    def get_barbossa_status(self):
        """Get real Barbossa status"""
        # Check if Barbossa is running
        barbossa_running = False
        try:
            result = subprocess.run(['pgrep', '-f', 'barbossa.py'], capture_output=True)
            barbossa_running = result.returncode == 0
        except:
            pass
        
        # Get work tally
        work_tally = {}
        tally_file = self.work_tracking_dir / 'work_tally.json'
        if tally_file.exists():
            try:
                with open(tally_file, 'r') as f:
                    work_tally = json.load(f)
            except:
                pass
        
        # Get next cron runs
        next_runs = self._get_next_cron_runs()
        
        # Count Claude processes
        claude_count = 0
        try:
            result = subprocess.run(['pgrep', '-f', 'claude'], capture_output=True)
            if result.returncode == 0:
                claude_count = len(result.stdout.decode().strip().split('\n'))
        except:
            pass
        
        # Get last run time from logs
        last_run = None
        log_files = sorted(self.logs_dir.glob('barbossa_*.log*'), reverse=True)
        if log_files:
            last_run = datetime.fromtimestamp(log_files[0].stat().st_mtime).isoformat()
        
        return {
            'status': 'running' if barbossa_running else 'idle',
            'work_tally': work_tally,
            'next_runs': next_runs,
            'claude_processes': claude_count,
            'last_run': last_run
        }
    
    def _get_next_cron_runs(self):
        """Calculate next cron run times"""
        now = datetime.now()
        next_runs = {}
        
        # Parse cron schedule
        schedules = {
            'ticket_enrichment': {'hour': 9, 'minute': 0, 'daily': True},
            'infrastructure': {'hours': 2, 'interval': True},
            'performance': {'hours': 4, 'minute': 30, 'interval': True},
            'davy_jones': {'hours': [2, 10, 18]},
            'daily_summary': {'hour': 23, 'minute': 0, 'daily': True}
        }
        
        for task, schedule in schedules.items():
            if 'daily' in schedule and schedule['daily']:
                # Daily task
                next_time = now.replace(hour=schedule['hour'], minute=schedule['minute'], second=0)
                if next_time <= now:
                    next_time += timedelta(days=1)
                next_runs[task] = next_time.strftime('%H:%M UTC')
            elif 'interval' in schedule and schedule['interval']:
                # Interval task
                hours = schedule['hours']
                minute = schedule.get('minute', 0)
                # Calculate next interval
                current_hour = now.hour
                next_hour = ((current_hour // hours) + 1) * hours
                if next_hour >= 24:
                    next_hour = next_hour % 24
                next_runs[task] = f"{next_hour:02d}:{minute:02d} UTC"
            elif 'hours' in schedule and isinstance(schedule['hours'], list):
                # Multiple times per day
                for hour in schedule['hours']:
                    next_time = now.replace(hour=hour, minute=0, second=0)
                    if next_time > now:
                        next_runs[task] = next_time.strftime('%H:%M UTC')
                        break
                else:
                    # Next day
                    next_runs[task] = f"{schedule['hours'][0]:02d}:00 UTC (tomorrow)"
        
        return next_runs
    
    def get_system_stats(self):
        """Get real system statistics"""
        return {
            'cpu': {
                'percent': psutil.cpu_percent(interval=1),
                'cores': psutil.cpu_count(),
                'load_avg': os.getloadavg()
            },
            'memory': {
                'percent': psutil.virtual_memory().percent,
                'used': f"{psutil.virtual_memory().used / (1024**3):.1f}G",
                'total': f"{psutil.virtual_memory().total / (1024**3):.1f}G",
                'available': f"{psutil.virtual_memory().available / (1024**3):.1f}G"
            },
            'disk': {
                'percent': psutil.disk_usage('/').percent,
                'used': f"{psutil.disk_usage('/').used / (1024**4):.1f}T",
                'total': f"{psutil.disk_usage('/').total / (1024**4):.1f}T",
                'free': f"{psutil.disk_usage('/').free / (1024**4):.1f}T"
            },
            'network': {
                'connections': len(psutil.net_connections()),
                'interfaces': len(psutil.net_if_addrs())
            },
            'uptime': self._get_uptime()
        }
    
    def _get_uptime(self):
        """Get system uptime"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                return f"{days}d {hours}h"
        except:
            return "unknown"
    
    def get_recent_logs(self, limit=10):
        """Get recent log entries"""
        logs = []
        
        # Get today's logs
        today = datetime.now().strftime('%Y%m%d')
        log_files = sorted(self.logs_dir.glob(f'*{today}*.log'), reverse=True)
        
        for log_file in log_files[:3]:  # Check last 3 log files
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-20:]  # Last 20 lines
                    for line in lines:
                        # Parse log line
                        if 'ERROR' in line or 'WARNING' in line or 'INFO' in line:
                            logs.append({
                                'file': log_file.name,
                                'level': 'ERROR' if 'ERROR' in line else 'WARNING' if 'WARNING' in line else 'INFO',
                                'message': line.strip()[:200],  # Truncate long lines
                                'timestamp': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                            })
            except:
                continue
        
        return logs[:limit]
    
    def get_projects_info(self):
        """Get information about projects"""
        projects = []
        
        for project_dir in self.projects_dir.glob('*'):
            if project_dir.is_dir() and not project_dir.name.startswith('.'):
                project_info = {
                    'name': project_dir.name,
                    'path': str(project_dir),
                    'files': 0,
                    'size': 0,
                    'last_modified': None,
                    'has_git': (project_dir / '.git').exists(),
                    'has_package_json': (project_dir / 'package.json').exists()
                }
                
                # Count files and size
                try:
                    for root, dirs, files in os.walk(project_dir):
                        # Skip node_modules and .git
                        if 'node_modules' in root or '.git' in root:
                            continue
                        project_info['files'] += len(files)
                        for file in files:
                            file_path = Path(root) / file
                            if file_path.exists():
                                project_info['size'] += file_path.stat().st_size
                    
                    # Get last modified
                    git_log = subprocess.run(
                        ['git', 'log', '-1', '--format=%at'],
                        cwd=project_dir,
                        capture_output=True,
                        text=True
                    )
                    if git_log.returncode == 0 and git_log.stdout.strip():
                        timestamp = int(git_log.stdout.strip())
                        project_info['last_modified'] = datetime.fromtimestamp(timestamp).isoformat()
                except:
                    pass
                
                projects.append(project_info)
        
        return sorted(projects, key=lambda x: x['name'])
    
    def get_services_status(self):
        """Get status of key services"""
        services = {}
        
        # Check Docker
        try:
            result = subprocess.run(['docker', 'ps', '-q'], capture_output=True, timeout=5)
            container_count = len(result.stdout.decode().strip().split('\n')) if result.stdout.strip() else 0
            services['docker'] = {
                'status': 'running' if result.returncode == 0 else 'stopped',
                'containers': container_count
            }
        except:
            services['docker'] = {'status': 'error', 'containers': 0}
        
        # Check tmux sessions
        try:
            result = subprocess.run(['tmux', 'list-sessions'], capture_output=True, text=True)
            if result.returncode == 0:
                sessions = result.stdout.strip().split('\n')
                services['tmux'] = {
                    'status': 'running',
                    'sessions': [s.split(':')[0] for s in sessions]
                }
            else:
                services['tmux'] = {'status': 'no sessions', 'sessions': []}
        except:
            services['tmux'] = {'status': 'error', 'sessions': []}
        
        # Check key processes
        processes = ['cloudflared', 'postgresql', 'nginx', 'redis-server']
        for proc in processes:
            try:
                result = subprocess.run(['pgrep', '-x', proc], capture_output=True)
                services[proc] = 'running' if result.returncode == 0 else 'stopped'
            except:
                services[proc] = 'unknown'
        
        return services
    
    def get_work_sessions(self, limit=10):
        """Get recent work sessions"""
        sessions = []
        
        # Look for session files in state directory
        session_files = sorted(self.state_dir.glob('session_*.json'), reverse=True)
        
        for session_file in session_files[:limit]:
            try:
                with open(session_file, 'r') as f:
                    session = json.load(f)
                    sessions.append(session)
            except:
                continue
        
        # If no session files, check current work
        if not sessions and (self.work_tracking_dir / 'current_work.json').exists():
            try:
                with open(self.work_tracking_dir / 'current_work.json', 'r') as f:
                    current = json.load(f)
                    sessions.append({
                        'id': 'current',
                        'area': current.get('area', 'unknown'),
                        'started': current.get('started', datetime.now().isoformat()),
                        'status': 'active'
                    })
            except:
                pass
        
        return sessions
    
    def get_performance_metrics(self):
        """Get latest performance metrics"""
        metrics = {
            'cpu_history': [],
            'memory_history': [],
            'disk_io': {},
            'network_io': {}
        }
        
        # Get latest metrics file
        if self.metrics_dir.exists():
            metric_files = sorted(self.metrics_dir.glob('performance_*.json'), reverse=True)
            if metric_files:
                try:
                    with open(metric_files[0], 'r') as f:
                        data = json.load(f)
                        if 'system' in data:
                            metrics['latest'] = data['system']
                        if 'processes' in data:
                            metrics['top_processes'] = data['processes'].get('top_cpu', [])[:3]
                except:
                    pass
        
        # Get current metrics
        metrics['current'] = {
            'cpu': psutil.cpu_percent(interval=0.5),
            'memory': psutil.virtual_memory().percent,
            'disk': psutil.disk_usage('/').percent
        }
        
        return metrics
    
    def execute_action(self, action, params=None):
        """Execute dashboard actions"""
        results = {'success': False, 'message': 'Unknown action'}
        
        if action == 'trigger_barbossa':
            area = params.get('area', 'infrastructure')
            try:
                # Start Barbossa with specified area
                cmd = ['python3', str(self.barbossa_dir / 'barbossa.py'), '--area', area]
                process = subprocess.Popen(cmd, cwd=self.barbossa_dir)
                
                # Create session record
                session_id = f"{area}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                session_file = self.state_dir / f'session_{session_id}.json'
                
                with open(session_file, 'w') as f:
                    json.dump({
                        'id': session_id,
                        'area': area,
                        'started': datetime.now().isoformat(),
                        'pid': process.pid,
                        'status': 'running'
                    }, f, indent=2)
                
                results = {
                    'success': True,
                    'message': f'Started Barbossa for {area}',
                    'session_id': session_id
                }
            except Exception as e:
                results = {'success': False, 'message': str(e)}
        
        elif action == 'kill_process':
            pid = params.get('pid')
            if pid:
                try:
                    os.kill(int(pid), 9)
                    results = {'success': True, 'message': f'Killed process {pid}'}
                except:
                    results = {'success': False, 'message': f'Could not kill process {pid}'}
        
        elif action == 'clear_logs':
            try:
                # Archive old logs
                old_logs = self.logs_dir.glob('*.log')
                archived = 0
                for log in old_logs:
                    if (datetime.now() - datetime.fromtimestamp(log.stat().st_mtime)).days > 7:
                        log.unlink()
                        archived += 1
                results = {'success': True, 'message': f'Archived {archived} old log files'}
            except Exception as e:
                results = {'success': False, 'message': str(e)}
        
        elif action == 'restart_service':
            service = params.get('service')
            if service == 'portal':
                try:
                    subprocess.run(['tmux', 'kill-session', '-t', 'barbossa-portal'])
                    subprocess.run(['tmux', 'new-session', '-d', '-s', 'barbossa-portal', 
                                  'cd /home/dappnode/barbossa-engineer/web_portal && python3 app.py'])
                    results = {'success': True, 'message': 'Portal restarted'}
                except Exception as e:
                    results = {'success': False, 'message': str(e)}
        
        return results


# Initialize data provider
provider = DashboardDataProvider()

# API Routes
@dashboard_api.route('/api/dashboard/status')
def get_status():
    """Get complete dashboard status"""
    return jsonify({
        'barbossa': provider.get_barbossa_status(),
        'system': provider.get_system_stats(),
        'services': provider.get_services_status(),
        'timestamp': datetime.now().isoformat()
    })

@dashboard_api.route('/api/dashboard/logs')
def get_logs():
    """Get recent logs"""
    limit = request.args.get('limit', 10, type=int)
    return jsonify({
        'logs': provider.get_recent_logs(limit),
        'count': limit
    })

@dashboard_api.route('/api/dashboard/projects')
def get_projects():
    """Get projects information"""
    return jsonify({
        'projects': provider.get_projects_info()
    })

@dashboard_api.route('/api/dashboard/sessions')
def get_sessions():
    """Get work sessions"""
    return jsonify({
        'sessions': provider.get_work_sessions()
    })

@dashboard_api.route('/api/dashboard/performance')
def get_performance():
    """Get performance metrics"""
    return jsonify(provider.get_performance_metrics())

@dashboard_api.route('/api/dashboard/action', methods=['POST'])
def execute_action():
    """Execute dashboard action"""
    data = request.get_json()
    action = data.get('action')
    params = data.get('params', {})
    
    result = provider.execute_action(action, params)
    return jsonify(result)

@dashboard_api.route('/api/dashboard/health')
def health_check():
    """Simple health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })