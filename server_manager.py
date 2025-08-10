#!/usr/bin/env python3
"""
Barbossa Server Manager - Comprehensive Server Infrastructure Management
Enhanced version with complete server monitoring, management, and control capabilities
"""

import asyncio
import json
import logging
import os
import platform
import psutil
import socket
import sqlite3
import subprocess
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import threading
import queue
import functools
import concurrent.futures
from contextlib import contextmanager

# Import existing security guard
from security_guard import security_guard, SecurityViolationError


class MetricsCollector:
    """Collects and stores system metrics with historical data"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.metrics_queue = queue.Queue()
        self.running = False
        self._cache = {}
        self._cache_expiry = {}
        self._cache_lock = threading.Lock()
        self._connection_pool = queue.Queue(maxsize=5)
        self._init_database()
        self._init_connection_pool()
    
    def _init_connection_pool(self):
        """Initialize database connection pool"""
        for _ in range(5):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._connection_pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        """Get database connection from pool"""
        conn = self._connection_pool.get()
        try:
            yield conn
        finally:
            self._connection_pool.put(conn)
    
    def _get_cached(self, key: str, ttl: int = 60):
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
    
    def _set_cache(self, key: str, value: Any, ttl: int = 60):
        """Set cached value with TTL"""
        with self._cache_lock:
            self._cache[key] = value
            self._cache_expiry[key] = time.time() + ttl
        
    def _init_database(self):
        """Initialize SQLite database for metrics storage with optimizations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Enable performance optimizations
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA synchronous=NORMAL')
            cursor.execute('PRAGMA cache_size=10000')
            cursor.execute('PRAGMA temp_store=MEMORY')
            
            # System metrics table with indexes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_used_mb INTEGER,
                    memory_total_mb INTEGER,
                    disk_percent REAL,
                    disk_used_gb REAL,
                    disk_total_gb REAL,
                    network_sent_mb REAL,
                    network_recv_mb REAL,
                    load_1min REAL,
                    load_5min REAL,
                    load_15min REAL,
                    process_count INTEGER,
                    docker_containers INTEGER,
                    temperature REAL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp)')
            
            # Service status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS service_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT,
                    status TEXT,
                    cpu_percent REAL,
                    memory_mb REAL,
                    uptime_seconds INTEGER,
                    pid INTEGER
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_status_timestamp ON service_status(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_service_status_name ON service_status(service_name)')
            
            # Alert history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT,
                    category TEXT,
                    message TEXT,
                    details TEXT,
                    acknowledged BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged)')
            
            # Barbossa work history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS work_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    work_area TEXT,
                    status TEXT,
                    duration_seconds INTEGER,
                    repository TEXT,
                    commit_hash TEXT,
                    pr_url TEXT,
                    changelog TEXT
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_history_timestamp ON work_history(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_work_history_area ON work_history(work_area)')
            
            # Network connections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS network_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    local_address TEXT,
                    local_port INTEGER,
                    remote_address TEXT,
                    remote_port INTEGER,
                    status TEXT,
                    process_name TEXT,
                    pid INTEGER
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_network_connections_timestamp ON network_connections(timestamp)')
            
            conn.commit()
    
    @functools.lru_cache(maxsize=128)
    def _get_static_info(self):
        """Get static system information that doesn't change frequently"""
        return {
            'cpu_count': psutil.cpu_count(),
            'memory_total_mb': psutil.virtual_memory().total / (1024 * 1024),
            'disk_total_gb': psutil.disk_usage('/').total / (1024 * 1024 * 1024),
            'boot_time': psutil.boot_time()
        }
    
    def collect_metrics(self) -> Dict:
        """Collect current system metrics with caching optimization"""
        # Check cache first for recent metrics
        cache_key = 'current_metrics'
        cached_metrics = self._get_cached(cache_key, ttl=10)  # 10 second cache
        if cached_metrics:
            return cached_metrics
        
        metrics = {}
        static_info = self._get_static_info()
        
        # CPU metrics (most expensive - use shorter interval when cached)
        metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        metrics['cpu_count'] = static_info['cpu_count']
        try:
            cpu_freq = psutil.cpu_freq()
            metrics['cpu_freq'] = cpu_freq.current if cpu_freq else 0
        except:
            metrics['cpu_freq'] = 0
        
        # Memory metrics
        mem = psutil.virtual_memory()
        metrics['memory_percent'] = mem.percent
        metrics['memory_used_mb'] = mem.used / (1024 * 1024)
        metrics['memory_total_mb'] = static_info['memory_total_mb']
        metrics['memory_available_mb'] = mem.available / (1024 * 1024)
        
        # Disk metrics (cache for 30 seconds as it's relatively stable)
        disk_cache_key = 'disk_metrics'
        disk_metrics = self._get_cached(disk_cache_key, ttl=30)
        if not disk_metrics:
            disk = psutil.disk_usage('/')
            disk_metrics = {
                'disk_percent': disk.percent,
                'disk_used_gb': disk.used / (1024 * 1024 * 1024),
                'disk_total_gb': static_info['disk_total_gb'],
                'disk_free_gb': disk.free / (1024 * 1024 * 1024)
            }
            self._set_cache(disk_cache_key, disk_metrics, ttl=30)
        metrics.update(disk_metrics)
        
        # Network metrics (calculate deltas)
        net_cache_key = 'network_counters'
        previous_net = self._get_cached(net_cache_key, ttl=300)  # 5 min cache
        net = psutil.net_io_counters()
        
        current_net = {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv,
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv,
            'timestamp': time.time()
        }
        
        if previous_net:
            time_delta = current_net['timestamp'] - previous_net['timestamp']
            if time_delta > 0:
                metrics['network_sent_mbps'] = (current_net['bytes_sent'] - previous_net['bytes_sent']) / (1024 * 1024 * time_delta)
                metrics['network_recv_mbps'] = (current_net['bytes_recv'] - previous_net['bytes_recv']) / (1024 * 1024 * time_delta)
            else:
                metrics['network_sent_mbps'] = 0
                metrics['network_recv_mbps'] = 0
        else:
            metrics['network_sent_mbps'] = 0
            metrics['network_recv_mbps'] = 0
        
        metrics['network_sent_mb'] = net.bytes_sent / (1024 * 1024)
        metrics['network_recv_mb'] = net.bytes_recv / (1024 * 1024)
        metrics['network_packets_sent'] = net.packets_sent
        metrics['network_packets_recv'] = net.packets_recv
        
        self._set_cache(net_cache_key, current_net, ttl=300)
        
        # System load
        load = os.getloadavg()
        metrics['load_1min'] = load[0]
        metrics['load_5min'] = load[1]
        metrics['load_15min'] = load[2]
        
        # Process count (cache for 5 seconds)
        proc_cache_key = 'process_count'
        proc_count = self._get_cached(proc_cache_key, ttl=5)
        if proc_count is None:
            proc_count = len(psutil.pids())
            self._set_cache(proc_cache_key, proc_count, ttl=5)
        metrics['process_count'] = proc_count
        
        # Docker containers count (cache for 15 seconds)
        docker_cache_key = 'docker_containers'
        docker_count = self._get_cached(docker_cache_key, ttl=15)
        if docker_count is None:
            try:
                result = subprocess.run(['docker', 'ps', '-q'], capture_output=True, text=True, timeout=5)
                docker_count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            except:
                docker_count = 0
            self._set_cache(docker_cache_key, docker_count, ttl=15)
        metrics['docker_containers'] = docker_count
        
        # Temperature (cache for 30 seconds)
        temp_cache_key = 'temperature'
        temperature = self._get_cached(temp_cache_key, ttl=30)
        if temperature is None:
            try:
                temps = psutil.sensors_temperatures()
                temperature = None
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            if entry.label in ['Core 0', 'CPU', 'Package']:
                                temperature = entry.current
                                break
                        if temperature:
                            break
            except:
                temperature = None
            self._set_cache(temp_cache_key, temperature, ttl=30)
        metrics['temperature'] = temperature
        
        # Uptime
        metrics['uptime_seconds'] = time.time() - static_info['boot_time']
        
        # Cache the complete metrics
        self._set_cache(cache_key, metrics, ttl=10)
        
        return metrics
    
    def store_metrics(self, metrics: Dict):
        """Store metrics in database using connection pool"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_metrics (
                        cpu_percent, memory_percent, memory_used_mb, memory_total_mb,
                        disk_percent, disk_used_gb, disk_total_gb,
                        network_sent_mb, network_recv_mb,
                        load_1min, load_5min, load_15min,
                        process_count, docker_containers, temperature
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.get('cpu_percent'),
                    metrics.get('memory_percent'),
                    metrics.get('memory_used_mb'),
                    metrics.get('memory_total_mb'),
                    metrics.get('disk_percent'),
                    metrics.get('disk_used_gb'),
                    metrics.get('disk_total_gb'),
                    metrics.get('network_sent_mb'),
                    metrics.get('network_recv_mb'),
                    metrics.get('load_1min'),
                    metrics.get('load_5min'),
                    metrics.get('load_15min'),
                    metrics.get('process_count'),
                    metrics.get('docker_containers'),
                    metrics.get('temperature')
                ))
                conn.commit()
        except Exception as e:
            # Log error but don't crash the monitoring
            logging.getLogger(__name__).error(f"Failed to store metrics: {e}")
    
    def store_metrics_batch(self, metrics_list: List[Dict]):
        """Store multiple metrics in a single transaction for better performance"""
        if not metrics_list:
            return
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                data = []
                for metrics in metrics_list:
                    data.append((
                        metrics.get('cpu_percent'),
                        metrics.get('memory_percent'),
                        metrics.get('memory_used_mb'),
                        metrics.get('memory_total_mb'),
                        metrics.get('disk_percent'),
                        metrics.get('disk_used_gb'),
                        metrics.get('disk_total_gb'),
                        metrics.get('network_sent_mb'),
                        metrics.get('network_recv_mb'),
                        metrics.get('load_1min'),
                        metrics.get('load_5min'),
                        metrics.get('load_15min'),
                        metrics.get('process_count'),
                        metrics.get('docker_containers'),
                        metrics.get('temperature')
                    ))
                
                cursor.executemany('''
                    INSERT INTO system_metrics (
                        cpu_percent, memory_percent, memory_used_mb, memory_total_mb,
                        disk_percent, disk_used_gb, disk_total_gb,
                        network_sent_mb, network_recv_mb,
                        load_1min, load_5min, load_15min,
                        process_count, docker_containers, temperature
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', data)
                conn.commit()
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to store metrics batch: {e}")
    
    def get_historical_metrics(self, hours: int = 24, limit: int = 1000) -> List[Dict]:
        """Get historical metrics for the specified time period with caching and optimization"""
        cache_key = f'historical_metrics_{hours}h_{limit}'
        cached_result = self._get_cached(cache_key, ttl=300)  # 5 min cache
        if cached_result:
            return cached_result
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Use LIMIT for performance and select only needed columns
                cursor.execute('''
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent, 
                           network_sent_mb, network_recv_mb, load_1min, 
                           process_count, docker_containers, temperature
                    FROM system_metrics 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (cutoff, limit))
                
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # Cache the result
                self._set_cache(cache_key, result, ttl=300)
                return result
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to get historical metrics: {e}")
            return []
    
    def cleanup_old_metrics(self, days: int = 30):
        """Clean up metrics older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM system_metrics WHERE timestamp < ?', (cutoff,))
            cursor.execute('DELETE FROM service_status WHERE timestamp < ?', (cutoff,))
            cursor.execute('DELETE FROM network_connections WHERE timestamp < ?', (cutoff,))
            conn.commit()


class ServiceManager:
    """Manages system services and Docker containers"""
    
    def __init__(self, metrics_db: Path):
        self.metrics_db = metrics_db
        self.services = {}
        self.docker_containers = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="ServiceManager")
        self._cache = {}
        self._cache_expiry = {}
        self._cache_lock = threading.Lock()
        self._update_services()
    
    def _get_cached(self, key: str, ttl: int = 60):
        """Get cached value if not expired"""
        with self._cache_lock:
            if key in self._cache and key in self._cache_expiry:
                if time.time() < self._cache_expiry[key]:
                    return self._cache[key]
                else:
                    del self._cache[key]
                    del self._cache_expiry[key]
            return None
    
    def _set_cache(self, key: str, value: Any, ttl: int = 60):
        """Set cached value with TTL"""
        with self._cache_lock:
            self._cache[key] = value
            self._cache_expiry[key] = time.time() + ttl
    
    def _update_services(self):
        """Update service and container information with parallel execution"""
        # Check cache first
        cache_key = 'all_services'
        cached_services = self._get_cached(cache_key, ttl=30)
        if cached_services:
            self.services = cached_services.get('services', {})
            self.docker_containers = cached_services.get('docker_containers', {})
            self.tmux_sessions = cached_services.get('tmux_sessions', [])
            return
        
        # Submit tasks to executor for parallel execution
        futures = {
            'services': self.executor.submit(self._get_systemd_services),
            'docker': self.executor.submit(self._get_docker_containers),
            'tmux': self.executor.submit(self._get_tmux_sessions)
        }
        
        # Wait for all tasks to complete
        try:
            self.services = futures['services'].result(timeout=10)
            self.docker_containers = futures['docker'].result(timeout=10)
            self.tmux_sessions = futures['tmux'].result(timeout=5)
            
            # Cache the results
            all_services = {
                'services': self.services,
                'docker_containers': self.docker_containers,
                'tmux_sessions': self.tmux_sessions
            }
            self._set_cache(cache_key, all_services, ttl=30)
            
        except concurrent.futures.TimeoutError:
            # Fallback to cached data if available
            for future in futures.values():
                future.cancel()
            logging.getLogger(__name__).warning("Service update timeout, using cached data")
    
    def _get_systemd_services(self) -> Dict:
        """Get status of important systemd services"""
        services = {}
        important_services = [
            'docker', 'ssh', 'nginx', 'postgresql', 'redis', 
            'cloudflared', 'grafana-server', 'prometheus'
        ]
        
        for service in important_services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True, text=True
                )
                services[service] = {
                    'status': result.stdout.strip(),
                    'active': result.stdout.strip() == 'active'
                }
                
                # Get additional info if active
                if services[service]['active']:
                    result = subprocess.run(
                        ['systemctl', 'show', service, '--property=MainPID,MemoryCurrent'],
                        capture_output=True, text=True
                    )
                    for line in result.stdout.strip().split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            if key == 'MainPID':
                                services[service]['pid'] = int(value) if value != '0' else None
                            elif key == 'MemoryCurrent' and value != '[not set]':
                                services[service]['memory_mb'] = int(value) / (1024 * 1024)
            except:
                services[service] = {'status': 'unknown', 'active': False}
        
        # Special handling for cloudflared which runs in tmux
        if 'cloudflared' in services and not services['cloudflared']['active']:
            # Check if cloudflared is running in tmux
            try:
                result = subprocess.run(['pgrep', '-f', 'cloudflared tunnel'], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    services['cloudflared'] = {
                        'status': 'active (tmux)',
                        'active': True,
                        'pid': int(result.stdout.strip().split()[0])
                    }
            except:
                pass
        
        return services
    
    def _get_docker_containers(self) -> Dict:
        """Get Docker container information"""
        containers = {}
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', 'json'],
                capture_output=True, text=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    container = json.loads(line)
                    containers[container['Names']] = {
                        'id': container['ID'],
                        'image': container['Image'],
                        'status': container['Status'],
                        'state': container['State'],
                        'ports': container.get('Ports', ''),
                        'running': container['State'] == 'running'
                    }
                    
                    # Get resource usage for running containers
                    if containers[container['Names']]['running']:
                        stats_result = subprocess.run(
                            ['docker', 'stats', container['ID'], '--no-stream', '--format', 'json'],
                            capture_output=True, text=True
                        )
                        if stats_result.stdout:
                            stats = json.loads(stats_result.stdout)
                            containers[container['Names']]['cpu_percent'] = stats.get('CPUPerc', '0%').rstrip('%')
                            containers[container['Names']]['memory_usage'] = stats.get('MemUsage', '')
        except:
            pass
        
        return containers
    
    def _get_tmux_sessions(self) -> List[Dict]:
        """Get tmux session information"""
        sessions = []
        
        try:
            result = subprocess.run(['tmux', 'ls'], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        parts = line.split(':')
                        session_name = parts[0]
                        info = ':'.join(parts[1:])
                        
                        sessions.append({
                            'name': session_name,
                            'windows': info.split(' ')[0],
                            'created': info.split('(created')[1].rstrip(')') if 'created' in info else '',
                            'attached': 'attached' in info
                        })
        except:
            pass
        
        return sessions
    
    def start_service(self, service_name: str) -> Tuple[bool, str]:
        """Start a system service or Docker container"""
        if service_name in self.services:
            # Systemd service
            result = subprocess.run(
                ['sudo', 'systemctl', 'start', service_name],
                capture_output=True, text=True
            )
            return result.returncode == 0, result.stderr or result.stdout
        
        elif service_name in self.docker_containers:
            # Docker container
            result = subprocess.run(
                ['docker', 'start', self.docker_containers[service_name]['id']],
                capture_output=True, text=True
            )
            return result.returncode == 0, result.stderr or result.stdout
        
        return False, f"Service {service_name} not found"
    
    def stop_service(self, service_name: str) -> Tuple[bool, str]:
        """Stop a system service or Docker container"""
        if service_name in self.services:
            # Systemd service
            result = subprocess.run(
                ['sudo', 'systemctl', 'stop', service_name],
                capture_output=True, text=True
            )
            return result.returncode == 0, result.stderr or result.stdout
        
        elif service_name in self.docker_containers:
            # Docker container
            result = subprocess.run(
                ['docker', 'stop', self.docker_containers[service_name]['id']],
                capture_output=True, text=True
            )
            return result.returncode == 0, result.stderr or result.stdout
        
        return False, f"Service {service_name} not found"
    
    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """Restart a system service or Docker container"""
        if service_name in self.services:
            # Systemd service
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', service_name],
                capture_output=True, text=True
            )
            return result.returncode == 0, result.stderr or result.stdout
        
        elif service_name in self.docker_containers:
            # Docker container
            result = subprocess.run(
                ['docker', 'restart', self.docker_containers[service_name]['id']],
                capture_output=True, text=True
            )
            return result.returncode == 0, result.stderr or result.stdout
        
        return False, f"Service {service_name} not found"


class NetworkMonitor:
    """Monitors network connections and port usage"""
    
    def __init__(self, metrics_db: Path):
        self.metrics_db = metrics_db
        self.known_ports = {
            22: 'SSH',
            80: 'HTTP',
            443: 'HTTPS',
            3000: 'Grafana',
            5173: 'Vite Dev',
            8080: 'VS Code Server',
            8443: 'Barbossa Portal',
            9000: 'Portainer',
            9090: 'Prometheus',
            5432: 'PostgreSQL',
            6379: 'Redis',
            3306: 'MySQL',
            27017: 'MongoDB'
        }
    
    def get_network_connections(self) -> List[Dict]:
        """Get current network connections"""
        connections = []
        
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' or conn.status == 'ESTABLISHED':
                connection = {
                    'local_address': conn.laddr.ip if conn.laddr else '',
                    'local_port': conn.laddr.port if conn.laddr else 0,
                    'remote_address': conn.raddr.ip if conn.raddr else '',
                    'remote_port': conn.raddr.port if conn.raddr else 0,
                    'status': conn.status,
                    'pid': conn.pid,
                    'service': self.known_ports.get(conn.laddr.port if conn.laddr else 0, 'Unknown')
                }
                
                # Get process name if PID is available
                if conn.pid:
                    try:
                        process = psutil.Process(conn.pid)
                        connection['process_name'] = process.name()
                    except:
                        connection['process_name'] = 'Unknown'
                
                connections.append(connection)
        
        return connections
    
    def get_open_ports(self) -> List[Dict]:
        """Get list of open ports"""
        open_ports = []
        seen_ports = set()
        
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr:
                port = conn.laddr.port
                if port not in seen_ports:
                    seen_ports.add(port)
                    open_ports.append({
                        'port': port,
                        'address': conn.laddr.ip,
                        'service': self.known_ports.get(port, 'Unknown'),
                        'pid': conn.pid
                    })
        
        return sorted(open_ports, key=lambda x: x['port'])
    
    def check_port_availability(self, port: int) -> bool:
        """Check if a port is available for use"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('', port))
            sock.close()
            return True
        except:
            return False
    
    def store_connections(self, connections: List[Dict]):
        """Store network connections in database"""
        with sqlite3.connect(self.metrics_db) as conn:
            cursor = conn.cursor()
            for connection in connections[:100]:  # Limit to 100 connections
                cursor.execute('''
                    INSERT INTO network_connections (
                        local_address, local_port, remote_address, remote_port,
                        status, process_name, pid
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    connection.get('local_address'),
                    connection.get('local_port'),
                    connection.get('remote_address'),
                    connection.get('remote_port'),
                    connection.get('status'),
                    connection.get('process_name'),
                    connection.get('pid')
                ))
            conn.commit()


class ProjectManager:
    """Manages git repositories and project information"""
    
    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir
        self.projects = {}
        self._scan_projects()
    
    def _scan_projects(self):
        """Scan for git projects"""
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir() and (project_dir / '.git').exists():
                self.projects[project_dir.name] = self._get_project_info(project_dir)
    
    def _get_project_info(self, project_dir: Path) -> Dict:
        """Get information about a git project"""
        info = {
            'path': str(project_dir),
            'name': project_dir.name,
            'last_modified': datetime.fromtimestamp(project_dir.stat().st_mtime).isoformat()
        }
        
        # Get git information
        try:
            # Current branch
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=project_dir, capture_output=True, text=True
            )
            info['branch'] = result.stdout.strip()
            
            # Last commit
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H %s %ar'],
                cwd=project_dir, capture_output=True, text=True
            )
            if result.stdout:
                parts = result.stdout.strip().split(' ', 2)
                if len(parts) >= 3:
                    info['last_commit'] = {
                        'hash': parts[0][:8],
                        'message': parts[1],
                        'time': parts[2]
                    }
            
            # Check for uncommitted changes
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=project_dir, capture_output=True, text=True
            )
            info['has_changes'] = bool(result.stdout.strip())
            
            # Remote URL
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=project_dir, capture_output=True, text=True
            )
            info['remote_url'] = result.stdout.strip()
            
        except:
            pass
        
        # Get project type and language
        if (project_dir / 'package.json').exists():
            info['type'] = 'Node.js'
            info['language'] = 'JavaScript/TypeScript'
        elif (project_dir / 'requirements.txt').exists() or (project_dir / 'setup.py').exists():
            info['type'] = 'Python'
            info['language'] = 'Python'
        elif (project_dir / 'Cargo.toml').exists():
            info['type'] = 'Rust'
            info['language'] = 'Rust'
        elif (project_dir / 'go.mod').exists():
            info['type'] = 'Go'
            info['language'] = 'Go'
        else:
            info['type'] = 'Unknown'
            info['language'] = 'Unknown'
        
        return info
    
    def get_project_stats(self) -> Dict:
        """Get statistics about all projects"""
        stats = {
            'total_projects': len(self.projects),
            'projects_with_changes': sum(1 for p in self.projects.values() if p.get('has_changes')),
            'languages': defaultdict(int),
            'types': defaultdict(int)
        }
        
        for project in self.projects.values():
            stats['languages'][project.get('language', 'Unknown')] += 1
            stats['types'][project.get('type', 'Unknown')] += 1
        
        return stats


class AlertManager:
    """Manages system alerts and notifications"""
    
    def __init__(self, metrics_db: Path):
        self.metrics_db = metrics_db
        self.alert_rules = {
            'high_cpu': {'threshold': 90, 'duration': 300, 'level': 'warning'},
            'high_memory': {'threshold': 90, 'duration': 300, 'level': 'warning'},
            'high_disk': {'threshold': 90, 'duration': 60, 'level': 'critical'},
            'service_down': {'duration': 60, 'level': 'error'},
            'security_violation': {'level': 'critical'},
            'barbossa_failure': {'level': 'error'}
        }
        self.active_alerts = {}
    
    def check_alerts(self, metrics: Dict, services: Dict) -> List[Dict]:
        """Check for alert conditions"""
        alerts = []
        current_time = time.time()
        
        # CPU alert
        if metrics.get('cpu_percent', 0) > self.alert_rules['high_cpu']['threshold']:
            alert_key = 'high_cpu'
            if alert_key not in self.active_alerts:
                self.active_alerts[alert_key] = current_time
            elif current_time - self.active_alerts[alert_key] > self.alert_rules['high_cpu']['duration']:
                alerts.append({
                    'level': self.alert_rules['high_cpu']['level'],
                    'category': 'System',
                    'message': f"High CPU usage: {metrics['cpu_percent']:.1f}%",
                    'details': f"CPU has been above {self.alert_rules['high_cpu']['threshold']}% for {self.alert_rules['high_cpu']['duration']} seconds"
                })
        else:
            self.active_alerts.pop('high_cpu', None)
        
        # Memory alert
        if metrics.get('memory_percent', 0) > self.alert_rules['high_memory']['threshold']:
            alert_key = 'high_memory'
            if alert_key not in self.active_alerts:
                self.active_alerts[alert_key] = current_time
            elif current_time - self.active_alerts[alert_key] > self.alert_rules['high_memory']['duration']:
                alerts.append({
                    'level': self.alert_rules['high_memory']['level'],
                    'category': 'System',
                    'message': f"High memory usage: {metrics['memory_percent']:.1f}%",
                    'details': f"Memory has been above {self.alert_rules['high_memory']['threshold']}% for {self.alert_rules['high_memory']['duration']} seconds"
                })
        else:
            self.active_alerts.pop('high_memory', None)
        
        # Disk alert
        if metrics.get('disk_percent', 0) > self.alert_rules['high_disk']['threshold']:
            alerts.append({
                'level': self.alert_rules['high_disk']['level'],
                'category': 'System',
                'message': f"High disk usage: {metrics['disk_percent']:.1f}%",
                'details': f"Disk space is critically low. Free space: {metrics.get('disk_free_gb', 0):.1f} GB"
            })
        
        # Service alerts
        for service_name, service_info in services.items():
            if not service_info.get('active', False) and service_name in ['docker', 'cloudflared']:
                alert_key = f'service_down_{service_name}'
                if alert_key not in self.active_alerts:
                    self.active_alerts[alert_key] = current_time
                elif current_time - self.active_alerts[alert_key] > self.alert_rules['service_down']['duration']:
                    alerts.append({
                        'level': self.alert_rules['service_down']['level'],
                        'category': 'Service',
                        'message': f"Service down: {service_name}",
                        'details': f"Service {service_name} has been down for {self.alert_rules['service_down']['duration']} seconds"
                    })
            else:
                self.active_alerts.pop(f'service_down_{service_name}', None)
        
        return alerts
    
    def store_alerts(self, alerts: List[Dict]):
        """Store alerts in database"""
        with sqlite3.connect(self.metrics_db) as conn:
            cursor = conn.cursor()
            for alert in alerts:
                cursor.execute('''
                    INSERT INTO alerts (level, category, message, details)
                    VALUES (?, ?, ?, ?)
                ''', (
                    alert['level'],
                    alert['category'],
                    alert['message'],
                    alert['details']
                ))
            conn.commit()
    
    def get_recent_alerts(self, hours: int = 24, acknowledged: Optional[bool] = None) -> List[Dict]:
        """Get recent alerts from database"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.metrics_db) as conn:
            cursor = conn.cursor()
            
            if acknowledged is None:
                cursor.execute('''
                    SELECT * FROM alerts 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC
                ''', (cutoff,))
            else:
                cursor.execute('''
                    SELECT * FROM alerts 
                    WHERE timestamp > ? AND acknowledged = ?
                    ORDER BY timestamp DESC
                ''', (cutoff, acknowledged))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge an alert"""
        with sqlite3.connect(self.metrics_db) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE alerts SET acknowledged = 1 WHERE id = ?', (alert_id,))
            conn.commit()


class BarbossaServerManager:
    """Main server management system integrating all components"""
    
    def __init__(self):
        self.work_dir = Path.home() / 'barbossa-engineer'
        self.db_path = self.work_dir / 'metrics.db'
        
        # Initialize components
        self.metrics_collector = MetricsCollector(self.db_path)
        self.service_manager = ServiceManager(self.db_path)
        self.network_monitor = NetworkMonitor(self.db_path)
        self.project_manager = ProjectManager(self.work_dir / 'projects')
        self.alert_manager = AlertManager(self.db_path)
        
        # Background threads
        self.metrics_thread = None
        self.running = False
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging"""
        log_file = self.work_dir / 'logs' / f"server_manager_{datetime.now().strftime('%Y%m%d')}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('BarbossaServerManager')
    
    def start_monitoring(self):
        """Start background monitoring"""
        if not self.running:
            self.running = True
            self.metrics_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.metrics_thread.start()
            self.logger.info("Server monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.running = False
        if self.metrics_thread:
            self.metrics_thread.join(timeout=5)
        self.logger.info("Server monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Collect metrics
                metrics = self.metrics_collector.collect_metrics()
                self.metrics_collector.store_metrics(metrics)
                
                # Update services
                self.service_manager._update_services()
                
                # Check alerts
                alerts = self.alert_manager.check_alerts(metrics, self.service_manager.services)
                if alerts:
                    self.alert_manager.store_alerts(alerts)
                    for alert in alerts:
                        self.logger.warning(f"Alert: {alert['message']}")
                
                # Store network connections periodically (every 5 minutes)
                if int(time.time()) % 300 < 60:
                    connections = self.network_monitor.get_network_connections()
                    self.network_monitor.store_connections(connections)
                
                # Sleep for 60 seconds
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'hostname': socket.gethostname(),
                'platform': platform.platform(),
                'uptime': self._format_uptime(time.time() - psutil.boot_time())
            },
            'metrics': self.metrics_collector.collect_metrics(),
            'services': {
                'systemd': self.service_manager.services,
                'docker': self.service_manager.docker_containers,
                'tmux': self.service_manager.tmux_sessions
            },
            'network': {
                'connections': len(self.network_monitor.get_network_connections()),
                'open_ports': self.network_monitor.get_open_ports()
            },
            'projects': self.project_manager.get_project_stats(),
            'alerts': {
                'active': len([a for a in self.alert_manager.get_recent_alerts(1) if not a.get('acknowledged')]),
                'recent': self.alert_manager.get_recent_alerts(24)[:5]
            }
        }
        
        return data
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def execute_command(self, command: str, args: Dict) -> Dict:
        """Execute management commands"""
        commands = {
            'start_service': lambda: self.service_manager.start_service(args.get('service')),
            'stop_service': lambda: self.service_manager.stop_service(args.get('service')),
            'restart_service': lambda: self.service_manager.restart_service(args.get('service')),
            'acknowledge_alert': lambda: self.alert_manager.acknowledge_alert(args.get('alert_id')),
            'cleanup_metrics': lambda: self.metrics_collector.cleanup_old_metrics(args.get('days', 30)),
            'scan_projects': lambda: self.project_manager._scan_projects()
        }
        
        if command in commands:
            try:
                result = commands[command]()
                return {'success': True, 'result': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': f"Unknown command: {command}"}


def main():
    """Main entry point for server manager"""
    manager = BarbossaServerManager()
    
    # Start monitoring
    manager.start_monitoring()
    
    print("Barbossa Server Manager initialized")
    print(f"Database: {manager.db_path}")
    print("Monitoring started in background")
    
    # Get initial dashboard data
    data = manager.get_dashboard_data()
    print(f"\nSystem: {data['system']['hostname']} - Uptime: {data['system']['uptime']}")
    print(f"CPU: {data['metrics']['cpu_percent']:.1f}% | Memory: {data['metrics']['memory_percent']:.1f}%")
    print(f"Active Alerts: {data['alerts']['active']}")
    
    # Keep running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nShutting down...")
        manager.stop_monitoring()


if __name__ == "__main__":
    main()