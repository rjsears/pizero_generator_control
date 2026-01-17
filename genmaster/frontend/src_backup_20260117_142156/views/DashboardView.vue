<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/DashboardView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 17th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">System overview and quick actions</p>
    </div>

    <!-- Status cards grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Generator Status -->
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Generator</p>
            <p class="text-2xl font-bold mt-1" :class="generatorStateClass">
              {{ generatorStateText }}
            </p>
          </div>
          <div :class="['w-12 h-12 rounded-full flex items-center justify-center', generatorIconBgClass]">
            <BoltIcon class="w-6 h-6 text-white" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Run time: {{ formatMinutes(generatorStore.runTimeMinutes) }}
          </p>
        </div>
      </Card>

      <!-- Slave Status -->
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">GenSlave</p>
            <p class="text-2xl font-bold mt-1" :class="slaveOnline ? 'text-green-500' : 'text-red-500'">
              {{ slaveOnline ? 'Online' : 'Offline' }}
            </p>
          </div>
          <div :class="['w-12 h-12 rounded-full flex items-center justify-center', slaveOnline ? 'bg-green-500' : 'bg-red-500']">
            <CpuChipIcon class="w-6 h-6 text-white" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Last seen: {{ lastSeenText }}
          </p>
        </div>
      </Card>

      <!-- Uptime Card -->
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">System Uptime</p>
            <p class="text-2xl font-bold mt-1 text-blue-500">
              {{ formattedUptime }}
            </p>
          </div>
          <div class="w-12 h-12 rounded-full flex items-center justify-center bg-blue-500">
            <ClockIcon class="w-6 h-6 text-white" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Since last boot
          </p>
        </div>
      </Card>

      <!-- Container Status Card -->
      <Card class="cursor-pointer hover:ring-2 hover:ring-blue-500/50 transition-all" @click="router.push('/containers')">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Containers</p>
            <p class="text-2xl font-bold mt-1" :class="containerStatusClass">
              {{ metricsStore.containersRunning }}/{{ metricsStore.containersTotal }}
            </p>
          </div>
          <div :class="['w-12 h-12 rounded-full flex items-center justify-center', containerStatusBgClass]">
            <ServerStackIcon class="w-6 h-6 text-white" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div class="flex items-center gap-4 text-sm">
            <span class="text-green-500">{{ metricsStore.containersRunning }} running</span>
            <span v-if="metricsStore.containersStopped > 0" class="text-gray-500">{{ metricsStore.containersStopped }} stopped</span>
            <span v-if="metricsStore.containersUnhealthy > 0" class="text-red-500">{{ metricsStore.containersUnhealthy }} unhealthy</span>
          </div>
        </div>
      </Card>
    </div>

    <!-- Quick Actions -->
    <Card title="Quick Actions">
      <div class="flex flex-wrap gap-3">
        <Button
          :variant="generatorStore.canStart ? 'success' : 'secondary'"
          :disabled="!generatorStore.canStart || generatorStore.actionLoading"
          :loading="generatorStore.actionLoading"
          @click="startGenerator"
        >
          Start Generator
        </Button>
        <Button
          :variant="generatorStore.canStop ? 'danger' : 'secondary'"
          :disabled="!generatorStore.canStop || generatorStore.actionLoading"
          :loading="generatorStore.actionLoading"
          @click="stopGenerator"
        >
          Stop Generator
        </Button>
        <Button
          variant="secondary"
          @click="router.push('/schedule')"
        >
          View Schedule
        </Button>
        <Button
          variant="secondary"
          @click="router.push('/history')"
        >
          View History
        </Button>
      </div>
    </Card>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- CPU History Chart -->
      <Card title="CPU Usage" subtitle="Last 60 minutes">
        <MetricsLineChart
          v-if="metricsStore.cpuHistory.length > 0"
          :labels="chartLabels"
          :datasets="[{
            label: 'CPU %',
            data: metricsStore.cpuHistory,
            borderColor: 'rgb(59, 130, 246)',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
          }]"
          :y-axis-max="100"
          y-axis-label="%"
          :height="180"
        />
        <div v-else class="h-[180px] flex items-center justify-center text-gray-400">
          <div class="text-center">
            <ChartBarIcon class="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p class="text-sm">Collecting metrics...</p>
          </div>
        </div>
      </Card>

      <!-- Memory History Chart -->
      <Card title="Memory Usage" subtitle="Last 60 minutes">
        <MetricsLineChart
          v-if="metricsStore.memoryHistory.length > 0"
          :labels="chartLabels"
          :datasets="[{
            label: 'Memory %',
            data: metricsStore.memoryHistory,
            borderColor: 'rgb(168, 85, 247)',
            backgroundColor: 'rgba(168, 85, 247, 0.1)',
          }]"
          :y-axis-max="100"
          y-axis-label="%"
          :height="180"
        />
        <div v-else class="h-[180px] flex items-center justify-center text-gray-400">
          <div class="text-center">
            <ChartBarIcon class="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p class="text-sm">Collecting metrics...</p>
          </div>
        </div>
      </Card>
    </div>

    <!-- Network I/O and Resource Usage Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Network I/O Card -->
      <Card title="Network I/O" subtitle="Current transfer rates">
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
            <div class="flex items-center gap-2 mb-1">
              <ArrowDownTrayIcon class="w-4 h-4 text-emerald-500" />
              <span class="text-sm font-medium text-emerald-700 dark:text-emerald-400">Download</span>
            </div>
            <p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
              {{ formatBytesPerSec(metricsStore.currentNetworkRecv) }}
            </p>
          </div>
          <div class="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20">
            <div class="flex items-center gap-2 mb-1">
              <ArrowUpTrayIcon class="w-4 h-4 text-blue-500" />
              <span class="text-sm font-medium text-blue-700 dark:text-blue-400">Upload</span>
            </div>
            <p class="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {{ formatBytesPerSec(metricsStore.currentNetworkSent) }}
            </p>
          </div>
        </div>
        <MetricsLineChart
          v-if="metricsStore.networkRecvHistory.length > 0"
          :labels="chartLabels"
          :datasets="[
            {
              label: 'Download',
              data: metricsStore.networkRecvHistory,
              borderColor: 'rgb(16, 185, 129)',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
            },
            {
              label: 'Upload',
              data: metricsStore.networkSentHistory,
              borderColor: 'rgb(59, 130, 246)',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
            },
          ]"
          :height="120"
          :show-legend="true"
          :format-tooltip="formatNetworkTooltip"
        />
      </Card>

      <!-- Resource Usage -->
      <Card title="Resource Usage">
        <div class="space-y-4">
          <!-- CPU -->
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-gray-600 dark:text-gray-400">CPU</span>
              <span class="font-medium">{{ systemStore.cpuPercent }}%</span>
            </div>
            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                class="h-2 rounded-full transition-all duration-300"
                :class="getProgressColor(systemStore.cpuPercent)"
                :style="{ width: `${systemStore.cpuPercent}%` }"
              ></div>
            </div>
          </div>

          <!-- Memory -->
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-gray-600 dark:text-gray-400">Memory</span>
              <span class="font-medium">{{ systemStore.memoryPercent }}%</span>
            </div>
            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                class="h-2 rounded-full transition-all duration-300"
                :class="getProgressColor(systemStore.memoryPercent)"
                :style="{ width: `${systemStore.memoryPercent}%` }"
              ></div>
            </div>
          </div>

          <!-- Disk -->
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span class="text-gray-600 dark:text-gray-400">Disk</span>
              <span class="font-medium">{{ systemStore.diskPercent }}%</span>
            </div>
            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                class="h-2 rounded-full transition-all duration-300"
                :class="getProgressColor(systemStore.diskPercent)"
                :style="{ width: `${systemStore.diskPercent}%` }"
              ></div>
            </div>
          </div>

          <!-- Temperature -->
          <div v-if="systemStore.temperature">
            <div class="flex justify-between text-sm mb-1">
              <span class="text-gray-600 dark:text-gray-400">Temperature</span>
              <span class="font-medium">{{ systemStore.temperature }}°C</span>
            </div>
            <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                class="h-2 rounded-full transition-all duration-300"
                :class="getTempColor(systemStore.temperature)"
                :style="{ width: `${Math.min(systemStore.temperature, 100)}%` }"
              ></div>
            </div>
          </div>
        </div>
      </Card>
    </div>

    <!-- Bottom Row: Victron Status and System Health -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Victron Status -->
      <Card title="Victron Status">
        <div class="flex items-center justify-between p-4 rounded-lg" :class="victronActive ? 'bg-green-50 dark:bg-green-900/20' : 'bg-gray-50 dark:bg-gray-800'">
          <div class="flex items-center gap-4">
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', victronActive ? 'bg-green-500' : 'bg-gray-400']">
              <SignalIcon class="w-6 h-6 text-white" />
            </div>
            <div>
              <p class="font-semibold" :class="victronActive ? 'text-green-700 dark:text-green-400' : 'text-gray-600 dark:text-gray-400'">
                {{ victronActive ? 'Signal Active' : 'No Signal' }}
              </p>
              <p class="text-sm text-gray-500 dark:text-gray-400">GPIO17 input</p>
            </div>
          </div>
          <div class="text-right">
            <span :class="['inline-flex items-center px-3 py-1 rounded-full text-sm font-medium', victronActive ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300']">
              {{ victronActive ? 'Active' : 'Inactive' }}
            </span>
          </div>
        </div>
      </Card>

      <!-- System Health -->
      <Card title="System Health">
        <div class="flex items-center justify-between p-4 rounded-lg" :class="healthBgClass.replace('bg-', 'bg-').replace('-500', '-50') + ' dark:bg-opacity-20'">
          <div class="flex items-center gap-4">
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', healthBgClass]">
              <HeartIcon class="w-6 h-6 text-white" />
            </div>
            <div>
              <p class="font-semibold" :class="healthClass">
                {{ healthText }}
              </p>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                CPU: {{ systemStore.cpuPercent }}% | RAM: {{ systemStore.memoryPercent }}%
              </p>
            </div>
          </div>
          <Button variant="secondary" size="sm" @click="router.push('/system')">
            View Details
          </Button>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '@/stores/generator'
