<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/DashboardView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

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
              <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
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
              <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Last seen: {{ lastSeenText }}
            </p>
          </div>
        </Card>

        <!-- Victron Status -->
        <Card>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Victron Input</p>
              <p class="text-2xl font-bold mt-1" :class="victronActive ? 'text-green-500' : 'text-gray-500'">
                {{ victronActive ? 'Active' : 'Inactive' }}
              </p>
            </div>
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', victronActive ? 'bg-green-500' : 'bg-gray-500']">
              <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p class="text-sm text-gray-500 dark:text-gray-400">
              GPIO17 signal detection
            </p>
          </div>
        </Card>

        <!-- System Health -->
        <Card>
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">System Health</p>
              <p class="text-2xl font-bold mt-1" :class="healthClass">
                {{ healthText }}
              </p>
            </div>
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', healthBgClass]">
              <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p class="text-sm text-gray-500 dark:text-gray-400">
              CPU: {{ systemStore.cpuPercent }}% | RAM: {{ systemStore.memoryPercent }}%
            </p>
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

      <!-- System Metrics -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
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

        <!-- Recent Activity placeholder -->
        <Card title="Recent Activity">
          <div class="text-center py-8 text-gray-500 dark:text-gray-400">
            <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>No recent activity</p>
            <Button
              variant="ghost"
              size="sm"
              class="mt-3"
              @click="router.push('/history')"
            >
              View all history
            </Button>
          </div>
        </Card>
      </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '@/stores/generator'
import { useSystemStore } from '@/stores/system'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'

const router = useRouter()
const generatorStore = useGeneratorStore()
const systemStore = useSystemStore()

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

// Actions
async function startGenerator() {
  await generatorStore.start()
}

async function stopGenerator() {
  await generatorStore.stop()
}
</script>
