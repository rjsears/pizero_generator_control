<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/SystemView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 17th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSystemStore } from '../stores/system'
import { useNotificationStore } from '../stores/notifications'
import api, { systemApi, containersApi } from '../services/api'
import { formatBytes, formatUptime } from '../utils/formatters'
import Card from '../components/common/Card.vue'
import LoadingSpinner from '../components/common/LoadingSpinner.vue'
import HeartbeatLoader from '../components/common/HeartbeatLoader.vue'
import ConfirmDialog from '../components/common/ConfirmDialog.vue'
import SystemTerminal from '../components/system/SystemTerminal.vue'
import {
  CpuChipIcon,
  CircleStackIcon,
  ServerStackIcon,
  ClockIcon,
  ArrowPathIcon,
  SignalIcon,
  CheckCircleIcon,
  GlobeAltIcon,
  ShieldCheckIcon,
  CommandLineIcon,
  WifiIcon,
  LockClosedIcon,
  HeartIcon,
  BoltIcon,
  ServerIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArchiveBoxIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const systemStore = useSystemStore()
const notificationStore = useNotificationStore()

const loading = ref(true)
const activeTab = ref('health')

// Tab definitions
const tabs = [
  { id: 'health', name: 'Health', icon: SignalIcon, iconColor: 'text-emerald-500', bgActive: 'bg-emerald-500/15 dark:bg-emerald-500/20', textActive: 'text-emerald-700 dark:text-emerald-400', borderActive: 'border-emerald-500/30' },
  { id: 'network', name: 'Network', icon: GlobeAltIcon, iconColor: 'text-purple-500', bgActive: 'bg-purple-500/15 dark:bg-purple-500/20', textActive: 'text-purple-700 dark:text-purple-400', borderActive: 'border-purple-500/30' },
  { id: 'terminal', name: 'Terminal', icon: CommandLineIcon, iconColor: 'text-amber-500', bgActive: 'bg-amber-500/15 dark:bg-amber-500/20', textActive: 'text-amber-700 dark:text-amber-400', borderActive: 'border-amber-500/30' },
  { id: 'genslave', name: 'GenSlave', icon: ServerIcon, iconColor: 'text-blue-500', bgActive: 'bg-blue-500/15 dark:bg-blue-500/20', textActive: 'text-blue-700 dark:text-blue-400', borderActive: 'border-blue-500/30' },
]

// Health data state (n8n_nginx style)
const healthData = ref({
  overall_status: 'loading',
  passed: 0,
  warnings: 0,
  errors: 0,
  version: '1.0.0',
  checks: {
    docker: { status: 'ok', details: { running: 0, stopped: 0, unhealthy: 0, unhealthy_containers: [] } },
    services: { status: 'ok', details: {} },
    resources: { status: 'ok', details: { cpu_percent: 0, memory_percent: 0, disk_percent: 0, disk_free_gb: 0 } },
    ssl: { status: 'ok', details: {} },
    genslave: { status: 'ok', details: {} },
  },
  ssl_certificates: [],
})
const healthLoading = ref(false)
const healthLastUpdated = ref(null)

// Loading messages
const healthLoadingMessages = [
  'Running health checks...',
  'Checking system resources...',
  'Inspecting Docker containers...',
  'Verifying SSL certificates...',
  'Pinging GenSlave...',
  'Almost done...',
]
const healthLoadingMessageIndex = ref(0)
let healthLoadingInterval = null

// Network state
const networkInfo = ref({ hostname: '', interfaces: [], gateway: null, dns_servers: [] })
const networkLoading = ref(false)

// External services state
const cloudflareInfo = ref({ installed: false, running: false, connected: false })
const tailscaleInfo = ref({ installed: false, running: false, logged_in: false, tailscale_ip: null })

// SSL state
const sslInfo = ref({ configured: false, certificates: [] })
const sslLoading = ref(false)

// GenSlave state
const slaveInfo = ref({ online: false, last_heartbeat: null, details: null })
const slaveLoading = ref(false)
const testingConnection = ref(false)

// Reboot dialog
const rebootDialog = ref({ open: false, loading: false })

// SSL Renew dialog
const sslRenewDialog = ref({ open: false, loading: false })

// Progress color helper
function getProgressColor(percent) {
  if (percent >= 90) return 'bg-red-500'
  if (percent >= 75) return 'bg-amber-500'
  return 'bg-emerald-500'
}

// Load comprehensive health data (n8n_nginx style)
async function loadHealthData() {
  healthLoading.value = true
  healthLoadingMessageIndex.value = 0

  // Start rotating messages
  healthLoadingInterval = setInterval(() => {
    healthLoadingMessageIndex.value = (healthLoadingMessageIndex.value + 1) % healthLoadingMessages.length
  }, 2000)

  try {
    // Load all health data in parallel
    const [systemRes, containersRes, sslRes, slaveRes] = await Promise.all([
      api.get('/system').catch(() => ({ data: {} })),
      api.get('/metrics/containers/summary').catch(() => ({ data: { total: 0, running: 0, stopped: 0, unhealthy: 0 } })),
      systemApi.getSsl().catch(() => ({ data: { certificates: [] } })),
      api.get('/health/slave').catch(() => ({ data: { connection_status: 'disconnected' } })),
    ])

    const system = systemRes.data
    const containers = containersRes.data
    const ssl = sslRes.data
    const slave = slaveRes.data

    // Calculate status counts
    let passed = 0
    let warnings = 0
    let errors = 0

    // Docker check
    const dockerStatus = containers.unhealthy > 0 ? 'error' : containers.stopped > 0 ? 'warning' : 'ok'
    if (dockerStatus === 'ok') passed++
    else if (dockerStatus === 'warning') warnings++
    else errors++

    // Resources check
    const cpuPercent = system.cpu_percent || 0
    const memPercent = system.ram_percent || 0
    const diskPercent = system.disk_percent || 0
    const resourceStatus = (cpuPercent >= 90 || memPercent >= 90 || diskPercent >= 95) ? 'error' :
                          (cpuPercent >= 75 || memPercent >= 75 || diskPercent >= 80) ? 'warning' : 'ok'
    if (resourceStatus === 'ok') passed++
    else if (resourceStatus === 'warning') warnings++
    else errors++

    // SSL check
    const certs = ssl.certificates || []
    const sslStatus = certs.length === 0 ? 'warning' :
                     certs.some(c => c.days_until_expiry <= 7) ? 'error' :
                     certs.some(c => c.days_until_expiry <= 30) ? 'warning' : 'ok'
    if (sslStatus === 'ok') passed++
    else if (sslStatus === 'warning') warnings++
    else errors++

    // GenSlave check
    const slaveOnline = slave.connection_status === 'connected'
    const slaveStatus = slaveOnline ? 'ok' : 'error'
    if (slaveStatus === 'ok') passed++
    else errors++

    // Overall status
    const overallStatus = errors > 0 ? 'error' : warnings > 0 ? 'warning' : 'healthy'

    healthData.value = {
      overall_status: overallStatus,
      passed,
      warnings,
      errors,
      version: '1.0.0',
      checks: {
        docker: {
          status: dockerStatus,
          details: {
            running: containers.running || 0,
            stopped: containers.stopped || 0,
            unhealthy: containers.unhealthy || 0,
            total: containers.total || 0,
            unhealthy_containers: [],
          },
        },
        services: {
          status: 'ok',
          details: {
            genmaster_api: 'ok',
            nginx: 'ok',
          },
        },
        resources: {
          status: resourceStatus,
          details: {
            cpu_percent: cpuPercent,
            memory_percent: memPercent,
            disk_percent: diskPercent,
            disk_free_gb: system.disk_total_gb ? (system.disk_total_gb - system.disk_used_gb) : 0,
          },
        },
        ssl: {
          status: sslStatus,
          details: certs.length > 0 ? {
            domain: certs[0].domain,
            days_until_expiry: certs[0].days_until_expiry,
          } : { message: 'No certificates found' },
        },
        genslave: {
          status: slaveStatus,
          details: {
            connection_status: slave.connection_status,
            last_heartbeat: slave.last_heartbeat_received,
            latency_ms: slave.latency_ms,
          },
        },
      },
      ssl_certificates: certs,
    }

    healthLastUpdated.value = new Date()
  } catch (error) {
    console.error('Health data load failed:', error)
    notificationStore.error('Failed to load health data')
    healthData.value.overall_status = 'error'
  } finally {
    if (healthLoadingInterval) {
      clearInterval(healthLoadingInterval)
      healthLoadingInterval = null
    }
    healthLoading.value = false
    loading.value = false
  }
}

// Load network info
async function loadNetworkInfo() {
  networkLoading.value = true
  try {
    const [networkRes, cloudflareRes, tailscaleRes] = await Promise.all([
      systemApi.getNetwork(),
      systemApi.getCloudflare().catch(() => ({ data: {} })),
      systemApi.getTailscale().catch(() => ({ data: {} })),
    ])
    networkInfo.value = networkRes.data
    cloudflareInfo.value = cloudflareRes.data
    tailscaleInfo.value = tailscaleRes.data
  } catch (error) {
    console.error('Network info load failed:', error)
    notificationStore.error('Failed to load network information')
  } finally {
    networkLoading.value = false
  }
}

// Load SSL info
async function loadSslInfo() {
  sslLoading.value = true
  try {
    const response = await systemApi.getSsl()
    sslInfo.value = response.data
  } catch (error) {
    console.error('SSL info load failed:', error)
  } finally {
    sslLoading.value = false
  }
}

// Load GenSlave info
async function loadSlaveInfo() {
  slaveLoading.value = true
  try {
    const [healthRes, detailsRes] = await Promise.all([
      api.get('/health/slave').catch(() => ({ data: { connection_status: 'disconnected' } })),
      api.get('/health/slave/details').catch(() => ({ data: null })),
    ])
    slaveInfo.value = {
      online: healthRes.data?.connection_status === 'connected',
      last_heartbeat: healthRes.data?.last_heartbeat_received,
      details: detailsRes.data,
    }
  } catch (error) {
    console.error('GenSlave info load failed:', error)
    slaveInfo.value = { online: false, last_heartbeat: null, details: null }
  } finally {
    slaveLoading.value = false
  }
}

// Test GenSlave connection
async function testSlaveConnection() {
  testingConnection.value = true
  try {
    const response = await api.post('/health/test-slave')
    if (response.data?.success) {
      notificationStore.success(`Connection successful (${response.data.latency_ms || response.data.response_time_ms || 0}ms)`)
      await loadSlaveInfo()
    } else {
      notificationStore.error(`Connection failed: ${response.data?.error || 'Unknown error'}`)
    }
  } catch (error) {
    notificationStore.error(`Connection failed: ${error.response?.data?.detail || error.message}`)
  } finally {
    testingConnection.value = false
  }
}

// SSL renewal
function openSslRenewModal() {
  sslRenewDialog.value.open = true
}

async function confirmSslRenew() {
  sslRenewDialog.value.loading = true
  try {
    const response = await systemApi.sslRenew()
    if (response.data?.success) {
      notificationStore.success('SSL certificate renewed successfully')
      await loadHealthData()
    } else {
      notificationStore.error(response.data?.message || 'Failed to renew certificate')
    }
    sslRenewDialog.value.open = false
  } catch (error) {
    notificationStore.error('Failed to renew certificate')
  } finally {
    sslRenewDialog.value.loading = false
  }
}

// Reboot system
function openRebootDialog() {
  rebootDialog.value.open = true
}

async function confirmReboot() {
  rebootDialog.value.loading = true
  try {
    await api.post('/system/reboot')
    notificationStore.warning('System is rebooting...')
    rebootDialog.value.open = false
  } catch (error) {
    notificationStore.error('Failed to reboot system')
  } finally {
    rebootDialog.value.loading = false
  }
}

// Watch for tab changes
watch(activeTab, (newTab) => {
  if (newTab === 'network' && networkInfo.value.interfaces.length === 0) {
    loadNetworkInfo()
    loadSslInfo()
  } else if (newTab === 'genslave') {
    loadSlaveInfo()
  }
})

// Check for query param
onMounted(async () => {
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
  await loadHealthData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-primary">System</h1>
        <p class="text-secondary mt-1">Server health, network, and GenSlave status</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-400 dark:border-gray-700 p-1.5 flex gap-1.5 overflow-x-auto">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap border',
          activeTab === tab.id
            ? `${tab.bgActive} ${tab.textActive} ${tab.borderActive}`
            : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50 border-transparent'
        ]"
      >
        <component :is="tab.icon" :class="['h-4 w-4', activeTab === tab.id ? '' : tab.iconColor]" />
        {{ tab.name }}
      </button>
    </div>

    <!-- Health Tab -->
    <template v-if="activeTab === 'health'">
      <HeartbeatLoader v-if="healthLoading" :text="healthLoadingMessages[healthLoadingMessageIndex]" color="emerald" class="py-16 mt-8" />

      <template v-else>
        <!-- Overall Status Banner -->
        <div
          :class="[
            'rounded-xl p-6 border-2 relative overflow-hidden',
            healthData.overall_status === 'healthy'
              ? 'bg-gradient-to-r from-emerald-500/10 to-emerald-500/5 border-emerald-500/50'
              : healthData.overall_status === 'warning'
                ? 'bg-gradient-to-r from-amber-500/10 to-amber-500/5 border-amber-500/50'
                : 'bg-gradient-to-r from-red-500/10 to-red-500/5 border-red-500/50'
          ]"
        >
          <!-- Animated pulse background for healthy status -->
          <div
            v-if="healthData.overall_status === 'healthy'"
            class="absolute inset-0 bg-emerald-500/5 animate-pulse"
          ></div>

          <div class="relative flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div
                :class="[
                  'p-4 rounded-2xl',
                  healthData.overall_status === 'healthy'
                    ? 'bg-emerald-500/20'
                    : healthData.overall_status === 'warning'
                      ? 'bg-amber-500/20'
                      : 'bg-red-500/20'
                ]"
              >
                <HeartIcon
                  :class="[
                    'h-10 w-10',
                    healthData.overall_status === 'healthy'
                      ? 'text-emerald-500'
                      : healthData.overall_status === 'warning'
                        ? 'text-amber-500'
                        : 'text-red-500'
                  ]"
                />
              </div>
              <div>
                <h2 class="text-2xl font-bold text-primary">
                  System Health:
                  <span
                    :class="[
                      healthData.overall_status === 'healthy'
                        ? 'text-emerald-500'
                        : healthData.overall_status === 'warning'
                          ? 'text-amber-500'
                          : 'text-red-500'
                    ]"
                  >
                    {{ healthData.overall_status?.toUpperCase() || 'CHECKING' }}
                  </span>
                </h2>
                <p class="text-secondary mt-1">
                  GenMaster v{{ healthData.version }} •
                  Last updated: {{ healthLastUpdated ? new Date(healthLastUpdated).toLocaleTimeString() : 'Never' }}
                </p>
              </div>
            </div>

            <div class="flex items-center gap-6">
              <!-- Counters -->
              <div class="text-center">
                <p class="text-3xl font-bold text-emerald-500">{{ healthData.passed || 0 }}</p>
                <p class="text-xs text-muted uppercase tracking-wide">Passed</p>
              </div>
              <div class="text-center">
                <p class="text-3xl font-bold text-amber-500">{{ healthData.warnings || 0 }}</p>
                <p class="text-xs text-muted uppercase tracking-wide">Warnings</p>
              </div>
              <div class="text-center">
                <p class="text-3xl font-bold text-red-500">{{ healthData.errors || 0 }}</p>
                <p class="text-xs text-muted uppercase tracking-wide">Errors</p>
              </div>

              <button
                @click="loadHealthData"
                :disabled="healthLoading"
                class="btn-secondary flex items-center gap-2 ml-4"
              >
                <ArrowPathIcon :class="['h-4 w-4', healthLoading ? 'animate-spin' : '']" />
                Refresh
              </button>
            </div>
          </div>
        </div>

        <!-- Health Check Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mt-6">
          <!-- Docker Containers -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                  <ServerIcon class="h-5 w-5 text-blue-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">Docker Containers</h3>
                  <p class="text-xs text-muted">Container status and health</p>
                </div>
                <span
                  :class="[
                    'px-2 py-1 rounded-full text-xs font-medium',
                    healthData.checks?.docker?.status === 'ok'
                      ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                      : healthData.checks?.docker?.status === 'warning'
                        ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
                        : 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400'
                  ]"
                >
                  {{ healthData.checks?.docker?.status?.toUpperCase() || 'N/A' }}
                </span>
              </div>
              <div class="space-y-2">
                <div class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Running</span>
                  <span class="font-medium text-emerald-500">{{ healthData.checks?.docker?.details?.running || 0 }}</span>
                </div>
                <div class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Stopped</span>
                  <span class="font-medium text-gray-500">{{ healthData.checks?.docker?.details?.stopped || 0 }}</span>
                </div>
                <div class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Unhealthy</span>
                  <span :class="['font-medium', (healthData.checks?.docker?.details?.unhealthy || 0) > 0 ? 'text-red-500' : 'text-gray-500']">
                    {{ healthData.checks?.docker?.details?.unhealthy || 0 }}
                  </span>
                </div>
                <div class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Total</span>
                  <span class="font-medium text-primary">{{ healthData.checks?.docker?.details?.total || 0 }}</span>
                </div>
              </div>
            </div>
          </Card>

          <!-- Core Services -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-500/20">
                  <BoltIcon class="h-5 w-5 text-purple-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">Core Services</h3>
                  <p class="text-xs text-muted">GenMaster API, Nginx</p>
                </div>
                <span
                  :class="[
                    'px-2 py-1 rounded-full text-xs font-medium',
                    healthData.checks?.services?.status === 'ok'
                      ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                      : 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400'
                  ]"
                >
                  {{ healthData.checks?.services?.status?.toUpperCase() || 'N/A' }}
                </span>
              </div>
              <div class="space-y-2">
                <div
                  v-for="(status, service) in healthData.checks?.services?.details"
                  :key="service"
                  class="flex justify-between items-center text-sm"
                >
                  <span class="text-secondary capitalize">{{ service.replace('_', ' ') }}</span>
                  <span
                    :class="[
                      'flex items-center gap-1 font-medium',
                      status === 'ok' ? 'text-emerald-500' : 'text-red-500'
                    ]"
                  >
                    <CheckCircleIcon v-if="status === 'ok'" class="h-4 w-4" />
                    <XCircleIcon v-else class="h-4 w-4" />
                    {{ status }}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          <!-- Host System Resources -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-cyan-100 dark:bg-cyan-500/20">
                  <CpuChipIcon class="h-5 w-5 text-cyan-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">Host System Resources</h3>
                  <p class="text-xs text-muted">CPU, Memory, Disk</p>
                </div>
                <span
                  :class="[
                    'px-2 py-1 rounded-full text-xs font-medium',
                    healthData.checks?.resources?.status === 'ok'
                      ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                      : healthData.checks?.resources?.status === 'warning'
                        ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
                        : 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400'
                  ]"
                >
                  {{ healthData.checks?.resources?.status?.toUpperCase() || 'N/A' }}
                </span>
              </div>
              <div class="space-y-3">
                <!-- CPU -->
                <div>
                  <div class="flex justify-between items-center text-sm mb-1">
                    <span class="text-secondary">CPU</span>
                    <span class="font-medium text-primary">{{ healthData.checks?.resources?.details?.cpu_percent?.toFixed(1) || 0 }}%</span>
                  </div>
                  <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      :class="['h-full rounded-full transition-all', getProgressColor(healthData.checks?.resources?.details?.cpu_percent || 0)]"
                      :style="{ width: `${healthData.checks?.resources?.details?.cpu_percent || 0}%` }"
                    ></div>
                  </div>
                </div>
                <!-- Memory -->
                <div>
                  <div class="flex justify-between items-center text-sm mb-1">
                    <span class="text-secondary">Memory</span>
                    <span class="font-medium text-primary">{{ healthData.checks?.resources?.details?.memory_percent?.toFixed(1) || 0 }}%</span>
                  </div>
                  <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      :class="['h-full rounded-full transition-all', getProgressColor(healthData.checks?.resources?.details?.memory_percent || 0)]"
                      :style="{ width: `${healthData.checks?.resources?.details?.memory_percent || 0}%` }"
                    ></div>
                  </div>
                </div>
                <!-- Disk -->
                <div>
                  <div class="flex justify-between items-center text-sm mb-1">
                    <span class="text-secondary">Disk</span>
                    <span class="font-medium text-primary">{{ healthData.checks?.resources?.details?.disk_percent?.toFixed(1) || 0 }}%</span>
                  </div>
                  <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      :class="['h-full rounded-full transition-all', getProgressColor(healthData.checks?.resources?.details?.disk_percent || 0)]"
                      :style="{ width: `${healthData.checks?.resources?.details?.disk_percent || 0}%` }"
                    ></div>
                  </div>
                  <p class="text-xs text-muted mt-1">{{ healthData.checks?.resources?.details?.disk_free_gb?.toFixed(1) || 0 }} GB free</p>
                </div>
              </div>
            </div>
          </Card>

          <!-- SSL Certificates -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-500/20">
                  <LockClosedIcon class="h-5 w-5 text-emerald-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">SSL Certificates</h3>
                  <p class="text-xs text-muted">Certificate validity</p>
                </div>
                <div class="flex items-center gap-2">
                  <button
                    @click="openSslRenewModal"
                    :class="[
                      'px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm flex items-center gap-1.5',
                      healthData.checks?.ssl?.status === 'ok'
                        ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                        : 'bg-amber-500 hover:bg-amber-600 text-white'
                    ]"
                  >
                    <ArrowPathIcon class="h-3.5 w-3.5" />
                    Force Renew
                  </button>
                  <span
                    :class="[
                      'px-2 py-1 rounded-full text-xs font-medium',
                      healthData.checks?.ssl?.status === 'ok'
                        ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                        : healthData.checks?.ssl?.status === 'warning'
                          ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
                          : 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400'
                    ]"
                  >
                    {{ healthData.checks?.ssl?.status?.toUpperCase() || 'N/A' }}
                  </span>
                </div>
              </div>
              <!-- Show certificates from array if available -->
              <div v-if="healthData.ssl_certificates?.length" class="space-y-2">
                <div
                  v-for="cert in healthData.ssl_certificates"
                  :key="cert.domain"
                  class="p-3 rounded-lg bg-surface-hover"
                >
                  <div class="flex justify-between items-center text-sm mb-2">
                    <span class="text-secondary">Domain</span>
                    <span class="font-medium text-primary">{{ cert.domain }}</span>
                  </div>
                  <div class="flex justify-between items-center text-sm mb-2">
                    <span class="text-secondary">Valid For</span>
                    <span
                      :class="[
                        'font-medium',
                        cert.days_until_expiry > 30 ? 'text-emerald-500' :
                        cert.days_until_expiry > 7 ? 'text-amber-500' : 'text-red-500'
                      ]"
                    >
                      {{ cert.days_until_expiry }} days
                    </span>
                  </div>
                  <div class="flex justify-between items-center text-sm">
                    <span class="text-secondary">Expires</span>
                    <span class="font-medium text-primary text-xs">{{ cert.valid_until || cert.expires }}</span>
                  </div>
                </div>
              </div>
              <!-- Fallback: show from ssl details if no certificates array -->
              <div v-else-if="healthData.checks?.ssl?.details?.domain" class="space-y-2">
                <div class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Domain</span>
                  <span class="font-medium text-primary">{{ healthData.checks?.ssl?.details?.domain }}</span>
                </div>
                <div class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Valid For</span>
                  <span
                    :class="[
                      'font-medium',
                      (healthData.checks?.ssl?.details?.days_until_expiry || 0) > 30 ? 'text-emerald-500' :
                      (healthData.checks?.ssl?.details?.days_until_expiry || 0) > 7 ? 'text-amber-500' : 'text-red-500'
                    ]"
                  >
                    {{ healthData.checks?.ssl?.details?.days_until_expiry || 0 }} days
                  </span>
                </div>
              </div>
              <!-- No SSL data at all -->
              <div v-else class="text-sm text-muted">
                {{ healthData.checks?.ssl?.details?.message || 'No certificates found' }}
              </div>
            </div>
          </Card>

          <!-- GenSlave Status -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                  <ServerIcon class="h-5 w-5 text-blue-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">GenSlave</h3>
                  <p class="text-xs text-muted">Remote relay controller</p>
                </div>
                <span
                  :class="[
                    'px-2 py-1 rounded-full text-xs font-medium',
                    healthData.checks?.genslave?.status === 'ok'
                      ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                      : 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400'
                  ]"
                >
                  {{ healthData.checks?.genslave?.details?.connection_status?.toUpperCase() || 'OFFLINE' }}
                </span>
              </div>
              <div class="space-y-2">
                <div class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Status</span>
                  <span :class="['font-medium', healthData.checks?.genslave?.status === 'ok' ? 'text-emerald-500' : 'text-red-500']">
                    {{ healthData.checks?.genslave?.status === 'ok' ? 'Online' : 'Offline' }}
                  </span>
                </div>
                <div v-if="healthData.checks?.genslave?.details?.latency_ms" class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Latency</span>
                  <span class="font-medium text-primary">{{ healthData.checks?.genslave?.details?.latency_ms?.toFixed(0) }}ms</span>
                </div>
                <div v-if="healthData.checks?.genslave?.details?.last_heartbeat" class="flex justify-between items-center text-sm">
                  <span class="text-secondary">Last Heartbeat</span>
                  <span class="font-medium text-primary text-xs">{{ new Date(healthData.checks?.genslave?.details?.last_heartbeat * 1000).toLocaleTimeString() }}</span>
                </div>
              </div>
            </div>
          </Card>

          <!-- System Actions -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-red-100 dark:bg-red-500/20">
                  <ExclamationTriangleIcon class="h-5 w-5 text-red-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">System Actions</h3>
                  <p class="text-xs text-muted">Administrative controls</p>
                </div>
              </div>
              <div class="space-y-2">
                <button @click="openRebootDialog" class="w-full btn-warning flex items-center justify-center gap-2">
                  <ArrowPathIcon class="h-5 w-5" />
                  Reboot System
                </button>
              </div>
            </div>
          </Card>
        </div>
      </template>
    </template>

    <!-- Network Tab -->
    <template v-if="activeTab === 'network'">
      <LoadingSpinner v-if="networkLoading" text="Loading network info..." class="py-16" />

      <template v-else>
        <!-- Network Interfaces -->
        <Card title="Network Interfaces" subtitle="Local network configuration">
          <div class="space-y-3">
            <div
              v-for="iface in networkInfo.interfaces"
              :key="iface.name"
              class="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50"
            >
              <div class="flex items-center gap-3">
                <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                  <WifiIcon class="h-5 w-5 text-blue-500" />
                </div>
                <div>
                  <p class="font-medium text-primary">{{ iface.name }}</p>
                  <p class="text-sm text-muted font-mono">{{ iface.ipv4 || 'No IP' }}</p>
                </div>
              </div>
              <span :class="['px-2 py-1 rounded-full text-xs font-medium', iface.state === 'up' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400']">
                {{ iface.state?.toUpperCase() || 'UNKNOWN' }}
              </span>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <dl class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt class="text-secondary">Hostname</dt>
                <dd class="font-medium text-primary">{{ networkInfo.hostname || 'N/A' }}</dd>
              </div>
              <div>
                <dt class="text-secondary">Gateway</dt>
                <dd class="font-medium text-primary font-mono">{{ networkInfo.gateway || 'N/A' }}</dd>
              </div>
              <div class="col-span-2">
                <dt class="text-secondary">DNS Servers</dt>
                <dd class="font-medium text-primary font-mono">{{ networkInfo.dns_servers?.join(', ') || 'N/A' }}</dd>
              </div>
            </dl>
          </div>
        </Card>

        <!-- External Services -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Cloudflare Tunnel -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div :class="['p-2 rounded-lg', cloudflareInfo.running ? 'bg-emerald-100 dark:bg-emerald-500/20' : 'bg-gray-100 dark:bg-gray-700']">
                  <GlobeAltIcon :class="['h-5 w-5', cloudflareInfo.running ? 'text-emerald-500' : 'text-gray-500']" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">Cloudflare Tunnel</h3>
                  <p class="text-xs text-muted">Secure tunnel for external access</p>
                </div>
                <span :class="['px-2 py-1 rounded-full text-xs font-medium', cloudflareInfo.running ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : cloudflareInfo.installed ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400']">
                  {{ cloudflareInfo.running ? 'CONNECTED' : cloudflareInfo.installed ? 'STOPPED' : 'NOT INSTALLED' }}
                </span>
              </div>
            </div>
          </Card>

          <!-- Tailscale -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div :class="['p-2 rounded-lg', tailscaleInfo.connected ? 'bg-emerald-100 dark:bg-emerald-500/20' : 'bg-gray-100 dark:bg-gray-700']">
                  <ShieldCheckIcon :class="['h-5 w-5', tailscaleInfo.connected ? 'text-emerald-500' : 'text-gray-500']" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">Tailscale VPN</h3>
                  <p class="text-xs text-muted">{{ tailscaleInfo.ip_addresses?.[0] || 'Mesh VPN network' }}</p>
                </div>
                <span :class="['px-2 py-1 rounded-full text-xs font-medium', tailscaleInfo.connected ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : tailscaleInfo.running ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400']">
                  {{ tailscaleInfo.connected ? 'CONNECTED' : tailscaleInfo.running ? 'DISCONNECTED' : 'NOT RUNNING' }}
                </span>
              </div>
            </div>
          </Card>
        </div>

        <!-- SSL Certificates -->
        <Card title="SSL Certificates" subtitle="HTTPS certificate status">
          <LoadingSpinner v-if="sslLoading" size="sm" text="Loading SSL info..." />
          <div v-else-if="sslInfo.certificates?.length > 0" class="space-y-3">
            <div
              v-for="cert in sslInfo.certificates"
              :key="cert.domain"
              class="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <ShieldCheckIcon :class="['h-5 w-5', cert.days_until_expiry > 30 ? 'text-emerald-500' : cert.days_until_expiry > 7 ? 'text-amber-500' : 'text-red-500']" />
                  <span class="font-medium text-primary">{{ cert.domain }}</span>
                </div>
                <span :class="['text-sm font-medium', cert.days_until_expiry > 30 ? 'text-emerald-500' : cert.days_until_expiry > 7 ? 'text-amber-500' : 'text-red-500']">
                  {{ cert.days_until_expiry }} days left
                </span>
              </div>
              <dl class="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <dt class="text-muted">Valid From</dt>
                  <dd class="text-secondary">{{ cert.valid_from }}</dd>
                </div>
                <div>
                  <dt class="text-muted">Valid Until</dt>
                  <dd class="text-secondary">{{ cert.valid_until }}</dd>
                </div>
              </dl>
            </div>
          </div>
          <div v-else class="text-center py-4 text-muted">
            No SSL certificates configured
          </div>
        </Card>
      </template>
    </template>

    <!-- Terminal Tab -->
    <template v-if="activeTab === 'terminal'">
      <!-- Header Banner -->
      <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-amber-500 via-orange-500 to-red-500 p-6 text-white shadow-lg">
        <div class="absolute inset-0 bg-black/10"></div>
        <div class="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
        <div class="absolute -bottom-8 -left-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
        <div class="relative flex items-center gap-4">
          <div class="flex h-14 w-14 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
            <CommandLineIcon class="h-8 w-8" />
          </div>
          <div>
            <h2 class="text-2xl font-bold">Terminal Access</h2>
            <p class="text-white/80">Connect to container or host shell</p>
          </div>
        </div>
      </div>

      <!-- Terminal Component -->
      <SystemTerminal />
    </template>

    <!-- GenSlave Tab -->
    <template v-if="activeTab === 'genslave'">
      <LoadingSpinner v-if="slaveLoading" text="Loading GenSlave info..." class="py-16" />

      <template v-else>
        <!-- GenSlave Status Banner -->
        <div :class="['rounded-xl p-6 border-2 relative overflow-hidden', slaveInfo.online ? 'bg-gradient-to-r from-emerald-500/10 to-emerald-500/5 border-emerald-500/50' : 'bg-gradient-to-r from-red-500/10 to-red-500/5 border-red-500/50']">
          <div class="relative flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div :class="['p-4 rounded-2xl', slaveInfo.online ? 'bg-emerald-500/20' : 'bg-red-500/20']">
                <ServerIcon :class="['h-10 w-10', slaveInfo.online ? 'text-emerald-500' : 'text-red-500']" />
              </div>
              <div>
                <h2 class="text-2xl font-bold text-primary">
                  GenSlave: <span :class="slaveInfo.online ? 'text-emerald-500' : 'text-red-500'">{{ slaveInfo.online ? 'ONLINE' : 'OFFLINE' }}</span>
                </h2>
                <p class="text-secondary mt-1">
                  Last heartbeat: {{ slaveInfo.last_heartbeat ? new Date(slaveInfo.last_heartbeat * 1000).toLocaleString() : 'Never' }}
                </p>
              </div>
            </div>

            <button
              @click="testSlaveConnection"
              :disabled="testingConnection"
              class="btn-secondary flex items-center gap-2"
            >
              <BoltIcon :class="['h-4 w-4', testingConnection ? 'animate-pulse' : '']" />
              Test Connection
            </button>
          </div>
        </div>

        <!-- GenSlave Details -->
        <div v-if="slaveInfo.details" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <!-- CPU -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-24 h-24" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="8" fill="transparent" r="42" cx="50" cy="50" />
                  <circle class="text-blue-500" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${(slaveInfo.details.cpu_percent || 0) * 2.64} 264`" transform="rotate(-90 50 50)" />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-primary">{{ slaveInfo.details.cpu_percent || 0 }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">CPU Usage</p>
            </div>
          </Card>

          <!-- Memory -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-24 h-24" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="8" fill="transparent" r="42" cx="50" cy="50" />
                  <circle class="text-purple-500" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${(slaveInfo.details.memory_percent || 0) * 2.64} 264`" transform="rotate(-90 50 50)" />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-primary">{{ slaveInfo.details.memory_percent || 0 }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Memory Usage</p>
            </div>
          </Card>

          <!-- Disk -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-24 h-24" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="8" fill="transparent" r="42" cx="50" cy="50" />
                  <circle class="text-emerald-500" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${(slaveInfo.details.disk_percent || 0) * 2.64} 264`" transform="rotate(-90 50 50)" />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-primary">{{ slaveInfo.details.disk_percent || 0 }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Disk Usage</p>
            </div>
          </Card>

          <!-- Temperature -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-24 h-24" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="8" fill="transparent" r="42" cx="50" cy="50" />
                  <circle class="text-amber-500" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${Math.min(slaveInfo.details.temperature || 0, 100) * 2.64} 264`" transform="rotate(-90 50 50)" />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-primary">{{ slaveInfo.details.temperature || 0 }}°C</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Temperature</p>
            </div>
          </Card>
        </div>

        <!-- No details available -->
        <Card v-else>
          <div class="text-center py-8 text-muted">
            <ServerIcon class="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>GenSlave details not available</p>
            <p class="text-sm mt-1">Connect to GenSlave to view system metrics</p>
          </div>
        </Card>
      </template>
    </template>

    <!-- Reboot Confirmation Dialog -->
    <ConfirmDialog
      :open="rebootDialog.open"
      title="Reboot System"
      message="Are you sure you want to reboot the system? This will temporarily interrupt all services including generator monitoring."
      confirm-text="Reboot"
      :loading="rebootDialog.loading"
      danger
      @confirm="confirmReboot"
      @cancel="rebootDialog.open = false"
    />

    <!-- SSL Renew Confirmation Dialog -->
    <ConfirmDialog
      :open="sslRenewDialog.open"
      title="Force SSL Renewal"
      message="This will force a renewal of the SSL certificates. Are you sure you want to continue?"
      confirm-text="Renew"
      :loading="sslRenewDialog.loading"
      @confirm="confirmSslRenew"
      @cancel="sslRenewDialog.open = false"
    />
  </div>
</template>
