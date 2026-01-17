// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/stores/containers.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 15th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { useNotificationStore } from './notifications'

export const useContainersStore = defineStore('containers', () => {
  // State
  const containers = ref([])
  const stats = ref([])
  const loading = ref(false)
  const actionLoading = ref(false)
  const error = ref(null)
  const lastUpdated = ref(null)

  // Getters - with defensive array checks
  const containerList = computed(() =>
    Array.isArray(containers.value) ? containers.value : []
  )

  const runningCount = computed(() =>
    containerList.value.filter(c => c.status === 'running').length
  )

  const stoppedCount = computed(() =>
    containerList.value.filter(c => c.status !== 'running').length
  )

  const unhealthyCount = computed(() =>
    containerList.value.filter(c => c.health === 'unhealthy').length
  )

  const totalCount = computed(() => containerList.value.length)

  // Actions
  async function fetchContainers(includeAll = true) {
    loading.value = true
    error.value = null

    try {
      const response = await api.get('/containers/', { params: { all: includeAll } })
      containers.value = Array.isArray(response.data) ? response.data : []
      lastUpdated.value = new Date()
    } catch (err) {
      if (err.response?.status === 503) {
        error.value = 'Docker is not available'
      } else {
        error.value = err.response?.data?.detail || 'Failed to fetch containers'
      }
      containers.value = []
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const response = await api.get('/containers/stats')
      stats.value = Array.isArray(response.data) ? response.data : []
    } catch {
      stats.value = []
    }
  }

  async function getContainer(name) {
    try {
      const response = await api.get(`/containers/${name}`)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to get container'
      return null
    }
  }

  async function startContainer(name) {
    const notifications = useNotificationStore()
    actionLoading.value = true

    try {
      await api.post(`/containers/${name}/start`)
      notifications.success(`Container ${name} started`)
      await fetchContainers()
      return true
    } catch (err) {
      notifications.error(`Failed to start ${name}`)
      return false
    } finally {
      actionLoading.value = false
    }
  }

  async function stopContainer(name) {
    const notifications = useNotificationStore()
    actionLoading.value = true

    try {
      await api.post(`/containers/${name}/stop`)
      notifications.success(`Container ${name} stopped`)
      await fetchContainers()
      return true
    } catch (err) {
      notifications.error(`Failed to stop ${name}`)
      return false
    } finally {
      actionLoading.value = false
    }
  }

  async function restartContainer(name) {
    const notifications = useNotificationStore()
    actionLoading.value = true

    try {
      await api.post(`/containers/${name}/restart`)
      notifications.success(`Container ${name} restarted`)
      await fetchContainers()
      return true
    } catch (err) {
      notifications.error(`Failed to restart ${name}`)
      return false
    } finally {
      actionLoading.value = false
    }
  }

  async function getContainerLogs(name, tail = 100) {
    try {
      const response = await api.get(`/containers/${name}/logs`, { params: { tail } })
      return response.data.logs
    } catch {
      return null
    }
  }

  function getContainerStats(name) {
    return stats.value.find(s => s.name === name) || null
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    containers,
    stats,
    loading,
    actionLoading,
    error,
    lastUpdated,

    // Getters
    containerList,
    runningCount,
    stoppedCount,
    unhealthyCount,
    totalCount,

    // Actions
    fetchContainers,
    fetchStats,
    getContainer,
    startContainer,
    stopContainer,
    restartContainer,
    getContainerLogs,
    getContainerStats,
    clearError,
  }
})
