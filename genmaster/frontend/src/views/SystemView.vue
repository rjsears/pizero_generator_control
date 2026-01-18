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
import api, { systemApi, containersApi, genslaveApi, configApi } from '../services/api'
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
  ShieldExclamationIcon,
  CommandLineIcon,
  WifiIcon,
  LockClosedIcon,
  HeartIcon,
  BoltIcon,
  ServerIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArchiveBoxIcon,
  CloudIcon,
  KeyIcon,
  LinkIcon,
  ChevronDownIcon,
  Cog6ToothIcon,
  FireIcon,
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
const networkLoadingMessages = [
  'Scanning network interfaces...',
  'Checking VPN status...',
  'Querying DNS servers...',
  'Detecting tunnel connections...',
]
const networkLoadingMessageIndex = ref(0)
let networkLoadingInterval = null

// External services state
const externalServices = ref([])
const cloudflareInfo = ref({ installed: false, running: false, connected: false })
const tailscaleInfo = ref({ installed: false, running: false, logged_in: false, tailscale_ip: null })
const peersExpanded = ref(false)

// SSL state
const sslInfo = ref({ configured: false, certificates: [] })
const sslLoading = ref(false)

// GenSlave state
const slaveInfo = ref({ online: false, last_heartbeat: null, details: null })
const slaveLoading = ref(false)
const testingConnection = ref(false)
const slaveLoadingMessages = [
  'Connecting to GenSlave...',
  'Fetching system info...',
  'Checking relay status...',
  'Reading failsafe state...',
]
const slaveLoadingMessageIndex = ref(0)
let slaveLoadingInterval = null

// GenSlave comprehensive data
const slaveSystemInfo = ref(null)  // GET /api/system
const slaveHealthStatus = ref(null)  // GET /api/health
const slaveFailsafeStatus = ref(null)  // GET /api/failsafe
const slaveRelayState = ref(null)  // GET /api/relay/state
const relayArmed = ref(false)
const armingRelay = ref(false)

// GenSlave connection settings
const slaveConfig = ref({
  slave_api_url: 'http://genslave.local:8001',
  heartbeat_interval_seconds: 30,
})
const savingSlaveConfig = ref(false)

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
    const [systemRes, containersRes, sslRes, slaveRes, dockerRes] = await Promise.all([
      api.get('/system').catch(() => ({ data: {} })),
      api.get('/metrics/containers/summary').catch(() => ({ data: { total: 0, running: 0, stopped: 0, unhealthy: 0 } })),
      systemApi.getSsl().catch(() => ({ data: { certificates: [] } })),
      api.get('/health/slave').catch(() => ({ data: { connection_status: 'disconnected' } })),
      systemApi.dockerInfo().catch(() => ({ data: { disk_usage_gb: 0 } })),
    ])

    const system = systemRes.data
    const containers = containersRes.data
    const ssl = sslRes.data
    const slave = slaveRes.data
    const docker = dockerRes.data

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
      docker_disk_usage_gb: docker.disk_usage_gb || 0,
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
  networkLoadingMessageIndex.value = 0

  // Start rotating messages
  networkLoadingInterval = setInterval(() => {
    networkLoadingMessageIndex.value = (networkLoadingMessageIndex.value + 1) % networkLoadingMessages.length
  }, 1500)

  try {
    const [networkRes, cloudflareRes, tailscaleRes, servicesRes] = await Promise.all([
      systemApi.getNetwork(),
      systemApi.getCloudflare().catch(() => ({ data: {} })),
      systemApi.getTailscale().catch(() => ({ data: {} })),
      systemApi.getExternalServices().catch(() => ({ data: [] })),
    ])
    networkInfo.value = networkRes.data
    cloudflareInfo.value = cloudflareRes.data
    tailscaleInfo.value = tailscaleRes.data
    externalServices.value = servicesRes.data || []
  } catch (error) {
    console.error('Network info load failed:', error)
    notificationStore.error('Failed to load network information')
  } finally {
    if (networkLoadingInterval) {
      clearInterval(networkLoadingInterval)
      networkLoadingInterval = null
    }
    networkLoading.value = false
  }
}

// Modal functions for VPN configuration
function openCloudflareTokenModal() {
  notificationStore.info('Cloudflare token configuration not yet implemented')
}

function openTailscaleKeyModal() {
  notificationStore.info('Tailscale key configuration not yet implemented')
}

function openRestartDialog(containerName, serviceName) {
  if (confirm(`Are you sure you want to restart ${serviceName}?`)) {
    restartContainer(containerName, serviceName)
  }
}

