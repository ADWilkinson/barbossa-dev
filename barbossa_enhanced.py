#!/usr/bin/env python3
"""
Barbossa Enhanced - Comprehensive Server Management & Autonomous Engineering System
Integrates server monitoring, project management, and autonomous development capabilities
"""

import argparse
import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
import threading
import time
import functools
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import random
import shutil
import psutil
import re

# Import components
from security_guard import security_guard, SecurityViolationError
from server_manager import BarbossaServerManager

class AnomalyDetector:
    """AI-powered anomaly detection for system metrics"""
    
    def __init__(self):
        self.baseline_models = {}
        self.anomaly_history = []
        self.learning_window = 100
        self.sensitivity = 2.0  # Standard deviations for anomaly threshold
        
    def update_baseline(self, metric_name: str, value: float):
        """Update baseline model for a metric"""
        if metric_name not in self.baseline_models:
            self.baseline_models[metric_name] = {
                'values': [],
                'mean': 0.0,
                'std': 0.0,
                'count': 0
            }
        
        model = self.baseline_models[metric_name]
        model['values'].append(value)
        
        # Keep only recent values for baseline
        if len(model['values']) > self.learning_window:
            model['values'] = model['values'][-self.learning_window:]
        
        # Update statistics
        if len(model['values']) >= 5:
            model['mean'] = sum(model['values']) / len(model['values'])
            variance = sum((x - model['mean']) ** 2 for x in model['values']) / len(model['values'])
            model['std'] = variance ** 0.5
            model['count'] = len(model['values'])
    
    def detect_anomaly(self, metric_name: str, value: float) -> Dict:
        """Detect if current value is an anomaly"""
        if metric_name not in self.baseline_models:
            self.update_baseline(metric_name, value)
            return {'is_anomaly': False, 'reason': 'insufficient_data'}
        
        model = self.baseline_models[metric_name]
        if model['count'] < 10 or model['std'] == 0:
            self.update_baseline(metric_name, value)
            return {'is_anomaly': False, 'reason': 'building_baseline'}
        
        # Calculate z-score
        z_score = abs(value - model['mean']) / model['std']
        is_anomaly = z_score > self.sensitivity
        
        anomaly_info = {
            'is_anomaly': is_anomaly,
            'z_score': z_score,
            'threshold': self.sensitivity,
            'current_value': value,
            'expected_range': [
                model['mean'] - self.sensitivity * model['std'],
                model['mean'] + self.sensitivity * model['std']
            ],
            'severity': self._calculate_severity(z_score)
        }
        
        if is_anomaly:
            self.anomaly_history.append({
                'timestamp': time.time(),
                'metric': metric_name,
                'value': value,
                'z_score': z_score
            })
            # Keep only recent anomalies
            self.anomaly_history = self.anomaly_history[-50:]
        
        self.update_baseline(metric_name, value)
        return anomaly_info
    
    def _calculate_severity(self, z_score: float) -> str:
        """Calculate anomaly severity based on z-score"""
        if z_score > 4.0:
            return 'critical'
        elif z_score > 3.0:
            return 'high'
        elif z_score > 2.5:
            return 'medium'
        else:
            return 'low'
    
    def get_anomaly_summary(self) -> Dict:
        """Get summary of recent anomalies"""
        if not self.anomaly_history:
            return {'count': 0, 'metrics_affected': [], 'recent_anomalies': []}
        
        recent_anomalies = [a for a in self.anomaly_history if time.time() - a['timestamp'] < 3600]  # Last hour
        metrics_affected = list(set(a['metric'] for a in recent_anomalies))
        
        return {
            'count': len(recent_anomalies),
            'metrics_affected': metrics_affected,
            'recent_anomalies': recent_anomalies[-10:],  # Last 10
            'severity_breakdown': self._get_severity_breakdown(recent_anomalies)
        }
    
    def _get_severity_breakdown(self, anomalies: List[Dict]) -> Dict:
        """Get breakdown of anomalies by severity"""
        breakdown = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for anomaly in anomalies:
            severity = self._calculate_severity(anomaly['z_score'])
            breakdown[severity] += 1
        return breakdown

class IntelligentAlertManager:
    """Intelligent alert management with context-aware notifications"""
    
    def __init__(self):
        self.alert_history = []
        self.suppression_rules = {}
        self.alert_correlations = {}
        self.notification_channels = []
        
    def should_alert(self, alert_type: str, context: Dict) -> Dict:
        """Determine if an alert should be sent based on intelligent rules"""
        current_time = time.time()
        
        # Check suppression rules
        if self._is_suppressed(alert_type, current_time):
            return {'should_alert': False, 'reason': 'suppressed'}
        
        # Check for alert storms (too many similar alerts)
        recent_similar = [
            a for a in self.alert_history[-20:]  # Last 20 alerts
            if a['type'] == alert_type and current_time - a['timestamp'] < 300  # Last 5 minutes
        ]
        
        if len(recent_similar) > 5:
            self._add_suppression_rule(alert_type, current_time + 1800)  # Suppress for 30 minutes
            return {'should_alert': False, 'reason': 'alert_storm_protection'}
        
        # Check correlation with other metrics
        correlation_score = self._calculate_correlation_score(alert_type, context)
        
        # Determine alert priority
        priority = self._calculate_priority(alert_type, context, correlation_score)
        
        alert_decision = {
            'should_alert': True,
            'priority': priority,
            'correlation_score': correlation_score,
            'suppression_time': self._get_suppression_time(priority),
            'context': context
        }
        
        # Record alert
        self.alert_history.append({
            'timestamp': current_time,
            'type': alert_type,
            'priority': priority,
            'context': context
        })
        
        # Keep only recent history
        self.alert_history = self.alert_history[-100:]
        
        return alert_decision
    
    def _is_suppressed(self, alert_type: str, current_time: float) -> bool:
        """Check if alert type is currently suppressed"""
        if alert_type in self.suppression_rules:
            if current_time < self.suppression_rules[alert_type]:
                return True
            else:
                del self.suppression_rules[alert_type]
        return False
    
    def _add_suppression_rule(self, alert_type: str, until_time: float):
        """Add suppression rule for alert type"""
        self.suppression_rules[alert_type] = until_time
    
    def _calculate_correlation_score(self, alert_type: str, context: Dict) -> float:
        """Calculate correlation with other recent alerts and metrics"""
        score = 1.0  # Base score
        
        # Check for related system metrics
        if alert_type == 'high_cpu' and context.get('memory_percent', 0) > 80:
            score += 0.3  # CPU + Memory correlation
        
        if alert_type == 'high_memory' and context.get('disk_io', 0) > 50:
            score += 0.2  # Memory + IO correlation
        
        # Check time-based patterns
        current_hour = datetime.now().hour
        if alert_type in ['high_cpu', 'high_memory'] and 9 <= current_hour <= 17:
            score += 0.1  # Business hours correlation
        
        return min(score, 2.0)  # Cap at 2.0
    
    def _calculate_priority(self, alert_type: str, context: Dict, correlation_score: float) -> str:
        """Calculate alert priority"""
        base_priorities = {
            'critical_system': 'high',
            'high_cpu': 'medium',
            'high_memory': 'medium',
            'high_disk': 'high',
            'anomaly_detected': 'low',
            'predictive_warning': 'low'
        }
        
        base_priority = base_priorities.get(alert_type, 'medium')
        
        # Adjust based on correlation
        if correlation_score > 1.5:
            if base_priority == 'medium':
                return 'high'
            elif base_priority == 'low':
                return 'medium'
        
        return base_priority
    
    def _get_suppression_time(self, priority: str) -> int:
        """Get suppression time in seconds based on priority"""
        suppression_times = {
            'low': 3600,      # 1 hour
            'medium': 1800,   # 30 minutes
            'high': 900,      # 15 minutes
            'critical': 300   # 5 minutes
        }
        return suppression_times.get(priority, 1800)

