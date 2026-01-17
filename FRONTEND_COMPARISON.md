# Frontend Comparison: n8n_nginx vs GenMaster

This document provides a side-by-side comparison of the n8n_nginx management frontend vs the current GenMaster frontend to identify missing features and differences.

---

## Navigation Menu Comparison

| n8n_nginx | GenMaster | Status |
|-----------|-----------|--------|
| Dashboard | Dashboard | EXISTS |
| Backups | - | MISSING |
| Notifications | Settings > Webhooks | NEEDS MOVE to main nav |
| Containers | Containers | EXISTS |
| Flows | - | N/A (n8n specific) |
| System | System | EXISTS (incomplete) |
| Settings | Settings | EXISTS (incomplete) |
| - | Generator | GenMaster specific |
| - | GenSlave | GenMaster specific |
| - | Schedule | GenMaster specific |
| - | History | GenMaster specific |

### Header/Navigation Controls

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Debug Mode Indicator | YES | NO | MISSING |
| Help Dialog Button | YES | NO | MISSING |
| About Dialog Button | YES | NO | MISSING |
| Dark Mode Toggle | YES | YES | EXISTS |
| User Menu with Logout | YES | YES | EXISTS |
| Status Badge (generator/n8n) | n8n status | Generator status | EXISTS (different) |

---

## Dashboard Comparison

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| CPU Usage Card | YES | YES | EXISTS |
| Memory Usage Card | YES | YES | EXISTS |
| Disk Usage Card | YES | YES | EXISTS |
| Uptime Display | YES | NO | MISSING |
| CPU History Chart | YES | NO | MISSING |
| Memory History Chart | YES | NO | MISSING |
| Container Status Tile | YES | NO | MISSING |
| Network I/O Current Rates | YES | NO | MISSING |
| Network Download History | YES | NO | MISSING |
| Network Upload History | YES | NO | MISSING |
| Generator Status Card | NO | YES | GenMaster specific |
| GenSlave Status Card | NO | YES | GenMaster specific |
| Victron Input Status | NO | YES | GenMaster specific |
| Quick Actions (Start/Stop) | NO | YES | GenMaster specific |
| Recent Activity | NO | YES | GenMaster specific |
| Temperature Display | NO | YES | GenMaster specific |

---

## Backups Section (ENTIRELY MISSING in GenMaster)

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Backup Now Button | YES | NO | MISSING |
| Backup Statistics | YES | NO | MISSING |
| Backup Progress | YES | NO | MISSING |
| Selective Restore | YES | NO | MISSING |
| Mount Backups | YES | NO | MISSING |
| Protected Backups | YES | NO | MISSING |
| Download Options | YES | NO | MISSING |
| Filtering/Sorting | YES | NO | MISSING |
| Verification | YES | NO | MISSING |

### Backup Settings (ENTIRELY MISSING in GenMaster)

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Storage Tab | YES | NO | MISSING |
| Schedule Tab | YES | NO | MISSING |
| Retention Tab (GFS) | YES | NO | MISSING |
| Compression Tab | YES | NO | MISSING |
| Verification Tab | YES | NO | MISSING |
| Backup Notifications Tab | YES | NO | MISSING |

---

## Notifications Section

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Main Navigation Item | YES | NO (in Settings > Webhooks) | NEEDS MOVE |
| Channels Tab | YES | NO | MISSING |
| Groups Tab | YES | NO | MISSING |
| NTFY Push Tab | YES | NO | MISSING |
| Multiple Channel Types | YES | NO | MISSING |
| - Apprise | YES | NO | MISSING |
| - NTFY | YES | NO | MISSING |
| - Email | YES | NO | MISSING |
| - Webhooks | YES | YES (basic) | PARTIAL |
| Message History | YES | NO | MISSING |
| n8n Webhook Integration | YES | NO | N/A |

---

