// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/stores/generator.js
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
import generatorService from '@/services/generator'
import { useNotificationStore } from './notifications'

export const useGeneratorStore = defineStore('generator', () => {
  // State
  const state = ref(null)
  const history = ref([])
  const stats = ref(null)
  const loading = ref(false)
  const actionLoading = ref(false)
  const error = ref(null)

  // Getters
  // Backend returns { running: bool, trigger: string, runtime_seconds: int }
  // Map to state names expected by UI
  const currentState = computed(() => {
    if (!state.value) return 'unknown'
    if (state.value.running) return 'running'
    return 'stopped'
  })
  const isRunning = computed(() => state.value?.running || false)
  const isStopped = computed(() => !state.value?.running)
  const canStart = computed(() => state.value && !state.value.running)
  const canStop = computed(() => state.value?.running || false)
  const runTimeMinutes = computed(() => {
    if (!state.value?.runtime_seconds) return 0
    return Math.floor(state.value.runtime_seconds / 60)
  })
  const lastRun = computed(() => state.value?.last_run_end || null)

  // State color mapping
  const stateColor = computed(() => {
    const colors = {
      stopped: 'gray',
      starting: 'amber',
      warmup: 'amber',
      running: 'green',
      stopping: 'amber',
      cooldown: 'blue',
      error: 'red',
    }
    return colors[currentState.value] || 'gray'
  })

  // Actions
  async function fetchState() {
    loading.value = true
    error.value = null

    try {
      const response = await generatorService.getState()
      state.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch generator state'
    } finally {
      loading.value = false
    }
  }

  async function fetchHistory(params = {}) {
    loading.value = true
    error.value = null

    try {
      const response = await generatorService.getHistory(params)
      history.value = response.data?.runs || []
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch history'
      return { runs: [], total: 0 }
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const response = await generatorService.getStats()
      stats.value = response.data
    } catch {
      // Stats are non-critical, silently fail
    }
  }

  async function start(durationMinutes = null, reason = 'manual') {
    const notifications = useNotificationStore()
    actionLoading.value = true
    error.value = null

    try {
      await generatorService.start({ duration_minutes: durationMinutes, reason })
      notifications.success('Generator start command sent')
      await fetchState()
      return true
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to start generator'
      error.value = message
      notifications.error(message)
      return false
    } finally {
      actionLoading.value = false
    }
  }

  async function stop(reason = 'manual') {
    const notifications = useNotificationStore()
    actionLoading.value = true
    error.value = null

    try {
      await generatorService.stop({ reason })
      notifications.success('Generator stop command sent')
      await fetchState()
      return true
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to stop generator'
      error.value = message
      notifications.error(message)
      return false
    } finally {
      actionLoading.value = false
    }
  }

  async function emergencyStop() {
    const notifications = useNotificationStore()
    actionLoading.value = true

    try {
      await generatorService.emergencyStop()
      notifications.warning('Emergency stop activated')
      await fetchState()
      return true
    } catch (err) {
      notifications.error('Emergency stop failed')
      return false
    } finally {
      actionLoading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    state,
    history,
    stats,
    loading,
    actionLoading,
    error,

    // Getters
    currentState,
    isRunning,
    isStopped,
    canStart,
    canStop,
    runTimeMinutes,
    lastRun,
    stateColor,

    // Actions
    fetchState,
    fetchStatus: fetchState,  // Alias for compatibility
    fetchHistory,
    fetchStats,
    start,
    stop,
    emergencyStop,
    clearError,
  }
})
