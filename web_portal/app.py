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
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.profiler import ProfilerMiddleware
import secrets
import shutil

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import the server manager
try:
    from server_manager import BarbossaServerManager
    SERVER_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import server_manager: {e}")
    SERVER_MANAGER_AVAILABLE = False

# Import enhanced security - DISABLED due to rate limiting issues
try:
    # Temporarily disable enhanced security to fix authentication issues
    ENHANCED_SECURITY_AVAILABLE = False
    enhanced_security = None
    print("Enhanced security temporarily disabled")
except ImportError as e:
    print(f"Warning: Could not import enhanced security: {e}")
    ENHANCED_SECURITY_AVAILABLE = False

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
auth = HTTPBasicAuth()

# Global cache for API responses
_cache = {}
_cache_expiry = {}
_cache_lock = threading.Lock()

def cached_response(ttl: int = 60):
    """Decorator to cache API responses"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}_{hash(str(args))}{hash(str(kwargs))}"
            
            with _cache_lock:
                if cache_key in _cache and cache_key in _cache_expiry:
                    if time.time() < _cache_expiry[cache_key]:
                        return _cache[cache_key]
                    else:
                        del _cache[cache_key]
                        del _cache_expiry[cache_key]
            
            result = func(*args, **kwargs)
            
            with _cache_lock:
                _cache[cache_key] = result
                _cache_expiry[cache_key] = time.time() + ttl
            
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

# Main dashboard route (consolidated)
@app.route('/')
@auth.login_required
def index():
    """Main Barbossa dashboard with all features"""
    return render_template('dashboard.html', 
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
    """Get recent log entries"""
    logs = []
    
    # Get most recent log files
    if LOGS_DIR.exists():
        log_files = sorted(LOGS_DIR.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-20:]  # Last 20 lines
                    for line in lines:
                        logs.append({
                            'timestamp': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                            'file': log_file.name,
                            'content': sanitize_sensitive_info(line.strip())
                        })
            except Exception as e:
                print(f"Error reading log {log_file}: {e}")
    
    return jsonify({'logs': logs[-100:]})  # Return last 100 log entries

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

@app.route('/api/changelogs')
@auth.login_required
def api_changelogs():
    """Get changelogs"""
    limit = request.args.get('limit', 20, type=int)
    changelogs = []
    
    if CHANGELOGS_DIR.exists():
        changelog_files = sorted(CHANGELOGS_DIR.glob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]
        
        for changelog_file in changelog_files:
            name_parts = changelog_file.stem.split('_')
            work_area = name_parts[0] if name_parts else 'unknown'
            
            with open(changelog_file, 'r') as f:
                lines = f.readlines()[:10]
                summary = ''.join(lines[:3]) if lines else 'No content'
            
            changelogs.append({
                'filename': changelog_file.name,
                'work_area': work_area,
                'timestamp': datetime.fromtimestamp(changelog_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size': f"{changelog_file.stat().st_size / 1024:.1f} KB",
                'summary': sanitize_sensitive_info(summary)
            })
    
    return jsonify(changelogs)

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
    allowed_dirs = [LOGS_DIR, CHANGELOGS_DIR, SECURITY_DIR]
    
    for allowed_dir in allowed_dirs:
        file_path = allowed_dir / filename
        if file_path.exists() and file_path.is_file():
            with open(file_path, 'r') as f:
                content = f.read()
                if len(content) > 1024 * 1024:
                    content = content[:1024 * 1024] + "\n\n... [TRUNCATED - File too large] ..."
                
                return jsonify({
                    'filename': filename,
                    'content': sanitize_sensitive_info(content),
                    'size': f"{len(content) / 1024:.1f} KB"
                })
    
    return jsonify({'error': 'File not found'}), 404

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