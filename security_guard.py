#!/usr/bin/env python3
"""
Security Guard Module for Barbossa
CRITICAL: Prevents any access to ZKP2P organization repositories
Enhanced with advanced security features and monitoring
"""

import json
import logging
import os
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Import enhanced security features
try:
    from security_enhanced import SecurityEnhanced
    ENHANCED_SECURITY_AVAILABLE = True
except ImportError:
    ENHANCED_SECURITY_AVAILABLE = False


class SecurityViolationError(Exception):
    """Raised when a security violation is detected"""
    pass


class RepositorySecurityGuard:
    """
    Enforces strict security rules to prevent access to ZKP2P organization repositories.
    This is the primary defense against unauthorized repository access.
    """
    
    FORBIDDEN_ORGS = [
        'zkp2p', 'ZKP2P', 'zkp2p-org', 'ZKP2P-org',
        'zkp2p-protocol', 'ZKP2P-protocol'
    ]
    
    FORBIDDEN_PATTERNS = [
        # Only block actual repository URLs, not mentions in text
        r'github\.com[/:](zkp2p|ZKP2P)[/:][\w-]+',  # GitHub repos
        r'git@github\.com:(zkp2p|ZKP2P)[/:]',  # SSH URLs
        r'gitlab\.com[/:](zkp2p|ZKP2P)[/:]',  # GitLab repos
        r'bitbucket\.org[/:](zkp2p|ZKP2P)[/:]'  # Bitbucket repos
    ]
    
    ALLOWED_OWNER = 'ADWilkinson'
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the security guard with configuration"""
        self.config_path = config_path or Path(__file__).parent / 'config' / 'repository_whitelist.json'
        self.audit_log_path = Path(__file__).parent / 'security' / 'audit.log'
        self.violations_log_path = Path(__file__).parent / 'security' / 'security_violations.log'
        
        # Ensure security directories exist
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self._setup_logging()
        
        # Load whitelist
        self.whitelist = self._load_whitelist()
        
        # Initialize enhanced security if available
        self.enhanced_security = None
        if ENHANCED_SECURITY_AVAILABLE:
            try:
                self.enhanced_security = SecurityEnhanced()
                self.audit_logger.info("Enhanced security features enabled")
            except Exception as e:
                self.audit_logger.warning(f"Could not enable enhanced security: {e}")
        
    def _setup_logging(self):
        """Configure logging for security events"""
        # Audit logger - logs all repository access attempts
        self.audit_logger = logging.getLogger('security.audit')
        self.audit_logger.setLevel(logging.INFO)
        audit_handler = logging.FileHandler(self.audit_log_path)
        audit_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.audit_logger.addHandler(audit_handler)
        
        # Violations logger - logs security violations
        self.violations_logger = logging.getLogger('security.violations')
        self.violations_logger.setLevel(logging.WARNING)
        violations_handler = logging.FileHandler(self.violations_log_path)
        violations_handler.setFormatter(
            logging.Formatter('%(asctime)s - VIOLATION - %(message)s')
        )
        self.violations_logger.addHandler(violations_handler)
    
    def _load_whitelist(self) -> Dict:
        """Load the repository whitelist configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {
            'allowed_repositories': [],
            'allowed_owner': self.ALLOWED_OWNER
        }
    
    def validate_repository_url(self, url: str) -> Tuple[bool, str]:
        """
        Validate a repository URL against security rules with enhanced checks.
        
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        self.audit_logger.info(f"Validating repository URL: {url}")
        
        # Enhanced security: Check for URL obfuscation attempts
        if self.enhanced_security:
            suspicious_patterns = self.enhanced_security.detect_suspicious_patterns(url)
            if suspicious_patterns:
                violation_msg = f"BLOCKED: URL contains suspicious patterns: {suspicious_patterns}"
                self._log_violation(violation_msg, url)
                return False, violation_msg
        
        # Check for forbidden organizations
        for org in self.FORBIDDEN_ORGS:
            if org.lower() in url.lower():
                violation_msg = f"BLOCKED: URL contains forbidden organization '{org}': {url}"
                self._log_violation(violation_msg, url)
                return False, violation_msg
        
        # Check forbidden patterns
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                violation_msg = f"BLOCKED: URL matches forbidden pattern '{pattern}': {url}"
                self._log_violation(violation_msg, url)
                return False, violation_msg
        
        # Extract owner from GitHub URL
        github_pattern = r'github\.com[/:]([^/]+)/([^/\.]+)'
        match = re.search(github_pattern, url)
        if match:
            owner = match.group(1)
            repo = match.group(2)
            
            # Verify owner is allowed
            if owner.lower() != self.ALLOWED_OWNER.lower():
                violation_msg = f"BLOCKED: Repository owner '{owner}' is not allowed. Only '{self.ALLOWED_OWNER}' is permitted: {url}"
                self._log_violation(violation_msg, url)
                return False, violation_msg
            
            # Check if repository is in whitelist
            full_repo = f"{owner}/{repo}"
            if self.whitelist['allowed_repositories']:
                if full_repo not in self.whitelist['allowed_repositories']:
                    violation_msg = f"BLOCKED: Repository '{full_repo}' not in whitelist"
                    self._log_violation(violation_msg, url)
                    return False, violation_msg
            
            # Enhanced security: Verify repository checksum if available
            if self.enhanced_security:
                try:
                    # Calculate repository identifier checksum
                    repo_checksum = hashlib.sha256(full_repo.encode()).hexdigest()
                    if not self.enhanced_security.validate_repository_checksum(full_repo, repo_checksum):
                        violation_msg = f"BLOCKED: Repository checksum validation failed for '{full_repo}'"
                        self._log_violation(violation_msg, url)
                        return False, violation_msg
                except Exception as e:
                    self.audit_logger.warning(f"Could not verify repository checksum: {e}")
            
            self.audit_logger.info(f"ALLOWED: Repository '{full_repo}' passed all security checks")
            return True, f"Repository '{full_repo}' is allowed"
        
        # Non-GitHub URLs are blocked by default
        violation_msg = f"BLOCKED: Non-GitHub URL or unrecognized format: {url}"
        self._log_violation(violation_msg, url)
        return False, violation_msg
    
    def _log_violation(self, violation_msg: str, url: str):
        """Log security violation with enhanced tracking"""
        self.violations_logger.warning(violation_msg)
        self.audit_logger.warning(violation_msg)
        
        # Enhanced security logging
        if self.enhanced_security:
            self.enhanced_security.log_security_event(
                'repository_access_violation',
                'critical',
                details={'message': violation_msg, 'url': url}
            )
    
    def validate_directory_path(self, path: str) -> Tuple[bool, str]:
        """
        Validate a local directory path doesn't contain ZKP2P repositories.
        
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        self.audit_logger.info(f"Validating directory path: {path}")
        
        # Check if path contains forbidden strings
        for org in self.FORBIDDEN_ORGS:
            if org.lower() in path.lower():
                violation_msg = f"BLOCKED: Path contains forbidden organization '{org}': {path}"
                self.violations_logger.warning(violation_msg)
                self.audit_logger.warning(violation_msg)
                return False, violation_msg
        
        # Check for .git directory and validate remote
        git_dir = Path(path) / '.git'
        if git_dir.exists():
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'remote', 'get-url', 'origin'],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    remote_url = result.stdout.strip()
                    is_valid, reason = self.validate_repository_url(remote_url)
                    if not is_valid:
                        return False, f"Git remote validation failed: {reason}"
            except Exception as e:
                self.audit_logger.warning(f"Could not validate git remote for {path}: {e}")
        
        self.audit_logger.info(f"ALLOWED: Directory path '{path}' passed security checks")
        return True, f"Directory path '{path}' is allowed"
    
    def validate_operation(self, operation: str, target: str) -> bool:
        """
        Validate an operation before execution.
        Raises SecurityViolationError if operation is not allowed.
        """
        self.audit_logger.info(f"Validating operation: {operation} on {target}")
        
        # Determine if target is URL or path
        if target.startswith('http') or 'github.com' in target or '@' in target:
            is_valid, reason = self.validate_repository_url(target)
        else:
            is_valid, reason = self.validate_directory_path(target)
        
        if not is_valid:
            self.audit_logger.error(f"Operation '{operation}' BLOCKED: {reason}")
            raise SecurityViolationError(f"Security violation: {reason}")
        
        self.audit_logger.info(f"Operation '{operation}' on '{target}' APPROVED")
        return True
    
    def get_audit_summary(self) -> Dict:
        """Get a summary of security audit events"""
        summary = {
            'total_validations': 0,
            'blocked_attempts': 0,
            'allowed_operations': 0,
            'recent_violations': []
        }
        
        if self.audit_log_path.exists():
            with open(self.audit_log_path, 'r') as f:
                lines = f.readlines()
                summary['total_validations'] = len([l for l in lines if 'Validating' in l])
                summary['blocked_attempts'] = len([l for l in lines if 'BLOCKED' in l])
                summary['allowed_operations'] = len([l for l in lines if 'ALLOWED' in l])
        
        if self.violations_log_path.exists():
            with open(self.violations_log_path, 'r') as f:
                lines = f.readlines()
                summary['recent_violations'] = lines[-10:] if lines else []
        
        return summary


