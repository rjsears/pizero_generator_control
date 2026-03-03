/*
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
/genmaster/frontend/src/services/api.js

Part of the "RPi Generator Control" suite
Version 1.0.0 - January 17th, 2026

Richard J. Sears
richardjsears@protonmail.com
https://github.com/rjsears
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
*/

import axios from 'axios'
import router from '../router'

// Create axios instance - GenMaster always uses /api
// Short timeout (5s) to fail fast and keep UI responsive
const api = axios.create({
  baseURL: '/api',
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle 401 Unauthorized - redirect to login
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      // Only redirect if not already on login page
      if (router.currentRoute.value.name !== 'login') {
        router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('Access forbidden:', error.response?.data?.detail)
    }

    // Handle 429 Too Many Requests
    if (error.response?.status === 429) {
      console.error('Rate limited:', error.response?.data?.detail)
    }

    return Promise.reject(error)
  }
)

export default api

// Convenience methods for common endpoints
export const authApi = {
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  changePassword: (data) => api.put('/auth/password', data),
  getSessions: () => api.get('/auth/sessions'),
  getSubnets: () => api.get('/auth/subnets'),
  addSubnet: (data) => api.post('/auth/subnets', data),
  deleteSubnet: (id) => api.delete(`/auth/subnets/${id}`),
}

export const systemApi = {
  health: () => api.get('/system/health'),
  healthFull: () => api.get('/system/health/full'),
  metrics: () => api.get('/system/metrics'),
  info: () => api.get('/system/info'),
  dockerInfo: () => api.get('/system/docker/info'),
  audit: (params) => api.get('/system/audit', { params }),
  network: () => api.get('/system/network'),
  ssl: () => api.get('/system/ssl'),
  sslRenew: () => api.post('/system/ssl/renew'),
  cloudflare: () => api.get('/system/cloudflare'),
  tailscale: () => api.get('/system/tailscale'),
  hostWifi: () => api.get('/system/host/wifi'),
  scanWifiNetworks: () => api.get('/system/host/wifi/networks'),
  connectWifi: (data) => api.post('/system/host/wifi/connect', data),
  listSavedWifiNetworks: () => api.get('/system/host/wifi/saved'),
  addWifiNetwork: (data) => api.post('/system/host/wifi/add', data),
  deleteWifiNetwork: (data) => api.post('/system/host/wifi/delete', data),
  terminalTargets: () => api.get('/system/terminal/targets'),
  externalServices: () => api.get('/system/external-services'),
  debug: () => api.get('/system/debug'),
  // Host power control
  hostShutdown: () => api.post('/system/host/shutdown'),
  hostReboot: () => api.post('/system/host/reboot'),
  // WiFi watchdog management
  getWifiWatchdog: () => api.get('/system/wifi-watchdog'),
  installWifiWatchdog: () => api.post('/system/wifi-watchdog/install', null, { timeout: 30000 }),
  enableWifiWatchdog: () => api.post('/system/wifi-watchdog/enable', null, { timeout: 15000 }),
  disableWifiWatchdog: () => api.post('/system/wifi-watchdog/disable', null, { timeout: 15000 }),
  // Automation arm/disarm (GenMaster state machine control)
  getArmStatus: () => api.get('/system/arm'),
  arm: (source = 'web') => api.post('/system/arm', { source }),
  disarm: (source = 'web') => api.post('/system/disarm', { source }),
  // Host metrics from database cache (collected via psutil + Docker API)
  hostMetricsCached: (historyMinutes = 60) => api.get('/system/host-metrics/cached', { params: { history_minutes: historyMinutes } }),

  // Aliases for SystemView compatibility
  getHealth: () => api.get('/system/health'),
  getHealthFull: () => api.get('/system/health/full'),
  getInfo: () => api.get('/system/info'),
  getNetwork: () => api.get('/system/network'),
  getSsl: () => api.get('/system/ssl'),
  getCloudflare: () => api.get('/system/cloudflare'),
  getTailscale: () => api.get('/system/tailscale'),
  getTerminalTargets: () => api.get('/system/terminal/targets'),
  getExternalServices: () => api.get('/system/external-services'),
  getDebug: () => api.get('/system/debug'),
}

// GenMaster-specific: Generator API
export const generatorApi = {
  getState: () => api.get('/generator/state'),
  start: (options = {}) => api.post('/generator/start', options),
  stop: (options = {}) => api.post('/generator/stop', options),
  emergencyStop: () => api.post('/generator/emergency-stop'),
  getHistory: (params = {}) => api.get('/generator/history', { params }),
  getStats: () => api.get('/generator/stats'),
  getRun: (runId) => api.get(`/generator/history/${runId}`),
  // Fuel tracking
  getFuelUsage: () => api.get('/generator/fuel-usage'),
  resetFuelTracking: () => api.post('/generator/fuel-usage/reset'),
  // Runtime limits
  getRuntimeLimitsStatus: () => api.get('/generator/runtime-limits'),
  clearLockout: (acknowledge = true) => api.post('/generator/clear-lockout', { acknowledge }),
}

