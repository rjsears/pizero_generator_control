# Agent Handoff: GenMaster Frontend

## Purpose
This document provides complete specifications for building the GenMaster Vue.js frontend, including all components, views, API integration, and styling with Tailwind CSS.

---

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Vue.js | 3.4+ | Frontend framework (Composition API) |
| Vite | 5.0+ | Build tool |
| Tailwind CSS | 3.4+ | Utility-first CSS |
| Pinia | 2.1+ | State management |
| Chart.js | 4.4+ | Runtime graphs |
| vue-chartjs | 5.3+ | Vue wrapper for Chart.js |
| Axios | 1.6+ | HTTP client |

---

## Project Structure

```
genmaster/frontend/
├── src/
│   ├── main.js                 # App entry point
│   ├── App.vue                 # Root component
│   ├── api/                    # API client modules
│   │   ├── index.js            # Axios instance
│   │   ├── generator.js        # Generator endpoints
│   │   ├── health.js           # Health endpoints
│   │   ├── system.js           # System endpoints
│   │   ├── schedule.js         # Schedule endpoints
│   │   └── config.js           # Config endpoints
│   ├── components/             # Reusable components
│   │   ├── StatusCard.vue
│   │   ├── HealthGauge.vue
│   │   ├── RuntimeChart.vue
│   │   ├── ScheduleTable.vue
│   │   ├── ScheduleModal.vue
│   │   ├── ConfirmDialog.vue
│   │   ├── ToastNotification.vue
│   │   ├── LoadingSpinner.vue
│   │   └── Toggle.vue
│   ├── views/                  # Page components
│   │   ├── Dashboard.vue       # Main dashboard
│   │   ├── History.vue         # Run history
│   │   ├── Schedule.vue        # Schedule management
│   │   └── Settings.vue        # Configuration
│   ├── stores/                 # Pinia stores
│   │   ├── index.js
│   │   ├── generator.js        # Generator state
│   │   ├── system.js           # System state
│   │   └── notifications.js    # Toast notifications
│   ├── composables/            # Reusable logic
│   │   ├── usePolling.js       # Polling helper
│   │   └── useFormatters.js    # Date/time formatters
│   ├── router/
│   │   └── index.js            # Vue Router config
│   └── assets/
│       └── styles/
│           └── main.css        # Tailwind imports
├── index.html
├── package.json
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
  "name": "genmaster-frontend",
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
    "vue-chartjs": "^5.3.0"
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
  theme: {
    extend: {
      colors: {
        // Custom color palette
        'gen-green': '#22C55E',
        'gen-red': '#EF4444',
        'gen-amber': '#F59E0B',
        'gen-gray': {
          50: '#F9FAFB',
          100: '#F3F4F6',
          200: '#E5E7EB',
          300: '#D1D5DB',
          400: '#9CA3AF',
          500: '#6B7280',
          600: '#4B5563',
          700: '#374151',
          800: '#1F2937',
          900: '#111827'
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'monospace']
      }
    }
  },
  plugins: []
};
```

### postcss.config.js

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {}
  }
};
```

### src/assets/styles/main.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gen-gray-900 text-gen-gray-50 antialiased;
  }
}

@layer components {
  .card {
    @apply bg-gen-gray-800 rounded-lg p-4 shadow-lg;
  }

  .card-header {
    @apply text-sm font-semibold text-gen-gray-400 uppercase tracking-wide mb-3;
  }

  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-colors duration-200;
  }

  .btn-primary {
    @apply bg-gen-green text-white hover:bg-green-600;
  }

  .btn-danger {
    @apply bg-gen-red text-white hover:bg-red-600;
  }

  .btn-secondary {
    @apply bg-gen-gray-700 text-gen-gray-200 hover:bg-gen-gray-600;
  }

  .btn-disabled {
    @apply opacity-50 cursor-not-allowed;
  }

  .status-dot {
    @apply w-3 h-3 rounded-full inline-block mr-2;
  }

  .status-running {
    @apply bg-gen-green animate-pulse;
  }

  .status-stopped {
    @apply bg-gen-gray-500;
  }

  .status-warning {
    @apply bg-gen-amber;
  }

  .status-error {
    @apply bg-gen-red;
  }

  .input {
    @apply bg-gen-gray-700 border border-gen-gray-600 rounded-lg px-3 py-2
           text-gen-gray-100 placeholder-gen-gray-500
           focus:outline-none focus:ring-2 focus:ring-gen-green focus:border-transparent;
  }
}
```

---

## Entry Point & App Shell

### index.html

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GenMaster Control Panel</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

### src/main.js

```javascript
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import './assets/styles/main.css';

const app = createApp(App);

app.use(createPinia());
app.use(router);

app.mount('#app');
```

### src/App.vue

