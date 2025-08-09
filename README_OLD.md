# Barbossa - Autonomous Software Engineer

⚓ **An autonomous software engineering program with strict security controls**

## 🛡️ CRITICAL SECURITY NOTICE

**This system has been designed with MAXIMUM SECURITY to prevent any access to ZKP2P organization repositories.**

- ✅ **ALLOWED**: All repositories under `ADWilkinson` GitHub account
- ❌ **BLOCKED**: ALL repositories under `zkp2p` or `ZKP2P` organizations
- 🔒 **ENFORCED**: Multi-layer security validation on every repository operation

## Overview

Barbossa is an autonomous software engineer that performs scheduled development tasks on your homeserver. It operates with strict security guardrails and can work on:

1. **Server Infrastructure** - System improvements, security hardening, optimization
2. **Personal Projects** - Feature development for ADWilkinson repositories
3. **Davy Jones Intern** - Bot improvements (without affecting production)

## Quick Start

```bash
# 1. Run the setup script
cd ~/barbossa-engineer
./setup_barbossa.sh

# 2. Test the security system
python3 barbossa.py --test-security

# 3. Run a test execution
python3 barbossa.py

# 4. Check status
python3 barbossa.py --status
```

## Installation

### Prerequisites
- Python 3.8+
- Git
- Claude CLI (`claude` command)
- Ubuntu/Debian Linux (tested on Ubuntu 24.04)

### Setup Steps

1. **Initial Setup**
   ```bash
   ./setup_barbossa.sh
   ```

2. **Create GitHub Repository** (optional)
   ```bash
   ./create_github_repo.sh
   ```

3. **Enable Scheduled Execution** (optional)
   ```bash
   ./setup_cron.sh
   ```

## Security Architecture

### Multi-Layer Protection

1. **Security Guard Module** (`security_guard.py`)
   - Validates ALL repository URLs before access
   - Maintains forbidden organization list
   - Enforces whitelist of allowed repositories
   - Logs all security events

2. **Repository Whitelist** (`config/repository_whitelist.json`)
   - Explicitly defines allowed repositories
   - All under ADWilkinson account only
   - No ZKP2P organization repos permitted

3. **Audit Logging**
   - All repository access attempts logged
   - Security violations tracked separately
   - Full audit trail maintained

### Testing Security

```bash
# Run comprehensive security tests
python3 tests/test_security.py

# Test Barbossa's security integration
python3 barbossa.py --test-security
```

## Usage

### Manual Execution

```bash
# Run with automatic work area selection
python3 barbossa.py

# Run specific work area
python3 barbossa.py --area infrastructure
python3 barbossa.py --area personal_projects
python3 barbossa.py --area davy_jones

# Pass work tally for balanced coverage
python3 barbossa.py --tally '{"infrastructure": 2, "personal_projects": 1, "davy_jones": 3}'
```

### Scheduled Execution

The system can run automatically every 4 hours via cron:

```bash
# Enable cron job
./setup_cron.sh

# Check cron status
crontab -l | grep barbossa
```

### Claude CLI Execution

For one-shot execution with Claude:

```bash
claude --dangerously-skip-permissions < barbossa_prompt.txt
```

## Web Portal

Access the HTTPS dashboard at `https://eastindiaonchaincompany.xyz` (via Cloudflare Tunnel)

Credentials are stored securely in `~/.barbossa_credentials.json` (outside git repository)
- Username: `admin`
- Password: Configured in external file

**🔒 Credentials file has restricted permissions (600) for security**

**Note**: External access is provided via Cloudflare Tunnel to bypass CGNAT restrictions. See [Cloudflare Tunnel Setup](docs/CLOUDFLARE_TUNNEL_SETUP.md) for details.

### Portal Features
- Real-time Barbossa status
- Work tally tracking
- Security audit logs
- Service monitoring
- Activity logs

### Starting the Portal

