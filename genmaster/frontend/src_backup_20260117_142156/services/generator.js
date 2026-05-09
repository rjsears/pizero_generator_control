// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/generator.js
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
   * Get current generator state
   * @returns {Promise<Object>}
   */
  getState() {
    return api.get('/generator/state')
  },

  /**
   * Start the generator
   * @param {Object} options - { duration_minutes, reason }
   * @returns {Promise<Object>}
   */
  start(options = {}) {
    return api.post('/generator/start', options)
  },

  /**
   * Stop the generator
   * @param {Object} options - { reason }
   * @returns {Promise<Object>}
   */
  stop(options = {}) {
    return api.post('/generator/stop', options)
  },

  /**
   * Emergency stop the generator
   * @returns {Promise<Object>}
   */
  emergencyStop() {
    return api.post('/generator/emergency-stop')
  },

  /**
   * Get generator run history
   * @param {Object} params - { limit, offset, start_date, end_date }
   * @returns {Promise<Object>} - { runs, total }
   */
  getHistory(params = {}) {
    return api.get('/generator/history', { params })
  },

  /**
   * Get generator statistics
   * @returns {Promise<Object>}
   */
  getStats() {
    return api.get('/generator/stats')
  },

  /**
   * Get a specific run by ID
   * @param {number} runId
   * @returns {Promise<Object>}
   */
  getRun(runId) {
    return api.get(`/generator/history/${runId}`)
  },
}
