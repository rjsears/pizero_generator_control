# Agent Handoff: GenMaster Frontend

## Purpose
This document provides complete specifications for building the Gen Management Vue.js frontend, modeled after the n8n_nginx management interface. The frontend provides a comprehensive web-based control panel for managing the generator control system.

---

## Overview

### Application Name
**Gen Management** - Generator Control System Management Interface

### Design Philosophy
The frontend is modeled after the n8n_nginx management interface, providing:
- Clean, modern UI with Tailwind CSS
- Dark/light theme support
- Real-time system monitoring
- Comprehensive container management
- Generator-specific controls and scheduling

### Navigation Structure

| Tab | Purpose | Based On |
|-----|---------|----------|
| **Dashboard** | System overview, metrics, generator status | n8n Dashboard |
| **Generator** | Generator control, manual start/stop, Victron monitoring | New |
| **Schedule** | Scheduled generator run times | New |
| **History** | Generator run history and statistics | New |
| **Containers** | Docker container management | n8n Containers |
| **System** | Health checks, network, terminal | n8n System |
| **Settings** | Appearance, notifications, security, account | n8n Settings (simplified) |

---

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Vue.js | 3.4+ | Frontend framework (Composition API) |
| Vite | 5.0+ | Build tool |
| Tailwind CSS | 3.4+ | Utility-first CSS |
| Pinia | 2.1+ | State management |
| Vue Router | 4.2+ | Client-side routing |
| Chart.js | 4.4+ | Runtime graphs and metrics |
| vue-chartjs | 5.3+ | Vue wrapper for Chart.js |
| Axios | 1.6+ | HTTP client |
| @heroicons/vue | 2.1+ | Icon library |
| xterm.js | 5.3+ | Terminal emulator |

---

## Project Structure

```
genmaster/frontend/
├── src/
│   ├── main.js                       # App entry point
│   ├── App.vue                       # Root component with layout
│   ├── router/
│   │   └── index.js                  # Vue Router configuration
│   ├── services/
│   │   └── api.js                    # Axios instance + API modules
│   ├── stores/                       # Pinia stores
│   │   ├── auth.js                   # Authentication state
│   │   ├── containers.js             # Container state
│   │   ├── generator.js              # Generator state
│   │   ├── notifications.js          # Toast notifications
│   │   ├── system.js                 # System health state
│   │   └── theme.js                  # Theme preferences
│   ├── composables/                  # Reusable composition functions
│   │   ├── usePoll.js                # Polling helper
│   │   └── useFormatters.js          # Date/time/byte formatters
│   ├── config/
│   │   └── constants.js              # Polling intervals, etc.
│   ├── utils/
│   │   └── formatters.js             # Formatting utilities
│   ├── components/
│   │   ├── common/                   # Shared components
│   │   │   ├── Card.vue
│   │   │   ├── StatusBadge.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   ├── EmptyState.vue
│   │   │   ├── ConfirmDialog.vue
│   │   │   └── SystemMetricsLoader.vue
│   │   ├── generator/                # Generator-specific components
│   │   │   ├── GeneratorStatus.vue
│   │   │   ├── VictronMonitor.vue
│   │   │   ├── ManualControl.vue
│   │   │   ├── OverridePanel.vue
│   │   │   └── RuntimeChart.vue
│   │   ├── schedule/                 # Schedule components
│   │   │   ├── ScheduleTable.vue
│   │   │   └── ScheduleModal.vue
│   │   └── settings/                 # Settings components
│   │       ├── WebhookSettings.vue
│   │       └── AppearanceSettings.vue
│   └── views/                        # Page components
│       ├── LoginView.vue
│       ├── DashboardView.vue
│       ├── GeneratorView.vue
│       ├── ScheduleView.vue
│       ├── HistoryView.vue
│       ├── ContainersView.vue
│       ├── SystemView.vue
│       └── SettingsView.vue
├── index.html
├── package.json
├── pnpm-lock.yaml
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── .env.example
```

---

## Configuration Files

### package.json

