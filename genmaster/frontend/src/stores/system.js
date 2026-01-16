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
import { useNotificationStore } from './notifications'

export const useSystemStore = defineStore('system', () => {
  // State
  const health = ref(null)
  const status = ref(null)
  const slaveHealth = ref(null)
  const victronStatus = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const cpuPercent = computed(() => health.value?.cpu_percent || 0)
  const memoryPercent = computed(() => health.value?.memory_percent || 0)
  const diskPercent = computed(() => health.value?.disk_percent || 0)
  const temperature = computed(() => health.value?.temperature || null)
  const uptime = computed(() => health.value?.uptime_seconds || 0)

  const isSlaveOnline = computed(() => slaveHealth.value?.online || false)
  const slaveLastSeen = computed(() => slaveHealth.value?.last_heartbeat || null)

  const victronInputActive = computed(() => victronStatus.value?.input_active || false)
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
      health.value = await systemService.getHealth()
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch system health'
    } finally {
      loading.value = false
    }
  }

  async function fetchStatus() {
    try {
      status.value = await systemService.getStatus()
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
      slaveHealth.value = await systemService.getSlaveHealth()
    } catch {
      slaveHealth.value = { online: false }
    }
  }

  async function fetchVictronStatus() {
    try {
      victronStatus.value = await systemService.getVictronStatus()
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
      const result = await systemService.testSlave()
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
    victronStatus,
    loading,
    error,

    // Getters
    cpuPercent,
    memoryPercent,
    diskPercent,
    temperature,
    uptime,
    isSlaveOnline,
    slaveLastSeen,
    victronInputActive,
    victronLastChange,
    overallHealth,

    // Actions
    fetchHealth,
    fetchStatus,
    fetchSlaveHealth,
    fetchVictronStatus,
    rebootSystem,
    testSlaveConnection,
    clearError,
  }
})
