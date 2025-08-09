#!/usr/bin/env python3
"""
Barbossa Web Portal - Advanced Management Dashboard
Provides comprehensive monitoring, logging, and control interface for Barbossa
"""

import json
import os
import ssl
import subprocess
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, send_file
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import shutil

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
auth = HTTPBasicAuth()

# Configuration
BARBOSSA_DIR = Path.home() / 'barbossa-engineer'
LOGS_DIR = BARBOSSA_DIR / 'logs'
CHANGELOGS_DIR = BARBOSSA_DIR / 'changelogs'
SECURITY_DIR = BARBOSSA_DIR / 'security'
WORK_TRACKING_DIR = BARBOSSA_DIR / 'work_tracking'
PROJECTS_DIR = BARBOSSA_DIR / 'projects'
ARCHIVE_DIR = BARBOSSA_DIR / 'archive'

# Ensure archive directory exists
ARCHIVE_DIR.mkdir(exist_ok=True)

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
    if username in users and check_password_hash(users.get(username), password):
        session['username'] = username
        return username

def sanitize_sensitive_info(text):
    """Remove sensitive information from logs"""
    if not text:
        return text
    
    # Hide API keys
    text = re.sub(r'(api[_-]?key|token|secret|password)["\']?\s*[:=]\s*["\']?[\w-]+', 
                  r'\1=***REDACTED***', text, flags=re.IGNORECASE)
    
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
    
    # Get recent logs
    if LOGS_DIR.exists():
        log_files = sorted(LOGS_DIR.glob('barbossa_*.log'), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
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

def get_changelogs(limit=20):
    """Get recent changelogs with details"""
    changelogs = []
    
    if CHANGELOGS_DIR.exists():
        changelog_files = sorted(CHANGELOGS_DIR.glob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]
        
        for changelog_file in changelog_files:
            # Parse filename for work area and timestamp
            name_parts = changelog_file.stem.split('_')
            work_area = name_parts[0] if name_parts else 'unknown'
            
            # Read first few lines for summary
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
    
    return changelogs

def get_security_events(limit=50):
    """Get recent security events"""
    events = []
    
    # Read audit log
    audit_log = SECURITY_DIR / 'audit.log'
    if audit_log.exists():
        with open(audit_log, 'r') as f:
            lines = f.readlines()[-limit:]
            for line in reversed(lines):
                if line.strip():
                    # Parse log line
                    parts = line.split(' - ')
                    if len(parts) >= 3:
                        events.append({
                            'timestamp': parts[0],
                            'level': parts[1],
                            'message': sanitize_sensitive_info(' - '.join(parts[2:]))
                        })
    
    return events

def get_claude_outputs():
    """Get Claude execution outputs"""
    outputs = []
    
    if LOGS_DIR.exists():
        claude_files = sorted(LOGS_DIR.glob('claude_*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
        
        for claude_file in claude_files:
            # Determine work type from filename
            work_type = 'unknown'
            if 'infrastructure' in claude_file.name:
                work_type = 'infrastructure'
            elif 'personal' in claude_file.name:
                work_type = 'personal_projects'
            elif 'davy' in claude_file.name:
                work_type = 'davy_jones'
            
            # Check if file has content
            size = claude_file.stat().st_size
            status = 'completed' if size > 100 else 'in_progress' if size == 0 else 'partial'
            
            outputs.append({
                'filename': claude_file.name,
                'work_type': work_type,
                'status': status,
                'size': f"{size / 1024:.1f} KB" if size > 0 else "0 KB",
                'timestamp': datetime.fromtimestamp(claude_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return outputs

@app.route('/')
@auth.login_required
def index():
    """Main dashboard"""
    return render_template('dashboard.html', 
                         username=session.get('username'),
                         timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))

@app.route('/api/status')
@auth.login_required
def api_status():
    """API endpoint for status data"""
    return jsonify({
        'barbossa': get_barbossa_status(),
        'system': get_system_stats(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/changelogs')
@auth.login_required
def api_changelogs():
    """API endpoint for changelogs"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify(get_changelogs(limit))

@app.route('/api/security')
@auth.login_required
def api_security():
    """API endpoint for security events"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify(get_security_events(limit))

@app.route('/api/claude')
@auth.login_required
def api_claude():
    """API endpoint for Claude outputs"""
    return jsonify(get_claude_outputs())

@app.route('/api/log/<path:filename>')
@auth.login_required
def api_log_content(filename):
    """Get content of a specific log file"""
    # Security check - ensure file is in allowed directories
    allowed_dirs = [LOGS_DIR, CHANGELOGS_DIR, SECURITY_DIR]
    
    for allowed_dir in allowed_dirs:
        file_path = allowed_dir / filename
        if file_path.exists() and file_path.is_file():
            with open(file_path, 'r') as f:
                content = f.read()
                # Limit to 1MB to prevent browser issues
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
    
    # Create archive with timestamp
    archive_subdir = ARCHIVE_DIR / datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_subdir.mkdir(exist_ok=True)
    
    # Archive old logs
    for log_dir in [LOGS_DIR, CHANGELOGS_DIR]:
        if log_dir.exists():
            for log_file in log_dir.glob('*'):
                if log_file.is_file():
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        # Move to archive
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
    
    # Check if already running
    result = subprocess.run(['pgrep', '-f', 'barbossa.py'], capture_output=True, text=True)
    if result.stdout.strip():
        return jsonify({'success': False, 'error': 'Barbossa is already running'}), 400
    
    # Build command
    cmd = ['python3', str(BARBOSSA_DIR / 'barbossa.py')]
    if work_area and work_area in ['infrastructure', 'personal_projects', 'davy_jones']:
        cmd.extend(['--area', work_area])
    
    # Launch Barbossa in background
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
        # Verify it's a Claude process
        result = subprocess.run(['ps', '-p', str(pid)], capture_output=True, text=True)
        if 'claude' not in result.stdout.lower():
            return jsonify({'success': False, 'error': 'Not a Claude process'}), 400
        
        # Kill the process
        subprocess.run(['kill', str(pid)])
        time.sleep(1)
        
        # Check if killed
        result = subprocess.run(['ps', '-p', str(pid)], capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({'success': True, 'message': f'Claude process {pid} terminated'})
        else:
            # Force kill if still running
            subprocess.run(['kill', '-9', str(pid)])
            return jsonify({'success': True, 'message': f'Claude process {pid} force terminated'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/services')
@auth.login_required
def api_services():
    """Get status of related services"""
    services = {}
    
    # Check Docker containers
    result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}:{{.Status}}'], capture_output=True, text=True)
    docker_containers = {}
    for line in result.stdout.strip().split('\n'):
        if ':' in line:
            name, status = line.split(':', 1)
            docker_containers[name] = 'running' if 'Up' in status else 'stopped'
    
    services['docker'] = docker_containers
    
    # Check important processes instead of systemd services
    process_checks = {
        'barbossa_portal': 'web_portal/app.py',
        'cloudflared': 'cloudflared',
        'claude': 'claude --dangerously-skip-permissions',
        'docker': 'dockerd'
    }
    
    ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    for name, search_term in process_checks.items():
        services[name] = 'active' if search_term in ps_result.stdout else 'inactive'
    
    # Check tmux sessions
    result = subprocess.run(['tmux', 'ls'], capture_output=True, text=True)
    tmux_sessions = []
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                session_name = line.split(':')[0]
                tmux_sessions.append(session_name)
    services['tmux_sessions'] = tmux_sessions
    
    return jsonify(services)

@app.route('/health')
def health():
    """Health check endpoint (no auth required)"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

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
    
    print(f"Starting Barbossa Web Portal on https://0.0.0.0:8443")
    print(f"Access locally: https://localhost:8443")
    print(f"Access remotely: https://eastindiaonchaincompany.xyz")
    
    app.run(
        host='0.0.0.0',
        port=8443,
        ssl_context=context,
        debug=False
    )