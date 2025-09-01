#!/usr/bin/env python3
"""
Enhanced Portal API - Functional implementations for all dashboard features
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from flask import Blueprint, jsonify, request
import psutil
import threading

# Import parent modules
import sys
sys.path.append(str(Path(__file__).parent.parent))
from ticket_enrichment import TicketEnrichmentEngine

enhanced_portal_api = Blueprint('enhanced_portal_api', __name__)

# Cache for performance
_cache = {}
_cache_lock = threading.Lock()

class BarbossaPortalController:
    """Central controller for all portal operations"""
    
    def __init__(self):
        self.work_dir = Path.home() / 'barbossa-engineer'
        self.ticket_engine = None
        self._init_ticket_engine()
    
    def _init_ticket_engine(self):
        """Initialize ticket enrichment engine"""
        try:
            self.ticket_engine = TicketEnrichmentEngine(self.work_dir)
        except Exception as e:
            print(f"Could not initialize ticket engine: {e}")
    
    def get_work_distribution(self) -> Dict:
        """Get detailed work distribution with progress"""
        tally_file = self.work_dir / 'work_tracking' / 'work_tally.json'
        distribution = {}
        
        if tally_file.exists():
            with open(tally_file, 'r') as f:
                tally = json.load(f)
                
            total = sum(tally.values())
            for area, count in tally.items():
                distribution[area] = {
                    'count': count,
                    'percentage': (count / total * 100) if total > 0 else 0,
                    'last_run': self._get_last_run(area),
                    'next_scheduled': self._get_next_scheduled(area)
                }
        
        return distribution
    
    def _get_last_run(self, area: str) -> Optional[str]:
        """Get last run time for a work area"""
        log_pattern = self.work_dir / 'logs' / f'{area}_*.log'
        logs = list(self.work_dir.glob(f'logs/{area}_*.log'))
        if logs:
            latest = max(logs, key=lambda p: p.stat().st_mtime)
            return datetime.fromtimestamp(latest.stat().st_mtime).isoformat()
        return None
    
    def _get_next_scheduled(self, area: str) -> Optional[str]:
        """Calculate next scheduled run based on cron"""
        schedules = {
            'personal_projects': 6,  # hours
            'davy_jones': 8,
            'infrastructure': 2,
            'barbossa_self': 168  # weekly
        }
        
        if area in schedules:
            last_run = self._get_last_run(area)
            if last_run:
                last = datetime.fromisoformat(last_run)
                next_run = last + timedelta(hours=schedules[area])
                return next_run.isoformat()
        
        return None
    
    def get_project_details(self, project_name: str) -> Dict:
        """Get detailed information about a project"""
        project_dir = self.work_dir / 'projects' / project_name
        
        if not project_dir.exists():
            return {'error': 'Project not found'}
        
        details = {
            'name': project_name,
            'path': str(project_dir),
            'last_modified': None,
            'size': 0,
            'file_count': 0,
            'recent_changes': [],
            'dependencies': {},
            'test_coverage': None,
            'build_status': 'unknown'
        }
        
        # Get project stats
        try:
            # File count and size
            for root, dirs, files in os.walk(project_dir):
                details['file_count'] += len(files)
                for file in files:
                    file_path = Path(root) / file
                    if file_path.exists():
                        details['size'] += file_path.stat().st_size
            
            # Recent git changes
            result = subprocess.run(
                ['git', 'log', '--oneline', '-10'],
                cwd=project_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                details['recent_changes'] = result.stdout.strip().split('\n')
            
            # Check for package.json
            package_json = project_dir / 'package.json'
            if package_json.exists():
                with open(package_json, 'r') as f:
                    pkg = json.load(f)
                    details['dependencies'] = {
                        'prod': len(pkg.get('dependencies', {})),
                        'dev': len(pkg.get('devDependencies', {}))
                    }
            
            # Check test coverage if available
            coverage_file = project_dir / 'coverage' / 'coverage-summary.json'
            if coverage_file.exists():
                with open(coverage_file, 'r') as f:
                    coverage = json.load(f)
                    if 'total' in coverage:
                        details['test_coverage'] = coverage['total'].get('lines', {}).get('pct', 0)
        
        except Exception as e:
            print(f"Error getting project details: {e}")
        
        return details
    
    def trigger_barbossa_work(self, area: str, custom_prompt: Optional[str] = None) -> Dict:
        """Trigger Barbossa to work on a specific area"""
        try:
            cmd = ['python3', str(self.work_dir / 'barbossa.py'), '--area', area]
            
            if custom_prompt:
                cmd.extend(['--prompt', custom_prompt])
            
            # Run in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.work_dir
            )
            
            # Create session tracking
            session_id = f"{area}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            session_file = self.work_dir / 'state' / f'session_{session_id}.json'
            session_file.parent.mkdir(exist_ok=True)
            
            with open(session_file, 'w') as f:
                json.dump({
                    'id': session_id,
                    'area': area,
                    'prompt': custom_prompt,
                    'started': datetime.now().isoformat(),
                    'pid': process.pid,
                    'status': 'running'
                }, f, indent=2)
            
            return {
                'success': True,
                'session_id': session_id,
                'message': f'Started Barbossa session for {area}'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_workflow_status(self, workflow_id: str) -> Dict:
        """Get detailed workflow status"""
        workflows = {
            'ticket_enrichment': {
                'name': 'Ticket Enrichment',
                'schedule': 'Daily at 09:00 UTC',
                'last_run': None,
                'next_run': None,
                'stats': {}
            },
            'performance_optimization': {
                'name': 'Performance Optimization',
                'schedule': 'Every 4 hours',
                'last_run': None,
                'next_run': None,
                'metrics': {}
            },
            'project_development': {
                'name': 'Project Development',
                'schedule': 'Every 6 hours',
                'active_projects': [],
                'completed_today': 0
            }
        }
        
        if workflow_id in workflows:
            workflow = workflows[workflow_id]
            
            # Get enrichment stats
            if workflow_id == 'ticket_enrichment' and self.ticket_engine:
                workflow['stats'] = self.ticket_engine.get_enrichment_stats()
            
            # Get performance metrics
            elif workflow_id == 'performance_optimization':
                metrics_dir = self.work_dir / 'metrics'
                if metrics_dir.exists():
                    metrics_files = sorted(metrics_dir.glob('performance_*.json'))
                    if metrics_files:
                        with open(metrics_files[-1], 'r') as f:
                            workflow['metrics'] = json.load(f)
            
            return workflow
        
        return {'error': 'Workflow not found'}
    
    def get_system_anomalies(self) -> List[Dict]:
        """Detect and return system anomalies"""
        anomalies = []
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            anomalies.append({
                'type': 'high_cpu',
                'severity': 'warning',
                'message': f'CPU usage at {cpu_percent}%',
                'timestamp': datetime.now().isoformat()
            })
        
        # Check memory
        mem = psutil.virtual_memory()
        if mem.percent > 85:
            anomalies.append({
                'type': 'high_memory',
                'severity': 'warning',
                'message': f'Memory usage at {mem.percent}%',
                'timestamp': datetime.now().isoformat()
            })
        
        # Check disk
        disk = psutil.disk_usage('/')
        if disk.percent > 85:
            anomalies.append({
                'type': 'low_disk',
                'severity': 'critical',
                'message': f'Disk usage at {disk.percent}%',
                'timestamp': datetime.now().isoformat()
            })
        
        # Check for zombie processes
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    anomalies.append({
                        'type': 'zombie_process',
                        'severity': 'low',
                        'message': f'Zombie process: {proc.info["name"]} (PID: {proc.info["pid"]})',
                        'timestamp': datetime.now().isoformat()
                    })
            except:
                pass
        
        # Check error logs
        log_dir = self.work_dir / 'logs'
        today = datetime.now().strftime('%Y%m%d')
        for log_file in log_dir.glob(f'*{today}*.log'):
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    error_count = content.count('ERROR') + content.count('CRITICAL')
                    if error_count > 10:
                        anomalies.append({
                            'type': 'high_errors',
                            'severity': 'warning',
                            'message': f'{error_count} errors in {log_file.name}',
                            'timestamp': datetime.now().isoformat()
                        })
            except:
                pass
        
        return anomalies
    
    def get_integration_status(self) -> Dict:
        """Get status of all integrations"""
        integrations = {}
        
        # GitHub
        integrations['github'] = {
            'name': 'GitHub',
            'status': 'unknown',
            'last_sync': None,
            'repositories': 0
        }
        
        if os.environ.get('GITHUB_TOKEN'):
            integrations['github']['status'] = 'configured'
            # Count repositories
            whitelist_file = self.work_dir / 'config' / 'repository_whitelist.json'
            if whitelist_file.exists():
                with open(whitelist_file, 'r') as f:
                    data = json.load(f)
                    integrations['github']['repositories'] = len(data.get('allowed_repositories', []))
        
        # Linear
        integrations['linear'] = {
            'name': 'Linear',
            'status': 'configured' if os.environ.get('LINEAR_API_KEY') else 'not_configured',
            'last_sync': None
        }
        
        # Cloudflare
        integrations['cloudflare'] = {
            'name': 'Cloudflare Tunnel',
            'status': 'unknown',
            'tunnel_id': '5ba42edf-f4d3-47c8-a1b3-68d46ac4f0ec'
        }
        
        # Check cloudflared status
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'cloudflared'],
                capture_output=True,
                text=True
            )
            integrations['cloudflare']['status'] = 'active' if result.stdout.strip() == 'active' else 'inactive'
        except:
            pass
        
        # Docker
        integrations['docker'] = {
            'name': 'Docker',
            'status': 'unknown',
            'containers': 0
        }
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '-q'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                integrations['docker']['status'] = 'active'
                integrations['docker']['containers'] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        except:
            pass
        
        return integrations
    
    def get_optimization_suggestions(self) -> List[Dict]:
        """Generate optimization suggestions based on system state"""
        suggestions = []
        
        # Analyze work distribution
        distribution = self.get_work_distribution()
        
        # Check for imbalanced work
        if distribution:
            percentages = [area['percentage'] for area in distribution.values()]
            if max(percentages) - min(percentages) > 50:
                suggestions.append({
                    'category': 'work_balance',
                    'priority': 'medium',
                    'suggestion': 'Work distribution is imbalanced. Consider adjusting weights.',
                    'action': 'rebalance_work'
                })
        
        # Check for old logs
        log_dir = self.work_dir / 'logs'
        old_logs = list(log_dir.glob('*.log'))
        old_logs = [f for f in old_logs if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days > 30]
        
        if len(old_logs) > 50:
            suggestions.append({
                'category': 'storage',
                'priority': 'low',
                'suggestion': f'Found {len(old_logs)} logs older than 30 days. Consider archiving.',
                'action': 'archive_logs'
            })
        
        # Check for unused cache
        cache_dir = self.work_dir / 'cache'
        if cache_dir.exists():
            cache_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
            if cache_size > 1024 * 1024 * 100:  # 100MB
                suggestions.append({
                    'category': 'storage',
                    'priority': 'low',
                    'suggestion': f'Cache is using {cache_size / 1024 / 1024:.1f}MB. Consider clearing.',
                    'action': 'clear_cache'
                })
        
        # Check for performance issues
        anomalies = self.get_system_anomalies()
        critical_anomalies = [a for a in anomalies if a['severity'] == 'critical']
        
        if critical_anomalies:
            suggestions.append({
                'category': 'performance',
                'priority': 'high',
                'suggestion': f'Found {len(critical_anomalies)} critical anomalies requiring attention.',
                'action': 'fix_anomalies'
            })
        
        return suggestions


# Initialize controller
controller = BarbossaPortalController()

# API Routes
@enhanced_portal_api.route('/api/v4/work-distribution')
def get_work_distribution():
    """Get detailed work distribution"""
    return jsonify(controller.get_work_distribution())

@enhanced_portal_api.route('/api/v4/project/<project_name>')
def get_project_details(project_name):
    """Get detailed project information"""
    return jsonify(controller.get_project_details(project_name))

@enhanced_portal_api.route('/api/v4/trigger-work', methods=['POST'])
def trigger_work():
    """Trigger Barbossa work session"""
    data = request.get_json()
    area = data.get('area', 'personal_projects')
    prompt = data.get('prompt')
    
    result = controller.trigger_barbossa_work(area, prompt)
    return jsonify(result)

@enhanced_portal_api.route('/api/v4/workflow/<workflow_id>')
def get_workflow_status(workflow_id):
    """Get workflow status"""
    return jsonify(controller.get_workflow_status(workflow_id))

@enhanced_portal_api.route('/api/v4/anomalies')
def get_anomalies():
    """Get system anomalies"""
    return jsonify({'anomalies': controller.get_system_anomalies()})

@enhanced_portal_api.route('/api/v4/integrations')
def get_integrations():
    """Get integration status"""
    return jsonify(controller.get_integration_status())

@enhanced_portal_api.route('/api/v4/optimizations')
def get_optimizations():
    """Get optimization suggestions"""
    return jsonify({'suggestions': controller.get_optimization_suggestions()})

@enhanced_portal_api.route('/api/v4/enrich-tickets', methods=['POST'])
def enrich_tickets():
    """Manually trigger ticket enrichment"""
    if controller.ticket_engine:
        results = controller.ticket_engine.run_daily_enrichment()
        return jsonify({
            'success': True,
            'results': {
                'enriched': len(results['enriched']),
                'failed': len(results['failed']),
                'skipped': len(results['skipped'])
            }
        })
    
    return jsonify({'success': False, 'error': 'Ticket engine not available'})

@enhanced_portal_api.route('/api/v4/performance-metrics')
def get_performance_metrics():
    """Get latest performance metrics"""
    metrics_dir = Path.home() / 'barbossa-engineer' / 'metrics'
    
    if metrics_dir.exists():
        metrics_files = sorted(metrics_dir.glob('performance_*.json'))
        if metrics_files:
            with open(metrics_files[-1], 'r') as f:
                return jsonify(json.load(f))
    
    return jsonify({'error': 'No metrics available'})

@enhanced_portal_api.route('/api/v4/execute-optimization', methods=['POST'])
def execute_optimization():
    """Execute an optimization suggestion"""
    data = request.get_json()
    action = data.get('action')
    
    results = {'success': False, 'message': 'Unknown action'}
    
    if action == 'archive_logs':
        # Archive old logs
        subprocess.run([str(Path.home() / 'barbossa-engineer' / 'run_daily_summary.sh')])
        results = {'success': True, 'message': 'Logs archived successfully'}
    
    elif action == 'clear_cache':
        # Clear cache
        cache_dir = Path.home() / 'barbossa-engineer' / 'cache'
        if cache_dir.exists():
            for f in cache_dir.rglob('*'):
                if f.is_file() and (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days > 7:
                    f.unlink()
            results = {'success': True, 'message': 'Cache cleared successfully'}
    
    elif action == 'rebalance_work':
        # Trigger work rebalancing
        controller.trigger_barbossa_work('barbossa_self', 'Analyze and rebalance work distribution weights')
        results = {'success': True, 'message': 'Work rebalancing initiated'}
    
    elif action == 'fix_anomalies':
        # Trigger infrastructure fix
        controller.trigger_barbossa_work('infrastructure', 'Fix critical system anomalies')
        results = {'success': True, 'message': 'Anomaly fixing initiated'}
    
    return jsonify(results)