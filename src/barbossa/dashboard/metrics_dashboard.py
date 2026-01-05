#!/usr/bin/env python3
"""
Barbossa Metrics Dashboard Generator

Generates a static HTML dashboard from collected metrics.
Uses Chart.js for visualization, served as a standalone HTML file.

Usage:
    python -m barbossa.dashboard.metrics_dashboard
    # or
    barbossa metrics dashboard

The generated dashboard includes:
- Agent success rates (pie chart)
- Cost over time (line chart)
- Duration by agent (bar chart)
- Error breakdown (doughnut chart)
- Key metrics summary cards
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from barbossa.utils.metrics import get_metrics, get_metrics_summary


def generate_dashboard_html(days: int = 7, output_path: Optional[Path] = None) -> Path:
    """
    Generate a static HTML dashboard from collected metrics.

    Args:
        days: Number of days of metrics to include
        output_path: Optional custom output path for the dashboard

    Returns:
        Path to the generated HTML file
    """
    # Get metrics data
    metrics = get_metrics(days=days)
    summary = get_metrics_summary(days=days)

    # Determine output path
    if output_path is None:
        data_dir = Path(os.environ.get('BARBOSSA_DIR', '/app')) / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        output_path = data_dir / 'metrics_dashboard.html'

    # Prepare chart data
    chart_data = _prepare_chart_data(metrics, summary, days)

    # Generate HTML
    html = _generate_html(summary, chart_data, days)

    # Write to file
    with open(output_path, 'w') as f:
        f.write(html)

    return output_path


def _prepare_chart_data(metrics: List[Dict], summary: Dict, days: int) -> Dict[str, Any]:
    """Prepare data for Chart.js charts."""
    # Success rate by agent
    by_agent = summary.get('by_agent', {})
    agent_labels = list(by_agent.keys())
    agent_success_rates = [
        round(a['successes'] / a['runs'] * 100, 1) if a['runs'] > 0 else 0
        for a in by_agent.values()
    ]
    agent_run_counts = [a['runs'] for a in by_agent.values()]
    agent_costs = [round(a['cost_usd'], 2) for a in by_agent.values()]

    # Cost over time (daily buckets)
    daily_costs = {}
    daily_runs = {}
    for m in metrics:
        ts = m.get('timestamp', '')[:10]  # YYYY-MM-DD
        if ts:
            daily_costs[ts] = daily_costs.get(ts, 0) + m.get('cost_usd', 0)
            daily_runs[ts] = daily_runs.get(ts, 0) + 1

    # Sort by date
    sorted_dates = sorted(daily_costs.keys())
    cost_timeline_labels = sorted_dates
    cost_timeline_values = [round(daily_costs.get(d, 0), 2) for d in sorted_dates]
    runs_timeline_values = [daily_runs.get(d, 0) for d in sorted_dates]

    # Error breakdown
    error_breakdown = summary.get('error_breakdown', {})
    error_labels = list(error_breakdown.keys())
    error_counts = list(error_breakdown.values())

    # Duration by agent
    agent_avg_durations = [
        round(a['duration_seconds'] / a['runs'], 1) if a['runs'] > 0 else 0
        for a in by_agent.values()
    ]

    # By repo stats
    by_repo = summary.get('by_repo', {})
    repo_labels = list(by_repo.keys())
    repo_run_counts = [r['runs'] for r in by_repo.values()]
    repo_success_rates = [
        round(r['successes'] / r['runs'] * 100, 1) if r['runs'] > 0 else 0
        for r in by_repo.values()
    ]

    return {
        'agent_labels': agent_labels,
        'agent_success_rates': agent_success_rates,
        'agent_run_counts': agent_run_counts,
        'agent_costs': agent_costs,
        'agent_avg_durations': agent_avg_durations,
        'cost_timeline_labels': cost_timeline_labels,
        'cost_timeline_values': cost_timeline_values,
        'runs_timeline_values': runs_timeline_values,
        'error_labels': error_labels,
        'error_counts': error_counts,
        'repo_labels': repo_labels,
        'repo_run_counts': repo_run_counts,
        'repo_success_rates': repo_success_rates,
    }


def _generate_html(summary: Dict, chart_data: Dict, days: int) -> str:
    """Generate the complete HTML dashboard."""
    generated_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Barbossa Metrics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #f0f6fc;
            --text-secondary: #8b949e;
            --border-color: #30363d;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-orange: #d29922;
            --accent-red: #f85149;
            --accent-purple: #a371f7;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }}

        h1 {{
            font-size: 1.8rem;
            font-weight: 600;
        }}

        .header-meta {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .metric-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
        }}

        .metric-card h3 {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}

        .metric-value {{
            font-size: 2rem;
            font-weight: 600;
        }}

        .metric-value.green {{ color: var(--accent-green); }}
        .metric-value.blue {{ color: var(--accent-blue); }}
        .metric-value.orange {{ color: var(--accent-orange); }}
        .metric-value.red {{ color: var(--accent-red); }}
        .metric-value.purple {{ color: var(--accent-purple); }}

        .metric-subtext {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}

        @media (max-width: 900px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .chart-container {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 20px;
        }}

        .chart-container h2 {{
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 15px;
            color: var(--text-primary);
        }}

        .chart-wrapper {{
            position: relative;
            height: 300px;
        }}

        .no-data {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 200px;
            color: var(--text-secondary);
        }}

        footer {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
        }}

        footer a {{
            color: var(--accent-blue);
            text-decoration: none;
        }}

        footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Barbossa Metrics Dashboard</h1>
            <div class="header-meta">
                <div>Period: Last {days} days</div>
                <div>Generated: {generated_at}</div>
            </div>
        </header>

        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Runs</h3>
                <div class="metric-value blue">{summary.get('total_runs', 0)}</div>
                <div class="metric-subtext">{summary.get('successful_runs', 0)} successful, {summary.get('failed_runs', 0)} failed</div>
            </div>
            <div class="metric-card">
                <h3>Success Rate</h3>
                <div class="metric-value {'green' if summary.get('success_rate', 0) >= 80 else 'orange' if summary.get('success_rate', 0) >= 60 else 'red'}">{summary.get('success_rate', 0)}%</div>
                <div class="metric-subtext">Target: 80%+</div>
            </div>
            <div class="metric-card">
                <h3>Total Cost</h3>
                <div class="metric-value purple">${summary.get('total_cost_usd', 0):.2f}</div>
                <div class="metric-subtext">~${summary.get('avg_cost_per_run', 0):.4f} per run</div>
            </div>
            <div class="metric-card">
                <h3>Total Tokens</h3>
                <div class="metric-value blue">{summary.get('total_tokens', 0):,}</div>
                <div class="metric-subtext">Input + Output</div>
            </div>
            <div class="metric-card">
                <h3>Avg Duration</h3>
                <div class="metric-value orange">{summary.get('avg_duration_seconds', 0):.1f}s</div>
                <div class="metric-subtext">Per agent run</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <h2>Cost Over Time (Daily)</h2>
                <div class="chart-wrapper">
                    {'<div class="no-data">No data available</div>' if not chart_data['cost_timeline_labels'] else '<canvas id="costChart"></canvas>'}
                </div>
            </div>

            <div class="chart-container">
                <h2>Runs Over Time (Daily)</h2>
                <div class="chart-wrapper">
                    {'<div class="no-data">No data available</div>' if not chart_data['runs_timeline_values'] else '<canvas id="runsChart"></canvas>'}
                </div>
            </div>

            <div class="chart-container">
                <h2>Success Rate by Agent</h2>
                <div class="chart-wrapper">
                    {'<div class="no-data">No data available</div>' if not chart_data['agent_labels'] else '<canvas id="agentSuccessChart"></canvas>'}
                </div>
            </div>

            <div class="chart-container">
                <h2>Cost by Agent</h2>
                <div class="chart-wrapper">
                    {'<div class="no-data">No data available</div>' if not chart_data['agent_labels'] else '<canvas id="agentCostChart"></canvas>'}
                </div>
            </div>

            <div class="chart-container">
                <h2>Avg Duration by Agent (seconds)</h2>
                <div class="chart-wrapper">
                    {'<div class="no-data">No data available</div>' if not chart_data['agent_labels'] else '<canvas id="durationChart"></canvas>'}
                </div>
            </div>

            <div class="chart-container">
                <h2>Error Breakdown</h2>
                <div class="chart-wrapper">
                    {'<div class="no-data">No errors in this period</div>' if not chart_data['error_labels'] else '<canvas id="errorChart"></canvas>'}
                </div>
            </div>
        </div>

        <footer>
            Barbossa Metrics Dashboard &bull;
            <a href="https://github.com/ADWilkinson/barbossa-dev" target="_blank">GitHub</a>
        </footer>
    </div>

    <script>
        // Chart.js defaults for dark theme
        Chart.defaults.color = '#8b949e';
        Chart.defaults.borderColor = '#30363d';

        const colors = {{
            blue: '#58a6ff',
            green: '#3fb950',
            orange: '#d29922',
            red: '#f85149',
            purple: '#a371f7',
            pink: '#db61a2',
            cyan: '#39c5cf'
        }};

        const colorArray = [colors.blue, colors.green, colors.orange, colors.purple, colors.pink, colors.cyan, colors.red];

        // Cost over time chart
        {_generate_line_chart_js('costChart', chart_data['cost_timeline_labels'], chart_data['cost_timeline_values'], 'Cost ($)', 'colors.purple')}

        // Runs over time chart
        {_generate_line_chart_js('runsChart', chart_data['runs_timeline_values'] and chart_data['cost_timeline_labels'], chart_data['runs_timeline_values'], 'Runs', 'colors.blue')}

        // Agent success rate chart
        {_generate_bar_chart_js('agentSuccessChart', chart_data['agent_labels'], chart_data['agent_success_rates'], 'Success Rate (%)')}

        // Agent cost chart
        {_generate_bar_chart_js('agentCostChart', chart_data['agent_labels'], chart_data['agent_costs'], 'Cost ($)', 'colors.purple')}

        // Duration chart
        {_generate_bar_chart_js('durationChart', chart_data['agent_labels'], chart_data['agent_avg_durations'], 'Duration (s)', 'colors.orange')}

        // Error chart
        {_generate_doughnut_chart_js('errorChart', chart_data['error_labels'], chart_data['error_counts'])}
    </script>
</body>
</html>'''


def _generate_line_chart_js(chart_id: str, labels: List[str], values: List, label: str, color: str = 'colors.blue') -> str:
    """Generate JavaScript for a line chart."""
    if not labels or not values:
        return ''

    return f'''
        if (document.getElementById('{chart_id}')) {{
            new Chart(document.getElementById('{chart_id}'), {{
                type: 'line',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: '{label}',
                        data: {json.dumps(values)},
                        borderColor: {color},
                        backgroundColor: {color} + '33',
                        fill: true,
                        tension: 0.3
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }}
                    }},
                    scales: {{
                        y: {{ beginAtZero: true }}
                    }}
                }}
            }});
        }}
    '''


def _generate_bar_chart_js(chart_id: str, labels: List[str], values: List, label: str, color: str = 'colors.blue') -> str:
    """Generate JavaScript for a bar chart."""
    if not labels or not values:
        return ''

    return f'''
        if (document.getElementById('{chart_id}')) {{
            new Chart(document.getElementById('{chart_id}'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        label: '{label}',
                        data: {json.dumps(values)},
                        backgroundColor: colorArray.slice(0, {len(labels)}),
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }}
                    }},
                    scales: {{
                        y: {{ beginAtZero: true }}
                    }}
                }}
            }});
        }}
    '''


def _generate_doughnut_chart_js(chart_id: str, labels: List[str], values: List) -> str:
    """Generate JavaScript for a doughnut chart."""
    if not labels or not values:
        return ''

    return f'''
        if (document.getElementById('{chart_id}')) {{
            new Chart(document.getElementById('{chart_id}'), {{
                type: 'doughnut',
                data: {{
                    labels: {json.dumps(labels)},
                    datasets: [{{
                        data: {json.dumps(values)},
                        backgroundColor: colorArray.slice(0, {len(labels)})
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'right'
                        }}
                    }}
                }}
            }});
        }}
    '''


def main():
    """Main entry point for dashboard generation."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate Barbossa Metrics Dashboard')
    parser.add_argument('--days', type=int, default=7, help='Number of days to include (default: 7)')
    parser.add_argument('--output', type=str, help='Output path for HTML file')
    parser.add_argument('--open', action='store_true', help='Open dashboard in browser after generation')

    args = parser.parse_args()

    output_path = Path(args.output) if args.output else None
    result_path = generate_dashboard_html(days=args.days, output_path=output_path)

    print(f"Dashboard generated: {result_path}")

    if args.open:
        import webbrowser
        webbrowser.open(f'file://{result_path}')


if __name__ == '__main__':
    main()
