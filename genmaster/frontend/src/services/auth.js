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
  login(credentials) {
    return api.post('/auth/login', credentials)
  },

  /**
   * Logout current user
   * @returns {Promise<Object>}
   */
  logout() {
    return api.post('/auth/logout')
  },

  /**
   * Get current user information
   * @returns {Promise<Object>} - User object
   */
  getCurrentUser() {
    return api.get('/auth/me')
  },

  /**
   * Change password
   * @param {string} currentPassword
   * @param {string} newPassword
   * @returns {Promise<Object>}
   */
  changePassword(currentPassword, newPassword) {
    return api.put('/auth/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },
}
