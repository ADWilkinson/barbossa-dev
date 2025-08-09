# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with the Barbossa Engineer project - an autonomous software engineering system with strict security controls.

## 🔒 CRITICAL SECURITY NOTICE

**This system has been designed with MAXIMUM SECURITY to prevent any access to ZKP2P organization repositories.**

- ✅ **ALLOWED**: All repositories under `ADWilkinson` GitHub account
- ❌ **BLOCKED**: ALL repositories under `zkp2p` or `ZKP2P` organizations
- 🔒 **ENFORCED**: Multi-layer security validation on every repository operation

## System Overview

Barbossa Engineer is an autonomous software engineering system running on Ubuntu 24.04 LTS that performs scheduled development tasks with strict security controls. The system operates on three main work areas:

1. **Server Infrastructure** - System improvements, security hardening, optimization
2. **Personal Projects** - Feature development for ADWilkinson repositories  
3. **Davy Jones Intern Development** - Bot improvements (without affecting production)

## Architecture & Components

### Core System (`/home/dappnode/barbossa-engineer/`)

**Main Program**
- `barbossa.py` - Core autonomous engineer with security-first design
- `security_guard.py` - Multi-layer security enforcement module
- `config/repository_whitelist.json` - Explicit repository access control

**Security Architecture**
- Repository URL validation with forbidden pattern matching
- Whitelist-only access for ADWilkinson repositories
- Multi-point validation before any git operation
- Comprehensive audit logging and violation tracking
- Hard-coded blocking of ZKP2P organizations

**Monitoring & Control**
- `web_portal/` - HTTPS management dashboard (Port 8443)
- `logs/` - Execution logs with sanitized sensitive information
- `changelogs/` - Work session documentation
- `security/` - Security audit trails and violation logs
- `work_tracking/` - Work tally for balanced task coverage

### Project Ecosystem (`/home/dappnode/barbossa-engineer/projects/`)

#### 1. Davy Jones Intern (`projects/davy-jones-intern/`)
**AI-powered Slack bot for development assistance**

- **Technology**: Node.js + TypeScript, Express.js, Slack Bolt SDK
- **Purpose**: Claude-integrated Slack bot for GitHub operations, build automation
- **Key Features**:
  - Claude AI integration for natural language understanding
  - GitHub PR management and status checking
  - SSH command execution on development server
  - Build & test automation with safety validation
  - Webhook handling for GitHub events

**Development Commands**:
```bash
cd ~/barbossa-engineer/projects/davy-jones-intern
npm run dev              # Development with hot reload
npm run build            # Compile TypeScript
npm run typecheck        # Type checking
npm run lint             # ESLint validation  
npm test                 # Jest testing
npm run test:coverage    # Coverage reports
```

**Architecture**:
- `src/services/claude.service.ts` - Claude SDK integration
- `src/handlers/slack.handler.ts` - Slack event processing
- `src/services/github.service.ts` - GitHub API operations
- `src/webhooks/` - GitHub webhook handlers
- `src/utils/` - Logging, formatting, progress tracking

#### 2. Saylor Memes (`projects/saylormemes/`)
**React + TypeScript media gallery application**

- **Technology**: React 18, TypeScript, Vite, Firebase, Tailwind CSS
- **Purpose**: Media gallery for Saylor-themed memes and content
- **Key Features**:
  - Firebase integration for storage and hosting
  - Search and tag filtering capabilities
  - Social sharing functionality

**Development Commands**:
```bash
cd ~/barbossa-engineer/projects/saylormemes
npm run dev              # Vite dev server
npm run build            # Production build
npm run lint             # ESLint validation
npm run preview          # Preview production build
npm run deploy           # Firebase deployment
```

**Architecture**:
- `src/components/` - Reusable React components
- `src/hooks/` - Custom React hooks for Firebase and analytics
- `src/types/` - TypeScript type definitions
- Firebase configuration for hosting and storage

#### 3. The Flying Dutchman Theme (`projects/the-flying-dutchman-theme/`)
**Multi-platform nautical-inspired dark theme collection**

- **Technology**: VS Code Extensions, Terminal themes, Cross-platform compatibility
- **Purpose**: Professional dark theme for developers with nautical inspiration
- **Key Features**:
  - VS Code marketplace extension with 150+ semantic tokens
  - Multi-platform support (6 editors/terminals)
  - WCAG AA compliant accessibility
  - Professional quality with comprehensive language support

