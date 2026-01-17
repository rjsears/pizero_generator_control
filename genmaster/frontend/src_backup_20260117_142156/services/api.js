// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/api.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 15th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import axios from 'axios'
import router from '../router'

// Create axios instance with default config
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
    const token = localStorage.getItem('token')
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
      localStorage.removeItem('token')
      // Only redirect if not already on login page
      if (router.currentRoute.value.name !== 'login') {
        router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('Access forbidden:', error.response?.data?.detail)
    }

    // Handle network errors
    if (!error.response) {
      error.message = 'Network error - please check your connection'
    }

    return Promise.reject(error)
  }
)

export default api

// Auth API
export const authApi = {
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
  changePassword: (data) => api.put('/auth/password', data),
}

// System API
export const systemApi = {
  health: () => api.get('/system'),
  info: () => api.get('/system/info'),
  status: () => api.get('/status'),
  reboot: () => api.post('/system/reboot'),
  logs: (params) => api.get('/system/logs', { params }),
  // Network
  network: () => api.get('/system/network'),
  getNetwork: () => api.get('/system/network'),
  // Docker
  dockerInfo: () => api.get('/system/docker/info'),
  getDockerInfo: () => api.get('/system/docker/info'),
  // SSL
  ssl: () => api.get('/system/ssl'),
  getSsl: () => api.get('/system/ssl'),
  sslRenew: () => api.post('/system/ssl/renew'),
  // External services
  externalServices: () => api.get('/system/external-services'),
  getExternalServices: () => api.get('/system/external-services'),
  cloudflare: () => api.get('/system/cloudflare'),
  getCloudflare: () => api.get('/system/cloudflare'),
  tailscale: () => api.get('/system/tailscale'),
  getTailscale: () => api.get('/system/tailscale'),
  // Terminal
  terminalTargets: () => api.get('/system/terminal/targets'),
  getTerminalTargets: () => api.get('/system/terminal/targets'),
  // GenSlave
  slaveHealth: () => api.get('/health/slave'),
  slaveDetails: () => api.get('/health/slave/details'),
  testSlave: () => api.post('/health/test-slave'),
  // Victron
  victron: () => api.get('/system/victron'),
  // Timezone
  timezone: () => api.get('/system/timezone'),
  // Health checks (for n8n_nginx compatibility)
  getHealth: () => api.get('/system'),
  getHealthFull: () => api.get('/system/health/full'),
  getInfo: () => api.get('/system/info'),
}

// Containers API
export const containersApi = {
  list: (all = true) => api.get('/containers/', { params: { all } }),
  get: (name) => api.get(`/containers/${name}`),
  stats: () => api.get('/containers/stats'),
  health: () => api.get('/containers/health'),
  start: (name) => api.post(`/containers/${name}/start`),
  stop: (name) => api.post(`/containers/${name}/stop`),
  restart: (name) => api.post(`/containers/${name}/restart`),
  logs: (name, params) => api.get(`/containers/${name}/logs`, { params }),
}

// Generator API
export const generatorApi = {
  status: () => api.get('/generator'),
  start: () => api.post('/generator/start'),
  stop: () => api.post('/generator/stop'),
  override: (enabled) => api.post(`/generator/override/${enabled ? 'enable' : 'disable'}`),
  history: (params) => api.get('/generator/history', { params }),
}

// Schedule API
export const scheduleApi = {
  list: () => api.get('/schedules'),
  create: (data) => api.post('/schedules', data),
  update: (id, data) => api.put(`/schedules/${id}`, data),
  delete: (id) => api.delete(`/schedules/${id}`),
  toggle: (id, enabled) => api.post(`/schedules/${id}/${enabled ? 'enable' : 'disable'}`),
}

// Settings API
export const settingsApi = {
  getAll: () => api.get('/settings/'),
  get: (key) => api.get(`/settings/${key}`),
  update: (key, data) => api.put(`/settings/${key}`, data),
  // Config
  getConfig: () => api.get('/config'),
  updateConfig: (data) => api.put('/config', data),
  // Webhook config
  getWebhookConfig: () => api.get('/config/webhooks'),
  updateWebhookConfig: (data) => api.put('/config/webhooks', data),
  testWebhook: () => api.post('/config/webhooks/test'),
  // Environment variables
  getEnvVariable: (key) => api.get(`/settings/env/${key}`),
  updateEnvVariable: (key, value) => api.put(`/settings/env/${key}`, { key, value }),
  // Container restart
  restartContainer: (containerName) => api.post(`/containers/${containerName}/restart`),
}

// Attach APIs to main instance for compatibility
api.auth = authApi
api.system = systemApi
api.containers = containersApi
api.generator = generatorApi
api.schedule = scheduleApi
api.settings = settingsApi
