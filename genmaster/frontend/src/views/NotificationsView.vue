<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/NotificationsView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import notificationsService from '@/services/notifications'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'
import Modal from '@/components/common/Modal.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import {
  BellIcon,
  BellSlashIcon,
  EnvelopeIcon,
  UserGroupIcon,
  PlusIcon,
  PencilSquareIcon,
  TrashIcon,
  PlayIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  CheckIcon,
  XMarkIcon,
  ClockIcon,
  PaperAirplaneIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  HashtagIcon,
} from '@heroicons/vue/24/outline'

const notifications = useNotificationStore()

// Main tab navigation
const mainTab = ref('channels')
const mainTabs = [
  { id: 'channels', name: 'Channels', icon: BellIcon, iconColor: 'text-blue-500', bgActive: 'bg-blue-500/15 dark:bg-blue-500/20', textActive: 'text-blue-700 dark:text-blue-400', borderActive: 'border-blue-500/30' },
  { id: 'groups', name: 'Groups', icon: HashtagIcon, iconColor: 'text-purple-500', bgActive: 'bg-purple-500/15 dark:bg-purple-500/20', textActive: 'text-purple-700 dark:text-purple-400', borderActive: 'border-purple-500/30' },
  { id: 'history', name: 'History', icon: ClockIcon, iconColor: 'text-amber-500', bgActive: 'bg-amber-500/15 dark:bg-amber-500/20', textActive: 'text-amber-700 dark:text-amber-400', borderActive: 'border-amber-500/30' },
]

// Loading state
const loading = ref(true)
const loadingError = ref(null)

// Fun loading messages
const allLoadingMessages = [
  'Ringing all the bells...',
  'Waking up the notification fairies...',
  'Checking who wants to be disturbed...',
  'Polishing the alert buttons...',
  'Making sure no alerts got lost...',
  'Loading carrier pigeons as backup...',
  'Ensuring smoke signals are calibrated...',
  'Testing if anyone\'s listening...',
  'Warming up the alert sirens...',
  'Organizing the notification queue...',
  'Preparing the royal trumpet fanfare...',
  'Tuning the alert frequencies...',
]
const loadingMessages = ref([])
const loadingMessageIndex = ref(0)
let loadingInterval = null

function shuffleLoadingMessages() {
  const shuffled = [...allLoadingMessages].sort(() => Math.random() - 0.5)
  loadingMessages.value = shuffled.slice(0, 8)
}

// Data
const channels = ref([])
const groups = ref([])
const history = ref([])

// Collapsible sections
const channelsExpanded = ref(true)
const groupsExpanded = ref(true)
const historyExpanded = ref(true)

// Testing state
const testingChannelId = ref(null)

// Modals
const showChannelModal = ref(false)
const showGroupModal = ref(false)
const showDeleteConfirm = ref(false)

const editingChannel = ref(null)
const editingGroup = ref(null)
const deletingItem = ref(null)
const deleteType = ref(null)
const saving = ref(false)
const deleting = ref(false)

// Form defaults
const defaultChannelForm = {
  name: '',
  channel_type: 'apprise',
  config: { url: '', use_tls: true },
  description: '',
  enabled: true,
}

const defaultGroupForm = {
  name: '',
  description: '',
  channel_ids: [],
  enabled: true,
}

const channelForm = ref({ ...defaultChannelForm })
const groupForm = ref({ ...defaultGroupForm })
const toAddressesInput = ref('')

// Stats computed with defensive array checks
const stats = computed(() => {
  const channelsList = Array.isArray(channels.value) ? channels.value : []
  const groupsList = Array.isArray(groups.value) ? groups.value : []
  const historyList = Array.isArray(history.value) ? history.value : []
  const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000
  return {
    total: channelsList.length,
    active: channelsList.filter(c => c.enabled).length,
    groups: groupsList.length,
    recentSent: historyList.filter(h => new Date(h.sent_at).getTime() > oneDayAgo).length,
    sent: historyList.filter(h => h.success).length,
    failed: historyList.filter(h => !h.success).length,
  }
})

