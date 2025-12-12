#!/usr/bin/env python3
"""
Barbossa v3.0 - Simple Web Portal
Shows work done, sessions, and changelogs.
"""

from flask import Flask, render_template_string, jsonify, send_file
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Support both Docker (/app) and local (~/) paths
WORK_DIR = Path(os.environ.get('BARBOSSA_DIR', '/app'))
if not WORK_DIR.exists():
    WORK_DIR = Path.home() / 'barbossa-engineer'

LOGS_DIR = WORK_DIR / 'logs'
CHANGELOGS_DIR = WORK_DIR / 'changelogs'
CONFIG_FILE = WORK_DIR / 'config' / 'repositories.json'
SESSIONS_FILE = WORK_DIR / 'sessions.json'

# Simple HTML template
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
        .container { max-width: 1200px; margin: 0 auto; }
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
        .status-running { background: #1f6feb; color: white; }
        .status-completed { background: #238636; color: white; }
        .status-failed { background: #da3633; color: white; }
        .status-idle { background: #30363d; color: #8b949e; }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
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

        .repo-list { list-style: none; }
        .repo-item {
            padding: 12px;
            background: #0d1117;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .repo-name { color: #58a6ff; font-weight: 600; }
        .repo-url { color: #8b949e; font-size: 12px; word-break: break-all; }

        .session-list { list-style: none; }
        .session-item {
            padding: 12px;
            background: #0d1117;
            border-radius: 6px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .session-info { flex: 1; }
        .session-repo { font-weight: 600; color: #c9d1d9; }
        .session-time { color: #8b949e; font-size: 12px; }
        .session-pr { color: #58a6ff; font-size: 12px; text-decoration: none; }
        .session-pr:hover { text-decoration: underline; }

        .changelog-list { list-style: none; max-height: 400px; overflow-y: auto; }
        .changelog-item {
            padding: 10px;
            border-bottom: 1px solid #21262d;
        }
        .changelog-item:last-child { border-bottom: none; }
        .changelog-name { color: #c9d1d9; font-size: 14px; }
        .changelog-date { color: #8b949e; font-size: 12px; }

        .log-viewer {
            background: #0d1117;
            border-radius: 6px;
            padding: 15px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 12px;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }

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

        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
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
                    {{ 'Running' if running else 'Idle' }}
                </span>
                <button class="refresh-btn" onclick="location.reload()">Refresh</button>
            </div>
        </header>

        <div class="grid">
            <!-- Repositories -->
            <div class="card">
                <h2>Repositories</h2>
                <ul class="repo-list">
                    {% for repo in repositories %}
                    <li class="repo-item">
                        <div class="repo-name">{{ repo.name }}</div>
                        <div class="repo-url">{{ repo.url }}</div>
                    </li>
                    {% endfor %}
                </ul>
            </div>

            <!-- Recent Sessions -->
            <div class="card">
                <h2>Recent Sessions</h2>
                {% if sessions %}
                <ul class="session-list">
                    {% for session in sessions[:10] %}
                    <li class="session-item">
                        <div class="session-info">
                            <div class="session-repo">{{ session.repository }}</div>
                            <div class="session-time">{{ session.started[:16] }}</div>
                            {% if session.pr_url %}
                            <a class="session-pr" href="{{ session.pr_url }}" target="_blank">View PR</a>
                            {% endif %}
                        </div>
                        <span class="status-badge status-{{ session.status }}">{{ session.status }}</span>
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <div class="empty-state">No sessions yet</div>
                {% endif %}
            </div>

            <!-- Changelogs -->
            <div class="card">
                <h2>Recent Changelogs</h2>
                {% if changelogs %}
                <ul class="changelog-list">
                    {% for cl in changelogs[:15] %}
                    <li class="changelog-item">
                        <div class="changelog-name">{{ cl.name }}</div>
                        <div class="changelog-date">{{ cl.date }}</div>
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <div class="empty-state">No changelogs yet</div>
                {% endif %}
            </div>

            <!-- Latest Log -->
            <div class="card" style="grid-column: 1 / -1;">
                <h2>Latest Output</h2>
                {% if latest_log %}
                <div class="log-viewer">{{ latest_log }}</div>
                {% else %}
                <div class="empty-state">No logs yet</div>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds if a session is running
        {% if running %}
        setTimeout(() => location.reload(), 30000);
        {% endif %}
    </script>
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
                # Limit to last 5000 chars
                if len(content) > 5000:
                    content = '...(truncated)...\n\n' + content[-5000:]
                return content
            except:
                return "Error reading log file"
    return None


def is_running():
    """Check if Barbossa is currently running"""
    sessions = load_sessions()
    if sessions:
        return sessions[0].get('status') == 'running'
    return False


@app.route('/')
def dashboard():
    """Main dashboard"""
    config = load_config()
    sessions = load_sessions()
    changelogs = get_changelogs()
    latest_log = get_latest_log()
    running = is_running()

    return render_template_string(
        DASHBOARD_HTML,
        repositories=config.get('repositories', []),
        sessions=sessions,
        changelogs=changelogs,
        latest_log=latest_log,
        running=running
    )


@app.route('/api/status')
def api_status():
    """API endpoint for status"""
    config = load_config()
    sessions = load_sessions()

    return jsonify({
        'version': '3.0.0',
        'running': is_running(),
        'repositories': len(config.get('repositories', [])),
        'total_sessions': len(sessions),
        'recent_sessions': sessions[:5]
    })


@app.route('/api/sessions')
def api_sessions():
    """API endpoint for sessions"""
    return jsonify(load_sessions())


@app.route('/api/changelogs')
def api_changelogs():
    """API endpoint for changelogs"""
    return jsonify(get_changelogs())


@app.route('/api/trigger/<repo_name>', methods=['POST'])
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
