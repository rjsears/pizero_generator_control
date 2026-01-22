// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/schedule.js
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
   * Get all scheduled runs
   * @returns {Promise<Array>}
   */
  async getAll() {
    const response = await api.get('/schedule')
    return response.data
  },

  /**
   * Get a specific schedule by ID
   * @param {number} id
   * @returns {Promise<Object>}
   */
  get(id) {
    return api.get(`/schedule/${id}`)
  },

  /**
   * Create a new scheduled run
   * @param {Object} schedule - Schedule data
   * @returns {Promise<Object>}
   */
  create(schedule) {
    return api.post('/schedule', schedule)
  },

  /**
   * Update an existing schedule
   * @param {number} id
   * @param {Object} schedule - Updated schedule data
   * @returns {Promise<Object>}
   */
  update(id, schedule) {
    return api.put(`/schedule/${id}`, schedule)
  },

  /**
   * Delete a schedule
   * @param {number} id
   * @returns {Promise<Object>}
   */
  delete(id) {
    return api.delete(`/schedule/${id}`)
  },

  /**
   * Enable a schedule
   * @param {number} id
   * @returns {Promise<Object>}
   */
  enable(id) {
    return api.post(`/schedule/${id}/enable`)
  },

  /**
   * Disable a schedule
   * @param {number} id
   * @returns {Promise<Object>}
   */
  disable(id) {
    return api.post(`/schedule/${id}/disable`)
  },

  /**
   * Get next scheduled run time
   * @returns {Promise<Object>}
   */
  getNextRun() {
    return api.get('/schedule/next')
  },
}
