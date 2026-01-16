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
import containersService from '@/services/containers'
import { useNotificationStore } from './notifications'

export const useContainersStore = defineStore('containers', () => {
  // State
  const containers = ref([])
  const stats = ref([])
  const loading = ref(false)
  const actionLoading = ref(false)
  const error = ref(null)

  // Getters
  const runningCount = computed(() =>
    containers.value.filter(c => c.status === 'running').length
  )

  const stoppedCount = computed(() =>
    containers.value.filter(c => c.status !== 'running').length
  )

  const totalCount = computed(() => containers.value.length)

  // Actions
  async function fetchContainers(includeAll = false) {
    loading.value = true
    error.value = null

    try {
      containers.value = await containersService.list(includeAll)
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
      stats.value = await containersService.getStats()
    } catch {
      stats.value = []
    }
  }

  async function getContainer(name) {
    try {
      return await containersService.get(name)
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to get container'
      return null
    }
  }

  async function startContainer(name) {
    const notifications = useNotificationStore()
    actionLoading.value = true

    try {
      await containersService.start(name)
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
      await containersService.stop(name)
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
      await containersService.restart(name)
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
      const result = await containersService.getLogs(name, tail)
      return result.logs
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

    // Getters
    runningCount,
    stoppedCount,
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
