#!/usr/bin/env python3
"""
Cleanup Manager for Barbossa
Automated cleanup of old logs, metrics, and temporary files
"""

import json
import logging
import os
import shutil
import gzip
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class CleanupManager:
    """
    Manages automatic cleanup of old files and optimization of storage
    """
    
    def __init__(self, work_dir: Optional[Path] = None):
        """Initialize cleanup manager"""
        self.work_dir = work_dir or Path.home() / 'barbossa-engineer'
        self.logger = logging.getLogger('barbossa.cleanup')
        
        # Cleanup policies (in days)
        self.policies = {
            'logs': {
                'max_age_days': 30,
                'compress_after_days': 7,
                'max_size_mb': 100,
                'patterns': ['*.log', '*.txt']
            },
            'changelogs': {
                'max_age_days': 90,
                'compress_after_days': 30,
                'max_size_mb': 50,
                'patterns': ['*.md']
            },
            'metrics': {
                'max_age_days': 60,
                'compress_after_days': 14,
                'max_size_mb': 200,
                'patterns': ['*.json', '*.csv']
            },
            'backups': {
                'max_age_days': 30,
                'keep_minimum': 5,  # Always keep at least 5 recent backups
                'max_total_size_gb': 10
            },
            'temp': {
                'max_age_days': 3,
                'patterns': ['*.tmp', '*.temp', '*~']
            },
            'cache': {
                'max_age_days': 7,
                'patterns': ['*.cache', '*.cached']
            }
        }
        
        # Track cleanup statistics
        self.stats = {
            'files_deleted': 0,
            'files_compressed': 0,
            'space_freed_mb': 0,
            'last_cleanup': None
        }
        
        self._load_stats()
    
    def _load_stats(self):
        """Load cleanup statistics from file"""
        stats_file = self.work_dir / 'cleanup_stats.json'
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    self.stats.update(json.load(f))
            except Exception as e:
                self.logger.warning(f"Could not load cleanup stats: {e}")
    
    def _save_stats(self):
        """Save cleanup statistics to file"""
        stats_file = self.work_dir / 'cleanup_stats.json'
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save cleanup stats: {e}")
    
    def perform_cleanup(self, dry_run: bool = False) -> Dict:
        """
        Perform comprehensive cleanup of old files
        
        Args:
            dry_run: If True, only simulate cleanup without deleting files
        
        Returns:
            Dictionary with cleanup results
        """
        self.logger.info(f"Starting cleanup {'(DRY RUN)' if dry_run else ''}")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'cleaned': {},
            'errors': [],
            'space_freed_mb': 0,
            'files_deleted': 0,
            'files_compressed': 0
        }
        
        # Clean logs
        self._cleanup_directory(
            self.work_dir / 'logs',
            self.policies['logs'],
            'logs',
            results,
            dry_run
        )
        
        # Clean changelogs
        self._cleanup_directory(
            self.work_dir / 'changelogs',
            self.policies['changelogs'],
            'changelogs',
            results,
            dry_run
        )
        
        # Clean metrics
        self._cleanup_directory(
            self.work_dir / 'metrics',
            self.policies['metrics'],
            'metrics',
            results,
            dry_run
        )
        
        # Clean backups with special handling
        self._cleanup_backups(results, dry_run)
        
        # Clean temporary files
        self._cleanup_temp_files(results, dry_run)
        
        # Archive old health check results
        self._archive_health_checks(results, dry_run)
        
        # Optimize databases
        self._optimize_databases(results, dry_run)
        
        # Update statistics
        if not dry_run:
            self.stats['files_deleted'] += results['files_deleted']
            self.stats['files_compressed'] += results['files_compressed']
            self.stats['space_freed_mb'] += results['space_freed_mb']
            self.stats['last_cleanup'] = datetime.now().isoformat()
            self._save_stats()
        
        # Generate summary
        results['summary'] = self._generate_cleanup_summary(results)
        
        self.logger.info(f"Cleanup completed: {results['files_deleted']} files deleted, "
                        f"{results['files_compressed']} files compressed, "
                        f"{results['space_freed_mb']:.1f} MB freed")
        
        return results
    
    def _cleanup_directory(self, directory: Path, policy: Dict, name: str, 
                          results: Dict, dry_run: bool):
        """Clean up a specific directory based on policy"""
        if not directory.exists():
            return
        
        cleaned_info = {
            'deleted': [],
            'compressed': [],
            'errors': []
        }
        
        now = datetime.now()
        max_age = timedelta(days=policy['max_age_days'])
        compress_age = timedelta(days=policy.get('compress_after_days', 999))
        
        # Find files matching patterns
        for pattern in policy.get('patterns', ['*']):
            for file_path in directory.rglob(pattern):
                if not file_path.is_file():
                    continue
                
                # Skip already compressed files
                if file_path.suffix == '.gz':
                    continue
                
                try:
                    file_age = now - datetime.fromtimestamp(file_path.stat().st_mtime)
                    file_size_mb = file_path.stat().st_size / (1024 * 1024)
                    
                    # Delete old files
                    if file_age > max_age:
                        if not dry_run:
                            file_path.unlink()
                        cleaned_info['deleted'].append(file_path.name)
                        results['files_deleted'] += 1
                        results['space_freed_mb'] += file_size_mb
                        self.logger.debug(f"Deleted: {file_path}")
                    
                    # Compress older files
                    elif file_age > compress_age and file_size_mb > 1:  # Only compress files > 1MB
                        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
                        if not compressed_path.exists():
                            if not dry_run:
                                self._compress_file(file_path, compressed_path)
                            cleaned_info['compressed'].append(file_path.name)
                            results['files_compressed'] += 1
                            # Calculate space saved (approximate)
                            results['space_freed_mb'] += file_size_mb * 0.7  # Assume 70% compression
                            self.logger.debug(f"Compressed: {file_path}")
                    
                except Exception as e:
                    cleaned_info['errors'].append(f"{file_path.name}: {e}")
                    results['errors'].append(f"Error processing {file_path}: {e}")
        
        # Check directory size limit
        if 'max_size_mb' in policy:
            self._enforce_size_limit(directory, policy['max_size_mb'], results, dry_run)
        
        results['cleaned'][name] = cleaned_info
    
    def _cleanup_backups(self, results: Dict, dry_run: bool):
        """Clean up old backups with special handling"""
        backup_dir = self.work_dir / 'backups'
        if not backup_dir.exists():
            return
        
        policy = self.policies['backups']
        backups = []
        
        # Collect all backup files/directories
        for item in backup_dir.iterdir():
            try:
                backups.append({
                    'path': item,
                    'mtime': item.stat().st_mtime,
                    'size_mb': self._get_size_mb(item)
                })
            except:
                pass
        
        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x['mtime'], reverse=True)
        
        # Keep minimum number of backups
        keep_count = policy.get('keep_minimum', 5)
        to_delete = []
        total_size_gb = sum(b['size_mb'] for b in backups) / 1024
        max_size_gb = policy.get('max_total_size_gb', 10)
        
        for i, backup in enumerate(backups):
            # Always keep minimum number
            if i < keep_count:
                continue
            
            # Check age
            age_days = (time.time() - backup['mtime']) / 86400
            if age_days > policy['max_age_days'] or total_size_gb > max_size_gb:
                to_delete.append(backup)
                total_size_gb -= backup['size_mb'] / 1024
        
        # Delete old backups
        for backup in to_delete:
            if not dry_run:
                if backup['path'].is_dir():
                    shutil.rmtree(backup['path'])
                else:
                    backup['path'].unlink()
            results['files_deleted'] += 1
            results['space_freed_mb'] += backup['size_mb']
            self.logger.info(f"Deleted backup: {backup['path'].name}")
    
    def _cleanup_temp_files(self, results: Dict, dry_run: bool):
        """Clean up temporary files throughout the system"""
        temp_policy = self.policies['temp']
        max_age = timedelta(days=temp_policy['max_age_days'])
        now = datetime.now()
        
        # Search for temp files in all subdirectories
        for pattern in temp_policy['patterns']:
            for temp_file in self.work_dir.rglob(pattern):
                if not temp_file.is_file():
                    continue
                
                try:
                    file_age = now - datetime.fromtimestamp(temp_file.stat().st_mtime)
                    if file_age > max_age:
                        size_mb = temp_file.stat().st_size / (1024 * 1024)
                        if not dry_run:
                            temp_file.unlink()
                        results['files_deleted'] += 1
                        results['space_freed_mb'] += size_mb
                        self.logger.debug(f"Deleted temp file: {temp_file}")
                except Exception as e:
                    results['errors'].append(f"Error deleting temp file {temp_file}: {e}")
    
    def _archive_health_checks(self, results: Dict, dry_run: bool):
        """Archive old health check results"""
        health_dir = self.work_dir / 'health'
        if not health_dir.exists():
            return
        
        archive_dir = health_dir / 'archive'
        if not dry_run:
            archive_dir.mkdir(exist_ok=True)
        
        # Archive health checks older than 7 days
        now = datetime.now()
        max_age = timedelta(days=7)
        
        for health_file in health_dir.glob('health_checks*.json'):
            try:
                file_age = now - datetime.fromtimestamp(health_file.stat().st_mtime)
                if file_age > max_age:
                    if not dry_run:
                        # Compress and move to archive
                        archive_path = archive_dir / f"{health_file.stem}_{datetime.now().strftime('%Y%m')}.gz"
                        self._compress_file(health_file, archive_path)
                        health_file.unlink()
                    results['files_compressed'] += 1
                    self.logger.debug(f"Archived health check: {health_file.name}")
            except Exception as e:
                results['errors'].append(f"Error archiving {health_file}: {e}")
    
    def _optimize_databases(self, results: Dict, dry_run: bool):
        """Optimize SQLite databases"""
        import sqlite3
        
        db_files = list(self.work_dir.glob('*.db'))
        
        for db_file in db_files:
            try:
                original_size = db_file.stat().st_size / (1024 * 1024)
                
                if not dry_run:
                    conn = sqlite3.connect(db_file)
                    conn.execute("VACUUM")
                    conn.close()
                
                new_size = db_file.stat().st_size / (1024 * 1024) if not dry_run else original_size
                space_saved = original_size - new_size
                
                if space_saved > 0:
                    results['space_freed_mb'] += space_saved
                    self.logger.info(f"Optimized {db_file.name}: saved {space_saved:.1f} MB")
                    
            except Exception as e:
                results['errors'].append(f"Error optimizing {db_file}: {e}")
    
    def _compress_file(self, source: Path, dest: Path):
        """Compress a file using gzip"""
        with open(source, 'rb') as f_in:
            with gzip.open(dest, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _get_size_mb(self, path: Path) -> float:
        """Get size of file or directory in MB"""
        if path.is_file():
            return path.stat().st_size / (1024 * 1024)
        else:
            total = 0
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
            return total / (1024 * 1024)
    
    def _enforce_size_limit(self, directory: Path, max_size_mb: float, 
                           results: Dict, dry_run: bool):
        """Enforce size limit on a directory by deleting oldest files"""
        files = []
        total_size = 0
        
        # Collect all files with sizes
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                files.append({
                    'path': file_path,
                    'size_mb': size_mb,
                    'mtime': file_path.stat().st_mtime
                })
                total_size += size_mb
        
        # If under limit, nothing to do
        if total_size <= max_size_mb:
            return
        
        # Sort by modification time (oldest first)
        files.sort(key=lambda x: x['mtime'])
        
        # Delete oldest files until under limit
        for file_info in files:
            if total_size <= max_size_mb:
                break
            
            if not dry_run:
                file_info['path'].unlink()
            
            results['files_deleted'] += 1
            results['space_freed_mb'] += file_info['size_mb']
            total_size -= file_info['size_mb']
            self.logger.debug(f"Deleted for size limit: {file_info['path']}")
    
    def _generate_cleanup_summary(self, results: Dict) -> str:
        """Generate a human-readable cleanup summary"""
        lines = []
        lines.append(f"Cleanup Summary ({results['timestamp']})")
        lines.append("-" * 50)
        
        if results['dry_run']:
            lines.append("DRY RUN - No files were actually deleted")
        
        lines.append(f"Files deleted: {results['files_deleted']}")
        lines.append(f"Files compressed: {results['files_compressed']}")
        lines.append(f"Space freed: {results['space_freed_mb']:.1f} MB")
        
        if results['errors']:
            lines.append(f"\nErrors encountered: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Show first 5 errors
                lines.append(f"  - {error}")
        
        lines.append("\nCleaned directories:")
        for name, info in results.get('cleaned', {}).items():
            if info['deleted'] or info['compressed']:
                lines.append(f"  {name}:")
                if info['deleted']:
                    lines.append(f"    Deleted: {len(info['deleted'])} files")
                if info['compressed']:
                    lines.append(f"    Compressed: {len(info['compressed'])} files")
        
        return "\n".join(lines)
    
    def schedule_cleanup(self, interval_hours: int = 24):
        """Schedule automatic cleanup at regular intervals"""
        import threading
        
        def run_cleanup():
            while True:
                time.sleep(interval_hours * 3600)
                try:
                    self.logger.info("Running scheduled cleanup")
                    self.perform_cleanup(dry_run=False)
                except Exception as e:
                    self.logger.error(f"Scheduled cleanup failed: {e}")
        
        thread = threading.Thread(target=run_cleanup, daemon=True)
        thread.start()
        self.logger.info(f"Scheduled cleanup every {interval_hours} hours")
    
    def get_storage_report(self) -> Dict:
        """Generate a storage usage report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'directories': {},
            'total_size_mb': 0,
            'recommendations': []
        }
        
        directories = {
            'logs': self.work_dir / 'logs',
            'changelogs': self.work_dir / 'changelogs',
            'metrics': self.work_dir / 'metrics',
            'backups': self.work_dir / 'backups',
            'health': self.work_dir / 'health',
            'work_tracking': self.work_dir / 'work_tracking'
        }
        
        for name, path in directories.items():
            if path.exists():
                size_mb = self._get_size_mb(path)
                file_count = len(list(path.rglob('*'))) if path.is_dir() else 1
                
                report['directories'][name] = {
                    'size_mb': size_mb,
                    'file_count': file_count
                }
                report['total_size_mb'] += size_mb
                
                # Generate recommendations
                policy = self.policies.get(name, {})
                if 'max_size_mb' in policy and size_mb > policy['max_size_mb']:
                    report['recommendations'].append(
                        f"{name} exceeds size limit ({size_mb:.1f} MB > {policy['max_size_mb']} MB)"
                    )
        
        # Check if cleanup is needed
        if self.stats.get('last_cleanup'):
            last_cleanup = datetime.fromisoformat(self.stats['last_cleanup'])
            days_since = (datetime.now() - last_cleanup).days
            if days_since > 7:
                report['recommendations'].append(
                    f"Cleanup recommended (last run {days_since} days ago)"
                )
        else:
            report['recommendations'].append("Initial cleanup recommended")
        
        return report