```json
{
  "name": "gen-management",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext .vue,.js --fix"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "chart.js": "^4.4.0",
    "vue-chartjs": "^5.3.0",
    "@heroicons/vue": "^2.1.0",
    "xterm": "^5.3.0",
    "xterm-addon-fit": "^0.8.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.56.0",
    "eslint-plugin-vue": "^9.20.0"
  }
}
```

### vite.config.js

```javascript
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    minify: 'terser'
  }
});
```

### tailwind.config.js

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}'
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Generator-specific colors
        'gen-green': '#22C55E',
        'gen-red': '#EF4444',
        'gen-amber': '#F59E0B',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'monospace']
      }
    }
  },
  plugins: []
};
```

### src/assets/styles/main.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --color-primary: theme('colors.blue.600');
    --color-primary-dark: theme('colors.blue.500');
  }

  body {
    @apply bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 antialiased;
  }
}

@layer components {
  /* Text color utilities */
  .text-primary {
    @apply text-gray-900 dark:text-white;
  }

  .text-secondary {
    @apply text-gray-600 dark:text-gray-400;
  }

  .text-muted {
    @apply text-gray-500 dark:text-gray-500;
  }

  /* Surface colors */
  .bg-surface {
    @apply bg-white dark:bg-gray-800;
  }

  .bg-surface-hover {
    @apply bg-gray-50 dark:bg-gray-700/50;
  }

  /* Card styles */
  .card {
    @apply bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm;
  }

  /* Button styles */
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-colors duration-200 inline-flex items-center justify-center gap-2;
  }

  .btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed;
  }

  .btn-secondary {
    @apply bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600;
  }

  .btn-danger {
    @apply bg-red-600 text-white hover:bg-red-700;
  }

  .btn-success {
    @apply bg-emerald-600 text-white hover:bg-emerald-700;
  }

  /* Form inputs */
  .input-field {
    @apply w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600
           bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
           placeholder-gray-400 dark:placeholder-gray-500;
  }

  .select-field {
    @apply input-field cursor-pointer;
  }

  /* Status indicators */
  .status-dot {
    @apply w-3 h-3 rounded-full inline-block;
  }

  .status-running {
    @apply bg-emerald-500 animate-pulse;
  }

  .status-stopped {
    @apply bg-gray-400;
  }

  .status-warning {
    @apply bg-amber-500;
  }

  .status-error {
    @apply bg-red-500;
  }
}
```

---

## Router Configuration

### src/router/index.js

```javascript
import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/generator',
    name: 'generator',
    component: () => import('../views/GeneratorView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/schedule',
    name: 'schedule',
    component: () => import('../views/ScheduleView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('../views/HistoryView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/containers',
    name: 'containers',
    component: () => import('../views/ContainersView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/system',
    name: 'system',
    component: () => import('../views/SystemView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  // Initialize auth if token exists
  if (!authStore.user && authStore.token) {
    await authStore.fetchCurrentUser();
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } });
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next({ name: 'dashboard' });
  } else {
    next();
  }
});

export default router;
```

---

## API Service

### src/services/api.js

