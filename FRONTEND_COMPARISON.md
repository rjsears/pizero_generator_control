# Frontend Comparison: n8n_nginx vs GenMaster

This document provides a side-by-side comparison of the n8n_nginx management frontend vs the current GenMaster frontend, with final implementation decisions.

---

## Implementation Progress

**Last Updated:** January 17th, 2026

### Completed Features

| Phase | Feature | Status | Commit |
|-------|---------|--------|--------|
| 1 | Notifications (Apprise + Email) | DONE | 1654356 |
| 1 | Debug Mode Toggle | DONE | 1654356 |
| 1 | About Dialog | DONE | 1654356 |
| 1 | Help Dialog | DONE | 1654356 |
| 2 | Dashboard CPU History Chart | DONE | b0aa18f |
| 2 | Dashboard Memory History Chart | DONE | b0aa18f |
| 2 | Dashboard Network I/O | DONE | b0aa18f |
| 2 | Dashboard Container Status Tile | DONE | b0aa18f |
| 2 | Dashboard Uptime Display | DONE | b0aa18f |
| 2 | Backend Metrics Service | DONE | b0aa18f |
| 2 | Backend Core Services Status API | DONE | b0aa18f |
| 2 | Backend Logs Analysis API | DONE | b0aa18f |
| 2 | Backend Docker Storage API | DONE | b0aa18f |

### Remaining Features

| Phase | Feature | Status |
|-------|---------|--------|
| 2 | System Health UI (core services, logs, docker) | PENDING |
| 4 | Settings Access Control Tab | PENDING |
| 4 | Settings Environment Tab | PENDING |
| 4 | Settings Account Tab enhancements | PENDING |
| 4 | Network Cloudflare Metrics | PENDING |
| 4 | Network Tailscale Peer Info | PENDING |
| 5 | System Terminal Tab with xterm.js | PENDING |

### Phase 3 Completed (January 17th, 2026)

| Feature | Status |
|---------|--------|
| Container Status Filtering | DONE |
| Container Recreate Button | DONE |
| Critical Container Warnings | DONE |
| Container Terminal Access | DONE |

---

## Files Created/Modified in Phase 1

### Backend
- `genmaster/backend/app/models/notifications.py` - Notification models (channels, groups, history)
- `genmaster/backend/app/schemas/notifications.py` - Notification schemas
- `genmaster/backend/app/services/notification_service.py` - Apprise & Email service
- `genmaster/backend/app/routers/notifications.py` - Notifications API router
- `genmaster/backend/alembic/versions/20260117_0002_002_add_notifications.py` - DB migration
- `genmaster/backend/requirements.txt` - Added apprise==1.9.0

### Frontend
- `genmaster/frontend/src/views/NotificationsView.vue` - Notifications page (Channels, Groups, History tabs)
- `genmaster/frontend/src/services/notifications.js` - Notifications API service
- `genmaster/frontend/src/stores/debug.js` - Debug mode store
- `genmaster/frontend/src/components/common/AboutDialog.vue` - About dialog
- `genmaster/frontend/src/components/common/HelpDialog.vue` - Help dialog
- `genmaster/frontend/src/components/layouts/SidebarLayout.vue` - Updated with debug indicator, help, about
- `genmaster/frontend/src/views/SettingsView.vue` - Removed webhooks tab, added Advanced tab with debug toggle
- `genmaster/frontend/src/router/index.js` - Added notifications route

---

## Files Created/Modified in Phase 2

### Backend
- `genmaster/backend/app/services/metrics_service.py` - Metrics collection service
  - Collects CPU, memory, network I/O every 60 seconds
  - Stores 60 data points (1 hour history)
  - Functions: `get_container_summary()`, `get_docker_storage()`, `get_core_services_status()`, `get_recent_logs_analysis()`
- `genmaster/backend/app/routers/metrics.py` - Metrics API router
  - `GET /api/metrics/history` - CPU/memory/network history
  - `GET /api/metrics/network` - Current network rates
  - `GET /api/metrics/containers/summary` - Container counts
  - `GET /api/metrics/services` - Core services status
  - `GET /api/metrics/docker/storage` - Docker storage usage
  - `GET /api/metrics/logs/analysis` - Logs error/warning counts
  - `GET /api/metrics/dashboard` - Combined dashboard data
- `genmaster/backend/app/main.py` - Added metrics router and service startup

### Frontend
- `genmaster/frontend/src/services/metrics.js` - Metrics API service
- `genmaster/frontend/src/stores/metrics.js` - Metrics Pinia store
- `genmaster/frontend/src/components/charts/MetricsLineChart.vue` - Reusable line chart component (vue-chartjs)
- `genmaster/frontend/src/views/DashboardView.vue` - Complete rewrite with:
  - Uptime card
  - Container status tile (clickable)
  - CPU/Memory history charts
  - Network I/O card with rates and chart
  - Improved Victron and System Health cards
  - Auto-refresh every 60 seconds

---

## Files Created/Modified in Phase 3

### Backend
- `genmaster/backend/app/routers/containers.py` - Updated with:
  - Added `pull_image` parameter to recreate endpoint
  - Conditional image pulling based on parameter

### Frontend
- `genmaster/frontend/src/stores/containers.js` - Added:
  - `recreateContainer(name, pullImage)` action
- `genmaster/frontend/src/components/containers/ContainerTerminal.vue` - NEW:
  - xterm.js-based terminal component
  - WebSocket connection to container shell
  - Dark Tokyo Night theme
  - Auto-fit to container size
  - Status bar with connection state