**Development Commands**:
```bash
cd ~/barbossa-engineer/projects/the-flying-dutchman-theme
npm test                 # Jest test suite
npm run lint             # Code quality validation
```

**Architecture**:
- `themes/flying-dutchman-color-theme.json` - VS Code theme definition
- `tests/` - Comprehensive test suite with accessibility validation
- Multi-platform theme files (iTerm, Windows Terminal, Vim, etc.)

#### 4. ADW (`projects/adw/`)
**Next.js personal website/portfolio**

- **Technology**: Next.js, React, TypeScript, Tailwind CSS
- **Purpose**: Personal website with interactive audio features
- **Key Features**:
  - Next.js 13+ with App Router
  - Audio playback functionality with custom hooks
  - Responsive design with Tailwind CSS

## Infrastructure & Deployment

### External Access (Cloudflare Tunnel)
The homeserver uses **Cloudflare Tunnel** to bypass ISP CGNAT restrictions:

- **Main Portal**: https://eastindiaonchaincompany.xyz (Barbossa dashboard)
- **Webhook Service**: https://webhook.eastindiaonchaincompany.xyz (Davy Jones)
- **API Endpoint**: https://api.eastindiaonchaincompany.xyz

**Tunnel Configuration**:
- Tunnel ID: `5ba42edf-f4d3-47c8-a1b3-68d46ac4f0ec`
- Config: `~/.cloudflared/config.yml`
- Service: `sudo systemctl status cloudflared`

### Barbossa Web Portal (`web_portal/app.py`)
**Flask-based HTTPS management dashboard**

**Features**:
- Real-time system statistics (CPU, memory, disk usage)
- Barbossa execution status and work tally tracking
- Security audit logs with sensitive information sanitization
- Claude process monitoring and management
- Log file viewing and archival capabilities
- Service status monitoring (Docker, tmux sessions)

**Security**:
- HTTPBasicAuth with external credentials file
- Self-signed SSL certificates (auto-generated)
- Sensitive data sanitization in logs
- Restricted file access validation

### Automation & Scheduling

**Cron Integration**:
- Automatic execution every 4 hours via `setup_cron.sh`
- Dynamic prompt generation with work tally balancing
- Comprehensive logging to `logs/cron_*.log`

**Scripts**:
- `setup_barbossa.sh` - Initial system setup and security validation
- `run_barbossa.sh` - Cron execution wrapper
- `test_barbossa.sh` - System testing and validation

## Development Workflows

### Security-First Development
1. **Repository Validation**: All repository operations go through security_guard.py
2. **Whitelist Enforcement**: Only ADWilkinson repositories permitted
3. **Audit Logging**: All access attempts logged with timestamps
4. **Violation Tracking**: Security breaches logged separately

### Work Area Selection
Barbossa uses weighted random selection favoring less-worked areas:
- **Infrastructure**: System maintenance, security updates, Docker optimization
- **Personal Projects**: Feature development, refactoring, test creation
- **Davy Jones**: Bot improvements without affecting production

### Quality Assurance
- TypeScript compilation required for all TS projects
- ESLint validation with strict rules
- Jest/Vitest testing with coverage requirements
- Comprehensive logging and error handling

## Technology Stack

### Core Technologies
- **Python 3.8+**: Main Barbossa system with security enforcement
- **Node.js + TypeScript**: Davy Jones Intern bot
- **React + TypeScript**: Frontend applications (Saylor Memes)
- **Next.js**: Personal website development
- **Flask**: Web portal and monitoring dashboard

### Development Tools
- **Git**: Version control with security validation
- **Docker**: Container orchestration for services
- **tmux**: Session management for long-running processes
- **Cloudflare Tunnel**: External access bypassing CGNAT
- **Firebase**: Hosting and storage for media applications

### AI Integration
- **Claude SDK**: AI-powered development assistance in Davy Jones
- **Anthropic API**: Natural language processing for task analysis
- **Automated prompting**: Dynamic prompt generation for autonomous work

## Essential Commands

### Barbossa Operations
```bash
cd ~/barbossa-engineer

# Manual execution
python3 barbossa.py                                    # Auto work area selection
python3 barbossa.py --area infrastructure              # Specific work area
python3 barbossa.py --area personal_projects          # Personal project focus
python3 barbossa.py --area davy_jones                 # Bot development

# Status and monitoring
python3 barbossa.py --status                          # System status
python3 barbossa.py --test-security                   # Security validation

# Setup and maintenance
./setup_barbossa.sh                                   # Initial setup
./setup_cron.sh                                       # Enable scheduling
./test_barbossa.sh                                     # System testing
```

