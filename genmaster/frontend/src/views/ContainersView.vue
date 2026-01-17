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

<template>
  <MainLayout>
    <div class="space-y-6">
      <!-- Page header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Containers</h1>
          <p class="text-gray-600 dark:text-gray-400 mt-1">Manage Docker containers</p>
        </div>
        <div class="flex items-center space-x-3">
          <Toggle v-model="showAll" label="Show all" />
          <Button variant="secondary" @click="refresh">
            <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </Button>
        </div>
      </div>

      <!-- Error state -->
      <Card v-if="error">
        <div class="text-center py-8">
          <svg class="w-16 h-16 mx-auto text-red-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">{{ error }}</h3>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Make sure Docker is running and accessible.</p>
        </div>
      </Card>

      <!-- Loading state -->
      <div v-else-if="loading">
        <ContainerStackLoader />
      </div>

      <!-- Empty state -->
      <Card v-else-if="containers.length === 0">
        <div class="text-center py-12">
          <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">No containers found</h3>
          <p class="text-gray-500 dark:text-gray-400 mt-1">
            {{ showAll ? 'No Docker containers exist.' : 'No running containers. Enable "Show all" to see stopped containers.' }}
          </p>
        </div>
      </Card>

      <!-- Containers grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card v-for="container in containers" :key="container.id">
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center space-x-3">
              <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', getStatusBgClass(container.status)]">
                <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
              <div>
                <h3 class="font-medium text-gray-900 dark:text-white">{{ container.name }}</h3>
                <p class="text-xs text-gray-500 dark:text-gray-400">{{ container.id }}</p>
              </div>
            </div>
            <StatusBadge :status="getStatusColor(container.status)">
              {{ container.status }}
            </StatusBadge>
          </div>

          <div class="text-sm text-gray-500 dark:text-gray-400 space-y-1 mb-4">
            <p><span class="font-medium">Image:</span> {{ container.image }}</p>
            <p v-if="getContainerStats(container.name)">
              <span class="font-medium">CPU:</span> {{ getContainerStats(container.name)?.cpu_percent }}%
              <span class="mx-2">|</span>
              <span class="font-medium">RAM:</span> {{ getContainerStats(container.name)?.memory_usage_mb }}MB
            </p>
          </div>

          <div class="flex flex-wrap gap-2">
            <Button
              v-if="container.status !== 'running'"
              variant="success"
              size="sm"
              :disabled="actionLoading"
              @click="startContainer(container.name)"
            >
              Start
            </Button>
            <Button
              v-if="container.status === 'running'"
              variant="warning"
              size="sm"
              :disabled="actionLoading"
              @click="stopContainer(container.name)"
            >
              Stop
            </Button>
            <Button
              variant="secondary"
              size="sm"
              :disabled="actionLoading"
              @click="restartContainer(container.name)"
            >
              Restart
            </Button>
            <Button
              variant="ghost"
              size="sm"
              @click="viewLogs(container)"
            >
              Logs
            </Button>
            <Button
              v-if="container.status === 'running'"
              variant="ghost"
              size="sm"
              @click="openTerminal(container)"
            >
              <svg class="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Shell
            </Button>
          </div>
        </Card>
      </div>
    </div>

    <!-- Logs Modal -->
    <Modal v-model="showLogsModal" :title="`Logs: ${selectedContainer?.name}`" size="full">
      <div class="bg-gray-900 rounded-lg p-4 h-96 overflow-auto">
        <pre class="text-green-400 text-sm font-mono whitespace-pre-wrap">{{ containerLogs || 'No logs available' }}</pre>
      </div>
      <template #footer>
        <Button variant="secondary" @click="showLogsModal = false">Close</Button>
      </template>
    </Modal>

    <!-- Terminal Dialog -->
    <TerminalDialog
      v-model="showTerminal"
      :target="terminalTarget"
      :target-name="terminalTargetName"
      target-type="container"
    />
  </MainLayout>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useContainersStore } from '@/stores/containers'
import MainLayout from '@/components/layout/MainLayout.vue'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Toggle from '@/components/common/Toggle.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ContainerStackLoader from '@/components/common/ContainerStackLoader.vue'
import Modal from '@/components/common/Modal.vue'
import TerminalDialog from '@/components/terminal/TerminalDialog.vue'

const containersStore = useContainersStore()

const showAll = ref(false)
const showLogsModal = ref(false)
const selectedContainer = ref(null)
const containerLogs = ref('')

// Terminal state
const showTerminal = ref(false)
const terminalTarget = ref('')
const terminalTargetName = ref('')

const containers = ref([])
const loading = ref(true)
const actionLoading = ref(false)
const error = ref(null)

onMounted(async () => {
  await refresh()
})

watch(showAll, () => {
  refresh()
})

async function refresh() {
  loading.value = true
  error.value = null
  try {
    await containersStore.fetchContainers(showAll.value)
    await containersStore.fetchStats()
    containers.value = containersStore.containers
    error.value = containersStore.error
  } finally {
    loading.value = false
  }
}

function getStatusColor(status) {
  const colors = {
    running: 'success',
    exited: 'gray',
    paused: 'warning',
    restarting: 'info',
  }
  return colors[status] || 'gray'
}

function getStatusBgClass(status) {
  const classes = {
    running: 'bg-green-500',
    exited: 'bg-gray-500',
    paused: 'bg-amber-500',
    restarting: 'bg-blue-500',
  }
  return classes[status] || 'bg-gray-500'
}

function getContainerStats(name) {
  return containersStore.getContainerStats(name)
}

async function startContainer(name) {
  actionLoading.value = true
  try {
    await containersStore.startContainer(name)
  } finally {
    actionLoading.value = false
  }
}

async function stopContainer(name) {
  actionLoading.value = true
  try {
    await containersStore.stopContainer(name)
  } finally {
    actionLoading.value = false
  }
}

async function restartContainer(name) {
  actionLoading.value = true
  try {
    await containersStore.restartContainer(name)
  } finally {
    actionLoading.value = false
  }
}

async function viewLogs(container) {
  selectedContainer.value = container
  containerLogs.value = 'Loading...'
  showLogsModal.value = true

  const logs = await containersStore.getContainerLogs(container.name)
  containerLogs.value = logs || 'No logs available'
}

function openTerminal(container) {
  terminalTarget.value = container.name
  terminalTargetName.value = container.name
  showTerminal.value = true
}
</script>
