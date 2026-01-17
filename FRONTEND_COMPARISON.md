# Frontend Comparison: n8n_nginx vs GenMaster

This document provides a side-by-side comparison of the n8n_nginx management frontend vs the current GenMaster frontend, with final implementation decisions.

---

## Final Implementation Decisions

### APPROVED FOR IMPLEMENTATION

| # | Feature | Decision |
|---|---------|----------|
| 1 | Move Notifications to main nav (Apprise + Email only, no webhooks) | YES |
| 2 | Terminal Access in System view | YES |
| 3 | Debug Mode Toggle | YES |
| 4 | About Dialog | YES |
| 5 | Help Dialog | YES |
| 6 | Dashboard CPU/Memory History Charts | YES |
| 7 | Dashboard Network I/O Display | YES |
| 8 | Dashboard Container Status Tile | YES |
| 9 | Dashboard Uptime Display | YES |
| 10 | Container Terminal Access | YES |
| 11 | Container Status Filtering | YES |
| 12 | Container Recreate Button | YES |
| 13 | Critical Container Warnings | YES |
| 14 | System Health Core Services Status | YES |
| 15 | System Health Recent Logs Analysis | YES |
| 16 | Settings Access Control Tab | YES |
| 17 | Settings Environment Variables Tab | YES |
| 18 | Settings Account Tab with User Profile | YES |
| 19 | Network Cloudflare Metrics Display | YES |
| 20 | Network Tailscale Peer Info | YES |
| 21 | System Health Docker Storage Usage | YES |
| 22 | Notification Groups | YES |

### NOT IMPLEMENTING

| Feature | Reason |
|---------|--------|
| File Browser | Not needed |
| Backups Section | Not needed - reinstall recovers everything, only loses history |
| NTFY Integration | Using Apprise + Email only |
| Webhooks | Replaced by Apprise + Email |

---

## Final Navigation Structure

```
MAIN NAVIGATION:
├── Dashboard
├── Generator (GenMaster specific)
├── GenSlave (GenMaster specific)
├── Schedule (GenMaster specific)
├── History (GenMaster specific)
├── Notifications (Apprise + Email with Groups)
├── Containers
├── System
│   ├── Health Tab
│   ├── Network Tab
│   ├── Terminal Tab
│   └── GenSlave Tab
└── Settings
    ├── Appearance Tab
    ├── Generator Tab
    ├── Security Tab
    ├── Access Control Tab
    ├── Environment Tab
    ├── Account Tab
    └── Debug Tab

HEADER CONTROLS:
├── Debug Mode Indicator
├── Help Button
├── About Button
├── Theme Toggle
└── User Menu
```

---

## Detailed Implementation Requirements

### 1. Notifications (Main Nav - Apprise + Email)

**Replace current webhooks with:**
- Channels Tab (Apprise + Email types only)
- Groups Tab (group multiple channels)
- Test functionality per channel
- Enable/disable per channel
- Message history

**Notification Events:**
- generator_started
- generator_stopped
- generator_failed
- heartbeat_lost
- heartbeat_restored
- failsafe_triggered
- schedule_executed
- system_warning
- system_error

### 2. Dashboard Enhancements

**Add:**
- Uptime display card
- CPU History Chart (line graph, last hour)
- Memory History Chart (line graph, last hour)
- Network I/O Current Rates (download/upload speed)
- Network Download History Chart
- Network Upload History Chart
- Container Status Tile (running/stopped/unhealthy counts, clickable)

**Keep existing:**
- Generator Status Card
- GenSlave Status Card
- Victron Input Status
- Quick Actions
- Resource Usage (CPU/Memory/Disk/Temperature)

### 3. Container Enhancements

**Add:**
- Terminal Access (direct shell into containers)
- Status Filtering (All/Running/Stopped)
- Recreate Button (rebuild with optional image pull)
- Critical Container Warnings (special dialogs for genmaster, nginx, postgres)

### 4. System View Enhancements

**Health Tab - Add:**
- Core Services Status (genmaster API, genslave, nginx)
- Recent Logs Analysis (error/warning counts by container)
- Docker Storage Usage (images/volumes disk usage)

**Network Tab - Add:**
- Cloudflare Metrics Display
- Cloudflare API Key Management
- Tailscale Peer Info
- Tailscale Auth Setup

**Terminal Tab - Add (NEW):**
- Container selection dropdown
- xterm.js terminal interface
- WebSocket communication
- Theme switching (dark/light)

### 5. Settings Enhancements

**Access Control Tab (NEW):**
- IP range management
- Nginx route configuration
- Quick-add common networks
- Description editing for IP ranges

**Environment Tab (NEW):**
- View/edit environment variables
- Restart required indicator

**Account Tab - Add:**
- User profile display (username, role, created date)
- Keep password change functionality

**Debug Tab (NEW):**
- Debug mode toggle
- Verbose logging enable/disable

### 6. Header Enhancements

**Add:**
- Debug Mode Indicator (visible when debug enabled)
- Help Dialog Button
- About Dialog Button

---

## Navigation Menu Comparison

| n8n_nginx | GenMaster | Status |
|-----------|-----------|--------|
| Dashboard | Dashboard | EXISTS - enhance |
| Backups | - | SKIP |
| Notifications | Notifications | ADD (replace webhooks) |
| Containers | Containers | EXISTS - enhance |
| Flows | - | N/A (n8n specific) |
| System | System | EXISTS - enhance |
| Settings | Settings | EXISTS - enhance |
| - | Generator | GenMaster specific |
| - | GenSlave | GenMaster specific |
| - | Schedule | GenMaster specific |
| - | History | GenMaster specific |

---

## Features GenMaster Has That n8n_nginx Doesn't

These are generator-specific features that are kept:

1. **Generator Control View** - Start/Stop/Emergency Stop/Timed Start
2. **GenSlave View** - Remote Pi monitoring
3. **Schedule View** - Scheduled generator runs
4. **History View** - Run history with filtering
5. **Victron Input Monitoring** - GPIO signal detection
6. **Generator Settings** - Warmup/Cooldown/Run times
7. **Manual Override** - Disable automatic Victron control

---

## Implementation Priority Order

### Phase 1: Core Infrastructure
1. Move Notifications to main nav with Apprise + Email
2. Add Debug Mode Toggle to Settings
3. Add About Dialog
4. Add Help Dialog

### Phase 2: Dashboard & System
5. Dashboard history charts (CPU/Memory)
6. Dashboard Network I/O
7. Dashboard Container Status tile
8. Dashboard Uptime display
9. System Health Core Services
10. System Health Recent Logs
11. System Health Docker Storage

### Phase 3: Containers
12. Container Terminal Access
13. Container Status Filtering
14. Container Recreate Button
15. Critical Container Warnings

### Phase 4: Settings & Network
16. Settings Access Control Tab
17. Settings Environment Tab
18. Settings Account Tab enhancements
19. Network Cloudflare Metrics
20. Network Tailscale Peer Info

### Phase 5: Terminal
21. System Terminal Tab with xterm.js
22. Notification Groups feature
