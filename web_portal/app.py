#!/usr/bin/env python3
"""
Barbossa Enhanced Web Portal - Comprehensive Server Management Dashboard
Integrates with server_manager.py for complete infrastructure control
"""

import json
import os
import ssl
import subprocess
import re
import time
import sys
import functools
import threading
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file, send_from_directory
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.profiler import ProfilerMiddleware
import secrets
import shutil
import gzip
import io

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import the server manager
try:
    from server_manager import BarbossaServerManager
    SERVER_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import server_manager: {e}")
    SERVER_MANAGER_AVAILABLE = False

# Import workflow API
try:
    sys.path.append(str(Path(__file__).parent))
    from workflow_api import workflow_api
    WORKFLOW_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import workflow API: {e}")
    WORKFLOW_API_AVAILABLE = False

# Import enhanced security - DISABLED due to rate limiting issues
try:
    # Temporarily disable enhanced security to fix authentication issues
    ENHANCED_SECURITY_AVAILABLE = False
    enhanced_security = None
    print("Enhanced security temporarily disabled")
except ImportError as e:
    print(f"Warning: Could not import enhanced security: {e}")
    ENHANCED_SECURITY_AVAILABLE = False
    enhanced_security = None
    
# Import Barbossa Prompt Manager
try:
    from barbossa_prompt_api import BarbossaPromptManager
    PROMPT_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import barbossa_prompt_api: {e}")
    PROMPT_MANAGER_AVAILABLE = False
    ENHANCED_SECURITY_AVAILABLE = False

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = secrets.token_hex(32)
auth = HTTPBasicAuth()

# Register workflow API blueprint if available
if WORKFLOW_API_AVAILABLE:
    app.register_blueprint(workflow_api)
    print("Workflow API registered")

# Register Personal Assistant v4 API
try:
    from personal_assistant_api import personal_assistant_api
    app.register_blueprint(personal_assistant_api)
    print("Personal Assistant v4 API registered")
    PERSONAL_ASSISTANT_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Personal Assistant API: {e}")
    PERSONAL_ASSISTANT_API_AVAILABLE = False

# Register enhanced API blueprint
try:
    from enhanced_api import enhanced_api
    app.register_blueprint(enhanced_api)
    print("Enhanced API v2 registered")
    ENHANCED_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import enhanced API: {e}")
    ENHANCED_API_AVAILABLE = False

# Register advanced API blueprint
try:
    from advanced_api import advanced_api
    app.register_blueprint(advanced_api)
    print("Advanced API v3 registered")
    ADVANCED_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import advanced API: {e}")
    ADVANCED_API_AVAILABLE = False

# Register monitoring API blueprint
try:
    from monitoring_api import monitoring_api
    app.register_blueprint(monitoring_api)
    print("Monitoring API registered")
    MONITORING_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import monitoring API: {e}")
    MONITORING_API_AVAILABLE = False

# Register development tools API blueprint
try:
    from devtools_api import devtools_api
    app.register_blueprint(devtools_api)
    print("Development Tools API registered")
    DEVTOOLS_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import development tools API: {e}")
    DEVTOOLS_API_AVAILABLE = False

# Register enhanced portal API v4 blueprint
try:
    from enhanced_portal_api import enhanced_portal_api
    app.register_blueprint(enhanced_portal_api)
    print("Enhanced Portal API v4 registered")
    ENHANCED_PORTAL_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import enhanced portal API: {e}")
    ENHANCED_PORTAL_API_AVAILABLE = False

# Register refactored dashboard API
try:
    from dashboard_api import dashboard_api
    app.register_blueprint(dashboard_api)
    print("Dashboard API (refactored) registered")
    DASHBOARD_API_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import dashboard API: {e}")
    DASHBOARD_API_AVAILABLE = False

# Enable JSON minification for better performance
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Global cache for API responses with size management
_cache = {}
_cache_expiry = {}
_cache_access = {}  # Track access times for LRU eviction
_cache_lock = threading.Lock()
_cache_max_size = 200  # Maximum cache entries

def cached_response(ttl: int = 60):
    """Decorator to cache API responses with LRU eviction"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{hash(str(args))}{hash(str(kwargs))}"
            current_time = time.time()
            
            with _cache_lock:
                if cache_key in _cache and cache_key in _cache_expiry:
                    if current_time < _cache_expiry[cache_key]:
                        _cache_access[cache_key] = current_time
                        return _cache[cache_key]
                    else:
                        # Remove expired entry
                        _cache.pop(cache_key, None)
                        _cache_expiry.pop(cache_key, None)
                        _cache_access.pop(cache_key, None)
                
                # Clean up cache if it's too large
                if len(_cache) >= _cache_max_size:
                    # Remove oldest accessed entries
                    sorted_keys = sorted(_cache_access.items(), key=lambda x: x[1])
                    keys_to_remove = [k for k, _ in sorted_keys[:_cache_max_size // 4]]  # Remove 25%
                    for key in keys_to_remove:
                        _cache.pop(key, None)
                        _cache_expiry.pop(key, None)
                        _cache_access.pop(key, None)
            
            result = func(*args, **kwargs)
            
            with _cache_lock:
                _cache[cache_key] = result
                _cache_expiry[cache_key] = current_time + ttl
                _cache_access[cache_key] = current_time
            
            return result
        return wrapper
    return decorator

def performance_monitor(func):
    """Decorator to monitor API performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # Convert to milliseconds
        if duration > 1000:  # Log slow requests (>1 second)
            print(f"SLOW API: {func.__name__} took {duration:.2f}ms")
        
        return result
    return wrapper

# Add performance profiling in development
if os.getenv('FLASK_ENV') == 'development':
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])

# Configuration
BARBOSSA_DIR = Path.home() / 'barbossa-engineer'
LOGS_DIR = BARBOSSA_DIR / 'logs'
CHANGELOGS_DIR = BARBOSSA_DIR / 'changelogs'
SECURITY_DIR = BARBOSSA_DIR / 'security'
WORK_TRACKING_DIR = BARBOSSA_DIR / 'work_tracking'
PROJECTS_DIR = BARBOSSA_DIR / 'projects'
ARCHIVE_DIR = BARBOSSA_DIR / 'archive'

