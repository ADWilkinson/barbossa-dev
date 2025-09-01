#!/usr/bin/env python3
"""
Personal Assistant v4 API for Web Portal
Provides status and control for Barbossa Personal Assistant
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Blueprint, jsonify, request
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash, generate_password_hash

# Create blueprint
personal_assistant_api = Blueprint('personal_assistant_api', __name__)
auth = HTTPBasicAuth()

# Paths
BARBOSSA_DIR = Path.home() / "barbossa-engineer"
STATE_FILE = BARBOSSA_DIR / "state" / "barbossa_state.json"
LOGS_DIR = BARBOSSA_DIR / "logs" / "barbossa"
ENV_FILE = BARBOSSA_DIR / ".env.personal_assistant"
CRON_LOG = LOGS_DIR / "cron.log"

# Load credentials
credentials_file = Path.home() / '.barbossa_credentials.json'
users = {}
if credentials_file.exists():
    with open(credentials_file) as f:
        users_data = json.load(f)
        users = {username: generate_password_hash(password) 
                for username, password in users_data.items()}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

@personal_assistant_api.route('/api/assistant/status')
@auth.login_required
def assistant_status():
    """Get Personal Assistant v4 status"""
    response = {
        'version': 'v4',
        'features': {
            'state_tracking': True,
            'linear_integration': True,
            'development_enrichment': True,
            'autonomous_improvements': True
        },
        'state': {},
        'settings': {},
        'cron': {},
        'last_run': None
    }
    
    # Load state if exists
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                response['state'] = {
                    'tickets_processed': len(state.get('processed_tickets', {})),
                    'improvements_found': len(state.get('processed_improvements', {})),
                    'statistics': state.get('statistics', {}),
                    'last_run': state.get('last_run')
                }
                response['last_run'] = state.get('last_run')
        except:
            pass
    
    # Check settings
    if ENV_FILE.exists():
        try:
            with open(ENV_FILE, 'r') as f:
                env_content = f.read()
                response['settings'] = {
                    'dry_run': 'DRY_RUN_MODE=true' in env_content,
                    'test_mode': 'TEST_ENVIRONMENT=true' in env_content,
                    'mode': 'DRY RUN' if 'DRY_RUN_MODE=true' in env_content else 'LIVE'
                }
        except:
            pass
    
    # Check cron status
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
        if 'barbossa_personal_assistant' in result.stdout or 'run_barbossa_v4' in result.stdout:
            # Extract schedule
            for line in result.stdout.split('\n'):
                if 'barbossa' in line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 6:
                        response['cron'] = {
                            'enabled': True,
                            'schedule': ' '.join(parts[:5]),
                            'time': f"{parts[1]}:{parts[0].zfill(2)}" if parts[0] != '*' else 'Multiple',
                            'command': ' '.join(parts[5:])
                        }
                        break
        else:
            response['cron'] = {'enabled': False}
    except:
        response['cron'] = {'enabled': False, 'error': 'Could not check cron'}
    
    return jsonify(response)

@personal_assistant_api.route('/api/assistant/state-details')
@auth.login_required
def assistant_state_details():
    """Get detailed state information"""
    if not STATE_FILE.exists():
        return jsonify({'error': 'No state file found'}), 404
    
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        # Get recent tickets
        recent_tickets = []
        for ticket_id, data in state.get('processed_tickets', {}).items():
            recent_tickets.append({
                'id': ticket_id,
                'title': data.get('title', 'Unknown'),
                'processed_at': data.get('processed_at'),
                'version': data.get('version', 1)
            })
        
        # Sort by processed_at
        recent_tickets = sorted(recent_tickets, 
                              key=lambda x: x['processed_at'] if x['processed_at'] else '', 
                              reverse=True)[:10]
        
        # Get recent improvements
        recent_improvements = []
        for imp_id, data in state.get('processed_improvements', {}).items():
            recent_improvements.append({
                'id': imp_id,
                'description': data.get('description', 'Unknown'),
                'processed_at': data.get('processed_at')
            })
        
        recent_improvements = sorted(recent_improvements,
                                    key=lambda x: x['processed_at'] if x['processed_at'] else '',
                                    reverse=True)[:10]
        
        return jsonify({
            'recent_tickets': recent_tickets,
            'recent_improvements': recent_improvements,
            'statistics': state.get('statistics', {}),
            'last_run': state.get('last_run')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@personal_assistant_api.route('/api/assistant/recent-logs')
@auth.login_required
def assistant_recent_logs():
    """Get recent operation logs"""
    logs = []
    
    # Find recent operation logs
    if LOGS_DIR.exists():
        log_files = sorted(LOGS_DIR.glob('barbossa_operations_*.log'), 
                          key=lambda x: x.stat().st_mtime, 
                          reverse=True)[:5]
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    
                # Parse log content
                timestamp = log_file.stem.replace('barbossa_operations_', '')
                logs.append({
                    'filename': log_file.name,
                    'timestamp': timestamp,
                    'size': f"{log_file.stat().st_size / 1024:.1f} KB",
                    'preview': content[:500] if content else 'Empty log'
                })
            except:
                pass
    
    # Add cron log if exists
    if CRON_LOG.exists():
        try:
            with open(CRON_LOG, 'r') as f:
                lines = f.readlines()
                last_lines = ''.join(lines[-20:]) if lines else 'No cron execution yet'
                
            logs.insert(0, {
                'filename': 'cron.log',
                'timestamp': 'Latest',
                'size': f"{CRON_LOG.stat().st_size / 1024:.1f} KB",
                'preview': last_lines
            })
        except:
            pass
    
    return jsonify({'logs': logs})

@personal_assistant_api.route('/api/assistant/run-now', methods=['POST'])
@auth.login_required
def run_assistant_now():
    """Manually trigger the personal assistant"""
    try:
        # Check if already running
        result = subprocess.run(['pgrep', '-f', 'barbossa_personal_assistant_v4'], 
                              capture_output=True, text=True, timeout=5)
        if result.stdout:
            return jsonify({'error': 'Assistant is already running'}), 400
        
        # Run the assistant
        script_path = BARBOSSA_DIR / 'run_barbossa_v4.sh'
        if not script_path.exists():
            # Create a simple run command
            cmd = f"cd {BARBOSSA_DIR} && source venv_personal_assistant/bin/activate && source .env.personal_assistant && python3 barbossa_personal_assistant_v4.py"
            result = subprocess.Popen(cmd, shell=True, 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
        else:
            result = subprocess.Popen([str(script_path)], 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE)
        
        return jsonify({
            'success': True,
            'message': 'Personal Assistant started',
            'pid': result.pid
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@personal_assistant_api.route('/api/assistant/toggle-mode', methods=['POST'])
@auth.login_required
def toggle_mode():
    """Toggle between DRY_RUN and LIVE mode"""
    if not ENV_FILE.exists():
        return jsonify({'error': 'Environment file not found'}), 404
    
    try:
        with open(ENV_FILE, 'r') as f:
            content = f.read()
        
        # Toggle DRY_RUN_MODE
        if 'DRY_RUN_MODE=true' in content:
            content = content.replace('DRY_RUN_MODE=true', 'DRY_RUN_MODE=false')
            new_mode = 'LIVE'
        else:
            content = content.replace('DRY_RUN_MODE=false', 'DRY_RUN_MODE=true')
            new_mode = 'DRY RUN'
        
        # Write back
        with open(ENV_FILE, 'w') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'new_mode': new_mode,
            'message': f'Mode switched to {new_mode}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@personal_assistant_api.route('/api/assistant/clear-state', methods=['POST'])
@auth.login_required
def clear_state():
    """Clear the state to force reprocessing"""
    try:
        if STATE_FILE.exists():
            # Create backup
            backup_file = STATE_FILE.with_suffix('.backup')
            STATE_FILE.rename(backup_file)
            
            # Create new empty state
            empty_state = {
                "processed_tickets": {},
                "processed_improvements": {},
                "last_run": None,
                "statistics": {
                    "total_tickets_enriched": 0,
                    "total_improvements_found": 0,
                    "total_runs": 0
                }
            }
            
            with open(STATE_FILE, 'w') as f:
                json.dump(empty_state, f, indent=2)
            
            return jsonify({
                'success': True,
                'message': 'State cleared - all tickets will be reprocessed',
                'backup': str(backup_file)
            })
        else:
            return jsonify({'error': 'No state file to clear'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@personal_assistant_api.route('/api/assistant/stats')
@auth.login_required
def assistant_stats():
    """Get assistant statistics and analytics"""
    stats = {
        'total_tickets': 0,
        'total_improvements': 0,
        'total_runs': 0,
        'mode': 'Unknown',
        'cron_enabled': False,
        'last_run': None,
        'next_run': None
    }
    
    # Load state statistics
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                stats.update(state.get('statistics', {}))
                stats['last_run'] = state.get('last_run')
        except:
            pass
    
    # Check mode
    if ENV_FILE.exists():
        try:
            with open(ENV_FILE, 'r') as f:
                env_content = f.read()
                stats['mode'] = 'DRY RUN' if 'DRY_RUN_MODE=true' in env_content else 'LIVE'
        except:
            pass
    
    # Check cron
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True, timeout=5)
        if 'run_barbossa_v4' in result.stdout:
            stats['cron_enabled'] = True
            # Calculate next run (assuming 7 AM daily)
            from datetime import datetime, timedelta
            now = datetime.now()
            next_7am = now.replace(hour=7, minute=0, second=0, microsecond=0)
            if now.hour >= 7:
                next_7am += timedelta(days=1)
            stats['next_run'] = next_7am.isoformat()
    except:
        pass
    
    return jsonify(stats)