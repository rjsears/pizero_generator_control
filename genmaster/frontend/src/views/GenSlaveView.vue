<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/GenSlaveView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 16th, 2026

  Dedicated view for GenSlave health monitoring with detailed
  system metrics, network info, and real-time status.

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <MainLayout>
    <div class="space-y-6">
      <!-- Page header with refresh button -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">GenSlave</h1>
          <p class="text-gray-600 dark:text-gray-400 mt-1">
            Remote generator controller health and status
          </p>
        </div>
        <div class="flex items-center space-x-3">
          <!-- Connection status badge -->
          <StatusBadge
            :status="connectionStatus"
            :text="connectionStatusText"
          />
          <!-- Refresh button -->
          <Button
            variant="secondary"
            @click="refreshHealth"
            :loading="loading"
            :disabled="loading"
          >
            <svg class="w-5 h-5 mr-2" :class="{ 'animate-spin': loading }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </Button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading && !slaveDetails">
        <GenSlaveLoader />
      </div>

      <!-- Error State -->
      <Card v-else-if="error" class="border-red-200 dark:border-red-800">
        <div class="flex items-center space-x-4">
          <div class="w-12 h-12 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
            <svg class="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div class="flex-1">
            <h3 class="font-medium text-gray-900 dark:text-white">Connection Failed</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">{{ error }}</p>
          </div>
          <Button variant="primary" @click="refreshHealth">
            Retry
          </Button>
        </div>
      </Card>

      <!-- Main Content -->
      <template v-else-if="slaveDetails">
        <!-- Quick Stats Row -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <!-- Hostname -->
          <Card class="col-span-1">
            <div class="text-center">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">Hostname</p>
              <p class="text-lg font-bold text-gray-900 dark:text-white mt-1 truncate">
                {{ slaveDetails.hostname || 'Unknown' }}
              </p>
            </div>
          </Card>

          <!-- IP Address -->
          <Card class="col-span-1">
            <div class="text-center">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">IP Address</p>
              <p class="text-lg font-bold text-cyan-600 dark:text-cyan-400 mt-1 font-mono">
                {{ slaveDetails.ip_address || 'N/A' }}
              </p>
            </div>
          </Card>

          <!-- Uptime -->
          <Card class="col-span-1">
            <div class="text-center">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">Uptime</p>
              <p class="text-lg font-bold text-gray-900 dark:text-white mt-1">
                {{ formatUptime(slaveDetails.uptime_seconds) }}
              </p>
            </div>
          </Card>

          <!-- Temperature -->
          <Card class="col-span-1">
            <div class="text-center">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">Temperature</p>
              <p class="text-lg font-bold mt-1" :class="getTempClass(slaveDetails.temperature_celsius)">
                {{ slaveDetails.temperature_celsius ? `${slaveDetails.temperature_celsius.toFixed(1)}°C` : 'N/A' }}
              </p>
            </div>
          </Card>

          <!-- WiFi Signal -->
          <Card class="col-span-1">
            <div class="text-center">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">WiFi Signal</p>
              <div class="flex items-center justify-center mt-1">
                <WifiIcon :strength="wifiSignalPercent" class="w-6 h-6 mr-1" />
                <span class="text-lg font-bold" :class="getWifiClass(wifiSignalPercent)">
                  {{ wifiSignalPercent !== null ? `${wifiSignalPercent}%` : 'N/A' }}
                </span>
              </div>
            </div>
          </Card>

          <!-- Status -->
          <Card class="col-span-1">
            <div class="text-center">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</p>
              <StatusBadge
                :status="slaveDetails.status"
                :text="slaveDetails.status"
                class="mt-2"
              />
            </div>
          </Card>
        </div>

        <!-- Resource Usage Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- CPU Usage -->
          <Card title="CPU Usage">
            <div class="flex items-center justify-between">
              <div class="relative w-24 h-24">
                <svg class="w-full h-full" viewBox="0 0 100 100">
                  <circle
                    class="text-gray-200 dark:text-gray-700"
                    stroke="currentColor"
                    stroke-width="8"
                    fill="transparent"
                    r="42"
                    cx="50"
                    cy="50"
                  />
                  <circle
                    :class="getProgressColorClass(slaveDetails.cpu_percent)"
                    stroke="currentColor"
                    stroke-width="8"
                    stroke-linecap="round"
                    fill="transparent"
                    r="42"
                    cx="50"
                    cy="50"
                    :stroke-dasharray="`${slaveDetails.cpu_percent * 2.64} 264`"
                    transform="rotate(-90 50 50)"
                    class="transition-all duration-500"
                  />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold">{{ slaveDetails.cpu_percent?.toFixed(0) || 0 }}%</span>
                </div>
              </div>
              <div class="flex-1 ml-6">
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  Pi Zero 2W - ARM Cortex-A53
                </p>
              </div>
            </div>
          </Card>

          <!-- Memory Usage -->
          <Card title="Memory Usage">
            <div class="flex items-center justify-between">
              <div class="relative w-24 h-24">
                <svg class="w-full h-full" viewBox="0 0 100 100">
                  <circle
                    class="text-gray-200 dark:text-gray-700"
                    stroke="currentColor"
                    stroke-width="8"
                    fill="transparent"
                    r="42"
                    cx="50"
                    cy="50"
                  />
                  <circle
                    :class="getProgressColorClass(slaveDetails.ram_percent)"
                    stroke="currentColor"
                    stroke-width="8"
                    stroke-linecap="round"
                    fill="transparent"
                    r="42"
                    cx="50"
                    cy="50"
                    :stroke-dasharray="`${slaveDetails.ram_percent * 2.64} 264`"
                    transform="rotate(-90 50 50)"
                    class="transition-all duration-500"
                  />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold">{{ slaveDetails.ram_percent?.toFixed(0) || 0 }}%</span>
                </div>
              </div>
              <div class="flex-1 ml-6 space-y-1">
                <div class="flex justify-between text-sm">
                  <span class="text-gray-500 dark:text-gray-400">Used</span>
                  <span class="font-medium">{{ slaveDetails.ram_used_mb || 0 }} MB</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-500 dark:text-gray-400">Available</span>
                  <span class="font-medium">{{ slaveDetails.ram_available_mb || 0 }} MB</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-500 dark:text-gray-400">Total</span>
                  <span class="font-medium">{{ slaveDetails.ram_total_mb || 0 }} MB</span>
                </div>
              </div>
            </div>
          </Card>

          <!-- Disk Usage -->
          <Card title="Disk Usage">
            <div class="flex items-center justify-between">
              <div class="relative w-24 h-24">
                <svg class="w-full h-full" viewBox="0 0 100 100">
                  <circle
                    class="text-gray-200 dark:text-gray-700"
                    stroke="currentColor"
                    stroke-width="8"
                    fill="transparent"
                    r="42"
                    cx="50"
                    cy="50"
                  />
                  <circle
                    :class="getProgressColorClass(slaveDetails.disk_percent)"
                    stroke="currentColor"
                    stroke-width="8"
                    stroke-linecap="round"
                    fill="transparent"
                    r="42"
                    cx="50"
                    cy="50"
                    :stroke-dasharray="`${slaveDetails.disk_percent * 2.64} 264`"
                    transform="rotate(-90 50 50)"
                    class="transition-all duration-500"
                  />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold">{{ slaveDetails.disk_percent?.toFixed(0) || 0 }}%</span>
                </div>
              </div>
              <div class="flex-1 ml-6 space-y-1">
                <div class="flex justify-between text-sm">
                  <span class="text-gray-500 dark:text-gray-400">Used</span>
                  <span class="font-medium">{{ slaveDetails.disk_used_gb?.toFixed(1) || 0 }} GB</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-500 dark:text-gray-400">Free</span>
                  <span class="font-medium">{{ slaveDetails.disk_free_gb?.toFixed(1) || 0 }} GB</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-500 dark:text-gray-400">Total</span>
                  <span class="font-medium">{{ slaveDetails.disk_total_gb?.toFixed(1) || 0 }} GB</span>
                </div>
              </div>
            </div>
          </Card>
        </div>

        <!-- Network Interfaces -->
        <Card title="Network Interfaces">
          <div class="space-y-4">
            <div
              v-for="iface in slaveDetails.network_interfaces"
              :key="iface.interface"
              class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
            >
              <div class="flex items-center space-x-4">
                <div :class="[
                  'w-10 h-10 rounded-full flex items-center justify-center',
                  iface.is_wifi ? 'bg-cyan-100 dark:bg-cyan-900/30' : 'bg-blue-100 dark:bg-blue-900/30'
                ]">
                  <svg v-if="iface.is_wifi" class="w-5 h-5 text-cyan-600 dark:text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                  </svg>
                  <svg v-else class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                  </svg>
                </div>
                <div>
                  <p class="font-medium text-gray-900 dark:text-white">
                    {{ iface.interface }}
                    <span v-if="iface.wifi_ssid" class="text-sm text-gray-500 dark:text-gray-400 ml-2">
                      ({{ iface.wifi_ssid }})
                    </span>
                  </p>
                  <p class="text-sm text-gray-500 dark:text-gray-400 font-mono">
                    {{ iface.ip_address || 'No IP' }}
                  </p>
                </div>
              </div>
              <div class="text-right">
                <p v-if="iface.mac_address" class="text-xs text-gray-400 dark:text-gray-500 font-mono">
                  {{ iface.mac_address }}
                </p>
                <div v-if="iface.is_wifi && iface.wifi_signal_percent !== null" class="flex items-center justify-end mt-1">
                  <WifiIcon :strength="iface.wifi_signal_percent" class="w-4 h-4 mr-1" />
                  <span class="text-sm font-medium" :class="getWifiClass(iface.wifi_signal_percent)">
                    {{ iface.wifi_signal_dbm }} dBm ({{ iface.wifi_signal_percent }}%)
                  </span>
                </div>
              </div>
            </div>

            <div v-if="!slaveDetails.network_interfaces?.length" class="text-center py-8 text-gray-500 dark:text-gray-400">
              No network interfaces found
            </div>
          </div>
        </Card>

        <!-- Warnings -->
        <Card v-if="slaveDetails.warnings?.length" title="Warnings" class="border-amber-200 dark:border-amber-800">
          <div class="space-y-2">
            <div
              v-for="(warning, index) in slaveDetails.warnings"
              :key="index"
              class="flex items-center space-x-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg"
            >
              <svg class="w-5 h-5 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span class="text-sm text-amber-700 dark:text-amber-300">{{ warning }}</span>
            </div>
          </div>
        </Card>

        <!-- Connection Test -->
        <Card title="Connection Test">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-600 dark:text-gray-400">
                Test the heartbeat connection to GenSlave
              </p>
              <p v-if="lastTestResult" class="text-sm mt-1" :class="lastTestResult.success ? 'text-green-600' : 'text-red-600'">
                Last test: {{ lastTestResult.success ? `OK (${lastTestResult.latency_ms}ms)` : lastTestResult.error }}
              </p>
            </div>
            <Button
              variant="primary"
              @click="testConnection"
              :loading="testing"
            >
              <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Test Connection
            </Button>
          </div>
        </Card>
      </template>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useNotificationStore } from '@/stores/notifications'