```bash
cd web_portal
python3 app.py
```

## Work Areas

### 1. Infrastructure Improvements
- System package updates
- Security configuration reviews
- Docker optimization
- Log file management
- Dependency updates

### 2. Personal Project Development

Allowed repositories:
- `ADWilkinson/_save`
- `ADWilkinson/chordcraft-app`
- `ADWilkinson/piggyonchain`
- `ADWilkinson/persona-website`
- `ADWilkinson/saylor-memes`
- `ADWilkinson/the-flying-dutchman-theme`

Tasks:
- Code analysis and improvements
- Feature implementation
- Refactoring
- Test creation
- Documentation updates

### 3. Davy Jones Intern Development

**⚠️ IMPORTANT**: Does not redeploy or affect production instance

- Code improvements
- New feature development
- Test coverage expansion
- Documentation
- PR creation for review

## File Structure

```
barbossa-engineer/
├── barbossa.py              # Main program
├── security_guard.py        # Security enforcement module
├── barbossa_prompt.txt      # Claude execution template
├── setup_barbossa.sh        # Setup script
├── config/
│   └── repository_whitelist.json
├── logs/                    # Execution logs
├── changelogs/             # Work session changelogs
├── security/               # Security audit logs
├── work_tracking/          # Work tally tracking
├── tests/                  # Test suite
│   └── test_security.py
└── web_portal/            # HTTPS dashboard
    ├── app.py
    └── templates/
```

## Monitoring

### Check Status
```bash
python3 barbossa.py --status
```

### View Logs
```bash
# Latest execution log
ls -la logs/

# Security audit
cat security/audit.log

# Violations log
cat security/security_violations.log
```

### Work Tally
```bash
cat work_tracking/work_tally.json
```

## Security Compliance

This system implements the following security measures:

1. **Hard-coded blocking** of ZKP2P organization
2. **Whitelist-only** repository access
3. **Multi-point validation** before any git operation
4. **Comprehensive audit logging**
5. **Security violation tracking**
6. **Automated testing** of security controls

## Network Infrastructure

### External Access
The homeserver uses **Cloudflare Tunnel** to provide external access, bypassing ISP CGNAT restrictions:

- **Main Portal**: https://eastindiaonchaincompany.xyz
- **Webhook Service**: https://webhook.eastindiaonchaincompany.xyz  
- **API Endpoint**: https://api.eastindiaonchaincompany.xyz

See [Cloudflare Tunnel Setup Documentation](docs/CLOUDFLARE_TUNNEL_SETUP.md) for configuration details.

### Service Ports
- **8443**: Barbossa HTTPS Portal (tunneled)
- **3001**: Davy Jones Webhook Service (tunneled)
- **80**: API Service (tunneled)
- **443**: HTTPS Service (tunneled)

## Troubleshooting

### Security Test Failures
If security tests fail:
1. Check `security/security_violations.log`
2. Verify whitelist configuration
3. Run `python3 barbossa.py --test-security`

### Cron Job Not Running
1. Check cron service: `systemctl status cron`
2. View cron logs: `grep CRON /var/log/syslog`
3. Verify Claude CLI is accessible

### Web Portal Issues
1. Check certificates exist in `web_portal/`
2. Verify port 8443 is not in use
3. Check Flask is installed: `pip3 install flask flask-httpauth`

### Cloudflare Tunnel Issues
1. Check tunnel status: `sudo systemctl status cloudflared`
2. View tunnel logs: `sudo journalctl -u cloudflared -f`
3. Verify DNS records in Cloudflare Dashboard
4. See [Cloudflare Tunnel Documentation](docs/CLOUDFLARE_TUNNEL_SETUP.md#troubleshooting)

## License

Private repository - All rights reserved

## Author

East India Onchain Company - Sailing the Digital Seas

---

**Remember**: This system will NEVER access ZKP2P organization repositories. All security measures are active and enforced.