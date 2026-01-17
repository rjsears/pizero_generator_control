<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/SystemView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

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
import { systemApi } from '../services/api'
import { formatBytes, formatUptime } from '../utils/formatters'
import Card from '../components/common/Card.vue'
import LoadingSpinner from '../components/common/LoadingSpinner.vue'
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
  HeartIcon,
  BoltIcon,
  ServerIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
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

// System info state
const systemInfo = ref({
  hostname: '',
  platform: '',
  architecture: '',
  kernel: '',
  uptime: 0,
  cpu: { model: '', cores: 0, usage: 0, temperature: 0 },
  memory: { total: 0, used: 0, free: 0, percent: 0 },
  disk: { total: 0, used: 0, free: 0, percent: 0 },
})

// Health state
const healthLoading = ref(false)
const healthLastUpdated = ref(null)

// Network state
const networkInfo = ref({ hostname: '', interfaces: [], gateway: null, dns_servers: [] })
const networkLoading = ref(false)

// Docker state
const dockerInfo = ref({ version: '', containers: { running: 0, total: 0 }, images: 0 })
const dockerLoading = ref(false)

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

// Computed properties from systemStore
const cpuPercent = computed(() => systemInfo.value.cpu?.usage || systemStore.cpuPercent || 0)
const memoryPercent = computed(() => systemInfo.value.memory?.percent || systemStore.memoryPercent || 0)
const diskPercent = computed(() => systemInfo.value.disk?.percent || systemStore.diskPercent || 0)
const temperature = computed(() => systemInfo.value.cpu?.temperature || systemStore.temperature || 0)

// Progress color helper
function getProgressColor(percent) {
  if (percent >= 90) return 'text-red-500'
  if (percent >= 75) return 'text-amber-500'
  return 'text-emerald-500'
}

function getTempColor(temp) {
  if (temp >= 80) return 'text-red-500'
  if (temp >= 60) return 'text-amber-500'
  return 'text-emerald-500'
}

