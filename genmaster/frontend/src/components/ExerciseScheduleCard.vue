<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/ExerciseScheduleCard.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <Card title="Generator Exercise Schedule">
    <template #actions>
      <div class="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          @click="showEditModal = true"
        >
          <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Edit
        </Button>
      </div>
    </template>

    <div v-if="loading" class="text-center py-8">
      <div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
      <p class="text-sm text-gray-500 mt-2">Loading exercise schedule...</p>
    </div>

    <div v-else class="space-y-4">
      <!-- Enable/Disable Toggle -->
      <div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        <div>
          <p class="text-sm font-medium text-gray-900 dark:text-white">Exercise Scheduling</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Automatically run the generator for maintenance
          </p>
        </div>
        <Toggle
          :modelValue="schedule.enabled"
          @update:modelValue="handleToggle"
          :disabled="toggling"
        />
      </div>

      <!-- Schedule Details -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Frequency</p>
          <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
            Every {{ schedule.frequency_days }} days
          </p>
        </div>
        <div>
          <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Start Time</p>
          <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
            {{ formatTime(schedule.start_time) }}
          </p>
        </div>
        <div>
          <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Duration</p>
          <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
            {{ schedule.duration_minutes }} minutes
          </p>
        </div>
      </div>

      <!-- Exercise History -->
      <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400">Last Exercise</p>
            <p class="text-sm font-semibold text-gray-900 dark:text-white mt-1">
              {{ schedule.last_exercise_date ? formatDate(schedule.last_exercise_date) : 'Never' }}
            </p>
          </div>
          <div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
            <p class="text-xs font-medium text-gray-500 dark:text-gray-400">Next Scheduled</p>
            <p class="text-sm font-semibold mt-1" :class="schedule.enabled ? 'text-green-600 dark:text-green-400' : 'text-gray-500'">
              {{ schedule.enabled && schedule.next_exercise_date ? formatDate(schedule.next_exercise_date) : 'Not scheduled' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Run Now Button -->
      <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
        <Button
          variant="primary"
          :loading="runningNow"
          :disabled="!canRunNow"
          @click="handleRunNow"
        >
          <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
          </svg>
          Run Exercise Now
        </Button>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Start an exercise run immediately ({{ schedule.duration_minutes }} minutes)
        </p>
      </div>
    </div>

    <!-- Edit Modal -->
    <ExerciseScheduleModal
      v-model="showEditModal"
      :schedule="schedule"
      @saved="handleSaved"
    />

    <!-- Confirm Run Now -->
    <Modal v-model="showConfirmRunNow" title="Run Exercise Now?">
      <p class="text-gray-600 dark:text-gray-400">
        This will start the generator for {{ schedule.duration_minutes }} minutes as an exercise run.
      </p>
      <p class="text-sm text-gray-500 dark:text-gray-500 mt-2">
        Make sure the relay is armed before proceeding.
      </p>
      <template #footer>
        <Button variant="secondary" @click="showConfirmRunNow = false">Cancel</Button>
        <Button variant="success" :loading="runningNow" @click="executeRunNow">
          Start Exercise
        </Button>
      </template>
    </Modal>
  </Card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Toggle from '@/components/common/Toggle.vue'
import Modal from '@/components/common/Modal.vue'
import ExerciseScheduleModal from '@/components/ExerciseScheduleModal.vue'
import exerciseService from '@/services/exercise'
import { useNotificationStore } from '@/stores/notifications'
import { useGeneratorStore } from '@/stores/generator'

const notificationStore = useNotificationStore()
const generatorStore = useGeneratorStore()

const loading = ref(true)
const toggling = ref(false)
const runningNow = ref(false)
const showEditModal = ref(false)
const showConfirmRunNow = ref(false)

const schedule = ref({
  enabled: false,
  frequency_days: 7,
  start_time: '10:00',
  duration_minutes: 15,
  last_exercise_date: null,
  next_exercise_date: null,
})

const canRunNow = computed(() => {
  return !generatorStore.isRunning && !runningNow.value
})

function formatTime(time) {
  if (!time) return 'Not set'
  try {
    const [hours, minutes] = time.split(':')
    const h = parseInt(hours)
    const ampm = h >= 12 ? 'PM' : 'AM'
    const displayHour = h % 12 || 12
    return `${displayHour}:${minutes} ${ampm}`
  } catch {
    return time
  }
}

function formatDate(dateStr) {
  if (!dateStr) return 'Not set'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return dateStr
  }
}

async function fetchSchedule() {
  loading.value = true
  try {
    const response = await exerciseService.getSchedule()
    schedule.value = response.data
  } catch (error) {
    console.error('Failed to fetch exercise schedule:', error)
  } finally {
    loading.value = false
  }
}

async function handleToggle(enabled) {
  toggling.value = true
  try {
    const response = await exerciseService.updateSchedule({ enabled })
    schedule.value = response.data
    notificationStore.success(`Exercise scheduling ${enabled ? 'enabled' : 'disabled'}`)
  } catch (error) {
    console.error('Failed to toggle exercise schedule:', error)
    notificationStore.error('Failed to update exercise schedule')
  } finally {
    toggling.value = false
  }
}

function handleSaved(updatedSchedule) {
  schedule.value = updatedSchedule
}

function handleRunNow() {
  showConfirmRunNow.value = true
}

async function executeRunNow() {
  runningNow.value = true
  try {
    await exerciseService.runNow()
    notificationStore.success('Exercise run started')
    showConfirmRunNow.value = false
    // Refresh generator state
    await generatorStore.fetchState()
    // Refresh schedule to update last_exercise_date
    await fetchSchedule()
  } catch (error) {
    console.error('Failed to start exercise run:', error)
    const message = error.response?.data?.detail || 'Failed to start exercise run'
    notificationStore.error(message)
  } finally {
    runningNow.value = false
  }
}

onMounted(() => {
  fetchSchedule()
})
</script>