```javascript
import axios from 'axios';
import router from '../router';

// Create axios instance
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      if (router.currentRoute.value.name !== 'login') {
        router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } });
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// =============================================================================
// API Modules
// =============================================================================

export const authApi = {
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  changePassword: (data) => api.put('/auth/password', data),
};

export const generatorApi = {
  // Status & Control
  getStatus: () => api.get('/status'),
  getState: () => api.get('/generator/state'),
  start: (durationMinutes, notes = null) => api.post('/generator/start', { duration_minutes: durationMinutes, notes }),
  stop: (reason = null) => api.post('/generator/stop', { reason }),

  // Victron Monitoring
  getVictronStatus: () => api.get('/victron/status'),

  // Override Control
  getOverride: () => api.get('/override'),
  enableOverride: (type) => api.post('/override/enable', { type }),
  disableOverride: () => api.post('/override/disable'),

  // History & Statistics
  getHistory: (limit = 10, offset = 0) => api.get('/generator/history', { params: { limit, offset } }),
  getStats: (days = 30) => api.get('/generator/stats', { params: { days } }),
};

export const scheduleApi = {
  list: (enabledOnly = false) => api.get('/schedule', { params: { enabled_only: enabledOnly } }),
  get: (id) => api.get(`/schedule/${id}`),
  create: (data) => api.post('/schedule', data),
  update: (id, data) => api.put(`/schedule/${id}`, data),
  delete: (id) => api.delete(`/schedule/${id}`),
  toggle: (id, enabled) => api.patch(`/schedule/${id}`, { enabled }),
};

export const healthApi = {
  getSlaveHealth: () => api.get('/health/slave'),
  getSlaveConnection: () => api.get('/health/slave/connection'),
  testHeartbeat: () => api.post('/health/test-heartbeat'),
  testWebhook: () => api.post('/health/test-webhook'),
};

export const systemApi = {
  health: () => api.get('/system/health'),
  healthFull: () => api.get('/system/health/full'),
  info: () => api.get('/system/info'),
  metrics: () => api.get('/system/metrics'),
  metricsCached: (historyMinutes = 60) => api.get('/system/host-metrics/cached', { params: { history_minutes: historyMinutes } }),
  network: () => api.get('/system/network'),
  tailscale: () => api.get('/system/tailscale'),
  terminalTargets: () => api.get('/system/terminal/targets'),
  reboot: () => api.post('/system/reboot'),
};

export const containersApi = {
  list: (all = true) => api.get('/containers/', { params: { all } }),
  get: (name) => api.get(`/containers/${name}`),
  stats: () => api.get('/containers/stats'),
  health: () => api.get('/containers/health'),
  start: (name) => api.post(`/containers/${name}/start`),
  stop: (name) => api.post(`/containers/${name}/stop`),
  restart: (name) => api.post(`/containers/${name}/restart`),
  logs: (name, params) => api.get(`/containers/${name}/logs`, { params }),
};

export const settingsApi = {
  getAll: () => api.get('/settings/'),
  get: (key) => api.get(`/settings/${key}`),
  update: (key, data) => api.put(`/settings/${key}`, data),

  // Webhook configuration
  getWebhooks: () => api.get('/settings/webhooks'),
  updateWebhooks: (data) => api.put('/settings/webhooks', data),
  testWebhook: (eventType) => api.post('/settings/webhooks/test', { event_type: eventType }),
};

export const configApi = {
  get: () => api.get('/config'),
  update: (data) => api.put('/config', data),
  createBackup: () => api.post('/backup'),
  downloadBackup: () => api.get('/backup/download', { responseType: 'blob' }),
};
```

---

## Pinia Stores

### src/stores/generator.js

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { generatorApi } from '@/services/api';
import { useNotificationStore } from './notifications';

