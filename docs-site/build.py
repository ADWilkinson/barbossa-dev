#!/usr/bin/env python3
"""
Barbossa docs site builder.
Converts markdown docs to HTML with enhanced minimal design.
"""

import os
import re
from pathlib import Path

# Enhanced HTML template with syntax highlighting and improved navigation
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Barbossa</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --ink: #1a1a1a;
            --paper: #fafafa;
            --ghost: #888;
            --line: #e5e5e5;
            --accent: #6366f1;
            --accent-dim: rgba(99, 102, 241, 0.1);
            --code-bg: #2d2d2d;
            --success: #22c55e;
            --warning: #f59e0b;
            --info: #3b82f6;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --ink: #e5e5e5;
                --paper: #0f0f0f;
                --ghost: #888;
                --line: #2a2a2a;
                --accent: #818cf8;
                --accent-dim: rgba(129, 140, 248, 0.1);
            }}
        }}

        html {{ scroll-behavior: smooth; }}

        body {{
            font: 15px/1.7 'SF Mono', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
            background: var(--paper);
            color: var(--ink);
            max-width: 720px;
            margin: 0 auto;
            padding: 3rem 2rem 6rem;
        }}

        /* Navigation */
        nav {{
            position: sticky;
            top: 0;
            background: var(--paper);
            padding: 1rem 0 1.5rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--line);
            font-size: 13px;
            z-index: 100;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        nav a {{
            color: var(--ghost);
            text-decoration: none !important;
            padding: 0.4rem 0.7rem;
            border-radius: 4px;
            transition: all 0.15s;
        }}
        nav a:hover {{
            color: var(--ink);
            background: var(--line);
            text-decoration: none !important;
        }}
        nav a.active {{
            color: var(--accent);
            background: var(--accent-dim);
        }}
        nav .logo {{
            font-weight: 600;
            color: var(--ink);
            margin-right: auto;
            padding-left: 0;
        }}
        nav .logo:hover {{
            background: none !important;
            color: var(--accent);
        }}

        /* Mobile nav toggle */
        .nav-toggle {{
            display: none;
            background: none;
            border: none;
            color: var(--ink);
            cursor: pointer;
            padding: 0.5rem;
            font-size: 18px;
        }}
        @media (max-width: 600px) {{
            nav {{
                flex-wrap: wrap;
            }}
            nav .logo {{
                margin-right: 0;
            }}
            .nav-toggle {{
                display: block;
                margin-left: auto;
            }}
            nav .nav-links {{
                display: none;
                width: 100%;
                flex-direction: column;
                gap: 0.25rem;
                padding-top: 1rem;
            }}
            nav .nav-links.open {{
                display: flex;
            }}
            nav .nav-links a {{
                width: 100%;
            }}
        }}
        @media (min-width: 601px) {{
            nav .nav-links {{
                display: flex;
                gap: 0.25rem;
            }}
        }}

        /* Typography */
        h1 {{
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--ghost);
            margin-bottom: 2.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--line);
        }}

        h2 {{
            font-size: 15px;
            font-weight: 600;
            margin: 3rem 0 1.5rem;
            padding-top: 1rem;
        }}

        h3 {{
            font-size: 14px;
            font-weight: 500;
            color: var(--ink);
            margin: 2rem 0 1rem;
        }}

        p {{
            margin-bottom: 1.5rem;
        }}

        a {{
            color: var(--accent);
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}

        strong {{
            font-weight: 600;
        }}

        /* Lists */
        ul, ol {{
            margin: 0 0 1.5rem 1.5rem;
        }}
        li {{
            margin-bottom: 0.5rem;
        }}
        li::marker {{
            color: var(--ghost);
        }}

        /* Inline code */
        code:not([class*="language-"]) {{
            font-family: inherit;
            background: var(--line);
            padding: 0.15em 0.4em;
            border-radius: 3px;
            font-size: 0.9em;
        }}

        /* Code blocks with Prism */
        pre[class*="language-"] {{
            margin: 1.5rem 0;
            border-radius: 6px;
            font-size: 13px;
            line-height: 1.6;
        }}
        pre[class*="language-"] code {{
            font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
        }}

        /* Fallback for code blocks without language */
        pre:not([class*="language-"]) {{
            background: var(--code-bg);
            color: #ccc;
            padding: 1.25rem 1.5rem;
            margin: 1.5rem 0;
            overflow-x: auto;
            font-size: 13px;
            line-height: 1.6;
            border-radius: 6px;
        }}
        pre:not([class*="language-"]) code {{
            background: none;
            padding: 0;
            color: inherit;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            font-size: 13px;
        }}
        th, td {{
            text-align: left;
            padding: 0.75rem 1rem 0.75rem 0;
            border-bottom: 1px solid var(--line);
        }}
        th {{
            font-weight: 600;
            color: var(--ghost);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        /* Blockquotes / Callouts */
        blockquote {{
            border-left: 3px solid var(--accent);
            padding: 0.75rem 1rem;
            margin: 1.5rem 0;
            background: var(--accent-dim);
            border-radius: 0 6px 6px 0;
        }}
        blockquote p {{
            margin: 0;
        }}

        /* Tip/Warning/Note callouts */
        .callout {{
            padding: 1rem 1.25rem;
            margin: 1.5rem 0;
            border-radius: 6px;
            border-left: 3px solid;
        }}
        .callout-tip {{
            background: rgba(34, 197, 94, 0.08);
            border-color: var(--success);
        }}
        .callout-warning {{
            background: rgba(245, 158, 11, 0.08);
            border-color: var(--warning);
        }}
        .callout-info {{
            background: rgba(59, 130, 246, 0.08);
            border-color: var(--info);
        }}
        .callout strong {{
            display: block;
            margin-bottom: 0.25rem;
        }}

        /* Horizontal rules */
        hr {{
            border: none;
            border-top: 1px solid var(--line);
            margin: 3rem 0;
        }}

        /* Table of Contents */
        .toc {{
            background: var(--line);
            padding: 1.25rem 1.5rem;
            border-radius: 6px;
            margin: 2rem 0 3rem;
        }}
        .toc-title {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--ghost);
            margin-bottom: 0.75rem;
        }}
        .toc ul {{
            margin: 0;
            list-style: none;
        }}
        .toc li {{
            margin: 0.35rem 0;
        }}
        .toc a {{
            color: var(--ink);
            font-size: 13px;
        }}

        /* Footer */
        footer {{
            margin-top: 6rem;
            padding-top: 2rem;
            border-top: 1px solid var(--line);
            font-size: 12px;
            color: var(--ghost);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        footer a {{
            color: var(--ghost);
        }}
        footer a:hover {{
            color: var(--ink);
        }}

        /* Smooth anchor scrolling offset for sticky nav */
        h2[id], h3[id] {{
            scroll-margin-top: 80px;
        }}
    </style>
</head>
<body>
    <nav>
        <a href="/" class="logo">barbossa</a>
        <button class="nav-toggle" onclick="document.querySelector('.nav-links').classList.toggle('open')" aria-label="Toggle navigation">☰</button>
        <div class="nav-links">
            <a href="/quickstart.html" class="{active_quickstart}">quickstart</a>
            <a href="/configuration.html" class="{active_configuration}">config</a>
            <a href="/agents.html" class="{active_agents}">agents</a>
            <a href="/architecture.html" class="{active_architecture}">architecture</a>
            <a href="/examples.html" class="{active_examples}">examples</a>
            <a href="/faq.html" class="{active_faq}">faq</a>
            <a href="https://github.com/ADWilkinson/barbossa-dev" target="_blank">github ↗</a>
        </div>
    </nav>

    <main>
        {toc}
        {content}
    </main>

    <footer>
        <span>MIT License</span>
        <a href="https://github.com/ADWilkinson/barbossa-dev">View on GitHub</a>
    </footer>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-yaml.min.js"></script>
</body>
</html>
"""


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')


def markdown_to_html(md: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Simple markdown to HTML converter.
    Returns (html, toc_items) where toc_items is [(title, id), ...]
    """
    html = md
    toc_items = []

    # Protect code blocks by replacing with placeholders
    code_blocks = []
    def save_code_block(match):
        lang = match.group(1) or 'text'
        code = match.group(2).strip()
        # Escape HTML in code
        code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        code_blocks.append(f'<pre class="language-{lang}"><code class="language-{lang}">{code}</code></pre>')
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

    # Headers with IDs for linking
    def header_with_id(match):
        level = len(match.group(1))
        text = match.group(2)
        slug = slugify(text)
        if level == 2:
            toc_items.append((text, slug))
        return f'<h{level} id="{slug}">{text}</h{level}>'

    html = re.sub(r'^(#{1,3}) (.+)$', header_with_id, html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Blockquotes
    html = re.sub(r'^> (.+)$', r'<blockquote><p>\1</p></blockquote>', html, flags=re.MULTILINE)

    # Callouts: **Tip:** text -> callout box
    html = re.sub(
        r'<p><strong>(Tip|Note|Info):</strong>\s*(.+?)</p>',
        r'<div class="callout callout-tip"><strong>\1</strong>\2</div>',
        html
    )
    html = re.sub(
        r'<p><strong>(Warning|Caution):</strong>\s*(.+?)</p>',
        r'<div class="callout callout-warning"><strong>\1</strong>\2</div>',
        html
    )

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
    list_type = None
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- '):
            if not in_list or list_type != 'ul':
                if in_list:
                    result.append(f'</{list_type}>')
                result.append('<ul>')
                in_list = True
                list_type = 'ul'
            result.append(f'<li>{stripped[2:]}</li>')
        elif re.match(r'^\d+\. ', stripped):
            if not in_list or list_type != 'ol':
                if in_list:
                    result.append(f'</{list_type}>')
                result.append('<ol>')
                in_list = True
                list_type = 'ol'
            list_content = re.sub(r'^\d+\. ', '', stripped)
            result.append(f'<li>{list_content}</li>')
        else:
            if in_list:
                result.append(f'</{list_type}>')
                in_list = False
                list_type = None
            result.append(line)
    if in_list:
        result.append(f'</{list_type}>')
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

    return html, toc_items


def generate_toc(items: list[tuple[str, str]]) -> str:
    """Generate table of contents HTML."""
    if len(items) < 3:
        return ''  # Don't show TOC for short pages

    toc = '<div class="toc"><div class="toc-title">On this page</div><ul>'
    for title, slug in items:
        toc += f'<li><a href="#{slug}">{title}</a></li>'
    toc += '</ul></div>'
    return toc


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

    # Build all docs and track page names for active states
    all_pages = []
    for md_file in docs_dir.glob('*.md'):
        if md_file.name not in skip_files:
            all_pages.append(md_file.stem)

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
        html_content, toc_items = markdown_to_html(content)
        toc_html = generate_toc(toc_items)

        # Generate active states for navigation
        active_states = {}
        for page in ['quickstart', 'configuration', 'agents', 'architecture', 'examples', 'faq', 'troubleshooting', 'firebase']:
            active_states[f'active_{page}'] = 'active' if md_file.stem == page else ''

        # Apply template
        html = TEMPLATE.format(
            title=title,
            content=html_content,
            toc=toc_html,
            **active_states
        )

        # Write output
        output_file = public_dir / f"{md_file.stem}.html"
        with open(output_file, 'w') as f:
            f.write(html)

        print(f"    -> {output_file.name}")

    print("Done!")


if __name__ == '__main__':
    build_docs()
