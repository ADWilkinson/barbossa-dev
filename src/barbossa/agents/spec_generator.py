#!/usr/bin/env python3
"""
Barbossa Spec Generator - Cross-repo product specification agent.

Operates on "products" (linked repo groups) to generate full-stack specs
with distributed tickets (parent spec + child implementation tickets).
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from barbossa.utils.prompts import get_system_prompt
from barbossa.agents.firebase import (
    get_client,
    check_version,
    track_run_start,
    track_run_end,
    configure_telemetry
)
from barbossa.utils.issue_tracker import get_issue_tracker, Issue, IssueTracker
from barbossa.utils.notifications import (
    notify_agent_run_complete,
    notify_error,
    notify_spec_created,
    wait_for_pending
)


class BarbossaSpecGenerator:
    """Cross-repo product specification generator."""

    VERSION = "1.8.1"
    DEFAULT_MAX_SPECS_PER_RUN = 2
    DEFAULT_DEDUP_DAYS = 14
    DEFAULT_MIN_VALUE_SCORE = 7
    MAX_CLAUDE_MD_SIZE = 10000  # 10KB per repo

    def __init__(self, work_dir: Optional[Path] = None, product_filter: Optional[str] = None):
        default_dir = Path(os.environ.get('BARBOSSA_DIR', '/app'))
        if not default_dir.exists():
            default_dir = Path.home() / 'barbossa-dev'

        self.work_dir = work_dir or default_dir
        self.logs_dir = self.work_dir / 'logs'
        self.projects_dir = self.work_dir / 'projects'
        self.config_file = self.work_dir / 'config' / 'repositories.json'
        self.product_filter = product_filter

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

        # Firebase client (analytics + state tracking, never blocks)
        self.firebase = get_client()

        # Soft version check - warn but never block
        update_msg = check_version()
        if update_msg:
            self.logger.info(f"UPDATE AVAILABLE: {update_msg}")

        self.config = self._load_config()
        self.products = self.config.get('products', [])
        self.repositories = self.config.get('repositories', [])
        self.owner = self.config.get('owner')

        if not self.owner:
            raise ValueError("'owner' is required in config/repositories.json")

        # Load global spec_mode settings (system switch)
        self.settings = self.config.get('settings', {})
        self.spec_mode_settings = self.settings.get('spec_mode', {})
        self.enabled = self.spec_mode_settings.get('enabled', False)  # Disabled by default
        self.dedup_days = self.spec_mode_settings.get('deduplication_days', self.DEFAULT_DEDUP_DAYS)
        self.min_value_score = self.spec_mode_settings.get('min_value_score', self.DEFAULT_MIN_VALUE_SCORE)
        self.max_specs_per_run = self.spec_mode_settings.get('max_specs_per_run', self.DEFAULT_MAX_SPECS_PER_RUN)
        self.spec_label = self.spec_mode_settings.get('spec_label', 'spec')
        self.impl_label = self.spec_mode_settings.get('implementation_label', 'backlog')

        # Configure telemetry based on settings
        telemetry_enabled = self.settings.get('telemetry', True)
        configure_telemetry(telemetry_enabled)

        self.logger.info("=" * 60)
        self.logger.info(f"BARBOSSA SPEC GENERATOR v{self.VERSION}")
        self.logger.info(f"Products configured: {len(self.products)}")
        if self.product_filter:
            self.logger.info(f"Product filter: {self.product_filter}")
        self.logger.info(f"Settings: dedup_days={self.dedup_days}, min_value_score={self.min_value_score}")
        self.logger.info("=" * 60)

    def _setup_logging(self):
        log_file = self.logs_dir / f"spec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('spec_generator')

    def _load_config(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in config file {self.config_file}: {e}")
                return {'repositories': [], 'products': []}
        return {'repositories': [], 'products': []}

    def _run_cmd(self, cmd: str, cwd: str = None, timeout: int = 60) -> Optional[str]:
        """Run a shell command and return output."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                self.logger.warning(f"Command failed (exit {result.returncode}): {cmd[:100]}")
                if result.stderr:
                    self.logger.warning(f"Stderr: {result.stderr[:500]}")
            return None
        except Exception as e:
            self.logger.warning(f"Command failed: {cmd[:100]} - {e}")
            return None

    def _clone_or_update_repo(self, repo_name: str, repo_url: str) -> Optional[Path]:
        """Ensure repo is cloned and up to date."""
        repo_path = self.projects_dir / repo_name

        if repo_path.exists():
            # Try main branch first, fall back to master
            result = self._run_cmd("git fetch origin && git checkout main && git pull origin main", cwd=str(repo_path))
            if result is None:
                # Try master branch as fallback
                self._run_cmd("git fetch origin && git checkout master && git pull origin master", cwd=str(repo_path))
        else:
            self.projects_dir.mkdir(parents=True, exist_ok=True)
            result = self._run_cmd(f"git clone {repo_url} {repo_name}", cwd=str(self.projects_dir))
            if result is None:
                self.logger.error(f"Failed to clone repository: {repo_url}")
                return None

        if repo_path.exists():
            return repo_path
        return None

    def _read_claude_md(self, repo_path: Path) -> str:
        """Read CLAUDE.md for project context."""
        claude_md = repo_path / 'CLAUDE.md'
        if claude_md.exists():
            with open(claude_md, 'r') as f:
                content = f.read()
                if len(content) > self.MAX_CLAUDE_MD_SIZE:
                    self.logger.info(f"Truncating CLAUDE.md from {len(content)} to {self.MAX_CLAUDE_MD_SIZE} bytes")
                return content[:self.MAX_CLAUDE_MD_SIZE]
        return ""

    def _get_repo_config(self, repo_name: str) -> Optional[Dict]:
        """Get repository configuration by name."""
        for repo in self.repositories:
            if repo['name'] == repo_name:
                return repo
        return None

    def _get_issue_tracker(self, repo_name: str) -> IssueTracker:
        """Get the issue tracker for a repository (GitHub or Linear)."""
        return get_issue_tracker(self.config, repo_name, self.logger)

    def _get_existing_specs(self, product: Dict) -> List[Dict]:
        """Get existing spec issues from the primary repo."""
        primary_repo = product.get('primary_repo')
        if not primary_repo:
            return []

        try:
            tracker = self._get_issue_tracker(primary_repo)
            issues = tracker.list_issues(labels=[self.spec_label], limit=50)
            return [{'title': i.title, 'body': i.body, 'labels': i.labels, 'url': i.url} for i in issues]
        except Exception as e:
            self.logger.warning(f"Failed to get existing specs: {e}")
            return []

    def _aggregate_product_context(self, product: Dict) -> Dict[str, Any]:
        """
        Aggregate context from all linked repositories.

        Returns dict with:
        - repos: {repo_name: {path, claude_md, role}}
        - context: product context from config
        - existing_specs: list of existing spec titles
        """
        context = {
            'repos': {},
            'context': product.get('context', {}),
            'existing_specs': []
        }

        repo_names = product.get('repositories', [])
        known_integrations = product.get('context', {}).get('known_integrations', {})

        for repo_name in repo_names:
            repo_config = self._get_repo_config(repo_name)
            if not repo_config:
                self.logger.warning(f"Repository '{repo_name}' not found in repositories config")
                continue

            repo_path = self._clone_or_update_repo(repo_name, repo_config['url'])
            if not repo_path:
                self.logger.error(f"Could not clone/update repo: {repo_name}")
                continue

            claude_md = self._read_claude_md(repo_path)
            role = known_integrations.get(repo_name, f"Repository: {repo_name}")

            context['repos'][repo_name] = {
                'path': repo_path,
                'claude_md': claude_md,
                'role': role,
                'config': repo_config
            }

            self.logger.info(f"Loaded context for {repo_name}: {len(claude_md)} chars")

        # Get existing specs for deduplication
        context['existing_specs'] = self._get_existing_specs(product)
        self.logger.info(f"Found {len(context['existing_specs'])} existing specs")

        return context

    def _build_spec_prompt(self, product: Dict, context: Dict[str, Any]) -> str:
        """Build the mega-prompt for spec generation."""
        template = get_system_prompt("spec_generator")
        if not template:
            self.logger.error("Failed to load spec_generator prompt from prompts/spec_generator.txt")
            raise RuntimeError("Spec generator prompt file not found. Check prompts/ directory.")

        # Build repository sections
        repo_sections = []
        for repo_name, repo_data in context['repos'].items():
            section = f"""### {repo_name}
**Role:** {repo_data['role']}

**Documentation:**
```
{repo_data['claude_md'][:8000] if repo_data['claude_md'] else 'No CLAUDE.md found'}
```
"""
            repo_sections.append(section)

        repos_text = "\n\n".join(repo_sections)

        # Build existing specs list
        existing_text = "None" if not context['existing_specs'] else "\n".join([
            f"- {spec['title']}" for spec in context['existing_specs']
        ])

        # Build constraints list
        constraints = context['context'].get('constraints', [])
        constraints_text = "\n".join([f"- {c}" for c in constraints]) if constraints else "None specified"

        # Build strategy notes
        strategy = context['context'].get('strategy_notes', [])
        strategy_text = "\n".join([f"- {s}" for s in strategy]) if strategy else "None specified"

        # Replace template variables
        prompt = template
        prompt = prompt.replace("{{product_name}}", product.get('name', 'Unknown'))
        prompt = prompt.replace("{{product_description}}", product.get('description', 'No description'))
        prompt = prompt.replace("{{product_vision}}", context['context'].get('vision', 'Not specified'))
        prompt = prompt.replace("{{current_phase}}", context['context'].get('current_phase', 'Not specified'))
        prompt = prompt.replace("{{target_users}}", context['context'].get('target_users', 'Not specified'))
        prompt = prompt.replace("{{constraints}}", constraints_text)
        prompt = prompt.replace("{{strategy_notes}}", strategy_text)
        prompt = prompt.replace("{{repository_sections}}", repos_text)
        prompt = prompt.replace("{{existing_specs}}", existing_text)
        prompt = prompt.replace("{{max_specs}}", str(self.max_specs_per_run))
        prompt = prompt.replace("{{min_value_score}}", str(self.min_value_score))
        prompt = prompt.replace("{{repo_names}}", ", ".join(context['repos'].keys()))

        return prompt

    def _analyze_with_claude(self, prompt: str) -> Optional[Dict]:
        """Call Claude to generate specs."""
        # Write prompt to temp file
        prompt_file = self.work_dir / 'temp_spec_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        self.logger.info(f"Prompt size: {len(prompt)} chars")

        # Call Claude CLI (20 minute timeout for complex cross-repo analysis)
        result = self._run_cmd(
            f'cat {prompt_file} | claude -p --output-format json',
            timeout=1200
        )

        prompt_file.unlink(missing_ok=True)

        if not result:
            self.logger.error("No response from Claude")
            return None

        try:
            # Claude CLI returns wrapper JSON with result field
            wrapper = json.loads(result)
            if 'result' not in wrapper:
                self.logger.warning("No 'result' field in Claude response")
                return None

            inner_result = wrapper['result']

            # Extract JSON from markdown code block if present
            json_block_match = re.search(r'```json\s*\n([\s\S]*?)\n```', inner_result)
            if json_block_match:
                json_str = json_block_match.group(1).strip()
                self.logger.info(f"Extracted JSON from code block: {len(json_str)} chars")
                return json.loads(json_str)

            # Try parsing the result directly
            try:
                return json.loads(inner_result)
            except json.JSONDecodeError:
                pass

            # Look for JSON object with specs array
            json_obj_match = re.search(r'\{[\s\S]*"specs"\s*:\s*\[[\s\S]*\][\s\S]*\}', inner_result)
            if json_obj_match:
                json_str = json_obj_match.group()
                self.logger.info(f"Extracted specs JSON: {len(json_str)} chars")
                return json.loads(json_str)

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            self.logger.debug(f"Raw result: {result[:1000]}")

        return None

    def _extract_keywords(self, text: str) -> set:
        """Extract meaningful keywords from text for similarity comparison."""
        text = text.lower()
        for prefix in ['[spec]', 'spec:', 'feature:', 'feat:', 'add ', 'implement ', 'create ']:
            text = text.replace(prefix, '')

        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                      'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
                      'that', 'these', 'those', 'new', 'support', 'add', 'enable'}

        words = text.split()
        keywords = {w.strip('.,!?()[]{}:;-') for w in words if len(w) > 3 and w not in stop_words}
        return keywords

    def _is_duplicate_spec(self, title: str, existing_specs: List[Dict]) -> bool:
        """Check if a spec is semantically similar to existing specs."""
        new_keywords = self._extract_keywords(title)

        for spec in existing_specs:
            existing_title = spec.get('title', '')
            existing_keywords = self._extract_keywords(existing_title)

            if not new_keywords or not existing_keywords:
                continue

            overlap = new_keywords & existing_keywords
            overlap_ratio = len(overlap) / min(len(new_keywords), len(existing_keywords))

            if overlap_ratio > 0.5:
                self.logger.info(f"Similar spec found: '{existing_title}' (overlap: {overlap_ratio:.2%})")
                return True

        return False

    def _build_critique_prompt(self, specs: List[Dict], product: Dict, context: Dict[str, Any]) -> str:
        """Build the critique prompt for second-pass review."""
        template = get_system_prompt("spec_critique")
        if not template:
            self.logger.warning("No critique prompt found, skipping refinement pass")
            return None

        specs_json = json.dumps({"specs": specs}, indent=2)

        prompt = template
        prompt = prompt.replace("{{product_name}}", product.get('name', 'Unknown'))
        prompt = prompt.replace("{{repo_names}}", ", ".join(context['repos'].keys()))
        prompt = prompt.replace("{{specs_json}}", specs_json)

        return prompt

    def _critique_and_refine_specs(self, specs: List[Dict], product: Dict, context: Dict[str, Any]) -> List[Dict]:
        """
        Second-pass review: critique and refine specs for precision.

        Returns only specs that pass review (approved or refined).
        Rejected specs are logged and discarded.
        """
        if not specs:
            return []

        self.logger.info(f"PASS 2: Critiquing {len(specs)} spec(s) for precision...")

        prompt = self._build_critique_prompt(specs, product, context)
        if not prompt:
            self.logger.warning("Skipping critique pass - no prompt template")
            return specs  # Return original specs if no critique prompt

        # Write prompt to temp file
        prompt_file = self.work_dir / 'temp_critique_prompt.txt'
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        self.logger.info(f"Critique prompt size: {len(prompt)} chars")

        # Call Claude CLI for critique (10 minute timeout)
        result = self._run_cmd(
            f'cat {prompt_file} | claude -p --output-format json',
            timeout=600
        )

        prompt_file.unlink(missing_ok=True)

        if not result:
            self.logger.warning("No response from critique pass, using original specs")
            return specs

        try:
            wrapper = json.loads(result)
            if 'result' not in wrapper:
                self.logger.warning("No 'result' in critique response, using original specs")
                return specs

            inner_result = wrapper['result']

            # Extract JSON from response
            review_data = None

            # Try markdown code block first
            json_block_match = re.search(r'```json\s*\n([\s\S]*?)\n```', inner_result)
            if json_block_match:
                review_data = json.loads(json_block_match.group(1).strip())
            else:
                # Try direct parse
                try:
                    review_data = json.loads(inner_result)
                except json.JSONDecodeError:
                    # Try finding JSON object
                    json_obj_match = re.search(r'\{[\s\S]*"reviewed_specs"\s*:\s*\[[\s\S]*\][\s\S]*\}', inner_result)
                    if json_obj_match:
                        review_data = json.loads(json_obj_match.group())

            if not review_data:
                self.logger.warning("Could not parse critique response, using original specs")
                return specs

            # Process reviewed specs
            reviewed = review_data.get('reviewed_specs', [])
            summary = review_data.get('summary', {})

            self.logger.info(f"Critique summary: {summary.get('approved', 0)} approved, "
                           f"{summary.get('refined', 0)} refined, {summary.get('rejected', 0)} rejected")
            if summary.get('notes'):
                self.logger.info(f"Reviewer notes: {summary['notes']}")

            refined_specs = []
            for review in reviewed:
                decision = review.get('decision', 'REJECT')
                original_title = review.get('original_title', 'Unknown')

                if decision == 'REJECT':
                    reason = review.get('rejection_reason', 'No reason provided')
                    self.logger.info(f"REJECTED: '{original_title}' - {reason}")
                    continue

                refined_spec = review.get('refined_spec')
                if refined_spec:
                    if decision == 'REFINE':
                        self.logger.info(f"REFINED: '{original_title}'")
                    else:
                        self.logger.info(f"APPROVED: '{original_title}'")
                    refined_specs.append(refined_spec)
                else:
                    self.logger.warning(f"No refined_spec for {decision} decision on '{original_title}'")

            return refined_specs

        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parse error in critique: {e}, using original specs")
            return specs
        except Exception as e:
            self.logger.warning(f"Error in critique pass: {e}, using original specs")
            return specs

    def _generate_parent_spec_body(self, spec: Dict, product: Dict, child_tickets: List[Dict] = None) -> str:
        """Generate the parent spec issue body."""
        user_stories = spec.get('user_stories', [])
        user_stories_text = "\n".join([f"- {s}" for s in user_stories]) if user_stories else "- As a user, I want this feature"

        success_metrics = spec.get('success_metrics', [])
        metrics_text = "\n".join([f"- {m}" for m in success_metrics]) if success_metrics else "- Feature works as expected"

        acceptance = spec.get('full_acceptance_criteria', [])
        acceptance_text = "\n".join([f"- [ ] {c}" for c in acceptance]) if acceptance else "- [ ] Feature implemented"

        dependencies = spec.get('dependencies', [])
        deps_text = "\n".join([f"- {d}" for d in dependencies]) if dependencies else "None"

        # Build per-repo implementation sections
        repo_sections = []
        affected_repos = spec.get('affected_repos', {})
        for repo_name, repo_spec in affected_repos.items():
            files = repo_spec.get('files_to_modify', [])
            files_text = "\n".join([f"  - `{f}`" for f in files]) if files else "  - TBD"
            criteria = repo_spec.get('acceptance_criteria', [])
            criteria_text = "\n".join([f"  - [ ] {c}" for c in criteria]) if criteria else "  - [ ] Implementation complete"

            section = f"""### {repo_name}
**Role:** {repo_spec.get('role', 'Implementation')}

**Implementation Details:**
{repo_spec.get('implementation_details', 'See child ticket for details')}

**Files to Modify:**
{files_text}

**Acceptance Criteria:**
{criteria_text}
"""
            repo_sections.append(section)

        repo_text = "\n".join(repo_sections)

        # Child ticket references (to be filled in after creation)
        child_refs = ""
        if child_tickets:
            child_refs = "\n## Implementation Tickets\n" + "\n".join([
                f"- [{t['repo']}#{t['number']}]({t['url']})" for t in child_tickets
            ])

        return f"""## Problem Statement
{spec.get('problem_statement', 'No problem statement provided.')}

## User Stories
{user_stories_text}

## Success Metrics
{metrics_text}

## Full-Stack Specification

{repo_text}

## Acceptance Criteria
{acceptance_text}

## Technical Approach
{spec.get('technical_approach', 'Follow existing patterns in each repository.')}

## Dependencies
{deps_text}

## Metadata
- **Value Score:** {spec.get('value_score', '?')}/10
- **Effort Estimate:** {spec.get('effort_estimate', 'medium')}
- **Product:** {product.get('name', 'Unknown')}
{child_refs}

---
*Created by Barbossa Spec Generator v{self.VERSION}*
"""

    def _generate_child_ticket_body(self, spec: Dict, repo_name: str, repo_spec: Dict, parent_issue: Issue, product: Dict) -> str:
        """Generate a child implementation ticket body for a specific repo."""
        files = repo_spec.get('files_to_modify', [])
        files_text = "\n".join([f"- `{f}`" for f in files]) if files else "- TBD based on implementation"

        criteria = repo_spec.get('acceptance_criteria', [])
        criteria_text = "\n".join([f"- [ ] {c}" for c in criteria]) if criteria else "- [ ] Implementation complete"

        return f"""**Parent Spec:** [{self.owner}/{product.get('primary_repo')}#{parent_issue.id}]({parent_issue.url})

## Scope
This ticket covers the **{repo_name}** portion of: **{spec.get('title', 'Feature')}**

## Role
{repo_spec.get('role', 'Implementation for this repository')}

## Implementation Details
{repo_spec.get('implementation_details', 'Implement according to parent spec.')}

## Files to Modify
{files_text}

## Acceptance Criteria
{criteria_text}

## Testing Requirements
- Unit tests for new functionality
- Integration tests where applicable
- Manual verification against parent spec criteria

## Context
**Problem:** {spec.get('problem_statement', 'See parent spec')[:500]}

**Technical Approach:** {spec.get('technical_approach', 'See parent spec')[:500]}

---
*Implementation ticket for [{self.owner}/{product.get('primary_repo')}#{parent_issue.id}]({parent_issue.url})*
*Created by Barbossa Spec Generator v{self.VERSION}*
"""

    def _create_distributed_tickets(
        self,
        spec: Dict,
        product: Dict,
        context: Dict[str, Any]
    ) -> Tuple[Optional[Issue], List[Dict]]:
        """
        Create parent spec ticket and child implementation tickets.

        Returns:
            (parent_issue, [{'repo': name, 'number': id, 'url': url}, ...])
        """
        primary_repo = product.get('primary_repo')

        if not primary_repo:
            self.logger.error("No primary_repo configured for product")
            return None, []

        title = spec.get('title', 'Untitled Spec')
        spec_title = f"[SPEC] {title}"

        # Create parent spec first (without child references)
        parent_body = self._generate_parent_spec_body(spec, product)

        try:
            primary_tracker = self._get_issue_tracker(primary_repo)
            parent_issue = primary_tracker.create_issue(
                title=spec_title,
                body=parent_body,
                labels=[self.spec_label, 'product']
            )

            if not parent_issue:
                self.logger.error(f"Failed to create parent spec in {primary_repo}")
                return None, []

            self.logger.info(f"Created parent spec: {parent_issue.url}")

        except Exception as e:
            self.logger.error(f"Error creating parent spec: {e}")
            return None, []

        # Create child tickets in each affected repo
        child_tickets = []
        affected_repos = spec.get('affected_repos', {})

        for repo_name, repo_spec in affected_repos.items():
            # Skip primary repo (parent spec is there)
            if repo_name == primary_repo:
                continue

            # Check if repo is in our configured repos
            if repo_name not in context['repos']:
                self.logger.warning(f"Repo '{repo_name}' not in product repos, skipping child ticket")
                continue

            child_title = f"{title} - {repo_name.replace('-', ' ').title()} Implementation"
            child_body = self._generate_child_ticket_body(spec, repo_name, repo_spec, parent_issue, product)

            try:
                child_tracker = self._get_issue_tracker(repo_name)
                child_issue = child_tracker.create_issue(
                    title=child_title,
                    body=child_body,
                    labels=[self.impl_label, 'spec-child']
                )

                if child_issue:
                    child_tickets.append({
                        'repo': repo_name,
                        'number': child_issue.id,
                        'url': child_issue.url
                    })
                    self.logger.info(f"Created child ticket: {child_issue.url}")
                else:
                    self.logger.warning(f"Failed to create child ticket in {repo_name}")

            except Exception as e:
                self.logger.warning(f"Error creating child ticket in {repo_name}: {e}")

        # Update parent spec with child ticket references
        if child_tickets:
            updated_body = self._generate_parent_spec_body(spec, product, child_tickets)
            self._update_issue_body(primary_repo, parent_issue.id, updated_body)

        return parent_issue, child_tickets

    def _update_issue_body(self, repo_name: str, issue_number: str, body: str):
        """
        Update an issue's body to add child ticket references.

        Note: This uses gh CLI directly (GitHub-specific). For Linear,
        this operation is skipped gracefully since Linear has native
        parent/child relationships that don't need body updates.
        """
        # Check if using Linear - skip update (Linear uses native relationships)
        issue_tracker_config = self.config.get('issue_tracker', {})
        if issue_tracker_config.get('type') == 'linear':
            self.logger.debug("Skipping issue body update for Linear (uses native relationships)")
            return

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(body)
            body_file = f.name

        try:
            result = self._run_cmd(
                f'gh issue edit {issue_number} --repo {self.owner}/{repo_name} --body-file {body_file}',
                timeout=30
            )
            if result is not None:
                self.logger.info(f"Updated issue #{issue_number} with child ticket references")
            else:
                self.logger.warning(f"Could not update issue #{issue_number} with child references (non-critical)")
        finally:
            os.unlink(body_file)

    def generate_for_product(self, product: Dict) -> int:
        """Generate specs for a single product."""
        product_name = product.get('name', 'Unknown')
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"GENERATING SPECS FOR: {product_name}")
        self.logger.info(f"{'='*60}")

        # Aggregate context from all repos
        context = self._aggregate_product_context(product)

        if not context['repos']:
            self.logger.error(f"No repositories loaded for {product_name}")
            return 0

        self.logger.info(f"Loaded {len(context['repos'])} repositories")

        # Build and run the spec generation prompt
        prompt = self._build_spec_prompt(product, context)
        self.logger.info("Calling Claude for spec generation...")

        response = self._analyze_with_claude(prompt)

        if not response:
            self.logger.warning("No valid response from Claude")
            return 0

        specs = response.get('specs', [])
        if not specs:
            reason = response.get('reason', 'No reason provided')
            self.logger.info(f"No specs generated: {reason}")
            return 0

        self.logger.info(f"PASS 1: Claude generated {len(specs)} raw spec(s)")

        # Pass 2: Critique and refine specs for precision
        specs = self._critique_and_refine_specs(specs, product, context)

        if not specs:
            self.logger.info("No specs passed critique review")
            return 0

        self.logger.info(f"Proceeding with {len(specs)} spec(s) after critique")

        # Process each spec
        specs_created = 0
        for spec in specs:
            title = spec.get('title', '')
            if not title:
                self.logger.warning("Spec missing title, skipping")
                continue

            # Check value score
            value_score = spec.get('value_score', 0)
            if value_score < self.min_value_score:
                self.logger.info(f"Skipping low-value spec (score {value_score}): {title}")
                continue

            # Check for duplicates
            if self._is_duplicate_spec(title, context['existing_specs']):
                self.logger.info(f"Skipping duplicate spec: {title}")
                continue

            # Create distributed tickets
            self.logger.info(f"Creating distributed tickets for: {title}")
            parent_issue, child_tickets = self._create_distributed_tickets(spec, product, context)

            if parent_issue:
                specs_created += 1
                self.logger.info(f"Created spec with {len(child_tickets)} child tickets")

                # Send notification
                affected_repos = list(spec.get('affected_repos', {}).keys())
                notify_spec_created(
                    product_name=product.get('name', 'Unknown'),
                    spec_title=title,
                    parent_url=parent_issue.url,
                    child_count=len(child_tickets),
                    affected_repos=affected_repos,
                    value_score=value_score
                )

                # Add to existing specs for deduplication in this run
                context['existing_specs'].append({
                    'title': f"[SPEC] {title}",
                    'url': parent_issue.url
                })

        self.logger.info(f"Created {specs_created} specs for {product_name}")
        return specs_created

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + str(uuid.uuid4())[:8]

    def run(self) -> int:
        """Run spec generation for all enabled products."""
        run_session_id = self._generate_session_id()

        if not self.enabled:
            self.logger.info("Spec Generator is disabled in config. Skipping.")
            return 0

        if not self.products:
            self.logger.info("No products configured. Add 'products' array to repositories.json.")
            return 0

        self.logger.info(f"\n{'#'*60}")
        self.logger.info("BARBOSSA SPEC GENERATOR RUN")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'#'*60}\n")

        # Track run start
        track_run_start("spec_generator", run_session_id, len(self.products))

        total_specs = 0
        errors = 0

        for product in self.products:
            # Apply product filter if specified
            if self.product_filter and product.get('name') != self.product_filter:
                continue

            try:
                specs = self.generate_for_product(product)
                total_specs += specs
            except Exception as e:
                self.logger.error(f"Error generating specs for {product.get('name', 'Unknown')}: {e}")
                errors += 1
                notify_error(
                    agent='spec_generator',
                    error_message=str(e),
                    context=f"Generating specs for product: {product.get('name', 'Unknown')}"
                )

        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"SPEC GENERATION COMPLETE: {total_specs} specs created")
        self.logger.info(f"{'#'*60}\n")

        # Track run end
        track_run_end("spec_generator", run_session_id, success=(errors == 0), pr_created=False)

        # Send run summary notification
        if total_specs > 0 or errors > 0:
            products_processed = len([p for p in self.products
                                      if not self.product_filter or p.get('name') == self.product_filter])
            notify_agent_run_complete(
                agent='spec_generator',
                success=(errors == 0),
                summary=f"Generated {total_specs} product spec(s) across {products_processed} product(s)",
                details={
                    'Specs Created': total_specs,
                    'Products': products_processed,
                    'Errors': errors
                }
            )

        # Ensure all notifications complete before process exits
        wait_for_pending()
        return total_specs


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Barbossa Spec Generator')
    parser.add_argument('--product', help='Generate specs for specific product only')
    args = parser.parse_args()

    generator = BarbossaSpecGenerator(product_filter=args.product)
    generator.run()


if __name__ == "__main__":
    main()
