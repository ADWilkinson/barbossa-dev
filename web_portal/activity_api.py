#!/usr/bin/env python3
"""
Enhanced Activity API for Barbossa Web Portal
Provides detailed activity endpoints with better insights
"""

from flask import Blueprint, jsonify, request
from flask_httpauth import HTTPBasicAuth
from pathlib import Path
from datetime import datetime, timedelta
import json
import logging

# Import the activity tracker
from activity_tracker import BarbossaActivityTracker

logger = logging.getLogger(__name__)

# Create blueprint
activity_api = Blueprint('activity_api', __name__, url_prefix='/api/activity')

# Setup auth (will use main app's auth)
auth = HTTPBasicAuth()

# Initialize tracker
tracker = BarbossaActivityTracker()

@activity_api.route('/detailed')
@auth.login_required
def get_detailed_activity():
    """Get detailed activity for specified time period"""
    hours = request.args.get('hours', 24, type=int)
    hours = min(hours, 168)  # Max 1 week
    
    try:
        activity = tracker.get_detailed_activity(hours)
        return jsonify(activity)
    except Exception as e:
        logger.error(f"Error getting detailed activity: {e}")
        return jsonify({'error': str(e)}), 500

@activity_api.route('/timeline')
@auth.login_required
def get_activity_timeline():
    """Get activity timeline"""
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    try:
        activity = tracker.get_detailed_activity(hours)
        timeline = activity.get('timeline', [])[:limit]
        
        # Format for frontend display
        formatted_timeline = []
        for event in timeline:
            formatted_timeline.append({
                'timestamp': event['timestamp'],
                'time': datetime.fromisoformat(event['timestamp']).strftime('%Y-%m-%d %H:%M'),
                'type': event['type'],
                'category': event['category'],
                'description': event['description'],
                'icon': _get_icon_for_type(event['type'], event['category'])
            })
        
        return jsonify({
            'timeline': formatted_timeline,
            'total_events': len(timeline)
        })
    except Exception as e:
        logger.error(f"Error getting timeline: {e}")
        return jsonify({'error': str(e)}), 500

@activity_api.route('/summary')
@auth.login_required
def get_activity_summary():
    """Get activity summary statistics"""
    hours = request.args.get('hours', 24, type=int)
    
    try:
        activity = tracker.get_detailed_activity(hours)
        summary = activity.get('summary', {})
        
        # Add percentage changes if we have historical data
        summary['period_hours'] = hours
        summary['current_focus'] = activity.get('current_focus', 'General Development')
        
        # Add work distribution
        work_distribution = _calculate_work_distribution(activity)
        summary['work_distribution'] = work_distribution
        
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return jsonify({'error': str(e)}), 500

@activity_api.route('/report')
@auth.login_required  
def get_activity_report():
    """Get human-readable activity report"""
    hours = request.args.get('hours', 24, type=int)
    format = request.args.get('format', 'markdown')
    
    try:
        if format == 'markdown':
            report = tracker.get_activity_report(hours)
            return report, 200, {'Content-Type': 'text/markdown'}
        else:
            activity = tracker.get_detailed_activity(hours)
            return jsonify(activity)
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({'error': str(e)}), 500

@activity_api.route('/work-areas')
@auth.login_required
def get_work_areas():
    """Get breakdown of work by area"""
    hours = request.args.get('hours', 24, type=int)
    
    try:
        activity = tracker.get_detailed_activity(hours)
        
        work_areas = {
            'infrastructure': {
                'count': 0,
                'recent_tasks': [],
                'icon': '🔧'
            },
            'personal_projects': {
                'count': 0,
                'recent_tasks': [],
                'icon': '📦'
            },
            'davy_jones': {
                'count': 0,
                'recent_tasks': [],
                'icon': '🤖'
            },
            'testing': {
                'count': 0,
                'recent_tasks': [],
                'icon': '🧪'
            },
            'documentation': {
                'count': 0,
                'recent_tasks': [],
                'icon': '📚'
            }
        }
        
        # Categorize activities
        for event in activity.get('timeline', []):
            area = _categorize_event(event)
            if area in work_areas:
                work_areas[area]['count'] += 1
                if len(work_areas[area]['recent_tasks']) < 5:
                    work_areas[area]['recent_tasks'].append({
                        'time': datetime.fromisoformat(event['timestamp']).strftime('%H:%M'),
                        'description': event['description'][:80]
                    })
        
        return jsonify(work_areas)
    except Exception as e:
        logger.error(f"Error getting work areas: {e}")
        return jsonify({'error': str(e)}), 500

@activity_api.route('/insights')
@auth.login_required
def get_activity_insights():
    """Get AI-generated insights about recent activity"""
    hours = request.args.get('hours', 24, type=int)
    
    try:
        activity = tracker.get_detailed_activity(hours)
        
        insights = {
            'productivity_score': _calculate_productivity_score(activity),
            'most_active_period': _find_most_active_period(activity),
            'focus_areas': _analyze_focus_areas(activity),
            'recommendations': _generate_recommendations(activity),
            'achievements': _identify_achievements(activity)
        }
        
        return jsonify(insights)
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        return jsonify({'error': str(e)}), 500

