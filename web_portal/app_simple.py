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
import subprocess
from datetime import datetime, timedelta
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

# Enhanced HTML template with much more info
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
        .container { max-width: 1600px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid #30363d;
            margin-bottom: 30px;
        }
        h1 { color: #58a6ff; font-size: 28px; }
        .version { color: #8b949e; font-size: 14px; }
        .header-right { display: flex; gap: 15px; align-items: center; }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }
        .status-running { background: #1f6feb; color: white; }
        .status-running::before {
            content: '';
            width: 8px;
            height: 8px;
            background: white;
            border-radius: 50%;
            animation: pulse 1.5s infinite;
        }
        .status-review { background: #d29922; color: white; }
        .status-completed { background: #238636; color: white; }
        .status-failed { background: #da3633; color: white; }
        .status-idle { background: #30363d; color: #8b949e; }
        .status-open { background: #238636; color: white; }
        .status-merged { background: #8957e5; color: white; }
        .status-closed { background: #da3633; color: white; }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
        }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; }
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
        }
        .card.full-width { grid-column: 1 / -1; }
        .card h2 {
            color: #58a6ff;
            font-size: 16px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .card h2 .icon {
            width: 20px;
            height: 20px;
            margin-right: 8px;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 18px;
            text-align: center;
        }
        .stat-value { font-size: 32px; font-weight: 700; color: #58a6ff; }
        .stat-value.warning { color: #d29922; }
        .stat-value.success { color: #238636; }
        .stat-value.danger { color: #da3633; }
        .stat-label { font-size: 12px; color: #8b949e; margin-top: 5px; text-transform: uppercase; letter-spacing: 0.5px; }

        /* Mode Indicator */
        .mode-banner {
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .mode-banner.create-mode {
            background: linear-gradient(135deg, #238636 0%, #161b22 100%);
            border: 1px solid #238636;
        }
        .mode-banner.review-mode {
            background: linear-gradient(135deg, #d29922 0%, #161b22 100%);
            border: 1px solid #d29922;
        }
        .mode-banner.idle-mode {
            background: #161b22;
            border: 1px solid #30363d;
        }
        .mode-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        .mode-banner.create-mode .mode-icon { background: rgba(35, 134, 54, 0.3); }
        .mode-banner.review-mode .mode-icon { background: rgba(210, 153, 34, 0.3); }
        .mode-banner.idle-mode .mode-icon { background: rgba(48, 54, 61, 0.5); }
        .mode-details h3 { font-size: 18px; color: white; margin-bottom: 4px; }
        .mode-details p { font-size: 13px; color: #8b949e; }
        .mode-details .next-run {
            margin-top: 8px;
            font-size: 12px;
            color: #58a6ff;
            background: rgba(88, 166, 255, 0.1);
            padding: 4px 10px;
            border-radius: 4px;
            display: inline-block;
        }

        /* Parallel Execution Panel */
        .parallel-panel {
            background: linear-gradient(135deg, #1f6feb22 0%, #161b22 100%);
            border: 1px solid #1f6feb44;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
        }
        .parallel-panel h3 {
            color: #58a6ff;
            font-size: 14px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .parallel-panel .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid #1f6feb;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .parallel-jobs {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        .job-card {
            background: #0d1117;
            border-radius: 8px;
            padding: 15px;
            border-left: 3px solid #1f6feb;
        }
        .job-card.completed { border-left-color: #238636; }
        .job-card.failed { border-left-color: #da3633; }
        .job-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .job-repo { font-weight: 600; color: #c9d1d9; }
        .job-time { color: #8b949e; font-size: 11px; }
        .job-progress {
            height: 4px;
            background: #30363d;
            border-radius: 2px;
            overflow: hidden;
            margin-top: 10px;
        }
        .job-progress-bar {
            height: 100%;
            background: #1f6feb;
            animation: progress 2s ease-in-out infinite;
        }
        @keyframes progress {
            0% { width: 0%; }
            50% { width: 70%; }
            100% { width: 100%; }
        }

        /* Repository Cards with PR Info */
        .repo-card {
            background: #0d1117;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 12px;
        }
        .repo-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .repo-name { font-weight: 600; color: #c9d1d9; font-size: 15px; }
        .repo-tech { color: #8b949e; font-size: 11px; background: #21262d; padding: 2px 8px; border-radius: 4px; }

        .pr-list { margin-top: 10px; }
        .pr-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px;
            background: #161b22;
            border-radius: 6px;
            margin-bottom: 6px;
            font-size: 12px;
        }
        .pr-number { color: #8b949e; font-weight: 600; }
        .pr-title { color: #c9d1d9; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .pr-status { padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }
        .pr-status.checks-pass { background: rgba(35, 134, 54, 0.2); color: #238636; }
        .pr-status.checks-fail { background: rgba(218, 54, 51, 0.2); color: #da3633; }
        .pr-status.checks-pending { background: rgba(210, 153, 34, 0.2); color: #d29922; }

        /* Session List */
        .session-list { list-style: none; }
        .session-item {
            padding: 15px;
            background: #0d1117;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 3px solid #30363d;
        }
        .session-item.running { border-left-color: #1f6feb; background: linear-gradient(90deg, rgba(31, 111, 235, 0.1) 0%, #0d1117 100%); }
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
        .session-meta { display: flex; gap: 15px; margin-top: 8px; flex-wrap: wrap; }
        .session-id { color: #8b949e; font-size: 11px; font-family: monospace; background: #21262d; padding: 2px 6px; border-radius: 4px; }

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

        .session-summary {
            margin-top: 10px;
            padding: 10px;
            background: #21262d;
            border-radius: 6px;
            font-size: 12px;
            line-height: 1.5;
            color: #8b949e;
        }

        /* Log Viewer */
        .log-viewer {
            background: #0d1117;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 12px;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
            line-height: 1.6;
        }

        /* Buttons */
        .btn {
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-primary { background: #238636; color: white; }
        .btn-primary:hover { background: #2ea043; }
        .btn-secondary { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
        .btn-secondary:hover { background: #30363d; }
        .btn-trigger { background: #1f6feb; color: white; }
        .btn-trigger:hover { background: #388bfd; }

        .empty-state {
            color: #8b949e;
            text-align: center;
            padding: 40px;
        }

        .trigger-buttons {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        .last-updated {
            color: #8b949e;
            font-size: 11px;
            text-align: right;
            margin-top: 20px;
        }

        @media (max-width: 1200px) {
            .stats-grid { grid-template-columns: repeat(3, 1fr); }
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
                <span class="version">v3.0.0 - Personal Dev Assistant | Schedule: Every 1 hour</span>
            </div>
            <div class="header-right">
                {% if running_sessions %}
                <span class="status-badge status-running">Working on {{ running_sessions|length }} repo(s)</span>
                {% else %}
                <span class="status-badge status-idle">Idle</span>
                {% endif %}
                <button class="btn btn-secondary" onclick="location.reload()">Refresh</button>
            </div>
        </header>

        <!-- Stats Overview -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ total_sessions }}</div>
                <div class="stat-label">Total Sessions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value success">{{ completed_sessions }}</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ prs_created }}</div>
                <div class="stat-label">PRs Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {{ 'warning' if total_open_prs > 5 else '' }}">{{ total_open_prs }}</div>
                <div class="stat-label">Open PRs</div>
            </div>
            <div class="stat-card">
                <div class="stat-value {{ 'danger' if failed_sessions > 0 else '' }}">{{ failed_sessions }}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ repositories|length }}</div>
                <div class="stat-label">Repos</div>
            </div>
        </div>

        <!-- Current Mode Banner -->
        <div class="mode-banner {{ 'review-mode' if total_open_prs > 5 else ('create-mode' if running_sessions else 'idle-mode') }}">
            <div class="mode-icon">
                {% if running_sessions %}
                    {% if total_open_prs > 5 %}
                    🔧
                    {% else %}
                    🚀
                    {% endif %}
                {% else %}
                ⏸️
                {% endif %}
            </div>
            <div class="mode-details">
                {% if running_sessions %}
                    {% if total_open_prs > 5 %}
                    <h3>Review Mode Active</h3>
                    <p>More than 5 open PRs detected. Barbossa is fixing existing PRs instead of creating new ones.</p>
                    {% else %}
                    <h3>Creating New PRs</h3>
                    <p>Running in parallel across {{ running_sessions|length }} repositories. Each session may take up to 30 minutes.</p>
                    {% endif %}
                {% else %}
                    <h3>Waiting for Next Run</h3>
                    <p>Barbossa runs every hour at :00. Sessions execute in parallel across all configured repositories.</p>
                {% endif %}
                <span class="next-run">Next run: {{ next_run }}</span>
            </div>
        </div>

        {% if running_sessions %}
        <!-- Parallel Execution Panel -->
        <div class="parallel-panel">
            <h3><span class="spinner"></span> Parallel Execution in Progress</h3>
            <div class="parallel-jobs">
                {% for session in running_sessions %}
                <div class="job-card">
                    <div class="job-header">
                        <span class="job-repo">{{ session.repository }}</span>
                        <span class="status-badge status-running">Running</span>
                    </div>
                    <div class="job-time">Started: {{ session.started[:19] }}</div>
                    <div class="session-id">{{ session.session_id }}</div>
                    <div class="job-progress">
                        <div class="job-progress-bar"></div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="grid">
            <!-- Repository Status with Open PRs -->
            <div class="card">
                <h2>
                    <span>Repositories & Open PRs</span>
                    <span style="font-size: 12px; color: #8b949e;">{{ total_open_prs }} open</span>
                </h2>
                {% for repo in repositories %}
                <div class="repo-card">
                    <div class="repo-header">
                        <span class="repo-name">{{ repo.name }}</span>
                        <span class="repo-tech">{{ repo.package_manager | default('npm') }}</span>
                    </div>
                    {% if repo.open_prs %}
                    <div class="pr-list">
                        {% for pr in repo.open_prs[:5] %}
                        <a href="{{ pr.url }}" target="_blank" class="pr-item" style="text-decoration: none;">
                            <span class="pr-number">#{{ pr.number }}</span>
                            <span class="pr-title">{{ pr.title }}</span>
                            {% if pr.checks_status == 'SUCCESS' %}
                            <span class="pr-status checks-pass">✓ Passing</span>
                            {% elif pr.checks_status == 'FAILURE' %}
                            <span class="pr-status checks-fail">✗ Failing</span>
                            {% else %}
                            <span class="pr-status checks-pending">◐ Pending</span>
                            {% endif %}
                        </a>
                        {% endfor %}
                        {% if repo.open_prs|length > 5 %}
                        <div style="color: #8b949e; font-size: 11px; padding: 5px;">+{{ repo.open_prs|length - 5 }} more</div>
                        {% endif %}
                    </div>
                    {% else %}
                    <div style="color: #8b949e; font-size: 12px;">No open PRs</div>
                    {% endif %}
                    <div class="trigger-buttons">
                        <button class="btn btn-trigger" onclick="triggerRun('{{ repo.name }}')">
                            Trigger Run
                        </button>
                    </div>
                </div>
                {% endfor %}
            </div>

            <!-- Recent Sessions -->
            <div class="card">
                <h2>Recent Sessions</h2>
                {% if sessions %}
                <ul class="session-list">
                    {% for session in sessions[:12] %}
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
                                    PR
                                </a>
                                {% endif %}
                                <a class="view-log-btn" href="/log/{{ session.session_id }}">Log</a>
                                <span class="status-badge status-{{ session.status }}">{{ session.status }}</span>
                            </div>
                        </div>
                        {% if session.summary %}
                        <div class="session-summary">{{ session.summary[:200] }}{% if session.summary|length > 200 %}...{% endif %}</div>
                        {% endif %}
                        <div class="session-meta">
                            <span class="session-id">{{ session.session_id[:20] }}...</span>
                            {% if session.completed %}
                            <span class="session-time">Done: {{ session.completed[:16] }}</span>
                            {% endif %}
                        </div>
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <div class="empty-state">No sessions yet. First run will start at the next hour.</div>
                {% endif %}
            </div>

            <!-- Latest Output -->
            <div class="card full-width">
                <h2>
                    <span>Latest Output</span>
                    <span style="font-size: 12px; color: #8b949e;">{{ latest_log_file }}</span>
                </h2>
                {% if latest_log %}
                <div class="log-viewer">{{ latest_log }}</div>
                {% else %}
                <div class="empty-state">No output yet</div>
                {% endif %}
            </div>
        </div>

        <div class="last-updated">Last updated: {{ now }}</div>
    </div>

    <script>
        function triggerRun(repoName) {
            if (confirm('Start a new Barbossa session for ' + repoName + '?')) {
                fetch('/api/trigger/' + repoName, { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert('Session started for ' + repoName);
                        setTimeout(() => location.reload(), 2000);
                    })
                    .catch(e => alert('Error: ' + e));
            }
        }

        // Auto-refresh
        {% if running_sessions %}
        setTimeout(() => location.reload(), 15000);  // 15s when running
        {% else %}
        setTimeout(() => location.reload(), 60000);  // 60s when idle
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
    <title>Log - {{ session.repository }} - {{ session_id[:12] }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .meta-item { }
        .meta-label { color: #8b949e; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
        .meta-value { color: #c9d1d9; font-size: 14px; margin-top: 4px; }
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
        .pr-link {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            color: #238636;
            text-decoration: none;
            font-weight: 600;
            padding: 6px 12px;
            background: rgba(35, 134, 54, 0.15);
            border-radius: 6px;
            margin-top: 4px;
        }
        .log-content {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 20px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 13px;
            line-height: 1.7;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 75vh;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Session Log: {{ session.repository }}</h1>
            <a class="back-btn" href="/">Back to Dashboard</a>
        </header>

        <div class="meta">
            <div class="meta-item">
                <div class="meta-label">Session ID</div>
                <div class="meta-value" style="font-family: monospace; font-size: 12px;">{{ session.session_id }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Repository</div>
                <div class="meta-value">{{ session.repository }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Started</div>
                <div class="meta-value">{{ session.started }}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Status</div>
                <div class="meta-value">
                    <span class="status-badge status-{{ session.status }}">{{ session.status }}</span>
                </div>
            </div>
            {% if session.completed %}
            <div class="meta-item">
                <div class="meta-label">Completed</div>
                <div class="meta-value">{{ session.completed }}</div>
            </div>
            {% endif %}
            {% if session.pr_url %}
            <div class="meta-item">
                <div class="meta-label">Pull Request</div>
                <a class="pr-link" href="{{ session.pr_url }}" target="_blank">
                    View PR →
                </a>
            </div>
            {% endif %}
        </div>

        <div class="log-content">{{ log_content }}</div>
    </div>

    {% if session.status == 'running' %}
    <script>
        setTimeout(() => location.reload(), 5000);
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


def get_open_prs_for_repo(owner, repo_name):
    """Fetch open PRs from GitHub for a repository"""
    try:
        result = subprocess.run(
            f"gh pr list --repo {owner}/{repo_name} --state open --json number,title,url,headRefName,checksStatusRaw --limit 10",
            shell=True,
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            prs = json.loads(result.stdout)
            # Process check status
            for pr in prs:
                checks = pr.get('checksStatusRaw', [])
                if not checks:
                    pr['checks_status'] = 'PENDING'
                elif all(c.get('conclusion') == 'SUCCESS' for c in checks if c.get('conclusion')):
                    pr['checks_status'] = 'SUCCESS'
                elif any(c.get('conclusion') == 'FAILURE' for c in checks):
                    pr['checks_status'] = 'FAILURE'
                else:
                    pr['checks_status'] = 'PENDING'
            return prs
    except Exception as e:
        pass
    return []


def get_latest_log():
    """Get content of latest non-empty log file"""
    if LOGS_DIR.exists():
        logs = sorted(LOGS_DIR.glob('claude_*.log'),
                     key=lambda x: x.stat().st_mtime, reverse=True)
        for log in logs:
            try:
                if log.stat().st_size > 0:
                    content = log.read_text()
                    if content.strip():
                        if len(content) > 4000:
                            content = '...(truncated)...\n\n' + content[-4000:]
                        return content, log.name
            except:
                continue
    return None, None


def get_log_for_session(session_id):
    """Get log content for a specific session"""
    sessions = load_sessions()
    session = next((s for s in sessions if s['session_id'] == session_id), None)

    if not session:
        return None, None

    output_file = session.get('output_file', '')
    log_path = Path(output_file)

    if not log_path.exists():
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


def get_running_sessions():
    """Get all currently running sessions"""
    sessions = load_sessions()
    return [s for s in sessions if s.get('status') == 'running']


def get_next_run_time():
    """Calculate next scheduled run time"""
    now = datetime.now()
    next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return next_hour.strftime('%H:%M')


def count_stats(sessions):
    """Calculate various stats from sessions"""
    return {
        'total': len(sessions),
        'completed': sum(1 for s in sessions if s.get('status') == 'completed'),
        'failed': sum(1 for s in sessions if s.get('status') == 'failed'),
        'prs': sum(1 for s in sessions if s.get('pr_url'))
    }


@app.route('/')
@requires_auth
def dashboard():
    """Main dashboard"""
    config = load_config()
    sessions = load_sessions()
    latest_log, latest_log_file = get_latest_log()
    running_sessions = get_running_sessions()
    stats = count_stats(sessions)

    # Get owner for GitHub API calls
    owner = config.get('owner', 'ADWilkinson')

    # Enrich repositories with open PR data
    repositories = config.get('repositories', [])
    total_open_prs = 0
    for repo in repositories:
        repo['open_prs'] = get_open_prs_for_repo(owner, repo['name'])
        total_open_prs += len(repo['open_prs'])

    return render_template_string(
        DASHBOARD_HTML,
        repositories=repositories,
        sessions=sessions,
        latest_log=latest_log,
        latest_log_file=latest_log_file or 'None',
        running_sessions=running_sessions,
        total_sessions=stats['total'],
        completed_sessions=stats['completed'],
        failed_sessions=stats['failed'],
        prs_created=stats['prs'],
        total_open_prs=total_open_prs,
        next_run=get_next_run_time(),
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    stats = count_stats(sessions)

    return jsonify({
        'version': '3.0.0',
        'running': len(get_running_sessions()) > 0,
        'running_sessions': get_running_sessions(),
        'repositories': len(config.get('repositories', [])),
        'total_sessions': stats['total'],
        'completed_sessions': stats['completed'],
        'failed_sessions': stats['failed'],
        'prs_created': stats['prs'],
        'next_run': get_next_run_time(),
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
    cmd = f"cd {WORK_DIR} && python3 barbossa_simple.py --repo {repo_name}"

    try:
        subprocess.Popen(cmd, shell=True, cwd=str(WORK_DIR))
        return jsonify({'status': 'started', 'repository': repo_name})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/prs')
@requires_auth
def api_prs():
    """API endpoint for all open PRs"""
    config = load_config()
    owner = config.get('owner', 'ADWilkinson')
    all_prs = {}

    for repo in config.get('repositories', []):
        all_prs[repo['name']] = get_open_prs_for_repo(owner, repo['name'])

    return jsonify(all_prs)


if __name__ == '__main__':
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
