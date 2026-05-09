<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/GeneratorView.vue

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
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Generator Control</h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">Monitor and control the generator</p>
      </div>

      <!-- Generator State Card -->
      <Card>
        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <!-- State Display -->
          <div class="flex items-center space-x-6">
            <div
              :class="['w-24 h-24 rounded-full flex items-center justify-center', stateColorBg]"
            >
              <svg class="w-12 h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <p class="text-sm text-gray-500 dark:text-gray-400">Current State</p>
              <p class="text-3xl font-bold" :class="stateColorText">{{ stateText }}</p>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Run time: {{ formatDuration(runTimeMinutes) }}
              </p>
            </div>
          </div>

          <!-- Control Buttons -->
          <div class="flex flex-col sm:flex-row gap-3">
            <Button
              :variant="canStart ? 'success' : 'secondary'"
              :disabled="!canStart || actionLoading"
              :loading="actionLoading"
              size="lg"
              @click="handleStart"
            >
              <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              </svg>
              Start Generator
            </Button>
            <Button
              :variant="canStop ? 'danger' : 'secondary'"
              :disabled="!canStop || actionLoading"
              :loading="actionLoading"
              size="lg"
              @click="handleStop"
            >
              <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
              </svg>
              Stop Generator
            </Button>
          </div>
        </div>
      </Card>

      <!-- Timed Start -->
      <Card title="Timed Start">
        <div class="flex flex-col sm:flex-row items-end gap-4">
          <div class="w-full sm:w-48">
            <Input
              v-model="timedDuration"
              type="number"
              label="Duration (minutes)"
              :min="1"
              :max="480"
              placeholder="30"
            />
          </div>
          <Button
            :variant="canStart ? 'primary' : 'secondary'"
            :disabled="!canStart || actionLoading || !timedDuration"
            :loading="actionLoading"
            @click="handleTimedStart"
          >
            Start for {{ timedDuration || '?' }} minutes
          </Button>
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-3">
          Start the generator for a specific duration. It will automatically stop after the time elapses.
        </p>
      </Card>

      <!-- Manual Override -->
      <Card title="Manual Override">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-700 dark:text-gray-300">
              Override automatic Victron control
            </p>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
              When enabled, the generator will not automatically start based on Victron signals.
            </p>
          </div>
          <Toggle
            v-model="overrideEnabled"
            @update:model-value="handleOverrideToggle"
          />
        </div>
      </Card>

      <!-- Statistics -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">Total Runs (30 days)</p>
            <p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
              {{ stats?.total_runs_30d || 0 }}
            </p>
          </div>
        </Card>
        <Card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">Total Runtime (30 days)</p>
            <p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
              {{ formatDuration(stats?.total_runtime_minutes_30d || 0) }}
            </p>
          </div>
        </Card>
        <Card>
          <div class="text-center">
            <p class="text-sm text-gray-500 dark:text-gray-400">Avg Run Duration</p>
            <p class="text-3xl font-bold text-gray-900 dark:text-white mt-2">
              {{ formatDuration(stats?.avg_duration_minutes || 0) }}
            </p>
          </div>
        </Card>
      </div>

      <!-- Emergency Stop -->
      <Card>
        <div class="flex items-center justify-between p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <div>
            <h3 class="font-semibold text-red-800 dark:text-red-200">Emergency Stop</h3>
            <p class="text-sm text-red-600 dark:text-red-400 mt-1">
              Immediately stop the generator and skip cooldown period.
            </p>
          </div>
          <Button
            variant="danger"
            :disabled="!isRunning || actionLoading"
            @click="handleEmergencyStop"
          >
            Emergency Stop
          </Button>
        </div>
      </Card>

    <!-- Confirm Modal -->
    <Modal v-model="showConfirm" :title="confirmTitle">
      <p class="text-gray-600 dark:text-gray-400">{{ confirmMessage }}</p>
      <template #footer>
        <Button variant="secondary" @click="showConfirm = false">Cancel</Button>
        <Button :variant="confirmVariant" @click="executeConfirmedAction">
          {{ confirmButtonText }}
        </Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useGeneratorStore } from '@/stores/generator'
