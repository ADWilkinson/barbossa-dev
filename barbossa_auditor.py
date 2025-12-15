#!/usr/bin/env python3
"""
Barbossa Auditor v1.0 - Self-Improving System Audit Agent
Runs daily to analyze logs, PR outcomes, and system health.
Identifies patterns, issues, and opportunities for improvement.
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


class BarbossaAuditor:
    """
    Self-improving audit agent that analyzes system performance
    and identifies opportunities for optimization.
    """

    VERSION = "1.0.0"
    ROLE = "auditor"

    def __init__(self, work_dir: Optional[Path] = None):
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-engineer'
        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.config_file = self.work_dir / 'config' / 'repositories.json'
        self.audit_history_file = self.work_dir / 'audit_history.json'
        self.insights_file = self.work_dir / 'system_insights.json'

        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self._setup_logging()
        self.config = self._load_config()
        self.repositories = self.config.get('repositories', [])
        self.owner = self.config.get('owner', 'ADWilkinson')

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
    # PATTERN DETECTION
    # =========================================================================

    def _detect_patterns(self, pr_stats: Dict, log_analysis: Dict, decision_analysis: Dict) -> List[Dict]:
        """Detect SYSTEM patterns and issues - focus on mechanics, not content restrictions"""
        patterns = []

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
    # RECOMMENDATIONS
    # =========================================================================

    def _generate_recommendations(self, patterns: List[Dict]) -> List[str]:
        """Generate SYSTEM-focused recommendations - no content restrictions"""
        recommendations = []

        for pattern in patterns:
            ptype = pattern['type']

            if ptype == 'low_merge_rate':
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

    def run(self, days: int = 7) -> Dict:
        """Run the full audit"""
        self.logger.info(f"\n{'#'*70}")
        self.logger.info("BARBOSSA AUDITOR - SYSTEM HEALTH CHECK")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Analysis Period: Last {days} days")
        self.logger.info(f"{'#'*70}\n")

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

        self.logger.info("\nDetecting patterns...")
        patterns = self._detect_patterns(pr_stats, log_analysis, decision_analysis)
        for p in patterns:
            icon = "🔴" if p['severity'] == 'high' else "🟡" if p['severity'] == 'medium' else "🟢"
            self.logger.info(f"  {icon} {p['message']}")

        self.logger.info("\nGenerating recommendations...")
        recommendations = self._generate_recommendations(patterns)
        for i, rec in enumerate(recommendations, 1):
            self.logger.info(f"  {i}. {rec}")

        # Calculate health score
        health_score = self._calculate_health_score(pr_stats, log_analysis, patterns)

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
            'patterns': patterns,
            'recommendations': recommendations,
        }

        # Save results
        self._save_audit_history(audit)

        # Save insights for other agents - system health only, no content restrictions
        insights = {
            'last_audit': datetime.now().isoformat(),
            'health_score': health_score,
            'status': 'healthy' if health_score >= 80 else 'fair' if health_score >= 60 else 'needs_attention',
            'recommendations': recommendations,
            'system_issues': [p['message'] for p in patterns if p['severity'] == 'high'],
            'merge_rates': {repo: stats.get('merge_rate', 0) for repo, stats in pr_stats.items()},
            'error_count': log_analysis.get('error_count', 0),
            'timeout_count': log_analysis.get('timeout_count', 0),
        }
        self._save_insights(insights)

        return audit


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Barbossa Auditor v1.0 - System Health & Self-Improvement'
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