import MainLayout from '@/components/layout/MainLayout.vue'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import GenSlaveLoader from '@/components/common/GenSlaveLoader.vue'

const systemStore = useSystemStore()
const notifications = useNotificationStore()

const loading = ref(false)
const testing = ref(false)
const error = ref(null)
const slaveDetails = ref(null)
const lastTestResult = ref(null)
let pollInterval = null

// Computed properties
const connectionStatus = computed(() => {
  if (loading.value && !slaveDetails.value) return 'unknown'
  if (error.value) return 'critical'
  if (!slaveDetails.value) return 'unknown'
  return slaveDetails.value.status || 'healthy'
})

const connectionStatusText = computed(() => {
  if (loading.value && !slaveDetails.value) return 'Connecting...'
  if (error.value) return 'Offline'
  if (!slaveDetails.value) return 'Unknown'
  return slaveDetails.value.status === 'healthy' ? 'Online' : slaveDetails.value.status
})

const wifiSignalPercent = computed(() => {
  const wifiIface = slaveDetails.value?.network_interfaces?.find(i => i.is_wifi)
  return wifiIface?.wifi_signal_percent ?? null
})

// Helper functions
function formatUptime(seconds) {
  if (!seconds) return '0s'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  const parts = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  if (minutes > 0) parts.push(`${minutes}m`)

  return parts.join(' ') || '< 1m'
}

