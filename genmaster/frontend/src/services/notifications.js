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

  // ============================================================================
  // System Notification Event Methods
  // ============================================================================

  async getSystemEvents(category = null, enabledOnly = false) {
    const params = {}
    if (category) params.category = category
    if (enabledOnly) params.enabled_only = enabledOnly
    const response = await api.get('/system-notifications/events', { params })
    return response.data
  },

  async getSystemEvent(id) {
    const response = await api.get(`/system-notifications/events/${id}`)
    return response.data
  },

  async updateSystemEvent(id, data) {
    const response = await api.put(`/system-notifications/events/${id}`, data)
    return response.data
  },

  async resetEventTemplate(id, resetTitle = true, resetMessage = true) {
    const response = await api.post(`/system-notifications/events/${id}/reset-template`, {
      reset_title: resetTitle,
      reset_message: resetMessage,
    })
    return response.data
  },

  async bulkUpdateEvents(eventIds, updates) {
    const response = await api.post('/system-notifications/events/bulk-update', {
      event_ids: eventIds,
      ...updates,
    })
    return response.data
  },

  // ============================================================================
  // Global Settings Methods
  // ============================================================================

  async getGlobalSettings() {
    const response = await api.get('/system-notifications/settings')
    return response.data
  },

  async updateGlobalSettings(data) {
    const response = await api.put('/system-notifications/settings', data)
    return response.data
  },

  // ============================================================================
  // Container Config Methods
  // ============================================================================

  async getContainerConfigs() {
    const response = await api.get('/system-notifications/containers')
    return response.data
  },

  async discoverContainers() {
    const response = await api.get('/system-notifications/containers/discover')
    return response.data
  },

  async createContainerConfig(data) {
    const response = await api.post('/system-notifications/containers', data)
    return response.data
  },

  async updateContainerConfig(id, data) {
    const response = await api.put(`/system-notifications/containers/${id}`, data)
    return response.data
  },

  async deleteContainerConfig(id) {
    const response = await api.delete(`/system-notifications/containers/${id}`)
    return response.data
  },

  // ============================================================================
  // System Notification History Methods
  // ============================================================================

  async getSystemHistory(page = 1, pageSize = 50, filters = {}) {
    const params = { page, page_size: pageSize, ...filters }
    const response = await api.get('/system-notifications/history', { params })
    return response.data
  },

  async getSystemHistoryStats() {
    const response = await api.get('/system-notifications/history/stats')
    return response.data
  },

  async cleanupHistory(days = 60) {
    const response = await api.delete('/system-notifications/history/cleanup', {
      params: { days },
    })
    return response.data
  },

  // ============================================================================
  // Test Methods
  // ============================================================================

  async triggerTestNotification(eventType, eventData = {}, skipRateLimiting = true) {
    const response = await api.post('/system-notifications/trigger', {
      event_type: eventType,
      event_data: eventData,
      skip_rate_limiting: skipRateLimiting,
    })
    return response.data
  },

  async testEventNotification(eventType) {
    const response = await api.post(`/system-notifications/test-event/${eventType}`)
    return response.data
  },
}