// Load system info
async function loadSystemInfo() {
  healthLoading.value = true
  try {
    const [systemRes, dockerRes] = await Promise.all([
      systemApi.info(),
      systemApi.dockerInfo().catch(() => ({ data: {} })),
    ])
    systemInfo.value = systemRes.data
    dockerInfo.value = dockerRes.data
    healthLastUpdated.value = new Date()
  } catch (error) {
    console.error('System info load failed:', error)
    notificationStore.error('Failed to load system information')
  } finally {
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
      systemApi.slaveHealth().catch(() => ({ data: { online: false } })),
      systemApi.slaveDetails().catch(() => ({ data: null })),
    ])
    slaveInfo.value = {
      online: healthRes.data?.online || false,
      last_heartbeat: healthRes.data?.last_heartbeat,
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
    const response = await systemApi.testSlave()
    if (response.data?.success) {
      notificationStore.success(`Connection successful (${response.data.latency_ms || 0}ms)`)
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
async function renewSslCertificate() {
  try {
    const response = await systemApi.sslRenew()
    if (response.data?.success) {
      notificationStore.success('SSL certificate renewed successfully')
      await loadSslInfo()
    } else {
      notificationStore.error(response.data?.message || 'Failed to renew certificate')
    }
  } catch (error) {
    notificationStore.error('Failed to renew certificate')
  }
}

// Reboot system
function openRebootDialog() {
  rebootDialog.value.open = true
}

async function confirmReboot() {
  rebootDialog.value.loading = true
  try {
    await systemApi.reboot()
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
  await loadSystemInfo()
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
      <LoadingSpinner v-if="loading" text="Loading system info..." class="py-16" />

      <template v-else>
        <!-- Overall Status Banner -->
        <div class="rounded-xl p-6 border-2 relative overflow-hidden bg-gradient-to-r from-emerald-500/10 to-emerald-500/5 border-emerald-500/50">
          <div class="relative flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div class="p-4 rounded-2xl bg-emerald-500/20">
                <HeartIcon class="h-10 w-10 text-emerald-500" />
              </div>
              <div>
                <h2 class="text-2xl font-bold text-primary">
                  System Health: <span class="text-emerald-500">HEALTHY</span>
                </h2>
                <p class="text-secondary mt-1">
                  {{ systemInfo.hostname || 'GenMaster' }} •
                  Last updated: {{ healthLastUpdated ? new Date(healthLastUpdated).toLocaleTimeString() : 'Never' }}
                </p>
              </div>
            </div>

            <button
              @click="loadSystemInfo"
              :disabled="healthLoading"
              class="btn-secondary flex items-center gap-2"
            >
              <ArrowPathIcon :class="['h-4 w-4', healthLoading ? 'animate-spin' : '']" />
              Refresh
            </button>
          </div>
        </div>

        <!-- Resource Usage Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <!-- CPU -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-24 h-24" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="8" fill="transparent" r="42" cx="50" cy="50" />
                  <circle :class="getProgressColor(cpuPercent)" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${cpuPercent * 2.64} 264`" transform="rotate(-90 50 50)" />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-primary">{{ cpuPercent }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">CPU Usage</p>
              <p class="text-xs text-muted">{{ systemInfo.cpu?.model || 'Unknown' }}</p>
            </div>
          </Card>

          <!-- Memory -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-24 h-24" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="8" fill="transparent" r="42" cx="50" cy="50" />
                  <circle :class="getProgressColor(memoryPercent)" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${memoryPercent * 2.64} 264`" transform="rotate(-90 50 50)" />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-primary">{{ memoryPercent }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Memory Usage</p>
              <p class="text-xs text-muted">{{ formatBytes(systemInfo.memory?.used || 0) }} / {{ formatBytes(systemInfo.memory?.total || 0) }}</p>
            </div>
          </Card>

          <!-- Disk -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-24 h-24" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="8" fill="transparent" r="42" cx="50" cy="50" />
                  <circle :class="getProgressColor(diskPercent)" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${diskPercent * 2.64} 264`" transform="rotate(-90 50 50)" />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-primary">{{ diskPercent }}%</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Disk Usage</p>
              <p class="text-xs text-muted">{{ formatBytes(systemInfo.disk?.used || 0) }} / {{ formatBytes(systemInfo.disk?.total || 0) }}</p>
            </div>
          </Card>

          <!-- Temperature -->
          <Card :padding="false">
            <div class="p-4 text-center">
              <div class="relative inline-block">
                <svg class="w-24 h-24" viewBox="0 0 100 100">
                  <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="8" fill="transparent" r="42" cx="50" cy="50" />
                  <circle :class="getTempColor(temperature)" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${Math.min(temperature, 100) * 2.64} 264`" transform="rotate(-90 50 50)" />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="text-2xl font-bold text-primary">{{ temperature }}°C</span>
                </div>
              </div>
              <p class="text-sm text-secondary mt-2">Temperature</p>
              <p class="text-xs text-muted">CPU Core</p>
            </div>
          </Card>
        </div>

        <!-- Docker & System Info -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Docker -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                  <ServerIcon class="h-5 w-5 text-blue-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">Docker</h3>
                  <p class="text-xs text-muted">Container runtime</p>
                </div>
                <span class="px-2 py-1 rounded-full text-xs font-medium bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400">
                  RUNNING
                </span>
              </div>
              <dl class="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <dt class="text-secondary">Version</dt>
                  <dd class="font-medium text-primary">{{ dockerInfo.version || 'N/A' }}</dd>
                </div>
                <div>
                  <dt class="text-secondary">Containers</dt>
                  <dd class="font-medium text-primary">{{ dockerInfo.containers?.running || 0 }}/{{ dockerInfo.containers?.total || 0 }} running</dd>
                </div>
                <div>
                  <dt class="text-secondary">Images</dt>
                  <dd class="font-medium text-primary">{{ dockerInfo.images || 0 }}</dd>
                </div>
                <div>
                  <dt class="text-secondary">Uptime</dt>
                  <dd class="font-medium text-primary">{{ formatUptime(systemInfo.uptime || 0) }}</dd>
                </div>
              </dl>
            </div>
          </Card>

          <!-- System Info -->
          <Card :padding="false">
            <div class="p-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-500/20">
                  <CpuChipIcon class="h-5 w-5 text-purple-500" />
                </div>
                <div class="flex-1">
                  <h3 class="font-semibold text-primary">System</h3>
                  <p class="text-xs text-muted">Hardware & OS</p>
                </div>
              </div>
              <dl class="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <dt class="text-secondary">Hostname</dt>
                  <dd class="font-medium text-primary">{{ systemInfo.hostname || 'N/A' }}</dd>
                </div>
                <div>
                  <dt class="text-secondary">Platform</dt>
                  <dd class="font-medium text-primary">{{ systemInfo.platform || 'Raspberry Pi' }}</dd>
                </div>
                <div>
                  <dt class="text-secondary">Kernel</dt>
                  <dd class="font-medium text-primary truncate">{{ systemInfo.kernel || 'N/A' }}</dd>
                </div>
                <div>
                  <dt class="text-secondary">Architecture</dt>
                  <dd class="font-medium text-primary">{{ systemInfo.architecture || 'aarch64' }}</dd>
                </div>
              </dl>
            </div>
          </Card>
        </div>

        <!-- System Actions -->
        <Card :padding="false">
          <div class="p-4">
            <h3 class="font-semibold text-primary mb-4">System Actions</h3>
            <div class="flex flex-wrap gap-3">
              <button @click="openRebootDialog" class="btn-warning flex items-center gap-2">
                <ArrowPathIcon class="h-5 w-5" />
                Reboot System
              </button>
            </div>
          </div>
        </Card>
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
              <!-- Tailscale details -->
              <div v-if="tailscaleInfo.connected" class="border-t border-gray-200 dark:border-gray-700 pt-3 space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-secondary">Hostname</span>
                  <span class="text-primary">{{ tailscaleInfo.hostname }}</span>
                </div>
                <div v-if="tailscaleInfo.tailnet_name" class="flex justify-between">
                  <span class="text-secondary">Tailnet</span>
                  <span class="text-primary">{{ tailscaleInfo.tailnet_name }}</span>
                </div>
                <div v-if="tailscaleInfo.peers?.length > 0" class="flex justify-between">
                  <span class="text-secondary">Peers</span>
                  <span class="text-primary">
                    {{ tailscaleInfo.peers.filter(p => p.online).length }} online / {{ tailscaleInfo.peers.length }} total
                  </span>
                </div>
              </div>
            </div>
          </Card>
        </div>

        <!-- Tailscale Peers -->
        <Card v-if="tailscaleInfo.connected && tailscaleInfo.peers?.length > 0" title="Tailscale Peers" subtitle="Connected devices on your tailnet">
          <div class="space-y-2">
            <div
              v-for="peer in tailscaleInfo.peers"
              :key="peer.id"
              class="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50"
            >
              <div class="flex items-center gap-3">
                <div :class="['w-2 h-2 rounded-full', peer.online ? 'bg-emerald-500' : 'bg-gray-400']" />
                <div>
                  <p class="font-medium text-primary">{{ peer.hostname }}</p>
                  <p class="text-xs text-muted font-mono">{{ peer.ip_addresses?.[0] || 'No IP' }}</p>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span v-if="peer.os" class="text-xs text-muted">{{ peer.os }}</span>
                <span v-if="peer.is_exit_node" class="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                  Exit Node
                </span>
                <span :class="['px-2 py-1 rounded-full text-xs font-medium', peer.online ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400']">
                  {{ peer.online ? 'Online' : 'Offline' }}
                </span>
              </div>
            </div>
          </div>
        </Card>

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
            <div class="flex justify-end pt-2">
              <button @click="renewSslCertificate" class="btn-secondary text-sm">
                <ArrowPathIcon class="h-4 w-4 mr-2" />
                Force Renew
              </button>
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
                  <circle :class="getProgressColor(slaveInfo.details.cpu_percent || 0)" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${(slaveInfo.details.cpu_percent || 0) * 2.64} 264`" transform="rotate(-90 50 50)" />
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
                  <circle :class="getProgressColor(slaveInfo.details.memory_percent || 0)" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${(slaveInfo.details.memory_percent || 0) * 2.64} 264`" transform="rotate(-90 50 50)" />
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
                  <circle :class="getProgressColor(slaveInfo.details.disk_percent || 0)" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${(slaveInfo.details.disk_percent || 0) * 2.64} 264`" transform="rotate(-90 50 50)" />
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
                  <circle :class="getTempColor(slaveInfo.details.temperature || 0)" stroke="currentColor" stroke-width="8" stroke-linecap="round" fill="transparent" r="42" cx="50" cy="50" :stroke-dasharray="`${Math.min(slaveInfo.details.temperature || 0, 100) * 2.64} 264`" transform="rotate(-90 50 50)" />
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
  </div>
</template>
