#!/usr/bin/env python3
"""
Barbossa Web Portal - HTTPS Dashboard
Provides secure web interface for monitoring Barbossa and server status
"""

import json
import os
import ssl
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
auth = HTTPBasicAuth()

# Configuration
BARBOSSA_DIR = Path.home() / 'barbossa-engineer'
LOGS_DIR = BARBOSSA_DIR / 'logs'
CHANGELOGS_DIR = BARBOSSA_DIR / 'changelogs'
SECURITY_DIR = BARBOSSA_DIR / 'security'
WORK_TRACKING_DIR = BARBOSSA_DIR / 'work_tracking'

# Default credentials (should be changed in production)
users = {
    "admin": generate_password_hash("changeme123!")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

@app.route('/')
@auth.login_required
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
@auth.login_required
def get_status():
    """Get Barbossa and system status"""
    status = {
        'barbossa': get_barbossa_status(),
        'system': get_system_status(),
        'services': get_services_status(),
        'security': get_security_status()
    }
    return jsonify(status)

@app.route('/api/logs')
@auth.login_required
def get_logs():
    """Get recent Barbossa logs"""
    logs = []
    if LOGS_DIR.exists():
        log_files = sorted(LOGS_DIR.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        for log_file in log_files:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                logs.append({
                    'filename': log_file.name,
                    'timestamp': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
                    'content': ''.join(lines[-50:])  # Last 50 lines
                })
    return jsonify(logs)

@app.route('/api/changelogs')
@auth.login_required
def get_changelogs():
    """Get recent changelogs"""
    changelogs = []
    if CHANGELOGS_DIR.exists():
        changelog_files = sorted(CHANGELOGS_DIR.glob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        for changelog_file in changelog_files:
            with open(changelog_file, 'r') as f:
                changelogs.append({
                    'filename': changelog_file.name,
                    'timestamp': datetime.fromtimestamp(changelog_file.stat().st_mtime).isoformat(),
                    'content': f.read()
                })
    return jsonify(changelogs)

@app.route('/api/security-audit')
@auth.login_required
def get_security_audit():
    """Get security audit log"""
    audit_log = SECURITY_DIR / 'audit.log'
    violations_log = SECURITY_DIR / 'security_violations.log'
    
    audit_data = {
        'audit_entries': [],
        'violations': []
    }
    
    if audit_log.exists():
        with open(audit_log, 'r') as f:
            audit_data['audit_entries'] = f.readlines()[-100:]  # Last 100 entries
    
    if violations_log.exists():
        with open(violations_log, 'r') as f:
            audit_data['violations'] = f.readlines()
    
    return jsonify(audit_data)

@app.route('/api/work-tally')
@auth.login_required
def get_work_tally():
    """Get current work tally"""
    tally_file = WORK_TRACKING_DIR / 'work_tally.json'
    if tally_file.exists():
        with open(tally_file, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({})

def get_barbossa_status():
    """Get Barbossa status"""
    try:
        result = subprocess.run(
            ['python3', str(BARBOSSA_DIR / 'barbossa.py'), '--status'],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except:
        return {'status': 'error', 'message': 'Could not get Barbossa status'}

def get_system_status():
    """Get system status"""
    status = {}
    
    # CPU usage
    try:
        result = subprocess.run(['top', '-bn1'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        for line in lines:
            if 'Cpu(s)' in line or '%Cpu' in line:
                status['cpu'] = line.strip()
                break
    except:
        status['cpu'] = 'N/A'
    
    # Memory usage
    try:
        result = subprocess.run(['free', '-h'], capture_output=True, text=True)
        status['memory'] = result.stdout
    except:
        status['memory'] = 'N/A'
    
    # Disk usage
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        status['disk'] = result.stdout
    except:
        status['disk'] = 'N/A'
    
    return status

def get_services_status():
    """Get status of related services"""
    services = {}
    
    # Check if Davy Jones Intern is running
    try:
        result = subprocess.run(['pgrep', '-f', 'davy-jones-intern'], capture_output=True)
        services['davy_jones_intern'] = 'running' if result.returncode == 0 else 'stopped'
    except:
        services['davy_jones_intern'] = 'unknown'
    
    # Check Docker
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True)
        services['docker'] = 'running' if result.returncode == 0 else 'stopped'
    except:
        services['docker'] = 'unknown'
    
    # Check cron
    try:
        result = subprocess.run(['pgrep', 'cron'], capture_output=True)
        services['cron'] = 'running' if result.returncode == 0 else 'stopped'
    except:
        services['cron'] = 'unknown'
    
    return services

def get_security_status():
    """Get security status summary"""
    import sys
    sys.path.append(str(BARBOSSA_DIR))
    from security_guard import security_guard
    
    return security_guard.get_audit_summary()

if __name__ == '__main__':
    # Create SSL context for HTTPS
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    
    # For development - in production, use proper certificates
    # You'll need to generate these certificates for eastindiaonchaincompany.xyz
    cert_file = BARBOSSA_DIR / 'web_portal' / 'cert.pem'
    key_file = BARBOSSA_DIR / 'web_portal' / 'key.pem'
    
    if not cert_file.exists() or not key_file.exists():
        print("Generating self-signed certificates for development...")
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096', 
            '-keyout', str(key_file), '-out', str(cert_file),
            '-days', '365', '-nodes',
            '-subj', '/C=US/ST=State/L=City/O=EastIndiaOnchainCompany/CN=eastindiaonchaincompany.xyz'
        ])
    
    context.load_cert_chain(str(cert_file), str(key_file))
    
    print("Starting Barbossa Web Portal on https://0.0.0.0:8443")
    print("Default credentials: admin / changeme123!")
    print("WARNING: Change default credentials in production!")
    
    app.run(host='0.0.0.0', port=8443, ssl_context=context, debug=False)