import { useSystemStore } from '@/stores/system'
import { useMetricsStore } from '@/stores/metrics'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import MetricsLineChart from '@/components/charts/MetricsLineChart.vue'
import {
  BoltIcon,
  CpuChipIcon,
  ClockIcon,
  ServerStackIcon,
  ChartBarIcon,
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  SignalIcon,
  HeartIcon,
} from '@heroicons/vue/24/outline'

const router = useRouter()
const generatorStore = useGeneratorStore()
const systemStore = useSystemStore()
const metricsStore = useMetricsStore()

let refreshInterval = null

// Fetch data on mount and set up polling
onMounted(async () => {
  await metricsStore.fetchDashboardMetrics()

  // Refresh every 60 seconds
  refreshInterval = setInterval(() => {
    metricsStore.fetchDashboardMetrics()
  }, 60000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

// Generator state computed properties
const generatorStateText = computed(() => {
  const states = {
    stopped: 'Stopped',
    starting: 'Starting',
    warmup: 'Warming Up',
    running: 'Running',
    stopping: 'Stopping',
    cooldown: 'Cooldown',
    error: 'Error',
    unknown: 'Unknown',
  }
  return states[generatorStore.currentState] || 'Unknown'
})

const generatorStateClass = computed(() => {
  const classes = {
    stopped: 'text-gray-500',
    starting: 'text-amber-500',
    warmup: 'text-amber-500',
    running: 'text-green-500',
    stopping: 'text-amber-500',
    cooldown: 'text-blue-500',
    error: 'text-red-500',
    unknown: 'text-gray-500',
  }
  return classes[generatorStore.currentState] || 'text-gray-500'
})

const generatorIconBgClass = computed(() => {
  const classes = {
    stopped: 'bg-gray-500',
    starting: 'bg-amber-500',
    warmup: 'bg-amber-500',
    running: 'bg-green-500',
    stopping: 'bg-amber-500',
    cooldown: 'bg-blue-500',
    error: 'bg-red-500',
    unknown: 'bg-gray-500',
  }
  return classes[generatorStore.currentState] || 'bg-gray-500'
})

// Slave status
const slaveOnline = computed(() => systemStore.isSlaveOnline)
const lastSeenText = computed(() => {
  const lastSeen = systemStore.slaveLastSeen
  if (!lastSeen) return 'Never'
  const date = new Date(lastSeen * 1000)
  return date.toLocaleTimeString()
})

// Uptime
const formattedUptime = computed(() => {
  const seconds = systemStore.uptime
  if (!seconds) return '0m'

  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (days > 0) {
    return `${days}d ${hours}h`
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }
  return `${minutes}m`
})

// Container status
const containerStatusClass = computed(() => {
  if (metricsStore.containersUnhealthy > 0) return 'text-red-500'
  if (metricsStore.containersStopped > 0) return 'text-amber-500'
  return 'text-green-500'
})

const containerStatusBgClass = computed(() => {
  if (metricsStore.containersUnhealthy > 0) return 'bg-red-500'
  if (metricsStore.containersStopped > 0) return 'bg-amber-500'
  return 'bg-green-500'
})

// Victron status
const victronActive = computed(() => systemStore.victronInputActive)

// System health
const healthText = computed(() => {
  const health = systemStore.overallHealth
  const texts = {
    healthy: 'Healthy',
    warning: 'Warning',
    critical: 'Critical',
    unknown: 'Unknown',
  }
  return texts[health] || 'Unknown'
})

const healthClass = computed(() => {
  const classes = {
    healthy: 'text-green-500',
    warning: 'text-amber-500',
    critical: 'text-red-500',
    unknown: 'text-gray-500',
  }
  return classes[systemStore.overallHealth] || 'text-gray-500'
})

const healthBgClass = computed(() => {
  const classes = {
    healthy: 'bg-green-500',
    warning: 'bg-amber-500',
    critical: 'bg-red-500',
    unknown: 'bg-gray-500',
  }
  return classes[systemStore.overallHealth] || 'bg-gray-500'
})

// Chart labels
const chartLabels = computed(() => {
  return metricsStore.timestamps.map(ts => {
    const date = new Date(ts * 1000)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  })
})

// Helper functions
function formatMinutes(minutes) {
  if (!minutes || minutes === 0) return '0m'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  return `${mins}m`
}

function getProgressColor(percent) {
  if (percent >= 90) return 'bg-red-500'
  if (percent >= 70) return 'bg-amber-500'
  return 'bg-green-500'
}

function getTempColor(temp) {
  if (temp >= 80) return 'bg-red-500'
  if (temp >= 60) return 'bg-amber-500'
  return 'bg-green-500'
}

function formatBytesPerSec(bytes) {
  if (!bytes || bytes === 0) return '0 B/s'
  const k = 1024
  const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatNetworkTooltip(context) {
  const value = context.raw
  return `${context.dataset.label}: ${formatBytesPerSec(value)}`
}

// Actions
async function startGenerator() {
  await generatorStore.start()
}

async function stopGenerator() {
  await generatorStore.stop()
}
</script>