async function restartContainer(containerName, serviceName) {
  try {
    await containersApi.restart(containerName)
    notificationStore.success(`${serviceName} restarted successfully`)
    await loadNetworkInfo()
  } catch (error) {
    notificationStore.error(`Failed to restart ${serviceName}`)
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

// Load GenSlave info (comprehensive)
async function loadSlaveInfo() {
  slaveLoading.value = true
  slaveLoadingMessageIndex.value = 0

  // Start rotating loading messages
  slaveLoadingInterval = setInterval(() => {
    slaveLoadingMessageIndex.value = (slaveLoadingMessageIndex.value + 1) % slaveLoadingMessages.length
  }, 1500)

  try {
    // Load config first
    try {
      const configRes = await configApi.get()
      if (configRes.data) {
        slaveConfig.value.slave_api_url = configRes.data.slave_api_url || slaveConfig.value.slave_api_url
        slaveConfig.value.heartbeat_interval_seconds = configRes.data.heartbeat_interval_seconds || 30
      }
    } catch (e) {
      console.warn('Failed to load config for GenSlave:', e)
    }

    // Load all GenSlave data in parallel with better error tracking
    let systemError = null
    let healthStatusError = null

    const [healthRes, systemRes, healthStatusRes, failsafeRes, relayRes] = await Promise.all([
      api.get('/health/slave').catch((e) => {
        console.warn('Failed to get /health/slave:', e.response?.data || e.message)
        return { data: { connection_status: 'disconnected' } }
      }),
      genslaveApi.getSystemInfo().catch((e) => {
        systemError = e.response?.data?.detail || e.message
        console.warn('Failed to get GenSlave system info:', systemError)
        return { data: null }
      }),
      genslaveApi.getHealthStatus().catch((e) => {
        healthStatusError = e.response?.data?.detail || e.message
        console.warn('Failed to get GenSlave health status:', healthStatusError)
        return { data: null }
      }),
      genslaveApi.getFailsafeStatus().catch((e) => {
        console.warn('Failed to get GenSlave failsafe status:', e.response?.data?.detail || e.message)
        return { data: null }
      }),
      genslaveApi.getRelayState().catch((e) => {
        console.warn('Failed to get GenSlave relay state:', e.response?.data?.detail || e.message)
        return { data: null }
      }),
    ])

    // Check if we got system data - if not, GenSlave is likely unreachable
    const isOnline = systemRes.data !== null

    // Basic connection info
    slaveInfo.value = {
      online: isOnline,
      last_heartbeat: healthRes.data?.last_heartbeat_received,
      details: systemRes.data,
      error: systemError,
    }

    // Comprehensive data
    slaveSystemInfo.value = systemRes.data
    slaveHealthStatus.value = healthStatusRes.data
    slaveFailsafeStatus.value = failsafeRes.data
    slaveRelayState.value = relayRes.data

    // Update armed state from relay state or health status
    relayArmed.value = relayRes.data?.armed || healthStatusRes.data?.armed || false

    // Show error notification if we couldn't reach GenSlave
    if (!isOnline && systemError) {
      notificationStore.error(`GenSlave unreachable: ${systemError}`)
    }
  } catch (error) {
    console.error('GenSlave info load failed:', error)
    slaveInfo.value = { online: false, last_heartbeat: null, details: null, error: error.message }
    slaveSystemInfo.value = null
    slaveHealthStatus.value = null
    slaveFailsafeStatus.value = null
    slaveRelayState.value = null
  } finally {
    if (slaveLoadingInterval) {
      clearInterval(slaveLoadingInterval)
      slaveLoadingInterval = null
    }
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

// Toggle relay ARM/DISARM
async function toggleRelayArm() {
  armingRelay.value = true
  try {
    if (relayArmed.value) {
      await genslaveApi.disarm()
      relayArmed.value = false
      notificationStore.success('Relay disarmed')
    } else {
      await genslaveApi.arm()
      relayArmed.value = true
      notificationStore.success('Relay armed - generator can now be started')
    }
  } catch (err) {
    notificationStore.error('Failed to toggle relay arm state')
    console.error('Failed to toggle relay arm state:', err)
  } finally {
    armingRelay.value = false
  }
}

// Save GenSlave connection settings
async function saveSlaveConfig() {
  savingSlaveConfig.value = true
  try {
    await configApi.update({
      slave_api_url: slaveConfig.value.slave_api_url,
      heartbeat_interval_seconds: slaveConfig.value.heartbeat_interval_seconds,
    })
    notificationStore.success('GenSlave settings saved')
  } catch (error) {
    notificationStore.error('Failed to save GenSlave settings')
  } finally {
    savingSlaveConfig.value = false
  }
}

// Format seconds to human readable
function formatSeconds(seconds) {
  if (!seconds || seconds <= 0) return '0s'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${mins}m`
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

// Check for query param and load appropriate data
onMounted(async () => {
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
  await loadHealthData()

  // Load tab-specific data based on initial tab
  if (activeTab.value === 'genslave') {
    loadSlaveInfo()
  } else if (activeTab.value === 'network') {
    loadNetworkInfo()
    loadSslInfo()
  }
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
                <!-- Disk -->
                <div>
                  <div class="flex justify-between items-center text-sm mb-1">
                    <span class="text-secondary">Disk</span>
                    <span class="font-medium text-primary">{{ healthData.checks?.resources?.details?.disk_percent || 0 }}%</span>
                  </div>
                  <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      :class="[
                        'h-full rounded-full transition-all',
                        (healthData.checks?.resources?.details?.disk_percent || 0) >= 90 ? 'bg-red-500' :
                        (healthData.checks?.resources?.details?.disk_percent || 0) >= 75 ? 'bg-amber-500' : 'bg-cyan-500'
                      ]"
                      :style="{ width: `${healthData.checks?.resources?.details?.disk_percent || 0}%` }"
                    ></div>
                  </div>
                  <p class="text-xs text-muted mt-1">{{ healthData.checks?.resources?.details?.disk_free_gb?.toFixed(1) || 0 }} GB free</p>
                </div>
                <!-- Memory -->
                <div>
                  <div class="flex justify-between items-center text-sm mb-1">
                    <span class="text-secondary">Memory</span>
                    <span class="font-medium text-primary">{{ healthData.checks?.resources?.details?.memory_percent || 0 }}%</span>
                  </div>
                  <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      :class="[
                        'h-full rounded-full transition-all',
                        (healthData.checks?.resources?.details?.memory_percent || 0) >= 90 ? 'bg-red-500' :
                        (healthData.checks?.resources?.details?.memory_percent || 0) >= 75 ? 'bg-amber-500' : 'bg-purple-500'
                      ]"
                      :style="{ width: `${healthData.checks?.resources?.details?.memory_percent || 0}%` }"
                    ></div>
                  </div>
                </div>
                <!-- CPU -->
                <div>
                  <div class="flex justify-between items-center text-sm mb-1">
                    <span class="text-secondary">CPU</span>
                    <span class="font-medium text-primary">{{ healthData.checks?.resources?.details?.cpu_percent?.toFixed(1) || 0 }}%</span>
                  </div>
                  <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      :class="[
                        'h-full rounded-full transition-all',
                        (healthData.checks?.resources?.details?.cpu_percent || 0) >= 90 ? 'bg-red-500' :
                        (healthData.checks?.resources?.details?.cpu_percent || 0) >= 75 ? 'bg-amber-500' : 'bg-blue-500'
                      ]"
                      :style="{ width: `${healthData.checks?.resources?.details?.cpu_percent || 0}%` }"
                    ></div>
                  </div>
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

          <!-- Docker Storage -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-orange-100 dark:bg-orange-500/20">
                  <ServerStackIcon class="h-5 w-5 text-orange-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">Docker Storage</h3>
                  <p class="text-xs text-muted">Images, volumes, containers</p>
                </div>
              </div>
              <div class="text-center py-4">
                <p class="text-4xl font-bold text-primary">
                  {{ healthData.docker_disk_usage_gb?.toFixed(1) || '0.0' }}
                  <span class="text-lg text-muted">GB</span>
                </p>
                <p class="text-xs text-muted mt-1">Total Docker disk usage</p>
              </div>
            </div>
          </Card>
        </div>
      </template>
    </template>

    <!-- Network Tab -->
    <template v-if="activeTab === 'network'">
      <HeartbeatLoader v-if="networkLoading" :text="networkLoadingMessages[networkLoadingMessageIndex] || 'Scanning network interfaces...'" color="purple" class="py-16 mt-8" />

      <template v-else>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- External Services -->
          <Card title="External Services">
            <div v-if="externalServices.length > 0" class="grid grid-cols-1 gap-3">
              <a
                v-for="service in externalServices"
                :key="service.name"
                :href="service.url"
                target="_blank"
                rel="noopener noreferrer"
                class="group block p-4 bg-surface rounded-lg border border-gray-400 dark:border-black hover:border-blue-500 hover:shadow-md transition-all"
              >
                <div class="flex items-center gap-3">
                  <div :class="['p-2 rounded-lg', service.color || 'bg-blue-100 dark:bg-blue-500/20']">
                    <LinkIcon :class="['h-5 w-5', service.iconColor || 'text-blue-500']" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <h4 class="font-semibold text-primary group-hover:text-blue-500 transition-colors">{{ service.name }}</h4>
                    <p class="text-xs text-muted">{{ service.description }}</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <span
                      :class="[
                        'w-2 h-2 rounded-full',
                        service.running ? 'bg-emerald-500' : 'bg-gray-400'
                      ]"
                    ></span>
                    <svg class="h-4 w-4 text-gray-400 group-hover:text-blue-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </div>
                </div>
              </a>
            </div>
            <div v-else class="text-center py-4 text-muted">
              No external services configured in nginx
            </div>
          </Card>

          <!-- Network Configuration (with hostname in header) -->
          <Card :padding="false">
            <template #header>
              <div class="flex items-center justify-between w-full px-4 py-3">
                <h3 class="font-semibold text-primary">Network Configuration</h3>
                <span class="px-3 py-1 bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 rounded-full text-sm font-mono">
                  {{ networkInfo.hostname || 'unknown' }}
                </span>
              </div>
            </template>
            <div class="p-4 space-y-4">
              <!-- Gateway & DNS -->
              <div class="space-y-2">
                <div class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Default Gateway</span>
                  <span class="font-medium text-primary font-mono">{{ networkInfo.gateway || 'N/A' }}</span>
                </div>
                <div class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">DNS Servers</span>
                  <div class="text-right">
                    <span
                      v-for="(dns, i) in networkInfo.dns_servers"
                      :key="i"
                      class="font-medium text-primary font-mono block"
                    >
                      {{ dns }}
                    </span>
                    <span v-if="!networkInfo.dns_servers?.length" class="text-muted">None</span>
                  </div>
                </div>
              </div>

              <!-- Network Interfaces -->
              <div class="space-y-3">
                <h4 class="text-sm font-medium text-secondary">Interfaces</h4>
                <div
                  v-for="iface in networkInfo.interfaces"
                  :key="iface.name"
                  class="p-3 rounded-lg bg-surface-hover"
                >
                  <div class="flex items-center gap-2 mb-2">
                    <WifiIcon class="h-4 w-4 text-blue-500" />
                    <span class="font-medium text-primary">{{ iface.name }}</span>
                  </div>
                  <div class="space-y-1 text-sm">
                    <div
                      v-for="addr in iface.addresses"
                      :key="addr.address"
                      class="flex justify-between"
                    >
                      <span class="text-secondary">{{ addr.type.toUpperCase() }}</span>
                      <span class="font-mono text-primary">{{ addr.address }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="!networkInfo.interfaces?.length" class="text-center py-4 text-muted">
                  No network interfaces found
                </div>
              </div>
            </div>
          </Card>
        </div>

        <!-- VPN & Tunnel Services -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <!-- Cloudflare Tunnel -->
          <Card :padding="false">
            <template #header>
              <div class="flex items-center justify-between w-full px-4 py-3">
                <div class="flex items-center gap-2">
                  <CloudIcon class="h-5 w-5 text-orange-500" />
                  <h3 class="font-semibold text-primary">Cloudflare Tunnel</h3>
                </div>
                <div class="flex items-center gap-2">
                  <button
                    @click="openCloudflareTokenModal"
                    :class="[
                      'px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm flex items-center gap-1.5',
                      cloudflareInfo.running
                        ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                        : 'bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500 text-gray-700 dark:text-gray-300'
                    ]"
                  >
                    <KeyIcon class="h-3.5 w-3.5" />
                    API Key
                  </button>
                  <button
                    v-if="cloudflareInfo.running"
                    @click="openRestartDialog('genmaster_cloudflared', 'Cloudflare Tunnel')"
                    class="btn-secondary flex items-center gap-1.5 text-xs py-1 px-2"
                    title="Restart Container"
                  >
                    <ArrowPathIcon class="h-3.5 w-3.5" />
                    Restart
                  </button>
                </div>
              </div>
            </template>
            <div class="p-4">
            <div v-if="cloudflareInfo.error && !cloudflareInfo.installed" class="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-500/10 rounded-lg">
              <CloudIcon class="h-6 w-6 text-gray-400" />
              <p class="text-muted">{{ cloudflareInfo.error }}</p>
            </div>
            <template v-else>
              <div class="space-y-3">
                <!-- Status -->
                <div class="flex items-center justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Status</span>
                  <span :class="[
                    'flex items-center gap-2 font-medium',
                    cloudflareInfo.running ? 'text-emerald-500' : 'text-red-500'
                  ]">
                    <span :class="['w-2 h-2 rounded-full', cloudflareInfo.running ? 'bg-emerald-500' : 'bg-red-500']"></span>
                    {{ cloudflareInfo.running ? 'Running' : 'Stopped' }}
                  </span>
                </div>
                <div v-if="cloudflareInfo.version" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Version</span>
                  <span class="font-medium text-primary">{{ cloudflareInfo.version }}</span>
                </div>
                <div v-if="cloudflareInfo.connected !== undefined" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Connected</span>
                  <span :class="cloudflareInfo.connected ? 'text-emerald-500' : 'text-amber-500'">
                    {{ cloudflareInfo.connected ? 'Yes' : 'No' }}
                  </span>
                </div>
                <div v-if="cloudflareInfo.edge_locations?.length" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Edge Locations</span>
                  <div class="flex flex-wrap gap-1 justify-end">
                    <span
                      v-for="loc in cloudflareInfo.edge_locations"
                      :key="loc"
                      class="px-2 py-0.5 text-xs rounded bg-orange-100 dark:bg-orange-500/20 text-orange-700 dark:text-orange-300 uppercase"
                    >
                      {{ loc }}
                    </span>
                  </div>
                </div>
                <div v-if="cloudflareInfo.tunnel_id" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Tunnel ID</span>
                  <span class="font-mono text-xs text-primary truncate max-w-[180px]" :title="cloudflareInfo.tunnel_id">
                    {{ cloudflareInfo.tunnel_id.slice(0, 8) }}...
                  </span>
                </div>

                <!-- Metrics Section -->
                <div v-if="cloudflareInfo.metrics && Object.keys(cloudflareInfo.metrics).length" class="pt-2">
                  <p class="text-xs text-muted uppercase tracking-wide mb-2">Traffic Metrics</p>
                  <div class="grid grid-cols-2 gap-3">
                    <div v-if="cloudflareInfo.metrics.total_requests !== undefined" class="bg-surface-hover rounded-lg p-3">
                      <p class="text-xs text-muted">Total Requests</p>
                      <p class="text-lg font-semibold text-primary">{{ cloudflareInfo.metrics.total_requests.toLocaleString() }}</p>
                    </div>
                    <div v-if="cloudflareInfo.metrics.ha_connections !== undefined" class="bg-surface-hover rounded-lg p-3">
                      <p class="text-xs text-muted">HA Connections</p>
                      <p class="text-lg font-semibold text-primary">{{ cloudflareInfo.metrics.ha_connections }}</p>
                    </div>
                  </div>
                </div>

                <!-- Error display -->
                <div v-if="cloudflareInfo.last_error" class="mt-3 p-3 bg-red-50 dark:bg-red-500/10 rounded-lg">
                  <p class="text-xs text-red-600 dark:text-red-400 font-mono break-all">{{ cloudflareInfo.last_error }}</p>
                </div>
              </div>
            </template>
            </div>
          </Card>

          <!-- Tailscale -->
          <Card :padding="false">
            <template #header>
              <div class="flex items-center justify-between w-full px-4 py-3">
                <div class="flex items-center gap-2">
                  <LinkIcon class="h-5 w-5 text-blue-500" />
                  <h3 class="font-semibold text-primary">Tailscale VPN</h3>
                </div>
                <div class="flex items-center gap-2">
                  <button
                    @click="openTailscaleKeyModal"
                    :class="[
                      'px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm flex items-center gap-1.5',
                      tailscaleInfo.running && tailscaleInfo.logged_in
                        ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                        : 'bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500 text-gray-700 dark:text-gray-300'
                    ]"
                  >
                    <KeyIcon class="h-3.5 w-3.5" />
                    API Key
                  </button>
                  <button
                    v-if="tailscaleInfo.running"
                    @click="openRestartDialog('genmaster_tailscale', 'Tailscale VPN')"
                    class="btn-secondary flex items-center gap-1.5 text-xs py-1 px-2"
                    title="Restart Container"
                  >
                    <ArrowPathIcon class="h-3.5 w-3.5" />
                    Restart
                  </button>
                </div>
              </div>
            </template>
            <div class="p-4">
            <div v-if="tailscaleInfo.error && !tailscaleInfo.installed" class="flex items-center gap-3 p-4 bg-gray-50 dark:bg-gray-500/10 rounded-lg">
              <LinkIcon class="h-6 w-6 text-gray-400" />
              <p class="text-muted">{{ tailscaleInfo.error }}</p>
            </div>
            <template v-else>
              <div class="space-y-3">
                <div class="flex items-center justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Status</span>
                  <span :class="[
                    'flex items-center gap-2 font-medium',
                    tailscaleInfo.running && tailscaleInfo.logged_in ? 'text-emerald-500' : 'text-red-500'
                  ]">
                    <span :class="['w-2 h-2 rounded-full', tailscaleInfo.running && tailscaleInfo.logged_in ? 'bg-emerald-500' : 'bg-red-500']"></span>
                    {{ tailscaleInfo.running && tailscaleInfo.logged_in ? 'Connected' : tailscaleInfo.running ? 'Not Logged In' : 'Stopped' }}
                  </span>
                </div>
                <div v-if="tailscaleInfo.tailscale_ip" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Tailscale IP</span>
                  <span class="font-medium text-primary font-mono">{{ tailscaleInfo.tailscale_ip }}</span>
                </div>
                <div v-if="tailscaleInfo.hostname" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Hostname</span>
                  <span class="font-medium text-primary">{{ tailscaleInfo.hostname }}</span>
                </div>
                <div v-if="tailscaleInfo.dns_name" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">DNS Name</span>
                  <span class="font-medium text-primary font-mono text-sm">{{ tailscaleInfo.dns_name }}</span>
                </div>
                <div v-if="tailscaleInfo.tailnet" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Tailnet</span>
                  <span class="font-medium text-primary">{{ tailscaleInfo.tailnet }}</span>
                </div>
                <!-- Devices with expandable list -->
                <div v-if="tailscaleInfo.peers?.length" class="py-2">
                  <button
                    @click="peersExpanded = !peersExpanded"
                    class="w-full flex items-center justify-between hover:bg-surface-hover rounded-lg p-1 -m-1 transition-colors"
                  >
                    <span class="text-secondary">Devices</span>
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-primary">
                        {{ tailscaleInfo.online_peers || 0 }} online / {{ tailscaleInfo.peer_count }} total
                      </span>
                      <ChevronDownIcon
                        :class="[
                          'h-4 w-4 text-secondary transition-transform duration-200',
                          peersExpanded ? 'rotate-180' : ''
                        ]"
                      />
                    </div>
                  </button>

                  <!-- Expandable Peer List -->
                  <div
                    v-show="peersExpanded"
                    class="mt-3 space-y-2 max-h-[250px] overflow-y-auto"
                  >
                    <div
                      v-for="peer in tailscaleInfo.peers"
                      :key="peer.id || peer.hostname"
                      :class="[
                        'flex items-center justify-between p-2 rounded-lg',
                        peer.is_self ? 'bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30' : 'bg-surface-hover'
                      ]"
                    >
                      <div class="flex items-center gap-2">
                        <span
                          :class="[
                            'w-2 h-2 rounded-full flex-shrink-0',
                            peer.online ? 'bg-emerald-500' : 'bg-gray-400'
                          ]"
                        ></span>
                        <div class="min-w-0">
                          <p class="font-medium text-primary text-sm truncate">
                            {{ peer.hostname }}
                            <span v-if="peer.is_self" class="text-xs text-blue-600 dark:text-blue-400 ml-1">(this device)</span>
                          </p>
                          <p class="text-xs text-muted font-mono truncate">{{ peer.ip }}</p>
                        </div>
                      </div>
                      <div class="text-right flex-shrink-0 ml-2">
                        <span
                          :class="[
                            'text-xs px-2 py-0.5 rounded',
                            peer.online
                              ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                              : 'bg-gray-100 dark:bg-gray-500/20 text-gray-600 dark:text-gray-400'
                          ]"
                        >
                          {{ peer.online ? 'online' : 'offline' }}
                        </span>
                        <p v-if="peer.os" class="text-xs text-muted mt-1">{{ peer.os }}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            </div>
          </Card>
        </div>
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
      <HeartbeatLoader v-if="slaveLoading" :text="slaveLoadingMessages[slaveLoadingMessageIndex]" color="blue" class="py-16 mt-8" />

      <template v-else>
        <!-- GenSlave Status Banner -->
        <div :class="['rounded-xl p-6 border-2 relative overflow-hidden', slaveInfo.online ? 'bg-gradient-to-r from-emerald-500/10 to-emerald-500/5 border-emerald-500/50' : 'bg-gradient-to-r from-red-500/10 to-red-500/5 border-red-500/50']">
          <div class="relative flex items-center justify-between flex-wrap gap-4">
            <div class="flex items-center gap-4">
              <div :class="['p-4 rounded-2xl', slaveInfo.online ? 'bg-emerald-500/20' : 'bg-red-500/20']">
                <ServerIcon :class="['h-10 w-10', slaveInfo.online ? 'text-emerald-500' : 'text-red-500']" />
              </div>
              <div>
                <h2 class="text-2xl font-bold text-primary">
                  GenSlave: <span :class="slaveInfo.online ? 'text-emerald-500' : 'text-red-500'">{{ slaveInfo.online ? 'ONLINE' : 'OFFLINE' }}</span>
                </h2>
                <p class="text-secondary mt-1">
                  {{ slaveSystemInfo?.hostname || 'genslave' }} • {{ slaveSystemInfo?.platform || 'Raspberry Pi' }}
                </p>
              </div>
            </div>

            <div class="flex items-center gap-3">
              <button
                @click="loadSlaveInfo"
                :disabled="slaveLoading"
                class="btn-secondary flex items-center gap-2"
              >
                <ArrowPathIcon :class="['h-4 w-4', slaveLoading ? 'animate-spin' : '']" />
                Refresh
              </button>
              <button
                @click="testSlaveConnection"
                :disabled="testingConnection"
                class="btn-secondary flex items-center gap-2"
              >
                <BoltIcon :class="['h-4 w-4', testingConnection ? 'animate-pulse' : '']" />
                Test
              </button>
            </div>
          </div>
        </div>

        <!-- ARM/DISARM Banner -->
        <div
          :class="[
            'rounded-xl p-4 border-2 relative overflow-hidden transition-all mt-4',
            relayArmed
              ? 'bg-gradient-to-r from-red-500/20 to-red-500/10 border-red-500'
              : 'bg-gradient-to-r from-gray-500/20 to-gray-500/10 border-gray-400 dark:border-gray-600'
          ]"
        >
          <div class="flex items-center justify-between flex-wrap gap-4">
            <div class="flex items-center gap-4">
              <div
                :class="[
                  'p-3 rounded-xl',
                  relayArmed ? 'bg-red-500/30' : 'bg-gray-500/30'
                ]"
              >
                <ShieldExclamationIcon
                  :class="[
                    'h-8 w-8',
                    relayArmed ? 'text-red-500' : 'text-gray-500'
                  ]"
                />
              </div>
              <div>
                <h3 class="text-lg font-bold text-primary">
                  Relay Status:
                  <span :class="relayArmed ? 'text-red-500' : 'text-gray-500'">
                    {{ relayArmed ? 'ARMED' : 'DISARMED' }}
                  </span>
                </h3>
                <p class="text-sm text-secondary">
                  {{ relayArmed ? 'Generator can be started via relay control' : 'Relay is disabled - generator cannot be started remotely' }}
                </p>
              </div>
            </div>
            <div class="flex items-center gap-4">
              <button
                @click="toggleRelayArm"
                :disabled="armingRelay || !slaveInfo.online"
                :class="[
                  'relative inline-flex h-8 w-16 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                  relayArmed
                    ? 'bg-red-500 focus:ring-red-500'
                    : 'bg-gray-400 focus:ring-gray-500',
                  (armingRelay || !slaveInfo.online) ? 'opacity-50 cursor-not-allowed' : ''
                ]"
              >
                <span
                  :class="[
                    'inline-block h-6 w-6 transform rounded-full bg-white shadow-lg transition-transform',
                    relayArmed ? 'translate-x-9' : 'translate-x-1'
                  ]"
                />
              </button>
              <span
                :class="[
                  'px-3 py-1 rounded-full text-sm font-bold',
                  relayArmed
                    ? 'bg-red-500 text-white'
                    : 'bg-gray-400 text-white'
                ]"
              >
                {{ relayArmed ? 'ARMED' : 'SAFE' }}
              </span>
            </div>
          </div>
        </div>

        <!-- System Resources Grid -->
        <div v-if="slaveSystemInfo" class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <!-- CPU -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-20 h-20" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="10" fill="transparent" r="40" cx="50" cy="50" />
                  <circle
                    :class="[
                      (slaveSystemInfo.cpu_percent || 0) >= 90 ? 'text-red-500' :
                      (slaveSystemInfo.cpu_percent || 0) >= 75 ? 'text-amber-500' : 'text-blue-500'
                    ]"
                    stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                    :stroke-dasharray="`${(slaveSystemInfo.cpu_percent || 0) * 2.51} 251`" transform="rotate(-90 50 50)"
                  />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.cpu_percent || 0) }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">CPU</p>
            </div>
          </Card>

          <!-- Memory -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-20 h-20" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="10" fill="transparent" r="40" cx="50" cy="50" />
                  <circle
                    :class="[
                      (slaveSystemInfo.ram_percent || 0) >= 90 ? 'text-red-500' :
                      (slaveSystemInfo.ram_percent || 0) >= 75 ? 'text-amber-500' : 'text-purple-500'
                    ]"
                    stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                    :stroke-dasharray="`${(slaveSystemInfo.ram_percent || 0) * 2.51} 251`" transform="rotate(-90 50 50)"
                  />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.ram_percent || 0) }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Memory</p>
              <p class="text-xs text-muted">{{ slaveSystemInfo.ram_used_mb || 0 }}MB / {{ slaveSystemInfo.ram_total_mb || 0 }}MB</p>
            </div>
          </Card>

          <!-- Disk -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-20 h-20" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="10" fill="transparent" r="40" cx="50" cy="50" />
                  <circle
                    :class="[
                      (slaveSystemInfo.disk_percent || 0) >= 90 ? 'text-red-500' :
                      (slaveSystemInfo.disk_percent || 0) >= 75 ? 'text-amber-500' : 'text-emerald-500'
                    ]"
                    stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                    :stroke-dasharray="`${(slaveSystemInfo.disk_percent || 0) * 2.51} 251`" transform="rotate(-90 50 50)"
                  />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.disk_percent || 0) }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Disk</p>
              <p class="text-xs text-muted">{{ ((slaveSystemInfo.disk_total_gb || 0) - (slaveSystemInfo.disk_used_gb || 0)).toFixed(1) }}GB free</p>
            </div>
          </Card>

          <!-- Temperature -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-20 h-20" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="10" fill="transparent" r="40" cx="50" cy="50" />
                  <circle
                    :class="[
                      (slaveSystemInfo.temperature_celsius || 0) >= 80 ? 'text-red-500' :
                      (slaveSystemInfo.temperature_celsius || 0) >= 60 ? 'text-amber-500' : 'text-cyan-500'
                    ]"
                    stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                    :stroke-dasharray="`${Math.min((slaveSystemInfo.temperature_celsius || 0), 100) * 2.51} 251`" transform="rotate(-90 50 50)"
                  />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.temperature_celsius || 0) }}°</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Temp</p>
              <p class="text-xs text-muted">{{ (slaveSystemInfo.temperature_celsius || 0) >= 60 ? 'Warm' : 'Normal' }}</p>
            </div>
          </Card>
        </div>

        <!-- Detail Cards Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
          <!-- System Info Card -->
          <Card title="System Information">
            <div v-if="slaveSystemInfo" class="space-y-3">
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Hostname</span>
                <span class="font-medium text-primary">{{ slaveSystemInfo.hostname || 'Unknown' }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Platform</span>
                <span class="font-medium text-primary">{{ slaveSystemInfo.platform || 'Unknown' }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">IP Address</span>
                <span class="font-medium text-primary font-mono">{{ slaveSystemInfo.ip_address || 'Unknown' }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Uptime</span>
                <span class="font-medium text-primary">{{ formatSeconds(slaveSystemInfo.uptime_seconds) }}</span>
              </div>
              <div v-if="slaveHealthStatus?.version" class="flex justify-between py-2">
                <span class="text-secondary">Version</span>
                <span class="font-medium text-primary">{{ slaveHealthStatus.version }}</span>
              </div>
            </div>
            <div v-else class="text-center py-4 text-muted">
              System information not available
            </div>
          </Card>

          <!-- Relay & Health Card -->
          <Card title="Relay & Health Status">
            <div class="space-y-3">
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Relay State</span>
                <span :class="['font-medium', slaveRelayState?.relay_on ? 'text-emerald-500' : 'text-gray-500']">
                  {{ slaveRelayState?.relay_on ? 'ON' : 'OFF' }}
                </span>
              </div>
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Armed</span>
                <span :class="['font-medium', relayArmed ? 'text-red-500' : 'text-emerald-500']">
                  {{ relayArmed ? 'Yes' : 'No' }}
                </span>
              </div>
              <div v-if="slaveRelayState?.armed_at" class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Armed At</span>
                <span class="font-medium text-primary text-sm">{{ new Date(slaveRelayState.armed_at * 1000).toLocaleString() }}</span>
              </div>
              <div v-if="slaveRelayState?.change_count !== undefined" class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">State Changes</span>
                <span class="font-medium text-primary">{{ slaveRelayState.change_count }}</span>
              </div>
              <div class="flex justify-between py-2">
                <span class="text-secondary">Mock Mode</span>
                <span :class="['font-medium', slaveHealthStatus?.mock_mode ? 'text-amber-500' : 'text-emerald-500']">
                  {{ slaveHealthStatus?.mock_mode ? 'Enabled' : 'Disabled' }}
                </span>
              </div>
            </div>
          </Card>

          <!-- Failsafe Monitoring Card -->
          <Card title="Failsafe Monitoring">
            <div v-if="slaveFailsafeStatus" class="space-y-3">
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Failsafe Running</span>
                <span :class="['font-medium', slaveFailsafeStatus.running ? 'text-emerald-500' : 'text-red-500']">
                  {{ slaveFailsafeStatus.running ? 'Yes' : 'No' }}
                </span>
              </div>
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Last Heartbeat</span>
                <span class="font-medium text-primary text-sm">
                  {{ slaveFailsafeStatus.last_heartbeat ? new Date(slaveFailsafeStatus.last_heartbeat * 1000).toLocaleTimeString() : 'Never' }}
                </span>
              </div>
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Since Heartbeat</span>
                <span :class="['font-medium', (slaveFailsafeStatus.seconds_since_heartbeat || 0) > 60 ? 'text-amber-500' : 'text-primary']">
                  {{ formatSeconds(slaveFailsafeStatus.seconds_since_heartbeat) }}
                </span>
              </div>
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Heartbeat Count</span>
                <span class="font-medium text-primary">{{ slaveFailsafeStatus.heartbeat_count || 0 }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
                <span class="text-secondary">Timeout</span>
                <span class="font-medium text-primary">{{ slaveFailsafeStatus.timeout_seconds || 60 }}s</span>
              </div>
              <div class="flex justify-between py-2">
                <span class="text-secondary">Failsafe Triggered</span>
                <span :class="['font-medium', slaveFailsafeStatus.failsafe_triggered ? 'text-red-500' : 'text-emerald-500']">
                  {{ slaveFailsafeStatus.failsafe_triggered ? 'Yes' : 'No' }}
                </span>
              </div>
            </div>
            <div v-else class="text-center py-4 text-muted">
              Failsafe status not available
            </div>
          </Card>

          <!-- Network & WiFi Card -->
          <Card title="Network & WiFi">
            <div v-if="slaveSystemInfo?.network_interfaces?.length" class="space-y-4">
              <div
                v-for="iface in slaveSystemInfo.network_interfaces"
                :key="iface.interface"
                class="p-3 rounded-lg bg-surface-hover"
              >
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-2">
                    <WifiIcon v-if="iface.is_wifi" class="h-4 w-4 text-blue-500" />
                    <GlobeAltIcon v-else class="h-4 w-4 text-emerald-500" />
                    <span class="font-medium text-primary">{{ iface.interface }}</span>
                  </div>
                  <span v-if="iface.ip_address" class="font-mono text-sm text-secondary">{{ iface.ip_address }}</span>
                </div>
                <!-- WiFi Signal if available -->
                <div v-if="iface.is_wifi && iface.wifi_ssid" class="mt-2">
                  <div class="flex justify-between items-center text-sm mb-1">
                    <span class="text-muted">WiFi Signal</span>
                    <span class="font-medium text-primary">{{ iface.wifi_ssid }}</span>
                  </div>
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        :class="[
                          'h-full rounded-full transition-all',
                          (iface.wifi_signal_percent || 0) >= 75 ? 'bg-emerald-500' :
                          (iface.wifi_signal_percent || 0) >= 50 ? 'bg-amber-500' : 'bg-red-500'
                        ]"
                        :style="{ width: `${iface.wifi_signal_percent || 0}%` }"
                      ></div>
                    </div>
                    <span class="text-xs text-muted w-12 text-right">{{ iface.wifi_signal_percent || 0 }}%</span>
                  </div>
                  <div v-if="iface.wifi_signal_dbm" class="text-xs text-muted mt-1">
                    {{ iface.wifi_signal_dbm }} dBm
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-4 text-muted">
              Network information not available
            </div>
          </Card>
        </div>

        <!-- Connection Settings Card -->
        <Card title="Connection Settings" subtitle="Configure GenSlave communication" class="mt-6">
          <div class="space-y-4">
            <div class="flex gap-3 items-end flex-wrap">
              <div class="flex-1 min-w-[250px]">
                <label class="block text-sm font-medium text-secondary mb-1">GenSlave URL</label>
                <input
                  v-model="slaveConfig.slave_api_url"
                  type="text"
                  placeholder="http://genslave.local:8001"
                  class="input"
                />
              </div>
              <button
                @click="testSlaveConnection"
                :disabled="testingConnection"
                class="btn-secondary flex items-center gap-2"
              >
                <BoltIcon v-if="!testingConnection" class="h-4 w-4" />
                <ArrowPathIcon v-else class="h-4 w-4 animate-spin" />
                Test
              </button>
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Heartbeat Interval (seconds)</label>
              <input
                v-model.number="slaveConfig.heartbeat_interval_seconds"
                type="number"
                min="5"
                max="60"
                class="input w-48"
              />
              <p class="text-xs text-muted mt-1">How often GenMaster sends heartbeat to GenSlave</p>
            </div>
          </div>
          <div class="flex justify-end mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button @click="saveSlaveConfig" :disabled="savingSlaveConfig" class="btn-primary flex items-center gap-2">
              <ArrowPathIcon v-if="savingSlaveConfig" class="h-4 w-4 animate-spin" />
              <CheckCircleIcon v-else class="h-4 w-4" />
              Save Settings
            </button>
          </div>
        </Card>

        <!-- Warnings if any -->
        <div v-if="slaveSystemInfo?.warnings?.length" class="mt-6">
          <Card title="Warnings" :padding="false">
            <div class="divide-y divide-gray-200 dark:divide-gray-700">
              <div
                v-for="(warning, index) in slaveSystemInfo.warnings"
                :key="index"
                class="p-4 flex items-start gap-3"
              >
                <ExclamationTriangleIcon class="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <p class="text-sm text-amber-700 dark:text-amber-400">{{ warning }}</p>
              </div>
            </div>
          </Card>
        </div>

        <!-- No data state -->
        <Card v-if="!slaveSystemInfo && !slaveInfo.online" class="mt-6">
          <div class="text-center py-8 text-muted">
            <ServerIcon class="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>GenSlave is offline or unreachable</p>
            <p class="text-sm mt-1">Check the connection settings and ensure GenSlave is running</p>
            <button
              @click="testSlaveConnection"
              :disabled="testingConnection"
              class="mt-4 btn-primary"
            >
              <BoltIcon class="h-4 w-4 mr-2" />
              Test Connection
            </button>
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
