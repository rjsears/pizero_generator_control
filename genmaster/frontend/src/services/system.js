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
}