// GenMaster-specific: GenSlave API
export const genslaveApi = {
  // Basic status
  getStatus: () => api.get('/health/slave'),
  getDetails: () => api.get('/health/slave/details'),
  // Full system info (CPU, RAM, disk, temp, network, WiFi)
  getSystemInfo: () => api.get('/health/slave/system'),
  // Quick health check (relay_state, failsafe, armed, mock_mode)
  getHealthStatus: () => api.get('/health/slave/health'),
  // Failsafe status
  getFailsafeStatus: () => api.get('/health/slave/failsafe'),
  // Test connection
  testConnection: () => api.post('/health/test-slave'),
  // Relay arm/disarm control (proxied through GenMaster to GenSlave)
  // Longer timeout for arm/disarm since it goes through GenSlave
  arm: () => api.post('/health/relay/arm', null, { timeout: 15000 }),
  disarm: () => api.post('/health/relay/disarm', null, { timeout: 15000 }),
  getRelayState: () => api.get('/health/relay/state'),
  // Cached status endpoints (instant response from background polling)
  getStatusCached: () => api.get('/health/slave/cached'),
  getHealthCached: () => api.get('/health/slave/cached/health'),
  getRelayCached: () => api.get('/health/slave/cached/relay'),
  getFailsafeCached: () => api.get('/health/slave/cached/failsafe'),
  getSystemCached: () => api.get('/health/slave/cached/system'),
  refreshCache: () => api.post('/health/slave/cached/refresh'),
  // Notification management (proxied to GenSlave)
  getNotifications: () => api.get('/genslave/notifications'),
  setNotifications: (appriseUrls) => api.post('/genslave/notifications', { apprise_urls: appriseUrls }),
  getNotificationSettings: () => api.get('/genslave/notifications/settings'),
  setNotificationSettings: (data) => api.post('/genslave/notifications/settings', data),
  testNotifications: () => api.post('/genslave/notifications/test'),
  setNotificationsEnabled: (enabled) => api.post('/genslave/notifications/enable', { enabled }),
  clearNotificationCooldown: (eventType = null) => api.post('/genslave/notifications/clear-cooldown', { event_type: eventType }),
  // WiFi configuration (proxied to GenSlave)
  scanWifiNetworks: () => api.get('/genslave/wifi/networks'),
  connectWifi: (data) => api.post('/genslave/wifi/connect', data),
  listSavedWifiNetworks: () => api.get('/genslave/wifi/saved'),
  addWifiNetwork: (data) => api.post('/genslave/wifi/add', data),
  deleteWifiNetwork: (data) => api.post('/genslave/wifi/delete', data),
  // System power control (proxied to GenSlave)
  shutdown: () => api.post('/genslave/shutdown'),
  reboot: () => api.post('/genslave/reboot'),
  getRebootStatus: () => api.get('/genslave/reboot-status'),
}

// GenMaster-specific: Schedule API
export const scheduleApi = {
  getSchedules: () => api.get('/schedule/'),
  createSchedule: (data) => api.post('/schedule/', data),
  updateSchedule: (id, data) => api.put(`/schedule/${id}`, data),
  deleteSchedule: (id) => api.delete(`/schedule/${id}`),
  toggleSchedule: (id, enabled) => api.put(`/schedule/${id}/toggle`, { enabled }),
  getUpcoming: () => api.get('/schedule/upcoming'),
}

export const containersApi = {
  list: (all = true) => api.get('/containers/', { params: { all } }),
  get: (name) => api.get(`/containers/${name}`),
  // Stats endpoint queries Docker for each container - can be slow with many containers
  stats: () => api.get('/containers/stats', { timeout: 30000 }),
  health: () => api.get('/containers/health'),
  start: (name) => api.post(`/containers/${name}/start`, null, { timeout: 30000 }),
  stop: (name) => api.post(`/containers/${name}/stop`, null, { timeout: 30000 }),
  restart: (name) => api.post(`/containers/${name}/restart`, null, { timeout: 30000 }),
  recreate: (name, pull = false) => api.post(`/containers/${name}/recreate`, null, { params: { pull }, timeout: 60000 }),
  logs: (name, params) => api.get(`/containers/${name}/logs`, { params, timeout: 15000 }),
}

