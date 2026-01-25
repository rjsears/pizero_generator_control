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
import DnaHelixLoader from '../components/common/DnaHelixLoader.vue'
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
  CloudIcon,
  KeyIcon,
  LinkIcon,
  ChevronDownIcon,
  Cog6ToothIcon,
  FireIcon,
  PowerIcon,
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
const cloudflareInfo = ref({
  installed: false,
  running: false,
  connected: false,
  version: null,
  tunnel_id: null,
  connector_id: null,
  edge_locations: [],
  connections_per_location: {},
  metrics: {},
  last_error: null,
})
const tailscaleInfo = ref({ installed: false, running: false, logged_in: false, tailscale_ip: null })
const hostWifiInfo = ref({ available: false, connected: false, interface: null, ssid: null, signal_dbm: null, signal_percent: null, ip_address: null })
const peersExpanded = ref(false)

// WiFi configuration modal state
const showWifiConfigModal = ref(false)
const wifiNetworks = ref([])
const wifiScanning = ref(false)
const wifiConnecting = ref(false)
const selectedWifiNetwork = ref(null)
const wifiPassword = ref('')
const wifiError = ref(null)

// Add known network state
const showAddNetworkModal = ref(false)
const addNetworkSsid = ref('')
const addNetworkPassword = ref('')
const addNetworkAutoConnect = ref(true)
const addingNetwork = ref(false)
const addNetworkError = ref(null)

// Saved networks state
const savedNetworks = ref([])
const loadingSavedNetworks = ref(false)
const deletingNetwork = ref(null)

// SSL state
const sslInfo = ref({ configured: false, certificates: [] })
const sslLoading = ref(false)

// Reboot dialog (legacy - kept for compatibility)
const rebootDialog = ref({ open: false, loading: false })

// SSL Renew dialog
const sslRenewDialog = ref({ open: false, loading: false })

// Host power control
const showHostShutdownConfirm = ref(false)
const showHostRebootConfirm = ref(false)
const hostShuttingDown = ref(false)
const hostRebooting = ref(false)

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
    const [networkRes, cloudflareRes, tailscaleRes, servicesRes, hostWifiRes] = await Promise.all([
      systemApi.getNetwork(),
      systemApi.getCloudflare().catch(() => ({ data: {} })),
      systemApi.getTailscale().catch(() => ({ data: {} })),
      systemApi.getExternalServices().catch(() => ({ data: [] })),
      systemApi.hostWifi().catch(() => ({ data: {} })),
    ])
    networkInfo.value = networkRes.data || { hostname: '', interfaces: [], gateway: null, dns_servers: [] }
    // Merge with defaults to ensure all properties exist
    cloudflareInfo.value = {
      installed: false,
      running: false,
      connected: false,
      version: null,
      tunnel_id: null,
      connector_id: null,
      edge_locations: [],
      connections_per_location: {},
      metrics: {},
      last_error: null,
      ...(cloudflareRes.data || {})
    }
    tailscaleInfo.value = {
      installed: false,
      running: false,
      logged_in: false,
      tailscale_ip: null,
      ...(tailscaleRes.data || {})
    }
    hostWifiInfo.value = {
      available: false,
      connected: false,
      interface: null,
      ssid: null,
      signal_dbm: null,
      signal_percent: null,
      ip_address: null,
      ...(hostWifiRes.data || {})
    }
    // Filter out services without valid URLs to prevent href errors
    externalServices.value = (servicesRes.data || []).filter(s => s && s.url)
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

// =========================================================================
// Host Power Control
// =========================================================================

function handleHostShutdown() {
  showHostShutdownConfirm.value = true
}

async function executeHostShutdown() {
  showHostShutdownConfirm.value = false
  hostShuttingDown.value = true
  try {
    await systemApi.hostShutdown()
    notificationStore.success('GenMaster host shutdown initiated. System will power off shortly.')
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to initiate host shutdown'
    notificationStore.error(message)
  } finally {
    hostShuttingDown.value = false
  }
}

