# 🏴‍☠️ Barbossa Enhanced v2.0 - Comprehensive Server Management System

## Overview

Barbossa Enhanced is a comprehensive server management and autonomous engineering system that transforms your local server into an intelligent, self-managing infrastructure. Built on top of the original Barbossa autonomous engineer, this enhanced version adds extensive monitoring, real-time metrics, service management, and a professional web dashboard.

## ✨ Key Features

### 🖥️ Comprehensive Server Management
- **Real-time System Monitoring**: CPU, memory, disk, network metrics with historical tracking
- **Service Management**: Control systemd services, Docker containers, and tmux sessions
- **Network Monitoring**: Track open ports, active connections, and network traffic
- **Alert System**: Automatic alerts for high resource usage and service failures
- **Project Management**: Git repository tracking with change detection

### 🤖 Autonomous Engineering
- **Infrastructure Management**: Automated system optimization and maintenance
- **Personal Project Development**: Feature development for whitelisted repositories
- **Self-Improvement**: Barbossa can enhance its own capabilities
- **Security-First Design**: Maximum security with ZKP2P organization blocking

### 📊 Professional Web Dashboard
- **Modern UI**: Responsive, dark-themed interface with real-time updates
- **Interactive Charts**: Performance graphs, network activity, work distribution
- **Service Control**: Start/stop/restart services directly from the web
- **Log Viewer**: Real-time log streaming with search and filtering
- **Security Center**: Monitor security events and access control

### 🔒 Advanced Security
- **Repository Whitelist**: Only ADWilkinson repositories allowed
- **Multi-Layer Validation**: Security checks at every level
- **Audit Logging**: Comprehensive tracking of all operations
- **Violation Detection**: Immediate blocking and logging of security breaches

## 🚀 Quick Start

### Installation

1. **Clone the repository** (if not already present):
```bash
cd ~
git clone https://github.com/ADWilkinson/barbossa-engineer.git
cd barbossa-engineer
```

2. **Install dependencies**:
```bash
sudo apt-get update
sudo apt-get install -y python3-psutil python3-flask
```

3. **Set up credentials** (if not exists):
```bash
echo '{"admin": "YourSecurePassword"}' > ~/.barbossa_credentials.json
chmod 600 ~/.barbossa_credentials.json
```

### Starting the System

#### Option 1: Full System (Recommended)
```bash
# Start the enhanced web portal
./start_enhanced_portal.sh

# Access the dashboard
# Local: https://localhost:8443/enhanced
# Remote: https://eastindiaonchaincompany.xyz
```

#### Option 2: Command Line Only
```bash
# Check system status
python3 barbossa_enhanced.py --status

# Perform health check
python3 barbossa_enhanced.py --health

# Execute autonomous work
python3 barbossa_enhanced.py

# Execute specific work area
python3 barbossa_enhanced.py --area infrastructure
```

## 📁 Project Structure

```
barbossa-engineer/
├── barbossa_enhanced.py          # Enhanced main system v2.0
├── server_manager.py             # Comprehensive server monitoring
├── security_guard.py             # Security enforcement module
├── web_portal/
│   ├── enhanced_app.py          # Enhanced Flask application
│   └── templates/
│       └── enhanced_dashboard.html  # Professional dashboard UI
├── logs/                         # Execution and monitoring logs
├── changelogs/                   # Work session documentation
├── work_tracking/                # Work tally and current status
├── metrics.db                    # SQLite database for metrics
└── projects/                     # Managed git repositories
```

## 🎯 Work Areas

### 1. Infrastructure Management
- System performance optimization
- Docker container management
- Service health monitoring
- Security hardening
- Log rotation and cleanup
- Network optimization

### 2. Personal Projects
- Feature development for ADWilkinson repositories
- Test creation and improvement
- Code refactoring
- Bug fixes
- Documentation updates

### 3. Davy Jones Intern
- Bot improvements (without affecting production)
- Error handling enhancements
- New feature development
- Performance optimization

### 4. Barbossa Self-Improvement (NEW)
- Dashboard UI/UX enhancements
- New monitoring metrics
- API endpoint additions
- Performance optimizations
- Security enhancements

## 📊 Monitoring & Metrics

### Collected Metrics
- **System**: CPU, memory, disk, network, load averages
- **Services**: Status, memory usage, PIDs
- **Docker**: Container status, resource usage
- **Network**: Open ports, active connections
- **Projects**: Git status, uncommitted changes

### Historical Data
- Metrics stored in SQLite database
- 30-day retention with automatic cleanup
- Exportable for analysis

### Alerts
- High CPU usage (>90% for 5 minutes)
- High memory usage (>90% for 5 minutes)
- Critical disk space (<10% free)
- Service failures
- Security violations

