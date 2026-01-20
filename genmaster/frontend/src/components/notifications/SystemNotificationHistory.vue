<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/notifications/SystemNotificationHistory.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Enhanced notification history with full message details,
  filtering, and pagination.

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import notificationsService from '@/services/notifications'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Select from '@/components/common/Select.vue'
import Modal from '@/components/common/Modal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import {
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  InboxStackIcon,
  FunnelIcon,
  ArrowPathIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EyeIcon,
  TrashIcon,
  DocumentTextIcon,
} from '@heroicons/vue/24/outline'

const notifications = useNotificationStore()

// State
const loading = ref(true)
const history = ref([])
const stats = ref(null)
const totalItems = ref(0)
const totalPages = ref(0)

// Pagination
const currentPage = ref(1)
const pageSize = ref(25)

// Filters
const filters = ref({
  category: '',
  status: '',
  event_type: '',
})

// Detail modal
const showDetailModal = ref(false)
const selectedNotification = ref(null)

// Category options
const categoryOptions = [
  { value: '', label: 'All Categories' },
  { value: 'generator', label: 'Generator' },
  { value: 'genslave', label: 'GenSlave' },
  { value: 'genmaster', label: 'GenMaster' },
  { value: 'ssl', label: 'SSL Certificates' },
  { value: 'container', label: 'Containers' },
]

// Status options
const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'sent', label: 'Sent' },
  { value: 'failed', label: 'Failed' },
  { value: 'suppressed', label: 'Suppressed' },
  { value: 'batched', label: 'Batched' },
]

// Computed
const hasFilters = computed(() => {
  return filters.value.category || filters.value.status || filters.value.event_type
})

// Watch for filter changes
watch(filters, () => {
  currentPage.value = 1
  loadHistory()
}, { deep: true })

// Lifecycle
onMounted(async () => {
  await Promise.all([loadHistory(), loadStats()])
})

// Methods
async function loadHistory() {
  loading.value = true
  try {
    const activeFilters = {}
    if (filters.value.category) activeFilters.category = filters.value.category
    if (filters.value.status) activeFilters.status = filters.value.status
    if (filters.value.event_type) activeFilters.event_type = filters.value.event_type

    const response = await notificationsService.getSystemHistory(
      currentPage.value,
      pageSize.value,
      activeFilters
    )
    history.value = response.items || []
    totalItems.value = response.total || 0
    totalPages.value = response.total_pages || 0
  } catch (error) {
    console.error('Failed to load history:', error)
    notifications.error('Failed to load notification history')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await notificationsService.getSystemHistoryStats()
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
}

function clearFilters() {
  filters.value = {
    category: '',
    status: '',
    event_type: '',
  }
}

function viewDetails(notification) {
  selectedNotification.value = notification
  showDetailModal.value = true
}

function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page
    loadHistory()
  }
}

function formatDate(dateStr) {
  if (!dateStr) return 'Unknown'
  const date = new Date(dateStr)
  return date.toLocaleString()
}