export const useGeneratorStore = defineStore('generator', () => {
  // State
  const status = ref({
    running: false,
    start_time: null,
    runtime_seconds: null,
    trigger: 'idle',
    current_run_id: null,
  });
  const victron = ref({
    signal_active: false,
    gpio_pin: 17,
    last_change: null,
  });
  const override = ref({
    enabled: false,
    type: 'none',
  });
  const slaveConnection = ref({
    status: 'unknown',
    last_heartbeat: null,
    last_heartbeat_ago_seconds: null,
    missed_count: 0,
  });
  const stats = ref(null);
  const history = ref([]);
  const loading = ref(false);
  const error = ref(null);

  // Getters
  const isRunning = computed(() => status.value.running);

  const runtimeFormatted = computed(() => {
    if (!status.value.runtime_seconds) return '--:--:--';
    const hours = Math.floor(status.value.runtime_seconds / 3600);
    const minutes = Math.floor((status.value.runtime_seconds % 3600) / 60);
    const seconds = status.value.runtime_seconds % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  });

  const triggerLabel = computed(() => {
    const labels = {
      idle: 'Idle',
      victron: 'Victron',
      manual: 'Manual',
      scheduled: 'Scheduled',
    };
    return labels[status.value.trigger] || status.value.trigger;
  });

  const slaveConnected = computed(() => slaveConnection.value.status === 'connected');

  // Actions
  async function fetchStatus() {
    try {
      const response = await generatorApi.getStatus();
      const data = response.data;
      status.value = data.generator;
      victron.value = data.victron;
      override.value = data.override;
      slaveConnection.value = data.slave_connection;
      error.value = null;
    } catch (e) {
      error.value = e.message;
    }
  }

  async function start(durationMinutes, notes = null) {
    const notifications = useNotificationStore();
    loading.value = true;
    try {
      const response = await generatorApi.start(durationMinutes, notes);
      notifications.success('Generator started successfully');
      await fetchStatus();
      return response.data;
    } catch (e) {
      const message = e.response?.data?.detail || 'Failed to start generator';
      notifications.error(message);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function stop(reason = null) {
    const notifications = useNotificationStore();
    loading.value = true;
    try {
      const response = await generatorApi.stop(reason);
      notifications.success('Generator stopped');
      await fetchStatus();
      return response.data;
    } catch (e) {
      const message = e.response?.data?.detail || 'Failed to stop generator';
      notifications.error(message);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function enableOverride(type) {
    const notifications = useNotificationStore();
    try {
      const response = await generatorApi.enableOverride(type);
      override.value = response.data;
      notifications.warning(`Override enabled: ${type}`);
    } catch (e) {
      notifications.error('Failed to enable override');
    }
  }

  async function disableOverride() {
    const notifications = useNotificationStore();
    try {
      const response = await generatorApi.disableOverride();
      override.value = response.data;
      notifications.success('Override disabled');
    } catch (e) {
      notifications.error('Failed to disable override');
    }
  }

  async function fetchStats(days = 30) {
    try {
      const response = await generatorApi.getStats(days);
      stats.value = response.data;
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  }

  async function fetchHistory(limit = 10, offset = 0) {
    try {
      const response = await generatorApi.getHistory(limit, offset);
      history.value = response.data;
    } catch (e) {
      console.error('Failed to fetch history:', e);
    }
  }

  return {
    // State
    status,
    victron,
    override,
    slaveConnection,
    stats,
    history,
    loading,
    error,
    // Getters
    isRunning,
    runtimeFormatted,
    triggerLabel,
    slaveConnected,
    // Actions
    fetchStatus,
    start,
    stop,
    enableOverride,
    disableOverride,
    fetchStats,
    fetchHistory,
  };
});
```

### src/stores/containers.js

```javascript
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { containersApi } from '@/services/api';
import { useNotificationStore } from './notifications';

export const useContainerStore = defineStore('containers', () => {
  const containers = ref([]);
  const loading = ref(false);

  async function fetchContainers() {
    loading.value = true;
    try {
      const response = await containersApi.list();
      containers.value = response.data;
    } catch (e) {
      console.error('Failed to fetch containers:', e);
    } finally {
      loading.value = false;
    }
  }

  async function startContainer(name) {
    const notifications = useNotificationStore();
    try {
      await containersApi.start(name);
      notifications.success(`Container ${name} started`);
      await fetchContainers();
    } catch (e) {
      notifications.error(`Failed to start ${name}`);
      throw e;
    }
  }

  async function stopContainer(name) {
    const notifications = useNotificationStore();
    try {
      await containersApi.stop(name);
      notifications.success(`Container ${name} stopped`);
      await fetchContainers();
    } catch (e) {
      notifications.error(`Failed to stop ${name}`);
      throw e;
    }
  }

  async function restartContainer(name) {
    const notifications = useNotificationStore();
    try {
      await containersApi.restart(name);
      notifications.success(`Container ${name} restarted`);
      await fetchContainers();
    } catch (e) {
      notifications.error(`Failed to restart ${name}`);
      throw e;
    }
  }

  async function getContainerLogs(name, params) {
    try {
      const response = await containersApi.logs(name, params);
      return response.data;
    } catch (e) {
      console.error('Failed to fetch logs:', e);
      throw e;
    }
  }

  return {
    containers,
    loading,
    fetchContainers,
    startContainer,
    stopContainer,
    restartContainer,
    getContainerLogs,
  };
});
```

### src/stores/theme.js

```javascript
import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

export const useThemeStore = defineStore('theme', () => {
  const colorMode = ref(localStorage.getItem('theme') || 'dark');

  // Apply theme to document
  function applyTheme() {
    if (colorMode.value === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', colorMode.value);
  }

  function setColorMode(mode) {
    colorMode.value = mode;
    applyTheme();
  }

  function toggleTheme() {
    setColorMode(colorMode.value === 'dark' ? 'light' : 'dark');
  }

  // Apply on init
  applyTheme();

  return {
    colorMode,
    setColorMode,
    toggleTheme,
  };
});
```

### src/stores/notifications.js

```javascript
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref([]);
  let nextId = 0;

  function add(type, message, duration = 5000) {
    const id = nextId++;
    notifications.value.push({ id, type, message });

    if (duration > 0) {
      setTimeout(() => remove(id), duration);
    }
  }

  function remove(id) {
    const index = notifications.value.findIndex(n => n.id === id);
    if (index !== -1) {
      notifications.value.splice(index, 1);
    }
  }

  function success(message) { add('success', message); }
  function error(message) { add('error', message, 8000); }
  function warning(message) { add('warning', message); }
  function info(message) { add('info', message); }

  return {
    notifications,
    add,
    remove,
    success,
    error,
    warning,
    info,
  };
});
```

---

## Views

### DashboardView.vue

The Dashboard provides a system overview combining metrics from n8n_nginx with generator status:

**Sections:**
1. **Quick Stats Row** - CPU, Memory, Disk usage, Uptime (like n8n Dashboard)
2. **Generator Status Card** - Current running state, runtime, trigger type
3. **GenSlave Connection** - Heartbeat status, connectivity
4. **Charts** - CPU/Memory history (last hour)
5. **Container Summary** - Total, running, stopped, unhealthy counts
6. **Network I/O** - Download/upload rates

**Key Features:**
- Real-time metrics polling (every 30 seconds)
- Progress bars with color thresholds
- Click-through to containers view
- Generator status indicator in header

### GeneratorView.vue

The Generator view provides comprehensive generator control:

**Sections:**
1. **Generator Status** - Large status display (RUNNING/STOPPED), runtime timer
2. **Victron Monitor** - GPIO17 signal status, last change time
3. **Manual Control** - Duration input, Start/Stop buttons
4. **Override Panel** - Enable/disable manual override
5. **Recent Activity** - Last 5 runs summary
6. **Statistics** - Today/week/month runtime summaries

**Key Features:**
- Big green/red status indicator
- Live runtime counter when running
- Confirmation dialogs for start/stop
- Override warnings

### ScheduleView.vue

Schedule management for automated generator runs:

**Sections:**
1. **Upcoming Schedules** - Next scheduled runs
2. **Schedule List** - All schedules with enable/disable toggles
3. **Add Schedule Modal** - Create new scheduled runs

**Schedule Properties:**
- Name (optional)
- Scheduled start (date/time)
- Duration (minutes)
- Recurring (daily/weekly/custom)
- Enabled status

### HistoryView.vue

Generator run history and statistics:

**Sections:**
1. **Runtime Chart** - Bar chart of daily runtime (last 14 days)
2. **Statistics Summary** - Total runtime, run count, averages
3. **Run History Table** - Detailed list with pagination

**Table Columns:**
- Start time
- Stop time
- Duration
- Trigger type (Victron/Manual/Scheduled)
- Stop reason

### ContainersView.vue

Docker container management (adapted from n8n_nginx):

**Features:**
- Container list with status badges
- Expand/collapse for details
- CPU/Memory/Network stats
- Start/Stop/Restart actions
- Log viewer dialog
- Terminal link to System view

**Remove from n8n version:**
- n8n-specific container handling
- Notification settings per container
- Recreate with pull functionality

### SystemView.vue

System health and management (adapted from n8n_nginx):

**Tabs:**
1. **Health** - Comprehensive health checks, disk usage, container memory
2. **Network** - Interfaces, Tailscale status, DNS
3. **Terminal** - Web terminal to containers

**Remove from n8n version:**
- SSL certificate management (not needed)
- Cloudflare tunnel management (handled in Docker profiles)

### SettingsView.vue

Application settings (simplified from n8n_nginx):

**Tabs:**
1. **Appearance** - Light/Dark theme toggle
2. **Notifications** - Webhook URL configuration (simplified)
3. **Security** - Session timeout, login attempts
4. **Account** - Change password

---

## Webhook Notification Settings

### Simplified Notification System

Unlike the n8n_nginx complex notification system with services, groups, and rules, Gen Management uses a simple webhook configuration:

```javascript
// Settings structure
{
  webhooks: {
    enabled: true,
    base_url: "http://n8n:5678/webhook/generator",
    secret: "webhook-secret",
    events: {
      generator_started: true,
      generator_stopped: true,
      generator_failed: true,
      heartbeat_lost: true,
      heartbeat_restored: true,
      failsafe_triggered: true,
      schedule_executed: true,
      override_enabled: true,
      override_disabled: true,
      system_warning: true,
      system_error: true,
    }
  }
}
```

### WebhookSettings.vue Component

```vue
<script setup>
import { ref, onMounted } from 'vue';
import { settingsApi } from '@/services/api';
import { useNotificationStore } from '@/stores/notifications';

const notifications = useNotificationStore();
const webhooks = ref({
  enabled: false,
  base_url: '',
  secret: '',
  events: {},
});
const loading = ref(true);
const saving = ref(false);
const testing = ref(false);

const eventTypes = [
  { key: 'generator_started', label: 'Generator Started', description: 'When generator starts running' },
  { key: 'generator_stopped', label: 'Generator Stopped', description: 'When generator stops (any reason)' },
  { key: 'generator_failed', label: 'Generator Failed', description: 'When generator fails to start/stop' },
  { key: 'heartbeat_lost', label: 'Heartbeat Lost', description: 'When GenSlave connection is lost' },
  { key: 'heartbeat_restored', label: 'Heartbeat Restored', description: 'When GenSlave connection is restored' },
  { key: 'failsafe_triggered', label: 'Failsafe Triggered', description: 'When GenSlave triggers failsafe stop' },
  { key: 'schedule_executed', label: 'Schedule Executed', description: 'When scheduled run starts' },
  { key: 'override_enabled', label: 'Override Enabled', description: 'When manual override is enabled' },
  { key: 'override_disabled', label: 'Override Disabled', description: 'When manual override is disabled' },
  { key: 'system_warning', label: 'System Warning', description: 'High temp, low disk, etc.' },
  { key: 'system_error', label: 'System Error', description: 'Critical system errors' },
];

onMounted(async () => {
  try {
    const response = await settingsApi.getWebhooks();
    webhooks.value = response.data;
  } catch (e) {
    console.error('Failed to load webhook settings:', e);
  } finally {
    loading.value = false;
  }
});

async function save() {
  saving.value = true;
  try {
    await settingsApi.updateWebhooks(webhooks.value);
    notifications.success('Webhook settings saved');
  } catch (e) {
    notifications.error('Failed to save webhook settings');
  } finally {
    saving.value = false;
  }
}

async function testWebhook() {
  testing.value = true;
  try {
    const response = await settingsApi.testWebhook('test');
    if (response.data.success) {
      notifications.success(`Webhook test successful (${response.data.response_time_ms}ms)`);
    } else {
      notifications.error(`Webhook test failed: ${response.data.error}`);
    }
  } catch (e) {
    notifications.error('Webhook test failed');
  } finally {
    testing.value = false;
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Master Enable -->
    <div class="flex items-center justify-between p-4 rounded-lg bg-surface-hover">
      <div>
        <p class="font-medium text-primary">Enable Webhooks</p>
        <p class="text-sm text-secondary">Send notifications to external webhook URL</p>
      </div>
      <Toggle v-model="webhooks.enabled" />
    </div>

    <!-- Webhook URL -->
    <div :class="{ 'opacity-50 pointer-events-none': !webhooks.enabled }">
      <label class="block text-sm font-medium text-secondary mb-2">Webhook URL</label>
      <input
        v-model="webhooks.base_url"
        type="url"
        class="input-field"
        placeholder="https://n8n.example.com/webhook/generator"
      />
      <p class="text-xs text-muted mt-1">
        URL will receive POST requests with event data
      </p>
    </div>

    <!-- Secret -->
    <div :class="{ 'opacity-50 pointer-events-none': !webhooks.enabled }">
      <label class="block text-sm font-medium text-secondary mb-2">Webhook Secret</label>
      <input
        v-model="webhooks.secret"
        type="password"
        class="input-field"
        placeholder="Enter webhook secret"
      />
      <p class="text-xs text-muted mt-1">
        Sent in X-Webhook-Secret header for verification
      </p>
    </div>

    <!-- Event Types -->
    <div :class="{ 'opacity-50 pointer-events-none': !webhooks.enabled }">
      <h4 class="font-medium text-primary mb-3">Event Types</h4>
      <div class="space-y-2">
        <div
          v-for="event in eventTypes"
          :key="event.key"
          class="flex items-center gap-3 p-3 rounded-lg hover:bg-surface-hover"
        >
          <input
            type="checkbox"
            v-model="webhooks.events[event.key]"
            class="form-checkbox h-4 w-4 text-blue-600 rounded"
          />
          <div>
            <p class="text-sm font-medium text-primary">{{ event.label }}</p>
            <p class="text-xs text-muted">{{ event.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
      <button
        @click="testWebhook"
        :disabled="!webhooks.enabled || !webhooks.base_url || testing"
        class="btn btn-secondary"
      >
        {{ testing ? 'Testing...' : 'Test Webhook' }}
      </button>
      <button
        @click="save"
        :disabled="saving"
        class="btn btn-primary"
      >
        {{ saving ? 'Saving...' : 'Save Settings' }}
      </button>
    </div>
  </div>
</template>
```

---

## Common Components

### Card.vue

```vue
<script setup>
defineProps({
  title: String,
  subtitle: String,
  padding: {
    type: Boolean,
    default: true,
  },
});
</script>

<template>
  <div class="card">
    <div v-if="title" class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
      <h3 class="font-semibold text-primary">{{ title }}</h3>
      <p v-if="subtitle" class="text-sm text-muted">{{ subtitle }}</p>
    </div>
    <div :class="padding ? 'p-4' : ''">
      <slot></slot>
    </div>
  </div>
</template>
```

### StatusBadge.vue

```vue
<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
  size: {
    type: String,
    default: 'md', // sm, md
  },
});

const statusStyles = {
  running: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400',
  stopped: 'bg-gray-100 text-gray-600 dark:bg-gray-500/20 dark:text-gray-400',
  healthy: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400',
  unhealthy: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400',
  warning: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400',
  starting: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400',
  exited: 'bg-gray-100 text-gray-600 dark:bg-gray-500/20 dark:text-gray-400',
};

const sizeClasses = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
};

const badgeClass = computed(() => [
  'rounded-full font-medium inline-flex items-center',
  statusStyles[props.status] || statusStyles.stopped,
  sizeClasses[props.size],
]);
</script>

<template>
  <span :class="badgeClass">
    {{ status }}
  </span>
</template>
```

### ConfirmDialog.vue

```vue
<script setup>
const props = defineProps({
  open: Boolean,
  title: String,
  message: String,
  confirmText: { type: String, default: 'Confirm' },
  cancelText: { type: String, default: 'Cancel' },
  danger: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
});

const emit = defineEmits(['confirm', 'cancel']);
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/50" @click="emit('cancel')"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full border border-gray-200 dark:border-gray-700">
          <div class="p-6">
            <h3 class="text-lg font-semibold text-primary mb-2">{{ title }}</h3>
            <p class="text-secondary">{{ message }}</p>
          </div>
          <div class="px-6 py-4 bg-gray-50 dark:bg-gray-900/50 rounded-b-lg flex justify-end gap-3">
            <button @click="emit('cancel')" :disabled="loading" class="btn btn-secondary">
              {{ cancelText }}
            </button>
            <button
              @click="emit('confirm')"
              :disabled="loading"
              :class="['btn', danger ? 'btn-danger' : 'btn-primary']"
            >
              {{ loading ? 'Processing...' : confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
</style>
```

---

## Polling Configuration

### src/config/constants.js

```javascript
export const POLLING = {
  // Dashboard metrics - every 30 seconds
  DASHBOARD_METRICS: 30000,

  // Generator status - every 5 seconds
  GENERATOR_STATUS: 5000,

  // Container stats - every 30 seconds
  CONTAINER_STATS: 30000,

  // Health checks - every 60 seconds
  HEALTH_CHECKS: 60000,
};
```

### src/composables/usePoll.js

```javascript
import { onMounted, onUnmounted, ref } from 'vue';

export function usePoll(callback, interval, immediate = true) {
  const intervalId = ref(null);

  function start() {
    if (immediate) callback();
    intervalId.value = setInterval(callback, interval);
  }

  function stop() {
    if (intervalId.value) {
      clearInterval(intervalId.value);
      intervalId.value = null;
    }
  }

  onMounted(start);
  onUnmounted(stop);

  return { start, stop };
}
```

---

## Key Differences from n8n_nginx

### Removed Features
1. **Backup Management** - No backup/restore views
2. **Flows View** - No n8n workflow management
3. **Complex Notifications** - No services, groups, rules (replaced with simple webhooks)
4. **ntfy Integration** - Not needed for generator control
5. **External Routes** - nginx routes managed via Docker
6. **n8n API Key** - Not applicable

### Added Features
1. **Generator View** - Dedicated generator control page
2. **Schedule View** - Scheduled run management
3. **History View** - Generator run history with statistics
4. **Victron Monitoring** - GPIO17 signal status display
5. **Override Controls** - Manual override management
6. **Runtime Statistics** - Generator usage analytics

### Modified Features
1. **Dashboard** - Added generator status summary
2. **System View** - Removed SSL/Cloudflare management
3. **Settings** - Simplified to webhooks + appearance + security
4. **Containers** - Removed n8n-specific features

---

## Agent Implementation Checklist

### Phase 1: Project Setup
- [ ] Initialize Vue project with Vite and pnpm
- [ ] Configure Tailwind CSS with dark mode
- [ ] Set up project structure (directories)
- [ ] Create main.css with custom styles
- [ ] Configure Vue Router
- [ ] Set up API service with axios

### Phase 2: Stores
- [ ] Create auth store
- [ ] Create generator store
- [ ] Create containers store
- [ ] Create system store
- [ ] Create theme store
- [ ] Create notifications store

### Phase 3: Common Components
- [ ] Card.vue
- [ ] StatusBadge.vue
- [ ] LoadingSpinner.vue
- [ ] EmptyState.vue
- [ ] ConfirmDialog.vue
- [ ] SystemMetricsLoader.vue
- [ ] Toggle.vue
- [ ] Toast notifications

### Phase 4: Views
- [ ] LoginView.vue
- [ ] DashboardView.vue (adapted from n8n)
- [ ] GeneratorView.vue (new)
- [ ] ScheduleView.vue (new)
- [ ] HistoryView.vue (new)
- [ ] ContainersView.vue (adapted from n8n)
- [ ] SystemView.vue (adapted from n8n)
- [ ] SettingsView.vue (simplified)

### Phase 5: Generator Components
- [ ] GeneratorStatus.vue
- [ ] VictronMonitor.vue
- [ ] ManualControl.vue
- [ ] OverridePanel.vue
- [ ] RuntimeChart.vue

### Phase 6: Settings Components
- [ ] WebhookSettings.vue
- [ ] AppearanceSettings.vue

### Phase 7: Testing & Polish
- [ ] Test all API integrations
- [ ] Test polling and real-time updates
- [ ] Verify responsive design
- [ ] Test dark/light themes
- [ ] Test authentication flow
- [ ] Build production bundle

---

## Related Documents

- `01-project-structure.md` - Project conventions
- `03-genmaster-backend.md` - API endpoints this frontend consumes
- `06-docker-infrastructure.md` - Nginx static file serving
- `05-genslave-backend.md` - GenSlave API for health monitoring
