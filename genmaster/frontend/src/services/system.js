// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/system.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 15th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import api from './api'

export default {
  /**
   * Get system health metrics
   * @returns {Promise<Object>}
   */
  getHealth() {
    return api.get('/system')
  },

  /**
   * Get full system status including generator, slave, and victron
   * @returns {Promise<Object>}
   */
  getStatus() {
    return api.get('/status')
  },

  /**
   * Get slave health status (basic)
   * @returns {Promise<Object>}
   */
  getSlaveHealth() {
    return api.get('/health/slave')
  },

  /**
   * Get detailed slave system info (CPU, RAM, disk, network, WiFi, etc.)
   * @returns {Promise<Object>}
   */
  getSlaveDetails() {
    return api.get('/health/slave/details')
  },

  /**
   * Get Victron status
   * @returns {Promise<Object>}
   */
  getVictronStatus() {
    return api.get('/system/victron')
  },

  /**
   * Test slave connection
   * @returns {Promise<Object>}
   */
  testSlave() {
    return api.post('/health/test-slave')
  },

  /**
   * Reboot the system
   * @returns {Promise<Object>}
   */
  reboot() {
    return api.post('/system/reboot')
  },

  /**
   * Get system logs
   * @param {Object} params - { lines, service }
   * @returns {Promise<Object>}
   */
  getLogs(params = {}) {
    return api.get('/system/logs', { params })
  },

  /**
   * Get SSL certificate info
   * @returns {Promise<Object>}
   */
  getSslInfo() {
    return api.get('/system/ssl')
  },

  /**
   * Force renew SSL certificate
   * @returns {Promise<Object>}
   */
  forceRenewSsl() {
    return api.post('/system/ssl/renew')
  },

  /**
   * Get external services status (Cloudflare, Tailscale)
   * @returns {Promise<Object>}
   */
  getExternalServices() {
    return api.get('/system/external-services')
  },

  /**
   * Get Cloudflare Tunnel status
   * @returns {Promise<Object>}
   */
  getCloudflareStatus() {
    return api.get('/system/cloudflare')
  },

  /**
   * Get Tailscale VPN status
   * @returns {Promise<Object>}
   */
  getTailscaleStatus() {
    return api.get('/system/tailscale')
  },

  /**
   * Get Docker daemon info
   * @returns {Promise<Object>}
   */
  getDockerInfo() {
    return api.get('/system/docker/info')
  },

  /**
   * Get network information
   * @returns {Promise<Object>}
   */
  getNetworkInfo() {
    return api.get('/system/network')
  },

  /**
   * Get timezone information
   * @returns {Promise<Object>}
   */
  getTimezone() {
    return api.get('/system/timezone')
  },
}
