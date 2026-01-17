<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/HistoryView.vue

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

      <!-- Runs table -->
      <Card v-else>
        <div class="overflow-x-auto">
          <table class="table">
            <thead>
              <tr>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Duration</th>
                <th>Trigger</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in runs" :key="run.id">
                <td>{{ formatDateTime(run.started_at) }}</td>
                <td>{{ run.ended_at ? formatDateTime(run.ended_at) : '-' }}</td>
                <td>{{ formatDuration(run.duration_minutes) }}</td>
                <td>
                  <StatusBadge :status="getTriggerColor(run.trigger_type)">
                    {{ formatTrigger(run.trigger_type) }}
                  </StatusBadge>
                </td>
                <td>
                  <StatusBadge :status="getStatusColor(run.end_reason)">
                    {{ formatStatus(run.end_reason) }}
                  </StatusBadge>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="flex items-center justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
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
      </Card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useGeneratorStore } from '@/stores/generator'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import HistoryLoader from '@/components/common/HistoryLoader.vue'

const generatorStore = useGeneratorStore()

const runs = ref([])
const loading = ref(true)
const total = ref(0)
const page = ref(1)
const limit = ref(20)

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

function formatDateTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString()
}

function formatDuration(minutes) {
  if (!minutes || minutes === 0) return '-'
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  if (hours > 0) {
    return `${hours}h ${mins}m`
  }
  return `${mins}m`
}

function formatTrigger(trigger) {
  const triggers = {
    manual: 'Manual',
    scheduled: 'Scheduled',
    victron: 'Victron',
    api: 'API',
  }
  return triggers[trigger] || trigger || 'Unknown'
}

function getTriggerColor(trigger) {
  const colors = {
    manual: 'blue',
    scheduled: 'green',
    victron: 'amber',
    api: 'gray',
  }
  return colors[trigger] || 'gray'
}

function formatStatus(endReason) {
  if (!endReason) return 'Running'
  const statuses = {
    completed: 'Completed',
    manual_stop: 'Manual Stop',
    emergency_stop: 'Emergency',
    error: 'Error',
    timeout: 'Timeout',
    scheduled_end: 'Scheduled End',
  }
  return statuses[endReason] || endReason
}

function getStatusColor(endReason) {
  if (!endReason) return 'amber'
  const colors = {
    completed: 'success',
    manual_stop: 'info',
    emergency_stop: 'danger',
    error: 'danger',
    timeout: 'warning',
    scheduled_end: 'success',
  }
  return colors[endReason] || 'gray'
}
</script>
