#!/usr/bin/env python3
"""
Security Test Suite for Barbossa
Validates that all security guards are functioning correctly
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from security_guard import RepositorySecurityGuard, SecurityViolationError


class TestSecurityGuard(unittest.TestCase):
    """Test cases for the security guard system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.guard = RepositorySecurityGuard()
    
    def test_zkp2p_urls_blocked(self):
        """Test that all ZKP2P organization URLs are blocked"""
        forbidden_urls = [
            "https://github.com/zkp2p/zkp2p-v2-contracts",
            "https://github.com/ZKP2P/some-repo",
            "git@github.com:zkp2p/anything.git",
            "https://github.com/zkp2p-org/project",
            "https://github.com/ZKP2P-protocol/contracts",
            "git@github.com:ZKP2P/test.git",
            "https://github.com/zkp2p/zkp2p-v2-client",
        ]
        
        for url in forbidden_urls:
            with self.subTest(url=url):
                is_valid, reason = self.guard.validate_repository_url(url)
                self.assertFalse(is_valid, f"URL should be blocked: {url}")
                self.assertIn("BLOCKED", reason)
    
    def test_adwilkinson_urls_allowed(self):
        """Test that ADWilkinson repository URLs are allowed"""
        allowed_urls = [
            "https://github.com/ADWilkinson/barbossa-engineer",
            "https://github.com/ADWilkinson/davy-jones-intern",
            "git@github.com:ADWilkinson/_save.git",
            "https://github.com/ADWilkinson/chordcraft-app",
            "https://github.com/ADWilkinson/piggyonchain",
            "https://github.com/ADWilkinson/persona-website",
            "https://github.com/ADWilkinson/saylor-memes",
            "https://github.com/ADWilkinson/the-flying-dutchman-theme",
        ]
        
        for url in allowed_urls:
            with self.subTest(url=url):
                is_valid, reason = self.guard.validate_repository_url(url)
                self.assertTrue(is_valid, f"URL should be allowed: {url}")
                self.assertIn("allowed", reason.lower())
    
    def test_other_users_blocked(self):
        """Test that non-ADWilkinson users are blocked"""
        blocked_urls = [
            "https://github.com/someuser/repo",
            "https://github.com/microsoft/vscode",
            "git@github.com:facebook/react.git",
            "https://github.com/torvalds/linux",
        ]
        
        for url in blocked_urls:
            with self.subTest(url=url):
                is_valid, reason = self.guard.validate_repository_url(url)
                self.assertFalse(is_valid, f"URL should be blocked: {url}")
                self.assertIn("not allowed", reason)
    
    def test_case_insensitive_blocking(self):
        """Test that blocking is case-insensitive"""
        variations = [
            "https://github.com/ZkP2p/repo",
            "https://github.com/zKp2P/repo",
            "https://github.com/ZKP2P/repo",
            "https://github.com/zkP2P/repo",
        ]
        
        for url in variations:
            with self.subTest(url=url):
                is_valid, reason = self.guard.validate_repository_url(url)
                self.assertFalse(is_valid, f"URL should be blocked: {url}")
    
    def test_directory_path_validation(self):
        """Test directory path validation"""
        # Test paths with forbidden strings
        forbidden_paths = [
            "/home/user/zkp2p/project",
            "/var/www/ZKP2P-app",
            "/projects/zkp2p-contracts",
        ]
        
        for path in forbidden_paths:
            with self.subTest(path=path):
                is_valid, reason = self.guard.validate_directory_path(path)
                self.assertFalse(is_valid, f"Path should be blocked: {path}")
                self.assertIn("BLOCKED", reason)
        
        # Test allowed paths
        allowed_paths = [
            "/home/user/barbossa-engineer",
            "/projects/davy-jones-intern",
            "/var/www/personal-site",
        ]
        
        for path in allowed_paths:
            with self.subTest(path=path):
                is_valid, reason = self.guard.validate_directory_path(path)
                self.assertTrue(is_valid, f"Path should be allowed: {path}")
    
    def test_validate_operation_raises_exception(self):
        """Test that validate_operation raises SecurityViolationError for forbidden repos"""
        forbidden_url = "https://github.com/zkp2p/contracts"
        
        with self.assertRaises(SecurityViolationError) as context:
            self.guard.validate_operation("git clone", forbidden_url)
        
        self.assertIn("Security violation", str(context.exception))
    
    def test_audit_logging(self):
        """Test that security events are properly logged"""
        # Trigger some validations
        self.guard.validate_repository_url("https://github.com/ADWilkinson/test")
        self.guard.validate_repository_url("https://github.com/zkp2p/forbidden")
        
        # Check audit summary
        summary = self.guard.get_audit_summary()
        
        self.assertGreater(summary['total_validations'], 0)
        self.assertGreater(summary['blocked_attempts'], 0)
        self.assertGreater(summary['allowed_operations'], 0)
    
    def test_whitelist_enforcement(self):
        """Test that whitelist is properly enforced"""
        # Create a guard with a custom whitelist
        config_path = Path(__file__).parent.parent / 'config' / 'repository_whitelist.json'
        guard = RepositorySecurityGuard(config_path)
        
        # Test that only whitelisted repos are allowed
        whitelisted = "https://github.com/ADWilkinson/barbossa-engineer"
        is_valid, _ = guard.validate_repository_url(whitelisted)
        self.assertTrue(is_valid)
        
        # Test that ADWilkinson repos not in whitelist are still validated
        # (depends on whitelist configuration)
        non_whitelisted = "https://github.com/ADWilkinson/some-new-repo"
        is_valid, reason = guard.validate_repository_url(non_whitelisted)
        # This should be blocked if whitelist is enforced strictly
        if guard.whitelist['allowed_repositories']:
            self.assertFalse(is_valid)
    
    def test_pattern_matching(self):
        """Test that all forbidden patterns are matched correctly"""
        test_cases = [
            ("https://github.com/zkp2p-something/repo", False),
            ("git@github.com:ZKP2P-org/test.git", False),
            ("https://github.com/user/zkp2p-fork", False),  # Contains zkp2p
            ("https://github.com/ADWilkinson/zk-proofs", True),  # zk alone is OK
        ]
        
        for url, should_be_valid in test_cases:
            with self.subTest(url=url):
                is_valid, _ = self.guard.validate_repository_url(url)
                self.assertEqual(is_valid, should_be_valid, 
                               f"URL validation mismatch for: {url}")


