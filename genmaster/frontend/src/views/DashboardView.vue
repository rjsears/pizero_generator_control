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
    <!-- Control Row: GenSlave | Automation | Generator | Emergency Stop -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <!-- GenSlave Online Status -->
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center gap-3">
            <div
              :class="[
                'p-2 rounded-lg',
                slaveOnline ? 'bg-emerald-100 dark:bg-emerald-500/20' : 'bg-red-100 dark:bg-red-500/20'
              ]"
            >
              <ServerIcon
                :class="[
                  'h-5 w-5',
                  slaveOnline ? 'text-emerald-500' : 'text-red-500'
                ]"
              />
            </div>
            <div>
              <p class="text-sm text-secondary">GenSlave</p>
              <p
                :class="[
                  'text-xl font-bold',
                  slaveOnline ? 'text-emerald-500' : 'text-red-500'
                ]"
              >
                {{ slaveOnline ? 'Online' : 'Offline' }}
              </p>
            </div>
          </div>
        </div>
      </Card>

      <!-- Relay Armed Status (GenSlave) -->
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div
                :class="[
                  'p-2 rounded-lg',
                  relayArmed ? 'bg-amber-100 dark:bg-amber-500/20' : 'bg-gray-100 dark:bg-gray-500/20'
                ]"
              >
                <ShieldExclamationIcon
                  :class="[
                    'h-5 w-5',
                    relayArmed ? 'text-amber-500' : 'text-gray-500'
                  ]"
                />
              </div>
              <div>
                <p class="text-sm text-secondary">Relay</p>
                <p
                  :class="[
                    'text-xl font-bold',
                    relayArmed ? 'text-amber-500' : 'text-gray-500'
                  ]"
                >
                  {{ relayArmed ? 'Armed' : 'Disarmed' }}
                </p>
              </div>
            </div>
            <button
              @click="toggleRelayArm"
              :disabled="togglingRelay || !slaveOnline"
              :class="[
                'relative inline-flex h-6 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                relayArmed
                  ? 'bg-amber-500 focus:ring-amber-500'
                  : 'bg-gray-400 focus:ring-gray-500',
                (togglingRelay || !slaveOnline) ? 'opacity-50 cursor-not-allowed' : ''
              ]"
            >
              <span
                :class="[
                  'inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition-transform',
                  relayArmed ? 'translate-x-7' : 'translate-x-1'
                ]"
              />
            </button>
          </div>
        </div>
      </Card>

      <!-- Generator Start/Stop Toggle -->
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div
                :class="[
                  'p-2 rounded-lg',
                  generatorStore.isRunning ? 'bg-green-100 dark:bg-green-500/20' : 'bg-gray-100 dark:bg-gray-500/20'
                ]"
              >
                <BoltIcon
                  :class="[
                    'h-5 w-5',
                    generatorStore.isRunning ? 'text-green-500' : 'text-gray-500'
                  ]"
                />
              </div>
              <div>
                <p class="text-sm text-secondary">Generator</p>
                <p
                  :class="[
                    'text-xl font-bold',
                    generatorStore.isRunning ? 'text-green-500' : 'text-gray-500'
                  ]"
                >
                  {{ generatorStore.isRunning ? 'Running' : 'Stopped' }}
                </p>
              </div>
            </div>
            <button
              @click="toggleGenerator"
              :disabled="generatorToggleLoading || !relayArmed"
              :class="[
                'relative inline-flex h-6 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                generatorStore.isRunning
                  ? 'bg-green-500 focus:ring-green-500'
                  : 'bg-gray-400 focus:ring-gray-500',
                (generatorToggleLoading || !relayArmed) ? 'opacity-50 cursor-not-allowed' : ''
              ]"
              :title="!relayArmed ? 'Relay must be armed to control generator' : ''"
            >
              <span
                :class="[
                  'inline-block h-4 w-4 transform rounded-full bg-white shadow-lg transition-transform',
                  generatorStore.isRunning ? 'translate-x-7' : 'translate-x-1'
                ]"
              />
            </button>
          </div>
        </div>
      </Card>

      <!-- Emergency Stop -->
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-red-100 dark:bg-red-500/20">
                <ExclamationTriangleIcon class="h-5 w-5 text-red-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Emergency</p>
                <p class="text-xl font-bold text-red-500">Stop</p>
              </div>
            </div>
            <button
              @click="handleEmergencyStop"
              :disabled="!generatorStore.isRunning || emergencyStopLoading"
              :class="[
                'px-4 py-2 rounded-lg font-bold text-sm text-white transition-all',
                generatorStore.isRunning && !emergencyStopLoading
                  ? 'bg-red-500 hover:bg-red-600 shadow-lg'
                  : 'bg-gray-400 cursor-not-allowed'
              ]"
            >
              <span v-if="emergencyStopLoading">...</span>
              <span v-else>STOP</span>
            </button>
          </div>
        </div>
      </Card>
    </div>

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

      <!-- Generator Status Row: Generator and Victron -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Generator Status - Enhanced with animated icon -->
        <Card :padding="false">
          <div class="p-6">
            <div class="flex items-start gap-6">
              <!-- Animated Generator Icon -->
              <div
                :class="[
                  'relative w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-500',
                  generatorStore.isRunning ? 'bg-gradient-to-br from-green-400 to-green-600 shadow-lg shadow-green-500/30' : 'bg-gradient-to-br from-gray-400 to-gray-600'
                ]"
              >
                <!-- Pulsing ring when running -->
                <div
                  v-if="generatorStore.isRunning"
                  class="absolute inset-0 rounded-2xl bg-green-400 animate-ping opacity-20"
                />
                <!-- Spinning cog when running -->
                <CogIcon
                  :class="[
                    'w-10 h-10 text-white relative z-10',
                    generatorStore.isRunning ? 'animate-spin-slow' : ''
                  ]"
                />
              </div>

              <!-- Status Info -->
              <div class="flex-1">
                <p class="text-sm font-medium text-secondary uppercase tracking-wider">Generator Status</p>
                <p class="text-3xl font-black mt-1" :class="generatorStateClass">
                  {{ generatorStateText }}
                </p>

                <!-- Trigger reason and runtime -->
                <div class="mt-3 flex flex-wrap gap-3">
                  <!-- Trigger Badge -->
                  <div
                    v-if="generatorTrigger && generatorStore.isRunning"
                    :class="[
                      'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold',
                      triggerBadgeClass
                    ]"
                  >
                    <component :is="triggerIcon" class="w-3.5 h-3.5" />
                    {{ triggerLabel }}
                  </div>

                  <!-- Runtime Badge -->
                  <div
                    v-if="generatorStore.isRunning"
                    class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300"
                  >
                    <ClockIcon class="w-3.5 h-3.5" />
                    {{ formatMinutes(localRunTimeMinutes) }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Runtime bar when running -->
            <div v-if="generatorStore.isRunning" class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div class="flex items-center justify-between text-sm mb-2">
                <span class="text-secondary">Runtime</span>
                <span class="font-medium text-primary">{{ formatMinutes(localRunTimeMinutes) }}</span>
              </div>
              <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-green-400 to-green-600 rounded-full transition-all animate-pulse"
                  :style="{ width: `${Math.min((localRunTimeMinutes / 120) * 100, 100)}%` }"
                />
              </div>
            </div>

            <!-- Last run info when stopped -->
            <div v-else class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <p class="text-sm text-secondary">
                <span class="text-muted">Generator is idle</span>
              </p>
            </div>
          </div>
        </Card>

        <!-- Victron Status - GPIO17 input from Victron Cerbo -->
        <Card>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-secondary">Victron Command</p>
              <p class="text-2xl font-bold mt-1" :class="victronActive ? 'text-green-500' : 'text-gray-500'">
                {{ victronActive ? 'Generator Run' : 'Generator Stop' }}
              </p>
            </div>
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', victronActive ? 'bg-green-500' : 'bg-gray-400']">
              <SignalIcon class="w-6 h-6 text-white" />
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p class="text-sm text-secondary">GPIO17 {{ victronActive ? 'HIGH' : 'LOW' }}</p>
          </div>
        </Card>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '@/stores/generator'
import { useSystemStore } from '@/stores/system'
import { useMetricsStore } from '@/stores/metrics'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import {
  BoltIcon,
  CpuChipIcon,
  ClockIcon,
  ServerStackIcon,
  CircleStackIcon,
  ServerIcon,
  SignalIcon,
  ShieldExclamationIcon,
  ExclamationTriangleIcon,
  CogIcon,
  CalendarIcon,
  HandRaisedIcon,
  BoltSlashIcon,
} from '@heroicons/vue/24/outline'
import { genslaveApi } from '@/services/api'

const router = useRouter()
const generatorStore = useGeneratorStore()
const systemStore = useSystemStore()
const metricsStore = useMetricsStore()

const loading = ref(true)
const metricsAvailable = ref(false)
let refreshInterval = null
let runtimeInterval = null

// Relay arm/disarm state (GenSlave)
const relayArmed = ref(false)
const togglingRelay = ref(false)

// Generator toggle state
const generatorToggleLoading = ref(false)

// Emergency stop state
const emergencyStopLoading = ref(false)

// Real-time runtime tracking
const localRunTimeSeconds = ref(0)
const localRunTimeMinutes = computed(() => Math.floor(localRunTimeSeconds.value / 60))

// Update local runtime from generator state
function syncRuntimeFromStore() {
  if (generatorStore.state?.start_time && generatorStore.isRunning) {
    // Calculate current runtime based on start_time
    const now = Math.floor(Date.now() / 1000)
    localRunTimeSeconds.value = now - generatorStore.state.start_time
  } else if (generatorStore.state?.runtime_seconds) {
    localRunTimeSeconds.value = generatorStore.state.runtime_seconds
  } else {
    localRunTimeSeconds.value = 0
  }
}

// Start/stop runtime timer based on generator state
function updateRuntimeTimer() {
  // Clear existing timer
  if (runtimeInterval) {
    clearInterval(runtimeInterval)
    runtimeInterval = null
  }

  // Start timer if generator is running
  if (generatorStore.isRunning) {
    syncRuntimeFromStore()
    runtimeInterval = setInterval(() => {
      localRunTimeSeconds.value++
    }, 1000)
  }
}

// Handle emergency stop
async function handleEmergencyStop() {
  emergencyStopLoading.value = true
  try {
    await generatorStore.emergencyStop()
  } catch (err) {
    console.error('Emergency stop failed:', err)
  } finally {
    emergencyStopLoading.value = false
  }
}

// Toggle relay arm/disarm - GenSlave is the source of truth
async function toggleRelayArm() {
  togglingRelay.value = true
  try {
    if (relayArmed.value) {
      await genslaveApi.disarm()
      relayArmed.value = false
    } else {
      await genslaveApi.arm()
      relayArmed.value = true
    }
  } catch (err) {
    console.error('Failed to toggle relay arm state:', err)
  } finally {
    togglingRelay.value = false
  }
}

// Toggle generator start/stop
async function toggleGenerator() {
  generatorToggleLoading.value = true
  try {
    if (generatorStore.isRunning) {
      await generatorStore.stop('manual')
    } else {
      await generatorStore.start(null, 'manual')
    }
    // Refresh state after action
    await generatorStore.fetchState()
  } catch (err) {
    console.error('Failed to toggle generator:', err)
  } finally {
    generatorToggleLoading.value = false
  }
}

// Fetch relay state from GenSlave
async function fetchRelayState() {
  try {
    const response = await genslaveApi.getRelayState()
    relayArmed.value = response.data?.armed || false
  } catch (err) {
    console.error('Failed to fetch relay state:', err)
    relayArmed.value = false
  }
}

// Watch for generator running state changes to start/stop runtime timer
watch(() => generatorStore.isRunning, (isRunning) => {
  if (isRunning) {
    syncRuntimeFromStore()
    updateRuntimeTimer()
  } else {
    if (runtimeInterval) {
      clearInterval(runtimeInterval)
      runtimeInterval = null
    }
    localRunTimeSeconds.value = 0
  }
})

// Fetch data on mount and set up polling
onMounted(async () => {
  try {
    await Promise.all([
      systemStore.fetchHealth(),
      systemStore.fetchSlaveHealth(),
      systemStore.fetchVictronStatus(),
      metricsStore.fetchDashboardMetrics(),
      fetchRelayState(),
      generatorStore.fetchState(),
    ])
    metricsAvailable.value = true

    // Initialize runtime timer if generator is already running
    updateRuntimeTimer()
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
  if (runtimeInterval) {
    clearInterval(runtimeInterval)
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

// Victron status - GPIO17 high means Victron is requesting generator to run
const victronActive = computed(() => systemStore.victronInputActive)

// Generator trigger info
const generatorTrigger = computed(() => generatorStore.state?.trigger || 'idle')

const triggerLabel = computed(() => {
  const labels = {
    victron: 'Victron Request',
    manual: 'Manual Start',
    scheduled: 'Scheduled Run',
    idle: 'Idle',
  }
  return labels[generatorTrigger.value] || generatorTrigger.value
})

const triggerBadgeClass = computed(() => {
  const classes = {
    victron: 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300',
    manual: 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300',
    scheduled: 'bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-300',
    idle: 'bg-gray-100 dark:bg-gray-500/20 text-gray-700 dark:text-gray-300',
  }
  return classes[generatorTrigger.value] || classes.idle
})

const triggerIcon = computed(() => {
  const icons = {
    victron: BoltIcon,
    manual: HandRaisedIcon,
    scheduled: CalendarIcon,
    idle: BoltSlashIcon,
  }
  return icons[generatorTrigger.value] || BoltSlashIcon
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

// Navigate to containers view with filter
function navigateToContainers(filter = null) {
  router.push({ name: 'containers', query: filter ? { status: filter } : {} })
}

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

<style scoped>
/* Slow spin animation for generator cog when running */
@keyframes spin-slow {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin-slow {
  animation: spin-slow 3s linear infinite;
}
</style>
