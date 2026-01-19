<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/HistoryView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Run History</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">View generator run history and statistics</p>
    </div>

    <!-- Filters -->
    <Card>
      <div class="flex flex-col sm:flex-row gap-4">
        <div class="flex-1">
          <Input
            v-model="filters.startDate"
            type="date"
            label="Start Date"
          />
        </div>
        <div class="flex-1">
          <Input
            v-model="filters.endDate"
            type="date"
            label="End Date"
          />
        </div>
        <div class="flex items-end">
          <Button variant="secondary" @click="applyFilters">
            Apply Filters
          </Button>
        </div>
      </div>
    </Card>

    <!-- Loading state -->
    <div v-if="loading">
      <HistoryLoader />
    </div>

    <!-- Empty state -->
    <Card v-else-if="runs.length === 0">
      <div class="text-center py-12">
        <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white">No runs found</h3>
        <p class="text-gray-500 dark:text-gray-400 mt-1">No generator runs match your criteria.</p>
      </div>
    </Card>

    <!-- Runs list with collapsible cards -->
    <div v-else class="space-y-3">
      <div
        v-for="run in runs"
        :key="run.id"
        class="rounded-lg border transition-all duration-200"
        :class="[
          expandedRun === run.id
            ? 'border-gray-300 dark:border-gray-600 shadow-md'
            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
        ]"
      >
        <!-- Collapsed header row -->
        <div
          class="flex items-center gap-4 p-4 cursor-pointer bg-white dark:bg-gray-800 rounded-lg"
          :class="{ 'rounded-b-none': expandedRun === run.id }"
          @click="toggleExpand(run.id)"
        >
          <!-- Trigger icon -->
          <div
            class="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center"
            :class="getTriggerBgColor(run.trigger_type)"
          >
            <component
              :is="getTriggerIcon(run.trigger_type)"
              class="w-6 h-6"
              :class="getTriggerIconColor(run.trigger_type)"
            />
          </div>

          <!-- Run info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-semibold text-gray-900 dark:text-white">
                {{ formatTrigger(run.trigger_type) }}
              </span>
              <span
                class="px-2 py-0.5 text-xs font-medium rounded-full"
                :class="getStatusBadgeClass(run.end_reason)"
              >
                {{ formatStatus(run.end_reason) }}
              </span>
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {{ formatDateTime(run.started_at) }}
            </div>
          </div>

          <!-- Duration -->
          <div class="text-right hidden sm:block">
            <div class="font-medium text-gray-900 dark:text-white">
              {{ formatDuration(run.duration_minutes) }}
            </div>
            <div class="text-sm text-gray-500 dark:text-gray-400">
              Duration
            </div>
          </div>

          <!-- Expand indicator -->
          <div class="flex-shrink-0">
            <svg
              class="w-5 h-5 text-gray-400 transition-transform duration-200"
              :class="{ 'rotate-180': expandedRun === run.id }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        <!-- Expanded details -->
        <Transition
          enter-active-class="transition-all duration-200 ease-out"
          enter-from-class="opacity-0 max-h-0"
          enter-to-class="opacity-100 max-h-96"
          leave-active-class="transition-all duration-150 ease-in"
          leave-from-class="opacity-100 max-h-96"
          leave-to-class="opacity-0 max-h-0"
        >
          <div
            v-if="expandedRun === run.id"
            class="overflow-hidden"
          >
            <div class="px-4 pb-4 pt-2 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700 rounded-b-lg">
              <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                <!-- Start Time -->
                <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                  <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                    Start Time
                  </div>
                  <div class="text-sm font-semibold text-gray-900 dark:text-white">
                    {{ formatDateTime(run.started_at) }}
                  </div>
                </div>

                <!-- Stop Time -->
                <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                  <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                    Stop Time
                  </div>
                  <div class="text-sm font-semibold text-gray-900 dark:text-white">
                    {{ run.ended_at ? formatDateTime(run.ended_at) : 'Running...' }}
                  </div>
                </div>

                <!-- Total Run Time -->
                <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                  <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                    Total Run Time
                  </div>
                  <div class="text-sm font-semibold text-gray-900 dark:text-white">
                    {{ formatDuration(run.duration_minutes) || 'In progress' }}
                  </div>
                </div>

                <!-- Fuel Used -->
                <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                  <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                    Fuel Used
                  </div>
                  <div class="text-sm font-semibold text-gray-900 dark:text-white">
                    <span v-if="run.estimated_fuel_used !== null && run.estimated_fuel_used !== undefined">
                      {{ run.estimated_fuel_used.toFixed(2) }} gal
                      <span v-if="run.fuel_type_at_run" class="text-xs text-gray-500 dark:text-gray-400 ml-1">
                        ({{ formatFuelType(run.fuel_type_at_run) }})
                      </span>
                    </span>
                    <span v-else class="text-gray-400 dark:text-gray-500 italic">
                      {{ run.ended_at ? 'N/A' : 'In progress' }}
                    </span>
                  </div>
                </div>

                <!-- Reason / End Status -->
                <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                  <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                    End Reason
                  </div>
                  <div class="text-sm font-semibold text-gray-900 dark:text-white">
                    {{ formatEndReason(run.end_reason) }}
                  </div>
                </div>
              </div>

              <!-- Notes (if any) -->
              <div v-if="run.notes" class="mt-4">
                <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                  <div class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
                    Notes
                  </div>
                  <div class="text-sm text-gray-900 dark:text-white">
                    {{ run.notes }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-between mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Showing {{ (page - 1) * limit + 1 }} to {{ Math.min(page * limit, total) }} of {{ total }} runs
        </p>
        <div class="flex space-x-2">
          <Button
            variant="secondary"
            size="sm"
            :disabled="page <= 1"
            @click="page--; loadHistory()"
          >
            Previous
          </Button>
          <Button
            variant="secondary"
            size="sm"
            :disabled="page >= totalPages"
            @click="page++; loadHistory()"
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useGeneratorStore } from '@/stores/generator'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import HistoryLoader from '@/components/common/HistoryLoader.vue'

