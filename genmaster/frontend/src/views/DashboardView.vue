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
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-primary">System Overview</h1>
      <p class="text-secondary mt-1">
        Real-time system monitoring
        <span v-if="!metricsAvailable && !loading" class="text-amber-500 text-xs ml-2">
          (Waiting for metrics collection...)
        </span>
      </p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4"></div>
        <p class="text-secondary">Loading metrics...</p>
      </div>
    </div>

    <!-- Dashboard Content -->
    <template v-else>
      <!-- Quick Stats Row: CPU, Memory, Disk, Uptime -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <!-- CPU Usage -->
        <Card :padding="false">
          <div class="p-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                <CpuChipIcon class="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">CPU Usage</p>
                <p class="text-xl font-bold text-primary">{{ systemStore.cpuPercent.toFixed(1) }}%</p>
              </div>
            </div>
            <div class="mt-3 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                :class="['h-full rounded-full transition-all', getProgressColor(systemStore.cpuPercent)]"
                :style="{ width: `${systemStore.cpuPercent}%` }"
              />
            </div>
          </div>
        </Card>

        <!-- Memory Usage -->
        <Card :padding="false">
          <div class="p-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-500/20">
                <CircleStackIcon class="h-5 w-5 text-purple-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Memory Usage</p>
                <p class="text-xl font-bold text-primary">{{ systemStore.memoryPercent.toFixed(1) }}%</p>
              </div>
            </div>
            <div class="mt-3 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                :class="['h-full rounded-full transition-all', getProgressColor(systemStore.memoryPercent)]"
                :style="{ width: `${systemStore.memoryPercent}%` }"
              />
            </div>
          </div>
        </Card>

        <!-- Disk Usage -->
        <Card :padding="false">
          <div class="p-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-500/20">
                <ServerStackIcon class="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Disk Usage</p>
                <p class="text-xl font-bold text-primary">{{ systemStore.diskPercent.toFixed(1) }}%</p>
              </div>
            </div>
            <div class="mt-3 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                :class="['h-full rounded-full transition-all', getProgressColor(systemStore.diskPercent)]"
                :style="{ width: `${systemStore.diskPercent}%` }"
              />
            </div>
          </div>
        </Card>

        <!-- Uptime -->
        <Card :padding="false">
          <div class="p-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-amber-100 dark:bg-amber-500/20">
                <ClockIcon class="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Uptime</p>
                <p class="text-xl font-bold text-primary">{{ formattedUptime }}</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- Generator Status Row: Generator, GenSlave, Victron -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Generator Status -->
        <Card>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-secondary">Generator</p>
              <p class="text-2xl font-bold mt-1" :class="generatorStateClass">
                {{ generatorStateText }}
              </p>
            </div>
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', generatorIconBgClass]">
              <BoltIcon class="w-6 h-6 text-white" />
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p class="text-sm text-secondary">
              Run time: {{ formatMinutes(generatorStore.runTimeMinutes) }}
            </p>
          </div>
        </Card>

        <!-- GenSlave Status -->
        <Card>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-secondary">GenSlave</p>
              <p class="text-2xl font-bold mt-1" :class="slaveOnline ? 'text-green-500' : 'text-red-500'">
                {{ slaveOnline ? 'Online' : 'Offline' }}
              </p>
            </div>
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', slaveOnline ? 'bg-green-500' : 'bg-red-500']">
              <CpuChipIcon class="w-6 h-6 text-white" />
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p class="text-sm text-secondary">
              Last seen: {{ lastSeenText }}
            </p>
          </div>
        </Card>

        <!-- Victron Status -->
        <Card>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-secondary">Victron Status</p>
              <p class="text-2xl font-bold mt-1" :class="victronActive ? 'text-green-500' : 'text-gray-500'">
                {{ victronActive ? 'Signal Active' : 'No Signal' }}
              </p>
            </div>
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', victronActive ? 'bg-green-500' : 'bg-gray-400']">
              <SignalIcon class="w-6 h-6 text-white" />
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p class="text-sm text-secondary">GPIO17 input</p>
          </div>
        </Card>
      </div>

      <!-- System & Containers Row -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- System Uptime Card -->
        <Card>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-secondary">System Uptime</p>
              <p class="text-2xl font-bold mt-1 text-blue-500">
                {{ formattedUptime }}
              </p>
            </div>
            <div class="w-12 h-12 rounded-full flex items-center justify-center bg-blue-500">
              <ClockIcon class="w-6 h-6 text-white" />
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p class="text-sm text-secondary">Since last boot</p>
          </div>
        </Card>

        <!-- Container Status Card -->
        <Card class="cursor-pointer hover:ring-2 hover:ring-blue-500/50 transition-all" @click="router.push('/containers')">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-secondary">Containers</p>
              <p class="text-2xl font-bold mt-1" :class="containerStatusClass">
                {{ metricsStore.containersRunning }}/{{ metricsStore.containersTotal }}
              </p>
            </div>
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', containerStatusBgClass]">
              <ServerIcon class="w-6 h-6 text-white" />
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

      <!-- Charts Row: CPU History & Memory History -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- CPU History Chart -->
        <Card title="CPU History" subtitle="Last 60 minutes">
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
        <Card title="Memory History" subtitle="Last 60 minutes">
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
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
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
  CircleStackIcon,
  ServerIcon,
  ChartBarIcon,
  SignalIcon,
} from '@heroicons/vue/24/outline'

const router = useRouter()
const generatorStore = useGeneratorStore()
const systemStore = useSystemStore()
const metricsStore = useMetricsStore()

const loading = ref(true)
const metricsAvailable = ref(false)
let refreshInterval = null

// Fetch data on mount and set up polling
onMounted(async () => {
  try {
    await Promise.all([
      systemStore.fetchHealth(),
      systemStore.fetchSlaveHealth(),
      systemStore.fetchVictronStatus(),
      metricsStore.fetchDashboardMetrics(),
    ])
    metricsAvailable.value = true
  } catch (err) {
    console.error('Failed to load dashboard data:', err)
  } finally {
    loading.value = false
  }

  // Refresh every 60 seconds
  refreshInterval = setInterval(async () => {
    await Promise.all([
      systemStore.fetchHealth(),
      systemStore.fetchSlaveHealth(),
      systemStore.fetchVictronStatus(),
      metricsStore.fetchDashboardMetrics(),
    ])
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

// Victron status
const victronActive = computed(() => systemStore.victronInputActive)

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

// Actions
async function startGenerator() {
  await generatorStore.start()
}

async function stopGenerator() {
  await generatorStore.stop()
}
</script>
