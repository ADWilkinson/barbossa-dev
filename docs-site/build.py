#!/usr/bin/env python3
"""
Simple docs site builder.
Converts markdown docs to HTML pages for Firebase Hosting.
"""

import os
import re
from pathlib import Path

# HTML template
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Barbossa</title>
    <style>
        :root {{
            --bg: #0d1117;
            --fg: #c9d1d9;
            --accent: #58a6ff;
            --border: #30363d;
            --code-bg: #161b22;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--fg);
            line-height: 1.6;
            padding: 2rem;
            max-width: 900px;
            margin: 0 auto;
        }}
        h1, h2, h3 {{ color: #fff; margin-top: 2rem; margin-bottom: 1rem; }}
        h1 {{ font-size: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
        h2 {{ font-size: 1.5rem; }}
        h3 {{ font-size: 1.2rem; }}
        a {{ color: var(--accent); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        p {{ margin-bottom: 1rem; }}
        ul, ol {{ margin-left: 1.5rem; margin-bottom: 1rem; }}
        li {{ margin-bottom: 0.5rem; }}
        code {{
            background: var(--code-bg);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'SF Mono', Consolas, monospace;
            font-size: 0.9rem;
        }}
        pre {{
            background: var(--code-bg);
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1rem 0;
        }}
        pre code {{ padding: 0; background: none; }}
        .nav {{
            display: flex;
            gap: 1.5rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
            flex-wrap: wrap;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        th, td {{
            text-align: left;
            padding: 0.5rem;
            border-bottom: 1px solid var(--border);
        }}
        blockquote {{
            border-left: 3px solid var(--accent);
            padding-left: 1rem;
            margin: 1rem 0;
            color: #8b949e;
        }}
        footer {{
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
            text-align: center;
            color: #8b949e;
        }}
    </style>
</head>
<body>
    <nav class="nav">
        <a href="/">Home</a>
        <a href="https://github.com/ADWilkinson/barbossa-engineer">GitHub</a>
        <a href="/quickstart.html">Quick Start</a>
        <a href="/configuration.html">Configuration</a>
        <a href="/agents.html">Agents</a>
        <a href="/troubleshooting.html">Troubleshooting</a>
        <a href="/faq.html">FAQ</a>
    </nav>

    <div class="content">
        {content}
    </div>

    <footer>
        <p>Barbossa is open source under the MIT License</p>
        <p><a href="https://github.com/ADWilkinson/barbossa-engineer">GitHub</a></p>
    </footer>
</body>
</html>
"""


def markdown_to_html(md: str) -> str:
    """Simple markdown to HTML converter."""
    html = md

    # Code blocks
    html = re.sub(
        r'```(\w*)\n(.*?)```',
        lambda m: f'<pre><code class="language-{m.group(1)}">{m.group(2).strip()}</code></pre>',
        html,
        flags=re.DOTALL
    )

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

    # Lists (simple)
    lines = html.split('\n')
    in_list = False
    result = []
    for line in lines:
        if line.strip().startswith('- '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append(f'<li>{line.strip()[2:]}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    if in_list:
        result.append('</ul>')
    html = '\n'.join(result)

    # Paragraphs (simple - wrap lines that aren't already HTML)
    lines = html.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<') and not stripped.startswith('|'):
            result.append(f'<p>{stripped}</p>')
        else:
            result.append(line)
    html = '\n'.join(result)

    return html


def build_docs():
    """Build docs from markdown files."""
    docs_dir = Path(__file__).parent.parent / 'docs'
    public_dir = Path(__file__).parent / 'public'

    print(f"Building docs from {docs_dir} to {public_dir}")

    for md_file in docs_dir.glob('*.md'):
        print(f"  Processing {md_file.name}")

        with open(md_file, 'r') as f:
            content = f.read()

        # Extract title from first # header
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else md_file.stem.title()

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
