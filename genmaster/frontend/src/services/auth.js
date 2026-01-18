// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/auth.js
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
   * Login with username and password
   * @param {Object} credentials - { username, password }
   * @returns {Promise<Object>} - { token, user }
   */
  async login(credentials) {
    const response = await api.post('/auth/login', credentials)
    return response.data
  },

  /**
   * Logout current user
   * @returns {Promise<Object>}
   */
  async logout() {
    const response = await api.post('/auth/logout')
    return response.data
  },

  /**
   * Get current user information
   * @returns {Promise<Object>} - User object
   */
  async getCurrentUser() {
    const response = await api.get('/auth/me')
    return response.data
  },

  /**
   * Change password
   * @param {string} currentPassword
   * @param {string} newPassword
   * @returns {Promise<Object>}
   */
  async changePassword(currentPassword, newPassword) {
    const response = await api.put('/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return response.data
  },
}