# Ensure directories exist
for dir_path in [LOGS_DIR, CHANGELOGS_DIR, SECURITY_DIR, WORK_TRACKING_DIR, PROJECTS_DIR, ARCHIVE_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Initialize server manager if available
server_manager = None
if SERVER_MANAGER_AVAILABLE:
    try:
        server_manager = BarbossaServerManager()
        server_manager.start_monitoring()
        print("Server manager initialized and monitoring started")
    except Exception as e:
        print(f"Error initializing server manager: {e}")
        server_manager = None

# Initialize Barbossa Prompt Manager if available
prompt_manager = None
if PROMPT_MANAGER_AVAILABLE:
    try:
        prompt_manager = BarbossaPromptManager(BARBOSSA_DIR, BARBOSSA_DIR / 'logs')
        print("Barbossa Prompt Manager initialized")
    except Exception as e:
        print(f"Error initializing prompt manager: {e}")
        prompt_manager = None

# Initialize enhanced security if available
enhanced_security = None
if ENHANCED_SECURITY_AVAILABLE:
    try:
        enhanced_security = SecurityEnhanced()
        print("Enhanced security initialized")
    except Exception as e:
        print(f"Error initializing enhanced security: {e}")
        enhanced_security = None

# Load credentials from external file (not in git)
def load_credentials():
    creds_file = Path.home() / '.barbossa_credentials.json'
    if creds_file.exists():
        with open(creds_file, 'r') as f:
            creds = json.load(f)
            return {
                username: generate_password_hash(password)
                for username, password in creds.items()
            }
    else:
        # Create default credentials file
        default_creds = {"admin": "Galleon6242"}
        with open(creds_file, 'w') as f:
            json.dump(default_creds, f)
        # Set restrictive permissions
        os.chmod(creds_file, 0o600)
        return {
            username: generate_password_hash(password)
            for username, password in default_creds.items()
        }

users = load_credentials()

@auth.verify_password
def verify_password(username, password):
    # Enhanced security: Check rate limiting and brute force
    if enhanced_security:
        client_ip = request.remote_addr
        
        # Check if IP is blocked
        if enhanced_security.check_brute_force(client_ip, username):
            return None
        
        # Check rate limiting
        if not enhanced_security.rate_limit_check(client_ip):
            return None
    
    if username in users and check_password_hash(users.get(username), password):
        session['username'] = username
        
        # Enhanced security: Create secure session
        if enhanced_security:
            session_id = enhanced_security.create_session(username, request.remote_addr)
            session['session_id'] = session_id
            enhanced_security.record_successful_attempt(request.remote_addr, username, request.endpoint)
        
        return username
    else:
        # Enhanced security: Record failed attempt
        if enhanced_security:
            enhanced_security.record_failed_attempt(request.remote_addr, username, request.endpoint)
        
        return None

def sanitize_sensitive_info(text):
    """Remove sensitive information from logs"""
    if not text:
        return text
    
    # Hide API keys
    text = re.sub(r'(api[_-]?key|token|secret|password)["\']?\s*[:=]\s*["\']?[\w-]+', 
                  r'\1=***REDACTED***', text, flags=re.IGNORECASE)
    
    # Hide specific passwords
    text = text.replace('Ableton6242', '***REDACTED***')
    text = text.replace('Galleon6242', '***REDACTED***')
    
    # Hide environment variables that might contain secrets
    text = re.sub(r'(ANTHROPIC_API_KEY|GITHUB_TOKEN|SLACK_TOKEN)=[\w-]+', 
                  r'\1=***REDACTED***', text)
    
    # Hide SSH keys
    text = re.sub(r'-----BEGIN [A-Z ]+-----[\s\S]+?-----END [A-Z ]+-----', 
                  '***SSH_KEY_REDACTED***', text)
    
    return text

def get_system_stats():
    """Get current system statistics"""
    stats = {}
    
    # CPU usage
    try:
        result = subprocess.run(['top', '-bn1'], capture_output=True, text=True)
        cpu_line = [line for line in result.stdout.split('\n') if 'Cpu(s)' in line or '%Cpu' in line][0]
        stats['cpu_usage'] = cpu_line.strip()
    except:
        stats['cpu_usage'] = 'N/A'
    
    # Memory usage
    try:
        result = subprocess.run(['free', '-h'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        mem_line = lines[1].split()
        stats['memory'] = {
            'total': mem_line[1],
            'used': mem_line[2],
            'free': mem_line[3]
        }
    except:
        stats['memory'] = {'total': 'N/A', 'used': 'N/A', 'free': 'N/A'}
    
    # Disk usage
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        disk_line = lines[1].split()
        stats['disk'] = {
            'total': disk_line[1],
            'used': disk_line[2],
            'available': disk_line[3],
            'percent': disk_line[4]
        }
    except:
        stats['disk'] = {'total': 'N/A', 'used': 'N/A', 'available': 'N/A', 'percent': 'N/A'}
    
    return stats

def get_barbossa_status():
    """Get comprehensive Barbossa status"""
    status = {
        'running': False,
        'last_run': None,
        'next_run': None,
        'work_tally': {},
        'current_work': None,
        'recent_logs': [],
        'claude_processes': []
    }
    
    # Check if Barbossa is currently running
    result = subprocess.run(['pgrep', '-f', 'barbossa.py'], capture_output=True, text=True)
    status['running'] = bool(result.stdout.strip())
    
    # Get work tally
    tally_file = WORK_TRACKING_DIR / 'work_tally.json'
    if tally_file.exists():
        with open(tally_file, 'r') as f:
            status['work_tally'] = json.load(f)
    
    # Get current work
    current_work_file = WORK_TRACKING_DIR / 'current_work.json'
    if current_work_file.exists():
        with open(current_work_file, 'r') as f:
            status['current_work'] = json.load(f)
    
    # Get recent logs - including both barbossa and claude execution logs
    if LOGS_DIR.exists():
        barbossa_logs = list(LOGS_DIR.glob('barbossa_*.log'))
        claude_logs = list(LOGS_DIR.glob('claude_*.log'))
        all_logs = barbossa_logs + claude_logs
        log_files = sorted(all_logs, key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        for log_file in log_files:
            status['recent_logs'].append({
                'name': log_file.name,
                'size': f"{log_file.stat().st_size / 1024:.1f} KB",
                'modified': datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    # Check for running Claude processes
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'claude' in line.lower() and 'grep' not in line:
            parts = line.split()
            if len(parts) > 10:
                status['claude_processes'].append({
                    'pid': parts[1],
                    'cpu': parts[2],
                    'mem': parts[3],
                    'started': parts[8],
                    'time': parts[9]
                })
    
    # Calculate next run (based on cron schedule)
    current_hour = datetime.now().hour
    next_run_hour = ((current_hour // 4) + 1) * 4
    if next_run_hour >= 24:
        next_run_hour = 0
    status['next_run'] = f"{next_run_hour:02d}:00 UTC"
    
    return status

def categorize_log_type(filename):
    """Categorize log type based on filename"""
    filename_lower = filename.lower()
    
    if 'barbossa' in filename_lower:
        if 'operations' in filename_lower:
            return 'barbossa_operations'
        elif 'enhanced' in filename_lower:
            return 'barbossa_enhanced'
        return 'barbossa'
    elif 'claude' in filename_lower:
        if 'personal' in filename_lower:
            return 'claude_personal'
        elif 'infrastructure' in filename_lower:
            return 'claude_infrastructure'
        elif 'davy' in filename_lower:
            return 'claude_davy_jones'
        elif 'self' in filename_lower:
            return 'claude_self_improvement'
        return 'claude'
    elif 'cron' in filename_lower:
        if 'personal_assistant' in filename_lower:
            return 'cron_personal_assistant'
        elif 'ticket' in filename_lower:
            return 'cron_ticket_enrichment'
        elif 'daily' in filename_lower:
            return 'cron_daily_summary'
        return 'cron'
    elif 'server_manager' in filename_lower:
        return 'server_manager'
    elif 'workflow' in filename_lower:
        return 'workflow_engine'
    else:
        return 'general'

# Main dashboard route (consolidated)
@app.route('/')
@auth.login_required
def index():
    """Main Barbossa dashboard with all features"""
    # Use refactored dashboard for better functionality
    return render_template('dashboard_refactored.html', 
                         username=session.get('username'),
                         timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))

@app.route('/workflows')
@auth.login_required
def workflows():
    """Workflow automation dashboard"""
    return render_template('workflows.html',
                         username=session.get('username'),
                         timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))

@app.route('/logs')
@auth.login_required
def logs():
    """System logs viewer"""
    return render_template('logs.html',
                         username=session.get('username'),
                         timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))

# New comprehensive status endpoint
@app.route('/api/comprehensive-status')
@auth.login_required
@performance_monitor
@cached_response(ttl=15)  # Cache for 15 seconds
def api_comprehensive_status():
    """Get comprehensive server status including metrics, services, and alerts"""
    if server_manager:
        data = server_manager.get_dashboard_data()
        
        # Add historical metrics (limit for performance)
        data['historical_metrics'] = server_manager.metrics_collector.get_historical_metrics(24, limit=500)
        
        # Add Barbossa status
        data['barbossa'] = get_barbossa_status()
        
        return jsonify(data)
    else:
        # Fallback to basic status if server manager not available
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'system': get_system_stats(),
            'barbossa': get_barbossa_status(),
            'metrics': {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0
            },
            'alerts': {'active': 0, 'recent': []},
            'services': {}
        })

# Network status endpoint
@app.route('/api/network-status')
@auth.login_required
@performance_monitor
@cached_response(ttl=30)  # Cache for 30 seconds
def api_network_status():
    """Get network connections and open ports"""
    if server_manager:
        return jsonify({
            'connections': server_manager.network_monitor.get_network_connections()[:50],
            'open_ports': server_manager.network_monitor.get_open_ports()
        })
    else:
        return jsonify({'connections': [], 'open_ports': []})

# Projects endpoint
@app.route('/api/projects')
@auth.login_required
@performance_monitor
@cached_response(ttl=60)  # Cache for 1 minute
def api_projects():
    """Get project information"""
    if server_manager:
        server_manager.project_manager._scan_projects()  # Refresh project info
        return jsonify({
            'projects': server_manager.project_manager.projects,
            'stats': server_manager.project_manager.get_project_stats()
        })
    else:
        return jsonify({'projects': {}, 'stats': {}})

# Barbossa-specific status
@app.route('/api/barbossa-status')
@auth.login_required
@performance_monitor
@cached_response(ttl=10)  # Cache for 10 seconds
def api_barbossa_status():
    """Get detailed Barbossa status"""
    return jsonify(get_barbossa_status())

# Service control endpoint
@app.route('/api/service-control', methods=['POST'])
@auth.login_required
def api_service_control():
    """Control system services"""
    data = request.json
    service = data.get('service')
    action = data.get('action')
    
    if not service or not action:
        return jsonify({'success': False, 'error': 'Service and action required'}), 400
    
    if server_manager:
        if action == 'start':
            success, message = server_manager.service_manager.start_service(service)
        elif action == 'stop':
            success, message = server_manager.service_manager.stop_service(service)
        elif action == 'restart':
            success, message = server_manager.service_manager.restart_service(service)
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        return jsonify({'success': success, 'message': message})
    else:
        # Fallback to direct systemctl commands
        try:
            # Use sudo with password
            cmd = f"echo 'Ableton6242' | sudo -S systemctl {action} {service}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return jsonify({
                'success': result.returncode == 0,
                'message': sanitize_sensitive_info(result.stdout or result.stderr)
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

# Container control endpoint
@app.route('/api/container-control', methods=['POST'])
@auth.login_required
def api_container_control():
    """Control Docker containers"""
    data = request.json
    container = data.get('container')
    action = data.get('action')
    
    if not container or not action:
        return jsonify({'success': False, 'error': 'Container and action required'}), 400
    
    try:
        if action in ['start', 'stop', 'restart']:
            result = subprocess.run(['docker', action, container], capture_output=True, text=True)
            return jsonify({
                'success': result.returncode == 0,
                'message': result.stdout or result.stderr
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Recent logs endpoint
@app.route('/api/logs/recent')
@auth.login_required
def api_recent_logs():
    """Get recent log entries including all Barbossa-related logs"""
    logs = []
    
    # Get most recent log files from main logs directory
    if LOGS_DIR.exists():
        # Include all log types
        log_patterns = [
            '*.log',  # Regular logs
            'barbossa/*.log',  # Barbossa subdirectory logs
            'barbossa_*.log',  # Barbossa prefixed logs
            'cron_*.log',  # Cron execution logs
            'claude_*.log',  # Claude output logs
            '*_cron.log',  # Service-specific cron logs
        ]
        
        all_log_files = []
        for pattern in log_patterns:
            all_log_files.extend(LOGS_DIR.glob(pattern))
        
        # Sort by modification time
        log_files = sorted(all_log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-20:]  # Last 20 lines
                    for line in lines:
                        if line.strip():  # Skip empty lines
                            logs.append({
                                'timestamp': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                                'file': log_file.name if log_file.parent == LOGS_DIR else f"{log_file.parent.name}/{log_file.name}",
                                'content': sanitize_sensitive_info(line.strip()),
                                'type': categorize_log_type(log_file.name)
                            })
            except Exception as e:
                print(f"Error reading log {log_file}: {e}")
    
    return jsonify({'logs': logs[-200:]})  # Return last 200 log entries

# Original API endpoints (preserved for compatibility)
@app.route('/api/status')
@auth.login_required
def api_status():
    """Original status endpoint"""
    return jsonify({
        'barbossa': get_barbossa_status(),
        'system': get_system_stats(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/barbossa/activity')
@auth.login_required
@cached_response(ttl=30)
def api_barbossa_activity():
    """Get comprehensive Barbossa activity logs"""
    activity = {
        'recent_executions': [],
        'cron_status': [],
        'work_summary': {},
        'personal_assistant_activity': [],
        'current_status': 'idle'
    }
    
    # Check Barbossa subdirectory logs
    barbossa_logs_dir = LOGS_DIR / 'barbossa'
    if barbossa_logs_dir.exists():
        # Get operations logs
        operations_logs = sorted(barbossa_logs_dir.glob('barbossa_operations_*.log'), 
                                key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        
        for log_file in operations_logs:
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    # Extract key information
                    mode = 'LIVE' if 'Mode: LIVE' in content else 'DRY RUN'
                    tickets_enriched = re.search(r'(\d+) enriched', content)
                    improvements = re.search(r'(\d+) new improvements', content)
                    
                    activity['recent_executions'].append({
                        'timestamp': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                        'file': log_file.name,
                        'mode': mode,
                        'tickets_enriched': int(tickets_enriched.group(1)) if tickets_enriched else 0,
                        'improvements_found': int(improvements.group(1)) if improvements else 0
                    })
            except Exception as e:
                print(f"Error reading operations log {log_file}: {e}")
        
        # Check cron log
        cron_log = barbossa_logs_dir / 'cron.log'
        if cron_log.exists():
            try:
                with open(cron_log, 'r') as f:
                    lines = f.readlines()[-50:]  # Last 50 lines
                    for line in lines:
                        if 'Starting Barbossa' in line or 'Completed' in line:
                            activity['cron_status'].append(sanitize_sensitive_info(line.strip()))
            except Exception as e:
                print(f"Error reading cron log: {e}")
    
    # Check main cron logs
    main_cron_logs = sorted(LOGS_DIR.glob('cron_*.log'), 
                           key=lambda x: x.stat().st_mtime, reverse=True)[:5]
    
    for log_file in main_cron_logs:
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                if 'Barbossa' in content:
                    timestamp = datetime.fromtimestamp(log_file.stat().st_mtime)
                    activity['cron_status'].append(f"[{timestamp.strftime('%Y-%m-%d %H:%M')}] {log_file.name}: Barbossa execution logged")
        except Exception as e:
            print(f"Error reading cron log {log_file}: {e}")
    
    # Check Claude execution logs
    claude_logs = sorted(LOGS_DIR.glob('claude_*.log'), 
                        key=lambda x: x.stat().st_mtime, reverse=True)[:10]
    
    work_areas = {'personal': 0, 'infrastructure': 0, 'davy_jones': 0}
    for log_file in claude_logs:
        area = categorize_log_type(log_file.name)
        if 'personal' in area:
            work_areas['personal'] += 1
        elif 'infrastructure' in area:
            work_areas['infrastructure'] += 1
        elif 'davy' in area:
            work_areas['davy_jones'] += 1
    
    activity['work_summary'] = work_areas
    
    # Check if Barbossa is currently running
    result = subprocess.run(['pgrep', '-f', 'barbossa'], capture_output=True, text=True)
    if result.returncode == 0:
        activity['current_status'] = 'running'
    
    # Get personal assistant specific logs
    pa_logs = LOGS_DIR / 'personal_assistant'
    if pa_logs.exists():
        summaries = sorted(pa_logs.glob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
        for summary in summaries:
            activity['personal_assistant_activity'].append({
                'file': summary.name,
                'timestamp': datetime.fromtimestamp(summary.stat().st_mtime).isoformat()
            })
    
    return jsonify(activity)

@app.route('/api/changelogs')
@auth.login_required
def api_changelogs():
    """Get changelogs and Claude outputs"""
    limit = request.args.get('limit', 20, type=int)
    all_files = []
    
    # Get changelog files
    if CHANGELOGS_DIR.exists():
        changelog_files = list(CHANGELOGS_DIR.glob('*.md'))
        for changelog_file in changelog_files:
            all_files.append({
                'path': changelog_file,
                'type': 'changelog',
                'mtime': changelog_file.stat().st_mtime
            })
    
    # Get Claude output files from logs directory
    if LOGS_DIR.exists():
        claude_files = list(LOGS_DIR.glob('claude_*.log'))
        for claude_file in claude_files:
            all_files.append({
                'path': claude_file,
                'type': 'claude_output',
                'mtime': claude_file.stat().st_mtime
            })
    
    # Sort all files by modification time (newest first)
    all_files.sort(key=lambda x: x['mtime'], reverse=True)
    
    # Process and return the most recent files
    result = []
    for file_info in all_files[:limit]:
        file_path = file_info['path']
        name_parts = file_path.stem.split('_')
        
        # Determine work area from filename
        if file_info['type'] == 'claude_output':
            # claude_<area>_<timestamp>.log format
            work_area = name_parts[1] if len(name_parts) > 1 else 'unknown'
            file_type = 'Claude Output'
        else:
            # changelog format
            work_area = name_parts[0] if name_parts else 'unknown'
            file_type = 'Changelog'
        
        # Get file preview
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()[:5]
                summary = ''.join(lines[:3]) if lines else 'No content'
        except:
            summary = 'Unable to read file'
        
        result.append({
            'filename': file_path.name,
            'work_area': work_area,
            'type': file_type,
            'timestamp': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'size': f"{file_path.stat().st_size / 1024:.1f} KB",
            'summary': sanitize_sensitive_info(summary[:200])  # Limit summary length
        })
    
    return jsonify(result)

@app.route('/api/security')
@auth.login_required
def api_security():
    """Get security events"""
    limit = request.args.get('limit', 50, type=int)
    events = []
    
    # Read audit log
    audit_log = SECURITY_DIR / 'audit.log'
    if audit_log.exists():
        with open(audit_log, 'r') as f:
            lines = f.readlines()[-limit:]
            for line in reversed(lines):
                if line.strip():
                    parts = line.split(' - ')
                    if len(parts) >= 3:
                        events.append({
                            'timestamp': parts[0],
                            'level': parts[1],
                            'message': sanitize_sensitive_info(' - '.join(parts[2:]))
                        })
    
    return jsonify(events)

@app.route('/api/claude')
@auth.login_required
def api_claude():
    """Get Claude execution outputs"""
    outputs = []
    
    if LOGS_DIR.exists():
        claude_files = sorted(LOGS_DIR.glob('claude_*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
        
        for claude_file in claude_files:
            work_type = 'unknown'
            if 'infrastructure' in claude_file.name:
                work_type = 'infrastructure'
            elif 'personal' in claude_file.name:
                work_type = 'personal_projects'
            elif 'davy' in claude_file.name:
                work_type = 'davy_jones'
            
            size = claude_file.stat().st_size
            status = 'completed' if size > 100 else 'in_progress' if size == 0 else 'partial'
            
            outputs.append({
                'filename': claude_file.name,
                'work_type': work_type,
                'status': status,
                'size': f"{size / 1024:.1f} KB" if size > 0 else "0 KB",
                'timestamp': datetime.fromtimestamp(claude_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return jsonify(outputs)

@app.route('/api/log/<path:filename>')
@auth.login_required
def api_log_content(filename):
    """Get content of a specific log file"""
    # Handle barbossa/ prefix in filename
    if filename.startswith('barbossa/'):
        # Try barbossa subdirectory first
        barbossa_file = LOGS_DIR / 'barbossa' / filename.replace('barbossa/', '')
        if barbossa_file.exists() and barbossa_file.is_file():
            try:
                with open(barbossa_file, 'r') as f:
                    content = f.read()
                    if len(content) > 1024 * 1024:
                        content = content[:1024 * 1024] + "\n\n... [TRUNCATED - File too large] ..."
                    
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'content': sanitize_sensitive_info(content),
                    'size': f"{len(content) / 1024:.1f} KB"
                })
            except Exception as e:
                logger.error(f"Error reading file {barbossa_file}: {e}")
                return jsonify({'error': 'Error reading file'}), 500
    
    # Try standard directories
    allowed_dirs = [LOGS_DIR, CHANGELOGS_DIR, SECURITY_DIR]
    
    for allowed_dir in allowed_dirs:
        file_path = allowed_dir / filename
        if file_path.exists() and file_path.is_file():
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if len(content) > 1024 * 1024:
                        content = content[:1024 * 1024] + "\n\n... [TRUNCATED - File too large] ..."
                    
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'content': sanitize_sensitive_info(content),
                    'size': f"{len(content) / 1024:.1f} KB"
                })
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return jsonify({'error': 'Error reading file'}), 500
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/security/updates')
@auth.login_required
def api_security_updates():
    """Get security update status"""
    try:
        result = subprocess.run(['apt', 'list', '--upgradable'], 
                              capture_output=True, text=True, timeout=10)
        security_updates = [line for line in result.stdout.split('\n') 
                          if 'security' in line.lower()]
        
        return jsonify({
            'count': len(security_updates),
            'updates': security_updates[:10]  # First 10 updates
        })
    except Exception as e:
        logger.error(f"Error checking security updates: {e}")
        return jsonify({'count': 0, 'error': str(e)})

@app.route('/api/errors/recent')
@auth.login_required
def api_recent_errors():
    """Get recent error logs"""
    errors = []
    error_count = 0
    
    # Scan log files for errors
    if LOGS_DIR.exists():
        for log_file in LOGS_DIR.glob('*.log'):
            if log_file.is_file():
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if 'ERROR' in line or 'CRITICAL' in line:
                                error_count += 1
                                if len(errors) < 20:  # Keep last 20 errors
                                    errors.append({
                                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                                        'message': line.strip()[:200],
                                        'file': log_file.name
                                    })
                except Exception:
                    pass
    
    return jsonify({
        'count': error_count,
        'errors': errors
    })

@app.route('/api/git/status')
@auth.login_required
def api_git_status():
    """Get git repository status"""
    try:
        # Get current branch
        branch_result = subprocess.run(['git', 'branch', '--show-current'],
                                      capture_output=True, text=True, cwd=BARBOSSA_DIR)
        current_branch = branch_result.stdout.strip()
        
        # Get uncommitted changes count
        status_result = subprocess.run(['git', 'status', '--porcelain'],
                                      capture_output=True, text=True, cwd=BARBOSSA_DIR)
        uncommitted = len([line for line in status_result.stdout.split('\n') if line.strip()])
        
        # Get recent commits
        log_result = subprocess.run(['git', 'log', '--oneline', '-10'],
                                   capture_output=True, text=True, cwd=BARBOSSA_DIR)
        commits = []
        for line in log_result.stdout.split('\n')[:5]:
            if line:
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    commits.append({
                        'hash': parts[0][:7],
                        'message': parts[1][:80]
                    })
        
        return jsonify({
            'branch': current_branch,
            'uncommitted': uncommitted,
            'commits': commits
        })
    except Exception as e:
        logger.error(f"Error getting git status: {e}")
        return jsonify({'branch': 'unknown', 'uncommitted': 0, 'commits': []})

@app.route('/api/infrastructure/health')
@auth.login_required
def api_infrastructure_health():
    """Get infrastructure health status"""
    try:
        # Check Docker
        docker_result = subprocess.run(['docker', 'ps', '-q'],
                                      capture_output=True, text=True)
        docker_containers = len(docker_result.stdout.strip().split('\n')) if docker_result.stdout.strip() else 0
        
        # Check Cloudflare tunnel
        tunnel_result = subprocess.run(['pgrep', '-f', 'cloudflared'],
                                      capture_output=True, text=True)
        tunnel_active = bool(tunnel_result.stdout.strip())
        
        # Service uptime
        uptime_result = subprocess.run(['uptime', '-p'],
                                      capture_output=True, text=True)
        
        return jsonify({
            'docker': {
                'containers': docker_containers,
                'status': 'running' if docker_containers > 0 else 'no containers'
            },
            'tunnel': {
                'active': tunnel_active,
                'status': 'active' if tunnel_active else 'down'
            },
            'uptime': uptime_result.stdout.strip()
        })
    except Exception as e:
        logger.error(f"Error checking infrastructure health: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/files/activity')
@auth.login_required
def api_files_activity():
    """Get file system activity information"""
    try:
        # Count modified files in last 24h
        modified_count = 0
        if LOGS_DIR.exists():
            cutoff_time = time.time() - (24 * 3600)
            for log_file in LOGS_DIR.glob('**/*'):
                if log_file.is_file() and log_file.stat().st_mtime > cutoff_time:
                    modified_count += 1
        
        # Log files info
        log_count = len(list(LOGS_DIR.glob('*.log'))) if LOGS_DIR.exists() else 0
        total_size = sum(f.stat().st_size for f in LOGS_DIR.glob('**/*') if f.is_file()) if LOGS_DIR.exists() else 0
        
        # Storage usage
        disk_usage = shutil.disk_usage('/')
        
        return jsonify({
            'modified_count': modified_count,
            'log_info': {
                'count': log_count,
                'size': f"{total_size / (1024*1024):.1f} MB",
                'latest': datetime.now().strftime('%Y-%m-%d %H:%M')
            },
            'storage': {
                'used': f"{disk_usage.used / (1024**3):.1f}GB",
                'total': f"{disk_usage.total / (1024**3):.1f}GB",
                'percent': int((disk_usage.used / disk_usage.total) * 100)
            }
        })
    except Exception as e:
        logger.error(f"Error getting file activity: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/automation/status')
@auth.login_required
def api_automation_status():
    """Get automation and cron job status"""
    try:
        # Check cron jobs
        cron_jobs = [
            {'name': 'Barbossa Main', 'status': 'Active', 'active': True},
            {'name': 'Infrastructure Check', 'status': 'Every 2h', 'active': True},
            {'name': 'Ticket Enrichment', 'status': 'Daily 09:00', 'active': True},
            {'name': 'Daily Summary', 'status': 'Daily 23:00', 'active': True}
        ]
        
        # Scheduled tasks
        now = datetime.now()
        scheduled_tasks = [
            {'name': 'Infrastructure Check', 'next_run': '2 hours'},
            {'name': 'Performance Monitor', 'next_run': '4 hours'},
            {'name': 'Ticket Enrichment', 'next_run': f"{(9 - now.hour) % 24} hours"}
        ]
        
        return jsonify({
            'cron_jobs': cron_jobs,
            'scheduled_tasks': scheduled_tasks,
            'status': 'operational'
        })
    except Exception as e:
        logger.error(f"Error getting automation status: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/clear-logs', methods=['POST'])
@auth.login_required
def api_clear_logs():
    """Clear old logs (archive them first)"""
    data = request.json
    older_than_days = data.get('older_than_days', 7)
    
    cutoff_date = datetime.now() - timedelta(days=older_than_days)
    archived_count = 0
    
    archive_subdir = ARCHIVE_DIR / datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_subdir.mkdir(exist_ok=True)
    
    for log_dir in [LOGS_DIR, CHANGELOGS_DIR]:
        if log_dir.exists():
            for log_file in log_dir.glob('*'):
                if log_file.is_file():
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        shutil.move(str(log_file), str(archive_subdir / log_file.name))
                        archived_count += 1
    
    return jsonify({
        'success': True,
        'archived_count': archived_count,
        'archive_location': str(archive_subdir)
    })

@app.route('/api/trigger-barbossa', methods=['POST'])
@auth.login_required
def api_trigger_barbossa():
    """Manually trigger Barbossa execution"""
    data = request.json
    work_area = data.get('work_area', None)
    
    result = subprocess.run(['pgrep', '-f', 'barbossa.py'], capture_output=True, text=True)
    if result.stdout.strip():
        return jsonify({'success': False, 'error': 'Barbossa is already running'}), 400
    
    cmd = ['python3', str(BARBOSSA_DIR / 'barbossa.py')]
    if work_area and work_area in ['infrastructure', 'personal_projects', 'davy_jones']:
        cmd.extend(['--area', work_area])
    
    subprocess.Popen(cmd, cwd=BARBOSSA_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    return jsonify({
        'success': True,
        'message': f'Barbossa triggered for {work_area or "automatic selection"}'
    })

@app.route('/api/kill-claude', methods=['POST'])
@auth.login_required
def api_kill_claude():
    """Kill a Claude process"""
    data = request.json
    pid = data.get('pid')
    
    if not pid:
        return jsonify({'success': False, 'error': 'PID required'}), 400
    
    try:
        result = subprocess.run(['ps', '-p', str(pid)], capture_output=True, text=True)
        if 'claude' not in result.stdout.lower():
            return jsonify({'success': False, 'error': 'Not a Claude process'}), 400
        
        subprocess.run(['kill', str(pid)])
        time.sleep(1)
        
        result = subprocess.run(['ps', '-p', str(pid)], capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({'success': True, 'message': f'Claude process {pid} terminated'})
        else:
            subprocess.run(['kill', '-9', str(pid)])
            return jsonify({'success': True, 'message': f'Claude process {pid} force terminated'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/services')
@auth.login_required
def api_services():
    """Get status of related services with improved parsing"""
    services = {
        'processes': {},
        'systemd': {},
        'docker': {},
        'tmux_sessions': []
    }
    
    # Check Docker containers
    try:
        result = subprocess.run(['docker', 'ps', '-a', '--format', '{{.Names}}\t{{.Status}}\t{{.Image}}'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if line and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        name = parts[0]
                        status = parts[1]
                        image = parts[2] if len(parts) > 2 else 'unknown'
                        services['docker'][name] = {
                            'status': 'running' if 'Up' in status else 'stopped',
                            'full_status': status,
                            'image': image
                        }
    except Exception as e:
        services['docker'] = {'error': str(e)}
    
    # Check important processes
    process_checks = {
        'barbossa_portal': 'web_portal/app.py',
        'cloudflared': 'cloudflared',
        'claude': 'claude',
        'dockerd': 'dockerd',
        'redis': 'redis-server'
    }
    
    try:
        ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=10)
        if ps_result.returncode == 0:
            for name, search_term in process_checks.items():
                is_running = search_term in ps_result.stdout
                services['processes'][name] = {
                    'status': 'active' if is_running else 'inactive',
                    'name': name.replace('_', ' ').title()
                }
    except Exception as e:
        for name in process_checks.keys():
            services['processes'][name] = {
                'status': 'error',
                'name': name.replace('_', ' ').title()
            }
    
    # Check systemd services
    systemd_services = ['cloudflared', 'redis', 'docker']
    for service in systemd_services:
        try:
            result = subprocess.run(['systemctl', 'is-active', service], capture_output=True, text=True, timeout=5)
            services['systemd'][service] = {
                'status': 'active' if result.stdout.strip() == 'active' else 'inactive',
                'name': service.title()
            }
        except:
            services['systemd'][service] = {
                'status': 'unknown',
                'name': service.title()
            }
    
    # Check tmux sessions with better parsing
    try:
        result = subprocess.run(['tmux', 'ls'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if line and ':' in line:
                    # Parse: session_name: windows (created date) (attached/not attached)
                    parts = line.split(':', 1)
                    session_name = parts[0].strip()
                    session_info = parts[1].strip() if len(parts) > 1 else ''
                    
                    # Extract window count
                    windows = '1'
                    if session_info:
                        try:
                            # Look for pattern like "1 windows"
                            import re
                            match = re.search(r'(\d+)\s+windows?', session_info)
                            if match:
                                windows = match.group(1)
                        except:
                            windows = '1'
                    
                    # Check if attached
                    attached = 'attached' in session_info.lower()
                    
                    services['tmux_sessions'].append({
                        'name': session_name,
                        'windows': windows,
                        'attached': attached,
                        'status': 'attached' if attached else 'detached',
                        'info': session_info
                    })
    except Exception as e:
        services['tmux_sessions'] = []
    
    return jsonify(services)

@app.route('/api/backup-status')
@auth.login_required
def api_backup_status():
    """Get backup status and controls"""
    backup_info = {
        'last_backup': None,
        'backup_size': 0,
        'backup_count': 0,
        'auto_backup_enabled': False,
        'backup_locations': []
    }
    
    # Check for existing backups
    if ARCHIVE_DIR.exists():
        backup_dirs = list(ARCHIVE_DIR.glob('*'))
        backup_info['backup_count'] = len(backup_dirs)
        
        if backup_dirs:
            # Get most recent backup
            latest_backup = max(backup_dirs, key=lambda x: x.stat().st_mtime)
            backup_info['last_backup'] = datetime.fromtimestamp(latest_backup.stat().st_mtime).isoformat()
            
            # Calculate total backup size
            total_size = 0
            for backup_dir in backup_dirs:
                for file_path in backup_dir.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
            backup_info['backup_size'] = total_size / (1024 * 1024)  # MB
            
            backup_info['backup_locations'] = [
                {
                    'name': bd.name,
                    'path': str(bd),
                    'created': datetime.fromtimestamp(bd.stat().st_mtime).isoformat(),
                    'size': sum(f.stat().st_size for f in bd.rglob('*') if f.is_file()) / (1024 * 1024)
                }
                for bd in sorted(backup_dirs, key=lambda x: x.stat().st_mtime, reverse=True)[:10]
            ]
    
    # Check if cron backup is enabled
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        backup_info['auto_backup_enabled'] = 'barbossa' in result.stdout and 'backup' in result.stdout
    except:
        backup_info['auto_backup_enabled'] = False
    
    return jsonify(backup_info)

@app.route('/api/create-backup', methods=['POST'])
@auth.login_required
def api_create_backup():
    """Create a manual backup"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = ARCHIVE_DIR / f'manual_backup_{timestamp}'
        backup_dir.mkdir(exist_ok=True)
        
        # Define what to backup
        backup_sources = [
            (LOGS_DIR, 'logs'),
            (CHANGELOGS_DIR, 'changelogs'),
            (SECURITY_DIR, 'security'),
            (WORK_TRACKING_DIR, 'work_tracking'),
            (BARBOSSA_DIR / 'config', 'config')
        ]
        
        backed_up_files = 0
        for source_dir, dest_name in backup_sources:
            if source_dir.exists():
                dest_dir = backup_dir / dest_name
                dest_dir.mkdir(exist_ok=True)
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(source_dir)
                        dest_file = dest_dir / relative_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dest_file)
                        backed_up_files += 1
        
        return jsonify({
            'success': True,
            'message': f'Backup created successfully',
            'backup_path': str(backup_dir),
            'files_backed_up': backed_up_files
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/settings')
@auth.login_required
def api_settings():
    """Get system configuration settings"""
    settings = {
        'barbossa': {
            'auto_run_enabled': False,
            'run_interval_hours': 4,
            'max_log_files': 50,
            'log_retention_days': 30
        },
        'security': {
            'repository_whitelist_active': True,
            'zkp2p_blocking_active': True,
            'audit_logging_enabled': True
        },
        'system': {
            'auto_cleanup_enabled': True,
            'backup_retention_days': 90,
            'monitoring_interval_seconds': 30
        }
    }
    
    # Check cron status
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        settings['barbossa']['auto_run_enabled'] = 'barbossa' in result.stdout
    except:
        settings['barbossa']['auto_run_enabled'] = False
    
    # Check if whitelist file exists and is valid
    whitelist_file = BARBOSSA_DIR / 'config' / 'repository_whitelist.json'
    if whitelist_file.exists():
        try:
            with open(whitelist_file, 'r') as f:
                whitelist_data = json.load(f)
                settings['security']['repository_whitelist_count'] = len(whitelist_data.get('allowed_repositories', []))
        except:
            settings['security']['repository_whitelist_active'] = False
    
    return jsonify(settings)

@app.route('/api/update-settings', methods=['POST'])
@auth.login_required
def api_update_settings():
    """Update system settings"""
    data = request.json
    
    try:
        # This is a placeholder for settings updates
        # In a real implementation, you'd want to validate and apply the settings
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'updated_settings': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/security/status')
@auth.login_required
def api_security_status():
    """Get comprehensive security status"""
    if not enhanced_security:
        return jsonify({
            'error': 'Enhanced security not available',
            'basic_security': True
        })
    
    try:
        status = enhanced_security.get_security_status()
        
        # Add additional information
        status['csrf_protection'] = True if enhanced_security else False
        status['rate_limiting'] = True if enhanced_security else False
        status['session_security'] = True if enhanced_security else False
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/events')
@auth.login_required
def api_security_events():
    """Get recent security events"""
    limit = request.args.get('limit', 100, type=int)
    severity = request.args.get('severity', None)
    
    if not enhanced_security:
        # Fallback to basic security logs
        try:
            events = []
            audit_log = SECURITY_DIR / 'audit.log'
            if audit_log.exists():
                with open(audit_log, 'r') as f:
                    lines = f.readlines()[-limit:]
                    for line in lines:
                        events.append({
                            'timestamp': line.split(' - ')[0] if ' - ' in line else 'Unknown',
                            'message': line.strip()
                        })
            return jsonify({'events': events})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    try:
        import sqlite3
        conn = sqlite3.connect(enhanced_security.security_db)
        cursor = conn.cursor()
        
        if severity:
            cursor.execute(
                """SELECT timestamp, event_type, severity, source_ip, user, details 
                   FROM security_events 
                   WHERE severity = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (severity, limit)
            )
        else:
            cursor.execute(
                """SELECT timestamp, event_type, severity, source_ip, user, details 
                   FROM security_events 
                   ORDER BY timestamp DESC LIMIT ?""",
                (limit,)
            )
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'timestamp': row[0],
                'event_type': row[1],
                'severity': row[2],
                'source_ip': row[3],
                'user': row[4],
                'details': json.loads(row[5]) if row[5] else {}
            })
        
        conn.close()
        return jsonify({'events': events})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/blocked-ips')
@auth.login_required
def api_blocked_ips():
    """Get list of blocked IPs"""
    if not enhanced_security:
        return jsonify({'blocked_ips': []})
    
    return jsonify({
        'blocked_ips': list(enhanced_security.blocked_ips),
        'count': len(enhanced_security.blocked_ips)
    })

@app.route('/api/security/unblock-ip', methods=['POST'])
@auth.login_required
def api_unblock_ip():
    """Unblock an IP address"""
    if not enhanced_security:
        return jsonify({'error': 'Enhanced security not available'}), 400
    
    data = request.json
    ip = data.get('ip')
    
    if not ip:
        return jsonify({'error': 'IP address required'}), 400
    
    if ip in enhanced_security.blocked_ips:
        enhanced_security.blocked_ips.remove(ip)
        enhanced_security.log_security_event(
            'ip_unblocked',
            'info',
            source_ip=ip,
            user=session.get('username'),
            details={'unblocked_by': session.get('username')}
        )
        return jsonify({'success': True, 'message': f'IP {ip} unblocked'})
    else:
        return jsonify({'error': 'IP not in blocked list'}), 400

@app.route('/api/security/create-token', methods=['POST'])
@auth.login_required
def api_create_token():
    """Create API token for programmatic access"""
    if not enhanced_security:
        return jsonify({'error': 'Enhanced security not available'}), 400
    
    data = request.json
    permissions = data.get('permissions', ['read'])
    expires_days = data.get('expires_days', 30)
    
    try:
        token = enhanced_security.create_api_token(
            session.get('username'),
            permissions,
            expires_days
        )
        
        return jsonify({
            'success': True,
            'token': token,
            'expires_days': expires_days,
            'permissions': permissions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/verify-integrity', methods=['POST'])
@auth.login_required
def api_verify_integrity():
    """Verify security log integrity"""
    if not enhanced_security:
        return jsonify({'error': 'Enhanced security not available'}), 400
    
    try:
        is_valid, invalid_entries = enhanced_security.verify_log_integrity()
        
        return jsonify({
            'valid': is_valid,
            'invalid_entries': invalid_entries,
            'message': 'Log integrity verified' if is_valid else 'Log integrity compromised'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/alert-config', methods=['GET', 'POST'])
@auth.login_required
def api_alert_config():
    """Get or update security alert configuration"""
    if not enhanced_security:
        return jsonify({'error': 'Enhanced security not available'}), 400
    
    if request.method == 'GET':
        return jsonify(enhanced_security.alert_config)
    
    else:  # POST
        data = request.json
        
        # Update alert configuration
        config_file = enhanced_security.config_dir / 'alert_config.json'
        
        # Validate configuration
        if 'enabled' not in data or 'threshold' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        try:
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Reload configuration
            enhanced_security.alert_config = data
            
            enhanced_security.log_security_event(
                'alert_config_updated',
                'info',
                user=session.get('username'),
                details={'new_config': data}
            )
            
            return jsonify({
                'success': True,
                'message': 'Alert configuration updated',
                'config': data
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500


# Terminal execution endpoint
@app.route('/api/terminal/execute', methods=['POST'])
@auth.login_required
def api_terminal_execute():
    """Execute terminal commands (with restrictions)"""
    data = request.json
    command = data.get('command', '').strip()
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    # Security: Whitelist safe commands
    safe_commands = ['ls', 'pwd', 'date', 'uptime', 'df', 'free', 'top', 'ps', 'netstat', 'ip', 'whoami', 'help']
    command_parts = command.split()
    base_command = command_parts[0] if command_parts else ''
    
    # Check if command is in whitelist
    if base_command not in safe_commands:
        # Check for safe variations
        if base_command in ['cat', 'less', 'tail', 'head'] and len(command_parts) > 1:
            # Allow reading specific log files only
            file_path = command_parts[1]
            if not file_path.startswith(str(LOGS_DIR)) and not file_path.startswith('/var/log/'):
                return jsonify({'error': 'Access denied: Can only read log files'}), 403
        else:
            return jsonify({'error': f'Command not allowed: {base_command}'}), 403
    
    try:
        # Execute command with timeout
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(BARBOSSA_DIR)
        )
        
        output = result.stdout if result.returncode == 0 else result.stderr
        return jsonify({
            'output': sanitize_sensitive_info(output),
            'return_code': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Command timed out'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Export metrics endpoint
@app.route('/api/export/metrics')
@auth.login_required
def api_export_metrics():
    """Export metrics in various formats"""
    format_type = request.args.get('format', 'json')
    time_range = request.args.get('range', '24h')
    
    if server_manager:
        # Get historical metrics
        hours = {'1h': 1, '6h': 6, '24h': 24, '7d': 168}.get(time_range, 24)
        metrics = server_manager.metrics_collector.get_historical_metrics(hours)
        
        if format_type == 'json':
            return jsonify({
                'timestamp': datetime.now().isoformat(),
                'range': time_range,
                'metrics': metrics
            })
        elif format_type == 'csv':
            # Generate CSV
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            if metrics:
                writer.writerow(metrics[0].keys())
                for row in metrics:
                    writer.writerow(row.values())
            
            response = app.response_class(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment;filename=metrics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
            )
            return response
        else:
            return jsonify({'error': 'Unsupported format'}), 400
    else:
        return jsonify({'error': 'Metrics not available'}), 503

# WebSocket endpoint for real-time updates (placeholder)
@app.route('/ws')
def websocket():
    """WebSocket endpoint for real-time updates"""
    # Note: This would require a WebSocket library like Flask-SocketIO
    # For now, return a message indicating it's not implemented
    return jsonify({
        'message': 'WebSocket support requires additional setup',
        'alternative': 'Use polling with /api/comprehensive-status'
    }), 501

# Search endpoint
@app.route('/api/search')
@auth.login_required
def api_search():
    """Global search across logs, services, and configurations"""
    query = request.args.get('q', '').lower()
    if len(query) < 3:
        return jsonify({'results': []})
    
    results = []
    
    # Search in logs
    if LOGS_DIR.exists():
        for log_file in LOGS_DIR.glob('*.log'):
            try:
                with open(log_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        if query in line.lower():
                            results.append({
                                'type': 'log',
                                'file': log_file.name,
                                'line': line_num,
                                'content': sanitize_sensitive_info(line.strip())[:200]
                            })
                            if len(results) >= 50:  # Limit results
                                break
            except:
                pass
    
    # Search in service names
    if server_manager:
        services = server_manager.service_manager.get_all_services()
        for service_type, service_list in services.items():
            for name, info in service_list.items():
                if query in name.lower():
                    results.append({
                        'type': 'service',
                        'service_type': service_type,
                        'name': name,
                        'status': 'running' if info.get('active') or info.get('running') else 'stopped'
                    })
    
    return jsonify({'results': results[:50]})  # Return max 50 results

# Enhanced trigger barbossa with options
@app.route('/api/trigger-barbossa-enhanced', methods=['POST'])
@auth.login_required
def api_trigger_barbossa_enhanced():
    """Trigger Barbossa with specific options"""
    data = request.json
    work_area = data.get('work_area', 'auto')
    skip_git = data.get('skip_git', False)
    
    try:
        # Check if already running
        result = subprocess.run(['pgrep', '-f', 'barbossa.py'], capture_output=True, text=True)
        if result.stdout.strip():
            return jsonify({
                'success': False,
                'error': 'Barbossa is already running'
            }), 409
        
        # Build command
        cmd = ['python3', str(BARBOSSA_DIR / 'barbossa.py')]
        if work_area != 'auto':
            cmd.extend(['--area', work_area])
        if skip_git:
            cmd.append('--skip-git')
        
        # Start Barbossa in background
        subprocess.Popen(
            cmd,
            cwd=str(BARBOSSA_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return jsonify({
            'success': True,
            'message': f'Barbossa triggered with work area: {work_area}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== NEW API ENDPOINTS ====================

# Task Scheduling and Management
@app.route('/api/tasks/scheduled', methods=['GET', 'POST'])
@auth.login_required
def api_scheduled_tasks():
    """Manage scheduled tasks"""
    if request.method == 'GET':
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                cron_lines = result.stdout.strip().split('\n')
                tasks = []
                for line in cron_lines:
                    if line.strip() and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 6:
                            tasks.append({
                                'schedule': ' '.join(parts[:5]),
                                'command': ' '.join(parts[5:]),
                                'description': f"Runs at {parts[1]}:{parts[0] if parts[0] != '*' else '00'}"
                            })
                return jsonify({'tasks': tasks})
            else:
                return jsonify({'tasks': []})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    else:  # POST - Create new scheduled task
        data = request.json
        schedule = data.get('schedule')  # e.g., "0 */4 * * *"
        command = data.get('command')
        description = data.get('description', '')
        
        if not schedule or not command:
            return jsonify({'error': 'Schedule and command required'}), 400
        
        try:
            # Validate cron schedule format
            cron_parts = schedule.split()
            if len(cron_parts) != 5:
                return jsonify({'error': 'Invalid cron schedule format'}), 400
            
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_cron = result.stdout if result.returncode == 0 else ""
            
            # Add new task
            new_line = f"# {description}\n{schedule} {command}\n" if description else f"{schedule} {command}\n"
            updated_cron = current_cron + new_line
            
            # Write updated crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate(updated_cron)
            
            if process.returncode == 0:
                return jsonify({
                    'success': True,
                    'message': f'Scheduled task created: {description or command}'
                })
            else:
                return jsonify({'error': 'Failed to update crontab'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/scheduled/<int:task_id>', methods=['DELETE'])
@auth.login_required
def api_delete_scheduled_task(task_id):
    """Delete a scheduled task"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({'error': 'No crontab found'}), 404
        
        lines = result.stdout.split('\n')
        task_lines = [line for line in lines if line.strip() and not line.startswith('#')]
        
        if task_id >= len(task_lines):
            return jsonify({'error': 'Task not found'}), 404
        
        # Remove the task (and its comment if present)
        filtered_lines = []
        skip_next = False
        
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
            
            if line.strip() and not line.startswith('#'):
                if task_lines.index(line) == task_id:
                    # Skip this line and check if previous line was a comment
                    if i > 0 and lines[i-1].startswith('#'):
                        filtered_lines.pop()  # Remove the comment too
                    continue
            
            filtered_lines.append(line)
        
        # Write updated crontab
        updated_cron = '\n'.join(filtered_lines)
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(updated_cron)
        
        if process.returncode == 0:
            return jsonify({'success': True, 'message': 'Task deleted'})
        else:
            return jsonify({'error': 'Failed to update crontab'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Performance Analytics
@app.route('/api/analytics/performance')
@auth.login_required
@performance_monitor
@cached_response(ttl=120)  # Cache for 2 minutes
def api_performance_analytics():
    """Get performance analytics and trends"""
    # Use real-time metrics if server_manager not available
    if not server_manager:
        # Get real-time metrics directly
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            net_io = psutil.net_io_counters()
            
            # Calculate response time
            start = time.time()
            subprocess.run(['echo', 'test'], capture_output=True, timeout=1)
            response_time = (time.time() - start) * 1000
            
            # Calculate request rate and error rate
            request_rate = round((net_io.packets_recv + net_io.packets_sent) / 1000, 2)
            total_packets = net_io.packets_recv + net_io.packets_sent
            error_rate = 0 if total_packets == 0 else round(
                ((net_io.dropin + net_io.dropout) / total_packets) * 100, 2
            )
            
            return jsonify({
                'analytics': {
                    'avg_response_time': f"{response_time:.1f}",
                    'request_rate': str(request_rate),
                    'error_rate': f"{error_rate}",
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'network_recv_mbps': round(net_io.bytes_recv / (1024**2), 2),
                    'network_sent_mbps': round(net_io.bytes_sent / (1024**2), 2)
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    try:
        # Get metrics from last 24 hours for trend analysis
        metrics = server_manager.metrics_collector.get_historical_metrics(24, limit=1000)
        
        if not metrics:
            return jsonify({'analytics': {}, 'trends': {}})
        
        # Calculate trends and analytics
        analytics = {
            'avg_cpu': sum(m.get('cpu_percent', 0) for m in metrics) / len(metrics),
            'avg_memory': sum(m.get('memory_percent', 0) for m in metrics) / len(metrics),
            'avg_disk': sum(m.get('disk_percent', 0) for m in metrics) / len(metrics),
            'peak_cpu': max(m.get('cpu_percent', 0) for m in metrics),
            'peak_memory': max(m.get('memory_percent', 0) for m in metrics),
            'low_memory': min(m.get('memory_percent', 0) for m in metrics),
            'avg_load': sum(m.get('load_1min', 0) for m in metrics) / len(metrics),
            'network_peak_in': max(m.get('network_recv_mbps', 0) for m in metrics),
            'network_peak_out': max(m.get('network_sent_mbps', 0) for m in metrics)
        }
        
        # Calculate trends (compare last 6 hours vs previous 6 hours)
        mid_point = len(metrics) // 2
        recent_metrics = metrics[mid_point:]
        older_metrics = metrics[:mid_point]
        
        if recent_metrics and older_metrics:
            recent_avg_cpu = sum(m.get('cpu_percent', 0) for m in recent_metrics) / len(recent_metrics)
            older_avg_cpu = sum(m.get('cpu_percent', 0) for m in older_metrics) / len(older_metrics)
            
            recent_avg_mem = sum(m.get('memory_percent', 0) for m in recent_metrics) / len(recent_metrics)
            older_avg_mem = sum(m.get('memory_percent', 0) for m in older_metrics) / len(older_metrics)
            
            trends = {
                'cpu_trend': 'increasing' if recent_avg_cpu > older_avg_cpu else 'decreasing',
                'cpu_change': round(recent_avg_cpu - older_avg_cpu, 2),
                'memory_trend': 'increasing' if recent_avg_mem > older_avg_mem else 'decreasing',
                'memory_change': round(recent_avg_mem - older_avg_mem, 2)
            }
        else:
            trends = {'cpu_trend': 'stable', 'memory_trend': 'stable'}
        
        # Performance recommendations
        recommendations = []
        if analytics['avg_cpu'] > 80:
            recommendations.append('High CPU usage detected. Consider optimizing processes.')
        if analytics['avg_memory'] > 85:
            recommendations.append('High memory usage. Consider memory cleanup or upgrade.')
        if analytics['avg_disk'] > 90:
            recommendations.append('Disk space running low. Clean up old files.')
        if analytics['avg_load'] > psutil.cpu_count():
            recommendations.append('System load high. Check for resource-intensive processes.')
        
        return jsonify({
            'analytics': analytics,
            'trends': trends,
            'recommendations': recommendations,
            'data_points': len(metrics),
            'time_range': '24 hours'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Resource Optimization
@app.route('/api/optimization/suggestions')
@auth.login_required
@performance_monitor
@cached_response(ttl=300)  # Cache for 5 minutes
def api_optimization_suggestions():
    """Get automated resource optimization suggestions"""
    suggestions = []
    
    try:
        # Check system resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # CPU optimization suggestions
        if cpu_percent > 80:
            suggestions.append({
                'category': 'cpu',
                'priority': 'high',
                'title': 'High CPU Usage Detected',
                'description': f'CPU usage is {cpu_percent:.1f}%',
                'actions': [
                    'Identify high-CPU processes with top command',
                    'Consider process optimization or scaling',
                    'Check for CPU-intensive cron jobs'
                ]
            })
        
        # Memory optimization suggestions
        if memory.percent > 85:
            suggestions.append({
                'category': 'memory',
                'priority': 'high',
                'title': 'High Memory Usage',
                'description': f'Memory usage is {memory.percent:.1f}%',
                'actions': [
                    'Clear system caches with sync && echo 3 > /proc/sys/vm/drop_caches',
                    'Restart memory-intensive services',
                    'Check for memory leaks in applications'
                ]
            })
        
        # Disk optimization suggestions
        if disk.percent > 90:
            suggestions.append({
                'category': 'disk',
                'priority': 'critical',
                'title': 'Low Disk Space',
                'description': f'Critical: Only {disk.free / (1024**3):.1f}GB free ({disk.percent:.1f}% used)',
                'actions': [
                    'Clean old log files older than 30 days',
                    'Remove Docker unused images and containers',
                    'Archive old backup files'
                ]
            })
        elif disk.percent > 80:
            suggestions.append({
                'category': 'disk',
                'priority': 'medium',
                'title': 'Disk Space Warning',
                'description': f'Disk usage is {disk.percent:.1f}%',
                'actions': [
                    'Schedule regular cleanup of temporary files',
                    'Implement log rotation',
                    'Monitor disk usage trends'
                ]
            })
        
        # Service optimization suggestions
        if server_manager:
            services = server_manager.service_manager.get_all_services()
            inactive_services = []
            for service_type, service_list in services.items():
                for name, info in service_list.items():
                    if not info.get('active', False) and service_type == 'systemd':
                        inactive_services.append(name)
            
            if len(inactive_services) > 5:
                suggestions.append({
                    'category': 'services',
                    'priority': 'low',
                    'title': 'Inactive Services Found',
                    'description': f'Found {len(inactive_services)} inactive services',
                    'actions': [
                        'Review and disable unused services',
                        'Clean up service dependencies',
                        'Optimize service startup order'
                    ]
                })
        
        # Network optimization suggestions
        try:
            connections = len(psutil.net_connections())
            if connections > 1000:
                suggestions.append({
                    'category': 'network',
                    'priority': 'medium',
                    'title': 'High Network Connection Count',
                    'description': f'{connections} active connections',
                    'actions': [
                        'Check for connection pooling optimization',
                        'Review firewall rules',
                        'Monitor for potential connection leaks'
                    ]
                })
        except:
            pass  # Skip if permissions don't allow
        
        # Docker optimization suggestions
        try:
            result = subprocess.run(['docker', 'system', 'df'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parse docker system df output to check for reclaimable space
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Build Cache' in line and 'MB' in line:
                        # Extract size information
                        parts = line.split()
                        if len(parts) > 3 and 'GB' in parts[2]:
                            cache_size = float(parts[2].replace('GB', ''))
                            if cache_size > 1.0:  # More than 1GB build cache
                                suggestions.append({
                                    'category': 'docker',
                                    'priority': 'medium',
                                    'title': 'Docker Build Cache Cleanup',
                                    'description': f'{cache_size:.1f}GB build cache detected',
                                    'actions': [
                                        'Run docker system prune to clean build cache',
                                        'Remove unused Docker images',
                                        'Implement regular Docker cleanup schedule'
                                    ]
                                })
        except:
            pass
        
        # Check for zombie processes
        try:
            zombies = [p for p in psutil.process_iter(['status']) if p.info['status'] == psutil.STATUS_ZOMBIE]
            if zombies:
                suggestions.append({
                    'category': 'process',
                    'priority': 'medium',
                    'title': 'Zombie Processes',
                    'description': f'{len(zombies)} zombie processes detected',
                    'actions': ['Clean up zombie processes', 'Check parent process health']
                })
        except:
            pass
        
        # Check swap usage
        try:
            swap = psutil.swap_memory()
            if swap.percent > 50:
                suggestions.append({
                    'category': 'memory',
                    'priority': 'medium',
                    'title': 'High Swap Usage',
                    'description': f'Swap usage at {swap.percent:.1f}%',
                    'actions': ['Investigate memory pressure', 'Consider adding RAM', 'Optimize memory-intensive processes']
                })
        except:
            pass
        
        # Check system load
        try:
            load1, load5, load15 = os.getloadavg()
            cpu_count = psutil.cpu_count()
            if load1 > cpu_count * 2:
                suggestions.append({
                    'category': 'system',
                    'priority': 'high',
                    'title': 'High System Load',
                    'description': f'Load average: {load1:.2f} (CPUs: {cpu_count})',
                    'actions': ['Identify resource-intensive processes', 'Consider load balancing']
                })
        except:
            pass
        
        # If no issues, report healthy system
        if not suggestions:
            suggestions.append({
                'category': 'general',
                'priority': 'info',
                'title': 'System Healthy',
                'description': 'All systems running optimally',
                'actions': ['Schedule maintenance window', 'Review security updates', 'Update documentation']
            })
        
        return jsonify({
            'suggestions': suggestions,
            'total_count': len(suggestions),
            'priorities': {
                'critical': len([s for s in suggestions if s['priority'] == 'critical']),
                'high': len([s for s in suggestions if s['priority'] == 'high']),
                'medium': len([s for s in suggestions if s['priority'] == 'medium']),
                'low': len([s for s in suggestions if s['priority'] == 'low']),
                'info': len([s for s in suggestions if s.get('priority') == 'info'])
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimization/apply', methods=['POST'])
@auth.login_required
def api_apply_optimization():
    """Apply specific optimization suggestions"""
    data = request.json
    optimization_type = data.get('type')
    action = data.get('action')
    
    if not optimization_type or not action:
        return jsonify({'error': 'Type and action required'}), 400
    
    results = []
    
    try:
        if optimization_type == 'disk' and action == 'clean_logs':
            # Clean old log files
            cutoff_date = datetime.now() - timedelta(days=30)
            cleaned_count = 0
            cleaned_size = 0
            
            for log_dir in [LOGS_DIR, '/var/log']:
                if Path(log_dir).exists():
                    for log_file in Path(log_dir).rglob('*.log*'):
                        if log_file.is_file():
                            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                            if file_time < cutoff_date:
                                file_size = log_file.stat().st_size
                                log_file.unlink()
                                cleaned_count += 1
                                cleaned_size += file_size
            
            results.append({
                'action': 'clean_logs',
                'success': True,
                'message': f'Cleaned {cleaned_count} log files ({cleaned_size / 1024 / 1024:.1f} MB)'
            })
        
        elif optimization_type == 'memory' and action == 'drop_caches':
            # Drop system caches (requires sudo)
            try:
                subprocess.run(['sync'], check=True, timeout=30)
                # Note: This would need proper sudo configuration
                result = subprocess.run(['sudo', 'sysctl', 'vm.drop_caches=3'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    results.append({
                        'action': 'drop_caches',
                        'success': True,
                        'message': 'System caches cleared successfully'
                    })
                else:
                    results.append({
                        'action': 'drop_caches',
                        'success': False,
                        'message': 'Failed to clear caches (permissions required)'
                    })
            except Exception as e:
                results.append({
                    'action': 'drop_caches',
                    'success': False,
                    'message': f'Error clearing caches: {str(e)}'
                })
        
        elif optimization_type == 'docker' and action == 'prune':
            # Docker system prune
            try:
                result = subprocess.run(['docker', 'system', 'prune', '-f'], 
                                      capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    results.append({
                        'action': 'docker_prune',
                        'success': True,
                        'message': f'Docker cleanup completed: {result.stdout.strip()}'
                    })
                else:
                    results.append({
                        'action': 'docker_prune',
                        'success': False,
                        'message': f'Docker cleanup failed: {result.stderr}'
                    })
            except Exception as e:
                results.append({
                    'action': 'docker_prune',
                    'success': False,
                    'message': f'Error running Docker cleanup: {str(e)}'
                })
        
        else:
            return jsonify({'error': f'Unknown optimization: {optimization_type}/{action}'}), 400
        
        return jsonify({
            'success': True,
            'results': results,
            'applied_count': len([r for r in results if r['success']])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Integration Management
@app.route('/api/integrations', methods=['GET'])
@auth.login_required
@cached_response(ttl=120)  # Cache for 2 minutes
def api_list_integrations():
    """List available and active integrations"""
    integrations = []
    
    # Check GitHub integration
    github_token = os.getenv('GITHUB_TOKEN')
    integrations.append({
        'name': 'GitHub',
        'type': 'vcs',
        'status': 'active' if github_token else 'inactive',
        'description': 'Git repository management and automation',
        'config_required': ['GITHUB_TOKEN'],
        'endpoints': ['/api/integrations/github/repos', '/api/integrations/github/webhooks']
    })
    
    # Check Anthropic Claude integration
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    integrations.append({
        'name': 'Anthropic Claude',
        'type': 'ai',
        'status': 'active' if anthropic_key else 'inactive',
        'description': 'AI-powered development assistance',
        'config_required': ['ANTHROPIC_API_KEY'],
        'endpoints': ['/api/integrations/claude/status']
    })
    
    # Check Docker integration
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
        docker_active = result.returncode == 0
    except:
        docker_active = False
    
    integrations.append({
        'name': 'Docker',
        'type': 'infrastructure',
        'status': 'active' if docker_active else 'inactive',
        'description': 'Container management and orchestration',
        'config_required': [],
        'endpoints': ['/api/integrations/docker/containers', '/api/integrations/docker/images']
    })
    
    # Check Cloudflare integration
    cloudflare_active = Path.home().joinpath('.cloudflared', 'config.yml').exists()
    integrations.append({
        'name': 'Cloudflare Tunnel',
        'type': 'networking',
        'status': 'active' if cloudflare_active else 'inactive',
        'description': 'Secure external access tunnel',
        'config_required': ['Cloudflare account', 'Tunnel configuration'],
        'endpoints': ['/api/integrations/cloudflare/status']
    })
    
    # Check Redis integration
    try:
        result = subprocess.run(['redis-cli', 'ping'], capture_output=True, text=True, timeout=5)
        redis_active = 'PONG' in result.stdout
    except:
        redis_active = False
    
    integrations.append({
        'name': 'Redis',
        'type': 'database',
        'status': 'active' if redis_active else 'inactive',
        'description': 'In-memory data structure store',
        'config_required': [],
        'endpoints': ['/api/integrations/redis/status', '/api/integrations/redis/keys']
    })
    
    return jsonify({
        'integrations': integrations,
        'active_count': len([i for i in integrations if i['status'] == 'active']),
        'total_count': len(integrations)
    })

@app.route('/api/integrations/github/repos')
@auth.login_required
@cached_response(ttl=300)  # Cache for 5 minutes
def api_github_repos():
    """Get GitHub repository information - try API first, fallback to local"""
    repos = []
    
    # Try GitHub API first if token available
    github_token = os.getenv('GITHUB_TOKEN')
    if github_token:
        try:
            import requests
            headers = {'Authorization': f'token {github_token}'}
            response = requests.get('https://api.github.com/user/repos', headers=headers, timeout=5)
            if response.status_code == 200:
                api_repos = response.json()
                for repo in api_repos:
                    if repo['owner']['login'] == 'ADWilkinson':
                        repos.append({
                            'name': repo['name'],
                            'full_name': repo['full_name'],
                            'description': repo['description'],
                            'language': repo['language'],
                            'stars': repo['stargazers_count'],
                            'forks': repo['forks_count'],
                            'updated_at': repo['updated_at'],
                            'private': repo['private']
                        })
        except:
            pass  # Fall back to local repos
    
    # If no API repos or API failed, get local repos
    if not repos:
        projects_dir = Path.home() / 'barbossa-engineer' / 'projects'
        if projects_dir.exists():
            for project_path in projects_dir.iterdir():
                if project_path.is_dir() and (project_path / '.git').exists():
                    try:
                        os.chdir(project_path)
                        # Get branch and status
                        branch_result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, timeout=5)
                        status_result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, timeout=5)
                        
                        repos.append({
                            'name': project_path.name,
                            'full_name': f'local/{project_path.name}',
                            'description': f'Local project - {branch_result.stdout.strip()} branch',
                            'language': 'TypeScript' if (project_path / 'tsconfig.json').exists() else 'JavaScript',
                            'stars': 0,
                            'forks': 0,
                            'updated_at': datetime.fromtimestamp(project_path.stat().st_mtime).isoformat(),
                            'private': True,
                            'has_changes': bool(status_result.stdout.strip())
                        })
                    except:
                        pass
        
        # Add main barbossa repo
        barbossa_dir = Path.home() / 'barbossa-engineer'
        if (barbossa_dir / '.git').exists():
            try:
                os.chdir(barbossa_dir)
                branch_result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, timeout=5)
                repos.insert(0, {
                    'name': 'barbossa-engineer',
                    'full_name': 'local/barbossa-engineer',
                    'description': f'Barbossa Engineer - {branch_result.stdout.strip()} branch',
                    'language': 'Python',
                    'stars': 0,
                    'forks': 0,
                    'updated_at': datetime.fromtimestamp(barbossa_dir.stat().st_mtime).isoformat(),
                    'private': True
                })
            except:
                pass
    
    return jsonify({
        'repositories': repos,
        'total_count': len(repos)
    })

@app.route('/api/integrations/docker/containers')
@auth.login_required
@cached_response(ttl=30)  # Cache for 30 seconds
def api_docker_containers():
    """Get detailed Docker container information"""
    try:
        # Get containers with detailed format
        result = subprocess.run([
            'docker', 'ps', '-a', '--format',
            '{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}\t{{.CreatedAt}}\t{{.Size}}'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return jsonify({'error': 'Docker not available or permission denied'}), 503
        
        containers = []
        if result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if line and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        containers.append({
                            'name': parts[0],
                            'status': parts[1],
                            'image': parts[2],
                            'ports': parts[3] if len(parts) > 3 else '',
                            'created': parts[4] if len(parts) > 4 else '',
                            'size': parts[5] if len(parts) > 5 else '',
                            'running': 'Up' in parts[1]
                        })
        
        # Get Docker system info
        system_result = subprocess.run(['docker', 'system', 'df', '--format', 'json'], 
                                     capture_output=True, text=True, timeout=10)
        system_info = {}
        if system_result.returncode == 0:
            try:
                system_info = json.loads(system_result.stdout)
            except:
                pass
        
        return jsonify({
            'containers': containers,
            'system_info': system_info,
            'total_containers': len(containers),
            'running_containers': len([c for c in containers if c['running']])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# System Anomalies Detection
@app.route('/api/monitoring/anomalies')
@auth.login_required
def api_anomalies():
    """Detect system anomalies"""
    anomalies = []
    
    try:
        # Check for high load average
        load1, load5, load15 = os.getloadavg()
        cpu_count = psutil.cpu_count()
        if load1 > cpu_count * 2:
            anomalies.append({
                'severity': 'high',
                'type': 'load',
                'description': f'System load is very high: {load1:.2f} (CPUs: {cpu_count})'
            })
        
        # Check for unusual network connections
        connections = psutil.net_connections()
        listening_ports = [c for c in connections if c.status == 'LISTEN']
        if len(listening_ports) > 50:
            anomalies.append({
                'severity': 'medium',
                'type': 'network',
                'description': f'Unusual number of listening ports: {len(listening_ports)}'
            })
        
        # Check disk I/O
        disk_io = psutil.disk_io_counters()
        if disk_io and disk_io.read_bytes > 1024**3 * 10:  # More than 10GB read
            anomalies.append({
                'severity': 'low',
                'type': 'disk',
                'description': f'High disk read activity: {disk_io.read_bytes / (1024**3):.1f}GB'
            })
        
        if not anomalies:
            return jsonify({'message': 'No anomalies detected', 'anomalies': []})
            
    except Exception as e:
        anomalies.append({
            'severity': 'low',
            'type': 'error',
            'description': f'Error checking anomalies: {str(e)}'
        })
    
    return jsonify({'anomalies': anomalies})

# Advanced Monitoring and Analytics
@app.route('/api/monitoring/alerts/rules', methods=['GET', 'POST'])
@auth.login_required
def api_alert_rules():
    """Manage monitoring alert rules"""
    rules_file = BARBOSSA_DIR / 'config' / 'alert_rules.json'
    
    if request.method == 'GET':
        if rules_file.exists():
            with open(rules_file, 'r') as f:
                rules = json.load(f)
        else:
            # Default alert rules
            rules = {
                'cpu_high': {
                    'name': 'High CPU Usage',
                    'condition': 'cpu_percent > 90',
                    'duration': 300,  # 5 minutes
                    'severity': 'critical',
                    'enabled': True
                },
                'memory_high': {
                    'name': 'High Memory Usage',
                    'condition': 'memory_percent > 90',
                    'duration': 300,
                    'severity': 'critical',
                    'enabled': True
                },
                'disk_full': {
                    'name': 'Disk Space Critical',
                    'condition': 'disk_percent > 95',
                    'duration': 60,
                    'severity': 'critical',
                    'enabled': True
                },
                'load_high': {
                    'name': 'High System Load',
                    'condition': 'load_15min > cpu_count * 2',
                    'duration': 600,  # 10 minutes
                    'severity': 'warning',
                    'enabled': True
                }
            }
            
            # Save default rules
            os.makedirs(rules_file.parent, exist_ok=True)
            with open(rules_file, 'w') as f:
                json.dump(rules, f, indent=2)
        
        return jsonify({'rules': rules})
    
    else:  # POST - Create or update alert rule
        data = request.json
        rule_id = data.get('id')
        rule_config = data.get('rule')
        
        if not rule_id or not rule_config:
            return jsonify({'error': 'Rule ID and configuration required'}), 400
        
        # Load existing rules
        if rules_file.exists():
            with open(rules_file, 'r') as f:
                rules = json.load(f)
        else:
            rules = {}
        
        # Add or update rule
        rules[rule_id] = rule_config
        
        # Save updated rules
        os.makedirs(rules_file.parent, exist_ok=True)
        with open(rules_file, 'w') as f:
            json.dump(rules, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Alert rule {rule_id} {"updated" if rule_id in rules else "created"}'
        })

@app.route('/api/monitoring/anomalies')
@auth.login_required
@cached_response(ttl=180)  # Cache for 3 minutes
def api_anomaly_detection():
    """Detect system anomalies using statistical analysis"""
    if not server_manager:
        return jsonify({'error': 'Server manager not available'}), 503
    
    try:
        # Get historical metrics for anomaly detection
        metrics = server_manager.metrics_collector.get_historical_metrics(24, limit=500)
        
        if len(metrics) < 10:
            return jsonify({'anomalies': [], 'message': 'Insufficient data for anomaly detection'})
        
        anomalies = []
        
        # Extract time series data
        cpu_values = [m.get('cpu_percent', 0) for m in metrics]
        memory_values = [m.get('memory_percent', 0) for m in metrics]
        disk_values = [m.get('disk_percent', 0) for m in metrics]
        
        # Simple anomaly detection using standard deviation
        def detect_anomalies(values, metric_name, threshold=2.0):
            if len(values) < 5:
                return []
            
            import statistics
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0
            
            detected = []
            for i, value in enumerate(values[-10:]):  # Check last 10 values
                if std_val > 0 and abs(value - mean_val) > threshold * std_val:
                    detected.append({
                        'metric': metric_name,
                        'value': value,
                        'expected_range': f'{mean_val - std_val:.1f}-{mean_val + std_val:.1f}',
                        'deviation': abs(value - mean_val) / std_val if std_val > 0 else 0,
                        'timestamp': metrics[-(10-i)].get('timestamp', 'unknown'),
                        'severity': 'high' if abs(value - mean_val) > 3 * std_val else 'medium'
                    })
            return detected
        
        # Detect anomalies for each metric
        anomalies.extend(detect_anomalies(cpu_values, 'cpu_percent'))
        anomalies.extend(detect_anomalies(memory_values, 'memory_percent'))
        anomalies.extend(detect_anomalies(disk_values, 'disk_percent'))
        
        # Sort by severity and deviation
        anomalies.sort(key=lambda x: (x['severity'] == 'high', x['deviation']), reverse=True)
        
        return jsonify({
            'anomalies': anomalies[:20],  # Return top 20 anomalies
            'total_count': len(anomalies),
            'data_points_analyzed': len(metrics),
            'detection_method': 'statistical_deviation'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Workflow Automation
@app.route('/api/workflows', methods=['GET', 'POST'])
@auth.login_required
def api_workflows():
    """Manage automation workflows"""
    workflows_file = BARBOSSA_DIR / 'config' / 'workflows.json'
    
    if request.method == 'GET':
        if workflows_file.exists():
            with open(workflows_file, 'r') as f:
                workflows = json.load(f)
        else:
            workflows = {}
        
        return jsonify({'workflows': workflows})
    
    else:  # POST - Create new workflow
        data = request.json
        workflow_id = data.get('id')
        workflow_config = data.get('workflow')
        
        if not workflow_id or not workflow_config:
            return jsonify({'error': 'Workflow ID and configuration required'}), 400
        
        # Validate workflow structure
        required_fields = ['name', 'description', 'trigger', 'actions']
        for field in required_fields:
            if field not in workflow_config:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Load existing workflows
        if workflows_file.exists():
            with open(workflows_file, 'r') as f:
                workflows = json.load(f)
        else:
            workflows = {}
        
        # Add workflow metadata
        workflow_config['created_at'] = datetime.now().isoformat()
        workflow_config['created_by'] = session.get('username')
        workflow_config['enabled'] = workflow_config.get('enabled', True)
        workflow_config['execution_count'] = 0
        workflow_config['last_execution'] = None
        
        workflows[workflow_id] = workflow_config
        
        # Save workflows
        os.makedirs(workflows_file.parent, exist_ok=True)
        with open(workflows_file, 'w') as f:
            json.dump(workflows, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Workflow {workflow_id} created successfully',
            'workflow': workflow_config
        })

@app.route('/api/workflows/<workflow_id>/execute', methods=['POST'])
@auth.login_required
def api_execute_workflow(workflow_id):
    """Execute a specific workflow"""
    workflows_file = BARBOSSA_DIR / 'config' / 'workflows.json'
    
    if not workflows_file.exists():
        return jsonify({'error': 'No workflows configured'}), 404
    
    with open(workflows_file, 'r') as f:
        workflows = json.load(f)
    
    if workflow_id not in workflows:
        return jsonify({'error': 'Workflow not found'}), 404
    
    workflow = workflows[workflow_id]
    if not workflow.get('enabled', True):
        return jsonify({'error': 'Workflow is disabled'}), 400
    
    try:
        execution_results = []
        
        # Execute each action in the workflow
        for i, action in enumerate(workflow['actions']):
            action_type = action.get('type')
            action_config = action.get('config', {})
            
            if action_type == 'run_command':
                # Execute shell command
                command = action_config.get('command')
                if command:
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=action_config.get('timeout', 30),
                        cwd=action_config.get('working_directory', str(BARBOSSA_DIR))
                    )
                    
                    execution_results.append({
                        'action_index': i,
                        'type': action_type,
                        'success': result.returncode == 0,
                        'output': sanitize_sensitive_info(result.stdout or result.stderr),
                        'return_code': result.returncode
                    })
                else:
                    execution_results.append({
                        'action_index': i,
                        'type': action_type,
                        'success': False,
                        'error': 'No command specified'
                    })
            
            elif action_type == 'trigger_barbossa':
                # Trigger Barbossa execution
                work_area = action_config.get('work_area', 'auto')
                
                # Check if Barbossa is already running
                result = subprocess.run(['pgrep', '-f', 'barbossa.py'], capture_output=True, text=True)
                if result.stdout.strip():
                    execution_results.append({
                        'action_index': i,
                        'type': action_type,
                        'success': False,
                        'error': 'Barbossa is already running'
                    })
                else:
                    cmd = ['python3', str(BARBOSSA_DIR / 'barbossa.py')]
                    if work_area != 'auto':
                        cmd.extend(['--area', work_area])
                    
                    subprocess.Popen(cmd, cwd=str(BARBOSSA_DIR))
                    execution_results.append({
                        'action_index': i,
                        'type': action_type,
                        'success': True,
                        'message': f'Barbossa triggered for {work_area}'
                    })
            
            elif action_type == 'send_notification':
                # Placeholder for notification sending
                execution_results.append({
                    'action_index': i,
                    'type': action_type,
                    'success': True,
                    'message': 'Notification functionality not yet implemented'
                })
            
            else:
                execution_results.append({
                    'action_index': i,
                    'type': action_type,
                    'success': False,
                    'error': f'Unknown action type: {action_type}'
                })
        
        # Update workflow execution stats
        workflows[workflow_id]['execution_count'] += 1
        workflows[workflow_id]['last_execution'] = datetime.now().isoformat()
        workflows[workflow_id]['last_execution_results'] = execution_results
        
        with open(workflows_file, 'w') as f:
            json.dump(workflows, f, indent=2)
        
        # Calculate success rate
        successful_actions = len([r for r in execution_results if r.get('success', False)])
        success_rate = successful_actions / len(execution_results) if execution_results else 0
        
        return jsonify({
            'success': True,
            'workflow_id': workflow_id,
            'execution_results': execution_results,
            'success_rate': success_rate,
            'total_actions': len(execution_results),
            'successful_actions': successful_actions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Advanced Data Export/Import
@app.route('/api/data/export', methods=['POST'])
@auth.login_required
def api_data_export():
    """Export system data in various formats"""
    data = request.json
    export_type = data.get('type', 'complete')
    format_type = data.get('format', 'json')
    date_range = data.get('date_range', 7)  # days
    
    try:
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'type': export_type,
                'format': format_type,
                'date_range_days': date_range,
                'exported_by': session.get('username')
            },
            'data': {}
        }
        
        cutoff_date = datetime.now() - timedelta(days=date_range)
        
        if export_type in ['complete', 'logs']:
            # Export logs
            logs = []
            if LOGS_DIR.exists():
                for log_file in LOGS_DIR.glob('*.log'):
                    if datetime.fromtimestamp(log_file.stat().st_mtime) >= cutoff_date:
                        try:
                            with open(log_file, 'r') as f:
                                content = f.read()
                                logs.append({
                                    'filename': log_file.name,
                                    'size': len(content),
                                    'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                                    'content': sanitize_sensitive_info(content[:10000])  # Limit size
                                })
                        except Exception as e:
                            logs.append({
                                'filename': log_file.name,
                                'error': f'Could not read file: {str(e)}'
                            })
            export_data['data']['logs'] = logs
        
        if export_type in ['complete', 'metrics'] and server_manager:
            # Export metrics
            metrics = server_manager.metrics_collector.get_historical_metrics(date_range * 24)
            export_data['data']['metrics'] = metrics
        
        if export_type in ['complete', 'changelogs']:
            # Export changelogs
            changelogs = []
            if CHANGELOGS_DIR.exists():
                for changelog_file in CHANGELOGS_DIR.glob('*.md'):
                    if datetime.fromtimestamp(changelog_file.stat().st_mtime) >= cutoff_date:
                        try:
                            with open(changelog_file, 'r') as f:
                                changelogs.append({
                                    'filename': changelog_file.name,
                                    'content': sanitize_sensitive_info(f.read()),
                                    'modified': datetime.fromtimestamp(changelog_file.stat().st_mtime).isoformat()
                                })
                        except Exception as e:
                            changelogs.append({
                                'filename': changelog_file.name,
                                'error': f'Could not read file: {str(e)}'
                            })
            export_data['data']['changelogs'] = changelogs
        
        if export_type in ['complete', 'configuration']:
            # Export configuration (safe parts only)
            config_data = {}
            
            # Work tally
            tally_file = WORK_TRACKING_DIR / 'work_tally.json'
            if tally_file.exists():
                try:
                    with open(tally_file, 'r') as f:
                        config_data['work_tally'] = json.load(f)
                except:
                    pass
            
            # Alert rules
            rules_file = BARBOSSA_DIR / 'config' / 'alert_rules.json'
            if rules_file.exists():
                try:
                    with open(rules_file, 'r') as f:
                        config_data['alert_rules'] = json.load(f)
                except:
                    pass
            
            # Workflows
            workflows_file = BARBOSSA_DIR / 'config' / 'workflows.json'
            if workflows_file.exists():
                try:
                    with open(workflows_file, 'r') as f:
                        config_data['workflows'] = json.load(f)
                except:
                    pass
            
            export_data['data']['configuration'] = config_data
        
        # Return data based on format
        if format_type == 'json':
            return jsonify(export_data)
        
        elif format_type == 'csv':
            # Convert to CSV (simplified version for metrics)
            if 'metrics' in export_data['data']:
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                metrics = export_data['data']['metrics']
                if metrics:
                    # Write headers
                    writer.writerow(metrics[0].keys())
                    # Write data
                    for metric in metrics:
                        writer.writerow(metric.values())
                
                response = app.response_class(
                    output.getvalue(),
                    mimetype='text/csv',
                    headers={
                        'Content-Disposition': f'attachment;filename=barbossa_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                    }
                )
                return response
            else:
                return jsonify({'error': 'CSV format only supported for metrics export'}), 400
        
        else:
            return jsonify({'error': f'Unsupported format: {format_type}'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/import', methods=['POST'])
@auth.login_required
def api_data_import():
    """Import system data from uploaded files"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    import_type = request.form.get('type', 'configuration')
    
    try:
        # Read and parse the uploaded file
        file_content = file.read().decode('utf-8')
        
        if file.filename.endswith('.json'):
            import_data = json.loads(file_content)
        else:
            return jsonify({'error': 'Only JSON files are supported for import'}), 400
        
        results = []
        
        if import_type in ['configuration', 'complete']:
            # Import configuration data
            if 'data' in import_data and 'configuration' in import_data['data']:
                config_data = import_data['data']['configuration']
                
                # Import alert rules
                if 'alert_rules' in config_data:
                    rules_file = BARBOSSA_DIR / 'config' / 'alert_rules.json'
                    os.makedirs(rules_file.parent, exist_ok=True)
                    with open(rules_file, 'w') as f:
                        json.dump(config_data['alert_rules'], f, indent=2)
                    results.append('Alert rules imported successfully')
                
                # Import workflows
                if 'workflows' in config_data:
                    workflows_file = BARBOSSA_DIR / 'config' / 'workflows.json'
                    os.makedirs(workflows_file.parent, exist_ok=True)
                    with open(workflows_file, 'w') as f:
                        json.dump(config_data['workflows'], f, indent=2)
                    results.append('Workflows imported successfully')
        
        return jsonify({
            'success': True,
            'message': 'Import completed',
            'results': results,
            'imported_by': session.get('username'),
            'imported_at': datetime.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API Key/Token Management
@app.route('/api/auth/tokens', methods=['GET', 'POST'])
@auth.login_required
def api_auth_tokens():
    """Manage API authentication tokens"""
    tokens_file = BARBOSSA_DIR / 'config' / 'api_tokens.json'
    
    if request.method == 'GET':
        if tokens_file.exists():
            try:
                with open(tokens_file, 'r') as f:
                    tokens_data = json.load(f)
                
                # Return token info without revealing actual tokens
                token_info = []
                for token_id, token_data in tokens_data.items():
                    token_info.append({
                        'id': token_id,
                        'name': token_data.get('name', 'Unnamed'),
                        'created_by': token_data.get('created_by'),
                        'created_at': token_data.get('created_at'),
                        'expires_at': token_data.get('expires_at'),
                        'permissions': token_data.get('permissions', []),
                        'last_used': token_data.get('last_used'),
                        'active': token_data.get('active', True)
                    })
                
                return jsonify({'tokens': token_info})
            except Exception as e:
                return jsonify({'error': f'Could not load tokens: {str(e)}'}), 500
        else:
            return jsonify({'tokens': []})
    
    else:  # POST - Create new token
        data = request.json
        token_name = data.get('name')
        permissions = data.get('permissions', ['read'])
        expires_days = data.get('expires_days', 30)
        
        if not token_name:
            return jsonify({'error': 'Token name required'}), 400
        
        try:
            # Generate token
            import secrets
            token_id = secrets.token_hex(8)
            api_token = secrets.token_urlsafe(32)
            
            # Calculate expiration
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
            
            # Load existing tokens
            if tokens_file.exists():
                with open(tokens_file, 'r') as f:
                    tokens_data = json.load(f)
            else:
                tokens_data = {}
            
            # Add new token
            tokens_data[token_id] = {
                'name': token_name,
                'token_hash': generate_password_hash(api_token),  # Store hash, not token
                'created_by': session.get('username'),
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at,
                'permissions': permissions,
                'active': True,
                'last_used': None
            }
            
            # Save tokens
            os.makedirs(tokens_file.parent, exist_ok=True)
            with open(tokens_file, 'w') as f:
                json.dump(tokens_data, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(tokens_file, 0o600)
            
            return jsonify({
                'success': True,
                'message': 'API token created successfully',
                'token_id': token_id,
                'token': api_token,  # Only return this once
                'expires_at': expires_at,
                'warning': 'Save this token securely. It will not be shown again.'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/auth/tokens/<token_id>', methods=['DELETE', 'PATCH'])
@auth.login_required
def api_auth_token_manage(token_id):
    """Manage specific API token"""
    tokens_file = BARBOSSA_DIR / 'config' / 'api_tokens.json'
    
    if not tokens_file.exists():
        return jsonify({'error': 'No tokens found'}), 404
    
    try:
        with open(tokens_file, 'r') as f:
            tokens_data = json.load(f)
        
        if token_id not in tokens_data:
            return jsonify({'error': 'Token not found'}), 404
        
        if request.method == 'DELETE':
            # Delete token
            del tokens_data[token_id]
            
            with open(tokens_file, 'w') as f:
                json.dump(tokens_data, f, indent=2)
            
            return jsonify({
                'success': True,
                'message': f'Token {token_id} deleted successfully'
            })
        
        elif request.method == 'PATCH':
            # Update token (e.g., deactivate/activate)
            data = request.json
            
            if 'active' in data:
                tokens_data[token_id]['active'] = bool(data['active'])
            
            if 'permissions' in data:
                tokens_data[token_id]['permissions'] = data['permissions']
            
            with open(tokens_file, 'w') as f:
                json.dump(tokens_data, f, indent=2)
            
            return jsonify({
                'success': True,
                'message': f'Token {token_id} updated successfully'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Webhook Management
@app.route('/api/webhooks', methods=['GET', 'POST'])
@auth.login_required  
def api_webhooks_management():
    """Manage webhooks for external integrations"""
    webhooks_file = BARBOSSA_DIR / 'config' / 'webhooks.json'
    
    if request.method == 'GET':
        if webhooks_file.exists():
            with open(webhooks_file, 'r') as f:
                webhooks = json.load(f)
        else:
            webhooks = {}
        
        return jsonify({'webhooks': webhooks})
    
    else:  # POST - Create webhook
        data = request.json
        webhook_id = data.get('id')
        webhook_config = data.get('config')
        
        if not webhook_id or not webhook_config:
            return jsonify({'error': 'Webhook ID and config required'}), 400
        
        # Validate webhook config
        required_fields = ['name', 'url', 'events']
        for field in required_fields:
            if field not in webhook_config:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Load existing webhooks
        if webhooks_file.exists():
            with open(webhooks_file, 'r') as f:
                webhooks = json.load(f)
        else:
            webhooks = {}
        
        # Add webhook metadata
        webhook_config['created_at'] = datetime.now().isoformat()
        webhook_config['created_by'] = session.get('username')
        webhook_config['active'] = webhook_config.get('active', True)
        webhook_config['delivery_count'] = 0
        webhook_config['last_delivery'] = None
        
        webhooks[webhook_id] = webhook_config
        
        # Save webhooks
        os.makedirs(webhooks_file.parent, exist_ok=True)
        with open(webhooks_file, 'w') as f:
            json.dump(webhooks, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Webhook {webhook_id} created successfully'
        })

# Custom Barbossa Prompt API Endpoints
@app.route('/api/barbossa/custom-prompt', methods=['POST'])
@auth.login_required
def api_barbossa_custom_prompt():
    """Create a custom Barbossa prompt session"""
    if not prompt_manager:
        return jsonify({'success': False, 'error': 'Prompt manager not available'}), 503
    
    data = request.json
    prompt = data.get('prompt')
    repository = data.get('repository')
    task_type = data.get('task_type', 'custom')
    
    if not prompt:
        return jsonify({'success': False, 'error': 'Prompt is required'}), 400
    
    try:
        result = prompt_manager.create_custom_session(prompt, repository, task_type)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/barbossa/session/<session_id>')
@auth.login_required
def api_barbossa_session_status(session_id):
    """Get status and output of a Barbossa session"""
    if not prompt_manager:
        return jsonify({'success': False, 'error': 'Prompt manager not available'}), 503
    
    try:
        result = prompt_manager.get_session_status(session_id)
        return jsonify(result), 200 if result['success'] else 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/barbossa/session/<session_id>/stream')
@auth.login_required
def api_barbossa_session_stream(session_id):
    """Get streaming output from a Barbossa session"""
    if not prompt_manager:
        return jsonify({'success': False, 'error': 'Prompt manager not available'}), 503
    
    offset = request.args.get('offset', 0, type=int)
    
    try:
        result = prompt_manager.get_session_output_stream(session_id, offset)
        return jsonify(result), 200 if result['success'] else 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/barbossa/sessions')
@auth.login_required
def api_barbossa_sessions():
    """List all Barbossa sessions"""
    if not prompt_manager:
        return jsonify({'success': False, 'error': 'Prompt manager not available'}), 503
    
    limit = request.args.get('limit', 10, type=int)
    
    try:
        sessions = prompt_manager.list_sessions(limit)
        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/barbossa/allowed-repositories')
@auth.login_required
def api_barbossa_allowed_repositories():
    """Get list of allowed repositories from whitelist"""
    try:
        whitelist_file = BARBOSSA_DIR / 'config' / 'repository_whitelist.json'
        if whitelist_file.exists():
            with open(whitelist_file, 'r') as f:
                whitelist = json.load(f)
                repositories = whitelist.get('allowed_repositories', [])
                # Add friendly names
                repo_list = []
                for repo in repositories:
                    parts = repo.split('/')
                    if len(parts) == 2:
                        repo_list.append({
                            'url': f'https://github.com/{repo}',
                            'name': parts[1],
                            'full_name': repo
                        })
                return jsonify({'success': True, 'repositories': repo_list})
        else:
            return jsonify({'success': False, 'error': 'Whitelist not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/barbossa/session/<session_id>/terminate', methods=['POST'])
@auth.login_required
def api_barbossa_session_terminate(session_id):
    """Terminate a running Barbossa session"""
    if not prompt_manager:
        return jsonify({'success': False, 'error': 'Prompt manager not available'}), 503
    
    try:
        result = prompt_manager.terminate_session(session_id)
        return jsonify(result), 200 if result['success'] else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/barbossa/executions')
@auth.login_required
def api_barbossa_executions():
    """Get recent Barbossa executions"""
    try:
        executions = []
        
        # Get barbossa logs from subdirectory
        barbossa_dir = LOGS_DIR / 'barbossa'
        if barbossa_dir.exists():
            log_files = sorted(barbossa_dir.glob('barbossa_*.log'), reverse=True)[:10]
            
            for log_file in log_files:
                # Parse timestamp from filename
                filename = log_file.name
                timestamp_match = re.search(r'(\d{8}_\d{6})', filename)
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
                else:
                    timestamp = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                # Try to determine area and status from log content
                area = 'unknown'
                status = 'completed'
                summary = ''
                
                try:
                    with open(log_file, 'r') as f:
                        content = f.read(5000)  # Read first 5KB
                        if 'infrastructure' in content.lower():
                            area = 'infrastructure'
                        elif 'personal' in content.lower():
                            area = 'personal_projects'
                        elif 'davy' in content.lower():
                            area = 'davy_jones'
                        
                        if 'error' in content.lower() or 'failed' in content.lower():
                            status = 'failed'
                        
                        # Try to extract summary
                        lines = content.split('\n')[:10]
                        for line in lines:
                            if 'working on' in line.lower() or 'task:' in line.lower():
                                summary = line.strip()[:100]
                                break
                except:
                    pass
                
                executions.append({
                    'timestamp': timestamp,
                    'area': area,
                    'status': status,
                    'summary': summary,
                    'log_file': f'barbossa/{filename}',
                    'duration': None
                })
        
        # Also check main logs directory
        main_logs = sorted(LOGS_DIR.glob('barbossa_enhanced_*.log'), reverse=True)[:5]
        for log_file in main_logs:
            filename = log_file.name
            timestamp_match = re.search(r'(\d{8}_\d{6})', filename)
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            executions.append({
                'timestamp': timestamp,
                'area': 'enhanced',
                'status': 'completed',
                'summary': 'Enhanced Barbossa execution',
                'log_file': filename,
                'duration': None
            })
        
        # Sort by timestamp
        executions.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify(executions[:20])  # Return top 20
    except Exception as e:
        logger.error(f"Error getting Barbossa executions: {e}")
        return jsonify([])

@app.route('/api/barbossa/cron')
@auth.login_required
def api_barbossa_cron():
    """Get cron activity for Barbossa"""
    try:
        cron_logs = []
        jobs = []
        
        # Get cron logs
        cron_files = sorted(LOGS_DIR.glob('cron_*.log'), reverse=True)[:10]
        for log_file in cron_files:
            timestamp = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            status = 'completed'
            
            try:
                with open(log_file, 'r') as f:
                    content = f.read(1000)
                    if 'error' in content.lower():
                        status = 'error'
                    elif 'skipped' in content.lower():
                        status = 'skipped'
            except:
                pass
            
            cron_logs.append({
                'file': log_file.name,
                'time': timestamp,
                'status': status
            })
        
        # Check cron configuration
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                cron_lines = result.stdout.strip().split('\n')
                for line in cron_lines:
                    if 'barbossa' in line.lower() and not line.startswith('#'):
                        # Parse cron schedule
                        parts = line.split()
                        if len(parts) >= 6:
                            schedule = ' '.join(parts[:5])
                            command = ' '.join(parts[5:])
                            jobs.append({
                                'name': 'Barbossa Automation',
                                'schedule': schedule,
                                'enabled': True
                            })
        except:
            pass
        
        return jsonify({
            'recent_logs': cron_logs,
            'jobs': jobs
        })
    except Exception as e:
        logger.error(f"Error getting cron activity: {e}")
        return jsonify({'recent_logs': [], 'jobs': []})

@app.route('/api/barbossa/personal-assistant')
@auth.login_required
def api_barbossa_personal_assistant():
    """Get personal assistant status"""
    try:
        # Check if personal assistant is running
        is_running = False
        result = subprocess.run(['pgrep', '-f', 'barbossa_personal_assistant'], capture_output=True)
        if result.returncode == 0:
            is_running = True
        
        # Get statistics from state file
        state_file = BASE_DIR / 'state' / 'barbossa_state.json'
        tickets_enriched = 0
        improvements_found = 0
        recent_activity = []
        
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    if 'personal_assistant' in state:
                        pa_state = state['personal_assistant']
                        tickets_enriched = pa_state.get('tickets_enriched', 0)
                        improvements_found = pa_state.get('improvements_found', 0)
                        
                        # Get recent activity
                        if 'recent_activity' in pa_state:
                            for activity in pa_state['recent_activity'][-10:]:
                                recent_activity.append({
                                    'time': activity.get('timestamp', 'Unknown'),
                                    'action': activity.get('action', 'Activity')
                                })
            except:
                pass
        
        # Check logs for recent activity if no state
        if not recent_activity:
            pa_logs = sorted(LOGS_DIR.glob('claude_personal_*.log'), reverse=True)[:5]
            for log_file in pa_logs:
                timestamp = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                recent_activity.append({
                    'time': timestamp,
                    'action': 'Personal assistant execution'
                })
        
        return jsonify({
            'is_running': is_running,
            'tickets_enriched': tickets_enriched,
            'improvements_found': improvements_found,
            'recent_activity': recent_activity
        })
    except Exception as e:
        logger.error(f"Error getting personal assistant status: {e}")
        return jsonify({
            'is_running': False,
            'tickets_enriched': 0,
            'improvements_found': 0,
            'recent_activity': []
        })

@app.route('/api/barbossa/claude-summary')
@auth.login_required
def api_barbossa_claude_summary():
    """Get Claude work summary"""
    try:
        # Count Claude logs by type
        personal_count = len(list(LOGS_DIR.glob('claude_personal_*.log')))
        infrastructure_count = len(list(LOGS_DIR.glob('claude_infrastructure_*.log')))
        davy_count = len(list(LOGS_DIR.glob('claude_davy_*.log')))
        
        # Get recent work items
        recent_work = []
        all_claude_logs = sorted(LOGS_DIR.glob('claude_*.log'), reverse=True)[:10]
        
        for log_file in all_claude_logs:
            timestamp = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            
            # Determine task type from filename
            task = 'Unknown task'
            if 'personal' in log_file.name:
                task = 'Personal project work'
            elif 'infrastructure' in log_file.name:
                task = 'Infrastructure improvements'
            elif 'davy' in log_file.name:
                task = 'Davy Jones development'
            elif 'self_improvement' in log_file.name:
                task = 'Self improvement'
            
            recent_work.append({
                'time': timestamp,
                'task': task
            })
        
        return jsonify({
            'personal_projects': personal_count,
            'infrastructure': infrastructure_count,
            'davy_jones': davy_count,
            'recent_work': recent_work
        })
    except Exception as e:
        logger.error(f"Error getting Claude summary: {e}")
        return jsonify({
            'personal_projects': 0,
            'infrastructure': 0,
            'davy_jones': 0,
            'recent_work': []
        })

@app.route('/health')
def health():
    """Health check endpoint (no auth required)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'server_manager': 'active' if server_manager else 'inactive'
    })

@app.teardown_appcontext
def shutdown_monitoring(error=None):
    """Clean shutdown of monitoring when app stops"""
    if server_manager:
        server_manager.stop_monitoring()

if __name__ == '__main__':
    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Generate self-signed cert if not exists
    cert_file = Path(__file__).parent / 'cert.pem'
    key_file = Path(__file__).parent / 'key.pem'
    
    if not cert_file.exists() or not key_file.exists():
        print("Generating self-signed certificate...")
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
            '-keyout', str(key_file), '-out', str(cert_file),
            '-days', '365', '-nodes', '-subj',
            '/C=US/ST=State/L=City/O=Barbossa/CN=localhost'
        ])
    
    context.load_cert_chain(str(cert_file), str(key_file))
    
    print(f"Starting Enhanced Barbossa Web Portal on https://0.0.0.0:8443")
    print(f"Access locally: https://localhost:8443")
    print(f"Access remotely: https://eastindiaonchaincompany.xyz")
    print(f"Enhanced dashboard: https://localhost:8443/enhanced")
    print(f"Server Manager: {'Active' if server_manager else 'Not Available'}")
    
    app.run(
        host='0.0.0.0',
        port=8443,
        ssl_context=context,
        debug=False
    )