- `genmaster/frontend/src/views/ContainersView.vue` - Major enhancements:
  - Status filtering (All/Running/Stopped/Unhealthy)
  - Clickable stat cards for filtering
  - Filter indicator with clear button
  - Recreate button with pull image option
  - Critical container warnings (genmaster, nginx, postgres)
  - Critical containers highlighted with amber border
  - Terminal button for running containers
  - ContainerTerminal modal integration

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
    └── Advanced Tab (Debug)

HEADER CONTROLS:
├── Debug Mode Indicator
├── Help Button
├── About Button
├── Theme Toggle
└── User Menu
```

---

## Detailed Implementation Requirements

### 1. Notifications (Main Nav - Apprise + Email) - DONE

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

### 2. Dashboard Enhancements - DONE

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

### 3. Container Enhancements - PENDING

**Add:**
- Terminal Access (direct shell into containers)
- Status Filtering (All/Running/Stopped)
- Recreate Button (rebuild with optional image pull)
- Critical Container Warnings (special dialogs for genmaster, nginx, postgres)

### 4. System View Enhancements - PARTIAL

**Health Tab - Add:**
- Core Services Status (genmaster API, genslave, nginx) - API DONE, UI PENDING
- Recent Logs Analysis (error/warning counts by container) - API DONE, UI PENDING
- Docker Storage Usage (images/volumes disk usage) - API DONE, UI PENDING

**Network Tab - Add:**
- Cloudflare Metrics Display - PENDING
- Cloudflare API Key Management - PENDING
- Tailscale Peer Info - PENDING
- Tailscale Auth Setup - PENDING

**Terminal Tab - Add (NEW):**
- Container selection dropdown - PENDING
- xterm.js terminal interface - PENDING
- WebSocket communication - PENDING
- Theme switching (dark/light) - PENDING

### 5. Settings Enhancements - PARTIAL

**Access Control Tab (NEW):** - PENDING
- IP range management
- Nginx route configuration
- Quick-add common networks
- Description editing for IP ranges

**Environment Tab (NEW):** - PENDING
- View/edit environment variables
- Restart required indicator

**Account Tab - Add:** - PENDING
- User profile display (username, role, created date)
- Keep password change functionality

**Advanced Tab (formerly Debug Tab):** - DONE
- Debug mode toggle
- Verbose logging enable/disable

### 6. Header Enhancements - DONE

**Add:**
- Debug Mode Indicator (visible when debug enabled)
- Help Dialog Button
- About Dialog Button

---

## Navigation Menu Comparison

| n8n_nginx | GenMaster | Status |
|-----------|-----------|--------|
| Dashboard | Dashboard | ENHANCED |
| Backups | - | SKIP |
| Notifications | Notifications | ADDED |
| Containers | Containers | EXISTS - enhance pending |
| Flows | - | N/A (n8n specific) |
| System | System | EXISTS - enhance pending |
| Settings | Settings | ENHANCED |
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

### Phase 1: Core Infrastructure - COMPLETE
1. [x] Move Notifications to main nav with Apprise + Email
2. [x] Add Debug Mode Toggle to Settings
3. [x] Add About Dialog
4. [x] Add Help Dialog

### Phase 2: Dashboard & System - IN PROGRESS
5. [x] Dashboard history charts (CPU/Memory)
6. [x] Dashboard Network I/O
7. [x] Dashboard Container Status tile
8. [x] Dashboard Uptime display
9. [x] System Health Core Services (API done, UI pending)
10. [x] System Health Recent Logs (API done, UI pending)
11. [x] System Health Docker Storage (API done, UI pending)

### Phase 3: Containers - COMPLETE
12. [x] Container Status Filtering
13. [x] Container Recreate Button
14. [x] Critical Container Warnings
15. [x] Container Terminal Access

### Phase 4: Settings & Network - PENDING
16. [ ] Settings Access Control Tab
17. [ ] Settings Environment Tab
18. [ ] Settings Account Tab enhancements
19. [ ] Network Cloudflare Metrics
20. [ ] Network Tailscale Peer Info

### Phase 5: Terminal - PENDING
21. [ ] System Terminal Tab with xterm.js
22. [ ] Notification Groups feature (note: Groups tab exists but may need enhancement)

---

## Technical Notes

### Dependencies Added
- `apprise==1.9.0` - Multi-platform notification library
- `chart.js` and `vue-chartjs` already in package.json

### Database Migrations
- `20260117_0002_002_add_notifications.py` - Creates notification_channels, notification_groups, notification_group_channels, notification_history tables

### API Endpoints Added

**Notifications:**
- `GET/POST /api/notifications/channels` - Channel CRUD
- `GET/POST /api/notifications/groups` - Group CRUD
- `POST /api/notifications/channels/{id}/test` - Test channel
- `GET /api/notifications/history` - Notification history
- `POST /api/notifications/send` - Send notification

**Metrics:**
- `GET /api/metrics/history` - Metrics history for charts
- `GET /api/metrics/network` - Current network I/O
- `GET /api/metrics/containers/summary` - Container counts
- `GET /api/metrics/services` - Core services status
- `GET /api/metrics/docker/storage` - Docker storage
- `GET /api/metrics/logs/analysis` - Logs analysis
- `GET /api/metrics/dashboard` - Combined dashboard data

**Terminal:**
- `WS /api/terminal/ws` - WebSocket terminal connection
- `GET /api/terminal/targets` - Available terminal targets

**Containers (updated):**
- `POST /api/containers/{name}/recreate?pull_image=true` - Recreate with optional image pull

### Stores Added
- `debug.js` - Debug mode state management
- `metrics.js` - Metrics and dashboard data

### Components Added
- `AboutDialog.vue` - About information modal
- `HelpDialog.vue` - Help reference modal
- `MetricsLineChart.vue` - Reusable chart component
- `ContainerTerminal.vue` - xterm.js container terminal