function handleHostReboot() {
  showHostRebootConfirm.value = true
}

async function executeHostReboot() {
  showHostRebootConfirm.value = false
  hostRebooting.value = true
  try {
    await systemApi.hostReboot()
    notificationStore.success('GenMaster host reboot initiated. System will restart in ~60-90 seconds.')
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to initiate host reboot'
    notificationStore.error(message)
  } finally {
    hostRebooting.value = false
  }
}

// =========================================================================
// WiFi Configuration
// =========================================================================

async function openWifiConfigModal() {
  showWifiConfigModal.value = true
  wifiError.value = null
  wifiPassword.value = ''
  selectedWifiNetwork.value = null
  await scanWifiNetworks()
}

function closeWifiConfigModal() {
  showWifiConfigModal.value = false
  wifiNetworks.value = []
  wifiPassword.value = ''
  selectedWifiNetwork.value = null
  wifiError.value = null
}

async function scanWifiNetworks() {
  wifiScanning.value = true
  wifiError.value = null
  try {
    const response = await systemApi.scanWifiNetworks()
    if (response.data?.success) {
      wifiNetworks.value = response.data.networks || []
    } else {
      wifiError.value = response.data?.error || 'Failed to scan networks'
    }
  } catch (error) {
    wifiError.value = error.response?.data?.detail || 'Failed to scan WiFi networks'
  } finally {
    wifiScanning.value = false
  }
}

function selectWifiNetwork(network) {
  selectedWifiNetwork.value = network
  wifiPassword.value = ''
  wifiError.value = null
}

async function connectToWifi() {
  if (!selectedWifiNetwork.value) {
    wifiError.value = 'Please select a network'
    return
  }

  wifiConnecting.value = true
  wifiError.value = null

  try {
    const response = await systemApi.connectWifi({
      ssid: selectedWifiNetwork.value.ssid,
      password: wifiPassword.value || null,
    })

    if (response.data?.success) {
      notificationStore.success(response.data.message || `Connected to ${selectedWifiNetwork.value.ssid}`)
      closeWifiConfigModal()
      // Refresh network info after a short delay
      setTimeout(() => {
        loadNetworkInfo()
      }, 2000)
    } else {
      wifiError.value = response.data?.error || 'Failed to connect'
    }
  } catch (error) {
    wifiError.value = error.response?.data?.detail || 'Failed to connect to WiFi'
  } finally {
    wifiConnecting.value = false
  }
}

// =========================================================================
// Add Known WiFi Network Functions
// =========================================================================

async function openAddNetworkModal() {
  showAddNetworkModal.value = true
  addNetworkSsid.value = ''
  addNetworkPassword.value = ''
  addNetworkAutoConnect.value = true
  addNetworkError.value = null
  await loadSavedNetworks()
}

function closeAddNetworkModal() {
  showAddNetworkModal.value = false
  addNetworkSsid.value = ''
  addNetworkPassword.value = ''
  addNetworkAutoConnect.value = true
  addNetworkError.value = null
}

async function loadSavedNetworks() {
  loadingSavedNetworks.value = true
  try {
    const response = await systemApi.listSavedWifiNetworks()
    if (response.data?.success) {
      savedNetworks.value = response.data.networks || []
    } else {
      console.error('Failed to load saved networks:', response.data?.error)
    }
  } catch (error) {
    console.error('Failed to load saved networks:', error)
  } finally {
    loadingSavedNetworks.value = false
  }
}