def create_safe_git_wrapper():
    """
    Create a safe wrapper for git operations that validates all repository interactions.
    """
    import subprocess
    from functools import wraps
    
    guard = RepositorySecurityGuard()
    
    class SafeGit:
        """Wrapper class for safe git operations"""
        
        @staticmethod
        def validate_before_execute(func):
            """Decorator to validate git operations before execution"""
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract URL or path from arguments
                cmd = args[0] if args else []
                
                # Check for clone operations
                if 'clone' in cmd:
                    for i, arg in enumerate(cmd):
                        if 'github.com' in arg or arg.startswith('git@'):
                            guard.validate_operation('git clone', arg)
                
                # Check for remote operations
                if 'remote' in cmd and ('add' in cmd or 'set-url' in cmd):
                    for i, arg in enumerate(cmd):
                        if 'github.com' in arg or arg.startswith('git@'):
                            guard.validate_operation('git remote', arg)
                
                # Check for push/pull operations
                if 'push' in cmd or 'pull' in cmd or 'fetch' in cmd:
                    # Get current directory's remote
                    cwd = kwargs.get('cwd', os.getcwd())
                    guard.validate_directory_path(cwd)
                
                return func(*args, **kwargs)
            return wrapper
        
        @staticmethod
        @validate_before_execute
        def run(cmd: List[str], **kwargs):
            """Execute a git command with security validation"""
            return subprocess.run(cmd, **kwargs)
    
    return SafeGit()


# Create singleton instance for import
security_guard = RepositorySecurityGuard()
safe_git = create_safe_git_wrapper()


if __name__ == "__main__":
    # Test the security guard
    guard = RepositorySecurityGuard()
    
    test_urls = [
        "https://github.com/ADWilkinson/davy-jones-intern",  # Should pass
        "https://github.com/zkp2p/zkp2p-v2-contracts",  # Should fail
        "https://github.com/ZKP2P/some-repo",  # Should fail
        "git@github.com:ADWilkinson/barbossa-engineer.git",  # Should pass
        "https://github.com/some-other-user/repo",  # Should fail
    ]
    
    print("Security Guard Test Results:")
    print("-" * 50)
    for url in test_urls:
        is_valid, reason = guard.validate_repository_url(url)
        status = "✓ PASS" if is_valid else "✗ FAIL"
        print(f"{status}: {url}")
        print(f"  Reason: {reason}")
    
    print("\nAudit Summary:")
    print(json.dumps(guard.get_audit_summary(), indent=2))