class TestBarbossaSecurity(unittest.TestCase):
    """Test Barbossa's integration with security guards"""
    
    def setUp(self):
        """Set up test fixtures"""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from barbossa import Barbossa
        self.barbossa = Barbossa()
    
    def test_barbossa_validates_repositories(self):
        """Test that Barbossa properly validates repository access"""
        # Test forbidden repository
        forbidden_url = "https://github.com/zkp2p/contracts"
        result = self.barbossa.validate_repository_access(forbidden_url)
        self.assertFalse(result)
        
        # Test allowed repository
        allowed_url = "https://github.com/ADWilkinson/barbossa-engineer"
        result = self.barbossa.validate_repository_access(allowed_url)
        self.assertTrue(result)
    
    def test_barbossa_blocks_zkp2p_in_personal_projects(self):
        """Test that Barbossa won't work on ZKP2P repos even if somehow in the list"""
        # Temporarily modify the work areas to include a forbidden repo
        original_repos = self.barbossa.WORK_AREAS['personal_projects']['repositories'].copy()
        
        try:
            # Add a forbidden repo to the list (simulating a configuration error)
            self.barbossa.WORK_AREAS['personal_projects']['repositories'].append(
                'zkp2p/forbidden-repo'
            )
            
            # The validation should still block it
            forbidden_url = "https://github.com/zkp2p/forbidden-repo"
            result = self.barbossa.validate_repository_access(forbidden_url)
            self.assertFalse(result)
            
        finally:
            # Restore original repos
            self.barbossa.WORK_AREAS['personal_projects']['repositories'] = original_repos
    
    def test_work_area_selection(self):
        """Test that work area selection favors less-worked areas"""
        # Set up a tally with uneven distribution
        test_tally = {
            'infrastructure': 5,
            'personal_projects': 1,
            'davy_jones': 3
        }
        
        # Run selection multiple times and check distribution
        selections = []
        for _ in range(100):
            selected = self.barbossa.select_work_area(test_tally.copy())
            selections.append(selected)
        
        # personal_projects should be selected most often (lowest count)
        personal_count = selections.count('personal_projects')
        self.assertGreater(personal_count, 30, 
                          "Low-count area should be selected more frequently")


class TestSecurityIntegration(unittest.TestCase):
    """Integration tests for the complete security system"""
    
    def test_end_to_end_security(self):
        """Test complete security flow from entry to execution"""
        from barbossa import Barbossa
        from security_guard import security_guard
        
        barbossa = Barbossa()
        
        # Test that security is active
        self.assertIsNotNone(security_guard)
        
        # Test that Barbossa status includes security info
        status = barbossa.get_status()
        self.assertIn('security_status', status)
        self.assertIn('BLOCKED', status['security_status'])
        
        # Test that audit system is working
        self.assertIn('security_audit', status)
    
    def test_security_violation_logging(self):
        """Test that security violations are properly logged"""
        from barbossa import Barbossa
        
        barbossa = Barbossa()
        
        # Attempt to access forbidden repository
        forbidden_url = "https://github.com/zkp2p/test"
        barbossa.validate_repository_access(forbidden_url)
        
        # Check that violation was logged
        violations_log = barbossa.changelogs_dir / 'security_violations.log'
        if violations_log.exists():
            with open(violations_log, 'r') as f:
                content = f.read()
                self.assertIn('VIOLATION', content)
                self.assertIn('zkp2p', content.lower())


def run_security_tests():
    """Run all security tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityGuard))
    suite.addTests(loader.loadTestsFromTestCase(TestBarbossaSecurity))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("SECURITY TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL SECURITY TESTS PASSED")
        print("ZKP2P organization access is properly BLOCKED")
    else:
        print("\n❌ SECURITY TESTS FAILED")
        print("WARNING: Security system may not be functioning correctly!")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_security_tests()
    sys.exit(0 if success else 1)