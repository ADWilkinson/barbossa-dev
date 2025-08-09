# Barbossa Web Portal Dashboard Guide

## Overview
The Barbossa Web Portal provides a comprehensive monitoring and control interface for the Barbossa autonomous engineer system. The dashboard is accessible at https://eastindiaonchaincompany.xyz with secure HTTPS and basic authentication.

## Access Information
- **Local Access**: https://localhost:8443
- **Remote Access**: https://eastindiaonchaincompany.xyz (via Cloudflare tunnel)
- **Authentication**: Basic auth with credentials stored in ~/.barbossa_credentials.json

## Dashboard Features

### 1. Barbossa Status Panel
**Purpose**: Monitor Barbossa's current state and work history

**Features**:
- **Status Indicator**: Shows if Barbossa is currently running or idle
- **Next Run Timer**: Displays when Barbossa will automatically execute (every 4 hours)
- **Claude Process Count**: Number of active Claude CLI processes
- **Work Tally**: Visual breakdown of completed work by area:
  - Infrastructure improvements
  - Personal projects
  - Davy Jones development

**Actions**:
- **Trigger Manual Run**: Execute Barbossa immediately without waiting for scheduled time
- **Refresh**: Update all status information

### 2. System Health Panel
**Purpose**: Monitor server resources and service status

**Features**:
- **CPU Usage**: Real-time CPU utilization
- **Memory Usage**: Current RAM usage vs total available
- **Disk Usage**: Storage utilization and available space
- **Service Status**: Health indicators for:
  - Barbossa portal (this dashboard)
  - Cloudflared tunnel
  - Claude processes
  - Docker daemon
  - Active tmux sessions

### 3. Claude Processes Panel
**Purpose**: Monitor and manage Claude CLI instances

**Features**:
- **Process List**: All running Claude processes with:
  - Process ID (PID)
  - CPU usage percentage
  - Memory usage percentage
  - Start time
  - Runtime duration
- **Kill Button**: Terminate stuck or unwanted Claude processes

**Important Notes**:
- Only shows actual Claude CLI processes
- Does not display other system processes
- Useful for cleaning up stuck background tasks

### 4. Work History Panel
**Purpose**: Track all work performed by Barbossa

**Three Tabs**:

#### Changelogs Tab
- Shows work session summaries
- Displays work area, timestamp, and file size
- Click entries to view full content
- Includes brief preview of changes

#### Claude Outputs Tab
- Lists all Claude execution logs
- Shows work type and completion status:
  - ✅ Completed: Successful execution
  - ⚠️ In Progress: Currently running
  - ❌ Partial: Incomplete or failed
- Click to view full Claude output

#### Security Tab
- Displays security audit events
- Shows access violations and blocks
- Tracks repository access attempts
- Monitors compliance with security rules

### 5. Log Management Panel
**Purpose**: Search, view, and archive system logs

**Features**:
- **Search Box**: Filter logs by keyword
- **Recent Logs Viewer**: Quick access to latest log files
- **Archive Old Logs**: Move old logs to timestamped archive folders
- **Clear 30+ Day Logs**: Archive logs older than 30 days

**Log Categories**:
- Barbossa execution logs
- Claude output logs
- Security audit logs
- Changelog files

### 6. Quick Actions Panel
**Purpose**: Manually trigger specific work areas

**Action Buttons**:
- **🔧 Run Infrastructure**: Execute infrastructure improvements
- **💻 Run Personal Projects**: Work on ADWilkinson repositories
- **🏴‍☠️ Run Davy Jones**: Improve Davy Jones Intern bot
- **📋 View Full Logs**: Comprehensive log browser modal

## Modal Features

### Log Viewer Modal
**Triggered by**: Clicking on any log entry or "View Full Logs" button

**Features**:
- Full-screen overlay for comfortable reading
- Syntax-highlighted log content
- Automatic sensitive data redaction:
  - API keys replaced with ***REDACTED***
  - Tokens and secrets hidden
  - SSH keys removed