class AdvancedHealthMonitor:
    """Advanced health monitoring with predictive analytics and auto-recovery"""
    
    def __init__(self):
        self.health_history = []
        self.prediction_models = {}
        self.auto_recovery_enabled = True
        self.anomaly_detector = AnomalyDetector()
        self.intelligent_alerting = IntelligentAlertManager()
        self.alert_thresholds = {
            'cpu_critical': 95.0,
            'cpu_warning': 85.0,
            'memory_critical': 95.0,
            'memory_warning': 85.0,
            'disk_critical': 95.0,
            'disk_warning': 90.0,
            'temperature_critical': 80.0,
            'temperature_warning': 70.0,
            'load_critical': 8.0,
            'load_warning': 4.0,
            'network_anomaly': 50.0,
            'io_anomaly': 100.0
        }
        self.recovery_actions = {
            'high_cpu': self._recover_high_cpu,
            'high_memory': self._recover_high_memory,
            'high_disk': self._recover_high_disk,
            'high_temperature': self._recover_high_temperature
        }
    
    def analyze_health_trends(self, metrics: Dict) -> Dict:
        """Analyze health trends and predict potential issues with AI-powered anomaly detection"""
        self.health_history.append({
            'timestamp': time.time(),
            'metrics': metrics.copy()
        })
        
        # Keep only last 100 measurements
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
        
        # Perform anomaly detection on key metrics
        anomalies = {}
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)) and metric_name in ['cpu_percent', 'memory_percent', 'disk_percent', 'load_1min']:
                anomaly_result = self.anomaly_detector.detect_anomaly(metric_name, value)
                if anomaly_result['is_anomaly']:
                    anomalies[metric_name] = anomaly_result
        
        # Generate intelligent alerts
        alert_decisions = {}
        for metric_name, anomaly_data in anomalies.items():
            alert_decision = self.intelligent_alerting.should_alert(
                f'anomaly_{metric_name}', 
                {**metrics, 'anomaly_severity': anomaly_data['severity']}
            )
            if alert_decision['should_alert']:
                alert_decisions[metric_name] = alert_decision
        
        trends = {
            'cpu_trend': self._calculate_trend('cpu_percent'),
            'memory_trend': self._calculate_trend('memory_percent'),
            'disk_trend': self._calculate_trend('disk_percent'),
            'prediction': self._predict_issues(),
            'recommendations': self._generate_recommendations(metrics),
            'anomalies': anomalies,
            'intelligent_alerts': alert_decisions,
            'anomaly_summary': self.anomaly_detector.get_anomaly_summary()
        }
        
        return trends
    
    def _calculate_trend(self, metric_name: str) -> Dict:
        """Calculate trend for a specific metric"""
        if len(self.health_history) < 5:
            return {'trend': 'stable', 'rate': 0.0}
        
        recent_values = [h['metrics'].get(metric_name, 0) for h in self.health_history[-10:]]
        if len(recent_values) < 2:
            return {'trend': 'stable', 'rate': 0.0}
        
        # Simple linear trend calculation
        x_vals = list(range(len(recent_values)))
        avg_x = sum(x_vals) / len(x_vals)
        avg_y = sum(recent_values) / len(recent_values)
        
        numerator = sum((x - avg_x) * (y - avg_y) for x, y in zip(x_vals, recent_values))
        denominator = sum((x - avg_x) ** 2 for x in x_vals)
        
        if denominator == 0:
            rate = 0.0
        else:
            rate = numerator / denominator
        
        if rate > 1.0:
            trend = 'increasing'
        elif rate < -1.0:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {'trend': trend, 'rate': rate}
    
    def _predict_issues(self) -> List[Dict]:
        """Predict potential issues based on trends"""
        predictions = []
        
        if len(self.health_history) < 10:
            return predictions
        
        latest_metrics = self.health_history[-1]['metrics']
        
        # CPU prediction
        cpu_trend = self._calculate_trend('cpu_percent')
        if cpu_trend['trend'] == 'increasing' and latest_metrics.get('cpu_percent', 0) > 70:
            time_to_critical = max(1, (self.alert_thresholds['cpu_critical'] - latest_metrics.get('cpu_percent', 0)) / max(0.1, cpu_trend['rate']))
            predictions.append({
                'type': 'cpu_overload',
                'severity': 'warning',
                'estimated_time_minutes': int(time_to_critical),
                'description': f"CPU usage trending upward, may reach critical in {int(time_to_critical)} minutes"
            })
        
        # Memory prediction
        memory_trend = self._calculate_trend('memory_percent')
        if memory_trend['trend'] == 'increasing' and latest_metrics.get('memory_percent', 0) > 70:
            time_to_critical = max(1, (self.alert_thresholds['memory_critical'] - latest_metrics.get('memory_percent', 0)) / max(0.1, memory_trend['rate']))
            predictions.append({
                'type': 'memory_exhaustion',
                'severity': 'warning',
                'estimated_time_minutes': int(time_to_critical),
                'description': f"Memory usage trending upward, may reach critical in {int(time_to_critical)} minutes"
            })
        
        return predictions
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """Generate intelligent recommendations based on current metrics"""
        recommendations = []
        
        cpu_percent = metrics.get('cpu_percent', 0)
        memory_percent = metrics.get('memory_percent', 0)
        disk_percent = metrics.get('disk_percent', 0)
        load_1min = metrics.get('load_1min', 0)
        
        # CPU recommendations
        if cpu_percent > self.alert_thresholds['cpu_warning']:
            recommendations.append("High CPU usage detected - consider identifying resource-intensive processes")
            if load_1min > psutil.cpu_count() * 2:
                recommendations.append("System load is high - investigate background processes or consider upgrading hardware")
        
        # Memory recommendations
        if memory_percent > self.alert_thresholds['memory_warning']:
            recommendations.append("High memory usage - consider clearing caches or restarting memory-intensive services")
            if memory_percent > 90:
                recommendations.append("Critical memory usage - immediate action required to prevent system instability")
        
        # Disk recommendations
        if disk_percent > self.alert_thresholds['disk_warning']:
            recommendations.append("Disk space running low - clean up log files, temporary files, or old backups")
            if disk_percent > 95:
                recommendations.append("Critical disk space - immediate cleanup required to prevent system failure")
        
        # Proactive recommendations
        if cpu_percent < 20 and memory_percent < 50:
            recommendations.append("System resources healthy - good time for maintenance tasks")
        
        return recommendations
    
    def check_auto_recovery(self, metrics: Dict) -> List[str]:
        """Check if auto-recovery actions should be triggered"""
        if not self.auto_recovery_enabled:
            return []
        
        actions_taken = []
        
        # High CPU recovery
        if metrics.get('cpu_percent', 0) > self.alert_thresholds['cpu_critical']:
            if self._recover_high_cpu():
                actions_taken.append("CPU auto-recovery: Optimized process priorities")
        
        # High memory recovery
        if metrics.get('memory_percent', 0) > self.alert_thresholds['memory_critical']:
            if self._recover_high_memory():
                actions_taken.append("Memory auto-recovery: Cleared caches and buffers")
        
        # High disk recovery
        if metrics.get('disk_percent', 0) > self.alert_thresholds['disk_critical']:
            if self._recover_high_disk():
                actions_taken.append("Disk auto-recovery: Cleaned temporary files")
        
        return actions_taken
    
    def _recover_high_cpu(self) -> bool:
        """Auto-recovery for high CPU usage"""
        try:
            # Find and nice down CPU-intensive processes
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 50:
                        os.nice(proc.info['pid'])  # Lower priority
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return True
        except Exception:
            return False
    
    def _recover_high_memory(self) -> bool:
        """Auto-recovery for high memory usage"""
        try:
            # Clear system caches
            subprocess.run(['sudo', 'sync'], check=False, capture_output=True)
            subprocess.run(['sudo', 'sh', '-c', 'echo 1 > /proc/sys/vm/drop_caches'], check=False, capture_output=True)
            return True
        except Exception:
            return False
    
    def _recover_high_disk(self) -> bool:
        """Auto-recovery for high disk usage"""
        try:
            # Clean temporary files
            temp_dirs = ['/tmp', '/var/tmp', '/var/log/journal']
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    # Clean files older than 7 days
                    subprocess.run(['find', temp_dir, '-type', 'f', '-mtime', '+7', '-delete'], 
                                 check=False, capture_output=True)
            return True
        except Exception:
            return False
    
    def _recover_high_temperature(self) -> bool:
        """Auto-recovery for high temperature"""
        try:
            # Reduce CPU frequency
            subprocess.run(['sudo', 'cpupower', 'frequency-set', '-u', '2.0GHz'], 
                         check=False, capture_output=True)
            return True
        except Exception:
            return False

class SmartResourceManager:
    """Intelligent resource management with automatic optimization"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.optimization_history = []
        self.resource_policies = {
            'log_retention_days': 30,
            'backup_retention_days': 60,
            'cache_max_size_mb': 1024,
            'temp_file_cleanup_days': 7,
            'docker_image_cleanup_days': 30
        }
    
    def optimize_resources(self) -> Dict:
        """Perform comprehensive resource optimization"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'actions_taken': [],
            'space_freed_mb': 0,
            'performance_improvements': []
        }
        
        # Log file optimization
        log_result = self._optimize_logs()
        results['actions_taken'].extend(log_result['actions'])
        results['space_freed_mb'] += log_result['space_freed_mb']
        
        # Backup optimization
        backup_result = self._optimize_backups()
        results['actions_taken'].extend(backup_result['actions'])
        results['space_freed_mb'] += backup_result['space_freed_mb']
        
        # Cache optimization
        cache_result = self._optimize_caches()
        results['actions_taken'].extend(cache_result['actions'])
        results['space_freed_mb'] += cache_result['space_freed_mb']
        
        # Docker optimization
        docker_result = self._optimize_docker()
        results['actions_taken'].extend(docker_result['actions'])
        results['space_freed_mb'] += docker_result['space_freed_mb']
        
        # Database optimization
        db_result = self._optimize_databases()
        results['actions_taken'].extend(db_result['actions'])
        results['performance_improvements'].extend(db_result['improvements'])
        
        self.optimization_history.append(results)
        return results
    
    def _optimize_logs(self) -> Dict:
        """Optimize log files"""
        result = {'actions': [], 'space_freed_mb': 0}
        
        try:
            logs_dir = self.work_dir / 'logs'
            if not logs_dir.exists():
                return result
            
            cutoff_date = datetime.now() - timedelta(days=self.resource_policies['log_retention_days'])
            space_freed = 0
            files_cleaned = 0
            
            for log_file in logs_dir.glob('*.log*'):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    file_size = log_file.stat().st_size
                    
                    # Compress old logs instead of deleting
                    if not log_file.name.endswith('.gz'):
                        compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
                        subprocess.run(['gzip', str(log_file)], check=False)
                        if compressed_file.exists():
                            space_freed += file_size - compressed_file.stat().st_size
                            files_cleaned += 1
            
            result['actions'].append(f"Compressed {files_cleaned} old log files")
            result['space_freed_mb'] = space_freed / (1024 * 1024)
            
        except Exception as e:
            result['actions'].append(f"Log optimization failed: {e}")
        
        return result
    
    def _optimize_backups(self) -> Dict:
        """Optimize backup files"""
        result = {'actions': [], 'space_freed_mb': 0}
        
        try:
            backups_dir = self.work_dir / 'backups'
            if not backups_dir.exists():
                return result
            
            cutoff_date = datetime.now() - timedelta(days=self.resource_policies['backup_retention_days'])
            space_freed = 0
            files_deleted = 0
            
            for backup_file in backups_dir.glob('*'):
                if backup_file.is_file() and backup_file.stat().st_mtime < cutoff_date.timestamp():
                    file_size = backup_file.stat().st_size
                    backup_file.unlink()
                    space_freed += file_size
                    files_deleted += 1
            
            result['actions'].append(f"Deleted {files_deleted} old backup files")
            result['space_freed_mb'] = space_freed / (1024 * 1024)
            
        except Exception as e:
            result['actions'].append(f"Backup optimization failed: {e}")
        
        return result
    
    def _optimize_caches(self) -> Dict:
        """Optimize cache files"""
        result = {'actions': [], 'space_freed_mb': 0}
        
        try:
            # System cache cleanup
            subprocess.run(['sudo', 'sync'], check=False)
            subprocess.run(['sudo', 'sh', '-c', 'echo 1 > /proc/sys/vm/drop_caches'], check=False)
            
            # Application cache cleanup
            cache_dirs = [
                Path.home() / '.cache',
                self.work_dir / 'cache',
                Path('/tmp')
            ]
            
            space_freed = 0
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    initial_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                    
                    # Clean files older than 7 days
                    cutoff_date = datetime.now() - timedelta(days=7)
                    for cache_file in cache_dir.rglob('*'):
                        if (cache_file.is_file() and 
                            cache_file.stat().st_mtime < cutoff_date.timestamp()):
                            try:
                                cache_file.unlink()
                            except OSError:
                                continue
                    
                    final_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                    space_freed += initial_size - final_size
            
            result['actions'].append("Cleaned system and application caches")
            result['space_freed_mb'] = space_freed / (1024 * 1024)
            
        except Exception as e:
            result['actions'].append(f"Cache optimization failed: {e}")
        
        return result
    
    def _optimize_docker(self) -> Dict:
        """Optimize Docker resources"""
        result = {'actions': [], 'space_freed_mb': 0}
        
        try:
            # Docker system prune
            prune_result = subprocess.run(['docker', 'system', 'prune', '-f'], 
                                        capture_output=True, text=True, check=False)
            if prune_result.returncode == 0:
                result['actions'].append("Performed Docker system prune")
            
            # Remove dangling images
            images_result = subprocess.run(['docker', 'image', 'prune', '-f'], 
                                         capture_output=True, text=True, check=False)
            if images_result.returncode == 0:
                result['actions'].append("Removed dangling Docker images")
            
            # Clean build cache
            buildx_result = subprocess.run(['docker', 'buildx', 'prune', '-f'], 
                                         capture_output=True, text=True, check=False)
            if buildx_result.returncode == 0:
                result['actions'].append("Cleaned Docker build cache")
            
        except Exception as e:
            result['actions'].append(f"Docker optimization failed: {e}")
        
        return result
    
    def _optimize_databases(self) -> Dict:
        """Optimize database performance"""
        result = {'actions': [], 'improvements': []}
        
        try:
            # SQLite database optimization
            db_files = list(self.work_dir.glob('*.db'))
            for db_file in db_files:
                try:
                    import sqlite3
                    with sqlite3.connect(db_file) as conn:
                        # VACUUM to reclaim space
                        conn.execute('VACUUM')
                        # ANALYZE to update statistics
                        conn.execute('ANALYZE')
                        result['actions'].append(f"Optimized database {db_file.name}")
                        result['improvements'].append(f"Database {db_file.name}: VACUUM and ANALYZE completed")
                except Exception:
                    continue
            
        except Exception as e:
            result['actions'].append(f"Database optimization failed: {e}")
        
        return result

