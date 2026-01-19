/*
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
/genmaster/frontend/src/services/generatorInfo.js

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
   * Get generator information
   * @returns {Promise<Object>}
   */
  get() {
    return api.get('/generator-info/')
  },

  /**
   * Update generator information (partial updates supported)
   * @param {Object} data - Fields to update
   * @returns {Promise<Object>}
   */
  update(data) {
    return api.patch('/generator-info/', data)
  },
}