## 🌐 Web Dashboard Features

### Overview Page
- Real-time system metrics
- 24-hour performance charts
- Active alerts display
- System uptime

### Service Management
- Systemd services control
- Docker container management
- Tmux session monitoring
- One-click start/stop/restart

### Network Monitor
- Open ports listing
- Active connections table
- Network traffic visualization
- Port availability checking

### Project Management
- Git repository status
- Uncommitted changes detection
- Branch information
- Quick actions (pull, open)

### Barbossa Control
- Execution status
- Work tally visualization
- Manual triggering
- Claude process management

### Security Center
- Security event log
- Access control status
- Whitelist management
- Violation tracking

## 🔐 Security Features

### Repository Access Control
- **Whitelist Only**: Only explicitly allowed repositories
- **Forbidden Organizations**: ZKP2P, zkp2p blocked at all levels
- **Multi-Point Validation**: Checks at every operation
- **Audit Trail**: Complete logging of all access attempts

### Web Portal Security
- HTTPS with self-signed certificates
- HTTP Basic Authentication
- Sensitive data sanitization in logs
- Session management

## 📝 Configuration

### Environment Variables
```bash
# Optional: Override work directory
export BARBOSSA_WORK_DIR=/custom/path

# Optional: Set monitoring interval (seconds)
export MONITORING_INTERVAL=60
```

### Work Area Weights
Adjust in `barbossa_enhanced.py`:
```python
WORK_AREAS = {
    'infrastructure': {'weight': 2.0},  # Higher priority
    'personal_projects': {'weight': 1.5},
    'davy_jones': {'weight': 1.0},
    'barbossa_self': {'weight': 1.5}
}
```

## 🛠️ API Endpoints

### Status & Monitoring
- `GET /api/comprehensive-status` - Full system status
- `GET /api/network-status` - Network connections
- `GET /api/projects` - Project information
- `GET /api/barbossa-status` - Barbossa specific status

### Control
- `POST /api/service-control` - Control system services
- `POST /api/container-control` - Docker container control
- `POST /api/trigger-barbossa` - Manually trigger Barbossa
- `POST /api/kill-claude` - Terminate Claude processes

### Logs & Security
- `GET /api/logs/recent` - Recent log entries
- `GET /api/security` - Security events
- `GET /api/changelogs` - Work changelogs

## 🚨 Troubleshooting

### Portal Won't Start
```bash
# Check if port 8443 is in use
lsof -i :8443

# Kill existing process if needed
kill <PID>

# Restart portal
./start_enhanced_portal.sh
```

### Metrics Not Collecting
```bash
# Check if psutil is installed
python3 -c "import psutil; print(psutil.__version__)"

# Reinstall if needed
sudo apt-get install --reinstall python3-psutil
```

### Security Test
```bash
# Test security system
python3 barbossa_enhanced.py --test-security
```

## 📈 Performance

- **Monitoring Overhead**: <1% CPU, ~50MB RAM
- **Database Size**: ~10MB per month of metrics
- **Web Portal**: Handles 100+ concurrent connections
- **Background Tasks**: Non-blocking async execution

## 🔄 Updates & Maintenance

### Updating Barbossa
```bash
cd ~/barbossa-engineer
git pull origin main
python3 barbossa_enhanced.py --area barbossa_self
```

### Database Maintenance
```bash
# Cleanup old metrics (>30 days)
python3 -c "from server_manager import BarbossaServerManager; m = BarbossaServerManager(); m.metrics_collector.cleanup_old_metrics(30)"
```

### Log Rotation
Logs are automatically rotated and archived. Manual cleanup:
```bash
# Archive logs older than 7 days
curl -X POST https://localhost:8443/api/clear-logs \
  -H "Content-Type: application/json" \
  -d '{"older_than_days": 7}'
```

## 🤝 Contributing

While Barbossa is designed to be autonomous, improvements are welcome:

1. Fork the repository (ADWilkinson/barbossa-engineer)
2. Create a feature branch
3. Make improvements (maintain security!)
4. Test thoroughly
5. Submit a pull request

## 📜 License

MIT License - See LICENSE file for details

## 🏴‍☠️ The Legend Continues

Barbossa Enhanced represents the evolution of autonomous server management, combining the wisdom of the seas with modern DevOps practices. May your servers run smooth as calm waters and your code be bug-free as the Flying Dutchman's curse is eternal.

**"The code is more what you'd call 'guidelines' than actual rules."** - Captain Barbossa

---

*Built with ⚓ by the East India Onchain Company - Sailing the Digital Seas*

**Version**: 2.0.0  
**Security**: MAXIMUM - ZKP2P Access BLOCKED  
**Status**: Production Ready