```vue
<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { RouterView, RouterLink, useRoute } from 'vue-router';
import { useGeneratorStore } from '@/stores/generator';
import { useSystemStore } from '@/stores/system';
import { useNotificationStore } from '@/stores/notifications';
import ToastNotification from '@/components/ToastNotification.vue';

const route = useRoute();
const generatorStore = useGeneratorStore();
const systemStore = useSystemStore();
const notificationStore = useNotificationStore();

const navItems = [
  { path: '/', label: 'Dashboard', icon: 'dashboard' },
  { path: '/history', label: 'History', icon: 'history' },
  { path: '/schedule', label: 'Schedule', icon: 'schedule' },
  { path: '/settings', label: 'Settings', icon: 'settings' }
];

let pollInterval = null;

onMounted(() => {
  // Initial fetch
  generatorStore.fetchStatus();
  systemStore.fetchHealth();

  // Start polling every 5 seconds
  pollInterval = setInterval(() => {
    generatorStore.fetchStatus();
    systemStore.fetchHealth();
  }, 5000);
});

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval);
  }
});
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-gen-gray-800 border-b border-gen-gray-700 px-4 py-3">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <h1 class="text-xl font-bold text-gen-gray-100">
          GenMaster Control Panel
        </h1>

        <!-- Quick Status -->
        <div class="flex items-center gap-4">
          <div class="flex items-center">
            <span
              class="status-dot"
              :class="generatorStore.isRunning ? 'status-running' : 'status-stopped'"
            ></span>
            <span class="text-sm">
              Generator: {{ generatorStore.isRunning ? 'Running' : 'Stopped' }}
            </span>
          </div>
          <div class="flex items-center">
            <span
              class="status-dot"
              :class="{
                'status-running': systemStore.slaveConnected,
                'status-error': !systemStore.slaveConnected
              }"
            ></span>
            <span class="text-sm">
              Slave: {{ systemStore.slaveConnected ? 'Online' : 'Offline' }}
            </span>
          </div>
        </div>
      </div>
    </header>

    <!-- Navigation -->
    <nav class="bg-gen-gray-800 border-b border-gen-gray-700">
      <div class="max-w-7xl mx-auto px-4">
        <div class="flex gap-1">
          <RouterLink
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="px-4 py-3 text-sm font-medium transition-colors"
            :class="[
              route.path === item.path
                ? 'text-gen-green border-b-2 border-gen-green'
                : 'text-gen-gray-400 hover:text-gen-gray-200'
            ]"
          >
            {{ item.label }}
          </RouterLink>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-1 p-4">
      <div class="max-w-7xl mx-auto">
        <RouterView />
      </div>
    </main>

    <!-- Footer -->
    <footer class="bg-gen-gray-800 border-t border-gen-gray-700 px-4 py-2">
      <div class="max-w-7xl mx-auto text-center text-sm text-gen-gray-500">
        GenMaster v1.0.0
      </div>
    </footer>

    <!-- Toast Notifications -->
    <ToastNotification />
  </div>
</template>
```

### src/router/index.js

```javascript
import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '@/views/Dashboard.vue';
import History from '@/views/History.vue';
import Schedule from '@/views/Schedule.vue';
import Settings from '@/views/Settings.vue';

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/history',
    name: 'History',
    component: History
  },
  {
    path: '/schedule',
    name: 'Schedule',
    component: Schedule
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
```

---

## API Client

### src/api/index.js

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    console.error('API Error:', message);
    return Promise.reject(error);
  }
);

export default api;
```

### src/api/generator.js

```javascript
import api from './index';

export const generatorApi = {
  getStatus() {
    return api.get('/status');
  },

  getState() {
    return api.get('/generator/state');
  },

  start(durationMinutes, notes = null) {
    return api.post('/generator/start', {
      duration_minutes: durationMinutes,
      notes
    });
  },

  stop(reason = null) {
    return api.post('/generator/stop', {
      reason
    });
  },

  getHistory(limit = 10, offset = 0) {
    return api.get('/generator/history', {
      params: { limit, offset }
    });
  },

  getStats(days = 30) {
    return api.get('/generator/stats', {
      params: { days }
    });
  }
};
```

### src/api/health.js

```javascript
import api from './index';

export const healthApi = {
  getSlaveHealth() {
    return api.get('/health/slave');
  },

  testHeartbeat() {
    return api.post('/health/test-heartbeat');
  },

  testWebhook() {
    return api.post('/health/test-webhook');
  }
};
```

### src/api/system.js

```javascript
import api from './index';

export const systemApi = {
  getHealth() {
    return api.get('/system/health');
  },

  getAllHealth() {
    return api.get('/system/health/all');
  },

  getVictronStatus() {
    return api.get('/system/victron');
  },

  reboot() {
    return api.post('/system/reboot');
  },

  getOverrideStatus() {
    return api.get('/override');
  },

  enableOverride(type) {
    return api.post('/override/enable', { type });
  },

  disableOverride() {
    return api.post('/override/disable');
  }
};
```

### src/api/schedule.js

```javascript
import api from './index';

export const scheduleApi = {
  list(enabledOnly = false) {
    return api.get('/schedule', {
      params: { enabled_only: enabledOnly }
    });
  },

  get(id) {
    return api.get(`/schedule/${id}`);
  },

  create(data) {
    return api.post('/schedule', data);
  },

  update(id, data) {
    return api.put(`/schedule/${id}`, data);
  },

  delete(id) {
    return api.delete(`/schedule/${id}`);
  }
};
```

### src/api/config.js

```javascript
import api from './index';

export const configApi = {
  get() {
    return api.get('/config');
  },

  update(data) {
    return api.put('/config', data);
  },

  createBackup() {
    return api.post('/backup');
  },

  listBackups() {
    return api.get('/backup/list');
  },

  downloadBackup() {
    return api.get('/backup/download', {
      responseType: 'blob'
    });
  }
};
```

---

## Pinia Stores

### src/stores/index.js

```javascript
export { useGeneratorStore } from './generator';
export { useSystemStore } from './system';
export { useNotificationStore } from './notifications';
```

### src/stores/generator.js

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { generatorApi } from '@/api/generator';
import { useNotificationStore } from './notifications';

export const useGeneratorStore = defineStore('generator', () => {
  // State
  const status = ref({
    running: false,
    start_time: null,
    runtime_seconds: null,
    trigger: 'idle',
    current_run_id: null
  });
  const victron = ref({
    signal_active: false,
    gpio_pin: 17,
    last_change: null
  });
  const override = ref({
    enabled: false,
    type: 'none'
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
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  });
  const triggerLabel = computed(() => {
    const labels = {
      idle: 'Idle',
      victron: 'Victron',
      manual: 'Manual',
      scheduled: 'Scheduled'
    };
    return labels[status.value.trigger] || status.value.trigger;
  });

  // Actions
  async function fetchStatus() {
    try {
      const response = await generatorApi.getStatus();
      const data = response.data;

      status.value = data.generator;
      victron.value = data.victron;
      override.value = data.override;

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

  async function fetchStats(days = 30) {
    try {
      const response = await generatorApi.getStats(days);
      stats.value = response.data;
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  }

  async function fetchHistory(limit = 10) {
    try {
      const response = await generatorApi.getHistory(limit);
      history.value = response.data;
    } catch (e) {
      console.error('Failed to fetch history:', e);
    }
  }

  async function enableOverride(type) {
    const notifications = useNotificationStore();
    try {
      const response = await fetch('/api/override/enable', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type })
      });
      const data = await response.json();
      override.value = data;
      notifications.warning(`Override enabled: ${type}`);
    } catch (e) {
      notifications.error('Failed to enable override');
    }
  }

  async function disableOverride() {
    const notifications = useNotificationStore();
    try {
      const response = await fetch('/api/override/disable', {
        method: 'POST'
      });
      const data = await response.json();
      override.value = data;
      notifications.success('Override disabled');
    } catch (e) {
      notifications.error('Failed to disable override');
    }
  }

  return {
    // State
    status,
    victron,
    override,
    stats,
    history,
    loading,
    error,
    // Getters
    isRunning,
    runtimeFormatted,
    triggerLabel,
    // Actions
    fetchStatus,
    start,
    stop,
    fetchStats,
    fetchHistory,
    enableOverride,
    disableOverride
  };
});
```