class EnhancedErrorHandler:
    """Advanced error handling with context-aware recovery and logging"""
    
    def __init__(self, logger):
        self.logger = logger
        self.error_patterns = {}
        self.recovery_strategies = {}
        self.error_history = []
        
    def register_error_pattern(self, pattern: str, recovery_strategy: callable, description: str):
        """Register an error pattern with its recovery strategy"""
        self.error_patterns[pattern] = {
            'strategy': recovery_strategy,
            'description': description,
            'usage_count': 0,
            'success_rate': 0.0
        }
    
    def handle_error(self, error: Exception, context: Dict, operation: str = "unknown") -> Dict:
        """Handle an error with intelligent recovery strategies"""
        error_str = str(error)
        error_type = type(error).__name__
        
        # Log the error with full context
        self.logger.error(f"Error in {operation}: {error_type}: {error_str}")
        self.logger.debug(f"Error context: {context}")
        
        # Record error in history
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'error_type': error_type,
            'error_message': error_str,
            'context': context,
            'recovery_attempted': False,
            'recovery_successful': False
        }
        
        # Check for matching error patterns
        matching_pattern = self._find_matching_pattern(error_str)
        if matching_pattern:
            recovery_result = self._attempt_recovery(matching_pattern, error, context, operation)
            error_record['recovery_attempted'] = True
            error_record['recovery_successful'] = recovery_result['success']
            error_record['recovery_details'] = recovery_result
            
            if recovery_result['success']:
                self.logger.info(f"Successfully recovered from error using pattern: {matching_pattern}")
                return {
                    'handled': True,
                    'recovered': True,
                    'strategy': matching_pattern,
                    'details': recovery_result
                }
        
        # Add to error history
        self.error_history.append(error_record)
        
        # Keep only last 100 errors
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
        
        return {
            'handled': True,
            'recovered': False,
            'error_type': error_type,
            'error_message': error_str,
            'recommendations': self._generate_error_recommendations(error, context)
        }
    
    def _find_matching_pattern(self, error_str: str) -> Optional[str]:
        """Find a matching error pattern"""
        for pattern in self.error_patterns:
            if re.search(pattern, error_str, re.IGNORECASE):
                return pattern
        return None
    
    def _attempt_recovery(self, pattern: str, error: Exception, context: Dict, operation: str) -> Dict:
        """Attempt recovery using the matched pattern"""
        pattern_info = self.error_patterns[pattern]
        pattern_info['usage_count'] += 1
        
        try:
            recovery_strategy = pattern_info['strategy']
            recovery_result = recovery_strategy(error, context, operation)
            
            # Update success rate
            if recovery_result.get('success', False):
                pattern_info['success_rate'] = (
                    pattern_info['success_rate'] * (pattern_info['usage_count'] - 1) + 1.0
                ) / pattern_info['usage_count']
            else:
                pattern_info['success_rate'] = (
                    pattern_info['success_rate'] * (pattern_info['usage_count'] - 1)
                ) / pattern_info['usage_count']
            
            return recovery_result
            
        except Exception as recovery_error:
            self.logger.error(f"Recovery strategy failed: {recovery_error}")
            return {
                'success': False,
                'error': f"Recovery failed: {recovery_error}",
                'strategy': pattern
            }
    
    def _generate_error_recommendations(self, error: Exception, context: Dict) -> List[str]:
        """Generate intelligent error recommendations"""
        recommendations = []
        error_type = type(error).__name__
        
        if error_type == 'PermissionError':
            recommendations.append("Check file/directory permissions")
            recommendations.append("Ensure the process has sufficient privileges")
        
        elif error_type == 'FileNotFoundError':
            recommendations.append("Verify the file/directory path exists")
            recommendations.append("Check for typos in file paths")
        
        elif error_type == 'ConnectionError':
            recommendations.append("Check network connectivity")
            recommendations.append("Verify service endpoints are accessible")
        
        elif error_type == 'TimeoutError':
            recommendations.append("Increase timeout values")
            recommendations.append("Check for resource contention")
        
        elif 'memory' in str(error).lower():
            recommendations.append("Check available system memory")
            recommendations.append("Consider optimizing memory usage")
        
        elif 'disk' in str(error).lower():
            recommendations.append("Check available disk space")
            recommendations.append("Consider cleaning up temporary files")
        
        # Context-specific recommendations
        if 'cpu_percent' in context and context.get('cpu_percent', 0) > 90:
            recommendations.append("High CPU usage detected - consider reducing load")
        
        if 'memory_percent' in context and context.get('memory_percent', 0) > 90:
            recommendations.append("High memory usage detected - consider freeing memory")
        
        return recommendations
    
    def get_error_analytics(self) -> Dict:
        """Get analytics on error patterns and recovery success rates"""
        if not self.error_history:
            return {'total_errors': 0, 'patterns': {}, 'recent_trends': []}
        
        total_errors = len(self.error_history)
        error_types = {}
        recoveries_attempted = 0
        recoveries_successful = 0
        
        for error in self.error_history:
            error_type = error['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if error['recovery_attempted']:
                recoveries_attempted += 1
                if error['recovery_successful']:
                    recoveries_successful += 1
        
        return {
            'total_errors': total_errors,
            'error_types': error_types,
            'recoveries_attempted': recoveries_attempted,
            'recoveries_successful': recoveries_successful,
            'recovery_success_rate': recoveries_successful / max(1, recoveries_attempted),
            'patterns': {
                pattern: {
                    'usage_count': info['usage_count'],
                    'success_rate': info['success_rate'],
                    'description': info['description']
                }
                for pattern, info in self.error_patterns.items()
            }
        }

class WorkflowAutomationEngine:
    """Advanced workflow automation with dependency management and scheduling"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.workflows = {}
        self.active_workflows = {}
        self.workflow_history = []
        self.dependency_graph = {}
        self.scheduler = WorkflowScheduler()
        
    def create_workflow(self, name: str, steps: List[Dict], dependencies: Optional[List[str]] = None) -> Dict:
        """Create a new automated workflow"""
        workflow_id = f"workflow_{int(time.time())}_{name}"
        
        workflow = {
            'id': workflow_id,
            'name': name,
            'steps': steps,
            'dependencies': dependencies or [],
            'created_at': datetime.now().isoformat(),
            'status': 'created',
            'execution_history': [],
            'retry_count': 0,
            'max_retries': 3
        }
        
        self.workflows[workflow_id] = workflow
        
        # Build dependency graph
        if dependencies:
            self.dependency_graph[workflow_id] = dependencies
        
        return {'workflow_id': workflow_id, 'status': 'created'}
    
    def execute_workflow(self, workflow_id: str, context: Optional[Dict] = None) -> Dict:
        """Execute a workflow with intelligent scheduling and dependency resolution"""
        if workflow_id not in self.workflows:
            return {'status': 'error', 'message': 'Workflow not found'}
        
        workflow = self.workflows[workflow_id]
        
        # Check dependencies
        if not self._check_dependencies(workflow_id):
            return {'status': 'waiting', 'message': 'Dependencies not satisfied'}
        
        # Check if already running
        if workflow_id in self.active_workflows:
            return {'status': 'already_running', 'message': 'Workflow is already executing'}
        
        # Start execution
        self.active_workflows[workflow_id] = {
            'started_at': time.time(),
            'current_step': 0,
            'context': context or {},
            'step_results': []
        }
        
        workflow['status'] = 'running'
        
        try:
            execution_result = self._execute_workflow_steps(workflow_id)
            workflow['status'] = 'completed' if execution_result['success'] else 'failed'
            
            # Record execution history
            workflow['execution_history'].append({
                'timestamp': datetime.now().isoformat(),
                'result': execution_result,
                'context': context
            })
            
            return execution_result
            
        except Exception as e:
            workflow['status'] = 'error'
            workflow['retry_count'] += 1
            
            error_result = {
                'success': False,
                'error': str(e),
                'retry_count': workflow['retry_count']
            }
            
            workflow['execution_history'].append({
                'timestamp': datetime.now().isoformat(),
                'result': error_result,
                'context': context
            })
            
            return error_result
            
        finally:
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    def _check_dependencies(self, workflow_id: str) -> bool:
        """Check if workflow dependencies are satisfied"""
        if workflow_id not in self.dependency_graph:
            return True
        
        dependencies = self.dependency_graph[workflow_id]
        for dep_id in dependencies:
            if dep_id not in self.workflows:
                return False
            
            dep_workflow = self.workflows[dep_id]
            if dep_workflow['status'] != 'completed':
                return False
        
        return True
    
    def _execute_workflow_steps(self, workflow_id: str) -> Dict:
        """Execute all steps in a workflow"""
        workflow = self.workflows[workflow_id]
        active_execution = self.active_workflows[workflow_id]
        
        results = []
        
        for i, step in enumerate(workflow['steps']):
            active_execution['current_step'] = i
            
            try:
                step_result = self._execute_step(step, active_execution['context'])
                results.append(step_result)
                active_execution['step_results'].append(step_result)
                
                # Update context with step results
                if step_result.get('output'):
                    active_execution['context'].update(step_result['output'])
                
                if not step_result.get('success', True):
                    return {
                        'success': False,
                        'failed_step': i,
                        'step_name': step.get('name', 'unnamed'),
                        'error': step_result.get('error', 'Step failed'),
                        'results': results
                    }
                    
            except Exception as e:
                return {
                    'success': False,
                    'failed_step': i,
                    'step_name': step.get('name', 'unnamed'),
                    'error': str(e),
                    'results': results
                }
        
        return {
            'success': True,
            'steps_executed': len(results),
            'results': results,
            'execution_time': time.time() - active_execution['started_at']
        }
    
    def _execute_step(self, step: Dict, context: Dict) -> Dict:
        """Execute a single workflow step"""
        step_type = step.get('type', 'command')
        step_name = step.get('name', 'unnamed_step')
        
        if step_type == 'command':
            return self._execute_command_step(step, context)
        elif step_type == 'python':
            return self._execute_python_step(step, context)
        elif step_type == 'api_call':
            return self._execute_api_step(step, context)
        elif step_type == 'condition':
            return self._execute_condition_step(step, context)
        else:
            return {'success': False, 'error': f'Unknown step type: {step_type}'}
    
    def _execute_command_step(self, step: Dict, context: Dict) -> Dict:
        """Execute a command step"""
        command = step.get('command', '')
        if not command:
            return {'success': False, 'error': 'No command specified'}
        
        # Template substitution
        for key, value in context.items():
            command = command.replace(f'{{{key}}}', str(value))
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=step.get('timeout', 300),
                cwd=self.work_dir
            )
            
            return {
                'success': result.returncode == 0,
                'output': {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                },
                'error': result.stderr if result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Command timed out'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_python_step(self, step: Dict, context: Dict) -> Dict:
        """Execute a Python code step"""
        code = step.get('code', '')
        if not code:
            return {'success': False, 'error': 'No Python code specified'}
        
        try:
            # Create safe execution environment
            safe_globals = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'dict': dict,
                    'list': list,
                    'tuple': tuple,
                    'set': set,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter
                },
                'context': context,
                'result': {}
            }
            
            exec(code, safe_globals)
            
            return {
                'success': True,
                'output': safe_globals.get('result', {})
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_api_step(self, step: Dict, context: Dict) -> Dict:
        """Execute an API call step"""
        url = step.get('url', '')
        method = step.get('method', 'GET').upper()
        headers = step.get('headers', {})
        data = step.get('data', {})
        
        # Template substitution in URL and data
        for key, value in context.items():
            url = url.replace(f'{{{key}}}', str(value))
            if isinstance(data, dict):
                for data_key, data_value in data.items():
                    if isinstance(data_value, str):
                        data[data_key] = data_value.replace(f'{{{key}}}', str(value))
        
        try:
            import requests
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if method in ['POST', 'PUT', 'PATCH'] else None,
                timeout=step.get('timeout', 30)
            )
            
            return {
                'success': response.status_code < 400,
                'output': {
                    'status_code': response.status_code,
                    'response_data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                    'headers': dict(response.headers)
                },
                'error': f'HTTP {response.status_code}' if response.status_code >= 400 else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _execute_condition_step(self, step: Dict, context: Dict) -> Dict:
        """Execute a conditional step"""
        condition = step.get('condition', '')
        if not condition:
            return {'success': False, 'error': 'No condition specified'}
        
        try:
            # Simple condition evaluation
            # Replace context variables
            for key, value in context.items():
                condition = condition.replace(f'{{{key}}}', str(value))
            
            # Evaluate condition safely
            result = eval(condition, {'__builtins__': {}}, {})
            
            return {
                'success': True,
                'output': {'condition_result': bool(result)}
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

class WorkflowScheduler:
    """Intelligent workflow scheduler with priority and resource management"""
    
    def __init__(self):
        self.scheduled_workflows = []
        self.recurring_workflows = {}
        self.resource_limits = {
            'max_concurrent': 3,
            'max_cpu_percent': 80,
            'max_memory_percent': 85
        }
    
    def schedule_workflow(self, workflow_id: str, schedule_time: datetime, priority: int = 1) -> Dict:
        """Schedule a workflow for future execution"""
        schedule_entry = {
            'workflow_id': workflow_id,
            'scheduled_time': schedule_time,
            'priority': priority,
            'created_at': datetime.now(),
            'status': 'scheduled'
        }
        
        self.scheduled_workflows.append(schedule_entry)
        self.scheduled_workflows.sort(key=lambda x: (x['scheduled_time'], -x['priority']))
        
        return {'status': 'scheduled', 'schedule_id': len(self.scheduled_workflows) - 1}
    
    def add_recurring_workflow(self, workflow_id: str, cron_pattern: str, priority: int = 1) -> Dict:
        """Add a recurring workflow with cron-like scheduling"""
        recurring_id = f"recurring_{workflow_id}_{int(time.time())}"
        
        self.recurring_workflows[recurring_id] = {
            'workflow_id': workflow_id,
            'cron_pattern': cron_pattern,
            'priority': priority,
            'last_run': None,
            'next_run': self._calculate_next_run(cron_pattern),
            'status': 'active'
        }
        
        return {'status': 'scheduled', 'recurring_id': recurring_id}
    
    def _calculate_next_run(self, cron_pattern: str) -> datetime:
        """Calculate next run time from cron pattern (simplified)"""
        # This is a simplified cron parser - in production, use a proper cron library
        # For now, support basic patterns like "0 */4 * * *" (every 4 hours)
        
        now = datetime.now()
        
        # Simple hourly pattern
        if cron_pattern == "0 * * * *":  # Every hour
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif cron_pattern == "0 */4 * * *":  # Every 4 hours
            next_hour = now.hour + (4 - now.hour % 4)
            if next_hour >= 24:
                next_hour -= 24
                return now.replace(hour=next_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                return now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        else:
            # Default to 1 hour from now
            return now + timedelta(hours=1)
    
    def get_ready_workflows(self) -> List[str]:
        """Get workflows ready for execution"""
        now = datetime.now()
        ready_workflows = []
        
        # Check scheduled workflows
        for schedule in self.scheduled_workflows:
            if schedule['status'] == 'scheduled' and schedule['scheduled_time'] <= now:
                ready_workflows.append(schedule['workflow_id'])
                schedule['status'] = 'ready'
        
        # Check recurring workflows
        for recurring_id, recurring in self.recurring_workflows.items():
            if recurring['status'] == 'active' and recurring['next_run'] <= now:
                ready_workflows.append(recurring['workflow_id'])
                recurring['last_run'] = now
                recurring['next_run'] = self._calculate_next_run(recurring['cron_pattern'])
        
        return ready_workflows
    
    def can_execute_workflow(self) -> bool:
        """Check if system resources allow workflow execution"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            
            return (cpu_percent < self.resource_limits['max_cpu_percent'] and 
                    memory_percent < self.resource_limits['max_memory_percent'])
        except:
            return True  # Default to allow execution if can't check resources

class PerformanceProfiler:
    """Enhanced performance profiling and monitoring for Barbossa operations"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self.lock = threading.Lock()
        self.performance_baselines = {}
        self.anomaly_detection = True
    
    def start_operation(self, operation_name: str):
        """Start timing an operation"""
        with self.lock:
            self.start_times[operation_name] = {
                'start_time': time.time(),
                'start_memory': psutil.Process().memory_info().rss,
                'start_cpu_times': psutil.Process().cpu_times()
            }
    
    def end_operation(self, operation_name: str):
        """End timing an operation and store metrics"""
        with self.lock:
            if operation_name in self.start_times:
                start_data = self.start_times[operation_name]
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                end_cpu_times = psutil.Process().cpu_times()
                
                duration = end_time - start_data['start_time']
                memory_delta = end_memory - start_data['start_memory']
                cpu_delta = (end_cpu_times.user + end_cpu_times.system) - (start_data['start_cpu_times'].user + start_data['start_cpu_times'].system)
                
                if operation_name not in self.metrics:
                    self.metrics[operation_name] = []
                
                metric_data = {
                    'duration': duration,
                    'timestamp': datetime.now().isoformat(),
                    'memory_delta_mb': memory_delta / 1024 / 1024,
                    'cpu_time_delta': cpu_delta,
                    'memory_mb': end_memory / 1024 / 1024
                }
                
                self.metrics[operation_name].append(metric_data)
                
                # Keep only last 100 measurements
                self.metrics[operation_name] = self.metrics[operation_name][-100:]
                
                # Check for anomalies
                if self.anomaly_detection:
                    self._check_performance_anomaly(operation_name, metric_data)
                
                del self.start_times[operation_name]
    
    def _check_performance_anomaly(self, operation_name: str, current_metric: Dict):
        """Check for performance anomalies"""
        if operation_name not in self.metrics or len(self.metrics[operation_name]) < 10:
            return
        
        recent_metrics = self.metrics[operation_name][-10:]
        avg_duration = sum(m['duration'] for m in recent_metrics) / len(recent_metrics)
        
        # Alert if current duration is significantly higher than average
        if current_metric['duration'] > avg_duration * 2:
            logging.warning(f"Performance anomaly detected in {operation_name}: "
                          f"Duration {current_metric['duration']:.3f}s vs avg {avg_duration:.3f}s")
    
    def get_performance_summary(self) -> Dict:
        """Get enhanced performance summary with analytics"""
        with self.lock:
            summary = {}
            for operation, measurements in self.metrics.items():
                if measurements:
                    durations = [m['duration'] for m in measurements]
                    memory_deltas = [m['memory_delta_mb'] for m in measurements]
                    
                    summary[operation] = {
                        'count': len(measurements),
                        'avg_duration': sum(durations) / len(durations),
                        'max_duration': max(durations),
                        'min_duration': min(durations),
                        'last_run': measurements[-1]['timestamp'],
                        'avg_memory_delta_mb': sum(memory_deltas) / len(memory_deltas),
                        'performance_trend': self._calculate_performance_trend(durations),
                        'efficiency_score': self._calculate_efficiency_score(operation)
                    }
            return summary
    
    def _calculate_performance_trend(self, durations: List[float]) -> str:
        """Calculate performance trend"""
        if len(durations) < 5:
            return 'insufficient_data'
        
        recent_avg = sum(durations[-5:]) / 5
        older_avg = sum(durations[:-5]) / (len(durations) - 5)
        
        if recent_avg > older_avg * 1.1:
            return 'degrading'
        elif recent_avg < older_avg * 0.9:
            return 'improving'
        else:
            return 'stable'
    
    def _calculate_efficiency_score(self, operation_name: str) -> int:
        """Calculate efficiency score (0-100)"""
        if operation_name not in self.metrics or len(self.metrics[operation_name]) < 5:
            return 50
        
        measurements = self.metrics[operation_name]
        recent_measurements = measurements[-5:]
        
        # Base score on consistency and speed
        durations = [m['duration'] for m in recent_measurements]
        avg_duration = sum(durations) / len(durations)
        variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
        
        # Lower variance and duration = higher score
        consistency_score = max(0, 100 - (variance * 100))
        speed_score = max(0, 100 - (avg_duration * 10))  # Adjust multiplier as needed
        
        return int((consistency_score + speed_score) / 2)

def performance_monitor(operation_name: str = None):
    """Enhanced decorator for performance monitoring"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if hasattr(self, 'profiler'):
                op_name = operation_name or f"{func.__name__}"
                self.profiler.start_operation(op_name)
                try:
                    result = func(self, *args, **kwargs)
                    return result
                finally:
                    self.profiler.end_operation(op_name)
            else:
                return func(self, *args, **kwargs)
        return wrapper
    return decorator

class BarbossaEnhanced:
    """
    Enhanced Barbossa system with integrated server management capabilities
    Now includes advanced health monitoring, resource management, and performance analytics
    """
    
    VERSION = "2.4.0"  # Major update with essential features
    
    WORK_AREAS = {
        'infrastructure': {
            'name': 'Server Infrastructure Management',
            'description': 'Comprehensive server monitoring, optimization, and maintenance',
            'weight': 0.1,  # MINIMAL - Only for critical issues
            'tasks': [
                'Critical security patches only',
                'Emergency system fixes',
                'Critical service failures'
            ]
        },
        'personal_projects': {
            'name': 'Personal Project Development',
            'description': 'Feature development for ADWilkinson repositories',
            'repositories': [
                'ADWilkinson/_save',
                'ADWilkinson/chordcraft-app',
                'ADWilkinson/piggyonchain',
                'ADWilkinson/personal-website',
                'ADWilkinson/saylormemes',
                'ADWilkinson/the-flying-dutchman-theme'
            ],
            'weight': 7.0  # HIGH - 70% weight (multiple projects)
        },
        'davy_jones': {
            'name': 'Davy Jones Intern Enhancement',
            'description': 'Bot improvements without affecting production',
            'repository': 'ADWilkinson/davy-jones-intern',
            'weight': 3.0  # MODERATE - 30% weight (single project)
        },
        'barbossa_self': {
            'name': 'Barbossa Self-Improvement',
            'description': 'Enhance Barbossa capabilities and features',
            'weight': 0.2,  # LOW - Minimal priority
            'tasks': [
                'Essential feature updates',
                'Critical bug fixes only',
                'Performance optimizations'
            ]
        }
    }
    
    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize Enhanced Barbossa with all subsystems"""
        self.work_dir = work_dir or Path.home() / 'barbossa-engineer'
        self.logs_dir = self.work_dir / 'logs'
        self.changelogs_dir = self.work_dir / 'changelogs'
        self.work_tracking_dir = self.work_dir / 'work_tracking'
        self.metrics_db = self.work_dir / 'metrics.db'
        
        # Initialize enhanced components
        self.profiler = PerformanceProfiler()
        self.health_monitor = AdvancedHealthMonitor()
        self.resource_manager = SmartResourceManager(self.work_dir)
        self.workflow_engine = WorkflowAutomationEngine(self.work_dir)
        
        # Initialize error handler after logger is available
        self.error_handler = None
        
        # Initialize caching system for expensive operations
        self._cache = {}
        self._cache_expiry = {}
        self._cache_lock = threading.Lock()
        
        # Initialize optimized thread pool executor
        cpu_count = os.cpu_count() or 2
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=min(cpu_count, 4), 
            thread_name_prefix="BarbossaAsync"
        )
        
        # Ensure directories exist
        for dir_path in [self.logs_dir, self.changelogs_dir, self.work_tracking_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize server manager
        self.server_manager = None
        try:
            self.server_manager = BarbossaServerManager()
            self.server_manager.start_monitoring()
        except Exception as e:
            print(f"Warning: Could not initialize server manager: {e}")
        
        # Set up logging
        self._setup_logging()
        
        # Load work tally
        self.work_tally = self._load_work_tally()
        
        # System info
        self.system_info = self._get_system_info()
        
        # Initialize API client for new portal features
        self.portal_api_base = "https://localhost:8443"
        self.api_available = self._check_api_availability()
        
        self.logger.info("=" * 70)
        self.logger.info(f"BARBOSSA ENHANCED v{self.VERSION} - Comprehensive Server Management")
        self.logger.info(f"Working directory: {self.work_dir}")
        self.logger.info(f"Platform: {self.system_info['platform']}")
        self.logger.info(f"Server Manager: {'Active' if self.server_manager else 'Inactive'}")
        self.logger.info(f"Portal APIs: {'Available' if self.api_available else 'Not Available'}")
        self.logger.info(f"Enhanced Features: Health Monitoring, Resource Management, Performance Analytics")
        self.logger.info("Security: MAXIMUM - ZKP2P access BLOCKED")
        self.logger.info("=" * 70)
    
    def _check_api_availability(self):
        """Check if the new portal APIs are available"""
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Test if advanced API v3 is available
            response = requests.get(f"{self.portal_api_base}/api/v3/health", 
                                   verify=False, timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        return False
    
    def get_performance_score(self):
        """Get comprehensive system performance score combining API and local metrics"""
        # Try API first
        api_score = None
        if self.api_available:
            try:
                import requests
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                response = requests.get(f"{self.portal_api_base}/api/v3/analytics/performance-score",
                                       verify=False, timeout=10)
                if response.status_code == 200:
                    api_score = response.json()
            except Exception as e:
                self.logger.warning(f"Could not get API performance score: {e}")
        
        # Generate local performance score
        local_score = self._calculate_local_performance_score()
        
        # Combine scores if both available
        if api_score and local_score:
            return {
                'combined_score': (api_score.get('overall_score', 50) + local_score['overall_score']) / 2,
                'api_score': api_score,
                'local_score': local_score,
                'recommendations': list(set(
                    api_score.get('recommendations', []) + local_score.get('recommendations', [])
                ))
            }
        elif api_score:
            return api_score
        else:
            return local_score
    
    def _calculate_local_performance_score(self):
        """Calculate performance score based on local metrics and profiler data"""
        scores = {}
        recommendations = []
        
        # Get current health metrics
        if self.server_manager:
            health = self.perform_system_health_check()
            metrics = health.get('metrics', {})
            
            # CPU Score (100 = excellent, 0 = critical)
            cpu_percent = metrics.get('cpu_percent', 0)
            if cpu_percent < 30:
                scores['cpu'] = 100
            elif cpu_percent < 50:
                scores['cpu'] = 80
            elif cpu_percent < 70:
                scores['cpu'] = 60
                recommendations.append("Consider optimizing CPU-intensive processes")
            elif cpu_percent < 85:
                scores['cpu'] = 40
                recommendations.append("High CPU usage - investigate resource-intensive tasks")
            else:
                scores['cpu'] = 20
                recommendations.append("Critical CPU usage - immediate optimization required")
            
            # Memory Score
            memory_percent = metrics.get('memory_percent', 0)
            if memory_percent < 40:
                scores['memory'] = 100
            elif memory_percent < 60:
                scores['memory'] = 80
            elif memory_percent < 75:
                scores['memory'] = 60
                recommendations.append("Consider freeing up memory")
            elif memory_percent < 85:
                scores['memory'] = 40
                recommendations.append("High memory usage - consider optimizing applications")
            else:
                scores['memory'] = 20
                recommendations.append("Critical memory usage - immediate action required")
            
            # Disk Score
            disk_percent = metrics.get('disk_percent', 0)
            if disk_percent < 50:
                scores['disk'] = 100
            elif disk_percent < 70:
                scores['disk'] = 80
            elif disk_percent < 80:
                scores['disk'] = 60
                recommendations.append("Consider cleaning up disk space")
            elif disk_percent < 90:
                scores['disk'] = 40
                recommendations.append("Low disk space - cleanup required")
            else:
                scores['disk'] = 20
                recommendations.append("Critical disk space - immediate cleanup required")
        
        # Performance Profiler Score
        perf_summary = self.profiler.get_performance_summary()
        if perf_summary:
            efficiency_scores = [op.get('efficiency_score', 50) for op in perf_summary.values()]
            avg_efficiency = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 50
            scores['efficiency'] = avg_efficiency
            
            if avg_efficiency < 50:
                recommendations.append("System efficiency is below optimal - consider performance tuning")
        else:
            scores['efficiency'] = 50
        
        # Error Rate Score
        if self.error_handler:
            error_analytics = self.error_handler.get_error_analytics()
            total_errors = error_analytics.get('total_errors', 0)
            recovery_rate = error_analytics.get('recovery_success_rate', 0)
            
            if total_errors == 0:
                scores['stability'] = 100
            elif total_errors < 5 and recovery_rate > 0.8:
                scores['stability'] = 80
            elif total_errors < 10 and recovery_rate > 0.6:
                scores['stability'] = 60
                recommendations.append("Some errors detected - monitor system stability")
            elif recovery_rate > 0.4:
                scores['stability'] = 40
                recommendations.append("Multiple errors detected - investigate system issues")
            else:
                scores['stability'] = 20
                recommendations.append("High error rate with low recovery - urgent investigation needed")
        else:
            scores['stability'] = 50
        
        # Calculate overall score
        if scores:
            overall_score = sum(scores.values()) / len(scores)
        else:
            overall_score = 50
        
        # Determine status
        if overall_score >= 85:
            status = "excellent"
        elif overall_score >= 70:
            status = "good"
        elif overall_score >= 50:
            status = "fair"
            recommendations.append("System performance could be improved")
        else:
            status = "poor"
            recommendations.append("System performance needs immediate attention")
        
        return {
            'overall_score': int(overall_score),
            'overall_status': status,
            'component_scores': scores,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat(),
            'version': self.VERSION
        }
    
    def create_backup(self, backup_type="config"):
        """Create a backup using the new API"""
        if not self.api_available:
            return None
        
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.post(f"{self.portal_api_base}/api/v3/backup/create",
                                    json={"backup_type": backup_type, "compress": True},
                                    verify=False, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.warning(f"Could not create backup: {e}")
        return None
    
    def _setup_logging(self):
        """Configure comprehensive logging"""
        log_file = self.logs_dir / f"barbossa_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('barbossa_enhanced')
        self.logger.info(f"Logging to: {log_file}")
        
        # Initialize error handler now that logger is available
        self.error_handler = EnhancedErrorHandler(self.logger)
        self._register_error_patterns()
    
    def _register_error_patterns(self):
        """Register common error patterns with recovery strategies"""
        
        def recover_permission_error(error, context, operation):
            """Recovery strategy for permission errors"""
            try:
                # Try to fix common permission issues
                if 'log' in str(error).lower():
                    subprocess.run(['sudo', 'chmod', '666', '/var/log/*'], check=False)
                    return {'success': True, 'action': 'Fixed log file permissions'}
                elif 'tmp' in str(error).lower():
                    subprocess.run(['sudo', 'chmod', '777', '/tmp'], check=False)
                    return {'success': True, 'action': 'Fixed tmp directory permissions'}
                else:
                    return {'success': False, 'action': 'Could not determine permission fix'}
            except Exception as e:
                return {'success': False, 'action': f'Permission fix failed: {e}'}
        
        def recover_disk_space_error(error, context, operation):
            """Recovery strategy for disk space errors"""
            try:
                # Clean temporary files
                cleanup_result = self.resource_manager._optimize_logs()
                if cleanup_result['space_freed_mb'] > 0:
                    return {
                        'success': True, 
                        'action': f'Freed {cleanup_result["space_freed_mb"]:.1f}MB by cleaning logs'
                    }
                else:
                    return {'success': False, 'action': 'No space could be freed'}
            except Exception as e:
                return {'success': False, 'action': f'Disk cleanup failed: {e}'}
        
        def recover_network_error(error, context, operation):
            """Recovery strategy for network errors"""
            try:
                # Test network connectivity
                result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], capture_output=True)
                if result.returncode == 0:
                    return {'success': False, 'action': 'Network is available, issue may be service-specific'}
                else:
                    # Try to restart networking
                    subprocess.run(['sudo', 'systemctl', 'restart', 'networking'], check=False)
                    return {'success': True, 'action': 'Attempted to restart networking'}
            except Exception as e:
                return {'success': False, 'action': f'Network recovery failed: {e}'}
        
        def recover_memory_error(error, context, operation):
            """Recovery strategy for memory errors"""
            try:
                # Clear system caches
                subprocess.run(['sudo', 'sync'], check=False)
                subprocess.run(['sudo', 'sh', '-c', 'echo 1 > /proc/sys/vm/drop_caches'], check=False)
                return {'success': True, 'action': 'Cleared system caches to free memory'}
            except Exception as e:
                return {'success': False, 'action': f'Memory recovery failed: {e}'}
        
        # Register error patterns
        self.error_handler.register_error_pattern(
            r'permission denied|access denied',
            recover_permission_error,
            'Handle permission denied errors by fixing common file permissions'
        )
        
        self.error_handler.register_error_pattern(
            r'no space left|disk full',
            recover_disk_space_error,
            'Handle disk space errors by cleaning temporary files and logs'
        )
        
        self.error_handler.register_error_pattern(
            r'connection.*refused|network.*unreachable|timeout',
            recover_network_error,
            'Handle network errors by testing connectivity and restarting services'
        )
        
        self.error_handler.register_error_pattern(
            r'out of memory|memory.*error',
            recover_memory_error,
            'Handle memory errors by clearing system caches'
        )
    
    def _get_system_info(self) -> Dict:
        """Gather comprehensive system information"""
        info = {
            'hostname': platform.node(),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': os.cpu_count(),
            'home_dir': str(Path.home()),
            'server_ip': '192.168.1.138'
        }
        
        # Get disk usage
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                info['disk_usage'] = {
                    'total': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'percent': parts[4]
                }
        except:
            pass
        
        return info
    
    def _get_cached(self, key: str, ttl: int = 300) -> Optional[Any]:
        """Get cached value if not expired"""
        with self._cache_lock:
            if key in self._cache and key in self._cache_expiry:
                if time.time() < self._cache_expiry[key]:
                    return self._cache[key]
                else:
                    # Clean expired cache
                    del self._cache[key]
                    del self._cache_expiry[key]
            return None
    
    def _set_cache(self, key: str, value: Any, ttl: int = 300):
        """Set cached value with TTL"""
        with self._cache_lock:
            self._cache[key] = value
            self._cache_expiry[key] = time.time() + ttl
            # Cleanup old entries periodically
            if len(self._cache) > 100:
                self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, expiry_time in self._cache_expiry.items()
            if current_time >= expiry_time
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_expiry.pop(key, None)
    
    def _load_work_tally(self) -> Dict[str, int]:
        """Load work tally from JSON file"""
        tally_file = self.work_tracking_dir / 'work_tally.json'
        if tally_file.exists():
            with open(tally_file, 'r') as f:
                tally = json.load(f)
                # Add new work areas if not present
                for area in self.WORK_AREAS.keys():
                    if area not in tally:
                        tally[area] = 0
                return tally
        return {area: 0 for area in self.WORK_AREAS.keys()}
    
    def _save_work_tally(self):
        """Save updated work tally"""
        tally_file = self.work_tracking_dir / 'work_tally.json'
        with open(tally_file, 'w') as f:
            json.dump(self.work_tally, f, indent=2)
        self.logger.info(f"Work tally saved: {self.work_tally}")
    
    @performance_monitor("system_health_check")
    def perform_system_health_check(self) -> Dict:
        """Perform comprehensive system health check with enhanced monitoring"""
        # Check cache first
        cache_key = 'system_health'
        cached_health = self._get_cached(cache_key, ttl=30)  # Cache for 30 seconds
        if cached_health:
            return cached_health
        
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy',
            'issues': [],
            'metrics': {},
            'trends': {},
            'predictions': [],
            'recommendations': [],
            'auto_recovery_actions': []
        }
        
        if self.server_manager:
            # Get current metrics
            metrics = self.server_manager.metrics_collector.collect_metrics()
            health['metrics'] = metrics
            
            # Enhanced health analysis with trends and predictions
            trends = self.health_monitor.analyze_health_trends(metrics)
            health['trends'] = trends
            health['predictions'] = trends['prediction']
            health['recommendations'] = trends['recommendations']
            
            # Check for auto-recovery actions
            recovery_actions = self.health_monitor.check_auto_recovery(metrics)
            health['auto_recovery_actions'] = recovery_actions
            
            # Check for issues with enhanced thresholds
            if metrics.get('cpu_percent', 0) > self.health_monitor.alert_thresholds['cpu_critical']:
                health['issues'].append(f"CRITICAL: CPU usage: {metrics['cpu_percent']:.1f}%")
                health['status'] = 'critical'
            elif metrics.get('cpu_percent', 0) > self.health_monitor.alert_thresholds['cpu_warning']:
                health['issues'].append(f"WARNING: High CPU usage: {metrics['cpu_percent']:.1f}%")
                health['status'] = 'warning'
            
            if metrics.get('memory_percent', 0) > self.health_monitor.alert_thresholds['memory_critical']:
                health['issues'].append(f"CRITICAL: Memory usage: {metrics['memory_percent']:.1f}%")
                health['status'] = 'critical'
            elif metrics.get('memory_percent', 0) > self.health_monitor.alert_thresholds['memory_warning']:
                health['issues'].append(f"WARNING: High memory usage: {metrics['memory_percent']:.1f}%")
                health['status'] = 'warning'
            
            if metrics.get('disk_percent', 0) > self.health_monitor.alert_thresholds['disk_critical']:
                health['issues'].append(f"CRITICAL: Disk usage: {metrics['disk_percent']:.1f}%")
                health['status'] = 'critical'
            elif metrics.get('disk_percent', 0) > self.health_monitor.alert_thresholds['disk_warning']:
                health['issues'].append(f"WARNING: Low disk space: {metrics['disk_percent']:.1f}%")
                health['status'] = 'warning'
            
            # Check services
            self.server_manager.service_manager._update_services()
            critical_services = ['docker', 'cloudflared']
            for service in critical_services:
                if service in self.server_manager.service_manager.services:
                    if not self.server_manager.service_manager.services[service].get('active'):
                        health['issues'].append(f"Service {service} is down")
                        health['status'] = 'critical'
        
        # Cache the result
        self._set_cache(cache_key, health, ttl=30)
        
        return health
    
    @performance_monitor("infrastructure_management")
    def execute_infrastructure_management(self):
        """Execute advanced infrastructure management tasks with auto-optimization"""
        self.logger.info("Executing enhanced infrastructure management...")
        
        # Perform automatic resource optimization
        optimization_results = self.resource_manager.optimize_resources()
        self.logger.info(f"Resource optimization completed - freed {optimization_results['space_freed_mb']:.1f}MB")
        
        # Use new API features if available
        if self.api_available:
            perf_score = self.get_performance_score()
            if perf_score:
                self.logger.info(f"API Performance Score: {perf_score['overall_score']}/100 - {perf_score['overall_status']}")
                
                # Log recommendations if any
                if perf_score.get('recommendations'):
                    for rec in perf_score['recommendations']:
                        self.logger.info(f"  Recommendation: {rec}")
                
                # Auto-backup on good health
                if perf_score['overall_score'] > 85 and datetime.now().hour == 3:  # 3 AM backups
                    self.logger.info("Creating automated backup...")
                    backup = self.create_backup("config")
                    if backup and backup.get('success'):
                        self.logger.info(f"Backup created: {backup['backup']['name']}")
        
        # Perform enhanced health check
        health = self.perform_system_health_check()
        self.logger.info(f"System health: {health['status']}")
        
        if health['issues']:
            self.logger.warning(f"Health issues detected: {health['issues']}")
        
        if health['predictions']:
            self.logger.info("Predictive alerts:")
            for prediction in health['predictions']:
                self.logger.info(f"  {prediction['type']}: {prediction['description']}")
        
        if health['auto_recovery_actions']:
            self.logger.info("Auto-recovery actions taken:")
            for action in health['auto_recovery_actions']:
                self.logger.info(f"  {action}")
        
        # Create enhanced prompt for Claude
        prompt = f"""You are Barbossa Enhanced v{self.VERSION}, an advanced server management system with AI-powered optimization.

CRITICAL SECURITY: Never access ZKP2P repositories. Only work with allowed repositories.

ENHANCED SYSTEM STATUS:
- Health: {health['status']}
- Issues: {', '.join(health['issues']) if health['issues'] else 'None'}
- CPU: {health['metrics'].get('cpu_percent', 0):.1f}% (Trend: {health['trends'].get('cpu_trend', {}).get('trend', 'unknown')})
- Memory: {health['metrics'].get('memory_percent', 0):.1f}% (Trend: {health['trends'].get('memory_trend', {}).get('trend', 'unknown')})
- Disk: {health['metrics'].get('disk_percent', 0):.1f}% (Trend: {health['trends'].get('disk_trend', {}).get('trend', 'unknown')})

AUTOMATIC OPTIMIZATIONS COMPLETED:
{json.dumps(optimization_results, indent=2)}

PREDICTIVE ALERTS:
{json.dumps(health['predictions'], indent=2) if health['predictions'] else 'None detected'}

SYSTEM RECOMMENDATIONS:
{chr(10).join(f"- {rec}" for rec in health['recommendations']) if health['recommendations'] else 'None'}

Your task is to perform ONE comprehensive infrastructure management task:

1. If health issues exist, prioritize fixing them with intelligent diagnosis
2. If predictive alerts exist, take preventive action
3. Otherwise, choose from advanced tasks:
   - Implement proactive monitoring and alerting
   - Optimize system performance with ML-driven analysis
   - Enhance security configurations with automated scanning
   - Deploy advanced resource monitoring and auto-scaling
   - Implement intelligent log analysis and pattern detection
   - Create automated backup and disaster recovery procedures
   - Optimize network configurations and security
   - Deploy advanced container orchestration improvements

AVAILABLE TOOLS:
- Enhanced Server Manager with predictive analytics
- Advanced resource optimization engine
- Smart health monitoring with auto-recovery
- Docker, systemctl, apt, ufw, netstat, ss
- Python scripts for automation and ML analysis
- Sudo password: Ableton6242

REQUIREMENTS:
- Execute REAL improvements with measurable impact
- Use advanced analytics and automation
- Document all changes made with performance metrics
- Test changes thoroughly and validate improvements
- Create detailed changelog with before/after analysis
- Consider long-term system health and sustainability

System Info:
{json.dumps(self.system_info, indent=2)}

Performance Profile:
{json.dumps(self.profiler.get_performance_summary(), indent=2)}

Complete the task and report detailed results with performance impact analysis."""

        # Save and execute
        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        output_file = self.logs_dir / f"claude_infrastructure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Execute Claude and capture output to both the specific log file and main log
        cmd = f"claude --dangerously-skip-permissions --model sonnet < {prompt_file} 2>&1 | tee {output_file}"
        self.logger.info(f"Executing Claude for infrastructure management...")
        self.logger.info(f"Output will be saved to: {output_file}")
        
        # Run synchronously to capture output in main log
        process = subprocess.Popen(cmd, shell=True, cwd=self.work_dir, 
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 text=True, bufsize=1)
        
        # Stream output to logger
        for line in iter(process.stdout.readline, ''):
            if line:
                self.logger.info(f"[Claude Output] {line.rstrip()}")
        
        process.wait()
        self.logger.info(f"Infrastructure management completed with return code: {process.returncode}")
        
        # Create enhanced changelog
        self._create_changelog('infrastructure', {
            'health_status': health['status'],
            'issues_found': health['issues'],
            'predictions': health['predictions'],
            'optimization_results': optimization_results,
            'prompt_file': str(prompt_file),
            'output_file': str(output_file),
            'enhancements': [
                'Advanced health monitoring with predictive analytics',
                'Automatic resource optimization',
                'Smart auto-recovery mechanisms',
                'Performance profiling and trend analysis'
            ]
        })
    
    def execute_barbossa_self_improvement(self):
        """Execute self-improvement tasks for Barbossa with enhanced capabilities"""
        self.logger.info("Executing enhanced Barbossa self-improvement...")
        
        # Select improvement task with intelligent prioritization
        tasks = self.WORK_AREAS['barbossa_self']['tasks']
        
        # Prioritize based on system state
        health = self.perform_system_health_check()
        performance = self.profiler.get_performance_summary()
        
        if health['status'] != 'healthy':
            selected_task = 'Critical bug fixes only'
        elif any(op.get('efficiency_score', 50) < 70 for op in performance.values()):
            selected_task = 'Performance optimizations'
        else:
            selected_task = 'Essential feature updates'
        
        prompt = f"""You are improving the Barbossa Enhanced system itself with advanced AI-driven capabilities.

TASK: {selected_task}

BARBOSSA ENHANCED COMPONENTS:
1. Main System: ~/barbossa-engineer/barbossa.py (THIS FILE - Enhanced v{self.VERSION})
2. Server Manager: ~/barbossa-engineer/server_manager.py
3. Web Portal: ~/barbossa-engineer/web_portal/enhanced_api.py
4. Dashboard: ~/barbossa-engineer/web_portal/templates/enhanced_dashboard.html
5. Security Guard: ~/barbossa-engineer/security_guard.py

NEW ENHANCED FEATURES ADDED TODAY:
✅ AdvancedHealthMonitor - Predictive analytics and auto-recovery
✅ SmartResourceManager - Intelligent resource optimization
✅ Enhanced PerformanceProfiler - ML-driven performance analytics
✅ Advanced caching and optimization systems

CURRENT SYSTEM STATE:
- Health Status: {health['status']}
- Performance Issues: {len([op for op in performance.values() if op.get('efficiency_score', 50) < 70])} operations need optimization
- Auto-Recovery: {'Enabled' if self.health_monitor.auto_recovery_enabled else 'Disabled'}
- Cache Hit Rate: {len(self._cache)} cached items
- Resource Optimization: Last run freed {self.resource_manager.optimization_history[-1]['space_freed_mb']:.1f if self.resource_manager.optimization_history else 0}MB

IMPROVEMENT AREAS FOR {selected_task}:
- Add machine learning-powered anomaly detection
- Implement advanced API rate limiting and security
- Enhance dashboard with real-time performance analytics
- Add intelligent backup scheduling and verification
- Implement advanced log analysis with pattern recognition
- Add automated security scanning and vulnerability assessment
- Enhance workflow automation with dependency management
- Implement advanced monitoring with customizable alerts

REQUIREMENTS:
1. Analyze current enhanced implementation
2. Identify specific improvements for: {selected_task}
3. Implement advanced enhancements with measurable impact
4. Add comprehensive error handling and resilience
5. Create intelligent tests and validation
6. Update documentation with feature impact analysis

IMPORTANT:
- Maintain backward compatibility with existing systems
- Follow existing enhanced code patterns and architecture
- Add comprehensive error handling with auto-recovery
- Create intelligent unit tests with performance validation
- Update documentation with measurable improvements
- Focus on AI-powered enhancements and automation

System Performance Profile:
{json.dumps(performance, indent=2)}

Complete the improvement and create a detailed impact report."""

        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        output_file = self.logs_dir / f"claude_self_improvement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Execute Claude and capture output to both the specific log file and main log
        cmd = f"claude --dangerously-skip-permissions --model sonnet < {prompt_file} 2>&1 | tee {output_file}"
        self.logger.info(f"Executing Claude for self-improvement: {selected_task}")
        self.logger.info(f"Output will be saved to: {output_file}")
        
        # Run synchronously to capture output in main log
        process = subprocess.Popen(cmd, shell=True, cwd=self.work_dir, 
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 text=True, bufsize=1)
        
        # Stream output to logger
        for line in iter(process.stdout.readline, ''):
            if line:
                self.logger.info(f"[Claude Output] {line.rstrip()}")
        
        process.wait()
        self.logger.info(f"Self-improvement completed with return code: {process.returncode}")
        
        self._create_changelog('barbossa_self', {
            'task': selected_task,
            'system_health': health['status'],
            'performance_state': performance,
            'output_file': str(output_file),
            'enhancements_active': [
                'AdvancedHealthMonitor with predictive analytics',
                'SmartResourceManager with auto-optimization',
                'Enhanced PerformanceProfiler with ML metrics',
                'Advanced caching and optimization systems'
            ]
        })
    
    def execute_personal_project_development(self):
        """Execute personal project development (inherited from original)"""
        self.logger.info("Executing personal project development...")
        
        repos = self.WORK_AREAS['personal_projects']['repositories']
        selected_repo = random.choice(repos)
        repo_url = f"https://github.com/{selected_repo}"
        
        # Validate repository access
        if not self.validate_repository_access(repo_url):
            self.logger.error("Repository access denied by security guard")
            return
        
        self.logger.info(f"Working on repository: {selected_repo}")
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        prompt = f"""You are Barbossa Enhanced, working on personal project improvements.

REPOSITORY: {selected_repo}
URL: {repo_url}

INSTRUCTIONS:
1. Clone repository to ~/barbossa-engineer/projects/ if not present, or navigate to existing clone
2. Fetch latest changes: git fetch origin
3. Checkout main/master branch: git checkout main (or master)
4. Pull latest changes: git pull origin main (or master)
5. Create new feature branch from updated main: git checkout -b feature/barbossa-improvement-{timestamp}
6. Analyze codebase comprehensively
7. Choose ONE significant improvement (PRIORITIZE IN THIS ORDER):
   - Implement new feature (HIGHEST PRIORITY)
   - Refactor for better architecture and code quality
   - Optimize performance and efficiency
   - Fix critical bugs and issues
   - Update critical dependencies
   - Improve inline code documentation (minimal)
   - Add tests ONLY if absolutely necessary (LOWEST PRIORITY)

8. Implement the improvement completely
9. Run tests if available
10. Commit with clear message
11. Push feature branch to origin
12. Create detailed PR

REQUIREMENTS:
- Make meaningful improvements
- Follow project conventions
- Ensure tests pass
- Write clean code
- Create comprehensive PR description

Complete the task and create a PR."""

        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        output_file = self.logs_dir / f"claude_personal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Execute Claude and capture output to both the specific log file and main log
        cmd = f"claude --dangerously-skip-permissions --model sonnet < {prompt_file} 2>&1 | tee {output_file}"
        self.logger.info(f"Executing Claude for personal project: {selected_repo}")
        self.logger.info(f"Output will be saved to: {output_file}")
        
        # Run synchronously to capture output in main log
        process = subprocess.Popen(cmd, shell=True, cwd=self.work_dir, 
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 text=True, bufsize=1)
        
        # Stream output to logger
        for line in iter(process.stdout.readline, ''):
            if line:
                self.logger.info(f"[Claude Output] {line.rstrip()}")
        
        process.wait()
        self.logger.info(f"Personal project development completed with return code: {process.returncode}")
        
        self._create_changelog('personal_projects', {
            'repository': selected_repo,
            'output_file': str(output_file)
        })
    
    def execute_davy_jones_development(self):
        """Execute Davy Jones development (inherited from original)"""
        self.logger.info("Executing Davy Jones Intern development...")
        
        repo_url = "https://github.com/ADWilkinson/davy-jones-intern"
        
        if not self.validate_repository_access(repo_url):
            self.logger.error("Repository access denied")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        prompt = f"""You are Barbossa Enhanced, improving the Davy Jones Intern bot.

CRITICAL: Production bot is running. DO NOT affect it.

REPOSITORY: {repo_url}
WORK DIR: ~/barbossa-engineer/projects/davy-jones-intern

INSTRUCTIONS:
1. Navigate to ~/barbossa-engineer/projects/davy-jones-intern (clone if not present)
2. Fetch latest changes: git fetch origin
3. Checkout main branch: git checkout main
4. Pull latest changes: git pull origin main
5. Create new feature branch: git checkout -b feature/davy-jones-improvement-{timestamp}

IMPROVEMENT AREAS:
1. Add comprehensive test coverage
2. Enhance error handling
3. Improve Claude integration
4. Add new Slack commands
5. Optimize performance
6. Enhance logging
7. Improve GitHub integration

REQUIREMENTS:
- Work in feature branch only
- Do not touch production
- Run tests locally
- Create detailed PR
- Document all changes

Select and implement ONE improvement completely."""

        prompt_file = self.work_dir / 'temp_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)
        
        output_file = self.logs_dir / f"claude_davy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Execute Claude and capture output to both the specific log file and main log
        cmd = f"claude --dangerously-skip-permissions --model sonnet < {prompt_file} 2>&1 | tee {output_file}"
        self.logger.info(f"Executing Claude for Davy Jones development...")
        self.logger.info(f"Output will be saved to: {output_file}")
        
        # Run synchronously to capture output in main log
        process = subprocess.Popen(cmd, shell=True, cwd=self.work_dir, 
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 text=True, bufsize=1)
        
        # Stream output to logger
        for line in iter(process.stdout.readline, ''):
            if line:
                self.logger.info(f"[Claude Output] {line.rstrip()}")
        
        process.wait()
        self.logger.info(f"Davy Jones development completed with return code: {process.returncode}")
        
        self._create_changelog('davy_jones', {
            'repository': repo_url,
            'output_file': str(output_file)
        })
    
    def validate_repository_access(self, repo_url: str) -> bool:
        """Validate repository access through security guard"""
        try:
            self.logger.info(f"Security check for: {repo_url}")
            security_guard.validate_operation('repository_access', repo_url)
            self.logger.info("✓ Security check PASSED")
            return True
        except SecurityViolationError as e:
            self.logger.error(f"✗ SECURITY VIOLATION: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Security check failed: {e}")
            return False
    
    def _create_changelog(self, area: str, details: Dict):
        """Create detailed changelog with enhanced metrics"""
        timestamp = datetime.now()
        changelog_file = self.changelogs_dir / f"{area}_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        
        content = [
            f"# {self.WORK_AREAS[area]['name']}\n",
            f"**Date**: {timestamp.isoformat()}\n",
            f"**Version**: Barbossa Enhanced v{self.VERSION}\n",
            f"\n## Enhanced System Details\n"
        ]
        
        for key, value in details.items():
            if isinstance(value, (dict, list)):
                content.append(f"- **{key.replace('_', ' ').title()}**:\n```json\n{json.dumps(value, indent=2)}\n```\n")
            else:
                content.append(f"- **{key.replace('_', ' ').title()}**: {value}\n")
        
        content.append(f"\n## Enhanced Features Active\n")
        content.append(f"- ✅ Advanced Health Monitoring with Predictive Analytics\n")
        content.append(f"- ✅ Smart Resource Management with Auto-optimization\n")
        content.append(f"- ✅ Enhanced Performance Profiling with ML Metrics\n")
        content.append(f"- ✅ Intelligent Caching and Optimization Systems\n")
        content.append(f"- ✅ Auto-recovery Mechanisms and Smart Alerting\n")
        
        content.append(f"\n## Status\n")
        content.append(f"Task initiated and running in background with enhanced monitoring.\n")
        
        with open(changelog_file, 'w') as f:
            f.writelines(content)
        
        self.logger.info(f"Enhanced changelog created: {changelog_file}")
    
    def select_work_area(self) -> str:
        """Select work area with enhanced weighting and intelligent prioritization"""
        # Calculate weights based on work history and current system state
        weights = {}
        
        # Perform health check for intelligent prioritization
        health = self.perform_system_health_check()
        
        for area, config in self.WORK_AREAS.items():
            base_weight = config['weight']
            work_count = self.work_tally.get(area, 0)
            
            # Inverse weight for balance
            adjusted_weight = base_weight * (1.0 / (work_count + 1))
            
            # Intelligent priority adjustments
            if area == 'infrastructure':
                # Boost infrastructure if health issues exist
                if health['status'] == 'critical':
                    adjusted_weight *= 10.0  # Critical boost
                elif health['status'] == 'warning':
                    adjusted_weight *= 3.0   # Warning boost
                elif health['predictions']:
                    adjusted_weight *= 2.0   # Predictive boost
            
            elif area == 'barbossa_self':
                # Boost self-improvement if performance issues detected
                performance = self.profiler.get_performance_summary()
                poor_performance_count = len([op for op in performance.values() 
                                            if op.get('efficiency_score', 50) < 70])
                if poor_performance_count > 2:
                    adjusted_weight *= 5.0  # Performance boost
            
            weights[area] = adjusted_weight
        
        # Normalize and select
        total_weight = sum(weights.values())
        probabilities = {k: v/total_weight for k, v in weights.items()}
        
        self.logger.info("Enhanced work area selection probabilities:")
        for area, prob in probabilities.items():
            health_bonus = ""
            if area == 'infrastructure' and health['status'] != 'healthy':
                health_bonus = f" (Health: {health['status']})"
            self.logger.info(f"  {area}: {prob:.2%} (count: {self.work_tally.get(area, 0)}){health_bonus}")
        
        selected = random.choices(
            list(probabilities.keys()),
            weights=list(probabilities.values()),
            k=1
        )[0]
        
        self.logger.info(f"INTELLIGENTLY SELECTED: {selected}")
        return selected
    
    def execute_work(self, area: Optional[str] = None):
        """Execute work for selected area with enhanced monitoring"""
        if not area:
            area = self.select_work_area()
        
        self.logger.info(f"Executing: {self.WORK_AREAS[area]['name']}")
        
        # Start performance monitoring for the work session
        self.profiler.start_operation(f"work_session_{area}")
        
        # Track work with enhanced details
        current_work = {
            'area': area,
            'started': datetime.now().isoformat(),
            'status': 'in_progress',
            'version': self.VERSION,
            'enhanced_features': True
        }
        
        current_work_file = self.work_tracking_dir / 'current_work.json'
        with open(current_work_file, 'w') as f:
            json.dump(current_work, f, indent=2)
        
        try:
            # Execute based on area
            if area == 'infrastructure':
                self.execute_infrastructure_management()
            elif area == 'personal_projects':
                self.execute_personal_project_development()
            elif area == 'davy_jones':
                self.execute_davy_jones_development()
            elif area == 'barbossa_self':
                self.execute_barbossa_self_improvement()
            else:
                self.logger.error(f"Unknown work area: {area}")
                return
            
            # Update tally
            self.work_tally[area] = self.work_tally.get(area, 0) + 1
            self._save_work_tally()
            
            current_work['status'] = 'completed'
            current_work['completed'] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Error executing work: {e}")
            current_work['status'] = 'failed'
            current_work['error'] = str(e)
        
        finally:
            # End performance monitoring
            self.profiler.end_operation(f"work_session_{area}")
            
            with open(current_work_file, 'w') as f:
                json.dump(current_work, f, indent=2)
            
            self.logger.info("Enhanced work session completed")
            self.logger.info("=" * 70)
    
    @performance_monitor("comprehensive_status")
    def get_comprehensive_status(self) -> Dict:
        """Get comprehensive system and Barbossa status with enhanced analytics"""
        # Check cache for non-critical status components
        cache_key = 'comprehensive_status'
        cached_status = self._get_cached(cache_key, ttl=15)  # Cache for 15 seconds
        
        if cached_status:
            # Update only timestamp and dynamic data
            cached_status['timestamp'] = datetime.now().isoformat()
            cached_status['performance'] = self.profiler.get_performance_summary()
            return cached_status
        
        status = {
            'version': self.VERSION,
            'timestamp': datetime.now().isoformat(),
            'work_tally': self.work_tally,
            'system_info': self.system_info,
            'health': self.perform_system_health_check() if self.server_manager else None,
            'server_manager': 'active' if self.server_manager else 'inactive',
            'security': 'MAXIMUM - ZKP2P blocked',
            'performance': self.profiler.get_performance_summary(),
            'enhanced_features': {
                'health_monitoring': 'active',
                'resource_management': 'active',
                'performance_analytics': 'active',
                'auto_recovery': self.health_monitor.auto_recovery_enabled,
                'predictive_analytics': True,
                'intelligent_optimization': True
            }
        }
        
        # Add enhanced resource optimization history
        if self.resource_manager.optimization_history:
            status['last_optimization'] = self.resource_manager.optimization_history[-1]
        
        # Add workflow automation status
        status['workflow_automation'] = {
            'active_workflows': len(self.workflow_engine.active_workflows),
            'total_workflows': len(self.workflow_engine.workflows),
            'ready_workflows': len(self.workflow_engine.scheduler.get_ready_workflows())
        }
        
        # Add error handling analytics
        if self.error_handler:
            status['error_analytics'] = self.error_handler.get_error_analytics()
        
        # Add current work
        current_work_file = self.work_tracking_dir / 'current_work.json'
        if current_work_file.exists():
            with open(current_work_file, 'r') as f:
                status['current_work'] = json.load(f)
        
        # Add recent logs
        if self.logs_dir.exists():
            log_files = sorted(self.logs_dir.glob('*.log'), 
                             key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            status['recent_logs'] = [
                {
                    'name': f.name,
                    'size': f"{f.stat().st_size / 1024:.1f} KB",
                    'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                }
                for f in log_files
            ]
        
        # Cache the status
        self._set_cache(cache_key, status, ttl=15)
        
        return status
    
    def cleanup(self):
        """Cleanup resources on shutdown with enhanced monitoring"""
        if self.server_manager:
            self.server_manager.stop_monitoring()
            self.logger.info("Server monitoring stopped")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        self.logger.info("Thread pool executor shutdown")
        
        # Clear cache
        with self._cache_lock:
            cache_size = len(self._cache)
            self._cache.clear()
            self._cache_expiry.clear()
            if cache_size > 0:
                self.logger.info(f"Cleared {cache_size} cached entries")
        
        # Log final performance summary
        performance_summary = self.profiler.get_performance_summary()
        if performance_summary:
            self.logger.info("Enhanced Performance Summary:")
            for operation, stats in performance_summary.items():
                efficiency = stats.get('efficiency_score', 'N/A')
                trend = stats.get('performance_trend', 'N/A')
                self.logger.info(f"  {operation}: avg={stats['avg_duration']:.3f}s, "
                               f"efficiency={efficiency}, trend={trend}, count={stats['count']}")
        
        # Log resource optimization summary
        if self.resource_manager.optimization_history:
            last_opt = self.resource_manager.optimization_history[-1]
            self.logger.info(f"Last resource optimization freed {last_opt['space_freed_mb']:.1f}MB")


def main():
    """Enhanced main entry point"""
    parser = argparse.ArgumentParser(
        description='Barbossa Enhanced - Comprehensive Server Management System with AI-Powered Optimization'
    )
    parser.add_argument(
        '--area',
        choices=['infrastructure', 'personal_projects', 'davy_jones', 'barbossa_self'],
        help='Specific work area to focus on'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show comprehensive status and exit'
    )
    parser.add_argument(
        '--health',
        action='store_true',
        help='Perform enhanced health check and exit'
    )
    parser.add_argument(
        '--test-security',
        action='store_true',
        help='Test security system and exit'
    )
    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Run resource optimization and exit'
    )
    parser.add_argument(
        '--start-portal',
        action='store_true',
        help='Start the enhanced web portal'
    )
    
    args = parser.parse_args()
    
    # Initialize Enhanced Barbossa
    barbossa = BarbossaEnhanced()
    
    try:
        if args.status:
            # Show comprehensive status
            status = barbossa.get_comprehensive_status()
            print(json.dumps(status, indent=2))
            
        elif args.health:
            # Perform enhanced health check
            health = barbossa.perform_system_health_check()
            print(json.dumps(health, indent=2))
            
        elif args.optimize:
            # Run resource optimization
            results = barbossa.resource_manager.optimize_resources()
            print(json.dumps(results, indent=2))
            
        elif args.test_security:
            # Test security
            print("Testing Enhanced Security System...")
            test_repos = [
                "https://github.com/ADWilkinson/barbossa-engineer",  # Should pass
                "https://github.com/zkp2p/zkp2p-v2-contracts",  # Should fail
                "https://github.com/ADWilkinson/davy-jones-intern",  # Should pass
                "https://github.com/ZKP2P/something",  # Should fail
            ]
            
            for repo in test_repos:
                result = barbossa.validate_repository_access(repo)
                status = "✓ ALLOWED" if result else "✗ BLOCKED"
                print(f"{status}: {repo}")
            
        elif args.start_portal:
            # Start web portal
            print("Starting Enhanced Web Portal...")
            portal_script = barbossa.work_dir / 'start_enhanced_portal.sh'
            subprocess.run(['bash', str(portal_script)])
            
        else:
            # Execute enhanced work
            barbossa.execute_work(args.area)
    
    finally:
        barbossa.cleanup()


if __name__ == "__main__":
    main()