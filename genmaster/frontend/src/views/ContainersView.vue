<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/ContainersView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useContainersStore } from '@/stores/containers'
import { useNotificationStore } from '@/stores/notifications'
import { usePoll } from '@/composables/usePoll'
import { formatBytes } from '@/utils/formatters'
import { POLLING } from '@/config/constants'
import Card from '@/components/common/Card.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ContainerStackLoader from '@/components/common/ContainerStackLoader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import Modal from '@/components/common/Modal.vue'
import {
  ServerStackIcon,
  PlayIcon,
  StopIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  CommandLineIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ChevronDoubleDownIcon,
  ChevronDoubleUpIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/vue/24/outline'

const containersStore = useContainersStore()
const notificationStore = useNotificationStore()

const loading = ref(true)
const containerStats = ref({})
const expandedContainers = ref({})
const showLogsModal = ref(false)
const selectedContainer = ref(null)
const containerLogs = ref('')
const logsLoading = ref(false)

// Confirm dialog state
const confirmDialog = ref({
  open: false,
  title: '',
  message: '',
  action: null,
  danger: false,
  loading: false,
})

// Toggle container expand/collapse
function toggleContainer(containerId) {
  expandedContainers.value[containerId] = !expandedContainers.value[containerId]
}

function isExpanded(containerId) {
  return !!expandedContainers.value[containerId]
}

// Check if all containers are expanded
const allExpanded = computed(() => {
  if (containersWithStats.value.length === 0) return false
  return containersWithStats.value.every(c => expandedContainers.value[c.id])
})

// Toggle all containers expand/collapse
function toggleAllContainers() {
  const shouldExpand = !allExpanded.value
  containersWithStats.value.forEach(container => {
    expandedContainers.value[container.id] = shouldExpand
  })
}

// Merge containers with their stats
const containersWithStats = computed(() => {
  return containersStore.containers.map(container => {
    const stats = containerStats.value[container.name] || {}
    return {
      ...container,
      cpu_percent: stats.cpu_percent || 0,
      memory_usage: stats.memory_usage || 0,
      memory_limit: stats.memory_limit || 0,
      memory_percent: stats.memory_percent || 0,
      memory_mb: stats.memory_usage ? Math.round(stats.memory_usage / (1024 * 1024)) : 0,
      network_rx: stats.network_rx || 0,
      network_tx: stats.network_tx || 0,
    }
  })
})

// Stats summary
const stats = computed(() => {
  const all = containersWithStats.value
  return {
    total: all.length,
    running: all.filter(c => c.status === 'running').length,
    stopped: all.filter(c => c.status !== 'running').length,
    unhealthy: all.filter(c => c.health === 'unhealthy').length,
  }
})

function getStatusIcon(container) {
  if (container.health === 'unhealthy') return ExclamationTriangleIcon
  if (container.status === 'running') return CheckCircleIcon
  if (container.status === 'exited' || container.status === 'stopped') return XCircleIcon
  return ServerStackIcon
}

function getStatusIconColor(container) {
  if (container.health === 'unhealthy') return 'text-red-500'
  if (container.status === 'running') return 'text-emerald-500'
  return 'text-gray-400'
}

function getMemoryColor(memoryMb) {
  if (memoryMb > 500) return 'text-red-500'
  if (memoryMb > 200) return 'text-amber-500'
  return 'text-emerald-500'
}

function getCpuColor(cpuPercent) {
  if (cpuPercent > 80) return 'text-red-500'
  if (cpuPercent > 50) return 'text-amber-500'
  return 'text-emerald-500'
}

// Actions with confirmation
function promptStart(container) {
  confirmDialog.value = {
    open: true,
    title: 'Start Container',
    message: `Are you sure you want to start ${container.name}?`,
    action: () => startContainer(container.name),
    danger: false,
    loading: false,
  }
}

function promptStop(container) {
  confirmDialog.value = {
    open: true,
    title: 'Stop Container',
    message: `Are you sure you want to stop ${container.name}?`,
    action: () => stopContainer(container.name),
    danger: true,
    loading: false,
  }
}

function promptRestart(container) {
  confirmDialog.value = {
    open: true,
    title: 'Restart Container',
    message: `Are you sure you want to restart ${container.name}?`,
    action: () => restartContainer(container.name),
    danger: false,
    loading: false,
  }
}

async function confirmAction() {
  if (!confirmDialog.value.action) return
  confirmDialog.value.loading = true
  try {
    await confirmDialog.value.action()
    confirmDialog.value.open = false
  } finally {
    confirmDialog.value.loading = false
  }
}

async function startContainer(name) {
  await containersStore.startContainer(name)
}

async function stopContainer(name) {
  await containersStore.stopContainer(name)
}

async function restartContainer(name) {
  await containersStore.restartContainer(name)
}

async function viewLogs(container) {
  selectedContainer.value = container
  containerLogs.value = ''
  showLogsModal.value = true
  logsLoading.value = true

  try {
    const logs = await containersStore.getContainerLogs(container.name, 200)
    containerLogs.value = logs || 'No logs available'
  } catch {
    containerLogs.value = 'Failed to fetch logs'
  } finally {
    logsLoading.value = false
  }
}

async function fetchStats() {
  try {
    await containersStore.fetchStats()
    const statsMap = {}
    for (const stat of containersStore.stats) {
      statsMap[stat.name] = stat
    }
    containerStats.value = statsMap
  } catch (error) {
    console.error('Failed to fetch container stats:', error)
  }
}

async function loadData() {
  loading.value = true
  try {
    await containersStore.fetchContainers(true) // Include all containers
    await fetchStats()
  } finally {
    loading.value = false
  }
}

// Setup polling
const { stop: stopPolling } = usePoll(async () => {
  if (!loading.value) {
    await containersStore.fetchContainers(true)
    await fetchStats()
  }
}, POLLING.CONTAINERS, false)

onMounted(async () => {
  await loadData()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-primary">Containers</h1>
        <p class="text-secondary mt-1">Manage Docker containers</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="toggleAllContainers"
          class="btn-secondary btn-sm flex items-center gap-1"
          :title="allExpanded ? 'Collapse All' : 'Expand All'"
        >
          <ChevronDoubleDownIcon v-if="!allExpanded" class="h-4 w-4" />
          <ChevronDoubleUpIcon v-else class="h-4 w-4" />
          {{ allExpanded ? 'Collapse' : 'Expand' }}
        </button>
        <button @click="loadData" class="btn-secondary btn-sm flex items-center gap-1" :disabled="loading">
          <ArrowPathIcon class="h-4 w-4" :class="{ 'animate-spin': loading }" />
          Refresh
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary">Total</p>
            <p class="text-2xl font-bold text-primary">{{ stats.total }}</p>
          </div>
          <ServerStackIcon class="h-8 w-8 text-blue-500" />
        </div>
      </Card>
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary">Running</p>
            <p class="text-2xl font-bold text-emerald-500">{{ stats.running }}</p>
          </div>
          <CheckCircleIcon class="h-8 w-8 text-emerald-500" />
        </div>
      </Card>
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary">Stopped</p>
            <p class="text-2xl font-bold text-gray-500">{{ stats.stopped }}</p>
          </div>
          <XCircleIcon class="h-8 w-8 text-gray-400" />
        </div>
      </Card>
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary">Unhealthy</p>
            <p class="text-2xl font-bold" :class="stats.unhealthy > 0 ? 'text-red-500' : 'text-gray-500'">
              {{ stats.unhealthy }}
            </p>
          </div>
          <ExclamationTriangleIcon class="h-8 w-8" :class="stats.unhealthy > 0 ? 'text-red-500' : 'text-gray-400'" />
        </div>
      </Card>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center py-12">
      <ContainerStackLoader text="Loading containers..." />
    </div>

    <!-- Error State -->
    <Card v-else-if="containersStore.error" class="border-red-500">
      <div class="text-center py-8">
        <ExclamationTriangleIcon class="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-primary">{{ containersStore.error }}</h3>
        <p class="text-secondary mt-1">Make sure Docker is running and accessible.</p>
        <button @click="loadData" class="btn-primary mt-4">Try Again</button>
      </div>
    </Card>

    <!-- Empty State -->
    <EmptyState
      v-else-if="containersWithStats.length === 0"
      :icon="ServerStackIcon"
      title="No containers found"
      description="No Docker containers were found on this system."
    />

    <!-- Container List -->
    <div v-else class="space-y-3">
      <Card
        v-for="container in containersWithStats"
        :key="container.id"
        :padding="false"
        class="overflow-hidden"
      >
        <!-- Container Header (always visible) -->
        <div
          class="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-surface-hover transition-colors"
          @click="toggleContainer(container.id)"
        >
          <div class="flex items-center gap-3">
            <ChevronRightIcon
              class="h-5 w-5 text-secondary transition-transform"
              :class="{ 'rotate-90': isExpanded(container.id) }"
            />
            <component
              :is="getStatusIcon(container)"
              class="h-6 w-6"
              :class="getStatusIconColor(container)"
            />
            <div>
              <h3 class="font-medium text-primary">{{ container.name }}</h3>
              <p class="text-xs text-muted">{{ container.image }}</p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <!-- Quick stats -->
            <div v-if="container.status === 'running'" class="hidden md:flex items-center gap-4 text-sm">
              <span :class="getCpuColor(container.cpu_percent)">
                CPU: {{ container.cpu_percent.toFixed(1) }}%
              </span>
              <span :class="getMemoryColor(container.memory_mb)">
                RAM: {{ container.memory_mb }}MB
              </span>
            </div>
            <StatusBadge :status="container.status" />
          </div>
        </div>

        <!-- Expanded Content -->
        <Transition name="expand">
          <div v-if="isExpanded(container.id)" class="border-t border-gray-400 dark:border-black">
            <div class="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Container Info -->
              <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-secondary">Container ID:</span>
                  <span class="text-primary font-mono text-xs">{{ container.id?.substring(0, 12) }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-secondary">Image:</span>
                  <span class="text-primary">{{ container.image }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-secondary">Status:</span>
                  <span class="text-primary capitalize">{{ container.status }}</span>
                </div>
                <div v-if="container.health" class="flex justify-between">
                  <span class="text-secondary">Health:</span>
                  <StatusBadge :status="container.health" size="sm" />
                </div>
              </div>

              <!-- Resource Usage -->
              <div v-if="container.status === 'running'" class="space-y-2 text-sm">
                <div class="flex justify-between">
                  <span class="text-secondary">CPU Usage:</span>
                  <span :class="getCpuColor(container.cpu_percent)">{{ container.cpu_percent.toFixed(2) }}%</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-secondary">Memory:</span>
                  <span :class="getMemoryColor(container.memory_mb)">
                    {{ formatBytes(container.memory_usage) }} / {{ formatBytes(container.memory_limit) }}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-secondary">Network RX:</span>
                  <span class="text-primary">{{ formatBytes(container.network_rx) }}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-secondary">Network TX:</span>
                  <span class="text-primary">{{ formatBytes(container.network_tx) }}</span>
                </div>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-400 dark:border-black flex flex-wrap gap-2">
              <button
                v-if="container.status !== 'running'"
                @click.stop="promptStart(container)"
                class="btn-success btn-sm flex items-center gap-1"
              >
                <PlayIcon class="h-4 w-4" />
                Start
              </button>
              <button
                v-if="container.status === 'running'"
                @click.stop="promptStop(container)"
                class="btn-danger btn-sm flex items-center gap-1"
              >
                <StopIcon class="h-4 w-4" />
                Stop
              </button>
              <button
                @click.stop="promptRestart(container)"
                class="btn-warning btn-sm flex items-center gap-1"
                :disabled="container.status !== 'running'"
              >
                <ArrowPathIcon class="h-4 w-4" />
                Restart
              </button>
              <button
                @click.stop="viewLogs(container)"
                class="btn-secondary btn-sm flex items-center gap-1"
              >
                <DocumentTextIcon class="h-4 w-4" />
                Logs
              </button>
            </div>
          </div>
        </Transition>
      </Card>
    </div>

    <!-- Confirm Dialog -->
    <ConfirmDialog
      v-model:open="confirmDialog.open"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :danger="confirmDialog.danger"
      :loading="confirmDialog.loading"
      @confirm="confirmAction"
    />

    <!-- Logs Modal -->
    <Modal v-model="showLogsModal" :title="`Logs: ${selectedContainer?.name}`" size="full">
      <div v-if="logsLoading" class="flex justify-center py-8">
        <LoadingSpinner text="Loading logs..." />
      </div>
      <div v-else class="bg-gray-900 rounded-lg p-4 h-96 overflow-auto">
        <pre class="text-green-400 text-sm font-mono whitespace-pre-wrap">{{ containerLogs }}</pre>
      </div>
      <template #footer>
        <button @click="showLogsModal = false" class="btn-secondary">Close</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
