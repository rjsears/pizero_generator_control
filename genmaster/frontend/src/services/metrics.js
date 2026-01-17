// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/services/metrics.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 17th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import api from './api'

/**
 * Metrics API service for dashboard charts and system monitoring.
 */
export const metricsApi = {
  /**
   * Get metrics history for charts.
   * @param {number} minutes - Number of minutes of history (1-60)
   */
  getHistory(minutes = 60) {
    return api.get('/metrics/history', { params: { minutes } })
  },

  /**
   * Get current network I/O metrics.
   */
  getNetworkMetrics() {
    return api.get('/metrics/network')
  },

  /**
   * Get container summary (running, stopped, unhealthy counts).
   */
  getContainerSummary() {
    return api.get('/metrics/containers/summary')
  },

  /**
   * Get Docker storage usage.
   */
  getDockerStorage() {
    return api.get('/metrics/docker/storage')
  },

  /**
   * Get core services status.
   */
  getServicesStatus() {
    return api.get('/metrics/services')
  },

  /**
   * Get logs analysis for all containers.
   * @param {number} lines - Number of lines to analyze per container
   */
  getLogsAnalysis(lines = 100) {
    return api.get('/metrics/logs/analysis', { params: { lines } })
  },

  /**
   * Get all dashboard metrics in a single call.
   */
  getDashboardMetrics() {
    return api.get('/metrics/dashboard')
  },
}

export default metricsApi