export const notificationsApi = {
  // Channels (Services)
  getServices: () => api.get('/notifications/services'),
  createService: (data) => api.post('/notifications/services', data),
  updateService: (id, data) => api.put(`/notifications/services/${id}`, data),
  deleteService: (id) => api.delete(`/notifications/services/${id}`),
  testService: (id, data) => api.post(`/notifications/services/${id}/test`, data),
  // Groups
  getGroups: () => api.get('/notifications/groups'),
  getGroup: (id) => api.get(`/notifications/groups/${id}`),
  createGroup: (data) => api.post('/notifications/groups', data),
  updateGroup: (id, data) => api.put(`/notifications/groups/${id}`, data),
  deleteGroup: (id) => api.delete(`/notifications/groups/${id}`),
  // Rules
  getRules: () => api.get('/notifications/rules'),
  createRule: (data) => api.post('/notifications/rules', data),
  updateRule: (id, data) => api.put(`/notifications/rules/${id}`, data),
  deleteRule: (id) => api.delete(`/notifications/rules/${id}`),
  getEventTypes: () => api.get('/notifications/event-types'),
  getHistory: (params) => api.get('/notifications/history', { params }),
  // Channels (Apprise)
  getChannels: () => api.get('/notifications/channels'),
  createChannel: (data) => api.post('/notifications/channels', data),
  updateChannel: (id, data) => api.put(`/notifications/channels/${id}`, data),
  deleteChannel: (id) => api.delete(`/notifications/channels/${id}`),
  testChannel: (id, data) => api.post(`/notifications/channels/${id}/test`, data),
  // Send
  send: (data) => api.post('/notifications/send', data),
}

export const emailApi = {
  getConfig: () => api.get('/email/config'),
  updateConfig: (data) => api.put('/email/config', data),
  test: (data) => api.post('/email/test', data),
  getTemplates: () => api.get('/email/templates'),
  updateTemplate: (key, data) => api.put(`/email/templates/${key}`, data),
  previewTemplate: (data) => api.post('/email/templates/preview', data),
}

// Config API (system configuration at /config endpoint)
export const configApi = {
  get: () => api.get('/config/'),
  update: (data) => api.put('/config/', data),
}

// Generator Info API
export const generatorInfoApi = {
  get: () => api.get('/generator-info/'),
  update: (data) => api.patch('/generator-info/', data),
}

// Exercise Schedule API
export const exerciseApi = {
  getSchedule: () => api.get('/exercise/'),
  updateSchedule: (data) => api.patch('/exercise/', data),
  runNow: () => api.post('/exercise/run-now'),
}

export const settingsApi = {
  list: (category) => api.get('/settings/', { params: { category } }),
  get: (key) => api.get(`/settings/${key}`),
  update: (key, data) => api.put(`/settings/${key}`, data),
  // Legacy aliases - use configApi instead
  getConfig: () => api.get('/config/'),
  updateConfig: (data) => api.put('/config/', data),
  // Environment variable management
  getEnvVariables: () => api.get('/settings/env'),
  getEnvVariable: (key) => api.get(`/settings/env/${key}`),
  updateEnvVariable: (key, value) => api.put(`/settings/env/${key}`, { key, value }),
  // Tailscale management
  resetTailscale: () => api.post('/settings/tailscale/reset'),
  getTailscaleStatus: () => api.get('/settings/tailscale/status'),
  // Debug mode
  getDebugMode: () => api.get('/settings/debug'),
  setDebugMode: (enabled) => api.put('/settings/debug', { enabled }),
  // Container restart (uses containers API)
  restartContainer: (containerName, reason) => api.post(`/containers/${containerName}/restart`),
  // Access Control
  getAccessControl: () => api.get('/settings/access-control'),
  updateAccessControl: (data) => api.put('/settings/access-control', data),
  addIpRange: (data) => api.post('/settings/access-control/ip', data),
  updateIpRange: (cidr, description) => api.put(`/settings/access-control/ip/${encodeURIComponent(cidr)}`, { description }),
  deleteIpRange: (cidr) => api.delete(`/settings/access-control/ip/${encodeURIComponent(cidr)}`),
  reloadNginx: () => api.post('/settings/access-control/reload-nginx'),
  getDefaultIpRanges: () => api.get('/settings/access-control/defaults'),
  // External Routes
  getExternalRoutes: () => api.get('/settings/external-routes'),
  addExternalRoute: (data) => api.post('/settings/external-routes', data),
  deleteExternalRoute: (path) => api.delete(`/settings/external-routes/${path.replace(/^\//, '')}`),
  // Aliases for view compatibility
  getAll: () => api.get('/settings/'),
}

// Attach APIs to the main instance for api.xxx.method() pattern compatibility
api.auth = authApi
api.system = {
  ...systemApi,
  // Aliases for SystemView compatibility
  getInfo: systemApi.info,
  getHealth: systemApi.health,
  getHealthFull: systemApi.healthFull,
  getNetwork: systemApi.network,
  getSsl: systemApi.ssl,
  getCloudflare: systemApi.cloudflare,
  getTailscale: systemApi.tailscale,
  getTerminalTargets: systemApi.terminalTargets,
  getExternalServices: systemApi.externalServices,
  getDebug: systemApi.debug,
}
api.generator = generatorApi
api.genslave = genslaveApi
api.schedule = scheduleApi
api.containers = containersApi
api.notifications = {
  ...notificationsApi,
  // Aliases for terminology compatibility
  getHistory: (params) => api.get('/notifications/history', { params }),
}
api.email = emailApi
api.config = configApi
api.settings = {
  ...settingsApi,
  getAll: () => api.get('/settings/'),
}
api.generatorInfo = generatorInfoApi
api.exercise = exerciseApi
