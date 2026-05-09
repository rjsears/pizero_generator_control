/*
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
/genmaster/frontend/src/services/exercise.js

Part of the "RPi Generator Control" suite
Version 1.0.0 - January 19th, 2026

Richard J. Sears
richardjsears@protonmail.com
https://github.com/rjsears
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
*/

import api from './api'

export default {
  /**
   * Get exercise schedule configuration
   * @returns {Promise<Object>}
   */
  getSchedule() {
    return api.get('/exercise/')
  },

  /**
   * Update exercise schedule configuration (partial updates supported)
   * @param {Object} data - Fields to update
   * @returns {Promise<Object>}
   */
  updateSchedule(data) {
    return api.patch('/exercise/', data)
  },

  /**
   * Manually trigger an exercise run now
   * @returns {Promise<Object>}
   */
  runNow() {
    return api.post('/exercise/run-now')
  },
}