async function addKnownNetwork() {
  if (!addNetworkSsid.value.trim()) {
    addNetworkError.value = 'Please enter an SSID'
    return
  }
  if (!addNetworkPassword.value) {
    addNetworkError.value = 'Please enter a password'
    return
  }

  addingNetwork.value = true
  addNetworkError.value = null

  try {
    const response = await systemApi.addWifiNetwork({
      ssid: addNetworkSsid.value.trim(),
      password: addNetworkPassword.value,
      auto_connect: addNetworkAutoConnect.value,
    })

    if (response.data?.success) {
      notificationStore.success(response.data.message || `Added network "${addNetworkSsid.value}"`)
      addNetworkSsid.value = ''
      addNetworkPassword.value = ''
      await loadSavedNetworks()
    } else {
      addNetworkError.value = response.data?.error || 'Failed to add network'
    }
  } catch (error) {
    addNetworkError.value = error.response?.data?.detail || 'Failed to add network'
  } finally {
    addingNetwork.value = false
  }
}

async function deleteSavedNetwork(networkName) {
  if (!confirm(`Delete saved network "${networkName}"?`)) {
    return
  }

  deletingNetwork.value = networkName
  try {
    const response = await systemApi.deleteWifiNetwork({ name: networkName })
    if (response.data?.success) {
      notificationStore.success(response.data.message || `Deleted network "${networkName}"`)
      await loadSavedNetworks()
    } else {
      notificationStore.error(response.data?.error || 'Failed to delete network')
    }
  } catch (error) {
    notificationStore.error(error.response?.data?.detail || 'Failed to delete network')
  } finally {
    deletingNetwork.value = null
  }
}

// Watch for tab changes
watch(activeTab, (newTab) => {
  if (newTab === 'network' && networkInfo.value.interfaces.length === 0) {
    loadNetworkInfo()
    loadSslInfo()
  }
})