### src/stores/system.js

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { systemApi } from '@/api/system';
import { healthApi } from '@/api/health';

export const useSystemStore = defineStore('system', () => {
  // State
  const masterHealth = ref(null);
  const slaveHealth = ref(null);
  const slaveConnection = ref({
    status: 'unknown',
    last_heartbeat: null,
    missed_count: 0
  });

  // Getters
  const slaveConnected = computed(() =>
    slaveConnection.value.status === 'connected'
  );

  const masterHealthStatus = computed(() =>
    masterHealth.value?.health_status || 'unknown'
  );

  const slaveHealthStatus = computed(() =>
    slaveHealth.value?.health_status || 'unknown'
  );

  // Actions
  async function fetchHealth() {
    try {
      // Fetch master health
      const masterResponse = await systemApi.getHealth();
      masterHealth.value = masterResponse.data;

      // Fetch slave connection status
      const slaveResponse = await healthApi.getSlaveHealth();
      slaveConnection.value = slaveResponse.data;

      // Try to get slave system health if connected
      if (slaveConnection.value.status === 'connected') {
        try {
          const allHealth = await systemApi.getAllHealth();
          slaveHealth.value = allHealth.data.genslave;
        } catch {
          slaveHealth.value = null;
        }
      }
    } catch (e) {
      console.error('Failed to fetch health:', e);
    }
  }

  async function testHeartbeat() {
    try {
      const response = await healthApi.testHeartbeat();
      return response.data;
    } catch (e) {
      throw e;
    }
  }

  async function testWebhook() {
    try {
      const response = await healthApi.testWebhook();
      return response.data;
    } catch (e) {
      throw e;
    }
  }

  return {
    masterHealth,
    slaveHealth,
    slaveConnection,
    slaveConnected,
    masterHealthStatus,
    slaveHealthStatus,
    fetchHealth,
    testHeartbeat,
    testWebhook
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
      setTimeout(() => {
        remove(id);
      }, duration);
    }
  }

  function remove(id) {
    const index = notifications.value.findIndex(n => n.id === id);
    if (index !== -1) {
      notifications.value.splice(index, 1);
    }
  }

  function success(message) {
    add('success', message);
  }

  function error(message) {
    add('error', message, 8000);
  }

  function warning(message) {
    add('warning', message);
  }

  function info(message) {
    add('info', message);
  }

  return {
    notifications,
    add,
    remove,
    success,
    error,
    warning,
    info
  };
});
```

---

## Components

### src/components/StatusCard.vue

```vue
<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <div class="card">
    <div class="card-header">{{ title }}</div>
    <div v-if="loading" class="flex justify-center py-4">
      <LoadingSpinner />
    </div>
    <div v-else>
      <slot></slot>
    </div>
  </div>
</template>
```

### src/components/HealthGauge.vue

```vue
<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: Number,
    required: true
  },
  max: {
    type: Number,
    default: 100
  },
  unit: {
    type: String,
    default: '%'
  },
  warningThreshold: {
    type: Number,
    default: 70
  },
  criticalThreshold: {
    type: Number,
    default: 90
  }
});

const percentage = computed(() => (props.value / props.max) * 100);

const barColor = computed(() => {
  if (percentage.value >= props.criticalThreshold) return 'bg-gen-red';
  if (percentage.value >= props.warningThreshold) return 'bg-gen-amber';
  return 'bg-gen-green';
});

const textColor = computed(() => {
  if (percentage.value >= props.criticalThreshold) return 'text-gen-red';
  if (percentage.value >= props.warningThreshold) return 'text-gen-amber';
  return 'text-gen-gray-300';
});
</script>

<template>
  <div class="mb-3">
    <div class="flex justify-between text-sm mb-1">
      <span class="text-gen-gray-400">{{ label }}</span>
      <span :class="textColor">{{ value }}{{ unit }}</span>
    </div>
    <div class="h-2 bg-gen-gray-700 rounded-full overflow-hidden">
      <div
        class="h-full rounded-full transition-all duration-300"
        :class="barColor"
        :style="{ width: `${percentage}%` }"
      ></div>
    </div>
  </div>
</template>
```

### src/components/RuntimeChart.vue

```vue
<script setup>
import { ref, watch, onMounted } from 'vue';
import { Bar } from 'vue-chartjs';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
});

const chartData = ref({
  labels: [],
  datasets: []
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const hours = Math.floor(context.raw / 60);
          const minutes = context.raw % 60;
          return `${hours}h ${minutes}m`;
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        color: '#374151'
      },
      ticks: {
        color: '#9CA3AF'
      }
    },
    y: {
      grid: {
        color: '#374151'
      },
      ticks: {
        color: '#9CA3AF',
        callback: (value) => `${Math.floor(value / 60)}h`
      }
    }
  }
};