// Lifecycle
onMounted(async () => {
  shuffleLoadingMessages()
  loadingMessageIndex.value = 0
  loadingInterval = setInterval(() => {
    loadingMessageIndex.value = (loadingMessageIndex.value + 1) % loadingMessages.value.length
  }, 2000)

  await loadData()
})

onUnmounted(() => {
  if (loadingInterval) {
    clearInterval(loadingInterval)
  }
})

// Methods
async function loadData() {
  loading.value = true
  loadingError.value = null

  try {
    const [channelsData, groupsData, historyData] = await Promise.all([
      notificationsService.getChannels(),
      notificationsService.getGroups(),
      notificationsService.getHistory(50),
    ])
    // Ensure we always have arrays
    channels.value = Array.isArray(channelsData) ? channelsData : []
    groups.value = Array.isArray(groupsData) ? groupsData : []
    history.value = Array.isArray(historyData) ? historyData : []
  } catch (error) {
    console.error('Failed to load notifications data:', error)
    loadingError.value = error.response?.data?.detail || error.message || 'Failed to load notification data'
    notifications.error(loadingError.value)
    // Reset to empty arrays on error
    channels.value = []
    groups.value = []
    history.value = []
  } finally {
    if (loadingInterval) {
      clearInterval(loadingInterval)
      loadingInterval = null
    }
    loading.value = false
  }
}

