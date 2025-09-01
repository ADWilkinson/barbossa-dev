#!/bin/bash
# Performance monitoring and optimization check

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "BARBOSSA PERFORMANCE CHECK"
echo "Started: $(date)"
echo "================================================"

# Collect performance metrics
python3 - <<'EOF'
import json
import psutil
import subprocess
from datetime import datetime
from pathlib import Path

metrics = {
    'timestamp': datetime.now().isoformat(),
    'system': {},
    'processes': {},
    'recommendations': []
}

# System metrics
metrics['system'] = {
    'cpu_percent': psutil.cpu_percent(interval=1),
    'memory_percent': psutil.virtual_memory().percent,
    'disk_usage_percent': psutil.disk_usage('/').percent,
    'network_connections': len(psutil.net_connections()),
    'process_count': len(psutil.pids())
}

# Top CPU consuming processes
processes = []
for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
    try:
        pinfo = proc.info
        if pinfo['cpu_percent'] > 1:
            processes.append(pinfo)
    except:
        pass

processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
metrics['processes']['top_cpu'] = processes[:5]

# Top memory consuming processes
processes.sort(key=lambda x: x['memory_percent'], reverse=True)
metrics['processes']['top_memory'] = processes[:5]

# Check for zombie processes
zombies = []
for proc in psutil.process_iter(['pid', 'name', 'status']):
    try:
        if proc.info['status'] == psutil.STATUS_ZOMBIE:
            zombies.append(proc.info)
    except:
        pass

if zombies:
    metrics['processes']['zombies'] = zombies
    metrics['recommendations'].append("Kill zombie processes")

# Performance recommendations
if metrics['system']['cpu_percent'] > 80:
    metrics['recommendations'].append("High CPU usage detected - investigate top processes")

if metrics['system']['memory_percent'] > 85:
    metrics['recommendations'].append("High memory usage - consider restarting services")

if metrics['system']['disk_usage_percent'] > 85:
    metrics['recommendations'].append("Disk space running low - cleanup required")

# Save metrics
metrics_dir = Path.cwd() / 'metrics'
metrics_dir.mkdir(exist_ok=True)

metrics_file = metrics_dir / f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(metrics_file, 'w') as f:
    json.dump(metrics, f, indent=2)

# Print summary
print(f"CPU Usage: {metrics['system']['cpu_percent']:.1f}%")
print(f"Memory Usage: {metrics['system']['memory_percent']:.1f}%")
print(f"Disk Usage: {metrics['system']['disk_usage_percent']:.1f}%")
print(f"Active Processes: {metrics['system']['process_count']}")

if metrics['recommendations']:
    print("\nRecommendations:")
    for rec in metrics['recommendations']:
        print(f"  ⚠️  {rec}")
else:
    print("\n✅ System performance is optimal")

print(f"\nDetailed metrics saved to: {metrics_file}")

# Trigger optimization if needed
if len(metrics['recommendations']) > 2:
    print("\n🔧 Multiple performance issues detected - triggering optimization...")
    import subprocess
    subprocess.run(['python3', 'barbossa.py', '--area', 'infrastructure', 
                   '--prompt', f"Performance issues detected: {', '.join(metrics['recommendations'])}"])
EOF

echo ""
echo "Performance check completed: $(date)"
echo "================================================"