# Helper functions

def _get_icon_for_type(event_type: str, category: str) -> str:
    """Get icon for event type"""
    icons = {
        'work': {
            'file_edit': '📝',
            'file_create': '➕',
            'test_run': '🧪',
            'bug_fix': '🐛',
            'feature_add': '✨',
            'refactor': '♻️',
            'commit': '📦',
            'pr_create': '🔀',
            'dependency': '📦',
            'completion': '✅'
        },
        'code_change': '💻',
        'git': '📦',
        'test': '🧪'
    }
    
    if event_type in icons:
        if isinstance(icons[event_type], dict):
            return icons[event_type].get(category, '•')
        return icons[event_type]
    return '•'

def _calculate_work_distribution(activity: dict) -> dict:
    """Calculate distribution of work across different areas"""
    distribution = {}
    total = 0
    
    for event in activity.get('timeline', []):
        area = _categorize_event(event)
        distribution[area] = distribution.get(area, 0) + 1
        total += 1
    
    # Convert to percentages
    if total > 0:
        for area in distribution:
            distribution[area] = round((distribution[area] / total) * 100, 1)
    
    return distribution

def _categorize_event(event: dict) -> str:
    """Categorize an event into a work area"""
    description = event.get('description', '').lower()
    category = event.get('category', '').lower()
    
    if 'davy' in description or 'slack' in description or 'bot' in description:
        return 'davy_jones'
    elif 'test' in description or 'test' in category:
        return 'testing'
    elif 'doc' in description or 'readme' in description:
        return 'documentation'
    elif 'infrastructure' in description or 'server' in description or 'docker' in description:
        return 'infrastructure'
    else:
        return 'personal_projects'

def _calculate_productivity_score(activity: dict) -> int:
    """Calculate a productivity score based on activity"""
    summary = activity.get('summary', {})
    
    score = 0
    score += min(summary.get('total_executions', 0) * 10, 30)
    score += min(summary.get('files_modified', 0) * 5, 25)
    score += min(summary.get('commits_made', 0) * 15, 30)
    score += min(summary.get('tests_run', 0) * 5, 10)
    score += min(summary.get('errors_fixed', 0) * 10, 5)
    
    return min(score, 100)

def _find_most_active_period(activity: dict) -> dict:
    """Find the most active time period"""
    timeline = activity.get('timeline', [])
    
    if not timeline:
        return {'period': 'No activity', 'count': 0}
    
    # Group by hour
    hours = {}
    for event in timeline:
        timestamp = datetime.fromisoformat(event['timestamp'])
        hour = timestamp.hour
        hours[hour] = hours.get(hour, 0) + 1
    
    # Find max
    if hours:
        max_hour = max(hours, key=hours.get)
        return {
            'period': f"{max_hour:02d}:00 - {(max_hour+1)%24:02d}:00",
            'count': hours[max_hour]
        }
    
    return {'period': 'No activity', 'count': 0}

def _analyze_focus_areas(activity: dict) -> list:
    """Analyze main focus areas"""
    distribution = _calculate_work_distribution(activity)
    
    focus_areas = []
    for area, percentage in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
        if percentage > 10:
            focus_areas.append({
                'area': area.replace('_', ' ').title(),
                'percentage': percentage
            })
    
    return focus_areas[:3]  # Top 3 areas

def _generate_recommendations(activity: dict) -> list:
    """Generate recommendations based on activity"""
    recommendations = []
    summary = activity.get('summary', {})
    
    if summary.get('tests_run', 0) < 5:
        recommendations.append("Consider running more tests to ensure code quality")
    
    if summary.get('commits_made', 0) < 2:
        recommendations.append("Remember to commit changes regularly")
    
    if summary.get('errors_fixed', 0) > 5:
        recommendations.append("Great bug fixing! Consider adding preventive tests")
    
    if not recommendations:
        recommendations.append("Keep up the great work!")
    
    return recommendations

def _identify_achievements(activity: dict) -> list:
    """Identify notable achievements"""
    achievements = []
    summary = activity.get('summary', {})
    
    if summary.get('files_modified', 0) > 10:
        achievements.append(f"Modified {summary['files_modified']} files")
    
    if summary.get('commits_made', 0) > 5:
        achievements.append(f"Made {summary['commits_made']} commits")
    
    if summary.get('errors_fixed', 0) > 0:
        achievements.append(f"Fixed {summary['errors_fixed']} errors")
    
    if summary.get('tickets_enriched', 0) > 0:
        achievements.append(f"Enriched {summary['tickets_enriched']} tickets")
    
    return achievements[:5]  # Top 5 achievements