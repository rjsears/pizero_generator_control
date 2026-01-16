// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/backup.js
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
   * List all backups
   * @returns {Promise<Object>} - { backups, total_count, total_size_bytes }
   */
  list() {
    return api.get('/backup')
  },

  /**
   * Create a new backup
   * @returns {Promise<Object>}
   */
  create() {
    return api.post('/backup')
  },

  /**
   * Delete a backup
   * @param {string} filename
   * @returns {Promise<Object>}
   */
  delete(filename) {
    return api.delete(`/backup/${filename}`)
  },

  /**
   * Get download URL for a backup
   * @param {string} filename
   * @returns {string}
   */
  getDownloadUrl(filename) {
    const token = localStorage.getItem('token')
    return `/api/backup/download/${filename}?token=${token}`
  },
}