## Containers Comparison

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Container List | YES | YES | EXISTS |
| Start/Stop/Restart | YES | YES | EXISTS |
| View Logs | YES | YES | EXISTS |
| CPU/Memory Stats | YES | YES | EXISTS |
| Network I/O Stats | YES | YES | EXISTS |
| Health Status | YES | YES | EXISTS |
| Status Filtering | YES | NO | MISSING |
| Terminal Access | YES | NO | MISSING |
| Recreate Container | YES | NO | MISSING |
| Per-container Notifications | YES | NO | MISSING |
| Critical Container Warnings | YES | NO | MISSING |
| Stopped Container Management | YES | NO | MISSING |
| Memory Color Coding | YES | YES | EXISTS |

---

## System Section Comparison

### Health Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Overall Status Banner | YES | YES | EXISTS |
| Docker Container Summary | YES | YES | EXISTS |
| Core Services Status | YES (n8n, nginx, API) | NO | MISSING |
| Database Status | YES | NO | MISSING |
| Host Resources | YES | YES | EXISTS |
| SSL Certificates Status | YES | YES | EXISTS |
| Management Database | YES | NO | MISSING |
| Backup Status Summary | YES | NO | MISSING |
| Recent Logs Analysis | YES | NO | MISSING |
| Docker Storage Usage | YES | NO | MISSING |
| System Info Card | YES | YES | EXISTS |
| Docker Info Card | YES | YES | EXISTS |
| Reboot Button | NO | YES | GenMaster specific |

### Network Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| External Services Links | YES | NO | MISSING |
| Network Configuration | YES | YES | EXISTS |
| Network Interfaces | YES | YES | EXISTS |
| Cloudflare Tunnel Status | YES | YES | EXISTS |
| Cloudflare Metrics | YES | NO | MISSING |
| Cloudflare API Key Mgmt | YES | NO | MISSING |
| Tailscale VPN Status | YES | YES | EXISTS |
| Tailscale Peer Info | YES | NO | MISSING |
| Tailscale Auth Setup | YES | NO | MISSING |
| Hostname Display | YES | YES | EXISTS |
| Gateway Info | YES | YES | EXISTS |
| DNS Servers | YES | YES | EXISTS |

### Terminal Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Terminal Access | YES | NO | MISSING |
| Container Selection | YES | NO | MISSING |
| Theme Switching | YES | NO | MISSING |
| WebSocket Communication | YES | NO | MISSING |
| xterm.js Interface | YES | NO | MISSING |

### Files Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| File Browser | YES | NO | MISSING |

### GenSlave Tab (GenMaster specific)

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| GenSlave Status | NO | YES | GenMaster specific |
| GenSlave Metrics | NO | YES | GenMaster specific |
| Test Connection | NO | YES | GenMaster specific |

---

## Settings Section Comparison

### Appearance Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Theme Selection | YES | YES | EXISTS |
| Navigation Layout Toggle | YES | YES | EXISTS |

### System Notifications Tab (n8n_nginx)

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Backup Alerts | YES | NO | MISSING |
| Container Health Alerts | YES | NO | MISSING |
| Disk Space Warnings | YES | NO | MISSING |

### Security Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Session Timeout Slider | YES | YES | EXISTS |
| Max Login Attempts | YES | YES | EXISTS |
| Lockout Duration | YES | YES | EXISTS |

### Access Control Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| IP Range Management | YES | NO | MISSING |
| Nginx Route Config | YES | NO | MISSING |
| Quick-add Common Networks | YES | NO | MISSING |
| Description Editing | YES | NO | MISSING |

### Environment Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Environment Variable Mgmt | YES | NO | MISSING |

### Account Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| User Profile Display | YES | NO | MISSING |
| Password Change | YES | YES | EXISTS |
| Visibility Toggles | YES | YES | EXISTS |

### n8n API / Debug Tab

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| API Key Management | YES | NO | N/A (n8n specific) |
| Debug Mode Toggle | YES | NO | MISSING |

### Generator Tab (GenMaster specific)

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Warmup Duration | NO | YES | GenMaster specific |
| Cooldown Duration | NO | YES | GenMaster specific |
| Min/Max Run Time | NO | YES | GenMaster specific |
| GenSlave URL Config | NO | YES | GenMaster specific |
| Heartbeat Interval | NO | YES | GenMaster specific |