### Service Management
```bash
# Web Portal
cd ~/barbossa-engineer/web_portal
python3 app.py                                        # Start HTTPS dashboard

# Cloudflare Tunnel
sudo systemctl status cloudflared                     # Tunnel status
sudo journalctl -u cloudflared -f                     # Tunnel logs

# Process monitoring
pgrep -f barbossa.py                                   # Check if running
ps aux | grep claude                                   # Active Claude processes
```

### Project Development
```bash
# Davy Jones Intern
cd ~/barbossa-engineer/projects/davy-jones-intern
npm run dev && npm run build && npm test              # Full development cycle

# Saylor Memes
cd ~/barbossa-engineer/projects/saylormemes  
npm run dev && npm run build && npm run deploy        # Development to deployment

# Flying Dutchman Theme
cd ~/barbossa-engineer/projects/the-flying-dutchman-theme
npm test                                               # Theme validation
```

## Security Considerations

### Multi-Layer Protection
1. **Security Guard Module**: Validates ALL repository URLs before access
2. **Repository Whitelist**: Explicitly defines allowed repositories
3. **Forbidden Patterns**: Regex matching for ZKP2P organizations
4. **Audit Logging**: Comprehensive tracking of all operations
5. **Violation Detection**: Immediate blocking and logging of security breaches

### Safe Development Practices
- Never modify production services during development
- All changes go through pull request workflow
- Comprehensive testing before deployment
- Environment variable security for API keys
- SSH key-based authentication for remote operations

### Data Protection
- Sensitive information sanitization in logs
- External credential file storage (not in git)
- SSL/TLS encryption for web portal access
- Restricted file permissions (600) for credentials

## Monitoring & Maintenance

### Log Management
- **Execution Logs**: `logs/barbossa_*.log` - Main program execution
- **Claude Outputs**: `logs/claude_*.log` - AI execution results  
- **Security Audit**: `security/audit.log` - Access attempt tracking
- **Cron Execution**: `logs/cron_*.log` - Scheduled run results

### Work Tracking
- **Current Work**: `work_tracking/current_work.json` - Active task status
- **Work Tally**: `work_tracking/work_tally.json` - Balanced coverage tracking
- **Changelogs**: `changelogs/` - Detailed session documentation

### Health Monitoring
- Web portal at https://eastindiaonchaincompany.xyz
- Real-time system statistics and process monitoring
- Service status tracking (Docker, tmux, Cloudflare)
- Automated log archival and cleanup capabilities

## File Structure Reference

```
barbossa-engineer/
├── barbossa.py                    # Main autonomous engineer
├── security_guard.py              # Security enforcement
├── barbossa_prompt.txt            # Claude execution template
├── config/
│   └── repository_whitelist.json  # Allowed repositories
├── projects/
│   ├── davy-jones-intern/         # AI Slack bot
│   ├── saylormemes/               # React media gallery
│   ├── the-flying-dutchman-theme/ # VS Code theme
│   └── adw/                       # Next.js website
├── web_portal/
│   ├── app.py                     # Flask dashboard
│   └── templates/                 # HTML templates
├── logs/                          # Execution logs
├── changelogs/                    # Work documentation
├── security/                      # Security audit trails
├── work_tracking/                 # Task management
└── docs/
    └── CLOUDFLARE_TUNNEL_SETUP.md # Infrastructure docs
```

## Troubleshooting

### Common Issues
1. **Security Test Failures**: Check `security/security_violations.log`
2. **Cron Job Problems**: Verify Claude CLI accessibility
3. **Web Portal Access**: Check certificates and port 8443
4. **Tunnel Connectivity**: Monitor cloudflared service status

### Debug Commands
```bash
# Security validation
python3 tests/test_security.py

# Service health checks
curl -I https://eastindiaonchaincompany.xyz/health

# Log analysis
tail -f logs/barbossa_$(date +%Y%m%d)*.log
tail -f security/audit.log
```

## License & Compliance

- **License**: MIT License for open source components
- **Security Compliance**: MAXIMUM security level with ZKP2P access blocking
- **Access Control**: ADWilkinson repositories only
- **Audit Requirements**: Full operation logging and violation tracking

---

**Remember**: This system will NEVER access ZKP2P organization repositories. All security measures are active and enforced at multiple levels.

**Author**: East India Onchain Company - Sailing the Digital Seas