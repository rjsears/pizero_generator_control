// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/stores/system.js
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
import systemService from '@/services/system'
import { genslaveApi } from '@/services/api'
import { useNotificationStore } from './notifications'

export const useSystemStore = defineStore('system', () => {
  // State
  const health = ref(null)
  const status = ref(null)
  const slaveHealth = ref(null)
  const slaveDetails = ref(null)
  const victronStatus = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Cached slave status state
  const slaveOnline = ref(null)
  const slaveStale = ref(false)
  const slaveCacheAge = ref(null)
  const slaveLastError = ref(null)

  // Getters
  // Note: Backend returns ram_percent, disk_percent, temperature_celsius
  const cpuPercent = computed(() => health.value?.cpu_percent || 0)
  const memoryPercent = computed(() => health.value?.ram_percent || 0)
  const diskPercent = computed(() => health.value?.disk_percent || 0)
  const temperature = computed(() => health.value?.temperature_celsius || null)
  const uptime = computed(() => health.value?.uptime_seconds || 0)

  // Note: Backend returns connection_status ("connected", "disconnected", "unknown")
  // Also use cached slave online status if available
  const isSlaveOnline = computed(() => {
    // Prefer cached status (from background polling service)
    if (slaveOnline.value !== null) {
      return slaveOnline.value
    }
    // Fallback to heartbeat-based connection status
    return slaveHealth.value?.connection_status === 'connected'
  })
  const slaveLastSeen = computed(() => slaveHealth.value?.last_heartbeat_received || null)
  const isSlaveStale = computed(() => slaveStale.value)
  const slaveError = computed(() => slaveLastError.value)

  const victronInputActive = computed(() => victronStatus.value?.signal_state || false)
  const victronLastChange = computed(() => victronStatus.value?.last_change || null)

  const overallHealth = computed(() => {
    if (!health.value) return 'unknown'
    if (cpuPercent.value > 90 || memoryPercent.value > 90 || diskPercent.value > 95) {
      return 'critical'
    }
    if (cpuPercent.value > 70 || memoryPercent.value > 70 || diskPercent.value > 80) {
      return 'warning'
    }
    return 'healthy'
  })

  // Actions
  async function fetchHealth() {
    loading.value = true
    error.value = null

    try {
      const response = await systemService.getHealth()
      health.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch system health'
    } finally {
      loading.value = false
    }
  }

  async function fetchStatus() {
    try {
      const response = await systemService.getStatus()
      status.value = response.data
      // Extract nested data
      if (status.value?.system) {
        health.value = status.value.system
      }
      if (status.value?.slave) {
        slaveHealth.value = status.value.slave
      }
      if (status.value?.victron) {
        victronStatus.value = status.value.victron
      }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch status'
    }
  }

  async function fetchSlaveHealth() {
    try {
      const response = await systemService.getSlaveHealth()
      slaveHealth.value = response.data
    } catch {
      slaveHealth.value = { online: false }
    }
  }

  async function fetchSlaveStatusCached() {
    // Fetch from the cached endpoint (instant response)
    try {
      const response = await genslaveApi.getStatusCached()
      const data = response.data
      slaveOnline.value = data.is_online
      slaveStale.value = data.is_stale
      slaveCacheAge.value = data.cache_age_seconds
      slaveLastError.value = data.last_error
      return data
    } catch {
      // If the cached endpoint fails, mark as unknown
      slaveOnline.value = null
      slaveStale.value = true
      return null
    }
  }

  async function fetchSlaveRelayCached() {
    // Fetch cached relay state (instant response)
    try {
      const response = await genslaveApi.getRelayCached()
      return response.data
    } catch {
      return null
    }
  }

  async function fetchSlaveDetails() {
    try {
      const response = await systemService.getSlaveDetails()
      slaveDetails.value = response.data
      return response.data
    } catch (err) {
      slaveDetails.value = null
      throw err
    }
  }

  async function fetchVictronStatus() {
    try {
      const response = await systemService.getVictronStatus()
      victronStatus.value = response.data
    } catch {
      victronStatus.value = null
    }
  }

  async function rebootSystem() {
    const notifications = useNotificationStore()

    try {
      await systemService.reboot()
      notifications.warning('System reboot initiated')
      return true
    } catch (err) {
      notifications.error('Reboot failed')
      return false
    }
  }

  async function testSlaveConnection() {
    const notifications = useNotificationStore()

    try {
      const response = await systemService.testSlave()
      const result = response.data
      if (result.success) {
        notifications.success(`Slave connection OK (${result.response_time_ms}ms)`)
      } else {
        notifications.error(`Slave connection failed: ${result.error}`)
      }
      return result
    } catch (err) {
      notifications.error('Failed to test slave connection')
      return { success: false }
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    health,
    status,
    slaveHealth,
    slaveDetails,
    victronStatus,
    loading,
    error,
    // Cached slave status state
    slaveOnline,
    slaveStale,
    slaveCacheAge,
    slaveLastError,

    // Getters
    cpuPercent,
    memoryPercent,
    diskPercent,
    temperature,
    uptime,
    isSlaveOnline,
    isSlaveStale,
    slaveError,
    slaveLastSeen,
    victronInputActive,
    victronLastChange,
    overallHealth,

    // Actions
    fetchHealth,
    fetchStatus,
    fetchSlaveHealth,
    fetchSlaveStatusCached,
    fetchSlaveRelayCached,
    fetchSlaveDetails,
    fetchVictronStatus,
    rebootSystem,
    testSlaveConnection,
    clearError,
  }
})
