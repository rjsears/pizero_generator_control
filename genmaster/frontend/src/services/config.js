// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/config.js
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
   * Get system configuration
   * @returns {Promise<Object>}
   */
  get() {
    return api.get('/config')
  },

  /**
   * Update system configuration
   * @param {Object} config - Configuration object
   * @returns {Promise<Object>}
   */
  update(config) {
    return api.put('/config', config)
  },

  /**
   * Get override status
   * @returns {Promise<Object>}
   */
  getOverride() {
    return api.get('/override/status')
  },

  /**
   * Enable manual override
   * @param {Object} options - { duration_minutes, reason }
   * @returns {Promise<Object>}
   */
  enableOverride(options = {}) {
    return api.post('/override/enable', options)
  },

  /**
   * Disable manual override
   * @returns {Promise<Object>}
   */
  disableOverride() {
    return api.post('/override/disable')
  },

  /**
   * Get all settings
   * @returns {Promise<Array>}
   */
  getSettings() {
    return api.get('/settings')
  },

  /**
   * Get a specific setting
   * @param {string} key
   * @returns {Promise<Object>}
   */
  getSetting(key) {
    return api.get(`/settings/${key}`)
  },

  /**
   * Set a setting value
   * @param {string} key
   * @param {any} value
   * @param {string} description
   * @returns {Promise<Object>}
   */
  setSetting(key, value, description = null) {
    return api.put(`/settings/${key}`, { value, description })
  },

  /**
   * Delete a setting
   * @param {string} key
   * @returns {Promise<Object>}
   */
  deleteSetting(key) {
    return api.delete(`/settings/${key}`)
  },

  /**
   * Get webhook configuration
   * @returns {Promise<Object>}
   */
  getWebhookConfig() {
    return api.get('/settings/webhooks/config')
  },

  /**
   * Update webhook configuration
   * @param {Object} config - Webhook config
   * @returns {Promise<Object>}
   */
  updateWebhookConfig(config) {
    return api.put('/settings/webhooks/config', config)
  },

  /**
   * Test webhook
   * @returns {Promise<Object>}
   */
  testWebhook() {
    return api.post('/settings/webhooks/test')
  },
}
