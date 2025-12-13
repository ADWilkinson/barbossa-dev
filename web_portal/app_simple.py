#!/usr/bin/env python3
"""
Barbossa v3.0 - Web Portal
Enhanced dashboard showing work done, sessions, logs, and PR status.
"""

from flask import Flask, render_template_string, jsonify, request, Response
from functools import wraps
import json
import os
import re
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Basic Auth Configuration
AUTH_USERNAME = "barbossa"
AUTH_PASSWORD = "Galleon6242"

def check_auth(username, password):
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def authenticate():
    return Response(
        'Access denied. Please provide valid credentials.',
        401,
        {'WWW-Authenticate': 'Basic realm="Barbossa Portal"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Support both Docker (/app) and local (~/) paths
WORK_DIR = Path(os.environ.get('BARBOSSA_DIR', '/app'))
if not WORK_DIR.exists():
    WORK_DIR = Path.home() / 'barbossa-engineer'

LOGS_DIR = WORK_DIR / 'logs'
CHANGELOGS_DIR = WORK_DIR / 'changelogs'
CONFIG_FILE = WORK_DIR / 'config' / 'repositories.json'
SESSIONS_FILE = WORK_DIR / 'sessions.json'

# Enhanced HTML template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Barbossa - Personal Dev Assistant</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #30363d;
            margin-bottom: 30px;
        }
        h1 { color: #58a6ff; font-size: 24px; }
        .version { color: #8b949e; font-size: 14px; }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-running { background: #1f6feb; color: white; animation: pulse 2s infinite; }
        .status-completed { background: #238636; color: white; }
        .status-failed { background: #da3633; color: white; }
        .status-idle { background: #30363d; color: #8b949e; }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
        }
        .card h2 {
            color: #58a6ff;
            font-size: 16px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card h2::before {
            content: '';
            width: 8px;
            height: 8px;
            background: #58a6ff;
            border-radius: 50%;
        }

        .session-list { list-style: none; }
        .session-item {
            padding: 15px;
            background: #0d1117;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 3px solid #30363d;
        }
        .session-item.running { border-left-color: #1f6feb; }
        .session-item.completed { border-left-color: #238636; }
        .session-item.failed { border-left-color: #da3633; }

        .session-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .session-repo { font-weight: 600; color: #c9d1d9; font-size: 15px; }
        .session-time { color: #8b949e; font-size: 12px; }
        .session-meta { display: flex; gap: 15px; margin-top: 8px; }
        .session-id { color: #8b949e; font-size: 11px; font-family: monospace; }

        .pr-link {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            color: #238636;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            padding: 4px 10px;
            background: rgba(35, 134, 54, 0.15);
            border-radius: 4px;
        }
        .pr-link:hover { background: rgba(35, 134, 54, 0.25); }

        .view-log-btn {
            color: #58a6ff;
            text-decoration: none;
            font-size: 12px;
            padding: 4px 8px;
            border: 1px solid #30363d;
            border-radius: 4px;
        }
        .view-log-btn:hover { background: #21262d; }

        .log-viewer {
            background: #0d1117;
            border-radius: 6px;
            padding: 15px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
            line-height: 1.5;
        }

        .log-highlight { color: #58a6ff; }
        .log-success { color: #238636; }
        .log-error { color: #da3633; }
        .log-warning { color: #d29922; }

        .refresh-btn {
            background: #238636;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover { background: #2ea043; }

        .empty-state {
            color: #8b949e;
            text-align: center;
            padding: 40px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }
        .stat-value { font-size: 28px; font-weight: 700; color: #58a6ff; }
        .stat-label { font-size: 12px; color: #8b949e; margin-top: 5px; }

        .current-activity {
            background: linear-gradient(135deg, #1f6feb22 0%, #161b22 100%);
            border: 1px solid #1f6feb44;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .current-activity h3 {
            color: #58a6ff;
            font-size: 14px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .current-activity .spinner {
            width: 12px;
            height: 12px;
            border: 2px solid #1f6feb;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .activity-details {
            font-size: 13px;
            color: #c9d1d9;
        }
        .activity-details .repo { color: #58a6ff; font-weight: 600; }
        .activity-details .time { color: #8b949e; font-size: 11px; }

        .next-run {
            color: #8b949e;
            font-size: 12px;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #30363d;
        }

        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Barbossa</h1>
                <span class="version">v3.0.0 - Personal Dev Assistant</span>
            </div>
            <div>
                <span class="status-badge {{ 'status-running' if running else 'status-idle' }}">
                    {{ 'Working...' if running else 'Idle' }}
                </span>
                <button class="refresh-btn" onclick="location.reload()">Refresh</button>
            </div>
        </header>

        <!-- Stats Overview -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ total_sessions }}</div>
                <div class="stat-label">Total Sessions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ completed_sessions }}</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ prs_created }}</div>
                <div class="stat-label">PRs Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ repositories|length }}</div>
                <div class="stat-label">Repositories</div>
            </div>
        </div>

        {% if running and current_session %}
        <!-- Current Activity -->
        <div class="current-activity">
            <h3><span class="spinner"></span> Currently Working</h3>
            <div class="activity-details">
                <span class="repo">{{ current_session.repository }}</span> -
                Started <span class="time">{{ current_session.started[:19] }}</span>
                <br>
                <span class="session-id">Session: {{ current_session.session_id }}</span>
            </div>
            <div class="next-run">Next scheduled run: Every 4 hours (00:00, 04:00, 08:00, 12:00, 16:00, 20:00)</div>
        </div>
        {% endif %}

        <div class="grid">
            <!-- Recent Sessions -->
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Recent Sessions</h2>
                {% if sessions %}
                <ul class="session-list">
                    {% for session in sessions[:10] %}
                    <li class="session-item {{ session.status }}">
                        <div class="session-header">
                            <div>
                                <span class="session-repo">{{ session.repository }}</span>
                                <span class="session-time">{{ session.started[:16] }}</span>
                            </div>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                {% if session.pr_url %}
                                <a class="pr-link" href="{{ session.pr_url }}" target="_blank">
                                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                        <path fill-rule="evenodd" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
                                    </svg>
                                    View PR
                                </a>
                                {% endif %}
                                <a class="view-log-btn" href="/log/{{ session.session_id }}">View Log</a>
                                <span class="status-badge status-{{ session.status }}">{{ session.status }}</span>
                            </div>
                        </div>
                        <div class="session-meta">
                            <span class="session-id">{{ session.session_id }}</span>
                            {% if session.completed %}
                            <span class="session-time">Completed: {{ session.completed[:16] }}</span>
                            {% endif %}
                        </div>
                        {% if session.summary %}
                        <div style="margin-top: 10px; padding: 10px; background: #21262d; border-radius: 4px; font-size: 12px;">
                            {{ session.summary }}
                        </div>
                        {% endif %}
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <div class="empty-state">No sessions yet. First run scheduled at next 4-hour mark.</div>
                {% endif %}
            </div>

            <!-- Repositories -->
            <div class="card">
                <h2>Repositories</h2>
                <ul class="session-list">
                    {% for repo in repositories %}
                    <li class="session-item">
                        <div class="session-repo">{{ repo.name }}</div>
                        <div style="color: #8b949e; font-size: 12px; margin-top: 5px;">
                            {{ repo.package_manager | default('npm') }} | {{ repo.url }}
                        </div>
                    </li>
                    {% endfor %}
                </ul>
            </div>

            <!-- Latest Output -->
            <div class="card">
                <h2>Latest Output</h2>
                {% if latest_log %}
                <div class="log-viewer">{{ latest_log }}</div>
                {% else %}
                <div class="empty-state">No output yet</div>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds if a session is running
        {% if running %}
        setTimeout(() => location.reload(), 30000);
        {% else %}
        // Refresh every 5 minutes when idle
        setTimeout(() => location.reload(), 300000);
        {% endif %}
    </script>
</body>
</html>
"""

LOG_VIEWER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log Viewer - {{ session_id }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #30363d;
            margin-bottom: 20px;
        }
        h1 { color: #58a6ff; font-size: 20px; }
        .back-btn {
            color: #58a6ff;
            text-decoration: none;
            padding: 8px 16px;
            border: 1px solid #30363d;
            border-radius: 6px;
        }
        .back-btn:hover { background: #21262d; }
        .meta {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .meta-item { margin: 5px 0; font-size: 13px; }
        .meta-label { color: #8b949e; }
        .meta-value { color: #c9d1d9; }
        .pr-link {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            color: #238636;
            text-decoration: none;
            font-weight: 600;
            padding: 4px 10px;
            background: rgba(35, 134, 54, 0.15);
            border-radius: 4px;
        }
        .log-content {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 20px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 70vh;
            overflow-y: auto;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-running { background: #1f6feb; color: white; }
        .status-completed { background: #238636; color: white; }
        .status-failed { background: #da3633; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Session Log</h1>
            <a class="back-btn" href="/">Back to Dashboard</a>
        </header>

        <div class="meta">
            <div class="meta-item">
                <span class="meta-label">Session ID:</span>
                <span class="meta-value">{{ session.session_id }}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Repository:</span>
                <span class="meta-value">{{ session.repository }}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Started:</span>
                <span class="meta-value">{{ session.started }}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Status:</span>
                <span class="status-badge status-{{ session.status }}">{{ session.status }}</span>
            </div>
            {% if session.pr_url %}
            <div class="meta-item" style="margin-top: 10px;">
                <a class="pr-link" href="{{ session.pr_url }}" target="_blank">
                    View Pull Request
                </a>
            </div>
            {% endif %}
        </div>

        <div class="log-content">{{ log_content }}</div>
    </div>

    {% if session.status == 'running' %}
    <script>
        setTimeout(() => location.reload(), 10000);
    </script>
    {% endif %}
</body>
</html>
"""


def load_config():
    """Load repository configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'repositories': []}


def load_sessions():
    """Load sessions data"""
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def get_changelogs():
    """Get recent changelogs"""
    changelogs = []
    if CHANGELOGS_DIR.exists():
        files = sorted(CHANGELOGS_DIR.glob('*.md'),
                      key=lambda x: x.stat().st_mtime, reverse=True)[:15]
        for f in files:
            changelogs.append({
                'name': f.stem,
                'date': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
                'path': str(f)
            })
    return changelogs


def get_latest_log():
    """Get content of latest log file"""
    if LOGS_DIR.exists():
        logs = sorted(LOGS_DIR.glob('claude_*.log'),
                     key=lambda x: x.stat().st_mtime, reverse=True)
        if logs:
            try:
                content = logs[0].read_text()
                # Limit to last 3000 chars
                if len(content) > 3000:
                    content = '...(truncated)...\n\n' + content[-3000:]
                return content
            except:
                return "Error reading log file"
    return None


def get_log_for_session(session_id):
    """Get log content for a specific session"""
    sessions = load_sessions()
    session = next((s for s in sessions if s['session_id'] == session_id), None)

    if not session:
        return None, None

    # Try to find the log file
    output_file = session.get('output_file', '')
    log_path = Path(output_file)

    # Handle Docker vs local paths
    if not log_path.exists():
        # Try the mounted path
        log_name = log_path.name
        log_path = LOGS_DIR / log_name

    content = ""
    if log_path.exists():
        try:
            content = log_path.read_text()
        except:
            content = "Error reading log file"
    else:
        content = "Log file not found"

    return session, content


def is_running():
    """Check if Barbossa is currently running"""
    sessions = load_sessions()
    if sessions:
        return sessions[0].get('status') == 'running'
    return False


def get_current_session():
    """Get the current running session"""
    sessions = load_sessions()
    if sessions and sessions[0].get('status') == 'running':
        return sessions[0]
    return None


def count_prs():
    """Count sessions with PRs"""
    sessions = load_sessions()
    return sum(1 for s in sessions if s.get('pr_url'))


def count_completed():
    """Count completed sessions"""
    sessions = load_sessions()
    return sum(1 for s in sessions if s.get('status') == 'completed')


@app.route('/')
@requires_auth
def dashboard():
    """Main dashboard"""
    config = load_config()
    sessions = load_sessions()
    latest_log = get_latest_log()
    running = is_running()
    current_session = get_current_session()

    return render_template_string(
        DASHBOARD_HTML,
        repositories=config.get('repositories', []),
        sessions=sessions,
        latest_log=latest_log,
        running=running,
        current_session=current_session,
        total_sessions=len(sessions),
        completed_sessions=count_completed(),
        prs_created=count_prs()
    )


@app.route('/log/<session_id>')
@requires_auth
def view_log(session_id):
    """View log for a specific session"""
    session, log_content = get_log_for_session(session_id)

    if not session:
        return "Session not found", 404

    return render_template_string(
        LOG_VIEWER_HTML,
        session=session,
        log_content=log_content,
        session_id=session_id
    )


@app.route('/api/status')
@requires_auth
def api_status():
    """API endpoint for status"""
    config = load_config()
    sessions = load_sessions()

    return jsonify({
        'version': '3.0.0',
        'running': is_running(),
        'repositories': len(config.get('repositories', [])),
        'total_sessions': len(sessions),
        'completed_sessions': count_completed(),
        'prs_created': count_prs(),
        'recent_sessions': sessions[:5]
    })


@app.route('/api/sessions')
@requires_auth
def api_sessions():
    """API endpoint for sessions"""
    return jsonify(load_sessions())


@app.route('/api/log/<session_id>')
@requires_auth
def api_log(session_id):
    """API endpoint for session log"""
    session, log_content = get_log_for_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify({
        'session': session,
        'log': log_content
    })


@app.route('/api/trigger/<repo_name>', methods=['POST'])
@requires_auth
def api_trigger(repo_name):
    """Trigger a run for specific repository"""
    import subprocess

    cmd = f"python3 {WORK_DIR}/barbossa_simple.py --repo {repo_name}"

    try:
        subprocess.Popen(cmd, shell=True, cwd=str(WORK_DIR))
        return jsonify({'status': 'started', 'repository': repo_name})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    # Get SSL certs
    cert_file = WORK_DIR / 'web_portal' / 'eastindia.crt'
    key_file = WORK_DIR / 'web_portal' / 'eastindia.key'

    ssl_context = None
    if cert_file.exists() and key_file.exists():
        ssl_context = (str(cert_file), str(key_file))
        print(f"Starting with HTTPS on port 8443")
    else:
        print(f"Starting with HTTP on port 8080 (no SSL certs found)")

    app.run(
        host='0.0.0.0',
        port=8443 if ssl_context else 8080,
        ssl_context=ssl_context,
        debug=False
    )
