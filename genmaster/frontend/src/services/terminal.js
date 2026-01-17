// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/terminal.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 16th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import api from './api'

export default {
  /**
   * Get available terminal targets (containers and host)
   * @returns {Promise<Object>}
   */
  getTargets() {
    return api.get('/terminal/targets')
  },

  /**
   * Create a WebSocket connection for terminal access
   * @param {string} target - Container name/ID or 'host'
   * @param {string} targetType - 'container' or 'host'
   * @returns {WebSocket}
   */
  connect(target, targetType = 'container') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/api/terminal/ws?target=${encodeURIComponent(target)}&target_type=${targetType}`
    return new WebSocket(url)
  },
}