function updateChart() {
  // Group runs by date
  const byDate = {};
  props.data.forEach(run => {
    const date = new Date(run.start_time * 1000).toLocaleDateString();
    if (!byDate[date]) byDate[date] = 0;
    byDate[date] += (run.duration_seconds || 0) / 60; // Convert to minutes
  });

  chartData.value = {
    labels: Object.keys(byDate).slice(-14), // Last 14 days
    datasets: [{
      data: Object.values(byDate).slice(-14),
      backgroundColor: '#22C55E',
      borderRadius: 4
    }]
  };
}

watch(() => props.data, updateChart, { immediate: true });
</script>

<template>
  <div class="h-64">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>
```

### src/components/ScheduleTable.vue

```vue
<script setup>
import { computed } from 'vue';

const props = defineProps({
  schedules: {
    type: Array,
    required: true
  }
});

const emit = defineEmits(['edit', 'delete', 'toggle']);

function formatDate(timestamp) {
  if (!timestamp) return '--';
  return new Date(timestamp * 1000).toLocaleString();
}

function formatDuration(minutes) {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="text-left text-gen-gray-400 border-b border-gen-gray-700">
          <th class="py-2 px-3">Name</th>
          <th class="py-2 px-3">Next Run</th>
          <th class="py-2 px-3">Duration</th>
          <th class="py-2 px-3">Recurring</th>
          <th class="py-2 px-3">Status</th>
          <th class="py-2 px-3">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="schedule in schedules"
          :key="schedule.id"
          class="border-b border-gen-gray-700 hover:bg-gen-gray-750"
        >
          <td class="py-3 px-3">{{ schedule.name || `Schedule #${schedule.id}` }}</td>
          <td class="py-3 px-3">{{ formatDate(schedule.next_execution) }}</td>
          <td class="py-3 px-3">{{ formatDuration(schedule.duration_minutes) }}</td>
          <td class="py-3 px-3">
            <span v-if="schedule.recurring" class="text-gen-green">
              {{ schedule.recurrence_pattern }}
            </span>
            <span v-else class="text-gen-gray-500">Once</span>
          </td>
          <td class="py-3 px-3">
            <span
              class="px-2 py-1 rounded text-xs"
              :class="schedule.enabled
                ? 'bg-gen-green/20 text-gen-green'
                : 'bg-gen-gray-600 text-gen-gray-400'"
            >
              {{ schedule.enabled ? 'Active' : 'Disabled' }}
            </span>
          </td>
          <td class="py-3 px-3">
            <div class="flex gap-2">
              <button
                @click="emit('edit', schedule)"
                class="text-gen-gray-400 hover:text-gen-gray-200"
              >
                Edit
              </button>
              <button
                @click="emit('delete', schedule)"
                class="text-gen-red hover:text-red-400"
              >
                Delete
              </button>
            </div>
          </td>
        </tr>
        <tr v-if="schedules.length === 0">
          <td colspan="6" class="py-8 text-center text-gen-gray-500">
            No scheduled runs
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
```

### src/components/ConfirmDialog.vue

```vue
<script setup>
const props = defineProps({
  show: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: 'Confirm'
  },
  message: {
    type: String,
    required: true
  },
  confirmText: {
    type: String,
    default: 'Confirm'
  },
  cancelText: {
    type: String,
    default: 'Cancel'
  },
  danger: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['confirm', 'cancel']);
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center"
    >
      <!-- Backdrop -->
      <div
        class="absolute inset-0 bg-black/60"
        @click="emit('cancel')"
      ></div>

      <!-- Dialog -->
      <div class="relative bg-gen-gray-800 rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
        <h3 class="text-lg font-semibold mb-2">{{ title }}</h3>
        <p class="text-gen-gray-400 mb-6">{{ message }}</p>

        <div class="flex justify-end gap-3">
          <button
            @click="emit('cancel')"
            class="btn btn-secondary"
          >
            {{ cancelText }}
          </button>
          <button
            @click="emit('confirm')"
            class="btn"
            :class="danger ? 'btn-danger' : 'btn-primary'"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
```

### src/components/ToastNotification.vue

```vue
<script setup>
import { useNotificationStore } from '@/stores/notifications';

const store = useNotificationStore();

const typeStyles = {
  success: 'bg-gen-green/20 border-gen-green text-gen-green',
  error: 'bg-gen-red/20 border-gen-red text-gen-red',
  warning: 'bg-gen-amber/20 border-gen-amber text-gen-amber',
  info: 'bg-blue-500/20 border-blue-500 text-blue-400'
};
</script>

<template>
  <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
    <TransitionGroup name="toast">
      <div
        v-for="notification in store.notifications"
        :key="notification.id"
        class="px-4 py-3 rounded-lg border shadow-lg min-w-[300px]"
        :class="typeStyles[notification.type]"
      >
        <div class="flex justify-between items-start">
          <span>{{ notification.message }}</span>
          <button
            @click="store.remove(notification.id)"
            class="ml-4 opacity-60 hover:opacity-100"
          >
            &times;
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
```

### src/components/Toggle.vue

```vue
<script setup>
const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true
  },
  disabled: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue']);

function toggle() {
  if (!props.disabled) {
    emit('update:modelValue', !props.modelValue);
  }
}
</script>

<template>
  <button
    type="button"
    @click="toggle"
    class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
    :class="[
      modelValue ? 'bg-gen-green' : 'bg-gen-gray-600',
      disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
    ]"
  >
    <span
      class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
      :class="modelValue ? 'translate-x-6' : 'translate-x-1'"
    />
  </button>