const generatorStore = useGeneratorStore()

const runs = ref([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const limit = ref(20)
const expandedRun = ref(null)

const filters = ref({
  startDate: '',
  endDate: '',
})

const totalPages = computed(() => Math.ceil(total.value / limit.value))

onMounted(async () => {
  await loadHistory()
})

async function loadHistory() {
  loading.value = true
  expandedRun.value = null
  try {
    const params = {
      limit: limit.value,
      offset: (page.value - 1) * limit.value,
    }
    if (filters.value.startDate) {
      params.start_date = filters.value.startDate
    }
    if (filters.value.endDate) {
      params.end_date = filters.value.endDate
    }

    const response = await generatorStore.fetchHistory(params)
    runs.value = response.runs || []
    total.value = response.total || 0
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.value = 1
  loadHistory()
}

function toggleExpand(runId) {
  expandedRun.value = expandedRun.value === runId ? null : runId
}

function formatDateTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString()
}

function formatDuration(minutes) {
  if (!minutes || minutes === 0) return null
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  return `${mins}m`
}

function formatTrigger(trigger) {
  const triggers = {
    manual: 'Manual Start',
    scheduled: 'Scheduled Run',
    victron: 'Victron Auto-Start',
    exercise: 'Exercise Run',
    api: 'API',
  }
  return triggers[trigger] || trigger || 'Unknown'
}

function formatStatus(endReason) {
  if (!endReason) return 'Running'
  const statuses = {
    victron: 'Auto-Stopped',
    manual: 'Manual Stop',
    scheduled_end: 'Completed',
    exercise_end: 'Completed',
    comm_loss: 'Comm Loss',
    override: 'Override',
    error: 'Error',
  }
  return statuses[endReason] || endReason
}

function formatEndReason(endReason) {
  if (!endReason) return 'Still running'
  const reasons = {
    victron: 'Victron signaled stop (battery charged)',
    manual: 'Manually stopped by user',
    scheduled_end: 'Scheduled duration completed',
    exercise_end: 'Exercise duration completed',
    comm_loss: 'Communication lost with GenSlave',
    override: 'Overridden by higher priority',
    error: 'Error occurred',
  }
  return reasons[endReason] || endReason
}

function formatFuelType(fuelType) {
  const types = {
    lpg: 'LPG',
    natural_gas: 'Natural Gas',
    diesel: 'Diesel',
  }
  return types[fuelType] || fuelType || 'Unknown'
}

function getStatusBadgeClass(endReason) {
  if (!endReason) {
    return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
  }
  const classes = {
    victron: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    manual: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    scheduled_end: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    exercise_end: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
    comm_loss: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    override: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
    error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  }
  return classes[endReason] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
}

function getTriggerBgColor(trigger) {
  const colors = {
    manual: 'bg-blue-100 dark:bg-blue-900/30',
    scheduled: 'bg-green-100 dark:bg-green-900/30',
    victron: 'bg-amber-100 dark:bg-amber-900/30',
    exercise: 'bg-purple-100 dark:bg-purple-900/30',
  }
  return colors[trigger] || 'bg-gray-100 dark:bg-gray-900/30'
}

function getTriggerIconColor(trigger) {
  const colors = {
    manual: 'text-blue-600 dark:text-blue-400',
    scheduled: 'text-green-600 dark:text-green-400',
    victron: 'text-amber-600 dark:text-amber-400',
    exercise: 'text-purple-600 dark:text-purple-400',
  }
  return colors[trigger] || 'text-gray-600 dark:text-gray-400'
}

// SVG Icons as functional components
const ManualIcon = {
  render() {
    return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11' })
    ])
  }
}

const ScheduledIcon = {
  render() {
    return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' })
    ])
  }
}

const VictronIcon = {
  render() {
    return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M13 10V3L4 14h7v7l9-11h-7z' })
    ])
  }
}

const ExerciseIcon = {
  render() {
    return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z' })
    ])
  }
}

const DefaultIcon = {
  render() {
    return h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' })
    ])
  }
}

function getTriggerIcon(trigger) {
  const icons = {
    manual: ManualIcon,
    scheduled: ScheduledIcon,
    victron: VictronIcon,
    exercise: ExerciseIcon,
  }
  return icons[trigger] || DefaultIcon
}
</script>