// Check for query param and load appropriate data
onMounted(async () => {
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
  await loadHealthData()

  // Load tab-specific data based on initial tab
  if (activeTab.value === 'network') {
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
        <p class="text-secondary mt-1">Server health, network, and system status</p>
      </div>
    </div>

    <!-- Tabs with Host Power Controls -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-400 dark:border-gray-700 p-1.5 flex items-center justify-between gap-1.5 relative z-10">
      <!-- Tab buttons -->
      <div class="flex gap-1.5 overflow-x-auto">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap border',
            activeTab === tab.id
              ? `${tab.bgActive} ${tab.textActive} ${tab.borderActive}`
              : 'text-gray-500 dark:text-gray-400 hover:bg-emerald-100 hover:text-emerald-700 dark:hover:bg-emerald-500/20 dark:hover:text-emerald-400 hover:border-emerald-300 dark:hover:border-emerald-500/30 border-transparent'
          ]"
        >
          <component :is="tab.icon" :class="['h-4 w-4', activeTab === tab.id ? '' : tab.iconColor]" />
          {{ tab.name }}
        </button>
      </div>

      <!-- Host Power Controls -->
      <div class="flex gap-1.5 flex-shrink-0">
        <button
          @click="handleHostReboot"
          :disabled="hostRebooting"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-500/10 border border-transparent"
          title="Reboot GenMaster host"
        >
          <ArrowPathIcon :class="['h-4 w-4', hostRebooting ? 'animate-spin' : '']" />
          <span class="hidden sm:inline">Reboot</span>
        </button>
        <button
          @click="handleHostShutdown"
          :disabled="hostShuttingDown"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 border border-transparent"
          title="Shutdown GenMaster host"
        >
          <PowerIcon :class="['h-4 w-4', hostShuttingDown ? 'animate-pulse' : '']" />
          <span class="hidden sm:inline">Shutdown</span>
        </button>
      </div>
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
      <DnaHelixLoader v-if="networkLoading" :text="networkLoadingMessages[networkLoadingMessageIndex] || 'Scanning network interfaces...'" class="py-16 mt-8" />

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

        <!-- Host WiFi Info (if available) -->
        <div v-if="hostWifiInfo.available" class="mt-6">
          <Card :padding="false">
            <template #header>
              <div class="flex items-center justify-between w-full px-4 py-3">
                <div class="flex items-center gap-2">
                  <WifiIcon class="h-5 w-5 text-cyan-500" />
                  <h3 class="font-semibold text-primary">Host WiFi</h3>
                </div>
                <div class="flex items-center gap-2">
                  <button
                    @click="openAddNetworkModal"
                    class="px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm flex items-center gap-1.5 bg-purple-500 hover:bg-purple-600 text-white"
                  >
                    <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                    </svg>
                    Add Network
                  </button>
                  <button
                    @click="openWifiConfigModal"
                    class="px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm flex items-center gap-1.5 bg-cyan-500 hover:bg-cyan-600 text-white"
                  >
                    <SignalIcon class="h-3.5 w-3.5" />
                    Scan &amp; Connect
                  </button>
                  <span
                    :class="[
                      'px-2 py-1 rounded-full text-xs font-medium',
                      hostWifiInfo.connected
                        ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                        : 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'
                    ]"
                  >
                    {{ hostWifiInfo.connected ? 'Connected' : 'Not Connected' }}
                  </span>
                </div>
              </div>
            </template>
            <div class="p-4">
              <div class="space-y-3">
                <div v-if="hostWifiInfo.interface" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Interface</span>
                  <span class="font-medium text-primary font-mono">{{ hostWifiInfo.interface }}</span>
                </div>
                <div v-if="hostWifiInfo.ssid" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">SSID</span>
                  <span class="font-medium text-primary">{{ hostWifiInfo.ssid }}</span>
                </div>
                <div v-if="hostWifiInfo.ip_address" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">IP Address</span>
                  <span class="font-medium text-primary font-mono">{{ hostWifiInfo.ip_address }}</span>
                </div>
                <div v-if="hostWifiInfo.signal_percent !== null" class="py-2">
                  <div class="flex justify-between mb-2">
                    <span class="text-secondary">Signal Strength</span>
                    <span class="font-medium text-primary">{{ hostWifiInfo.signal_percent }}% ({{ hostWifiInfo.signal_dbm }} dBm)</span>
                  </div>
                  <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      class="h-2 rounded-full transition-all duration-300"
                      :class="[
                        hostWifiInfo.signal_percent >= 70 ? 'bg-emerald-500' :
                        hostWifiInfo.signal_percent >= 40 ? 'bg-amber-500' : 'bg-red-500'
                      ]"
                      :style="{ width: `${hostWifiInfo.signal_percent}%` }"
                    ></div>
                  </div>
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
                <div v-if="cloudflareInfo.connector_id" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Connector ID</span>
                  <span class="font-mono text-xs text-primary truncate max-w-[180px]" :title="cloudflareInfo.connector_id">
                    {{ cloudflareInfo.connector_id.slice(0, 8) }}...
                  </span>
                </div>
                <div v-if="cloudflareInfo.connections_per_location && Object.keys(cloudflareInfo.connections_per_location).length" class="flex justify-between py-2 border-b border-gray-400 dark:border-black">
                  <span class="text-secondary">Connections</span>
                  <div class="flex flex-wrap gap-1 justify-end">
                    <span
                      v-for="(count, loc) in cloudflareInfo.connections_per_location"
                      :key="loc"
                      class="px-2 py-0.5 text-xs rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 uppercase"
                    >
                      {{ loc }}: {{ count }}
                    </span>
                  </div>
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
                    <div v-if="cloudflareInfo.metrics.active_streams !== undefined" class="bg-surface-hover rounded-lg p-3">
                      <p class="text-xs text-muted">Active Streams</p>
                      <p class="text-lg font-semibold text-primary">{{ cloudflareInfo.metrics.active_streams }}</p>
                    </div>
                    <div v-if="cloudflareInfo.metrics.request_errors !== undefined" class="bg-surface-hover rounded-lg p-3">
                      <p class="text-xs text-muted">Errors</p>
                      <p :class="['text-lg font-semibold', cloudflareInfo.metrics.request_errors > 0 ? 'text-red-500' : 'text-primary']">
                        {{ cloudflareInfo.metrics.request_errors }}
                      </p>
                    </div>
                  </div>

                  <!-- Response Codes -->
                  <div v-if="cloudflareInfo.metrics.response_codes" class="mt-3">
                    <p class="text-xs text-muted mb-2">Response Codes</p>
                    <div class="flex flex-wrap gap-2">
                      <span
                        v-for="(count, code) in cloudflareInfo.metrics.response_codes"
                        :key="code"
                        :class="[
                          'px-2 py-1 text-xs rounded font-mono',
                          code.startsWith('2') ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300' :
                          code.startsWith('3') ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300' :
                          code.startsWith('4') ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300' :
                          'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300'
                        ]"
                      >
                        {{ code }}: {{ count }}
                      </span>
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

    <!-- Host Shutdown Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showHostShutdownConfirm" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
          <div class="flex items-center gap-4 mb-4">
            <div class="p-3 rounded-full bg-red-100 dark:bg-red-500/20">
              <ExclamationTriangleIcon class="h-8 w-8 text-red-500" />
            </div>
            <h3 class="text-xl font-bold text-primary">Shutdown GenMaster Host</h3>
          </div>
          <div class="space-y-3 mb-6">
            <p class="text-secondary">
              Are you sure you want to <strong>shut down</strong> the GenMaster host?
            </p>
            <div class="p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30">
              <p class="text-sm text-red-700 dark:text-red-300 font-medium">
                ⚠️ Warning: This will make GenMaster completely unreachable!
              </p>
              <ul class="text-sm text-red-600 dark:text-red-400 mt-2 list-disc list-inside">
                <li>All containers (including web interface) will stop</li>
                <li>Generator monitoring will be unavailable</li>
                <li>You will need physical access to power it back on</li>
              </ul>
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button
              @click="showHostShutdownConfirm = false"
              class="btn-secondary"
            >
              Cancel
            </button>
            <button
              @click="executeHostShutdown"
              :disabled="hostShuttingDown"
              class="px-4 py-2 rounded-lg font-medium text-white bg-red-500 hover:bg-red-600 transition-colors disabled:opacity-50"
            >
              <span v-if="hostShuttingDown">Shutting down...</span>
              <span v-else>Shutdown Now</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Host Reboot Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showHostRebootConfirm" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
          <div class="flex items-center gap-4 mb-4">
            <div class="p-3 rounded-full bg-amber-100 dark:bg-amber-500/20">
              <ArrowPathIcon class="h-8 w-8 text-amber-500" />
            </div>
            <h3 class="text-xl font-bold text-primary">Reboot GenMaster Host</h3>
          </div>
          <div class="space-y-3 mb-6">
            <p class="text-secondary">
              Are you sure you want to <strong>reboot</strong> the GenMaster host?
            </p>
            <div class="p-3 rounded-lg bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30">
              <p class="text-sm text-amber-700 dark:text-amber-300 font-medium">
                ℹ️ GenMaster will be temporarily unavailable
              </p>
              <ul class="text-sm text-amber-600 dark:text-amber-400 mt-2 list-disc list-inside">
                <li>All containers will restart automatically</li>
                <li>System will be back online in ~60-90 seconds</li>
                <li>Generator state will be preserved</li>
              </ul>
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button
              @click="showHostRebootConfirm = false"
              class="btn-secondary"
            >
              Cancel
            </button>
            <button
              @click="executeHostReboot"
              :disabled="hostRebooting"
              class="px-4 py-2 rounded-lg font-medium text-white bg-amber-500 hover:bg-amber-600 transition-colors disabled:opacity-50"
            >
              <span v-if="hostRebooting">Rebooting...</span>
              <span v-else>Reboot Now</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- WiFi Configuration Modal -->
    <Teleport to="body">
      <div v-if="showWifiConfigModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="p-3 rounded-full bg-cyan-100 dark:bg-cyan-500/20">
                <WifiIcon class="h-6 w-6 text-cyan-500" />
              </div>
              <h3 class="text-xl font-bold text-primary">Configure WiFi</h3>
            </div>
            <button
              @click="closeWifiConfigModal"
              class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <XCircleIcon class="h-5 w-5 text-gray-500" />
            </button>
          </div>

          <!-- Error display -->
          <div v-if="wifiError" class="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30">
            <p class="text-sm text-red-700 dark:text-red-300">{{ wifiError }}</p>
          </div>

          <!-- Network List -->
          <div class="mb-4">
            <div class="flex items-center justify-between mb-2">
              <label class="text-sm font-medium text-secondary">Available Networks</label>
              <button
                @click="scanWifiNetworks"
                :disabled="wifiScanning"
                class="btn-secondary text-xs flex items-center gap-1"
              >
                <ArrowPathIcon :class="['h-3.5 w-3.5', wifiScanning ? 'animate-spin' : '']" />
                Refresh
              </button>
            </div>

            <div v-if="wifiScanning" class="py-8 text-center">
              <ArrowPathIcon class="h-8 w-8 animate-spin mx-auto text-cyan-500" />
              <p class="text-sm text-muted mt-2">Scanning for networks...</p>
            </div>

            <div v-else-if="wifiNetworks.length === 0" class="py-8 text-center text-muted">
              <WifiIcon class="h-8 w-8 mx-auto opacity-50 mb-2" />
              <p class="text-sm">No networks found</p>
            </div>

            <div v-else class="max-h-64 overflow-y-auto space-y-1 border border-gray-200 dark:border-gray-700 rounded-lg">
              <button
                v-for="network in wifiNetworks"
                :key="network.ssid"
                @click="selectWifiNetwork(network)"
                :class="[
                  'w-full p-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors',
                  selectedWifiNetwork?.ssid === network.ssid ? 'bg-cyan-50 dark:bg-cyan-500/10 border-l-4 border-cyan-500' : ''
                ]"
              >
                <div class="flex items-center gap-3">
                  <WifiIcon :class="[
                    'h-5 w-5',
                    network.signal_percent >= 70 ? 'text-emerald-500' :
                    network.signal_percent >= 40 ? 'text-amber-500' : 'text-red-500'
                  ]" />
                  <div class="text-left">
                    <p class="font-medium text-primary">{{ network.ssid }}</p>
                    <p class="text-xs text-muted">{{ network.security }}</p>
                  </div>
                </div>
                <div class="text-right">
                  <p class="text-sm font-medium text-primary">{{ network.signal_percent }}%</p>
                </div>
              </button>
            </div>
          </div>

          <!-- Password Input (shown when network is selected) -->
          <div v-if="selectedWifiNetwork" class="mb-4">
            <div class="p-3 rounded-lg bg-cyan-50 dark:bg-cyan-500/10 mb-3">
              <p class="text-sm font-medium text-cyan-700 dark:text-cyan-300">
                Selected: {{ selectedWifiNetwork.ssid }}
              </p>
            </div>

            <div v-if="selectedWifiNetwork.security !== 'Open'">
              <label class="block text-sm font-medium text-secondary mb-1">Password</label>
              <input
                v-model="wifiPassword"
                type="password"
                placeholder="Enter WiFi password"
                class="input w-full"
                @keyup.enter="connectToWifi"
              />
            </div>
            <p v-else class="text-sm text-muted">
              This is an open network (no password required)
            </p>
          </div>

          <!-- Action Buttons -->
          <div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              @click="closeWifiConfigModal"
              class="btn-secondary"
            >
              Cancel
            </button>
            <button
              @click="connectToWifi"
              :disabled="wifiConnecting || !selectedWifiNetwork"
              class="px-4 py-2 rounded-lg font-medium text-white bg-cyan-500 hover:bg-cyan-600 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowPathIcon v-if="wifiConnecting" class="h-4 w-4 animate-spin" />
              <WifiIcon v-else class="h-4 w-4" />
              {{ wifiConnecting ? 'Connecting...' : 'Connect' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Add Known Network Modal -->
    <Teleport to="body">
      <div v-if="showAddNetworkModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="p-3 rounded-full bg-purple-100 dark:bg-purple-500/20">
                <WifiIcon class="h-6 w-6 text-purple-500" />
              </div>
              <div>
                <h3 class="text-xl font-bold text-primary">Add Known Network</h3>
                <p class="text-sm text-muted">Pre-configure WiFi for automatic connection</p>
              </div>
            </div>
            <button
              @click="closeAddNetworkModal"
              class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <XCircleIcon class="h-5 w-5 text-gray-500" />
            </button>
          </div>

          <!-- Error display -->
          <div v-if="addNetworkError" class="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30">
            <p class="text-sm text-red-700 dark:text-red-300">{{ addNetworkError }}</p>
          </div>

          <!-- Add Network Form -->
          <div class="space-y-4 mb-6">
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Network Name (SSID)</label>
              <input
                v-model="addNetworkSsid"
                type="text"
                placeholder="Enter network SSID"
                class="input w-full"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Password</label>
              <input
                v-model="addNetworkPassword"
                type="password"
                placeholder="Enter network password"
                class="input w-full"
                @keyup.enter="addKnownNetwork"
              />
            </div>
            <div class="flex items-center gap-2">
              <input
                v-model="addNetworkAutoConnect"
                type="checkbox"
                id="autoConnect"
                class="rounded border-gray-300 text-purple-500 focus:ring-purple-500"
              />
              <label for="autoConnect" class="text-sm text-secondary">Auto-connect when network is available</label>
            </div>
            <button
              @click="addKnownNetwork"
              :disabled="addingNetwork || !addNetworkSsid.trim() || !addNetworkPassword"
              class="w-full px-4 py-2 rounded-lg font-medium text-white bg-purple-500 hover:bg-purple-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <ArrowPathIcon v-if="addingNetwork" class="h-4 w-4 animate-spin" />
              <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              {{ addingNetwork ? 'Adding...' : 'Add Network' }}
            </button>
          </div>

          <!-- Saved Networks List -->
          <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
            <div class="flex items-center justify-between mb-3">
              <h4 class="text-sm font-medium text-secondary">Saved WiFi Networks</h4>
              <button
                @click="loadSavedNetworks"
                :disabled="loadingSavedNetworks"
                class="btn-secondary text-xs flex items-center gap-1"
              >
                <ArrowPathIcon :class="['h-3.5 w-3.5', loadingSavedNetworks ? 'animate-spin' : '']" />
                Refresh
              </button>
            </div>

            <div v-if="loadingSavedNetworks" class="py-4 text-center">
              <ArrowPathIcon class="h-6 w-6 animate-spin mx-auto text-purple-500" />
            </div>

            <div v-else-if="savedNetworks.length === 0" class="py-4 text-center text-muted">
              <WifiIcon class="h-6 w-6 mx-auto opacity-50 mb-1" />
              <p class="text-sm">No saved networks</p>
            </div>

            <div v-else class="max-h-48 overflow-y-auto space-y-2">
              <div
                v-for="network in savedNetworks"
                :key="network.name"
                class="flex items-center justify-between p-3 bg-surface-hover rounded-lg"
              >
                <div class="flex items-center gap-3">
                  <WifiIcon class="h-5 w-5 text-purple-500" />
                  <div>
                    <p class="font-medium text-primary">{{ network.name }}</p>
                    <p class="text-xs text-muted">
                      {{ network.auto_connect ? 'Auto-connect enabled' : 'Manual connection' }}
                    </p>
                  </div>
                </div>
                <button
                  @click="deleteSavedNetwork(network.name)"
                  :disabled="deletingNetwork === network.name"
                  class="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
                  title="Delete network"
                >
                  <ArrowPathIcon v-if="deletingNetwork === network.name" class="h-4 w-4 animate-spin" />
                  <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- Close Button -->
          <div class="flex justify-end pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              @click="closeAddNetworkModal"
              class="btn-secondary"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