</template>
```

### src/components/LoadingSpinner.vue

```vue
<template>
  <div class="animate-spin rounded-full h-6 w-6 border-2 border-gen-gray-600 border-t-gen-green"></div>
</template>
```

---

## Views

### src/views/Dashboard.vue

```vue
<script setup>
import { ref, onMounted } from 'vue';
import { useGeneratorStore } from '@/stores/generator';
import { useSystemStore } from '@/stores/system';
import StatusCard from '@/components/StatusCard.vue';
import HealthGauge from '@/components/HealthGauge.vue';
import RuntimeChart from '@/components/RuntimeChart.vue';
import Toggle from '@/components/Toggle.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';

const generatorStore = useGeneratorStore();
const systemStore = useSystemStore();

const showStartDialog = ref(false);
const showStopDialog = ref(false);
const startDuration = ref(30);

onMounted(() => {
  generatorStore.fetchStats();
  generatorStore.fetchHistory(30);
});

async function handleStart() {
  await generatorStore.start(startDuration.value);
  showStartDialog.value = false;
}

async function handleStop() {
  await generatorStore.stop('manual');
  showStopDialog.value = false;
}

function formatRuntime(seconds) {
  if (!seconds) return '--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}
</script>

<template>
  <div class="space-y-4">
    <!-- Top Row: Generator Status & Communication -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Generator Status -->
      <StatusCard title="Generator Status">
        <div class="flex items-center mb-4">
          <span
            class="status-dot w-4 h-4"
            :class="generatorStore.isRunning ? 'status-running' : 'status-stopped'"
          ></span>
          <span class="text-2xl font-bold">
            {{ generatorStore.isRunning ? 'RUNNING' : 'STOPPED' }}
          </span>
        </div>

        <div v-if="generatorStore.isRunning" class="space-y-2 mb-4">
          <div class="flex justify-between text-sm">
            <span class="text-gen-gray-400">Runtime</span>
            <span class="font-mono">{{ generatorStore.runtimeFormatted }}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gen-gray-400">Trigger</span>
            <span>{{ generatorStore.triggerLabel }}</span>
          </div>
        </div>

        <div class="flex gap-2">
          <button
            v-if="!generatorStore.isRunning"
            @click="showStartDialog = true"
            class="btn btn-primary flex-1"
            :disabled="generatorStore.loading"
          >
            Start Generator
          </button>
          <button
            v-else
            @click="showStopDialog = true"
            class="btn btn-danger flex-1"
            :disabled="generatorStore.loading"
          >
            Stop Generator
          </button>
        </div>
      </StatusCard>

      <!-- Communication Status -->
      <StatusCard title="Communication">
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-gen-gray-400">GenSlave</span>
            <div class="flex items-center">
              <span
                class="status-dot"
                :class="systemStore.slaveConnected ? 'status-running' : 'status-error'"
              ></span>
              <span>{{ systemStore.slaveConnected ? 'Online' : 'Offline' }}</span>
            </div>
          </div>

          <div class="flex justify-between text-sm">
            <span class="text-gen-gray-400">Last Heartbeat</span>
            <span>
              {{ systemStore.slaveConnection.last_heartbeat_ago_seconds
                ? `${systemStore.slaveConnection.last_heartbeat_ago_seconds}s ago`
                : '--' }}
            </span>
          </div>

          <div class="flex justify-between text-sm">
            <span class="text-gen-gray-400">Missed</span>
            <span :class="systemStore.slaveConnection.missed_count > 0 ? 'text-gen-amber' : ''">
              {{ systemStore.slaveConnection.missed_count }}
            </span>
          </div>

          <button
            @click="systemStore.testHeartbeat()"
            class="btn btn-secondary w-full text-sm"
          >
            Test Connection
          </button>
        </div>
      </StatusCard>
    </div>

    <!-- Second Row: Victron Input & Override -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Victron Input -->
      <StatusCard title="Victron Input">
        <div class="flex items-center justify-between">
          <div>
            <div class="flex items-center mb-1">
              <span
                class="status-dot"
                :class="generatorStore.victron.signal_active ? 'status-running' : 'status-stopped'"
              ></span>
              <span class="text-lg font-semibold">
                GPIO17: {{ generatorStore.victron.signal_active ? 'ACTIVE' : 'INACTIVE' }}
              </span>
            </div>
            <p class="text-sm text-gen-gray-400">
              {{ generatorStore.victron.signal_active
                ? 'Run Requested'
                : 'No Run Request' }}
            </p>
          </div>
        </div>
      </StatusCard>

      <!-- Manual Override -->
      <StatusCard title="Manual Override">
        <div class="space-y-3">
          <div class="flex justify-between items-center">
            <span>Override Active</span>
            <Toggle
              :model-value="generatorStore.override.enabled"
              @update:model-value="val => val
                ? generatorStore.enableOverride('force_stop')
                : generatorStore.disableOverride()"
            />
          </div>

          <div v-if="generatorStore.override.enabled" class="text-sm">
            <span class="text-gen-gray-400">Mode: </span>
            <span class="text-gen-amber">{{ generatorStore.override.type }}</span>
          </div>

          <p class="text-xs text-gen-gray-500">
            Override ignores Victron signals
          </p>
        </div>
      </StatusCard>
    </div>

    <!-- Manual Start Section -->
    <StatusCard title="Manual Start">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <label class="text-gen-gray-400">Duration:</label>
          <input
            v-model.number="startDuration"
            type="number"
            min="1"
            max="480"
            class="input w-20"
          />
          <span class="text-gen-gray-400">minutes</span>
        </div>
        <button
          @click="showStartDialog = true"
          class="btn btn-primary"
          :disabled="generatorStore.isRunning || generatorStore.loading"
        >
          Start Generator
        </button>
      </div>
    </StatusCard>

    <!-- Statistics -->
    <StatusCard title="Runtime Statistics (Last 30 Days)">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <div class="text-2xl font-bold text-gen-green">
            {{ generatorStore.stats?.total_runtime_formatted || '--' }}
          </div>
          <div class="text-sm text-gen-gray-400">Total Runtime</div>
        </div>
        <div>
          <div class="text-2xl font-bold">
            {{ generatorStore.stats?.run_count || 0 }}
          </div>
          <div class="text-sm text-gen-gray-400">Run Count</div>
        </div>
        <div>
          <div class="text-2xl font-bold">
            {{ formatRuntime(generatorStore.stats?.avg_runtime_seconds) }}
          </div>
          <div class="text-sm text-gen-gray-400">Avg Runtime</div>
        </div>
        <div>
          <div class="text-2xl font-bold">
            {{ generatorStore.stats?.by_trigger?.victron?.count || 0 }}
          </div>
          <div class="text-sm text-gen-gray-400">Victron Triggers</div>
        </div>
      </div>

      <RuntimeChart :data="generatorStore.history" />
    </StatusCard>

    <!-- System Health -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- GenMaster Health -->
      <StatusCard title="GenMaster Health">
        <template v-if="systemStore.masterHealth">
          <HealthGauge
            label="CPU"
            :value="systemStore.masterHealth.cpu_percent"
          />
          <HealthGauge
            label="RAM"
            :value="systemStore.masterHealth.ram_percent"
            :warning-threshold="80"
          />
          <HealthGauge
            label="Disk"
            :value="systemStore.masterHealth.disk_percent"
            :warning-threshold="80"
          />
          <div class="flex justify-between text-sm mt-3">
            <span class="text-gen-gray-400">Temperature</span>
            <span :class="systemStore.masterHealth.temperature_celsius > 70 ? 'text-gen-amber' : ''">
              {{ systemStore.masterHealth.temperature_celsius || '--' }}°C
            </span>
          </div>
        </template>
        <div v-else class="text-gen-gray-500">Loading...</div>
      </StatusCard>

      <!-- GenSlave Health -->
      <StatusCard title="GenSlave Health">
        <template v-if="systemStore.slaveHealth">
          <HealthGauge
            label="CPU"
            :value="systemStore.slaveHealth.cpu_percent"
          />
          <HealthGauge
            label="RAM"
            :value="systemStore.slaveHealth.ram_percent"
            :warning-threshold="80"
          />
          <HealthGauge
            label="Disk"
            :value="systemStore.slaveHealth.disk_percent"
            :warning-threshold="80"
          />
          <div class="flex justify-between text-sm mt-3">
            <span class="text-gen-gray-400">Temperature</span>
            <span :class="systemStore.slaveHealth.temperature_celsius > 70 ? 'text-gen-amber' : ''">
              {{ systemStore.slaveHealth.temperature_celsius || '--' }}°C
            </span>
          </div>
        </template>
        <div v-else-if="!systemStore.slaveConnected" class="text-gen-gray-500">
          GenSlave offline
        </div>
        <div v-else class="text-gen-gray-500">Loading...</div>
      </StatusCard>
    </div>

    <!-- Confirm Dialogs -->
    <ConfirmDialog
      :show="showStartDialog"
      title="Start Generator"
      :message="`Start the generator for ${startDuration} minutes?`"
      confirm-text="Start"
      @confirm="handleStart"
      @cancel="showStartDialog = false"
    />

    <ConfirmDialog
      :show="showStopDialog"
      title="Stop Generator"
      message="Are you sure you want to stop the generator?"
      confirm-text="Stop"
      :danger="true"
      @confirm="handleStop"
      @cancel="showStopDialog = false"
    />
  </div>
</template>
```

### src/views/History.vue

```vue
<script setup>
import { ref, onMounted } from 'vue';
import { useGeneratorStore } from '@/stores/generator';
import StatusCard from '@/components/StatusCard.vue';

const generatorStore = useGeneratorStore();
const limit = ref(25);

onMounted(() => {
  generatorStore.fetchHistory(limit.value);
});

function formatDate(timestamp) {
  if (!timestamp) return '--';
  return new Date(timestamp * 1000).toLocaleString();
}

function formatDuration(seconds) {
  if (!seconds) return '--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function loadMore() {
  limit.value += 25;
  generatorStore.fetchHistory(limit.value);
}
</script>

<template>
  <div class="space-y-4">
    <StatusCard title="Generator Run History">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gen-gray-400 border-b border-gen-gray-700">
              <th class="py-2 px-3">Start Time</th>
              <th class="py-2 px-3">Stop Time</th>
              <th class="py-2 px-3">Duration</th>
              <th class="py-2 px-3">Trigger</th>
              <th class="py-2 px-3">Stop Reason</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in generatorStore.history"
              :key="run.id"
              class="border-b border-gen-gray-700"
            >
              <td class="py-3 px-3">{{ formatDate(run.start_time) }}</td>
              <td class="py-3 px-3">{{ formatDate(run.stop_time) }}</td>
              <td class="py-3 px-3 font-mono">{{ formatDuration(run.duration_seconds) }}</td>
              <td class="py-3 px-3">
                <span
                  class="px-2 py-1 rounded text-xs"
                  :class="{
                    'bg-blue-500/20 text-blue-400': run.trigger_type === 'victron',
                    'bg-purple-500/20 text-purple-400': run.trigger_type === 'manual',
                    'bg-gen-amber/20 text-gen-amber': run.trigger_type === 'scheduled'
                  }"
                >
                  {{ run.trigger_type }}
                </span>
              </td>
              <td class="py-3 px-3 text-gen-gray-400">
                {{ run.stop_reason || (run.stop_time ? '--' : 'Running') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-4 text-center">
        <button @click="loadMore" class="btn btn-secondary">
          Load More
        </button>
      </div>
    </StatusCard>
  </div>
</template>
```

### src/views/Schedule.vue

```vue
<script setup>
import { ref, onMounted } from 'vue';
import { scheduleApi } from '@/api/schedule';
import { useNotificationStore } from '@/stores/notifications';
import StatusCard from '@/components/StatusCard.vue';
import ScheduleTable from '@/components/ScheduleTable.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';

const notifications = useNotificationStore();

const schedules = ref([]);
const showAddModal = ref(false);
const showDeleteDialog = ref(false);
const selectedSchedule = ref(null);
const loading = ref(false);

// Form state
const form = ref({
  name: '',
  scheduledDate: '',
  scheduledTime: '',
  durationMinutes: 30,
  recurring: false,
  recurrencePattern: 'daily'
});

onMounted(fetchSchedules);

async function fetchSchedules() {
  try {
    const response = await scheduleApi.list();
    schedules.value = response.data;
  } catch (e) {
    notifications.error('Failed to load schedules');
  }
}

async function createSchedule() {
  loading.value = true;
  try {
    // Convert date/time to timestamp
    const dateTime = new Date(`${form.value.scheduledDate}T${form.value.scheduledTime}`);
    const timestamp = Math.floor(dateTime.getTime() / 1000);

    await scheduleApi.create({
      name: form.value.name || null,
      scheduled_start: timestamp,
      duration_minutes: form.value.durationMinutes,
      recurring: form.value.recurring,
      recurrence_pattern: form.value.recurring ? form.value.recurrencePattern : null
    });

    notifications.success('Schedule created');
    showAddModal.value = false;
    resetForm();
    await fetchSchedules();
  } catch (e) {
    notifications.error('Failed to create schedule');
  } finally {
    loading.value = false;
  }
}

async function deleteSchedule() {
  if (!selectedSchedule.value) return;

  try {
    await scheduleApi.delete(selectedSchedule.value.id);
    notifications.success('Schedule deleted');
    showDeleteDialog.value = false;
    selectedSchedule.value = null;
    await fetchSchedules();
  } catch (e) {
    notifications.error('Failed to delete schedule');
  }
}

function handleEdit(schedule) {
  // For now, just show info. Full edit modal can be added later.
  notifications.info(`Editing schedule #${schedule.id} - coming soon`);
}

function handleDelete(schedule) {
  selectedSchedule.value = schedule;
  showDeleteDialog.value = true;
}

function resetForm() {
  form.value = {
    name: '',
    scheduledDate: '',
    scheduledTime: '',
    durationMinutes: 30,
    recurring: false,
    recurrencePattern: 'daily'
  };
}
</script>

<template>
  <div class="space-y-4">
    <StatusCard title="Scheduled Runs">
      <div class="flex justify-end mb-4">
        <button @click="showAddModal = true" class="btn btn-primary">
          + Add Schedule
        </button>
      </div>

      <ScheduleTable
        :schedules="schedules"
        @edit="handleEdit"
        @delete="handleDelete"
      />
    </StatusCard>

    <!-- Add Schedule Modal -->
    <Teleport to="body">
      <div v-if="showAddModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60" @click="showAddModal = false"></div>

        <div class="relative bg-gen-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
          <h3 class="text-lg font-semibold mb-4">New Scheduled Run</h3>

          <form @submit.prevent="createSchedule" class="space-y-4">
            <div>
              <label class="block text-sm text-gen-gray-400 mb-1">Name (optional)</label>
              <input v-model="form.name" type="text" class="input w-full" placeholder="Morning run" />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm text-gen-gray-400 mb-1">Date</label>
                <input v-model="form.scheduledDate" type="date" class="input w-full" required />
              </div>
              <div>
                <label class="block text-sm text-gen-gray-400 mb-1">Time</label>
                <input v-model="form.scheduledTime" type="time" class="input w-full" required />
              </div>
            </div>

            <div>
              <label class="block text-sm text-gen-gray-400 mb-1">Duration (minutes)</label>
              <input
                v-model.number="form.durationMinutes"
                type="number"
                min="1"
                max="480"
                class="input w-full"
                required
              />
            </div>

            <div class="flex items-center gap-3">
              <input
                v-model="form.recurring"
                type="checkbox"
                id="recurring"
                class="w-4 h-4"
              />
              <label for="recurring" class="text-sm">Recurring</label>
            </div>

            <div v-if="form.recurring">
              <label class="block text-sm text-gen-gray-400 mb-1">Repeat</label>
              <select v-model="form.recurrencePattern" class="input w-full">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>

            <div class="flex justify-end gap-3 mt-6">
              <button type="button" @click="showAddModal = false" class="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" class="btn btn-primary" :disabled="loading">
                {{ loading ? 'Creating...' : 'Create Schedule' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :show="showDeleteDialog"
      title="Delete Schedule"
      :message="`Delete '${selectedSchedule?.name || 'this schedule'}'?`"
      confirm-text="Delete"
      :danger="true"
      @confirm="deleteSchedule"
      @cancel="showDeleteDialog = false"
    />
  </div>
</template>
```

### src/views/Settings.vue

```vue
<script setup>
import { ref, onMounted } from 'vue';
import { configApi } from '@/api/config';
import { useSystemStore } from '@/stores/system';
import { useNotificationStore } from '@/stores/notifications';
import StatusCard from '@/components/StatusCard.vue';
import Toggle from '@/components/Toggle.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';

const systemStore = useSystemStore();
const notifications = useNotificationStore();

const config = ref(null);
const loading = ref(false);
const showRebootDialog = ref(false);

onMounted(fetchConfig);

async function fetchConfig() {
  try {
    const response = await configApi.get();
    config.value = response.data;
  } catch (e) {
    notifications.error('Failed to load configuration');
  }
}

async function saveConfig() {
  loading.value = true;
  try {
    await configApi.update(config.value);
    notifications.success('Configuration saved');
  } catch (e) {
    notifications.error('Failed to save configuration');
  } finally {
    loading.value = false;
  }
}

async function createBackup() {
  try {
    const response = await configApi.createBackup();
    notifications.success(`Backup created: ${response.data.filename}`);
  } catch (e) {
    notifications.error('Failed to create backup');
  }
}

async function downloadBackup() {
  try {
    const response = await configApi.downloadBackup();
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'genmaster-backup.sql.gz');
    document.body.appendChild(link);
    link.click();
    link.remove();
  } catch (e) {
    notifications.error('Failed to download backup');
  }
}

async function testWebhook() {
  try {
    const result = await systemStore.testWebhook();
    if (result.success) {
      notifications.success(`Webhook test successful (${result.response_time_ms}ms)`);
    } else {
      notifications.error(`Webhook test failed: ${result.error}`);
    }
  } catch (e) {
    notifications.error('Webhook test failed');
  }
}

async function rebootSystem() {
  try {
    await fetch('/api/system/reboot', { method: 'POST' });
    notifications.warning('System rebooting...');
    showRebootDialog.value = false;
  } catch (e) {
    notifications.error('Failed to initiate reboot');
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- Heartbeat Settings -->
    <StatusCard title="Heartbeat Settings">
      <div v-if="config" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm text-gen-gray-400 mb-1">Interval (seconds)</label>
            <input
              v-model.number="config.heartbeat_interval_seconds"
              type="number"
              min="10"
              max="300"
              class="input w-full"
            />
          </div>
          <div>
            <label class="block text-sm text-gen-gray-400 mb-1">Failure Threshold</label>
            <input
              v-model.number="config.heartbeat_failure_threshold"
              type="number"
              min="1"
              max="10"
              class="input w-full"
            />
          </div>
        </div>
      </div>
    </StatusCard>

    <!-- Webhook Settings -->
    <StatusCard title="Webhook Settings">
      <div v-if="config" class="space-y-4">
        <div class="flex items-center justify-between">
          <span>Webhooks Enabled</span>
          <Toggle v-model="config.webhook_enabled" />
        </div>

        <div>
          <label class="block text-sm text-gen-gray-400 mb-1">Webhook URL</label>
          <input
            v-model="config.webhook_base_url"
            type="url"
            class="input w-full"
            placeholder="https://n8n.example.com/webhook/..."
          />
        </div>

        <button @click="testWebhook" class="btn btn-secondary">
          Test Webhook
        </button>
      </div>
    </StatusCard>

    <!-- Health Thresholds -->
    <StatusCard title="Health Thresholds">
      <div v-if="config" class="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm text-gen-gray-400 mb-1">Temp Warning (°C)</label>
          <input
            v-model.number="config.temp_warning_celsius"
            type="number"
            class="input w-full"
          />
        </div>
        <div>
          <label class="block text-sm text-gen-gray-400 mb-1">Temp Critical (°C)</label>
          <input
            v-model.number="config.temp_critical_celsius"
            type="number"
            class="input w-full"
          />
        </div>
        <div>
          <label class="block text-sm text-gen-gray-400 mb-1">Disk Warning (%)</label>
          <input
            v-model.number="config.disk_warning_percent"
            type="number"
            class="input w-full"
          />
        </div>
        <div>
          <label class="block text-sm text-gen-gray-400 mb-1">Disk Critical (%)</label>
          <input
            v-model.number="config.disk_critical_percent"
            type="number"
            class="input w-full"
          />
        </div>
        <div>
          <label class="block text-sm text-gen-gray-400 mb-1">RAM Warning (%)</label>
          <input
            v-model.number="config.ram_warning_percent"
            type="number"
            class="input w-full"
          />
        </div>
        <div>
          <label class="block text-sm text-gen-gray-400 mb-1">Log Retention (days)</label>
          <input
            v-model.number="config.event_log_retention_days"
            type="number"
            class="input w-full"
          />
        </div>
      </div>
    </StatusCard>

    <!-- Save Button -->
    <div class="flex justify-end">
      <button @click="saveConfig" class="btn btn-primary" :disabled="loading">
        {{ loading ? 'Saving...' : 'Save Configuration' }}
      </button>
    </div>

    <!-- Backup & System -->
    <StatusCard title="Backup & System">
      <div class="space-y-4">
        <div class="flex gap-2">
          <button @click="createBackup" class="btn btn-secondary">
            Create Backup
          </button>
          <button @click="downloadBackup" class="btn btn-secondary">
            Download Backup
          </button>
        </div>

        <hr class="border-gen-gray-700" />

        <div>
          <button @click="showRebootDialog = true" class="btn btn-danger">
            Reboot System
          </button>
          <p class="text-xs text-gen-gray-500 mt-1">
            Reboots GenMaster. Generator state is preserved.
          </p>
        </div>
      </div>
    </StatusCard>

    <!-- Reboot Confirmation -->
    <ConfirmDialog
      :show="showRebootDialog"
      title="Reboot System"
      message="Are you sure you want to reboot GenMaster? The system will be unavailable for approximately 1-2 minutes."
      confirm-text="Reboot"
      :danger="true"
      @confirm="rebootSystem"
      @cancel="showRebootDialog = false"
    />
  </div>
</template>
```

---

## Agent Implementation Checklist

- [ ] Initialize Vue project with Vite
- [ ] Configure Tailwind CSS
- [ ] Create `main.css` with custom styles
- [ ] Set up Vue Router
- [ ] Create all API client modules in `src/api/`
- [ ] Create Pinia stores in `src/stores/`
- [ ] Create all components in `src/components/`
- [ ] Create all views in `src/views/`
- [ ] Create `App.vue` with navigation and layout
- [ ] Test polling and real-time updates
- [ ] Test all API integrations
- [ ] Verify responsive design on mobile
- [ ] Test dark theme consistency
- [ ] Build production bundle

---

## Related Documents

- `01-project-structure.md` - Conventions and patterns
- `03-genmaster-backend.md` - API this frontend consumes
- `06-docker-infrastructure.md` - Nginx static file serving
