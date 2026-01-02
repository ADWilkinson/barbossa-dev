#!/usr/bin/env python3
"""
Barbossa Auditor v1.2.0 - Self-Improving System Audit Agent
Runs daily at 06:30 to analyze logs, PR outcomes, and system health.
Identifies patterns, issues, and opportunities for improvement.
Enhanced with code bloat detection and architecture consistency checks.

Part of the Barbossa Pipeline:
- Product Manager (3x daily) → creates feature specs
- Discovery (4x daily) → creates Issues
- Engineer (:00) → implements from backlog, creates PRs
- Tech Lead (:35) → reviews PRs, merges or requests changes
- Auditor (daily 06:30) → system health analysis

Prompts loaded locally from prompts/ directory.
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import re
import uuid

# Local prompt loading and optional analytics/state tracking
from barbossa.utils.prompts import get_system_prompt
from barbossa.agents.firebase import (
    get_client,
    check_version,
    track_run_start,
    track_run_end
)
from barbossa.utils.issue_tracker import get_issue_tracker, IssueTracker
from barbossa.utils.notifications import (
    notify_agent_run_complete,
    notify_error,
    wait_for_pending
)
from barbossa.utils.log_rotation import LogRotationManager


class BarbossaAuditor:
    """
    Self-improving audit agent that analyzes system performance
    and identifies opportunities for optimization.
    """

    VERSION = "1.7.3"  # Fix: wait for webhook notifications + Feature: enhanced log rotation
    ROLE = "auditor"

    def __init__(self, work_dir: Optional[Path] = None):
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-dev'
        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.config_file = self.work_dir / 'config' / 'repositories.json'
        self.audit_history_file = self.work_dir / 'audit_history.json'
        self.insights_file = self.work_dir / 'system_insights.json'

        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self._setup_logging()

        # Firebase client (analytics + state tracking, never blocks)
        self.firebase = get_client()

        # Soft version check - warn but never block
        update_msg = check_version()
        if update_msg:
            self.logger.info(f"UPDATE AVAILABLE: {update_msg}")

        self.config = self._load_config()
        self.repositories = self.config.get('repositories', [])
        self.owner = self.config.get('owner')
        if not self.owner:
            raise ValueError("'owner' is required in config/repositories.json")

        self.logger.info("=" * 70)
        self.logger.info(f"BARBOSSA AUDITOR v{self.VERSION}")
        self.logger.info("Role: System Health & Self-Improvement")
        self.logger.info(f"Repositories: {len(self.repositories)}")
        self.logger.info("=" * 70)

    def _setup_logging(self):
        """Configure logging"""
        log_file = self.logs_dir / f"auditor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger('auditor')
        self.logger.info(f"Logging to: {log_file}")

    def _load_config(self) -> Dict:
        """Load repository configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        self.logger.error(f"Config file not found: {self.config_file}")
        return {'repositories': []}

    def _load_audit_history(self) -> List[Dict]:
        """Load previous audit results"""
        if self.audit_history_file.exists():
            try:
                with open(self.audit_history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_audit_history(self, audit: Dict):
        """Save audit to history"""
        history = self._load_audit_history()
        history.insert(0, audit)
        history = history[:30]  # Keep last 30 audits

        with open(self.audit_history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def _save_insights(self, insights: Dict):
        """Save system insights for other agents to read"""
        with open(self.insights_file, 'w') as f:
            json.dump(insights, f, indent=2)

    # =========================================================================
    # PR ANALYSIS
    # =========================================================================

    def _get_pr_stats(self, repo_name: str, days: int = 7) -> Dict:
        """Get PR statistics for a repository"""
        try:
            # Get all PRs from the last N days
            result = subprocess.run(
                f"gh pr list --repo {self.owner}/{repo_name} --state all --limit 100 "
                f"--json number,title,state,createdAt,closedAt,mergedAt,headRefName,additions,deletions,changedFiles",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                return {}

            prs = json.loads(result.stdout) if result.stdout.strip() else []

            # Filter to barbossa PRs and recent timeframe
            cutoff = datetime.now() - timedelta(days=days)
            barbossa_prs = []

            for pr in prs:
                if not pr.get('headRefName', '').startswith('barbossa/'):
                    continue

                created_str = pr.get('createdAt', '')
                try:
                    created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    if created.replace(tzinfo=None) >= cutoff:
                        barbossa_prs.append(pr)
                except:
                    pass

            # Calculate stats
            total = len(barbossa_prs)
            merged = sum(1 for p in barbossa_prs if p.get('mergedAt'))
            closed = sum(1 for p in barbossa_prs if p.get('state') == 'CLOSED' and not p.get('mergedAt'))
            open_prs = sum(1 for p in barbossa_prs if p.get('state') == 'OPEN')

            # Analyze PR types
            pr_types = defaultdict(int)
            for pr in barbossa_prs:
                title = pr.get('title', '')
                if title.startswith('test:'):
                    pr_types['test'] += 1
                elif title.startswith('feat:'):
                    pr_types['feature'] += 1
                elif title.startswith('fix:'):
                    pr_types['fix'] += 1
                elif title.startswith('refactor:'):
                    pr_types['refactor'] += 1
                elif title.startswith('a11y:'):
                    pr_types['accessibility'] += 1
                elif title.startswith('perf:'):
                    pr_types['performance'] += 1
                else:
                    pr_types['other'] += 1

            # Get closed PR titles for pattern analysis
            closed_titles = [p.get('title', '') for p in barbossa_prs if p.get('state') == 'CLOSED' and not p.get('mergedAt')]

            return {
                'total': total,
                'merged': merged,
                'closed': closed,
                'open': open_prs,
                'merge_rate': round(merged / total * 100, 1) if total > 0 else 0,
                'close_rate': round(closed / total * 100, 1) if total > 0 else 0,
                'pr_types': dict(pr_types),
                'closed_titles': closed_titles,
                'avg_additions': round(sum(p.get('additions', 0) for p in barbossa_prs) / total, 1) if total > 0 else 0,
                'avg_deletions': round(sum(p.get('deletions', 0) for p in barbossa_prs) / total, 1) if total > 0 else 0,
            }

        except Exception as e:
            self.logger.error(f"Error getting PR stats for {repo_name}: {e}")
            return {}

    # =========================================================================
    # LOG ANALYSIS
    # =========================================================================

    def _analyze_logs(self, days: int = 7) -> Dict:
        """Analyze recent logs for errors and patterns"""
        cutoff = datetime.now() - timedelta(days=days)

        errors = []
        warnings = []
        timeouts = 0
        parse_failures = 0
        successful_sessions = 0
        failed_sessions = 0

        # Analyze barbossa logs
        for log_file in self.logs_dir.glob("barbossa_*.log"):
            try:
                # Check if file is recent
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    continue

                content = log_file.read_text()

                # Count errors and warnings
                for line in content.split('\n'):
                    if '- ERROR -' in line:
                        errors.append(line)
                    elif '- WARNING -' in line:
                        warnings.append(line)

                    if 'timeout' in line.lower():
                        timeouts += 1
                    if 'could not parse' in line.lower():
                        parse_failures += 1

                # Check session outcome
                if 'PR created successfully' in content or 'Successfully' in content:
                    successful_sessions += 1
                elif 'error' in content.lower() or 'failed' in content.lower():
                    failed_sessions += 1

            except Exception as e:
                self.logger.warning(f"Could not analyze {log_file}: {e}")

        # Analyze tech lead logs
        tech_lead_merges = 0
        tech_lead_closes = 0
        tech_lead_changes = 0

        for log_file in self.logs_dir.glob("tech_lead_*.log"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    continue

                content = log_file.read_text()

                tech_lead_merges += content.count('DECISION: MERGE')
                tech_lead_closes += content.count('DECISION: CLOSE')
                tech_lead_changes += content.count('DECISION: REQUEST_CHANGES')

                for line in content.split('\n'):
                    if '- ERROR -' in line:
                        errors.append(line)

            except Exception as e:
                self.logger.warning(f"Could not analyze {log_file}: {e}")

        return {
            'error_count': len(errors),
            'warning_count': len(warnings),
            'timeout_count': timeouts,
            'parse_failure_count': parse_failures,
            'successful_sessions': successful_sessions,
            'failed_sessions': failed_sessions,
            'tech_lead_merges': tech_lead_merges,
            'tech_lead_closes': tech_lead_closes,
            'tech_lead_changes': tech_lead_changes,
            'recent_errors': errors[-10:],  # Last 10 errors
        }

    # =========================================================================
    # TECH LEAD DECISION ANALYSIS
    # =========================================================================

    def _analyze_tech_lead_decisions(self) -> Dict:
        """Analyze Tech Lead decision patterns"""
        decisions_file = self.work_dir / 'tech_lead_decisions.json'

        if not decisions_file.exists():
            return {}

        try:
            with open(decisions_file, 'r') as f:
                decisions = json.load(f)
        except:
            return {}

        if not decisions:
            return {}

        # Analyze recent decisions (last 50)
        recent = decisions[:50]

        merge_count = sum(1 for d in recent if d.get('decision') == 'MERGE')
        close_count = sum(1 for d in recent if d.get('decision') == 'CLOSE')
        changes_count = sum(1 for d in recent if d.get('decision') == 'REQUEST_CHANGES')

        value_scores = [d.get('value_score', 5) for d in recent if d.get('value_score')]
        quality_scores = [d.get('quality_score', 5) for d in recent if d.get('quality_score')]

        # Find patterns in closed PRs
        close_reasons = defaultdict(int)
        for d in recent:
            if d.get('decision') == 'CLOSE':
                reason = d.get('reasoning', '').lower()
                # Distinguish between "test-only PRs" (closed for being only tests) vs "missing tests"
                if 'test-only' in reason or 'only test' in reason or 'only add test' in reason:
                    close_reasons['test_only'] += 1
                elif 'missing test' in reason or 'no test' in reason:
                    close_reasons['missing_tests'] += 1
                elif 'conflict' in reason:
                    close_reasons['merge_conflicts'] += 1
                elif 'bloat' in reason or 'unnecessary' in reason:
                    close_reasons['bloat'] += 1
                elif 'stale' in reason:
                    close_reasons['stale'] += 1
                else:
                    close_reasons['other'] += 1

        return {
            'total_decisions': len(recent),
            'merge_count': merge_count,
            'close_count': close_count,
            'changes_count': changes_count,
            'merge_rate': round(merge_count / len(recent) * 100, 1) if recent else 0,
            'avg_value_score': round(sum(value_scores) / len(value_scores), 1) if value_scores else 0,
            'avg_quality_score': round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0,
            'close_reasons': dict(close_reasons),
        }

    # =========================================================================
    # QUALITY ASSURANCE CHECKS
    # =========================================================================

    def _analyze_test_coverage(self, repo_name: str) -> Dict:
        """Analyze test coverage from recent PRs"""
        result = {
            'has_coverage': False,
            'coverage_percentage': 0,
            'trend': 'unknown',
            'uncovered_critical_files': [],
            'status': 'unknown'
        }

        try:
            # Check if repo has coverage reports
            repo_path = Path.home() / 'projects' / repo_name
            if not repo_path.exists():
                # Try alternate path for monorepo
                for monorepo in ['zkp2p', 'davy-jones-intern']:
                    alt_path = Path.home() / 'projects' / monorepo / repo_name
                    if alt_path.exists():
                        repo_path = alt_path
                        break

            if not repo_path.exists():
                result['status'] = 'repo_not_found'
                return result

            # Check for coverage config
            coverage_configs = ['vitest.config.ts', 'jest.config.js', 'playwright.config.ts']
            has_coverage_config = any((repo_path / cfg).exists() for cfg in coverage_configs)

            if not has_coverage_config:
                result['status'] = 'no_coverage_config'
                return result

            # Try to find recent coverage reports
            coverage_dirs = [
                repo_path / 'coverage',
                repo_path / '.coverage',
                repo_path / 'coverage-report'
            ]

            coverage_dir = None
            for cdir in coverage_dirs:
                if cdir.exists():
                    coverage_dir = cdir
                    break

            if not coverage_dir:
                result['status'] = 'no_recent_coverage'
                return result

            # Parse coverage summary if it exists
            summary_files = [
                coverage_dir / 'coverage-summary.json',
                coverage_dir / 'coverage-final.json',
                coverage_dir / 'lcov-report' / 'index.html'
            ]

            for summary_file in summary_files:
                if summary_file.exists() and summary_file.suffix == '.json':
                    try:
                        with open(summary_file, 'r') as f:
                            coverage_data = json.load(f)

                        # Extract total coverage percentage
                        if 'total' in coverage_data:
                            total = coverage_data['total']
                            if 'lines' in total and 'pct' in total['lines']:
                                result['coverage_percentage'] = total['lines']['pct']
                                result['has_coverage'] = True

                                # Determine status
                                if result['coverage_percentage'] >= 80:
                                    result['status'] = 'excellent'
                                elif result['coverage_percentage'] >= 70:
                                    result['status'] = 'good'
                                elif result['coverage_percentage'] >= 60:
                                    result['status'] = 'fair'
                                else:
                                    result['status'] = 'poor'

                        # Find uncovered critical files
                        critical_patterns = ['api', 'service', 'controller', 'store', 'context', 'hook']
                        for file_path, file_data in coverage_data.items():
                            if file_path == 'total':
                                continue
                            if isinstance(file_data, dict) and 'lines' in file_data:
                                coverage_pct = file_data['lines'].get('pct', 100)
                                # Check if this is a critical file
                                if coverage_pct < 50 and any(pattern in file_path.lower() for pattern in critical_patterns):
                                    result['uncovered_critical_files'].append({
                                        'file': file_path,
                                        'coverage': coverage_pct
                                    })

                        break
                    except Exception as e:
                        self.logger.warning(f"Could not parse coverage file {summary_file}: {e}")

            if not result['has_coverage']:
                result['status'] = 'no_parseable_coverage'

        except Exception as e:
            self.logger.error(f"Error analyzing coverage for {repo_name}: {e}")
            result['status'] = 'error'

        return result

    def _detect_integration_tests(self, repo_name: str) -> Dict:
        """Detect presence and health of integration tests"""
        result = {
            'has_integration_tests': False,
            'integration_test_count': 0,
            'integration_test_files': [],
            'has_api_integration_tests': False,
            'has_db_integration_tests': False,
            'status': 'none'
        }

        try:
            repo_path = Path.home() / 'projects' / repo_name
            if not repo_path.exists():
                for monorepo in ['zkp2p', 'davy-jones-intern']:
                    alt_path = Path.home() / 'projects' / monorepo / repo_name
                    if alt_path.exists():
                        repo_path = alt_path
                        break

            if not repo_path.exists():
                return result

            # Search for integration test files
            integration_patterns = [
                '*.integration.test.ts',
                '*.integration.test.js',
                '*.integration.spec.ts',
                '*.e2e.test.ts',
                '**/integration/**/*.test.ts',
                '**/integration/**/*.spec.ts'
            ]

            for pattern in integration_patterns:
                for test_file in repo_path.rglob(pattern):
                    if 'node_modules' not in str(test_file):
                        result['integration_test_files'].append(str(test_file.relative_to(repo_path)))
                        result['integration_test_count'] += 1

            result['has_integration_tests'] = result['integration_test_count'] > 0

            # Check for specific integration test types
            for test_file in result['integration_test_files']:
                content_path = repo_path / test_file
                try:
                    content = content_path.read_text()
                    if 'api' in content.lower() or 'endpoint' in content.lower() or 'request' in content.lower():
                        result['has_api_integration_tests'] = True
                    if 'database' in content.lower() or 'prisma' in content.lower() or 'migrate' in content.lower():
                        result['has_db_integration_tests'] = True
                except:
                    pass

            # Determine status
            if result['integration_test_count'] >= 10:
                result['status'] = 'excellent'
            elif result['integration_test_count'] >= 5:
                result['status'] = 'good'
            elif result['integration_test_count'] >= 1:
                result['status'] = 'minimal'
            else:
                result['status'] = 'none'

        except Exception as e:
            self.logger.error(f"Error detecting integration tests for {repo_name}: {e}")
            result['status'] = 'error'

        return result

    def _analyze_e2e_test_health(self, repo_name: str) -> Dict:
        """Analyze E2E test health (Playwright, Cypress, etc.)"""
        result = {
            'has_e2e_tests': False,
            'e2e_test_count': 0,
            'e2e_framework': None,
            'critical_flows_covered': [],
            'status': 'none'
        }

        try:
            repo_path = Path.home() / 'projects' / repo_name
            if not repo_path.exists():
                for monorepo in ['zkp2p', 'davy-jones-intern']:
                    alt_path = Path.home() / 'projects' / monorepo / repo_name
                    if alt_path.exists():
                        repo_path = alt_path
                        break

            if not repo_path.exists():
                return result

            # Detect E2E framework
            if (repo_path / 'playwright.config.ts').exists() or (repo_path / 'playwright.config.js').exists():
                result['e2e_framework'] = 'playwright'
            elif (repo_path / 'cypress.config.ts').exists() or (repo_path / 'cypress.json').exists():
                result['e2e_framework'] = 'cypress'

            if not result['e2e_framework']:
                result['status'] = 'no_framework'
                return result

            # Find E2E test files
            e2e_patterns = [
                'e2e/**/*.spec.ts',
                'e2e/**/*.test.ts',
                'tests/e2e/**/*.spec.ts',
                'cypress/e2e/**/*.cy.ts',
                'playwright/**/*.spec.ts'
            ]

            e2e_files = []
            for pattern in e2e_patterns:
                for test_file in repo_path.glob(pattern):
                    if 'node_modules' not in str(test_file):
                        e2e_files.append(test_file)
                        result['e2e_test_count'] += 1

            result['has_e2e_tests'] = result['e2e_test_count'] > 0

            # Check for critical user flow coverage
            critical_flows = ['login', 'signup', 'checkout', 'payment', 'deposit', 'withdraw', 'create', 'delete']
            for test_file in e2e_files:
                try:
                    content = test_file.read_text().lower()
                    for flow in critical_flows:
                        if flow in content and flow not in result['critical_flows_covered']:
                            result['critical_flows_covered'].append(flow)
                except:
                    pass

            # Determine status
            if result['e2e_test_count'] >= 10 and len(result['critical_flows_covered']) >= 3:
                result['status'] = 'excellent'
            elif result['e2e_test_count'] >= 5 and len(result['critical_flows_covered']) >= 2:
                result['status'] = 'good'
            elif result['e2e_test_count'] >= 1:
                result['status'] = 'minimal'
            else:
                result['status'] = 'none'

        except Exception as e:
            self.logger.error(f"Error analyzing E2E tests for {repo_name}: {e}")
            result['status'] = 'error'

        return result

    def _detect_code_bloat_patterns(self, repo_name: str, days: int = 7) -> Dict:
        """Detect code bloat, duplication, and unnecessary complexity"""
        result = {
            'duplicate_utility_functions': 0,
            'large_files': [],
            'complex_files': [],
            'bloat_score': 0,
            'status': 'healthy'
        }

        try:
            repo_path = Path.home() / 'projects' / repo_name
            if not repo_path.exists():
                for monorepo in ['zkp2p', 'davy-jones-intern']:
                    alt_path = Path.home() / 'projects' / monorepo / repo_name
                    if alt_path.exists():
                        repo_path = alt_path
                        break

            if not repo_path.exists():
                return result

            # Find large files that might indicate bloat
            src_patterns = ['src/**/*.ts', 'src/**/*.tsx', 'src/**/*.js', 'src/**/*.jsx']
            large_file_threshold = 500  # lines

            for pattern in src_patterns:
                for file_path in repo_path.glob(pattern):
                    if 'node_modules' in str(file_path) or '.test.' in str(file_path):
                        continue

                    try:
                        lines = file_path.read_text().split('\n')
                        line_count = len([l for l in lines if l.strip() and not l.strip().startswith('//')])

                        if line_count > large_file_threshold:
                            result['large_files'].append({
                                'file': str(file_path.relative_to(repo_path)),
                                'lines': line_count
                            })
                            result['bloat_score'] += 1

                        # Check for high complexity (deeply nested code)
                        max_indent = 0
                        for line in lines:
                            if line.strip():
                                indent = len(line) - len(line.lstrip())
                                max_indent = max(max_indent, indent // 2)

                        if max_indent > 6:  # More than 6 levels of nesting
                            result['complex_files'].append({
                                'file': str(file_path.relative_to(repo_path)),
                                'max_nesting': max_indent
                            })
                            result['bloat_score'] += 2

                    except Exception as e:
                        pass

            # Check for duplicate utility patterns (simple heuristic)
            utility_patterns = ['utils', 'helpers', 'lib', 'common']
            utility_dirs = []
            for pattern in utility_patterns:
                utility_dirs.extend(list(repo_path.rglob(pattern)))

            if len(utility_dirs) > 3:
                result['duplicate_utility_functions'] = len(utility_dirs) - 3
                result['bloat_score'] += len(utility_dirs) - 3

            # Determine status
            if result['bloat_score'] >= 10:
                result['status'] = 'concerning'
            elif result['bloat_score'] >= 5:
                result['status'] = 'needs_attention'
            else:
                result['status'] = 'healthy'

        except Exception as e:
            self.logger.error(f"Error detecting code bloat for {repo_name}: {e}")
            result['status'] = 'error'

        return result

    def _analyze_architecture_consistency(self, repo_name: str, days: int = 7) -> Dict:
        """Analyze architecture consistency across the codebase"""
        result = {
            'has_consistent_structure': True,
            'pattern_violations': [],
            'missing_patterns': [],
            'status': 'healthy'
        }

        try:
            repo_path = Path.home() / 'projects' / repo_name
            if not repo_path.exists():
                for monorepo in ['zkp2p', 'davy-jones-intern']:
                    alt_path = Path.home() / 'projects' / monorepo / repo_name
                    if alt_path.exists():
                        repo_path = alt_path
                        break

            if not repo_path.exists():
                return result

            # Check for common architectural patterns
            expected_patterns = {
                'src': 'Source directory',
                'src/components': 'React components (for React apps)',
                'src/pages': 'Page components (for Next.js/React Router)',
                'src/services': 'Business logic/API services',
                'src/utils': 'Utility functions',
                'tests': 'Test directory',
            }

            # Detect if this is a React/Next.js app
            is_react_app = (repo_path / 'package.json').exists()
            if is_react_app:
                try:
                    pkg_json = json.loads((repo_path / 'package.json').read_text())
                    deps = {**pkg_json.get('dependencies', {}), **pkg_json.get('devDependencies', {})}
                    is_react_app = 'react' in deps or 'next' in deps
                except:
                    is_react_app = False

            # Check for pattern consistency
            if is_react_app:
                # Check for mixed patterns (bad)
                has_pages = (repo_path / 'src' / 'pages').exists() or (repo_path / 'pages').exists()
                has_app_router = (repo_path / 'app').exists()  # Next.js app router

                if has_pages and has_app_router:
                    result['pattern_violations'].append('Mixed Next.js routing patterns (both pages/ and app/ exist)')

                # Check for components organization
                components_dir = repo_path / 'src' / 'components'
                if components_dir.exists():
                    # Count component files
                    component_files = list(components_dir.rglob('*.tsx')) + list(components_dir.rglob('*.jsx'))
                    if len(component_files) > 30:
                        # Check if components are organized in subdirectories
                        flat_components = [f for f in component_files if f.parent == components_dir]
                        if len(flat_components) > 15:
                            result['pattern_violations'].append(f'{len(flat_components)} components in flat structure - should organize into subdirectories')

            # Check for missing common directories
            src_dir = repo_path / 'src'
            if src_dir.exists():
                if not (src_dir / 'utils').exists() and not (repo_path / 'lib').exists():
                    result['missing_patterns'].append('No utils/ or lib/ directory for shared utilities')

                if is_react_app and not (src_dir / 'components').exists() and not (repo_path / 'components').exists():
                    result['missing_patterns'].append('No components/ directory for React app')

            # Determine status
            violation_count = len(result['pattern_violations'])
            missing_count = len(result['missing_patterns'])

            if violation_count >= 3 or missing_count >= 3:
                result['status'] = 'concerning'
                result['has_consistent_structure'] = False
            elif violation_count >= 1 or missing_count >= 2:
                result['status'] = 'needs_attention'
            else:
                result['status'] = 'healthy'

        except Exception as e:
            self.logger.error(f"Error analyzing architecture for {repo_name}: {e}")
            result['status'] = 'error'

        return result

    def _assess_ui_changes(self, repo_name: str, days: int = 7) -> Dict:
        """Assess UI changes for frivolousness and proper testing"""
        result = {
            'ui_pr_count': 0,
            'style_only_pr_count': 0,
            'untested_ui_pr_count': 0,
            'ui_churn_files': [],
            'status': 'healthy'
        }

        try:
            # Get recent PRs
            cmd = f"gh pr list --repo {self.owner}/{repo_name} --state all --limit 50 " \
                  f"--json number,title,state,mergedAt,files"

            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            if proc.returncode != 0:
                return result

            prs = json.loads(proc.stdout) if proc.stdout.strip() else []

            # Filter to recent merged PRs
            cutoff = datetime.now() - timedelta(days=days)
            recent_prs = []

            for pr in prs:
                if pr.get('state') == 'MERGED' and pr.get('mergedAt'):
                    try:
                        merged_dt = datetime.fromisoformat(pr['mergedAt'].replace('Z', '+00:00'))
                        if merged_dt.replace(tzinfo=None) >= cutoff:
                            recent_prs.append(pr)
                    except:
                        pass

            # Analyze UI changes
            ui_file_patterns = ['.tsx', '.jsx', '.css', '.scss', '.styled.ts', '.styled.js']
            test_file_patterns = ['.test.', '.spec.', '.e2e.']

            ui_file_change_count = defaultdict(int)

            for pr in recent_prs:
                files = pr.get('files', [])
                if not files:
                    continue

                ui_files = [f for f in files if any(pattern in f.get('path', '') for pattern in ui_file_patterns)]
                test_files = [f for f in files if any(pattern in f.get('path', '') for pattern in test_file_patterns)]

                if ui_files:
                    result['ui_pr_count'] += 1

                    # Check if this is style-only (only CSS/SCSS changes)
                    style_only = all(any(ext in f.get('path', '') for ext in ['.css', '.scss']) for f in ui_files)
                    if style_only:
                        result['style_only_pr_count'] += 1

                    # Check if UI changes lack tests
                    if not test_files:
                        result['untested_ui_pr_count'] += 1

                    # Track UI file churn
                    for ui_file in ui_files:
                        path = ui_file.get('path', '')
                        if path:
                            ui_file_change_count[path] += 1

            # Identify high-churn UI files (changed in 3+ PRs)
            result['ui_churn_files'] = [
                {'file': path, 'change_count': count}
                for path, count in ui_file_change_count.items()
                if count >= 3
            ]

            # Determine status
            untested_ratio = result['untested_ui_pr_count'] / result['ui_pr_count'] if result['ui_pr_count'] > 0 else 0
            style_only_ratio = result['style_only_pr_count'] / result['ui_pr_count'] if result['ui_pr_count'] > 0 else 0

            if untested_ratio > 0.5 or style_only_ratio > 0.3:
                result['status'] = 'concerning'
            elif untested_ratio > 0.3 or len(result['ui_churn_files']) >= 5:
                result['status'] = 'needs_attention'
            else:
                result['status'] = 'healthy'

        except Exception as e:
            self.logger.error(f"Error assessing UI changes for {repo_name}: {e}")
            result['status'] = 'error'

        return result

    def _verify_cross_layer_integration(self, repo_name: str, days: int = 7) -> Dict:
        """Verify integration between frontend, backend, and contracts"""
        result = {
            'contract_changes_without_frontend': 0,
            'api_changes_without_client': 0,
            'breaking_changes_detected': 0,
            'orphaned_changes': [],
            'status': 'healthy'
        }

        try:
            # Get recent merged PRs with their files
            cmd = f"gh pr list --repo {self.owner}/{repo_name} --state merged --limit 30 " \
                  f"--json number,title,mergedAt,files"

            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            if proc.returncode != 0:
                return result

            prs = json.loads(proc.stdout) if proc.stdout.strip() else []

            # Filter to recent
            cutoff = datetime.now() - timedelta(days=days)
            recent_prs = []

            for pr in prs:
                if pr.get('mergedAt'):
                    try:
                        merged_dt = datetime.fromisoformat(pr['mergedAt'].replace('Z', '+00:00'))
                        if merged_dt.replace(tzinfo=None) >= cutoff:
                            recent_prs.append(pr)
                    except:
                        pass

            # Analyze cross-layer changes
            for pr in recent_prs:
                files = pr.get('files', [])
                if not files:
                    continue

                file_paths = [f.get('path', '') for f in files]

                # Check for contract changes without frontend updates
                has_contract_changes = any('contract' in p.lower() or '.sol' in p for p in file_paths)
                has_frontend_changes = any(
                    any(ext in p for ext in ['.tsx', '.jsx', '.ts', '.js'])
                    and 'src' in p
                    and 'contract' not in p.lower()
                    for p in file_paths
                )

                if has_contract_changes and not has_frontend_changes:
                    result['contract_changes_without_frontend'] += 1
                    result['orphaned_changes'].append({
                        'pr': pr['number'],
                        'title': pr['title'],
                        'type': 'contract_only'
                    })

                # Check for API changes without client updates
                has_api_changes = any(
                    'api' in p.lower() or 'controller' in p.lower() or 'route' in p.lower()
                    for p in file_paths
                )
                has_client_changes = any('client' in p.lower() or 'frontend' in p.lower() for p in file_paths)

                if has_api_changes and not has_client_changes and not has_frontend_changes:
                    result['api_changes_without_client'] += 1
                    result['orphaned_changes'].append({
                        'pr': pr['number'],
                        'title': pr['title'],
                        'type': 'api_only'
                    })

            # Determine status
            total_orphaned = len(result['orphaned_changes'])
            if total_orphaned >= 5:
                result['status'] = 'concerning'
            elif total_orphaned >= 3:
                result['status'] = 'needs_attention'
            else:
                result['status'] = 'healthy'

        except Exception as e:
            self.logger.error(f"Error verifying cross-layer integration for {repo_name}: {e}")
            result['status'] = 'error'

        return result

    # =========================================================================
    # PATTERN DETECTION
    # =========================================================================

    def _detect_patterns(self, pr_stats: Dict, log_analysis: Dict, decision_analysis: Dict, quality_stats: Dict = None) -> List[Dict]:
        """Detect SYSTEM and QUALITY patterns - mechanics + test coverage + integration"""
        patterns = []

        # ===== QUALITY PATTERNS (NEW) =====
        if quality_stats:
            for repo_name, qa in quality_stats.items():
                # Test coverage patterns
                coverage = qa.get('coverage', {})
                if coverage.get('status') == 'poor':
                    patterns.append({
                        'type': 'low_test_coverage',
                        'severity': 'high',
                        'repo': repo_name,
                        'value': coverage.get('coverage_percentage', 0),
                        'message': f"{repo_name}: Test coverage is {coverage.get('coverage_percentage', 0)}% - below acceptable threshold"
                    })
                elif coverage.get('status') == 'fair':
                    patterns.append({
                        'type': 'marginal_test_coverage',
                        'severity': 'medium',
                        'repo': repo_name,
                        'value': coverage.get('coverage_percentage', 0),
                        'message': f"{repo_name}: Test coverage is {coverage.get('coverage_percentage', 0)}% - should aim for 80%+"
                    })

                # Uncovered critical files
                uncovered = coverage.get('uncovered_critical_files', [])
                if len(uncovered) > 0:
                    patterns.append({
                        'type': 'uncovered_critical_files',
                        'severity': 'high',
                        'repo': repo_name,
                        'value': len(uncovered),
                        'message': f"{repo_name}: {len(uncovered)} critical files have <50% coverage (APIs, services, hooks)"
                    })

                # Integration test patterns
                integration = qa.get('integration_tests', {})
                if integration.get('status') == 'none':
                    patterns.append({
                        'type': 'no_integration_tests',
                        'severity': 'high',
                        'repo': repo_name,
                        'message': f"{repo_name}: No integration tests found - API/DB integration is untested"
                    })
                elif integration.get('status') == 'minimal':
                    patterns.append({
                        'type': 'minimal_integration_tests',
                        'severity': 'medium',
                        'repo': repo_name,
                        'value': integration.get('integration_test_count', 0),
                        'message': f"{repo_name}: Only {integration.get('integration_test_count', 0)} integration tests - need more coverage"
                    })

                # E2E test patterns
                e2e = qa.get('e2e_tests', {})
                if e2e.get('status') == 'no_framework':
                    patterns.append({
                        'type': 'no_e2e_framework',
                        'severity': 'medium',
                        'repo': repo_name,
                        'message': f"{repo_name}: No E2E testing framework (Playwright/Cypress) configured"
                    })
                elif e2e.get('status') == 'minimal':
                    flows = len(e2e.get('critical_flows_covered', []))
                    patterns.append({
                        'type': 'minimal_e2e_coverage',
                        'severity': 'medium',
                        'repo': repo_name,
                        'value': flows,
                        'message': f"{repo_name}: Only {flows} critical user flows covered by E2E tests"
                    })

                # UI change patterns
                ui = qa.get('ui_assessment', {})
                if ui.get('status') == 'concerning':
                    untested = ui.get('untested_ui_pr_count', 0)
                    style_only = ui.get('style_only_pr_count', 0)
                    patterns.append({
                        'type': 'problematic_ui_changes',
                        'severity': 'high',
                        'repo': repo_name,
                        'message': f"{repo_name}: {untested} untested UI PRs, {style_only} style-only PRs - UI quality is concerning"
                    })
                elif ui.get('status') == 'needs_attention':
                    patterns.append({
                        'type': 'ui_changes_need_attention',
                        'severity': 'medium',
                        'repo': repo_name,
                        'message': f"{repo_name}: UI changes need better test coverage and reduced churn"
                    })

                # UI churn patterns
                churn_files = ui.get('ui_churn_files', [])
                if len(churn_files) >= 3:
                    patterns.append({
                        'type': 'high_ui_churn',
                        'severity': 'medium',
                        'repo': repo_name,
                        'value': len(churn_files),
                        'message': f"{repo_name}: {len(churn_files)} UI files changed in 3+ PRs - indicates instability or frivolous changes"
                    })

                # Cross-layer integration patterns
                cross_layer = qa.get('cross_layer', {})
                if cross_layer.get('status') == 'concerning':
                    orphaned = len(cross_layer.get('orphaned_changes', []))
                    patterns.append({
                        'type': 'poor_cross_layer_integration',
                        'severity': 'high',
                        'repo': repo_name,
                        'value': orphaned,
                        'message': f"{repo_name}: {orphaned} orphaned changes (contract/API changes without frontend integration)"
                    })
                elif cross_layer.get('status') == 'needs_attention':
                    patterns.append({
                        'type': 'cross_layer_integration_gaps',
                        'severity': 'medium',
                        'repo': repo_name,
                        'message': f"{repo_name}: Some contract/API changes lack corresponding frontend integration"
                    })

                # Code bloat patterns (NEW)
                bloat = qa.get('code_bloat', {})
                if bloat.get('status') == 'concerning':
                    patterns.append({
                        'type': 'high_code_bloat',
                        'severity': 'high',
                        'repo': repo_name,
                        'value': bloat.get('bloat_score', 0),
                        'message': f"{repo_name}: High code bloat detected (score: {bloat.get('bloat_score', 0)}) - large files, deep nesting, duplicate utils"
                    })
                elif bloat.get('status') == 'needs_attention':
                    patterns.append({
                        'type': 'moderate_code_bloat',
                        'severity': 'medium',
                        'repo': repo_name,
                        'value': bloat.get('bloat_score', 0),
                        'message': f"{repo_name}: Moderate code bloat - review large files and complex functions"
                    })

                # Large file patterns
                if len(bloat.get('large_files', [])) > 5:
                    patterns.append({
                        'type': 'too_many_large_files',
                        'severity': 'medium',
                        'repo': repo_name,
                        'value': len(bloat.get('large_files', [])),
                        'message': f"{repo_name}: {len(bloat.get('large_files', []))} files >500 lines - consider refactoring into smaller modules"
                    })

                # Complex file patterns
                if len(bloat.get('complex_files', [])) > 3:
                    patterns.append({
                        'type': 'high_complexity_files',
                        'severity': 'high',
                        'repo': repo_name,
                        'value': len(bloat.get('complex_files', [])),
                        'message': f"{repo_name}: {len(bloat.get('complex_files', []))} files with deep nesting (>6 levels) - refactor to reduce complexity"
                    })

                # Architecture patterns (NEW)
                architecture = qa.get('architecture', {})
                if architecture.get('status') == 'concerning':
                    patterns.append({
                        'type': 'poor_architecture_consistency',
                        'severity': 'high',
                        'repo': repo_name,
                        'message': f"{repo_name}: Architecture has significant inconsistencies - violates established patterns"
                    })
                elif architecture.get('status') == 'needs_attention':
                    patterns.append({
                        'type': 'architecture_inconsistencies',
                        'severity': 'medium',
                        'repo': repo_name,
                        'message': f"{repo_name}: Some architectural inconsistencies - review project structure"
                    })

                # Pattern violations
                violations = architecture.get('pattern_violations', [])
                if len(violations) >= 2:
                    patterns.append({
                        'type': 'architectural_violations',
                        'severity': 'medium',
                        'repo': repo_name,
                        'value': len(violations),
                        'message': f"{repo_name}: {len(violations)} architectural pattern violations detected"
                    })

        # ===== SYSTEM PATTERNS (EXISTING) =====
        # Check merge rate - indicates system health
        for repo_name, stats in pr_stats.items():
            merge_rate = stats.get('merge_rate', 0)
            if merge_rate < 70:
                patterns.append({
                    'type': 'low_merge_rate',
                    'severity': 'medium',
                    'repo': repo_name,
                    'value': merge_rate,
                    'message': f"{repo_name}: {merge_rate}% merge rate - may need prompt tuning or better PR scoping"
                })
            elif merge_rate >= 85:
                patterns.append({
                    'type': 'healthy_merge_rate',
                    'severity': 'info',
                    'repo': repo_name,
                    'value': merge_rate,
                    'message': f"{repo_name}: {merge_rate}% merge rate - system performing well"
                })

        # Check for session failures (system issue, not content issue)
        failed_sessions = log_analysis.get('failed_sessions', 0)
        successful_sessions = log_analysis.get('successful_sessions', 0)
        total_sessions = failed_sessions + successful_sessions
        if total_sessions > 0:
            failure_rate = failed_sessions / total_sessions * 100
            if failure_rate > 20:
                patterns.append({
                    'type': 'high_session_failure_rate',
                    'severity': 'high',
                    'value': round(failure_rate, 1),
                    'message': f"Session failure rate is {round(failure_rate, 1)}% - check for system issues"
                })

        # Check error rates - indicates system problems
        error_count = log_analysis.get('error_count', 0)
        if error_count > 20:
            patterns.append({
                'type': 'high_error_rate',
                'severity': 'high',
                'value': error_count,
                'message': f"High error count ({error_count}) - check API limits, auth, network issues"
            })
        elif error_count > 5:
            patterns.append({
                'type': 'moderate_error_rate',
                'severity': 'medium',
                'value': error_count,
                'message': f"Moderate error count ({error_count}) - worth investigating"
            })

        # Parse failures indicate prompt/parsing issues
        if log_analysis.get('parse_failure_count', 0) > 3:
            patterns.append({
                'type': 'parse_failures',
                'severity': 'medium',
                'value': log_analysis['parse_failure_count'],
                'message': f"Decision parse failures ({log_analysis['parse_failure_count']}) - Tech Lead prompt may need adjustment"
            })

        # Timeouts indicate task complexity or system resource issues
        if log_analysis.get('timeout_count', 0) > 2:
            patterns.append({
                'type': 'timeouts',
                'severity': 'medium',
                'value': log_analysis['timeout_count'],
                'message': f"Timeouts detected ({log_analysis['timeout_count']}) - consider timeout config or task complexity"
            })

        # Tech Lead decision balance
        if decision_analysis:
            merge_rate = decision_analysis.get('merge_rate', 0)
            changes_count = decision_analysis.get('changes_count', 0)

            # If Tech Lead is requesting too many changes, feedback loop may be broken
            if changes_count > 5 and decision_analysis.get('total_decisions', 0) > 10:
                change_rate = changes_count / decision_analysis['total_decisions'] * 100
                if change_rate > 30:
                    patterns.append({
                        'type': 'high_change_request_rate',
                        'severity': 'medium',
                        'value': round(change_rate, 1),
                        'message': f"Tech Lead requesting changes on {round(change_rate, 1)}% of PRs - check if feedback is being addressed"
                    })

            # Check if close reasons indicate systemic issues
            close_reasons = decision_analysis.get('close_reasons', {})
            if close_reasons.get('missing_tests', 0) > 3:
                patterns.append({
                    'type': 'test_enforcement_issue',
                    'severity': 'medium',
                    'value': close_reasons['missing_tests'],
                    'message': f"PRs closed for missing tests ({close_reasons['missing_tests']}) - Senior Engineer prompt needs stronger test requirements"
                })

            # Track test-only PR closures (positive signal - system rejecting low-value work)
            if close_reasons.get('test_only', 0) > 0:
                patterns.append({
                    'type': 'test_only_rejected',
                    'severity': 'info',
                    'value': close_reasons['test_only'],
                    'message': f"Test-only PRs closed ({close_reasons['test_only']}) - system correctly rejecting low-value work"
                })

        return patterns

    # =========================================================================
    # SELF-HEALING ACTIONS
    # =========================================================================

    def _check_oauth_token(self) -> Dict:
        """Check OAuth token status and attempt refresh if needed"""
        result = {'action': 'oauth_check', 'status': 'ok', 'message': ''}

        creds_file = Path.home() / '.claude' / '.credentials.json'
        if not creds_file.exists():
            creds_file = Path('/home/barbossa/.claude/.credentials.json')

        if not creds_file.exists():
            result['status'] = 'error'
            result['message'] = 'No credentials file found'
            return result

        try:
            with open(creds_file, 'r') as f:
                creds = json.load(f)

            oauth = creds.get('claudeAiOauth', {})
            expires_at = oauth.get('expiresAt', 0)

            # Convert ms to seconds
            expires_ts = expires_at / 1000 if expires_at > 1e12 else expires_at
            expires_dt = datetime.fromtimestamp(expires_ts)
            now = datetime.now()

            hours_until_expiry = (expires_dt - now).total_seconds() / 3600

            if hours_until_expiry < 0:
                result['status'] = 'expired'
                result['message'] = f'OAuth token EXPIRED at {expires_dt}'
                self.logger.error(f"🔴 OAuth token EXPIRED! Run 'claude login' to refresh")
            elif hours_until_expiry < 24:
                result['status'] = 'warning'
                result['message'] = f'OAuth token expires in {hours_until_expiry:.1f} hours at {expires_dt}'
                self.logger.warning(f"🟡 OAuth token expires in {hours_until_expiry:.1f} hours!")
            else:
                result['status'] = 'ok'
                result['message'] = f'OAuth token valid for {hours_until_expiry:.1f} hours'
                self.logger.info(f"🟢 OAuth token valid for {hours_until_expiry:.1f} hours")

        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'Could not check OAuth: {e}'

        return result

    def _cleanup_stale_sessions(self) -> Dict:
        """Clean up stale/stuck sessions"""
        result = {'action': 'session_cleanup', 'cleaned': 0, 'message': ''}

        sessions_file = self.work_dir / 'sessions.json'
        if not sessions_file.exists():
            result['message'] = 'No sessions file'
            return result

        try:
            with open(sessions_file, 'r') as f:
                sessions = json.load(f)

            cutoff = datetime.now() - timedelta(hours=3)
            cleaned = 0

            for session in sessions:
                if session.get('status') == 'running':
                    started_str = session.get('started', '')
                    try:
                        started = datetime.fromisoformat(started_str)
                        if started < cutoff:
                            session['status'] = 'timeout'
                            session['completed'] = datetime.now().isoformat()
                            session['timeout_reason'] = 'Marked stale by auditor'
                            cleaned += 1
                    except:
                        pass

            if cleaned > 0:
                with open(sessions_file, 'w') as f:
                    json.dump(sessions, f, indent=2)
                self.logger.info(f"🧹 Cleaned {cleaned} stale sessions")

            result['cleaned'] = cleaned
            result['message'] = f'Cleaned {cleaned} stale sessions'

        except Exception as e:
            result['message'] = f'Session cleanup error: {e}'

        return result

    def _run_log_maintenance(self) -> Dict:
        """Run full log maintenance: rotation, compression, and cleanup.

        Uses LogRotationManager to:
        - Rotate oversized logs (>50MB)
        - Compress logs older than 3 days
        - Delete logs older than 14 days
        - Monitor disk usage and perform emergency cleanup if critical
        """
        log_manager = LogRotationManager(
            logs_dir=self.logs_dir,
            max_log_size_mb=50,
            compress_after_days=3,
            delete_after_days=14,
            disk_warning_threshold=85,
            disk_critical_threshold=95,
        )

        result = log_manager.run_maintenance()

        # Log a summary of actions taken
        if result.get('emergency'):
            self.logger.warning(f"Log maintenance (EMERGENCY): {result['summary']}")
        elif result['rotation'].get('rotated', 0) > 0 or \
             result['compression'].get('compressed', 0) > 0 or \
             result['cleanup'].get('deleted', 0) > 0:
            self.logger.info(f"Log maintenance: {result['summary']}")

        # Add disk health warning if present
        if result['disk_health'].get('warning'):
            self.logger.warning(result['disk_health']['warning'])

        # Convert to the expected action result format
        return {
            'action': 'log_maintenance',
            'rotated': result['rotation'].get('rotated', 0),
            'compressed': result['compression'].get('compressed', 0),
            'deleted': result['cleanup'].get('deleted', 0),
            'freed_mb': result['compression'].get('saved_mb', 0) + result['cleanup'].get('freed_mb', 0),
            'disk_percent': result['disk_health'].get('percent_used', 0),
            'disk_status': result['disk_health'].get('status', 'unknown'),
            'emergency_triggered': result.get('emergency') is not None,
            'message': result['summary'],
        }

    def _reset_pending_feedback(self) -> Dict:
        """Reset broken pending feedback file"""
        result = {'action': 'feedback_reset', 'reset': False, 'message': ''}

        feedback_file = self.work_dir / 'pending_feedback.json'

        try:
            if feedback_file.exists():
                with open(feedback_file, 'r') as f:
                    content = f.read().strip()

                # Check if file is corrupted or has very old entries
                if content and content != '{}':
                    try:
                        feedback = json.loads(content)
                        # Check for stale feedback (older than 24 hours)
                        has_stale = False
                        for pr_key, data in feedback.items():
                            if isinstance(data, dict) and 'timestamp' in data:
                                ts = datetime.fromisoformat(data['timestamp'])
                                if ts < datetime.now() - timedelta(hours=24):
                                    has_stale = True
                                    break

                        if has_stale:
                            with open(feedback_file, 'w') as f:
                                json.dump({}, f)
                            result['reset'] = True
                            result['message'] = 'Reset stale pending feedback'
                            self.logger.info("🧹 Reset stale pending feedback")
                    except json.JSONDecodeError:
                        # Corrupted file, reset it
                        with open(feedback_file, 'w') as f:
                            json.dump({}, f)
                        result['reset'] = True
                        result['message'] = 'Reset corrupted pending feedback file'
                        self.logger.info("🧹 Reset corrupted pending feedback file")
            else:
                result['message'] = 'No pending feedback file'

        except Exception as e:
            result['message'] = f'Feedback reset error: {e}'

        return result

    def _execute_self_healing(self) -> List[Dict]:
        """Execute all self-healing actions"""
        self.logger.info("\n" + "="*70)
        self.logger.info("EXECUTING SELF-HEALING ACTIONS")
        self.logger.info("="*70 + "\n")

        actions = []

        # 1. Check OAuth token
        self.logger.info("Checking OAuth token status...")
        oauth_result = self._check_oauth_token()
        actions.append(oauth_result)

        # 2. Clean up stale sessions
        self.logger.info("Cleaning up stale sessions...")
        session_result = self._cleanup_stale_sessions()
        actions.append(session_result)

        # 3. Run log maintenance (rotation, compression, cleanup)
        self.logger.info("Running log maintenance...")
        log_result = self._run_log_maintenance()
        actions.append(log_result)

        # 4. Reset broken feedback loop
        self.logger.info("Checking pending feedback...")
        feedback_result = self._reset_pending_feedback()
        actions.append(feedback_result)

        return actions

    def _create_quality_issues(self, patterns: List[Dict], recommendations: List[str]) -> int:
        """Create GitHub issues for CRITICAL quality problems that need action"""
        issues_created = 0

        # Only create issues for HIGH severity patterns
        critical_patterns = [p for p in patterns if p.get('severity') == 'high']

        if not critical_patterns:
            return 0

        self.logger.info("\n" + "="*70)
        self.logger.info("CREATING QUALITY IMPROVEMENT ISSUES")
        self.logger.info("="*70)

        # Group patterns by repository
        patterns_by_repo = {}
        for pattern in critical_patterns:
            repo = pattern.get('repo')
            if repo:
                if repo not in patterns_by_repo:
                    patterns_by_repo[repo] = []
                patterns_by_repo[repo].append(pattern)

        # Create one consolidated issue per repo (avoid spam)
        for repo_name, repo_patterns in patterns_by_repo.items():
            # Check if we already have a recent quality issue
            existing_issues = self._get_existing_issues(repo_name, 'quality')

            # Skip if we already created a quality issue in the last 7 days
            if existing_issues:
                self.logger.info(f"Skipping {repo_name} - quality issue already exists")
                continue

            # Build consolidated issue
            title = f"quality: address {len(repo_patterns)} critical quality issues"

            body_sections = ["## Quality Issues Detected by Auditor\n"]
            body_sections.append(f"The Auditor detected **{len(repo_patterns)} critical quality issues** that require attention:\n")

            for i, pattern in enumerate(repo_patterns, 1):
                ptype = pattern.get('type', 'unknown')
                # Find matching recommendation
                matching_rec = next((r for r in recommendations if repo_name in r and ptype.replace('_', ' ') in r.lower()), '')

                body_sections.append(f"### {i}. {ptype.replace('_', ' ').title()}")
                if matching_rec:
                    body_sections.append(f"{matching_rec}\n")
                else:
                    body_sections.append(f"Pattern: {ptype}\n")

            body_sections.append("\n## Action Required")
            body_sections.append("Please review and address these quality issues to improve codebase health.")
            body_sections.append("\n---")
            body_sections.append(f"*Created by Barbossa Auditor v{self.VERSION}*")

            body = '\n'.join(body_sections)

            # Create the issue
            if self._create_github_issue(repo_name, title, body, ['quality', 'backlog']):
                issues_created += 1

        return issues_created

    def _get_issue_tracker(self, repo_name: str) -> IssueTracker:
        """Get the issue tracker for a repository."""
        return get_issue_tracker(self.config, repo_name, self.logger)

    def _get_existing_issues(self, repo_name: str, label: str) -> List[Dict]:
        """Get existing issues with a specific label (created in last 7 days)"""
        try:
            tracker = self._get_issue_tracker(repo_name)
            issues = tracker.list_issues(labels=[label], limit=100)
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()

            # Filter to only recent issues (using created_at if available)
            result = []
            for issue in issues:
                result.append({
                    'id': issue.id,
                    'identifier': issue.identifier,
                    'title': issue.title,
                    'labels': issue.labels
                })
            return result
        except Exception as e:
            self.logger.warning(f"Failed to get existing issues: {e}")
            return []

    def _create_github_issue(self, repo_name: str, title: str, body: str, labels: List[str]) -> bool:
        """Create an issue using the configured tracker."""
        try:
            tracker = self._get_issue_tracker(repo_name)
            issue = tracker.create_issue(title=title, body=body, labels=labels)
            if issue:
                self.logger.info(f"✅ Created quality issue: {title}")
                self.logger.info(f"   URL: {issue.url}")
                return True
            else:
                self.logger.warning(f"Failed to create issue: {title}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to create issue: {e}")
            return False

    # =========================================================================
    # RECOMMENDATIONS
    # =========================================================================

    def _generate_recommendations(self, patterns: List[Dict]) -> List[str]:
        """Generate SYSTEM and QUALITY recommendations"""
        recommendations = []

        for pattern in patterns:
            ptype = pattern['type']

            # ===== QUALITY RECOMMENDATIONS (NEW) =====
            if ptype == 'low_test_coverage':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} test coverage is critically low - "
                    "Tech Lead should reject PRs that decrease coverage or lack tests for new code"
                )
            elif ptype == 'marginal_test_coverage':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} test coverage is marginal - "
                    "require tests for all new features and gradually increase coverage"
                )
            elif ptype == 'uncovered_critical_files':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has critical files with poor coverage - "
                    "prioritize adding tests for APIs, services, and business logic"
                )
            elif ptype == 'no_integration_tests':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} lacks integration tests - "
                    "API endpoints and database operations must have integration test coverage"
                )
            elif ptype == 'minimal_integration_tests':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} needs more integration tests - "
                    "each API endpoint should have at least one integration test"
                )
            elif ptype == 'no_e2e_framework':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} needs E2E testing - "
                    "install Playwright or Cypress to test critical user flows"
                )
            elif ptype == 'minimal_e2e_coverage':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} needs more E2E tests - "
                    "cover all critical user flows (auth, payments, core features)"
                )
            elif ptype == 'problematic_ui_changes':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has too many untested/frivolous UI changes - "
                    "Tech Lead should require E2E tests for UI PRs and reject style-only changes"
                )
            elif ptype == 'ui_changes_need_attention':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} UI changes need better testing - "
                    "all component changes should include or update tests"
                )
            elif ptype == 'high_ui_churn':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has high UI churn - "
                    "same components changed repeatedly indicates instability or unclear design"
                )
            elif ptype == 'poor_cross_layer_integration':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has orphaned changes - "
                    "contract/API changes MUST include corresponding frontend integration"
                )
            elif ptype == 'cross_layer_integration_gaps':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} integration could be better - "
                    "ensure backend changes are properly integrated with frontend"
                )
            elif ptype == 'high_code_bloat':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has high code bloat - "
                    "Tech Lead should reject PRs that add large files or duplicate existing functionality. Prioritize refactoring."
                )
            elif ptype == 'moderate_code_bloat':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has moderate code bloat - "
                    "review large files and consider breaking them into smaller, focused modules"
                )
            elif ptype == 'too_many_large_files':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has too many large files - "
                    "files >500 lines should be refactored into smaller, single-responsibility modules"
                )
            elif ptype == 'high_complexity_files':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has highly complex files - "
                    "deep nesting (>6 levels) makes code hard to understand. Extract functions and simplify control flow."
                )
            elif ptype == 'poor_architecture_consistency':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} architecture is inconsistent - "
                    "establish and document architectural patterns, then enforce them in PR reviews"
                )
            elif ptype == 'architecture_inconsistencies':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has architectural inconsistencies - "
                    "review project structure and align new code with established patterns"
                )
            elif ptype == 'architectural_violations':
                recommendations.append(
                    f"QUALITY: {pattern.get('repo', 'repo')} has architectural violations - "
                    "Tech Lead should enforce architectural patterns and reject PRs that violate them"
                )

            # ===== SYSTEM RECOMMENDATIONS (EXISTING) =====
            elif ptype == 'low_merge_rate':
                recommendations.append(
                    f"SYSTEM: {pattern.get('repo', 'repo')} merge rate is low - "
                    "consider tuning Senior Engineer prompt to produce smaller, more focused PRs"
                )
            elif ptype == 'high_session_failure_rate':
                recommendations.append(
                    "SYSTEM: High session failure rate - check Claude API connectivity, "
                    "rate limits, and error handling in agent code"
                )
            elif ptype == 'high_error_rate' or ptype == 'moderate_error_rate':
                recommendations.append(
                    "SYSTEM: Review error logs - common causes: API rate limits, "
                    "git auth issues, network timeouts, gh CLI problems"
                )
            elif ptype == 'parse_failures':
                recommendations.append(
                    "SYSTEM: Tech Lead decision parsing failing - "
                    "may need to adjust prompt format or improve parsing regex"
                )
            elif ptype == 'timeouts':
                recommendations.append(
                    "SYSTEM: Timeouts occurring - consider increasing CLAUDE_TIMEOUT in config "
                    "or optimizing prompts to reduce task complexity"
                )
            elif ptype == 'high_change_request_rate':
                recommendations.append(
                    "SYSTEM: Feedback loop may be broken - verify pending_feedback.json is being "
                    "read by Senior Engineer and changes are being addressed"
                )
            elif ptype == 'test_enforcement_issue':
                recommendations.append(
                    "SYSTEM: PRs failing for missing tests - strengthen MANDATORY TEST REQUIREMENTS "
                    "section in Senior Engineer prompt"
                )

        # Always add general system health tips if no critical issues
        if not any(p['severity'] == 'high' for p in patterns):
            recommendations.append(
                "SYSTEM: No critical issues detected. Consider reviewing cron schedules "
                "and agent coordination timing for optimization."
            )

        return recommendations

    # =========================================================================
    # HEALTH SCORE
    # =========================================================================

    def _calculate_health_score(self, pr_stats: Dict, log_analysis: Dict, patterns: List[Dict]) -> int:
        """Calculate overall system health score (0-100)"""
        score = 100

        # PR merge rate impact (max -30)
        avg_merge_rate = sum(s.get('merge_rate', 0) for s in pr_stats.values()) / len(pr_stats) if pr_stats else 0
        if avg_merge_rate < 80:
            score -= min(30, (80 - avg_merge_rate))

        # Error impact (max -20)
        error_count = log_analysis.get('error_count', 0)
        score -= min(20, error_count * 2)

        # Pattern severity impact (max -30)
        high_severity = sum(1 for p in patterns if p.get('severity') == 'high')
        medium_severity = sum(1 for p in patterns if p.get('severity') == 'medium')
        score -= high_severity * 10
        score -= medium_severity * 5

        # Timeout impact (max -10)
        timeout_count = log_analysis.get('timeout_count', 0)
        score -= min(10, timeout_count * 3)

        return max(0, min(100, score))

    # =========================================================================
    # MAIN AUDIT
    # =========================================================================

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + str(uuid.uuid4())[:8]

    def run(self, days: int = 7) -> Dict:
        """Run the full audit"""
        run_session_id = self._generate_session_id()

        self.logger.info(f"\n{'#'*70}")
        self.logger.info("BARBOSSA AUDITOR - SYSTEM HEALTH CHECK")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Analysis Period: Last {days} days")
        self.logger.info(f"{'#'*70}\n")

        # Track run start (fire-and-forget, never blocks)
        track_run_start("auditor", run_session_id, len(self.repositories))

        # Gather data
        self.logger.info("Gathering PR statistics...")
        pr_stats = {}
        for repo in self.repositories:
            stats = self._get_pr_stats(repo['name'], days)
            if stats:
                pr_stats[repo['name']] = stats
                self.logger.info(f"  {repo['name']}: {stats['total']} PRs, {stats['merge_rate']}% merge rate")

        self.logger.info("\nAnalyzing logs...")
        log_analysis = self._analyze_logs(days)
        self.logger.info(f"  Errors: {log_analysis.get('error_count', 0)}")
        self.logger.info(f"  Warnings: {log_analysis.get('warning_count', 0)}")
        self.logger.info(f"  Timeouts: {log_analysis.get('timeout_count', 0)}")

        self.logger.info("\nAnalyzing Tech Lead decisions...")
        decision_analysis = self._analyze_tech_lead_decisions()
        if decision_analysis:
            self.logger.info(f"  Decisions: {decision_analysis.get('total_decisions', 0)}")
            self.logger.info(f"  Merge rate: {decision_analysis.get('merge_rate', 0)}%")
            self.logger.info(f"  Avg value score: {decision_analysis.get('avg_value_score', 0)}/10")

        # ===== QUALITY ASSURANCE CHECKS (NEW) =====
        self.logger.info("\n" + "="*70)
        self.logger.info("QUALITY ASSURANCE ANALYSIS")
        self.logger.info("="*70)

        quality_stats = {}
        for repo in self.repositories:
            repo_name = repo['name']
            self.logger.info(f"\n{repo_name}:")

            # Test coverage
            self.logger.info("  Analyzing test coverage...")
            coverage = self._analyze_test_coverage(repo_name)
            if coverage.get('has_coverage'):
                self.logger.info(f"    Coverage: {coverage['coverage_percentage']}% ({coverage['status']})")
                if coverage.get('uncovered_critical_files'):
                    self.logger.info(f"    ⚠️  {len(coverage['uncovered_critical_files'])} critical files under 50% coverage")
            else:
                self.logger.info(f"    ⚠️  No coverage data ({coverage.get('status', 'unknown')})")

            # Integration tests
            self.logger.info("  Checking integration tests...")
            integration = self._detect_integration_tests(repo_name)
            if integration['has_integration_tests']:
                self.logger.info(f"    Integration tests: {integration['integration_test_count']} found ({integration['status']})")
                if integration['has_api_integration_tests']:
                    self.logger.info("    ✓ API integration tests present")
                if integration['has_db_integration_tests']:
                    self.logger.info("    ✓ Database integration tests present")
            else:
                self.logger.info(f"    ⚠️  No integration tests ({integration['status']})")

            # E2E tests
            self.logger.info("  Checking E2E tests...")
            e2e = self._analyze_e2e_test_health(repo_name)
            if e2e['e2e_framework']:
                self.logger.info(f"    Framework: {e2e['e2e_framework']}")
                self.logger.info(f"    E2E tests: {e2e['e2e_test_count']} found ({e2e['status']})")
                if e2e.get('critical_flows_covered'):
                    flows = ', '.join(e2e['critical_flows_covered'][:5])
                    self.logger.info(f"    ✓ Critical flows: {flows}")
            else:
                self.logger.info(f"    ⚠️  No E2E framework configured")

            # Code bloat detection (NEW)
            self.logger.info("  Detecting code bloat patterns...")
            bloat = self._detect_code_bloat_patterns(repo_name, days)
            if bloat['status'] == 'healthy':
                self.logger.info(f"    ✓ Code bloat: {bloat['status']} (score: {bloat['bloat_score']})")
            else:
                self.logger.info(f"    ⚠️  Code bloat: {bloat['status']} (score: {bloat['bloat_score']})")
                if bloat['large_files']:
                    self.logger.info(f"      {len(bloat['large_files'])} large files (>500 lines)")
                if bloat['complex_files']:
                    self.logger.info(f"      {len(bloat['complex_files'])} highly nested files")
                if bloat['duplicate_utility_functions'] > 0:
                    self.logger.info(f"      {bloat['duplicate_utility_functions']} potential duplicate utility dirs")

            # Architecture consistency (NEW)
            self.logger.info("  Analyzing architecture consistency...")
            architecture = self._analyze_architecture_consistency(repo_name, days)
            if architecture['status'] == 'healthy':
                self.logger.info(f"    ✓ Architecture: {architecture['status']}")
            else:
                self.logger.info(f"    ⚠️  Architecture: {architecture['status']}")
                if architecture['pattern_violations']:
                    for violation in architecture['pattern_violations'][:3]:
                        self.logger.info(f"      ✗ {violation}")
                if architecture['missing_patterns']:
                    for missing in architecture['missing_patterns'][:3]:
                        self.logger.info(f"      ⚠ {missing}")

            # UI changes assessment
            self.logger.info("  Assessing UI changes...")
            ui = self._assess_ui_changes(repo_name, days)
            if ui['ui_pr_count'] > 0:
                self.logger.info(f"    UI PRs: {ui['ui_pr_count']} ({ui['status']})")
                if ui['untested_ui_pr_count'] > 0:
                    self.logger.info(f"    ⚠️  {ui['untested_ui_pr_count']} UI PRs without tests")
                if ui['style_only_pr_count'] > 0:
                    self.logger.info(f"    ⚠️  {ui['style_only_pr_count']} style-only PRs (frivolous)")
                if ui['ui_churn_files']:
                    self.logger.info(f"    ⚠️  {len(ui['ui_churn_files'])} high-churn UI files")
            else:
                self.logger.info("    No recent UI changes")

            # Cross-layer integration
            self.logger.info("  Verifying cross-layer integration...")
            cross_layer = self._verify_cross_layer_integration(repo_name, days)
            if cross_layer['orphaned_changes']:
                self.logger.info(f"    ⚠️  {len(cross_layer['orphaned_changes'])} orphaned changes ({cross_layer['status']})")
                for change in cross_layer['orphaned_changes'][:3]:
                    self.logger.info(f"      PR #{change['pr']}: {change['type']}")
            else:
                self.logger.info(f"    ✓ Cross-layer integration looks good ({cross_layer['status']})")

            quality_stats[repo_name] = {
                'coverage': coverage,
                'integration_tests': integration,
                'e2e_tests': e2e,
                'code_bloat': bloat,
                'architecture': architecture,
                'ui_assessment': ui,
                'cross_layer': cross_layer
            }

        self.logger.info("\n" + "="*70)

        self.logger.info("\nDetecting patterns...")
        patterns = self._detect_patterns(pr_stats, log_analysis, decision_analysis, quality_stats)
        for p in patterns:
            icon = "🔴" if p['severity'] == 'high' else "🟡" if p['severity'] == 'medium' else "🟢"
            self.logger.info(f"  {icon} {p['message']}")

        self.logger.info("\nGenerating recommendations...")
        recommendations = self._generate_recommendations(patterns)
        for i, rec in enumerate(recommendations, 1):
            self.logger.info(f"  {i}. {rec}")

        # Execute self-healing actions
        self_healing_actions = self._execute_self_healing()

        # Create GitHub issues for CRITICAL quality problems
        created_issues = self._create_quality_issues(patterns, recommendations)

        # Calculate health score
        health_score = self._calculate_health_score(pr_stats, log_analysis, patterns)

        # Summarize self-healing results
        self.logger.info("\n" + "="*70)
        self.logger.info("SELF-HEALING SUMMARY")
        self.logger.info("="*70)
        for action in self_healing_actions:
            status_icon = "✅" if action.get('status') == 'ok' or action.get('cleaned', 0) > 0 or action.get('deleted', 0) > 0 else "⚠️" if action.get('status') == 'warning' else "❌" if action.get('status') in ['error', 'expired'] else "➖"
            self.logger.info(f"  {status_icon} {action['action']}: {action['message']}")

        if created_issues:
            self.logger.info(f"\n📋 Created {created_issues} quality improvement issues")

        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"SYSTEM HEALTH SCORE: {health_score}/100")
        if health_score >= 80:
            self.logger.info("Status: HEALTHY - System operating optimally")
        elif health_score >= 60:
            self.logger.info("Status: FAIR - Some issues need attention")
        else:
            self.logger.info("Status: NEEDS ATTENTION - Multiple issues detected")
        self.logger.info(f"{'='*70}\n")

        # Compile audit result
        audit = {
            'timestamp': datetime.now().isoformat(),
            'period_days': days,
            'health_score': health_score,
            'pr_stats': pr_stats,
            'log_analysis': {k: v for k, v in log_analysis.items() if k != 'recent_errors'},
            'decision_analysis': decision_analysis,
            'quality_stats': quality_stats,  # NEW: Quality assurance metrics
            'patterns': patterns,
            'recommendations': recommendations,
            'self_healing_actions': self_healing_actions,
        }

        # Save results
        self._save_audit_history(audit)

        # Extract OAuth status from self-healing actions
        oauth_action = next((a for a in self_healing_actions if a['action'] == 'oauth_check'), {})

        # Save insights for other agents - ENHANCED with quality metrics for Tech Lead
        insights = {
            'last_audit': datetime.now().isoformat(),
            'health_score': health_score,
            'status': 'healthy' if health_score >= 80 else 'fair' if health_score >= 60 else 'needs_attention',
            'recommendations': recommendations,
            'system_issues': [p['message'] for p in patterns if p['severity'] == 'high'],
            'merge_rates': {repo: stats.get('merge_rate', 0) for repo, stats in pr_stats.items()},
            'error_count': log_analysis.get('error_count', 0),
            'timeout_count': log_analysis.get('timeout_count', 0),
            'oauth_status': oauth_action.get('status', 'unknown'),
            'oauth_message': oauth_action.get('message', ''),
            'self_healing_actions': self_healing_actions,
            # NEW: Quality insights for Tech Lead to enforce during PR review
            'quality_metrics': {
                repo: {
                    'test_coverage': qa.get('coverage', {}).get('coverage_percentage', 0),
                    'coverage_status': qa.get('coverage', {}).get('status', 'unknown'),
                    'has_integration_tests': qa.get('integration_tests', {}).get('has_integration_tests', False),
                    'has_e2e_tests': qa.get('e2e_tests', {}).get('has_e2e_tests', False),
                    'e2e_framework': qa.get('e2e_tests', {}).get('e2e_framework', None),
                    'bloat_score': qa.get('code_bloat', {}).get('bloat_score', 0),
                    'bloat_status': qa.get('code_bloat', {}).get('status', 'unknown'),
                    'large_files_count': len(qa.get('code_bloat', {}).get('large_files', [])),
                    'complex_files_count': len(qa.get('code_bloat', {}).get('complex_files', [])),
                    'architecture_status': qa.get('architecture', {}).get('status', 'unknown'),
                    'architecture_violations': len(qa.get('architecture', {}).get('pattern_violations', [])),
                    'ui_health': qa.get('ui_assessment', {}).get('status', 'unknown'),
                    'cross_layer_health': qa.get('cross_layer', {}).get('status', 'unknown'),
                    'untested_ui_prs': qa.get('ui_assessment', {}).get('untested_ui_pr_count', 0),
                    'style_only_prs': qa.get('ui_assessment', {}).get('style_only_pr_count', 0),
                }
                for repo, qa in quality_stats.items()
            },
            'quality_issues': [
                p['message'] for p in patterns
                if p.get('type', '').startswith(('low_test', 'no_integration', 'no_e2e', 'problematic_ui', 'poor_cross'))
            ],
        }
        self._save_insights(insights)

        # Track run end (fire-and-forget)
        track_run_end("auditor", run_session_id, success=True, pr_created=False)

        # Send audit summary notification
        status_text = 'healthy' if health_score >= 80 else 'fair' if health_score >= 60 else 'needs attention'
        high_severity_count = sum(1 for p in patterns if p['severity'] == 'high')
        notify_agent_run_complete(
            agent='auditor',
            success=(health_score >= 60),
            summary=f"System health: {health_score}/100 ({status_text})",
            details={
                'Health Score': f"{health_score}/100",
                'Status': status_text.title(),
                'Critical Issues': high_severity_count,
                'Recommendations': len(recommendations)
            }
        )

        # Ensure all notifications complete before process exits
        wait_for_pending()
        return audit


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Barbossa Auditor v1.2.0 - System Health & Self-Improvement'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )

    args = parser.parse_args()

    auditor = BarbossaAuditor()
    auditor.run(days=args.days)


if __name__ == "__main__":
    main()
