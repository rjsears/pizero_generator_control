<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/ContainersView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 17th, 2026

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
import ContainerTerminal from '@/components/containers/ContainerTerminal.vue'
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
  ArrowPathRoundedSquareIcon,
  FunnelIcon,
  ShieldExclamationIcon,
} from '@heroicons/vue/24/outline'

const containersStore = useContainersStore()
const notificationStore = useNotificationStore()

const loading = ref(true)
const containerStats = ref({})
const expandedContainers = ref({})
const showLogsModal = ref(false)
const showTerminalModal = ref(false)
const selectedContainer = ref(null)
const containerLogs = ref('')
const logsLoading = ref(false)

// Status filter
const statusFilter = ref('all') // 'all', 'running', 'stopped', 'unhealthy'

// Recreate dialog state
const recreateDialog = ref({
  open: false,
  container: null,
  pullImage: true,
  loading: false,
})

// Critical container warning dialog
const criticalWarning = ref({
  open: false,
  container: null,
  action: null,
  actionName: '',
})

// Critical containers that require extra confirmation
const CRITICAL_CONTAINERS = ['genmaster', 'nginx', 'postgres', 'genmaster-api', 'genmaster-nginx', 'genmaster-db']

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

// Check if container is critical
function isCriticalContainer(containerName) {
  return CRITICAL_CONTAINERS.some(critical =>
    containerName.toLowerCase().includes(critical.toLowerCase())
  )
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
      isCritical: isCriticalContainer(container.name),
    }
  })
})

// Filtered containers based on status
const filteredContainers = computed(() => {
  if (statusFilter.value === 'all') {
    return containersWithStats.value
  }
  if (statusFilter.value === 'running') {
    return containersWithStats.value.filter(c => c.status === 'running')
  }
  if (statusFilter.value === 'stopped') {
    return containersWithStats.value.filter(c => c.status !== 'running')
  }
  if (statusFilter.value === 'unhealthy') {
    return containersWithStats.value.filter(c => c.health === 'unhealthy')
  }
  return containersWithStats.value
})

// Check if all filtered containers are expanded
const allExpanded = computed(() => {
  if (filteredContainers.value.length === 0) return false
  return filteredContainers.value.every(c => expandedContainers.value[c.id])
})

// Toggle all containers expand/collapse
function toggleAllContainers() {
  const shouldExpand = !allExpanded.value
  filteredContainers.value.forEach(container => {
    expandedContainers.value[container.id] = shouldExpand
  })
}

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

// Check for critical container and show warning if needed
function checkCriticalAndExecute(container, action, actionName) {
  if (container.isCritical) {
    criticalWarning.value = {
      open: true,
      container,
      action,
      actionName,
    }
  } else {
    action()
  }
}

function confirmCriticalAction() {
  if (criticalWarning.value.action) {
    criticalWarning.value.action()
  }
  criticalWarning.value.open = false
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
  const action = () => {
    confirmDialog.value = {
      open: true,
      title: 'Stop Container',
      message: `Are you sure you want to stop ${container.name}?`,
      action: () => stopContainer(container.name),
      danger: true,
      loading: false,
    }
  }
  checkCriticalAndExecute(container, action, 'stop')
}

function promptRestart(container) {
  const action = () => {
    confirmDialog.value = {
      open: true,
      title: 'Restart Container',
      message: `Are you sure you want to restart ${container.name}?`,
      action: () => restartContainer(container.name),
      danger: false,
      loading: false,
    }
  }
  checkCriticalAndExecute(container, action, 'restart')
}

