// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/containers.js
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
   * List all containers
   * @param {boolean} all - Include stopped containers
   * @returns {Promise<Array>}
   */
  list(all = false) {
    return api.get('/containers', { params: { all } })
  },

  /**
   * Get container details
   * @param {string} name - Container name or ID
   * @returns {Promise<Object>}
   */
  get(name) {
    return api.get(`/containers/${name}`)
  },

  /**
   * Get container stats
   * @returns {Promise<Array>}
   */
  getStats() {
    return api.get('/containers/stats')
  },

  /**
   * Start a container
   * @param {string} name - Container name or ID
   * @returns {Promise<Object>}
   */
  start(name) {
    return api.post(`/containers/${name}/start`)
  },

  /**
   * Stop a container
   * @param {string} name - Container name or ID
   * @returns {Promise<Object>}
   */
  stop(name) {
    return api.post(`/containers/${name}/stop`)
  },

  /**
   * Restart a container
   * @param {string} name - Container name or ID
   * @returns {Promise<Object>}
   */
  restart(name) {
    return api.post(`/containers/${name}/restart`)
  },

  /**
   * Get container logs
   * @param {string} name - Container name or ID
   * @param {number} tail - Number of lines
   * @returns {Promise<Object>}
   */
  getLogs(name, tail = 100) {
    return api.get(`/containers/${name}/logs`, { params: { tail } })
  },
}