function formatRelativeDate(dateStr) {
  if (!dateStr) return 'Unknown'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return 'Just now'
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return `${mins}m ago`
  }
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours}h ago`
  }
  const days = Math.floor(diff / 86400000)
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString()
}

function getStatusIcon(status) {
  const icons = {
    sent: CheckCircleIcon,
    failed: XCircleIcon,
    suppressed: ExclamationTriangleIcon,
    batched: InboxStackIcon,
  }
  return icons[status] || ClockIcon
}

function getStatusColor(status) {
  const colors = {
    sent: 'text-green-500 bg-green-100 dark:bg-green-500/20',
    failed: 'text-red-500 bg-red-100 dark:bg-red-500/20',
    suppressed: 'text-amber-500 bg-amber-100 dark:bg-amber-500/20',
    batched: 'text-blue-500 bg-blue-100 dark:bg-blue-500/20',
  }
  return colors[status] || 'text-gray-500 bg-gray-100 dark:bg-gray-500/20'
}

function getSeverityColor(severity) {
  const colors = {
    info: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
    warning: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300',
    critical: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300',
  }
  return colors[severity] || colors.info
}

function getCategoryLabel(category) {
  const labels = {
    generator: 'Generator',
    genslave: 'GenSlave',
    genmaster: 'GenMaster',
    ssl: 'SSL',
    container: 'Container',
  }
  return labels[category] || category
}
</script>

<template>
  <div class="space-y-6">
    <!-- Stats Cards -->
    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-green-100 dark:bg-green-500/20">
              <CheckCircleIcon class="h-5 w-5 text-green-500" />
            </div>
            <div>
              <p class="text-sm text-secondary">Sent</p>
              <p class="text-xl font-bold text-primary">{{ stats.sent_count }}</p>
            </div>
          </div>
        </div>
      </Card>

      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-red-100 dark:bg-red-500/20">
              <XCircleIcon class="h-5 w-5 text-red-500" />
            </div>
            <div>
              <p class="text-sm text-secondary">Failed</p>
              <p class="text-xl font-bold text-primary">{{ stats.failed_count }}</p>
            </div>
          </div>
        </div>
      </Card>

      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-amber-100 dark:bg-amber-500/20">
              <ExclamationTriangleIcon class="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p class="text-sm text-secondary">Suppressed</p>
              <p class="text-xl font-bold text-primary">{{ stats.suppressed_count }}</p>
            </div>
          </div>
        </div>
      </Card>

      <Card :padding="false">
        <div class="p-4">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
              <InboxStackIcon class="h-5 w-5 text-blue-500" />
            </div>
            <div>
              <p class="text-sm text-secondary">Batched</p>
              <p class="text-xl font-bold text-primary">{{ stats.batched_count }}</p>
            </div>
          </div>
        </div>
      </Card>
    </div>

    <!-- Filters -->
    <Card :padding="false">
      <div class="p-4">
        <div class="flex items-center gap-4 flex-wrap">
          <div class="flex items-center gap-2">
            <FunnelIcon class="h-5 w-5 text-secondary" />
            <span class="text-sm font-medium text-secondary">Filters:</span>
          </div>

          <Select
            v-model="filters.category"
            :options="categoryOptions"
            class="w-40"
          />

          <Select
            v-model="filters.status"
            :options="statusOptions"
            class="w-40"
          />

          <button
            v-if="hasFilters"
            @click="clearFilters"
            class="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            <XCircleIcon class="h-4 w-4" />
            Clear
          </button>

          <div class="ml-auto">
            <button
              @click="loadHistory"
              class="p-2 text-gray-400 hover:text-primary-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <ArrowPathIcon class="h-5 w-5" :class="{ 'animate-spin': loading }" />
            </button>
          </div>
        </div>
      </div>
    </Card>

    <!-- History List -->
    <Card :padding="false">
      <div class="p-4 border-b border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-500/20">
              <ClockIcon class="h-5 w-5 text-purple-500" />
            </div>
            <div>
              <h3 class="font-semibold text-primary">System Notification History</h3>
              <p class="text-sm text-secondary">{{ totalItems }} total notifications</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="py-12 flex justify-center">
        <LoadingSpinner />
      </div>

      <!-- Empty State -->
      <EmptyState
        v-else-if="history.length === 0"
        :icon="ClockIcon"
        title="No notifications found"
        :description="hasFilters ? 'Try adjusting your filters' : 'Notification history will appear here'"
        class="py-12"
      />

      <!-- History Items -->
      <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
        <div
          v-for="item in history"
          :key="item.id"
          class="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex items-start gap-3 flex-1 min-w-0">
              <!-- Status Icon -->
              <div :class="['p-2 rounded-lg flex-shrink-0', getStatusColor(item.status)]">
                <component :is="getStatusIcon(item.status)" class="h-5 w-5" />
              </div>

              <!-- Content -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <h4 class="font-medium text-primary truncate">{{ item.title }}</h4>
                  <span :class="['text-xs px-2 py-0.5 rounded-full', getSeverityColor(item.severity)]">
                    {{ item.severity }}
                  </span>
                  <span class="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                    {{ getCategoryLabel(item.category) }}
                  </span>
                  <span v-if="item.escalation_level > 1" class="text-xs px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300">
                    L{{ item.escalation_level }}
                  </span>
                </div>

                <p class="text-sm text-secondary mt-1 line-clamp-2">{{ item.message }}</p>

                <div class="flex items-center gap-3 mt-2 text-xs text-muted">
                  <span>{{ item.event_type }}</span>
                  <span v-if="item.target_label">{{ item.target_label }}</span>
                  <span v-if="item.suppression_reason" class="text-amber-600 dark:text-amber-400">
                    Suppressed: {{ item.suppression_reason }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-2 flex-shrink-0">
              <span class="text-sm text-secondary whitespace-nowrap">{{ formatRelativeDate(item.triggered_at) }}</span>
              <button
                @click="viewDetails(item)"
                class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg"
                title="View details"
              >
                <EyeIcon class="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="p-4 border-t border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between">
          <p class="text-sm text-secondary">
            Showing {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, totalItems) }} of {{ totalItems }}
          </p>

          <div class="flex items-center gap-2">
            <button
              @click="goToPage(currentPage - 1)"
              :disabled="currentPage === 1"
              class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeftIcon class="h-5 w-5" />
            </button>

            <span class="text-sm text-primary px-3">
              Page {{ currentPage }} of {{ totalPages }}
            </span>

            <button
              @click="goToPage(currentPage + 1)"
              :disabled="currentPage === totalPages"
              class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRightIcon class="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </Card>

    <!-- Detail Modal -->
    <Modal v-model="showDetailModal" title="Notification Details" size="lg">
      <div v-if="selectedNotification" class="space-y-4">
        <!-- Header Info -->
        <div class="flex items-center gap-3">
          <div :class="['p-3 rounded-lg', getStatusColor(selectedNotification.status)]">
            <component :is="getStatusIcon(selectedNotification.status)" class="h-6 w-6" />
          </div>
          <div>
            <h3 class="font-semibold text-primary text-lg">{{ selectedNotification.title }}</h3>
            <div class="flex items-center gap-2 mt-1">
              <span :class="['text-xs px-2 py-0.5 rounded-full', getSeverityColor(selectedNotification.severity)]">
                {{ selectedNotification.severity }}
              </span>
              <span class="text-xs text-muted">{{ selectedNotification.event_type }}</span>
            </div>
          </div>
        </div>

        <!-- Message -->
        <div>
          <label class="text-sm font-medium text-secondary block mb-1">Message</label>
          <pre class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-sm whitespace-pre-wrap font-mono">{{ selectedNotification.message }}</pre>
        </div>

        <!-- Details Grid -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm font-medium text-secondary block mb-1">Category</label>
            <p class="text-primary">{{ getCategoryLabel(selectedNotification.category) }}</p>
          </div>
          <div>
            <label class="text-sm font-medium text-secondary block mb-1">Status</label>
            <p class="text-primary capitalize">{{ selectedNotification.status }}</p>
          </div>
          <div>
            <label class="text-sm font-medium text-secondary block mb-1">Triggered At</label>
            <p class="text-primary">{{ formatDate(selectedNotification.triggered_at) }}</p>
          </div>
          <div>
            <label class="text-sm font-medium text-secondary block mb-1">Sent At</label>
            <p class="text-primary">{{ selectedNotification.sent_at ? formatDate(selectedNotification.sent_at) : 'Not sent' }}</p>
          </div>
          <div v-if="selectedNotification.target_label">
            <label class="text-sm font-medium text-secondary block mb-1">Target</label>
            <p class="text-primary">{{ selectedNotification.target_label }}</p>
          </div>
          <div>
            <label class="text-sm font-medium text-secondary block mb-1">Escalation Level</label>
            <p class="text-primary">L{{ selectedNotification.escalation_level }}</p>
          </div>
        </div>

        <!-- Suppression Reason -->
        <div v-if="selectedNotification.suppression_reason">
          <label class="text-sm font-medium text-secondary block mb-1">Suppression Reason</label>
          <p class="text-amber-600 dark:text-amber-400">{{ selectedNotification.suppression_reason }}</p>
        </div>

        <!-- Error Message -->
        <div v-if="selectedNotification.error_message">
          <label class="text-sm font-medium text-secondary block mb-1">Error</label>
          <p class="text-red-600 dark:text-red-400">{{ selectedNotification.error_message }}</p>
        </div>

        <!-- Channels Sent -->
        <div v-if="selectedNotification.channels_sent?.length > 0">
          <label class="text-sm font-medium text-secondary block mb-1">Channels</label>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(ch, idx) in selectedNotification.channels_sent"
              :key="idx"
              :class="[
                'text-xs px-3 py-1 rounded-full',
                ch.success ? 'bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300'
              ]"
            >
              {{ ch.name || `Channel ${ch.id}` }}
              <span v-if="!ch.success && ch.error" class="ml-1">({{ ch.error }})</span>
            </span>
          </div>
        </div>

        <!-- Event Data -->
        <div v-if="selectedNotification.event_data && Object.keys(selectedNotification.event_data).length > 0">
          <label class="text-sm font-medium text-secondary block mb-1">Event Data</label>
          <pre class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg text-xs overflow-auto max-h-40 font-mono">{{ JSON.stringify(selectedNotification.event_data, null, 2) }}</pre>
        </div>
      </div>

      <template #footer>
        <Button variant="secondary" @click="showDetailModal = false">Close</Button>
      </template>
    </Modal>
  </div>
</template>