### Webhooks Tab (GenMaster specific - should become Notifications)

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| Master Enable Toggle | NO | YES | GenMaster specific |
| Webhook URL/Secret | NO | YES | GenMaster specific |
| Event Type Selection | NO | YES | GenMaster specific |
| Test Webhook | NO | YES | GenMaster specific |

---

## Dialogs and Modals

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| About Dialog | YES | NO | MISSING |
| Help Dialog | YES | NO | MISSING |
| Confirm Dialog | YES | YES | EXISTS |

---

## Loading States and UI Components

| Feature | n8n_nginx | GenMaster | Status |
|---------|-----------|-----------|--------|
| BackupScanLoader | YES | NO | MISSING |
| ContainerStackLoader | YES | YES | EXISTS |
| DnaHelixLoader | YES | NO | MISSING |
| HeartbeatLoader | YES | NO | MISSING |
| SystemMetricsLoader | YES | NO | MISSING |
| LoadingSpinner | YES | YES | EXISTS |
| ToastContainer | YES | YES | EXISTS |
| StatusBadge | YES | YES | EXISTS |
| EmptyState | YES | YES | EXISTS |
| Card Component | YES | YES | EXISTS |

---

## Summary: Missing Features to Add

### HIGH PRIORITY (Core Functionality)

1. **Notifications as Main Nav Item** - Move webhooks to main navigation as "Notifications"
2. **Terminal Access** - Add terminal tab to System view
3. **Debug Mode Toggle** - Add to Settings or header
4. **About Dialog** - Add About button and dialog
5. **Help Dialog** - Add Help button and dialog

### MEDIUM PRIORITY (Enhanced Features)

6. **Dashboard History Charts** - CPU/Memory history graphs
7. **Dashboard Network I/O** - Current rates and history
8. **Container Terminal** - Direct shell access to containers
9. **Container Status Filtering** - Filter by running/stopped
10. **System Health - Core Services** - Service status display
11. **System Health - Recent Logs** - Error/warning analysis
12. **Access Control Tab** - IP range management in Settings
13. **Uptime Display** - Add to dashboard

### LOWER PRIORITY (Nice to Have)

14. **Backup System** - Full backup management (if applicable to GenMaster)
15. **NTFY Integration** - Push notification service
16. **Notification Channels/Groups** - Advanced notification routing
17. **Environment Variables Tab** - Env var management in Settings
18. **File Browser** - File management interface
19. **Container Recreate** - Rebuild containers with optional pull
20. **Critical Container Warnings** - Special dialogs for important containers

---

## Features GenMaster Has That n8n_nginx Doesn't

These are generator-specific features that should be kept:

1. **Generator Control View** - Start/Stop/Emergency Stop/Timed Start
2. **GenSlave View** - Remote Pi monitoring
3. **Schedule View** - Scheduled generator runs
4. **History View** - Run history with filtering
5. **Victron Input Monitoring** - GPIO signal detection
6. **Generator Settings** - Warmup/Cooldown/Run times
7. **Manual Override** - Disable automatic Victron control

---

## Recommended Final Navigation Structure

```
MAIN NAVIGATION:
├── Dashboard
├── Generator (GenMaster specific)
├── GenSlave (GenMaster specific)
├── Schedule (GenMaster specific)
├── History (GenMaster specific)
├── Notifications (moved from Settings > Webhooks)
├── Containers
├── System
│   ├── Health Tab
│   ├── Network Tab
│   ├── Terminal Tab (ADD)
│   └── GenSlave Tab
└── Settings
    ├── Appearance Tab
    ├── Generator Tab
    ├── Security Tab
    ├── Access Control Tab (ADD)
    ├── Account Tab (ADD user profile)
    └── Debug Tab (ADD)

HEADER CONTROLS:
├── Debug Mode Indicator (ADD)
├── Help Button (ADD)
├── About Button (ADD)
├── Theme Toggle (EXISTS)
└── User Menu (EXISTS)
```
