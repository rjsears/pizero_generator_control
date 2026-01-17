// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/notifications.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 17th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import api from './api'

export default {
  // ============================================================================
  // Channel Methods
  // ============================================================================

  async getChannels() {
    const response = await api.get('/notifications/channels')
    return response.data
  },

  async getChannel(id) {
    const response = await api.get(`/notifications/channels/${id}`)
    return response.data
  },

  async createChannel(data) {
    const response = await api.post('/notifications/channels', data)
    return response.data
  },

  async updateChannel(id, data) {
    const response = await api.put(`/notifications/channels/${id}`, data)
    return response.data
  },

  async deleteChannel(id) {
    const response = await api.delete(`/notifications/channels/${id}`)
    return response.data
  },

  async testChannel(id, data = {}) {
    const response = await api.post(`/notifications/channels/${id}/test`, data)
    return response.data
  },

  async toggleChannel(id) {
    const response = await api.post(`/notifications/channels/${id}/toggle`)
    return response.data
  },

  // ============================================================================
  // Group Methods
  // ============================================================================

  async getGroups() {
    const response = await api.get('/notifications/groups')
    return response.data
  },

  async getGroup(id) {
    const response = await api.get(`/notifications/groups/${id}`)
    return response.data
  },

  async createGroup(data) {
    const response = await api.post('/notifications/groups', data)
    return response.data
  },

  async updateGroup(id, data) {
    const response = await api.put(`/notifications/groups/${id}`, data)
    return response.data
  },

  async deleteGroup(id) {
    const response = await api.delete(`/notifications/groups/${id}`)
    return response.data
  },

  // ============================================================================
  // History Methods
  // ============================================================================

  async getHistory(limit = 50, channelId = null) {
    const params = { limit }
    if (channelId) {
      params.channel_id = channelId
    }
    const response = await api.get('/notifications/history', { params })
    return response.data
  },

  // ============================================================================
  // Send Methods
  // ============================================================================

  async sendNotification(data) {
    const response = await api.post('/notifications/send', data)
    return response.data
  },
}