function promptRecreate(container) {
  const action = () => {
    recreateDialog.value = {
      open: true,
      container,
      pullImage: true,
      loading: false,
    }
  }
  checkCriticalAndExecute(container, action, 'recreate')
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

async function executeRecreate() {
  if (!recreateDialog.value.container) return
  recreateDialog.value.loading = true
  try {
    await containersStore.recreateContainer(
      recreateDialog.value.container.name,
      recreateDialog.value.pullImage
    )
    recreateDialog.value.open = false
  } finally {
    recreateDialog.value.loading = false
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

function openTerminal(container) {
  selectedContainer.value = container
  showTerminalModal.value = true
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
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
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

    <!-- Stats Cards (clickable for filtering) -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card
        class="cursor-pointer transition-all hover:ring-2 hover:ring-blue-500"
        :class="{ 'ring-2 ring-blue-500': statusFilter === 'all' }"
        @click="statusFilter = 'all'"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary">Total</p>
            <p class="text-2xl font-bold text-primary">{{ stats.total }}</p>
          </div>
          <ServerStackIcon class="h-8 w-8 text-blue-500" />
        </div>
      </Card>
      <Card
        class="cursor-pointer transition-all hover:ring-2 hover:ring-emerald-500"
        :class="{ 'ring-2 ring-emerald-500': statusFilter === 'running' }"
        @click="statusFilter = 'running'"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary">Running</p>
            <p class="text-2xl font-bold text-emerald-500">{{ stats.running }}</p>
          </div>
          <CheckCircleIcon class="h-8 w-8 text-emerald-500" />
        </div>
      </Card>
      <Card
        class="cursor-pointer transition-all hover:ring-2 hover:ring-gray-500"
        :class="{ 'ring-2 ring-gray-500': statusFilter === 'stopped' }"
        @click="statusFilter = 'stopped'"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-secondary">Stopped</p>
            <p class="text-2xl font-bold text-gray-500">{{ stats.stopped }}</p>
          </div>
          <XCircleIcon class="h-8 w-8 text-gray-400" />
        </div>
      </Card>
      <Card
        class="cursor-pointer transition-all hover:ring-2 hover:ring-red-500"
        :class="{ 'ring-2 ring-red-500': statusFilter === 'unhealthy' }"
        @click="statusFilter = 'unhealthy'"
      >
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

    <!-- Filter indicator -->
    <div v-if="statusFilter !== 'all'" class="flex items-center gap-2 text-sm text-secondary">
      <FunnelIcon class="h-4 w-4" />
      <span>
        Showing {{ filteredContainers.length }} {{ statusFilter }} container{{ filteredContainers.length !== 1 ? 's' : '' }}
      </span>
      <button @click="statusFilter = 'all'" class="text-blue-500 hover:underline">
        Clear filter
      </button>
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
      v-else-if="filteredContainers.length === 0"
      :icon="ServerStackIcon"
      :title="statusFilter === 'all' ? 'No containers found' : `No ${statusFilter} containers`"
      :description="statusFilter === 'all' ? 'No Docker containers were found on this system.' : `No containers with status '${statusFilter}' were found.`"
    >
      <template v-if="statusFilter !== 'all'" #action>
        <button @click="statusFilter = 'all'" class="btn-secondary">Show All Containers</button>
      </template>
    </EmptyState>

    <!-- Container List -->
    <div v-else class="space-y-3">
      <Card
        v-for="container in filteredContainers"
        :key="container.id"
        :padding="false"
        class="overflow-hidden"
        :class="{ 'border-l-4 border-l-amber-500': container.isCritical }"
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
            <div class="flex items-center gap-2">
              <div>
                <h3 class="font-medium text-primary flex items-center gap-2">
                  {{ container.name }}
                  <ShieldExclamationIcon
                    v-if="container.isCritical"
                    class="h-4 w-4 text-amber-500"
                    title="Critical container"
                  />
                </h3>
                <p class="text-xs text-muted">{{ container.image }}</p>
              </div>
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
                <div v-if="container.isCritical" class="flex justify-between">
                  <span class="text-secondary">Type:</span>
                  <span class="text-amber-500 font-medium">Critical</span>
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
                @click.stop="promptRecreate(container)"
                class="btn-secondary btn-sm flex items-center gap-1"
                title="Recreate container with latest image"
              >
                <ArrowPathRoundedSquareIcon class="h-4 w-4" />
                Recreate
              </button>
              <button
                @click.stop="viewLogs(container)"
                class="btn-secondary btn-sm flex items-center gap-1"
              >
                <DocumentTextIcon class="h-4 w-4" />
                Logs
              </button>
              <button
                v-if="container.status === 'running'"
                @click.stop="openTerminal(container)"
                class="btn-secondary btn-sm flex items-center gap-1"
                title="Open terminal in container"
              >
                <CommandLineIcon class="h-4 w-4" />
                Terminal
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

    <!-- Critical Container Warning Dialog -->
    <Modal v-model="criticalWarning.open" title="Critical Container Warning" size="md">
      <div class="space-y-4">
        <div class="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <ShieldExclamationIcon class="h-6 w-6 text-amber-500 flex-shrink-0" />
          <div>
            <h4 class="font-medium text-amber-800 dark:text-amber-200">Warning: Critical Container</h4>
            <p class="text-sm text-amber-700 dark:text-amber-300 mt-1">
              <strong>{{ criticalWarning.container?.name }}</strong> is a critical system container.
              Performing this action may affect system functionality.
            </p>
          </div>
        </div>
        <p class="text-secondary">
          Are you sure you want to <strong>{{ criticalWarning.actionName }}</strong> this container?
          This action could temporarily disrupt services.
        </p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <button @click="criticalWarning.open = false" class="btn-secondary">
            Cancel
          </button>
          <button @click="confirmCriticalAction" class="btn-warning">
            Yes, Continue
          </button>
        </div>
      </template>
    </Modal>

    <!-- Recreate Dialog -->
    <Modal v-model="recreateDialog.open" title="Recreate Container" size="md">
      <div class="space-y-4">
        <p class="text-secondary">
          This will stop the container, optionally pull the latest image, and recreate it with the same configuration.
        </p>
        <div class="p-4 bg-surface-secondary rounded-lg">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="font-medium text-primary">{{ recreateDialog.container?.name }}</h4>
              <p class="text-sm text-muted">{{ recreateDialog.container?.image }}</p>
            </div>
            <StatusBadge v-if="recreateDialog.container" :status="recreateDialog.container.status" />
          </div>
        </div>
        <label class="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            v-model="recreateDialog.pullImage"
            class="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div>
            <span class="text-primary">Pull latest image</span>
            <p class="text-xs text-muted">Download the newest version of the image before recreating</p>
          </div>
        </label>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <button @click="recreateDialog.open = false" class="btn-secondary" :disabled="recreateDialog.loading">
            Cancel
          </button>
          <button @click="executeRecreate" class="btn-primary flex items-center gap-2" :disabled="recreateDialog.loading">
            <ArrowPathIcon v-if="recreateDialog.loading" class="h-4 w-4 animate-spin" />
            <ArrowPathRoundedSquareIcon v-else class="h-4 w-4" />
            {{ recreateDialog.loading ? 'Recreating...' : 'Recreate Container' }}
          </button>
        </div>
      </template>
    </Modal>

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

    <!-- Terminal Modal -->
    <ContainerTerminal
      v-model="showTerminalModal"
      :container="selectedContainer"
    />
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
