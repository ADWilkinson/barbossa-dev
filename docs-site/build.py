#!/usr/bin/env python3
"""
Barbossa docs site builder.
Converts markdown docs to HTML with ultra-minimal design.
"""

import os
import re
from pathlib import Path

# Ultra-minimal HTML template
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --ink: #1a1a1a;
            --paper: #fafafa;
            --ghost: #999;
            --line: #e5e5e5;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --ink: #e5e5e5;
                --paper: #111;
                --ghost: #666;
                --line: #333;
            }}
        }}

        body {{
            font: 16px/1.7 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
            background: var(--paper);
            color: var(--ink);
            max-width: 680px;
            margin: 0 auto;
            padding: 4rem 2rem;
        }}

        /* Navigation - just links */
        nav {{
            margin-bottom: 4rem;
            font-size: 14px;
        }}
        nav a {{
            color: var(--ghost);
            text-decoration: none;
            margin-right: 1.5rem;
        }}
        nav a:hover {{
            color: var(--ink);
        }}
        nav .logo {{
            display: inline-block;
            width: 16px;
            height: 16px;
            vertical-align: middle;
            margin-right: 0.25rem;
        }}

        /* Typography */
        h1 {{
            font-size: 14px;
            font-weight: 400;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 3rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--line);
        }}

        h2 {{
            font-size: 14px;
            font-weight: 600;
            margin: 3rem 0 1.5rem;
        }}

        h3 {{
            font-size: 14px;
            font-weight: 400;
            color: var(--ghost);
            margin: 2rem 0 1rem;
        }}

        p {{
            margin-bottom: 1.5rem;
        }}

        a {{
            color: var(--ink);
            text-decoration: underline;
            text-underline-offset: 2px;
        }}

        /* Lists */
        ul, ol {{
            margin: 0 0 1.5rem 1.5rem;
        }}
        li {{
            margin-bottom: 0.5rem;
        }}

        /* Code */
        code {{
            font-family: inherit;
            background: var(--line);
            padding: 0.1em 0.3em;
            font-size: 0.9em;
        }}

        pre {{
            background: var(--line);
            padding: 1.5rem;
            margin: 1.5rem 0;
            overflow-x: auto;
            font-size: 13px;
            line-height: 1.5;
        }}

        pre code {{
            background: none;
            padding: 0;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            font-size: 14px;
        }}
        th, td {{
            text-align: left;
            padding: 0.75rem 1rem 0.75rem 0;
            border-bottom: 1px solid var(--line);
        }}
        th {{
            font-weight: 600;
        }}

        /* Blockquotes */
        blockquote {{
            border-left: 2px solid var(--line);
            padding-left: 1rem;
            margin: 1.5rem 0;
            color: var(--ghost);
        }}

        /* Horizontal rules */
        hr {{
            border: none;
            border-top: 1px solid var(--line);
            margin: 3rem 0;
        }}

        /* Footer */
        footer {{
            margin-top: 6rem;
            padding-top: 2rem;
            border-top: 1px solid var(--line);
            font-size: 13px;
            color: var(--ghost);
        }}

        /* Hero for home page */
        .hero {{
            margin: 4rem 0;
        }}
        .hero h1 {{
            font-size: 14px;
            border: none;
            padding: 0;
            margin-bottom: 1rem;
        }}
        .hero p {{
            font-size: 24px;
            font-weight: 300;
            line-height: 1.4;
            margin-bottom: 0;
        }}

        /* Features grid */
        .features {{
            display: grid;
            gap: 2rem;
            margin: 3rem 0;
        }}
        .feature {{
            padding: 1.5rem 0;
            border-top: 1px solid var(--line);
        }}
        .feature h3 {{
            margin: 0 0 0.5rem;
            font-weight: 600;
            color: var(--ink);
        }}
        .feature p {{
            margin: 0;
            color: var(--ghost);
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <nav>
        <a href="/">_b</a>
        <a href="/quickstart.html">start</a>
        <a href="/configuration.html">config</a>
        <a href="/agents.html">agents</a>
        <a href="/faq.html">faq</a>
        <a href="https://github.com/ADWilkinson/barbossa-dev">github</a>
    </nav>

    <main>
        {content}
    </main>

    <footer>
        MIT License · <a href="https://github.com/ADWilkinson/barbossa-dev">Source</a>
    </footer>
</body>
</html>
"""

# Home page template
HOME_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Barbossa</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --ink: #1a1a1a;
            --paper: #fafafa;
            --ghost: #999;
            --line: #e5e5e5;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --ink: #e5e5e5;
                --paper: #111;
                --ghost: #666;
                --line: #333;
            }}
        }}

        body {{
            font: 16px/1.7 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
            background: var(--paper);
            color: var(--ink);
            max-width: 680px;
            margin: 0 auto;
            padding: 4rem 2rem;
        }}

        nav {{
            margin-bottom: 4rem;
            font-size: 14px;
        }}
        nav a {{
            color: var(--ghost);
            text-decoration: none;
            margin-right: 1.5rem;
        }}
        nav a:hover {{
            color: var(--ink);
        }}
        nav .logo {{
            display: inline-block;
            width: 16px;
            height: 16px;
            vertical-align: middle;
            margin-right: 0.25rem;
        }}

        a {{
            color: var(--ink);
            text-decoration: underline;
            text-underline-offset: 2px;
        }}

        .hero {{
            margin: 2rem 0 4rem;
        }}
        .hero small {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--ghost);
        }}
        .hero h1 {{
            font-size: 32px;
            font-weight: 300;
            line-height: 1.3;
            margin: 1rem 0;
        }}

        .cta {{
            margin: 3rem 0;
            padding: 2rem;
            background: var(--line);
        }}
        .cta code {{
            display: block;
            font-size: 14px;
            background: none;
        }}

        .features {{
            margin: 4rem 0;
        }}
        .feature {{
            padding: 1.5rem 0;
            border-top: 1px solid var(--line);
        }}
        .feature:last-child {{
            border-bottom: 1px solid var(--line);
        }}
        .feature h3 {{
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        .feature p {{
            font-size: 14px;
            color: var(--ghost);
            margin: 0;
        }}

        footer {{
            margin-top: 6rem;
            padding-top: 2rem;
            border-top: 1px solid var(--line);
            font-size: 13px;
            color: var(--ghost);
        }}
    </style>
</head>
<body>
    <nav>
        <a href="/">_b</a>
        <a href="/quickstart.html">start</a>
        <a href="/configuration.html">config</a>
        <a href="/agents.html">agents</a>
        <a href="/faq.html">faq</a>
        <a href="https://github.com/ADWilkinson/barbossa-dev">github</a>
    </nav>

    <main>
        <div class="hero">
            <small>v1.1.0</small>
            <h1>AI engineers that ship code while you sleep</h1>
        </div>

        <p>Barbossa is a team of AI agents that work on your codebase autonomously.
        They find issues, write code, create PRs, and review each other's work.</p>

        <div class="cta">
            <code>docker pull ghcr.io/adwilkinson/barbossa-dev:latest</code>
        </div>

        <div class="features">
            <div class="feature">
                <h3>Engineer</h3>
                <p>Picks tasks from backlog, implements features, creates pull requests</p>
            </div>
            <div class="feature">
                <h3>Tech Lead</h3>
                <p>Reviews PRs with strict quality criteria, merges or requests changes</p>
            </div>
            <div class="feature">
                <h3>Discovery</h3>
                <p>Scans codebase for TODOs, missing tests, accessibility issues</p>
            </div>
            <div class="feature">
                <h3>Product Manager</h3>
                <p>Reads your docs, proposes features that align with product vision</p>
            </div>
            <div class="feature">
                <h3>Auditor</h3>
                <p>Reviews system health, identifies patterns, generates insights</p>
            </div>
        </div>

        <p><a href="/quickstart.html">Get started →</a></p>
    </main>

    <footer>
        MIT License · <a href="https://github.com/ADWilkinson/barbossa-dev">Source</a>
    </footer>
</body>
</html>
"""


def markdown_to_html(md: str) -> str:
    """Simple markdown to HTML converter."""
    html = md

    # Protect code blocks by replacing with placeholders
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(f'<pre><code>{match.group(2).strip()}</code></pre>')
        return f'[[CODE_BLOCK_{len(code_blocks) - 1}]]'

    html = re.sub(
        r'```(\w*)\n(.*?)```',
        save_code_block,
        html,
        flags=re.DOTALL
    )

    # Horizontal rules (must be before other processing)
    html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)

    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Blockquotes
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    # Tables
    def convert_table(match):
        lines = match.group(0).strip().split('\n')
        table_html = '<table>'
        for i, line in enumerate(lines):
            if '---' in line:
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            tag = 'th' if i == 0 else 'td'
            row = ''.join(f'<{tag}>{c}</{tag}>' for c in cells)
            table_html += f'<tr>{row}</tr>'
        table_html += '</table>'
        return table_html

    html = re.sub(r'(\|.+\|\n)+', convert_table, html)

    # Lists
    lines = html.split('\n')
    in_list = False
    result = []
    for line in lines:
        if line.strip().startswith('- '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append(f'<li>{line.strip()[2:]}</li>')
        elif re.match(r'^\d+\. ', line.strip()):
            if not in_list:
                result.append('<ol>')
                in_list = True
            list_content = re.sub(r'^\d+\. ', '', line.strip())
            result.append(f'<li>{list_content}</li>')
        else:
            if in_list:
                result.append('</ul>' if '</li>' in result[-1] else '</ol>')
                in_list = False
            result.append(line)
    if in_list:
        result.append('</ul>')
    html = '\n'.join(result)

    # Paragraphs (skip empty lines, HTML tags, and code block placeholders)
    lines = html.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<') and not stripped.startswith('|') and not stripped.startswith('[[CODE_BLOCK_'):
            result.append(f'<p>{stripped}</p>')
        else:
            result.append(line)
    html = '\n'.join(result)

    # Restore code blocks
    for i, block in enumerate(code_blocks):
        html = html.replace(f'[[CODE_BLOCK_{i}]]', block)

    return html


def build_docs():
    """Build docs from markdown files."""
    docs_dir = Path(__file__).parent.parent / 'docs'
    public_dir = Path(__file__).parent / 'public'

    public_dir.mkdir(exist_ok=True)

    print(f"Building docs from {docs_dir} to {public_dir}")

    # Copy home page from source
    import shutil
    shutil.copy(Path(__file__).parent / 'index.html', public_dir / 'index.html')
    print("  -> index.html")

    # Skip internal docs
    skip_files = {'TRANSITION_GUIDE.md', 'SYSTEM_PROMPTS.md'}

    for md_file in docs_dir.glob('*.md'):
        if md_file.name in skip_files:
            continue
        print(f"  Processing {md_file.name}")

        with open(md_file, 'r') as f:
            content = f.read()

        # Extract title from first # header
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else md_file.stem.replace('_', ' ').title()

        # Convert to HTML
        html_content = markdown_to_html(content)

        # Apply template
        html = TEMPLATE.format(title=title, content=html_content)

        # Write output
        output_file = public_dir / f"{md_file.stem}.html"
        with open(output_file, 'w') as f:
            f.write(html)

        print(f"    -> {output_file.name}")

    print("Done!")


if __name__ == '__main__':
    build_docs()