- Categorized log browser with sections for:
  - Barbossa logs
  - Claude outputs
  - Changelogs
  - Security logs

## Auto-Refresh
- Dashboard automatically refreshes every 30 seconds
- Manual refresh available via button
- Real-time clock shows current UTC time

## Security Features

### Data Protection
- All sensitive information is automatically redacted:
  - API keys (ANTHROPIC_API_KEY, GITHUB_TOKEN, etc.)
  - Passwords and secrets
  - SSH private keys
  - Authentication tokens

### Access Control
- HTTPS-only access with self-signed certificate
- Basic authentication required
- Credentials stored securely outside git repository
- Session-based authentication

### Repository Protection
- Dashboard enforces security rules
- Blocks access to zkp2p repositories
- Logs all security violations
- Audit trail for compliance

## Button Functionality Status

All dashboard buttons are fully functional:
- ✅ **Trigger Manual Run**: Launches Barbossa with automatic area selection
- ✅ **Refresh**: Updates all dashboard data
- ✅ **Kill Process**: Terminates Claude processes
- ✅ **Run Infrastructure**: Executes infrastructure work
- ✅ **Run Personal Projects**: Works on personal repositories
- ✅ **Run Davy Jones**: Improves bot (development only)
- ✅ **View Full Logs**: Opens comprehensive log browser
- ✅ **Archive Old Logs**: Moves logs to archive with timestamp
- ✅ **Clear 30+ Day Logs**: Archives old logs

## Monitoring Best Practices

1. **Regular Checks**: Monitor the dashboard daily to ensure:
   - No stuck Claude processes
   - Work is being completed as scheduled
   - No security violations

2. **Process Management**: 
   - Kill stuck processes promptly
   - Check Claude output logs for errors
   - Verify work completion in changelogs

3. **Log Maintenance**:
   - Archive logs weekly to prevent buildup
   - Review security logs for anomalies
   - Check Claude outputs for successful PRs

4. **Manual Triggers**:
   - Use sparingly to avoid overloading system
   - Wait for current work to complete
   - Check process list before triggering new work

## Troubleshooting

### Portal Not Accessible
1. Check if process is running: `ps aux | grep "web_portal/app.py"`
2. Restart portal: `~/barbossa-engineer/web_portal/restart_portal.sh`
3. Check Cloudflare tunnel: `ps aux | grep cloudflared`

### Buttons Not Working
- Verify authentication is active
- Check browser console for errors
- Ensure JavaScript is enabled
- Try refreshing the page

### Logs Not Loading
- Check file permissions in logs directory
- Verify log files exist
- Check for disk space issues

### Claude Processes Stuck
- Use Kill button on dashboard
- Or manually: `pkill -f "claude --dangerously-skip-permissions"`
- Check logs for error details

## Technical Details

### Architecture
- **Backend**: Flask (Python 3)
- **Frontend**: Vanilla JavaScript with real-time updates
- **Transport**: HTTPS with self-signed certificate
- **Tunnel**: Cloudflare tunnel for external access
- **Authentication**: HTTP Basic Auth with hashed passwords

### File Locations
- **Portal Code**: ~/barbossa-engineer/web_portal/
- **Logs**: ~/barbossa-engineer/logs/
- **Changelogs**: ~/barbossa-engineer/changelogs/
- **Archives**: ~/barbossa-engineer/archive/
- **Credentials**: ~/.barbossa_credentials.json

### API Endpoints
- `/api/status` - System and Barbossa status
- `/api/changelogs` - Work history
- `/api/security` - Security events
- `/api/claude` - Claude outputs
- `/api/services` - Service status
- `/api/trigger-barbossa` - Manual execution
- `/api/kill-claude` - Process termination
- `/api/clear-logs` - Log archival
- `/api/log/<filename>` - Individual log content

## Updates and Maintenance

The dashboard is actively maintained and includes:
- Automatic sensitive data redaction
- Real-time process monitoring
- Comprehensive logging
- Security audit trails
- Background task management

For issues or feature requests, check the Barbossa repository or system logs for troubleshooting information.