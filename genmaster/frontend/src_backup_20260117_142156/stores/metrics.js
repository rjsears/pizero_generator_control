// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/stores/metrics.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 17th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import metricsApi from '@/services/metrics'

export const useMetricsStore = defineStore('metrics', () => {
  // State
  const history = ref(null)
  const networkMetrics = ref(null)
  const containerSummary = ref(null)
  const servicesStatus = ref(null)
  const dockerStorage = ref(null)
  const logsAnalysis = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const lastUpdated = ref(null)

  // Computed
  const cpuHistory = computed(() => history.value?.cpu_percent || [])
  const memoryHistory = computed(() => history.value?.memory_percent || [])
  const networkSentHistory = computed(() => history.value?.network_rate_sent || [])
  const networkRecvHistory = computed(() => history.value?.network_rate_recv || [])
  const timestamps = computed(() => history.value?.timestamps || [])

  const currentNetworkSent = computed(() => networkMetrics.value?.bytes_sent_rate || 0)
  const currentNetworkRecv = computed(() => networkMetrics.value?.bytes_recv_rate || 0)

  const containersRunning = computed(() => containerSummary.value?.running || 0)
  const containersStopped = computed(() => containerSummary.value?.stopped || 0)
  const containersUnhealthy = computed(() => containerSummary.value?.unhealthy || 0)
  const containersTotal = computed(() => containerSummary.value?.total || 0)

  const allServicesHealthy = computed(() => servicesStatus.value?.overall_status === 'healthy')

  // Actions
  async function fetchHistory(minutes = 60) {
    try {
      const response = await metricsApi.getHistory(minutes)
      history.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch metrics history'
    }
  }

  async function fetchNetworkMetrics() {
    try {
      const response = await metricsApi.getNetworkMetrics()
      networkMetrics.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch network metrics'
    }
  }

  async function fetchContainerSummary() {
    try {
      const response = await metricsApi.getContainerSummary()
      containerSummary.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch container summary'
    }
  }

  async function fetchServicesStatus() {
    try {
      const response = await metricsApi.getServicesStatus()
      servicesStatus.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch services status'
    }
  }

  async function fetchDockerStorage() {
    try {
      const response = await metricsApi.getDockerStorage()
      dockerStorage.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch Docker storage'
    }
  }

  async function fetchLogsAnalysis(lines = 100) {
    try {
      const response = await metricsApi.getLogsAnalysis(lines)
      logsAnalysis.value = response.data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch logs analysis'
    }
  }

  async function fetchDashboardMetrics() {
    loading.value = true
    error.value = null

    try {
      const response = await metricsApi.getDashboardMetrics()
      const data = response.data

      history.value = data.history
      networkMetrics.value = data.network
      containerSummary.value = data.containers
      servicesStatus.value = data.services
      lastUpdated.value = Date.now()
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch dashboard metrics'
    } finally {
      loading.value = false
    }
  }

  async function fetchAll() {
    loading.value = true
    error.value = null

    try {
      await Promise.all([
        fetchHistory(),
        fetchNetworkMetrics(),
        fetchContainerSummary(),
        fetchServicesStatus(),
      ])
      lastUpdated.value = Date.now()
    } catch {
      // Individual errors are handled in each function
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  // Helper functions
  function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 B'

    const k = 1024
    const dm = decimals < 0 ? 0 : decimals
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']

    const i = Math.floor(Math.log(bytes) / Math.log(k))

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
  }

  function formatBytesPerSecond(bytesPerSec) {
    return formatBytes(bytesPerSec) + '/s'
  }

  return {
    // State
    history,
    networkMetrics,
    containerSummary,
    servicesStatus,
    dockerStorage,
    logsAnalysis,
    loading,
    error,
    lastUpdated,

    // Computed
    cpuHistory,
    memoryHistory,
    networkSentHistory,
    networkRecvHistory,
    timestamps,
    currentNetworkSent,
    currentNetworkRecv,
    containersRunning,
    containersStopped,
    containersUnhealthy,
    containersTotal,
    allServicesHealthy,

    // Actions
    fetchHistory,
    fetchNetworkMetrics,
    fetchContainerSummary,
    fetchServicesStatus,
    fetchDockerStorage,
    fetchLogsAnalysis,
    fetchDashboardMetrics,
    fetchAll,
    clearError,

    // Helpers
    formatBytes,
    formatBytesPerSecond,
  }
})