function formatDate(dateStr) {
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
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatEventType(eventType) {
  if (!eventType) return 'Unknown'
  const labels = {
    generator_started: 'Generator Started',
    generator_stopped: 'Generator Stopped',
    generator_failed: 'Generator Failed',
    heartbeat_lost: 'Heartbeat Lost',
    heartbeat_restored: 'Heartbeat Restored',
    failsafe_triggered: 'Failsafe Triggered',
    schedule_executed: 'Schedule Executed',
    system_warning: 'System Warning',
    system_error: 'System Error',
    test: 'Test',
  }
  return labels[eventType] || eventType
}

// Channel methods
function openChannelModal(channel = null) {
  if (channel) {
    editingChannel.value = channel
    channelForm.value = {
      name: channel.name,
      channel_type: channel.channel_type,
      config: { ...channel.config },
      description: channel.description || '',
      enabled: channel.enabled,
    }
    if (channel.channel_type === 'email' && channel.config.to_addresses) {
      toAddressesInput.value = Array.isArray(channel.config.to_addresses)
        ? channel.config.to_addresses.join(', ')
        : channel.config.to_addresses
    }
  } else {
    editingChannel.value = null
    channelForm.value = { ...defaultChannelForm, config: { url: '', use_tls: true } }
    toAddressesInput.value = ''
  }
  showChannelModal.value = true
}

async function saveChannel() {
  if (channelForm.value.channel_type === 'email') {
    channelForm.value.config.to_addresses = toAddressesInput.value
      .split(',')
      .map(e => e.trim())
      .filter(e => e)
  }

  saving.value = true
  try {
    if (editingChannel.value) {
      await notificationsService.updateChannel(editingChannel.value.id, channelForm.value)
      notifications.success('Channel updated successfully')
    } else {
      await notificationsService.createChannel(channelForm.value)
      notifications.success('Channel created successfully')
    }
    showChannelModal.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to save channel:', error)
    const message = error.response?.data?.detail || 'Failed to save channel'
    notifications.error(message)
  } finally {
    saving.value = false
  }
}

async function testChannel(channel) {
  testingChannelId.value = channel.id
  try {
    const result = await notificationsService.testChannel(channel.id, {
      title: 'Test Notification',
      message: `This is a test notification from GenMaster sent to "${channel.name}" channel.`,
    })
    if (result.success) {
      notifications.success('Test notification sent successfully!')
    } else {
      notifications.error(result.error || 'Test notification failed')
    }
    // Refresh history
    history.value = await notificationsService.getHistory(50)
  } catch (error) {
    console.error('Failed to test channel:', error)
    notifications.error('Failed to send test notification')
  } finally {
    testingChannelId.value = null
  }
}

async function toggleChannel(channel) {
  try {
    await notificationsService.toggleChannel(channel.id)
    channel.enabled = !channel.enabled
    notifications.success(`Channel ${channel.enabled ? 'enabled' : 'disabled'}`)
  } catch (error) {
    console.error('Failed to toggle channel:', error)
    notifications.error('Failed to update channel')
  }
}

function confirmDeleteChannel(channel) {
  deletingItem.value = channel
  deleteType.value = 'channel'
  showDeleteConfirm.value = true
}

// Group methods
function openGroupModal(group = null) {
  if (group) {
    editingGroup.value = group
    groupForm.value = {
      name: group.name,
      description: group.description || '',
      channel_ids: group.channels.map(c => c.id),
      enabled: group.enabled,
    }
  } else {
    editingGroup.value = null
    groupForm.value = { ...defaultGroupForm, channel_ids: [] }
  }
  showGroupModal.value = true
}

async function saveGroup() {
  saving.value = true
  try {
    if (editingGroup.value) {
      await notificationsService.updateGroup(editingGroup.value.id, groupForm.value)
      notifications.success('Group updated successfully')
    } else {
      await notificationsService.createGroup(groupForm.value)
      notifications.success('Group created successfully')
    }
    showGroupModal.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to save group:', error)
    const message = error.response?.data?.detail || 'Failed to save group'
    notifications.error(message)
  } finally {
    saving.value = false
  }
}

function confirmDeleteGroup(group) {
  deletingItem.value = group
  deleteType.value = 'group'
  showDeleteConfirm.value = true
}

// Delete
async function executeDelete() {
  deleting.value = true
  try {
    if (deleteType.value === 'channel') {
      await notificationsService.deleteChannel(deletingItem.value.id)
      notifications.success('Channel deleted successfully')
    } else {
      await notificationsService.deleteGroup(deletingItem.value.id)
      notifications.success('Group deleted successfully')
    }
    showDeleteConfirm.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to delete:', error)
    notifications.error('Failed to delete')
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-primary">Notifications</h1>
        <p class="text-secondary mt-1">Configure Apprise notification channels and groups</p>
      </div>
      <button
        v-if="mainTab === 'channels' && !loading && channels.length > 0"
        @click="openChannelModal()"
        class="btn-primary flex items-center gap-2"
      >
        <PlusIcon class="h-4 w-4" />
        Add Channel
      </button>
      <button
        v-else-if="mainTab === 'groups' && !loading && channels.length > 0"
        @click="openGroupModal()"
        class="btn-primary flex items-center gap-2"
      >
        <PlusIcon class="h-4 w-4" />
        Add Group
      </button>
      <button
        v-else-if="!loading"
        @click="loadData"
        class="btn-secondary flex items-center gap-2"
      >
        <ArrowPathIcon class="h-4 w-4" />
        Refresh
      </button>
    </div>

    <!-- Main Tab Navigation -->
    <div class="flex flex-wrap gap-2 pb-4 border-b border-gray-400 dark:border-gray-700">
      <button
        v-for="tab in mainTabs"
        :key="tab.id"
        @click="mainTab = tab.id"
        :class="[
          'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap border',
          mainTab === tab.id
            ? `${tab.bgActive} ${tab.textActive} ${tab.borderActive}`
            : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50 border-transparent'
        ]"
      >
        <component :is="tab.icon" :class="['h-4 w-4', mainTab === tab.id ? '' : tab.iconColor]" />
        {{ tab.name }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="py-16 flex flex-col items-center justify-center">
      <div class="relative">
        <div class="notification-bell">
          <BellIcon class="h-12 w-12 text-blue-500 animate-bounce" />
        </div>
      </div>
      <p class="mt-6 text-sm font-medium text-secondary">{{ loadingMessages[loadingMessageIndex] || 'Loading notifications...' }}</p>
      <p class="mt-1 text-xs text-muted">Fetching notification channels</p>
    </div>

    <!-- Error State -->
    <Card v-else-if="loadingError" class="text-center py-12">
      <div class="p-4 rounded-full bg-red-100 dark:bg-red-500/20 inline-block mb-4">
        <XMarkIcon class="w-12 h-12 text-red-500" />
      </div>
      <h3 class="text-lg font-medium text-primary">Failed to Load Notifications</h3>
      <p class="text-secondary mt-1 mb-4">{{ loadingError }}</p>
      <Button variant="primary" @click="loadData">
        <ArrowPathIcon class="w-5 h-5 mr-2" />
        Try Again
      </Button>
    </Card>

    <!-- Content -->
    <template v-else>
      <!-- Stats Grid -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card :padding="false">
          <div class="p-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                <BellIcon class="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Total Channels</p>
                <p class="text-xl font-bold text-primary">{{ stats.total }}</p>
              </div>
            </div>
          </div>
        </Card>

        <Card :padding="false">
          <div class="p-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-500/20">
                <CheckCircleIcon class="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Active</p>
                <p class="text-xl font-bold text-primary">{{ stats.active }}</p>
              </div>
            </div>
          </div>
        </Card>

        <Card :padding="false">
          <div class="p-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-500/20">
                <HashtagIcon class="h-5 w-5 text-purple-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Groups</p>
                <p class="text-xl font-bold text-primary">{{ stats.groups }}</p>
              </div>
            </div>
          </div>
        </Card>

        <Card :padding="false">
          <div class="p-4">
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-amber-100 dark:bg-amber-500/20">
                <PaperAirplaneIcon class="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p class="text-sm text-secondary">Sent (24h)</p>
                <p class="text-xl font-bold text-primary">{{ stats.recentSent }}</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- Channels Tab -->
      <template v-if="mainTab === 'channels'">
        <Card :padding="false">
          <div
            @click="channelsExpanded = !channelsExpanded"
            class="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                <BellIcon class="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <h3 class="font-semibold text-primary">Notification Channels</h3>
                <p class="text-sm text-secondary">Configure where alerts are sent</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs px-2 py-1 rounded-full bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300">
                {{ channels.length }} channel{{ channels.length !== 1 ? 's' : '' }}
              </span>
              <ChevronDownIcon v-if="channelsExpanded" class="h-5 w-5 text-secondary" />
              <ChevronRightIcon v-else class="h-5 w-5 text-secondary" />
            </div>
          </div>

          <Transition name="collapse">
            <div v-if="channelsExpanded" class="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
              <!-- Empty State -->
              <EmptyState
                v-if="channels.length === 0"
                :icon="BellSlashIcon"
                title="No channels configured"
                description="Add a notification channel to start receiving alerts."
                action-text="Add Channel"
                @action="openChannelModal()"
                class="pt-4"
              >
                <!-- Apprise Examples -->
                <div class="mt-6 text-left max-w-2xl mx-auto">
                  <h4 class="text-sm font-semibold text-primary mb-3">Popular Apprise URL Examples:</h4>
                  <div class="space-y-2 text-sm">
                    <div class="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <code class="text-blue-600 dark:text-blue-400">discord://webhook_id/webhook_token</code>
                      <p class="text-muted text-xs mt-1">Discord webhook</p>
                    </div>
                    <div class="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <code class="text-blue-600 dark:text-blue-400">tgram://bot_token/chat_id</code>
                      <p class="text-muted text-xs mt-1">Telegram bot</p>
                    </div>
                    <div class="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <code class="text-blue-600 dark:text-blue-400">slack://token_a/token_b/token_c</code>
                      <p class="text-muted text-xs mt-1">Slack webhook</p>
                    </div>
                    <div class="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <code class="text-blue-600 dark:text-blue-400">pover://user@token</code>
                      <p class="text-muted text-xs mt-1">Pushover</p>
                    </div>
                  </div>
                  <p class="text-xs text-muted mt-3">
                    See <a href="https://github.com/caronc/apprise/wiki" target="_blank" class="text-primary-600 hover:underline">Apprise documentation</a> for all supported services.
                  </p>
                </div>
              </EmptyState>

              <!-- Channels List -->
              <div v-else class="space-y-2 pt-3">
                <div
                  v-for="channel in channels"
                  :key="channel.id"
                  class="flex items-center justify-between p-4 rounded-lg bg-surface-hover border border-gray-200 dark:border-gray-700"
                >
                  <div class="flex items-center space-x-4">
                    <div :class="['p-2.5 rounded-xl flex-shrink-0', channel.enabled ? 'bg-blue-100 dark:bg-blue-500/20' : 'bg-gray-100 dark:bg-gray-600']">
                      <BellIcon v-if="channel.channel_type === 'apprise'" :class="['w-5 h-5', channel.enabled ? 'text-blue-600' : 'text-gray-400']" />
                      <EnvelopeIcon v-else :class="['w-5 h-5', channel.enabled ? 'text-blue-600' : 'text-gray-400']" />
                    </div>
                    <div>
                      <h4 class="font-semibold text-primary">{{ channel.name }}</h4>
                      <p class="text-sm text-secondary">
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 mr-2">
                          {{ channel.channel_type === 'apprise' ? 'Apprise' : 'Email' }}
                        </span>
                        <span v-if="channel.description" class="text-muted">{{ channel.description }}</span>
                      </p>
                    </div>
                  </div>
                  <div class="flex items-center space-x-2">
                    <StatusBadge :status="channel.enabled ? 'success' : 'gray'">
                      {{ channel.enabled ? 'Active' : 'Disabled' }}
                    </StatusBadge>
                    <button
                      class="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-500/10 rounded-lg transition-colors"
                      @click="testChannel(channel)"
                      :disabled="testingChannelId === channel.id"
                      title="Send test notification"
                    >
                      <ArrowPathIcon v-if="testingChannelId === channel.id" class="w-5 h-5 animate-spin" />
                      <PlayIcon v-else class="w-5 h-5" />
                    </button>
                    <button
                      class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg transition-colors"
                      @click="openChannelModal(channel)"
                      title="Edit channel"
                    >
                      <PencilSquareIcon class="w-5 h-5" />
                    </button>
                    <button
                      class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
                      @click="confirmDeleteChannel(channel)"
                      title="Delete channel"
                    >
                      <TrashIcon class="w-5 h-5" />
                    </button>
                    <!-- Toggle Switch -->
                    <label class="relative inline-flex items-center cursor-pointer ml-2">
                      <input
                        type="checkbox"
                        :checked="channel.enabled"
                        @change.stop="toggleChannel(channel)"
                        class="sr-only peer"
                      />
                      <div
                        class="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-500"
                      ></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </Card>
      </template>

      <!-- Groups Tab -->
      <template v-if="mainTab === 'groups'">
        <Card :padding="false">
          <div
            @click="groupsExpanded = !groupsExpanded"
            class="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-500/20">
                <HashtagIcon class="h-5 w-5 text-purple-500" />
              </div>
              <div>
                <h3 class="font-semibold text-primary">Notification Groups</h3>
                <p class="text-sm text-secondary">Send to multiple channels at once</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs px-2 py-1 rounded-full bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300">
                {{ groups.length }} group{{ groups.length !== 1 ? 's' : '' }}
              </span>
              <ChevronDownIcon v-if="groupsExpanded" class="h-5 w-5 text-secondary" />
              <ChevronRightIcon v-else class="h-5 w-5 text-secondary" />
            </div>
          </div>

          <Transition name="collapse">
            <div v-if="groupsExpanded" class="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
              <p v-if="channels.length === 0" class="text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 p-3 rounded-lg mt-3">
                Create at least one channel before creating groups.
              </p>

              <!-- Empty State -->
              <EmptyState
                v-else-if="groups.length === 0"
                :icon="UserGroupIcon"
                title="No groups configured"
                description="Groups let you send notifications to multiple channels at once."
                action-text="Create Group"
                @action="openGroupModal()"
                class="pt-4"
              />

              <!-- Groups List -->
              <div v-else class="space-y-3 pt-3">
                <div
                  v-for="group in groups"
                  :key="group.id"
                  class="bg-surface-hover rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
                >
                  <div class="flex items-center justify-between p-4">
                    <div class="flex items-center space-x-4">
                      <div :class="['p-2.5 rounded-xl flex-shrink-0', group.enabled ? 'bg-purple-100 dark:bg-purple-500/20' : 'bg-gray-100 dark:bg-gray-600']">
                        <HashtagIcon :class="['w-5 h-5', group.enabled ? 'text-purple-600' : 'text-gray-400']" />
                      </div>
                      <div>
                        <h4 class="font-semibold text-primary">{{ group.name }}</h4>
                        <p class="text-sm text-secondary">
                          {{ group.channels.length }} channel{{ group.channels.length !== 1 ? 's' : '' }}
                          <span v-if="group.description" class="text-muted ml-2">- {{ group.description }}</span>
                        </p>
                      </div>
                    </div>
                    <div class="flex items-center space-x-2">
                      <StatusBadge :status="group.enabled ? 'success' : 'gray'">
                        {{ group.enabled ? 'Active' : 'Disabled' }}
                      </StatusBadge>
                      <button
                        class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg transition-colors"
                        @click="openGroupModal(group)"
                        title="Edit group"
                      >
                        <PencilSquareIcon class="w-5 h-5" />
                      </button>
                      <button
                        class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-lg transition-colors"
                        @click="confirmDeleteGroup(group)"
                        title="Delete group"
                      >
                        <TrashIcon class="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  <div v-if="group.channels.length > 0" class="px-4 pb-4">
                    <div class="flex flex-wrap gap-2">
                      <span
                        v-for="ch in group.channels"
                        :key="ch.id"
                        class="inline-flex items-center px-3 py-1 text-sm font-medium rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                      >
                        <BellIcon v-if="ch.channel_type === 'apprise'" class="w-3.5 h-3.5 mr-1.5" />
                        <EnvelopeIcon v-else class="w-3.5 h-3.5 mr-1.5" />
                        {{ ch.name }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </Card>
      </template>

      <!-- History Tab -->
      <template v-if="mainTab === 'history'">
        <Card :padding="false">
          <div
            @click="historyExpanded = !historyExpanded"
            class="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <div class="flex items-center gap-3">
              <div class="p-2 rounded-lg bg-amber-100 dark:bg-amber-500/20">
                <ClockIcon class="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <h3 class="font-semibold text-primary">Notification History</h3>
                <p class="text-sm text-secondary">Recent notifications sent</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs px-2 py-1 rounded-full bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300">
                {{ history.length }} total
              </span>
              <ChevronDownIcon v-if="historyExpanded" class="h-5 w-5 text-secondary" />
              <ChevronRightIcon v-else class="h-5 w-5 text-secondary" />
            </div>
          </div>

          <Transition name="collapse">
            <div v-if="historyExpanded" class="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
              <!-- Empty State -->
              <EmptyState
                v-if="history.length === 0"
                :icon="ClockIcon"
                title="No notifications sent yet"
                description="Notification history will appear here when events trigger alerts."
                class="pt-4"
              />

              <!-- History List -->
              <div v-else class="space-y-2 pt-3">
                <div
                  v-for="item in history"
                  :key="item.id"
                  class="flex items-center justify-between p-4 bg-surface-hover rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div class="flex items-center space-x-3">
                    <div :class="['w-10 h-10 rounded-full flex items-center justify-center', item.success ? 'bg-green-100 dark:bg-green-500/20' : 'bg-red-100 dark:bg-red-500/20']">
                      <CheckIcon v-if="item.success" class="w-5 h-5 text-green-600" />
                      <XMarkIcon v-else class="w-5 h-5 text-red-600" />
                    </div>
                    <div>
                      <p class="font-medium text-primary">{{ item.title }}</p>
                      <p class="text-sm text-secondary">
                        <span class="font-medium">{{ item.channel_name || 'Unknown' }}</span>
                        <span class="mx-2 text-muted">-</span>
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                          {{ formatEventType(item.event_type) }}
                        </span>
                      </p>
                    </div>
                  </div>
                  <div class="text-right">
                    <p class="text-sm text-secondary">{{ formatDate(item.sent_at) }}</p>
                    <p v-if="item.error_message" class="text-xs text-red-500 truncate max-w-xs mt-1">{{ item.error_message }}</p>
                  </div>
                </div>
              </div>
            </div>
          </Transition>
        </Card>
      </template>
    </template>

    <!-- Channel Modal -->
    <Modal v-model="showChannelModal" :title="editingChannel ? 'Edit Channel' : 'Add Notification Channel'" size="lg">
      <form @submit.prevent="saveChannel" class="space-y-5">
        <Input v-model="channelForm.name" label="Channel Name" placeholder="Discord Alerts" required />

        <div>
          <label class="label mb-2">Channel Type</label>
          <div class="flex space-x-4">
            <label class="flex items-center p-3 rounded-lg border-2 cursor-pointer transition-colors" :class="channelForm.channel_type === 'apprise' ? 'border-primary-500 bg-primary-50 dark:bg-primary-500/10' : 'border-gray-200 dark:border-gray-700'">
              <input type="radio" v-model="channelForm.channel_type" value="apprise" class="sr-only" />
              <BellIcon class="w-5 h-5 mr-2" :class="channelForm.channel_type === 'apprise' ? 'text-primary-600' : 'text-gray-400'" />
              <span :class="channelForm.channel_type === 'apprise' ? 'text-primary-700 dark:text-primary-300 font-medium' : 'text-secondary'">Apprise</span>
            </label>
            <label class="flex items-center p-3 rounded-lg border-2 cursor-pointer transition-colors" :class="channelForm.channel_type === 'email' ? 'border-primary-500 bg-primary-50 dark:bg-primary-500/10' : 'border-gray-200 dark:border-gray-700'">
              <input type="radio" v-model="channelForm.channel_type" value="email" class="sr-only" />
              <EnvelopeIcon class="w-5 h-5 mr-2" :class="channelForm.channel_type === 'email' ? 'text-primary-600' : 'text-gray-400'" />
              <span :class="channelForm.channel_type === 'email' ? 'text-primary-700 dark:text-primary-300 font-medium' : 'text-secondary'">Email</span>
            </label>
          </div>
        </div>

        <!-- Apprise Config -->
        <div v-if="channelForm.channel_type === 'apprise'" class="space-y-4">
          <div>
            <Input
              v-model="channelForm.config.url"
              label="Apprise URL"
              placeholder="discord://webhook_id/webhook_token"
              required
            />
            <div class="mt-2 p-3 bg-blue-50 dark:bg-blue-500/10 rounded-lg">
              <p class="text-xs text-blue-700 dark:text-blue-300">
                <strong>Examples:</strong> discord://, tgram://, slack://, pover://, mailto://
                <br />
                See <a href="https://github.com/caronc/apprise/wiki" target="_blank" class="underline">Apprise Wiki</a> for all supported services and URL formats.
              </p>
            </div>
          </div>
        </div>

        <!-- Email Config -->
        <div v-if="channelForm.channel_type === 'email'" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <Input v-model="channelForm.config.smtp_host" label="SMTP Host" placeholder="smtp.gmail.com" required />
            <Input v-model="channelForm.config.smtp_port" type="number" label="SMTP Port" placeholder="587" required />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <Input v-model="channelForm.config.username" label="Username" placeholder="your@email.com" required />
            <Input v-model="channelForm.config.password" type="password" label="Password" placeholder="********" :required="!editingChannel" />
          </div>
          <Input v-model="channelForm.config.from_address" label="From Address" placeholder="genmaster@example.com" required />
          <Input v-model="toAddressesInput" label="To Addresses" placeholder="admin@example.com, alerts@example.com" required />
          <div class="flex items-center">
            <Toggle v-model="channelForm.config.use_tls" label="Use TLS encryption" />
          </div>
        </div>

        <Input v-model="channelForm.description" label="Description (optional)" placeholder="Alerts for critical generator events" />

        <div class="flex items-center">
          <Toggle v-model="channelForm.enabled" label="Enable this channel" />
        </div>
      </form>

      <template #footer>
        <Button variant="secondary" @click="showChannelModal = false">Cancel</Button>
        <Button variant="primary" @click="saveChannel" :loading="saving">
          {{ editingChannel ? 'Update Channel' : 'Create Channel' }}
        </Button>
      </template>
    </Modal>

    <!-- Group Modal -->
    <Modal v-model="showGroupModal" :title="editingGroup ? 'Edit Group' : 'Create Notification Group'" size="lg">
      <form @submit.prevent="saveGroup" class="space-y-5">
        <Input v-model="groupForm.name" label="Group Name" placeholder="Critical Alerts" required />
        <Input v-model="groupForm.description" label="Description (optional)" placeholder="All critical notification channels" />

        <div>
          <label class="label mb-2">Select Channels</label>
          <div class="space-y-2 max-h-64 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg p-2">
            <label
              v-for="channel in channels"
              :key="channel.id"
              class="flex items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
              :class="groupForm.channel_ids.includes(channel.id) ? 'bg-primary-50 dark:bg-primary-500/10' : ''"
            >
              <input
                type="checkbox"
                :value="channel.id"
                v-model="groupForm.channel_ids"
                class="form-checkbox text-primary-600 rounded"
              />
              <div class="ml-3 flex items-center">
                <BellIcon v-if="channel.channel_type === 'apprise'" class="w-4 h-4 text-gray-400 mr-2" />
                <EnvelopeIcon v-else class="w-4 h-4 text-gray-400 mr-2" />
                <span class="font-medium text-primary">{{ channel.name }}</span>
                <span class="ml-2 text-xs text-muted">({{ channel.channel_type }})</span>
              </div>
            </label>
          </div>
          <p v-if="groupForm.channel_ids.length === 0" class="text-xs text-amber-600 mt-2">Select at least one channel</p>
        </div>

        <div class="flex items-center">
          <Toggle v-model="groupForm.enabled" label="Enable this group" />
        </div>
      </form>

      <template #footer>
        <Button variant="secondary" @click="showGroupModal = false">Cancel</Button>
        <Button variant="primary" @click="saveGroup" :loading="saving" :disabled="groupForm.channel_ids.length === 0">
          {{ editingGroup ? 'Update Group' : 'Create Group' }}
        </Button>
      </template>
    </Modal>

    <!-- Delete Confirmation Modal -->
    <Modal v-model="showDeleteConfirm" title="Confirm Delete">
      <p class="text-secondary">
        Are you sure you want to delete "<strong class="text-primary">{{ deletingItem?.name }}</strong>"?
        This action cannot be undone.
      </p>
      <template #footer>
        <Button variant="secondary" @click="showDeleteConfirm = false">Cancel</Button>
        <Button variant="danger" @click="executeDelete" :loading="deleting">Delete</Button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  max-height: 0;
}

.collapse-enter-to,
.collapse-leave-from {
  opacity: 1;
  max-height: 2000px;
}
</style>
