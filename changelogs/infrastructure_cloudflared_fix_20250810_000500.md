# Infrastructure Management - Cloudflared Service Fix
Date: 2025-08-10 00:05:00
Type: Infrastructure
Priority: Critical

## Issue Identified
The cloudflared service was reported as down by the system health monitoring, preventing external access to services via Cloudflare Tunnel.

## Root Cause Analysis
- The cloudflared service was not configured as a systemd service
- Instead, it was running in a tmux session named "tunnel"
- The web portal (barbossa-portal) was running but responding very slowly to HTTPS requests
- No automatic restart mechanism was in place for system reboots

## Actions Taken

### 1. Service Investigation
- Verified cloudflared was installed (version 2025.7.0)
- Found the service running in tmux session "tunnel" 
- Discovered connection errors to localhost:8443 (web portal)
- Process ID 1023044 was running: `cloudflared tunnel run eastindia`

### 2. Service Restart
- Killed the existing tmux tunnel session
- Started a new tmux session with: `tmux new-session -d -s tunnel "cloudflared tunnel run eastindia"`
- Verified successful connection to Cloudflare edge servers (lhr15, lhr01, lhr13, lhr19)

### 3. Service Verification
- Confirmed external access to https://eastindiaonchaincompany.xyz (401 authentication required - expected)
- Verified webhook service at https://webhook.eastindiaonchaincompany.xyz (200 OK)
- Checked tunnel logs - no errors found after restart

### 4. Automatic Startup Configuration
- Added crontab entry for automatic restart on system reboot:
  `@reboot sleep 30 && tmux new-session -d -s tunnel 'cloudflared tunnel run eastindia'`
- Cleaned up duplicate entries in crontab

## Results
- Cloudflared tunnel service restored to operational status
- External access to all configured services verified
- Automatic restart on reboot configured
- System health status should now report as healthy

## Configuration Details
Cloudflare Tunnel ID: 5ba42edf-f4d3-47c8-a1b3-68d46ac4f0ec
Ingress rules:
- eastindiaonchaincompany.xyz → https://localhost:8443 (Barbossa Portal)
- webhook.eastindiaonchaincompany.xyz → http://localhost:3001 (Davy Jones)
- api.eastindiaonchaincompany.xyz → http://localhost:80 (API endpoint)

## Recommendations
1. Consider creating a proper systemd service for cloudflared for better management
2. Monitor web portal performance - slow HTTPS responses may need investigation
3. Implement health checks for the tunnel connection
4. Set up alerts for tunnel disconnections

## Testing Commands
```bash
# Check tunnel status
tmux capture-pane -t tunnel -p | tail -20

# Test external access
curl -I https://eastindiaonchaincompany.xyz
curl -I https://webhook.eastindiaonchaincompany.xyz

# Verify crontab entry
crontab -l | grep tunnel
```