import configService from '@/services/config'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'
import Modal from '@/components/common/Modal.vue'

const generatorStore = useGeneratorStore()

const timedDuration = ref(30)
const overrideEnabled = ref(false)
const stats = ref(null)

// Confirmation modal state
const showConfirm = ref(false)
const confirmTitle = ref('')
const confirmMessage = ref('')
const confirmVariant = ref('primary')
const confirmButtonText = ref('')
const pendingAction = ref(null)

// Computed properties
const currentState = computed(() => generatorStore.currentState)
const canStart = computed(() => generatorStore.canStart)
const canStop = computed(() => generatorStore.canStop)
const isRunning = computed(() => generatorStore.isRunning)
const actionLoading = computed(() => generatorStore.actionLoading)
const runTimeMinutes = computed(() => generatorStore.runTimeMinutes)

const stateText = computed(() => {
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
  return states[currentState.value] || 'Unknown'
})

const stateColorText = computed(() => {
  const colors = {
    stopped: 'text-gray-500',
    starting: 'text-amber-500',
    warmup: 'text-amber-500',
    running: 'text-green-500',
    stopping: 'text-amber-500',
    cooldown: 'text-blue-500',
    error: 'text-red-500',
    unknown: 'text-gray-500',
  }
  return colors[currentState.value] || 'text-gray-500'
})

const stateColorBg = computed(() => {
  const colors = {
    stopped: 'bg-gray-500',
    starting: 'bg-amber-500',
    warmup: 'bg-amber-500',
    running: 'bg-green-500',
    stopping: 'bg-amber-500',
    cooldown: 'bg-blue-500',
    error: 'bg-red-500',
    unknown: 'bg-gray-500',
  }
  return colors[currentState.value] || 'bg-gray-500'
})

// Lifecycle
onMounted(async () => {
  await generatorStore.fetchStats()
  stats.value = generatorStore.stats

  try {
    const override = await configService.getOverride()
    overrideEnabled.value = override.enabled
  } catch {
    // Ignore errors
  }
})

// Helper functions
function formatDuration(minutes) {
  if (!minutes || minutes === 0) return '0m'
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  return `${mins}m`
}

// Actions
function handleStart() {
  confirmTitle.value = 'Start Generator'
  confirmMessage.value = 'Are you sure you want to start the generator?'
  confirmVariant.value = 'success'
  confirmButtonText.value = 'Start'
  pendingAction.value = () => generatorStore.start()
  showConfirm.value = true
}

function handleTimedStart() {
  confirmTitle.value = 'Start Generator'
  confirmMessage.value = `Start the generator for ${timedDuration.value} minutes?`
  confirmVariant.value = 'success'
  confirmButtonText.value = 'Start'
  pendingAction.value = () => generatorStore.start(timedDuration.value)
  showConfirm.value = true
}

function handleStop() {
  confirmTitle.value = 'Stop Generator'
  confirmMessage.value = 'Are you sure you want to stop the generator?'
  confirmVariant.value = 'warning'
  confirmButtonText.value = 'Stop'
  pendingAction.value = () => generatorStore.stop()
  showConfirm.value = true
}

function handleEmergencyStop() {
  confirmTitle.value = 'Emergency Stop'
  confirmMessage.value = 'This will immediately stop the generator without cooldown. Continue?'
  confirmVariant.value = 'danger'
  confirmButtonText.value = 'Emergency Stop'
  pendingAction.value = () => generatorStore.emergencyStop()
  showConfirm.value = true
}

async function executeConfirmedAction() {
  showConfirm.value = false
  if (pendingAction.value) {
    await pendingAction.value()
    pendingAction.value = null
  }
}

async function handleOverrideToggle(enabled) {
  try {
    if (enabled) {
      await configService.enableOverride()
    } else {
      await configService.disableOverride()
    }
  } catch {
    overrideEnabled.value = !enabled
  }
}
</script>
