#!/usr/bin/env python3
"""
Barbossa v3.1 - Web Portal
Minimal black/off-white public dashboard with secure admin features.
"""

from flask import Flask, render_template_string, jsonify, request, Response
from functools import wraps
import json
import os
import re
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__)

# Basic Auth Configuration (for admin functions only)
AUTH_USERNAME = os.environ.get('BARBOSSA_USER', 'barbossa')
AUTH_PASSWORD = os.environ.get('BARBOSSA_PASS', 'Galleon6242')

def check_auth(username, password):
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def authenticate():
    return Response(
        'Access denied.',
        401,
        {'WWW-Authenticate': 'Basic realm="Barbossa Admin"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def is_authenticated():
    """Check if current request is authenticated"""
    auth = request.authorization
    return auth and check_auth(auth.username, auth.password)

# Support both Docker (/app) and local (~/) paths
WORK_DIR = Path(os.environ.get('BARBOSSA_DIR', '/app'))
if not WORK_DIR.exists():
    WORK_DIR = Path.home() / 'barbossa-engineer'

LOGS_DIR = WORK_DIR / 'logs'
CHANGELOGS_DIR = WORK_DIR / 'changelogs'
CONFIG_FILE = WORK_DIR / 'config' / 'repositories.json'
SESSIONS_FILE = WORK_DIR / 'sessions.json'
DECISIONS_FILE = WORK_DIR / 'tech_lead_decisions.json'
PENDING_FEEDBACK_FILE = WORK_DIR / 'pending_feedback.json'
SYSTEM_INSIGHTS_FILE = WORK_DIR / 'system_insights.json'
AUDIT_HISTORY_FILE = WORK_DIR / 'audit_history.json'


def obfuscate_session_id(session_id):
    """Obfuscate session ID for public display"""
    if not session_id:
        return ''
    return f"...{session_id[-6:]}"


def obfuscate_path(path):
    """Remove sensitive path information"""
    if not path:
        return ''
    return Path(path).name if path else ''


def sanitize_log_content(content):
    """Remove sensitive information from log content"""
    if not content:
        return ''
    # Remove file paths
    content = re.sub(r'/[\w/.-]+/barbossa-engineer/[^\s]+', '[path]', content)
    content = re.sub(r'/home/[\w]+/[^\s]+', '[path]', content)
    content = re.sub(r'/app/[^\s]+', '[path]', content)
    # Remove potential tokens/keys
    content = re.sub(r'(token|key|secret|password)["\s:=]+[\w-]+', r'\1=[REDACTED]', content, flags=re.IGNORECASE)
    return content


# Minimal Design HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Barbossa</title>
    <style>
        :root {
            --bg: #000;
            --bg-elevated: #0a0a0a;
            --bg-card: #111;
            --border: #222;
            --text: #f0f0f0;
            --text-muted: #666;
            --text-dim: #444;
            --accent: #fff;
            --success: #22c55e;
            --warning: #eab308;
            --danger: #ef4444;
            --purple: #a855f7;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro', 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 20px;
        }

        /* Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 32px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 48px;
        }

        .logo {
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.5px;
        }

        .logo span {
            color: var(--text-muted);
            font-weight: 400;
            font-size: 14px;
            margin-left: 12px;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 100px;
            font-size: 13px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--text-muted);
        }

        .status-dot.active {
            background: var(--success);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Stats Row */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 16px;
            margin-bottom: 48px;
        }

        .stat {
            text-align: center;
            padding: 24px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
        }

        .stat-value {
            font-size: 36px;
            font-weight: 600;
            letter-spacing: -1px;
            line-height: 1;
        }

        .stat-value.success { color: var(--success); }
        .stat-value.warning { color: var(--warning); }
        .stat-value.danger { color: var(--danger); }

        .stat-label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 8px;
        }

        /* Mode Banner */
        .mode-banner {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 48px;
        }

        .mode-indicator {
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            font-size: 20px;
        }

        .mode-content h2 {
            font-size: 18px;
            font-weight: 500;
            margin-bottom: 4px;
        }

        .mode-content p {
            font-size: 14px;
            color: var(--text-muted);
        }

        .mode-meta {
            margin-left: auto;
            text-align: right;
        }

        .next-run {
            font-size: 12px;
            color: var(--text-muted);
        }

        .next-run strong {
            color: var(--text);
            font-weight: 500;
        }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 24px;
        }

        @media (max-width: 900px) {
            .grid { grid-template-columns: 1fr; }
            .stats { grid-template-columns: repeat(3, 1fr); }
        }

        @media (max-width: 600px) {
            .stats { grid-template-columns: repeat(2, 1fr); }
            header { flex-direction: column; gap: 16px; text-align: center; }
            .mode-banner { flex-direction: column; text-align: center; }
            .mode-meta { margin-left: 0; margin-top: 16px; text-align: center; }
        }

        /* Cards */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
        }

        .card.full-width {
            grid-column: 1 / -1;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .card-title {
            font-size: 14px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-muted);
        }

        .card-meta {
            font-size: 12px;
            color: var(--text-dim);
        }

        /* Repository List */
        .repo-item {
            padding: 16px 0;
            border-bottom: 1px solid var(--border);
        }

        .repo-item:last-child {
            border-bottom: none;
            padding-bottom: 0;
        }

        .repo-item:first-child {
            padding-top: 0;
        }

        .repo-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .repo-name {
            font-weight: 500;
            font-size: 15px;
        }

        .repo-tech {
            font-size: 11px;
            color: var(--text-dim);
            background: var(--bg);
            padding: 4px 8px;
            border-radius: 4px;
        }

        .pr-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .pr-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            background: var(--bg);
            border-radius: 8px;
            text-decoration: none;
            color: inherit;
            transition: background 0.15s;
        }

        .pr-item:hover {
            background: var(--bg-elevated);
        }

        .pr-number {
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 500;
            min-width: 40px;
        }

        .pr-title {
            flex: 1;
            font-size: 13px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .pr-status {
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 500;
        }

        .pr-status.pass { background: rgba(34, 197, 94, 0.15); color: var(--success); }
        .pr-status.fail { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
        .pr-status.pending { background: rgba(234, 179, 8, 0.15); color: var(--warning); }

        /* Session List */
        .session-item {
            padding: 16px 0;
            border-bottom: 1px solid var(--border);
        }

        .session-item:last-child { border-bottom: none; padding-bottom: 0; }
        .session-item:first-child { padding-top: 0; }

        .session-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }

        .session-repo {
            font-weight: 500;
            font-size: 14px;
        }

        .session-time {
            font-size: 12px;
            color: var(--text-dim);
        }

        .session-badges {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .badge {
            font-size: 10px;
            padding: 4px 10px;
            border-radius: 100px;
            font-weight: 500;
        }

        .badge.running { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .badge.completed { background: rgba(34, 197, 94, 0.15); color: var(--success); }
        .badge.failed { background: rgba(239, 68, 68, 0.15); color: var(--danger); }

        .session-pr {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            color: var(--success);
            text-decoration: none;
            padding: 4px 10px;
            background: rgba(34, 197, 94, 0.1);
            border-radius: 4px;
            margin-top: 8px;
        }

        .session-pr:hover {
            background: rgba(34, 197, 94, 0.2);
        }

        /* Decision List */
        .decision-item {
            padding: 16px 0;
            border-bottom: 1px solid var(--border);
        }

        .decision-item:last-child { border-bottom: none; padding-bottom: 0; }
        .decision-item:first-child { padding-top: 0; }

        .decision-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
        }

        .decision-pr {
            font-size: 14px;
            font-weight: 500;
            color: inherit;
            text-decoration: none;
        }

        .decision-pr:hover {
            text-decoration: underline;
        }

        .decision-meta {
            font-size: 12px;
            color: var(--text-dim);
            margin-top: 2px;
        }

        .badge.merge { background: rgba(34, 197, 94, 0.15); color: var(--success); }
        .badge.close { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
        .badge.changes { background: rgba(234, 179, 8, 0.15); color: var(--warning); }

        .decision-reasoning {
            font-size: 13px;
            color: var(--text-muted);
            margin-top: 10px;
            padding: 12px;
            background: var(--bg);
            border-radius: 8px;
            line-height: 1.5;
        }

        .decision-scores {
            display: flex;
            gap: 16px;
            margin-top: 12px;
            font-size: 11px;
        }

        .score {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .score-label { color: var(--text-dim); }
        .score-value { font-weight: 600; }
        .score-value.high { color: var(--success); }
        .score-value.mid { color: var(--warning); }
        .score-value.low { color: var(--danger); }

        /* System Health Banner */
        .health-banner {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 20px 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 24px;
        }

        .health-banner.healthy { border-color: rgba(34, 197, 94, 0.3); }
        .health-banner.fair { border-color: rgba(234, 179, 8, 0.3); }
        .health-banner.poor { border-color: rgba(239, 68, 68, 0.3); }

        .health-score {
            width: 64px;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg);
            border: 2px solid var(--border);
            border-radius: 50%;
            font-size: 20px;
            font-weight: 600;
        }

        .health-score.healthy { border-color: var(--success); color: var(--success); }
        .health-score.fair { border-color: var(--warning); color: var(--warning); }
        .health-score.poor { border-color: var(--danger); color: var(--danger); }

        .health-details {
            flex: 1;
        }

        .health-issues {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
        }

        .health-issue {
            font-size: 11px;
            padding: 4px 10px;
            background: rgba(239, 68, 68, 0.1);
            color: var(--danger);
            border-radius: 4px;
        }

        .health-issue.warning {
            background: rgba(234, 179, 8, 0.1);
            color: var(--warning);
        }

        /* Tech Lead Banner */
        .tech-lead-banner {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 20px 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 24px;
        }

        .tech-lead-icon {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(168, 85, 247, 0.1);
            border-radius: 10px;
            color: var(--purple);
        }

        .tech-lead-stats {
            display: flex;
            gap: 24px;
            margin-left: auto;
        }

        .tl-stat {
            text-align: center;
        }

        .tl-stat-value {
            font-size: 20px;
            font-weight: 600;
        }

        .tl-stat-value.merged { color: var(--success); }
        .tl-stat-value.closed { color: var(--danger); }
        .tl-stat-value.changes { color: var(--warning); }

        .tl-stat-label {
            font-size: 10px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Pending Feedback */
        .feedback-item {
            padding: 12px;
            background: var(--bg);
            border-radius: 8px;
            margin-bottom: 8px;
        }

        .feedback-item:last-child { margin-bottom: 0; }

        .feedback-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .feedback-pr {
            font-size: 13px;
            font-weight: 500;
            color: var(--warning);
        }

        .feedback-time {
            font-size: 11px;
            color: var(--text-dim);
        }

        .feedback-text {
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.5;
        }

        /* Error Log */
        .error-item {
            padding: 10px 12px;
            background: var(--bg);
            border-radius: 6px;
            margin-bottom: 6px;
            border-left: 3px solid var(--danger);
        }

        .error-item:last-child { margin-bottom: 0; }

        .error-meta {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            color: var(--text-dim);
            margin-bottom: 4px;
        }

        .error-message {
            font-size: 11px;
            color: var(--text-muted);
            font-family: 'Monaco', 'Consolas', monospace;
            word-break: break-word;
        }

        /* Cron Schedule */
        .cron-schedule {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-top: 12px;
        }

        .cron-item {
            text-align: center;
            padding: 12px;
            background: var(--bg);
            border-radius: 8px;
        }

        .cron-agent {
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .cron-time {
            font-size: 14px;
            font-weight: 500;
            margin-top: 4px;
        }

        /* Empty State */
        .empty {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-dim);
            font-size: 14px;
        }

        /* Admin Controls */
        .admin-controls {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }

        .btn {
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 500;
            border: 1px solid var(--border);
            background: var(--bg);
            color: var(--text);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.15s;
        }

        .btn:hover {
            background: var(--bg-elevated);
            border-color: var(--text-dim);
        }

        .btn-primary {
            background: var(--text);
            color: var(--bg);
            border-color: var(--text);
        }

        .btn-primary:hover {
            background: var(--text-muted);
        }

        /* Footer */
        footer {
            margin-top: 64px;
            padding: 24px 0;
            border-top: 1px solid var(--border);
            text-align: center;
            font-size: 12px;
            color: var(--text-dim);
        }

        footer a {
            color: var(--text-muted);
            text-decoration: none;
        }

        footer a:hover {
            color: var(--text);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                Barbossa
            </div>
            <div class="status-pill">
                <span class="status-dot {{ 'active' if running_sessions else '' }}"></span>
                {% if running_sessions %}
                    Working on {{ running_sessions|length }} repo{{ 's' if running_sessions|length > 1 else '' }}
                {% else %}
                    Idle
                {% endif %}
            </div>
        </header>

        <!-- Stats -->
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{{ total_sessions }}</div>
                <div class="stat-label">Runs</div>
            </div>
            <div class="stat">
                <div class="stat-value success">{{ completed_sessions }}</div>
                <div class="stat-label">Done</div>
            </div>
            <div class="stat">
                <div class="stat-value">{{ prs_created }}</div>
                <div class="stat-label">PRs</div>
            </div>
            <div class="stat">
                <div class="stat-value {{ 'warning' if total_open_prs > 5 else '' }}">{{ total_open_prs }}</div>
                <div class="stat-label">Open</div>
            </div>
            <div class="stat">
                <div class="stat-value {{ 'danger' if failed_sessions > 0 else '' }}">{{ failed_sessions }}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat">
                <div class="stat-value">{{ repositories|length }}</div>
                <div class="stat-label">Repos</div>
            </div>
        </div>

        <!-- Mode Banner -->
        <div class="mode-banner">
            <div class="mode-indicator">
                {% if running_sessions %}
                    {% if revision_mode %}+{% else %}+{% endif %}
                {% else %}
                    =
                {% endif %}
            </div>
            <div class="mode-content">
                {% if running_sessions %}
                    {% if revision_mode %}
                        <h2>Fixing PRs</h2>
                        <p>Addressing review feedback before shipping new work</p>
                    {% else %}
                        <h2>Shipping</h2>
                        <p>Finding and fixing things across repos</p>
                    {% endif %}
                {% else %}
                    <h2>Idle</h2>
                    <p>Runs every hour on the hour</p>
                {% endif %}
            </div>
            <div class="mode-meta">
                <div class="next-run">Next: <strong>{{ next_run }}</strong></div>
            </div>
        </div>

        <!-- System Health Banner -->
        {% if system_health %}
        <div class="health-banner {{ system_health.status }}">
            <div class="health-score {{ system_health.status }}">{{ system_health.health_score }}</div>
            <div class="health-details">
                <div style="font-weight: 500; font-size: 14px;">System Health</div>
                <div style="font-size: 12px; color: var(--text-dim);">
                    Last audit: {{ system_health.last_audit[:16] if system_health.last_audit else 'Never' }}
                </div>
                {% if system_health.system_issues %}
                <div class="health-issues">
                    {% for issue in system_health.system_issues[:3] %}
                    <span class="health-issue">{{ issue[:50] }}{% if issue|length > 50 %}...{% endif %}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </div>
            {% if is_admin %}
            <button class="btn" onclick="triggerAuditor()">Run Audit</button>
            {% endif %}
        </div>
        {% endif %}

        <!-- Tech Lead Banner -->
        {% if tech_lead_decisions %}
        <div class="tech-lead-banner">
            <div class="tech-lead-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 12l2 2 4-4"/>
                    <circle cx="12" cy="12" r="10"/>
                </svg>
            </div>
            <div>
                <div style="font-weight: 500; font-size: 14px;">Reviewer</div>
                <div style="font-size: 12px; color: var(--text-dim);">Merges good PRs, closes bad ones</div>
            </div>
            <div class="tech-lead-stats">
                <div class="tl-stat">
                    <div class="tl-stat-value merged">{{ tech_lead_merged }}</div>
                    <div class="tl-stat-label">Merged</div>
                </div>
                <div class="tl-stat">
                    <div class="tl-stat-value closed">{{ tech_lead_closed }}</div>
                    <div class="tl-stat-label">Closed</div>
                </div>
                <div class="tl-stat">
                    <div class="tl-stat-value changes">{{ tech_lead_changes }}</div>
                    <div class="tl-stat-label">Changes</div>
                </div>
            </div>
            {% if is_admin %}
            <button class="btn" onclick="triggerTechLead()">Run Review</button>
            {% endif %}
        </div>
        {% endif %}

        <div class="grid">
            <!-- Repositories -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Repos</div>
                    <div class="card-meta">{{ total_open_prs }} open</div>
                </div>
                {% for repo in repositories %}
                <div class="repo-item">
                    <div class="repo-header">
                        <span class="repo-name">{{ repo.name }}</span>
                        <span class="repo-tech">{{ repo.package_manager | default('npm') }}</span>
                    </div>
                    {% if repo.open_prs %}
                    <div class="pr-list">
                        {% for pr in repo.open_prs[:4] %}
                        <a href="{{ pr.url }}" target="_blank" rel="noopener" class="pr-item">
                            <span class="pr-number">#{{ pr.number }}</span>
                            <span class="pr-title">{{ pr.title }}</span>
                            {% if pr.checks_status == 'SUCCESS' %}
                            <span class="pr-status pass">Pass</span>
                            {% elif pr.checks_status == 'FAILURE' %}
                            <span class="pr-status fail">Fail</span>
                            {% else %}
                            <span class="pr-status pending">...</span>
                            {% endif %}
                        </a>
                        {% endfor %}
                    </div>
                    {% else %}
                    <div style="color: var(--text-dim); font-size: 13px;">No open PRs</div>
                    {% endif %}
                    {% if is_admin %}
                    <div class="admin-controls">
                        <button class="btn" onclick="triggerRun('{{ repo.name }}')">Run now</button>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>

            <!-- Recent Sessions -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Activity</div>
                </div>
                {% if sessions %}
                    {% for session in sessions[:8] %}
                    <div class="session-item">
                        <div class="session-header">
                            <div>
                                <div class="session-repo">{{ session.repository }}</div>
                                <div class="session-time">{{ session.started[:16] if session.started else '' }}</div>
                            </div>
                            <div class="session-badges">
                                <span class="badge {{ session.status }}">{{ session.status }}</span>
                            </div>
                        </div>
                        {% if session.pr_url %}
                        <a href="{{ session.pr_url }}" target="_blank" rel="noopener" class="session-pr">
                            View PR
                        </a>
                        {% endif %}
                    </div>
                    {% endfor %}
                {% else %}
                <div class="empty">No sessions yet</div>
                {% endif %}
            </div>

            <!-- Tech Lead Decisions -->
            <div class="card full-width">
                <div class="card-header">
                    <div class="card-title">Review Log</div>
                    <div class="card-meta">What got merged, closed, or sent back</div>
                </div>
                {% if tech_lead_decisions %}
                    {% for decision in tech_lead_decisions[:6] %}
                    <div class="decision-item">
                        <div class="decision-header">
                            <div>
                                <a href="{{ decision.pr_url }}" target="_blank" rel="noopener" class="decision-pr">
                                    {{ decision.pr_title[:60] }}{% if decision.pr_title|length > 60 %}...{% endif %}
                                </a>
                                <div class="decision-meta">{{ decision.repository }} · {{ decision.timestamp[:10] if decision.timestamp else '' }}</div>
                            </div>
                            {% if decision.decision == 'MERGE' %}
                            <span class="badge merge">Merged</span>
                            {% elif decision.decision == 'CLOSE' %}
                            <span class="badge close">Closed</span>
                            {% else %}
                            <span class="badge changes">Changes</span>
                            {% endif %}
                        </div>
                        <div class="decision-reasoning">{{ decision.reasoning[:180] }}{% if decision.reasoning|length > 180 %}...{% endif %}</div>
                        <div class="decision-scores">
                            <div class="score">
                                <span class="score-label">Value</span>
                                <span class="score-value {{ 'high' if decision.value_score >= 7 else ('low' if decision.value_score <= 3 else 'mid') }}">{{ decision.value_score }}/10</span>
                            </div>
                            <div class="score">
                                <span class="score-label">Quality</span>
                                <span class="score-value {{ 'high' if decision.quality_score >= 7 else ('low' if decision.quality_score <= 3 else 'mid') }}">{{ decision.quality_score }}/10</span>
                            </div>
                            <div class="score">
                                <span class="score-label">Risk</span>
                                <span class="score-value {{ 'high' if decision.bloat_risk == 'LOW' else ('low' if decision.bloat_risk == 'HIGH' else 'mid') }}">{{ decision.bloat_risk }}</span>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                <div class="empty">No decisions yet</div>
                {% endif %}
            </div>

            <!-- Pending Feedback -->
            {% if pending_feedback %}
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Awaiting Fixes</div>
                    <div class="card-meta">{{ pending_feedback|length }} PR{{ 's' if pending_feedback|length > 1 else '' }} need attention</div>
                </div>
                {% for key, item in pending_feedback.items() %}
                <div class="feedback-item">
                    <div class="feedback-header">
                        <span class="feedback-pr">{{ item.repo }}#{{ item.pr_number }}</span>
                        <span class="feedback-time">{{ item.timestamp[:10] if item.timestamp else '' }}</span>
                    </div>
                    <div class="feedback-text">{{ item.feedback[:150] }}{% if item.feedback|length > 150 %}...{% endif %}</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <!-- Recent Errors -->
            {% if recent_errors and is_admin %}
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Recent Errors</div>
                    <div class="card-meta">From system logs</div>
                </div>
                {% for error in recent_errors[:5] %}
                <div class="error-item">
                    <div class="error-meta">
                        <span>{{ error.file }}</span>
                        <span>{{ error.timestamp[:16] if error.timestamp else '' }}</span>
                    </div>
                    <div class="error-message">{{ error.message[:120] }}{% if error.message|length > 120 %}...{% endif %}</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <!-- PR Metrics -->
            {% if total_decisions > 0 %}
            <div class="card">
                <div class="card-header">
                    <div class="card-title">PR Analytics</div>
                    <div class="card-meta">{{ total_decisions }} total</div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 16px;">
                    <div style="text-align: center; padding: 16px; background: var(--bg); border-radius: 8px;">
                        <div style="font-size: 24px; font-weight: 600; color: var(--success);">{{ merge_rate }}%</div>
                        <div style="font-size: 11px; color: var(--text-dim); text-transform: uppercase;">Merge Rate</div>
                    </div>
                    <div style="text-align: center; padding: 16px; background: var(--bg); border-radius: 8px;">
                        <div style="font-size: 24px; font-weight: 600; color: {{ 'var(--danger)' if test_only_count > 5 else 'var(--text)' }};">{{ test_only_count }}</div>
                        <div style="font-size: 11px; color: var(--text-dim); text-transform: uppercase;">Test-only PRs</div>
                    </div>
                </div>
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Type Distribution</div>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    {% for pr_type, count in pr_types.items() %}
                    <div style="padding: 6px 12px; background: var(--bg); border-radius: 6px; font-size: 12px;">
                        <span style="color: {{ 'var(--danger)' if pr_type == 'test' else 'var(--text)' }};">{{ pr_type }}</span>
                        <span style="color: var(--text-dim); margin-left: 4px;">{{ count }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            <!-- Cron Schedule -->
            <div class="card {{ 'full-width' if not pending_feedback and not (recent_errors and is_admin) and total_decisions == 0 else '' }}">
                <div class="card-header">
                    <div class="card-title">Schedule</div>
                    <div class="card-meta">Automated runs</div>
                </div>
                <div class="cron-schedule">
                    <div class="cron-item">
                        <div class="cron-agent">Tech Lead</div>
                        <div class="cron-time">:45</div>
                    </div>
                    <div class="cron-item">
                        <div class="cron-agent">Engineer</div>
                        <div class="cron-time">:00</div>
                    </div>
                    <div class="cron-item">
                        <div class="cron-agent">Auditor</div>
                        <div class="cron-time">6:30 AM</div>
                    </div>
                </div>
                <div style="margin-top: 16px; font-size: 12px; color: var(--text-dim);">
                    Next engineer run: <strong style="color: var(--text);">{{ next_run }}</strong>
                </div>
            </div>
        </div>

        <footer>
            Barbossa v3.1 · Updated {{ now }}
            {% if is_admin %}
            · <a href="/admin">Admin Panel</a>
            {% endif %}
        </footer>
    </div>

    {% if is_admin %}
    <script>
        function triggerRun(repoName) {
            if (confirm('Start Barbossa session for ' + repoName + '?')) {
                fetch('/api/trigger/' + repoName, { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert('Started: ' + repoName);
                        setTimeout(() => location.reload(), 2000);
                    })
                    .catch(e => alert('Error: ' + e));
            }
        }

        function triggerTechLead() {
            if (confirm('Start Tech Lead PR review session?')) {
                fetch('/api/tech-lead/trigger', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert('Tech Lead review started');
                        setTimeout(() => location.reload(), 2000);
                    })
                    .catch(e => alert('Error: ' + e));
            }
        }

        function triggerAuditor() {
            if (confirm('Run system health audit?')) {
                fetch('/api/auditor/trigger', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        alert('Auditor started');
                        setTimeout(() => location.reload(), 3000);
                    })
                    .catch(e => alert('Error: ' + e));
            }
        }
    </script>
    {% endif %}

    <script>
        // Auto-refresh
        setTimeout(() => location.reload(), {{ '15000' if running_sessions else '60000' }});
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
    <title>Session Log</title>
    <style>
        :root {
            --bg: #000;
            --bg-card: #111;
            --border: #222;
            --text: #f0f0f0;
            --text-muted: #666;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 24px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }
        h1 { font-size: 18px; font-weight: 500; }
        .back {
            color: var(--text-muted);
            text-decoration: none;
            font-size: 14px;
        }
        .back:hover { color: var(--text); }
        .meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            padding: 20px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 24px;
        }
        .meta-label {
            font-size: 10px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .meta-value {
            font-size: 14px;
            margin-top: 4px;
        }
        .log {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 12px;
            line-height: 1.7;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 70vh;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ session.repository }} · {{ session_id_display }}</h1>
            <a class="back" href="/">Back</a>
        </header>
        <div class="meta">
            <div>
                <div class="meta-label">Repository</div>
                <div class="meta-value">{{ session.repository }}</div>
            </div>
            <div>
                <div class="meta-label">Started</div>
                <div class="meta-value">{{ session.started[:16] if session.started else 'N/A' }}</div>
            </div>
            <div>
                <div class="meta-label">Status</div>
                <div class="meta-value">{{ session.status }}</div>
            </div>
            {% if session.pr_url %}
            <div>
                <div class="meta-label">PR</div>
                <div class="meta-value"><a href="{{ session.pr_url }}" target="_blank" style="color: #22c55e;">View PR</a></div>
            </div>
            {% endif %}
        </div>
        <div class="log">{{ log_content }}</div>
    </div>
    {% if session.status == 'running' %}
    <script>setTimeout(() => location.reload(), 5000);</script>
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


def load_tech_lead_decisions():
    """Load tech lead decisions data"""
    if DECISIONS_FILE.exists():
        try:
            with open(DECISIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def load_pending_feedback():
    """Load pending feedback waiting for Senior Engineer"""
    if PENDING_FEEDBACK_FILE.exists():
        try:
            with open(PENDING_FEEDBACK_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def load_system_insights():
    """Load system health insights from auditor"""
    if SYSTEM_INSIGHTS_FILE.exists():
        try:
            with open(SYSTEM_INSIGHTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def load_audit_history():
    """Load audit history"""
    if AUDIT_HISTORY_FILE.exists():
        try:
            with open(AUDIT_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def get_recent_errors(limit=10):
    """Get recent errors from log files"""
    errors = []
    try:
        log_files = sorted(LOGS_DIR.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)[:20]
        for log_file in log_files:
            try:
                content = log_file.read_text()
                for line in content.split('\n'):
                    if 'ERROR' in line or 'error' in line.lower() and 'error_count' not in line.lower():
                        # Extract timestamp and message
                        parts = line.split(' - ', 2)
                        if len(parts) >= 3:
                            errors.append({
                                'timestamp': parts[0],
                                'level': parts[1],
                                'message': parts[2][:200],
                                'file': log_file.name
                            })
                        elif len(line) > 20:
                            errors.append({
                                'timestamp': '',
                                'level': 'ERROR',
                                'message': line[:200],
                                'file': log_file.name
                            })
                        if len(errors) >= limit:
                            break
            except:
                continue
            if len(errors) >= limit:
                break
    except:
        pass
    return errors[:limit]


def count_tech_lead_stats(decisions):
    """Calculate tech lead decision stats"""
    return {
        'merged': sum(1 for d in decisions if d.get('decision') == 'MERGE' and d.get('executed')),
        'closed': sum(1 for d in decisions if d.get('decision') == 'CLOSE' and d.get('executed')),
        'changes': sum(1 for d in decisions if d.get('decision') == 'REQUEST_CHANGES' and d.get('executed'))
    }


def get_next_tech_lead_run():
    """Calculate next tech lead scheduled run time (every hour at :45)"""
    now = datetime.now()
    if now.minute < 45:
        # Next run is :45 of current hour
        next_run = now.replace(minute=45, second=0, microsecond=0)
    else:
        # Next run is :45 of next hour
        next_run = (now.replace(minute=45, second=0, microsecond=0) + timedelta(hours=1))
    return next_run.strftime('%H:%M')


def get_open_prs_for_repo(owner, repo_name):
    """Fetch open PRs from GitHub"""
    try:
        result = subprocess.run(
            f"gh pr list --repo {owner}/{repo_name} --state open --json number,title,url,headRefName,statusCheckRollup,mergeable --limit 10",
            shell=True,
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            prs = json.loads(result.stdout)
            for pr in prs:
                checks = pr.get('statusCheckRollup', [])
                if not checks:
                    pr['checks_status'] = 'PENDING'
                else:
                    # Check for failures first
                    has_failure = any(
                        c.get('conclusion') == 'FAILURE' or c.get('state') == 'FAILURE'
                        for c in checks
                    )
                    # Check if all completed checks passed
                    all_success = all(
                        c.get('conclusion') in ('SUCCESS', 'NEUTRAL', 'SKIPPED') or c.get('state') == 'SUCCESS'
                        for c in checks
                        if c.get('status') == 'COMPLETED' or c.get('state')
                    )

                    if has_failure:
                        pr['checks_status'] = 'FAILURE'
                    elif all_success and checks:
                        pr['checks_status'] = 'SUCCESS'
                    else:
                        pr['checks_status'] = 'PENDING'

                # Add merge status info
                pr['mergeable'] = pr.get('mergeable', 'UNKNOWN')
            return prs
    except Exception:
        pass
    return []


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
            content = sanitize_log_content(content)
        except:
            content = "Error reading log file"
    else:
        content = "Log file not found"

    return session, content


@app.route('/')
def dashboard():
    """Main public dashboard"""
    admin = is_authenticated()
    config = load_config()
    sessions = load_sessions()
    running_sessions = get_running_sessions()
    stats = count_stats(sessions)

    owner = config.get('owner', 'ADWilkinson')

    repositories = config.get('repositories', [])
    total_open_prs = 0
    for repo in repositories:
        repo['open_prs'] = get_open_prs_for_repo(owner, repo['name'])
        total_open_prs += len(repo['open_prs'])

    tech_lead_decisions = load_tech_lead_decisions()
    tech_lead_stats = count_tech_lead_stats(tech_lead_decisions)

    # Load new data sources
    pending_feedback = load_pending_feedback()
    system_health = load_system_insights()
    recent_errors = get_recent_errors(10) if admin else []

    # Check if in revision mode (has PRs needing attention)
    revision_mode = any(
        pr.get('reviewDecision') == 'CHANGES_REQUESTED' or
        pr.get('checks_status') == 'FAILURE'
        for repo in repositories
        for pr in repo.get('open_prs', [])
    )

    # Calculate metrics for dashboard
    pr_types = {}
    for d in tech_lead_decisions:
        title = d.get('pr_title', '')
        if ':' in title:
            pr_type = title.split(':')[0].split('(')[0].strip().lower()
        else:
            pr_type = 'other'
        pr_types[pr_type] = pr_types.get(pr_type, 0) + 1

    total_decisions = len(tech_lead_decisions)
    merge_rate = (tech_lead_stats['merged'] / total_decisions * 100) if total_decisions > 0 else 0
    test_only_count = pr_types.get('test', 0)

    return render_template_string(
        DASHBOARD_HTML,
        repositories=repositories,
        sessions=sessions,
        running_sessions=running_sessions,
        total_sessions=stats['total'],
        completed_sessions=stats['completed'],
        failed_sessions=stats['failed'],
        prs_created=stats['prs'],
        total_open_prs=total_open_prs,
        next_run=get_next_run_time(),
        revision_mode=revision_mode,
        tech_lead_decisions=tech_lead_decisions,
        tech_lead_merged=tech_lead_stats['merged'],
        tech_lead_closed=tech_lead_stats['closed'],
        tech_lead_changes=tech_lead_stats['changes'],
        pending_feedback=pending_feedback,
        system_health=system_health,
        recent_errors=recent_errors,
        is_admin=admin,
        now=datetime.now().strftime('%Y-%m-%d %H:%M'),
        # Metrics
        pr_types=pr_types,
        merge_rate=round(merge_rate, 1),
        test_only_count=test_only_count,
        total_decisions=total_decisions
    )


@app.route('/log/<session_id>')
@requires_auth
def view_log(session_id):
    """View log for a specific session (admin only)"""
    session, log_content = get_log_for_session(session_id)

    if not session:
        return "Session not found", 404

    return render_template_string(
        LOG_VIEWER_HTML,
        session=session,
        log_content=log_content,
        session_id_display=obfuscate_session_id(session_id)
    )


@app.route('/admin')
@requires_auth
def admin_panel():
    """Redirect admin to dashboard with auth"""
    return dashboard()


# API Endpoints (protected)

@app.route('/api/status')
def api_status():
    """API endpoint for status (public, sanitized)"""
    sessions = load_sessions()
    stats = count_stats(sessions)
    running = get_running_sessions()

    return jsonify({
        'version': '3.1.0',
        'running': len(running) > 0,
        'sessions': stats['total'],
        'completed': stats['completed'],
        'prs_created': stats['prs'],
        'next_run': get_next_run_time()
    })


@app.route('/api/sessions')
@requires_auth
def api_sessions():
    """API endpoint for sessions (admin only)"""
    return jsonify(load_sessions())


@app.route('/api/trigger/<repo_name>', methods=['POST'])
@requires_auth
def api_trigger(repo_name):
    """Trigger a run for specific repository (admin only)"""
    # Run as barbossa user (Claude CLI rejects root)
    cmd = f"su - barbossa -c 'cd {WORK_DIR} && python3 barbossa_simple.py --repo {repo_name}'"
    try:
        subprocess.Popen(cmd, shell=True, cwd=str(WORK_DIR))
        return jsonify({'status': 'started', 'repository': repo_name})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/prs')
def api_prs():
    """API endpoint for all open PRs (public)"""
    config = load_config()
    owner = config.get('owner', 'ADWilkinson')
    all_prs = {}

    for repo in config.get('repositories', []):
        prs = get_open_prs_for_repo(owner, repo['name'])
        all_prs[repo['name']] = [{'number': p['number'], 'title': p['title'], 'status': p['checks_status']} for p in prs]

    return jsonify(all_prs)


@app.route('/api/tech-lead/decisions')
def api_tech_lead_decisions():
    """API endpoint for tech lead decisions (public, sanitized)"""
    decisions = load_tech_lead_decisions()
    stats = count_tech_lead_stats(decisions)

    # Sanitize for public
    public_decisions = []
    for d in decisions[:20]:
        public_decisions.append({
            'pr_title': d.get('pr_title', ''),
            'repository': d.get('repository', ''),
            'decision': d.get('decision', ''),
            'value_score': d.get('value_score', 0),
            'quality_score': d.get('quality_score', 0),
            'bloat_risk': d.get('bloat_risk', ''),
            'timestamp': d.get('timestamp', '')[:10] if d.get('timestamp') else ''
        })

    return jsonify({
        'decisions': public_decisions,
        'stats': stats
    })


@app.route('/api/tech-lead/trigger', methods=['POST'])
@requires_auth
def api_tech_lead_trigger():
    """Trigger a tech lead review run (admin only)"""
    # Run as barbossa user (Claude CLI rejects root)
    cmd = f"su - barbossa -c 'cd {WORK_DIR} && python3 barbossa_tech_lead.py'"
    try:
        subprocess.Popen(cmd, shell=True, cwd=str(WORK_DIR))
        return jsonify({'status': 'started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/auditor/trigger', methods=['POST'])
@requires_auth
def api_auditor_trigger():
    """Trigger a system health audit (admin only)"""
    # Run as barbossa user
    cmd = f"su - barbossa -c 'cd {WORK_DIR} && python3 barbossa_auditor.py --days 7'"
    try:
        subprocess.Popen(cmd, shell=True, cwd=str(WORK_DIR))
        return jsonify({'status': 'started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/system-health')
def api_system_health():
    """API endpoint for system health data (public)"""
    health = load_system_insights()
    return jsonify({
        'health_score': health.get('health_score', 0),
        'status': health.get('status', 'unknown'),
        'last_audit': health.get('last_audit', ''),
        'merge_rates': health.get('merge_rates', {}),
        'error_count': health.get('error_count', 0),
        'system_issues': health.get('system_issues', [])
    })


@app.route('/api/pending-feedback')
def api_pending_feedback():
    """API endpoint for pending feedback (public)"""
    feedback = load_pending_feedback()
    return jsonify({
        'count': len(feedback),
        'items': list(feedback.values())
    })


@app.route('/api/metrics')
def api_metrics():
    """API endpoint for system metrics and PR analytics"""
    config = load_config()
    owner = config.get('owner', 'ADWilkinson')
    decisions = load_tech_lead_decisions()
    sessions = load_sessions()

    # Calculate PR type distribution from decisions
    pr_types = {}
    for d in decisions:
        title = d.get('pr_title', '')
        # Extract type prefix (feat, fix, test, refactor, etc.)
        if ':' in title:
            pr_type = title.split(':')[0].split('(')[0].strip().lower()
        else:
            pr_type = 'other'
        pr_types[pr_type] = pr_types.get(pr_type, 0) + 1

    # Calculate merge rate
    total_decisions = len(decisions)
    merged = sum(1 for d in decisions if d.get('decision') == 'MERGE')
    closed = sum(1 for d in decisions if d.get('decision') == 'CLOSE')
    merge_rate = (merged / total_decisions * 100) if total_decisions > 0 else 0

    # Calculate average scores
    value_scores = [d.get('value_score', 0) for d in decisions if d.get('value_score')]
    quality_scores = [d.get('quality_score', 0) for d in decisions if d.get('quality_score')]
    avg_value = sum(value_scores) / len(value_scores) if value_scores else 0
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

    # Session stats
    completed_sessions = sum(1 for s in sessions if s.get('status') == 'completed')
    failed_sessions = sum(1 for s in sessions if s.get('status') in ('failed', 'error', 'timeout'))
    success_rate = (completed_sessions / len(sessions) * 100) if sessions else 0

    # Test-only PR stats (to track if the new policy is working)
    test_only_prs = sum(1 for d in decisions if d.get('pr_title', '').lower().startswith('test:'))
    test_only_closed = sum(1 for d in decisions
                          if d.get('pr_title', '').lower().startswith('test:')
                          and d.get('decision') == 'CLOSE')

    return jsonify({
        'pr_type_distribution': pr_types,
        'total_decisions': total_decisions,
        'merged': merged,
        'closed': closed,
        'merge_rate': round(merge_rate, 1),
        'avg_value_score': round(avg_value, 1),
        'avg_quality_score': round(avg_quality, 1),
        'session_success_rate': round(success_rate, 1),
        'test_only_prs': test_only_prs,
        'test_only_closed': test_only_closed,
        'total_sessions': len(sessions),
        'completed_sessions': completed_sessions,
        'failed_sessions': failed_sessions
    })


if __name__ == '__main__':
    cert_file = WORK_DIR / 'web_portal' / 'eastindia.crt'
    key_file = WORK_DIR / 'web_portal' / 'eastindia.key'

    ssl_context = None
    if cert_file.exists() and key_file.exists():
        ssl_context = (str(cert_file), str(key_file))
        print("Starting with HTTPS on port 8443")
    else:
        print("Starting with HTTP on port 8080")

    app.run(
        host='0.0.0.0',
        port=8443 if ssl_context else 8080,
        ssl_context=ssl_context,
        debug=False
    )
