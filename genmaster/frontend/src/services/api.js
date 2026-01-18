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
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
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
  terminalTargets: () => api.get('/system/terminal/targets'),
  externalServices: () => api.get('/system/external-services'),
  debug: () => api.get('/system/debug'),
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
}

// GenMaster-specific: GenSlave API
export const genslaveApi = {
  getStatus: () => api.get('/health/slave'),
  getSlaves: () => api.get('/genslave/list'),
  getSlave: (id) => api.get(`/genslave/${id}`),
  sync: (id) => api.post(`/genslave/${id}/sync`),
  restart: (id) => api.post(`/genslave/${id}/restart`),
  // Relay arm/disarm control (proxied through GenMaster to GenSlave)
  arm: () => api.post('/health/relay/arm'),
  disarm: () => api.post('/health/relay/disarm'),
  getRelayState: () => api.get('/health/relay/state'),
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
  stats: () => api.get('/containers/stats'),
  health: () => api.get('/containers/health'),
  start: (name) => api.post(`/containers/${name}/start`),
  stop: (name) => api.post(`/containers/${name}/stop`),
  restart: (name) => api.post(`/containers/${name}/restart`),
  recreate: (name, pull = false) => api.post(`/containers/${name}/recreate`, null, { params: { pull } }),
  logs: (name, params) => api.get(`/containers/${name}/logs`, { params }),
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

export const settingsApi = {
  list: (category) => api.get('/settings/', { params: { category } }),
  get: (key) => api.get(`/settings/${key}`),
  update: (key, data) => api.put(`/settings/${key}`, data),
  getConfig: (type) => api.get(`/settings/config/${type}`),
  updateConfig: (type, data) => api.put(`/settings/config/${type}`, data),
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
api.settings = {
  ...settingsApi,
  getAll: () => api.get('/settings/'),
}