function getProgressColorClass(percent) {
  if (percent >= 90) return 'text-red-500'
  if (percent >= 70) return 'text-amber-500'
  return 'text-green-500'
}

function getTempClass(temp) {
  if (!temp) return 'text-gray-500'
  if (temp >= 80) return 'text-red-500'
  if (temp >= 70) return 'text-amber-500'
  return 'text-green-500'
}

function getWifiClass(percent) {
  if (percent === null) return 'text-gray-500'
  if (percent >= 70) return 'text-green-500'
  if (percent >= 40) return 'text-amber-500'
  return 'text-red-500'
}

// Actions
async function refreshHealth() {
  loading.value = true
  error.value = null

  try {
    slaveDetails.value = await systemStore.fetchSlaveDetails()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Failed to connect to GenSlave'
    notifications.error('Failed to fetch GenSlave health')
  } finally {
    loading.value = false
  }
}

async function testConnection() {
  testing.value = true
  try {
    const result = await systemStore.testSlaveConnection()
    lastTestResult.value = result
    if (result.success) {
      notifications.success(`Connection successful (${result.latency_ms}ms)`)
    } else {
      notifications.error(`Connection failed: ${result.error}`)
    }
  } catch (err) {
    lastTestResult.value = { success: false, error: err.message }
    notifications.error('Connection test failed')
  } finally {
    testing.value = false
  }
}

// Lifecycle
onMounted(() => {
  refreshHealth()
  // Poll every 30 seconds
  pollInterval = setInterval(refreshHealth, 30000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})

// WifiIcon component (inline for simplicity)
const WifiIcon = {
  props: {
    strength: {
      type: Number,
      default: null
    }
  },
  template: `
    <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <path v-if="strength === null" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" class="text-gray-400" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
      <template v-else>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :class="strength >= 20 ? 'text-current' : 'text-gray-300 dark:text-gray-600'" d="M12 20h.01" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :class="strength >= 40 ? 'text-current' : 'text-gray-300 dark:text-gray-600'" d="M8.111 16.404a5.5 5.5 0 017.778 0" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :class="strength >= 60 ? 'text-current' : 'text-gray-300 dark:text-gray-600'" d="M4.93 13.333c3.904-3.905 10.236-3.905 14.141 0" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :class="strength >= 80 ? 'text-current' : 'text-gray-300 dark:text-gray-600'" d="M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
      </template>
    </svg>
  `
}
</script>
