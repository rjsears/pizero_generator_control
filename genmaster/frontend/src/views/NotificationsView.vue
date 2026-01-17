<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/NotificationsView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 17th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Notifications</h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">Manage notification channels and groups</p>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <div class="text-center">
          <p class="text-sm text-gray-500 dark:text-gray-400">Total Channels</p>
          <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ channels.length }}</p>
        </div>
      </Card>
      <Card>
        <div class="text-center">
          <p class="text-sm text-gray-500 dark:text-gray-400">Active Channels</p>
          <p class="text-2xl font-bold text-green-600">{{ activeChannels }}</p>
        </div>
      </Card>
      <Card>
        <div class="text-center">
          <p class="text-sm text-gray-500 dark:text-gray-400">Groups</p>
          <p class="text-2xl font-bold text-blue-600">{{ groups.length }}</p>
        </div>
      </Card>
      <Card>
        <div class="text-center">
          <p class="text-sm text-gray-500 dark:text-gray-400">Recent Sent</p>
          <p class="text-2xl font-bold text-purple-600">{{ recentSentCount }}</p>
        </div>
      </Card>
    </div>

    <!-- Tabs -->
    <Card>
      <div class="border-b border-gray-200 dark:border-gray-700">
        <nav class="-mb-px flex space-x-8">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === tab.id
                ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300',
            ]"
            @click="activeTab = tab.id"
          >
            {{ tab.name }}
          </button>
        </nav>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="py-12 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p class="mt-2 text-gray-500 dark:text-gray-400">Loading...</p>
      </div>

      <!-- Channels Tab -->
      <div v-else-if="activeTab === 'channels'" class="py-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Notification Channels</h3>
          <Button variant="primary" @click="openChannelModal()">
            <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Channel
          </Button>
        </div>

        <!-- Empty State -->
        <div v-if="channels.length === 0" class="text-center py-12">
          <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">No channels configured</h3>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Add a notification channel to get started.</p>
        </div>

        <!-- Channels List -->
        <div v-else class="space-y-3">
          <div
            v-for="channel in channels"
            :key="channel.id"
            class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
          >
            <div class="flex items-center space-x-4">
              <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', channel.enabled ? 'bg-green-100 dark:bg-green-900' : 'bg-gray-100 dark:bg-gray-600']">
                <svg v-if="channel.channel_type === 'apprise'" class="w-5 h-5" :class="channel.enabled ? 'text-green-600' : 'text-gray-400'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                <svg v-else class="w-5 h-5" :class="channel.enabled ? 'text-green-600' : 'text-gray-400'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <h4 class="font-medium text-gray-900 dark:text-white">{{ channel.name }}</h4>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  {{ channel.channel_type === 'apprise' ? 'Apprise' : 'Email' }}
                  <span v-if="channel.description"> - {{ channel.description }}</span>
                </p>
              </div>
            </div>
            <div class="flex items-center space-x-3">
              <StatusBadge :status="channel.enabled ? 'success' : 'gray'">
                {{ channel.enabled ? 'Active' : 'Disabled' }}
              </StatusBadge>
              <button class="p-2 text-gray-400 hover:text-blue-600" @click="testChannel(channel)" title="Test">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                </svg>
              </button>
              <button class="p-2 text-gray-400 hover:text-gray-600" @click="openChannelModal(channel)" title="Edit">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button class="p-2 text-gray-400 hover:text-red-600" @click="confirmDeleteChannel(channel)" title="Delete">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Groups Tab -->
      <div v-else-if="activeTab === 'groups'" class="py-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">Notification Groups</h3>
          <Button variant="primary" @click="openGroupModal()" :disabled="channels.length === 0">
            <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Group
          </Button>
        </div>

        <!-- Empty State -->
        <div v-if="groups.length === 0" class="text-center py-12">
          <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">No groups configured</h3>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Groups allow you to send notifications to multiple channels at once.</p>
        </div>

        <!-- Groups List -->
        <div v-else class="space-y-3">
          <div
            v-for="group in groups"
            :key="group.id"
            class="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-4">
                <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', group.enabled ? 'bg-blue-100 dark:bg-blue-900' : 'bg-gray-100 dark:bg-gray-600']">
                  <svg class="w-5 h-5" :class="group.enabled ? 'text-blue-600' : 'text-gray-400'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <div>
                  <h4 class="font-medium text-gray-900 dark:text-white">{{ group.name }}</h4>
                  <p class="text-sm text-gray-500 dark:text-gray-400">
                    {{ group.channels.length }} channel{{ group.channels.length !== 1 ? 's' : '' }}
                    <span v-if="group.description"> - {{ group.description }}</span>
                  </p>
                </div>
              </div>
              <div class="flex items-center space-x-3">
                <StatusBadge :status="group.enabled ? 'success' : 'gray'">
                  {{ group.enabled ? 'Active' : 'Disabled' }}
                </StatusBadge>
                <button class="p-2 text-gray-400 hover:text-gray-600" @click="openGroupModal(group)" title="Edit">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button class="p-2 text-gray-400 hover:text-red-600" @click="confirmDeleteGroup(group)" title="Delete">
                  <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
            <!-- Channel badges -->
            <div v-if="group.channels.length > 0" class="mt-3 flex flex-wrap gap-2">
              <span
                v-for="ch in group.channels"
                :key="ch.id"
                class="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300"
              >
                {{ ch.name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- History Tab -->
      <div v-else-if="activeTab === 'history'" class="py-6">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Notification History</h3>

        <!-- Empty State -->
        <div v-if="history.length === 0" class="text-center py-12">
          <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">No notifications sent yet</h3>
          <p class="text-gray-500 dark:text-gray-400 mt-1">Notification history will appear here.</p>
        </div>

        <!-- History List -->
        <div v-else class="space-y-2">
          <div
            v-for="item in history"
            :key="item.id"
            class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
          >
            <div class="flex items-center space-x-3">
              <div :class="['w-8 h-8 rounded-full flex items-center justify-center', item.success ? 'bg-green-100' : 'bg-red-100']">
                <svg v-if="item.success" class="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <svg v-else class="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <div>
                <p class="font-medium text-gray-900 dark:text-white text-sm">{{ item.title }}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  {{ item.channel_name || 'Unknown' }} - {{ item.event_type }}
                </p>
              </div>
            </div>
            <div class="text-right">
              <p class="text-xs text-gray-500 dark:text-gray-400">{{ formatDate(item.sent_at) }}</p>
              <p v-if="item.error_message" class="text-xs text-red-500 truncate max-w-xs">{{ item.error_message }}</p>
            </div>
          </div>
        </div>
      </div>
    </Card>

    <!-- Channel Modal -->
    <Modal v-model="showChannelModal" :title="editingChannel ? 'Edit Channel' : 'Add Channel'" size="lg">
      <form @submit.prevent="saveChannel" class="space-y-4">
        <Input v-model="channelForm.name" label="Name" placeholder="Discord Alerts" required />

        <div>
          <label class="label">Channel Type</label>
          <div class="flex space-x-4 mt-2">
            <label class="flex items-center">
              <input type="radio" v-model="channelForm.channel_type" value="apprise" class="form-radio text-primary-600" />
              <span class="ml-2 text-gray-700 dark:text-gray-300">Apprise</span>
            </label>
            <label class="flex items-center">
              <input type="radio" v-model="channelForm.channel_type" value="email" class="form-radio text-primary-600" />
              <span class="ml-2 text-gray-700 dark:text-gray-300">Email</span>
            </label>
          </div>
        </div>

        <!-- Apprise Config -->
        <div v-if="channelForm.channel_type === 'apprise'">
          <Input
            v-model="channelForm.config.url"
            label="Apprise URL"
            placeholder="discord://webhook_id/webhook_token"
            required
          />
          <p class="text-xs text-gray-500 mt-1">
            See <a href="https://github.com/caronc/apprise/wiki" target="_blank" class="text-primary-600 hover:underline">Apprise documentation</a> for URL formats.
          </p>
        </div>

        <!-- Email Config -->
        <div v-if="channelForm.channel_type === 'email'" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <Input v-model="channelForm.config.smtp_host" label="SMTP Host" placeholder="smtp.gmail.com" required />
            <Input v-model="channelForm.config.smtp_port" type="number" label="SMTP Port" placeholder="587" required />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <Input v-model="channelForm.config.username" label="Username" placeholder="your@email.com" required />
            <Input v-model="channelForm.config.password" type="password" label="Password" placeholder="********" required />
          </div>
          <Input v-model="channelForm.config.from_address" label="From Address" placeholder="genmaster@example.com" required />
          <Input v-model="toAddressesInput" label="To Addresses" placeholder="admin@example.com, alerts@example.com" required />
          <div class="flex items-center">
            <Toggle v-model="channelForm.config.use_tls" label="Use TLS" />
          </div>
        </div>

        <Input v-model="channelForm.description" label="Description (optional)" placeholder="Alerts for critical events" />

        <div class="flex items-center">
          <Toggle v-model="channelForm.enabled" label="Enable channel" />
        </div>
      </form>

      <template #footer>
        <Button variant="secondary" @click="showChannelModal = false">Cancel</Button>
        <Button variant="primary" @click="saveChannel" :loading="saving">
          {{ editingChannel ? 'Update' : 'Create' }}
        </Button>
      </template>
    </Modal>

    <!-- Group Modal -->
    <Modal v-model="showGroupModal" :title="editingGroup ? 'Edit Group' : 'Add Group'" size="lg">
      <form @submit.prevent="saveGroup" class="space-y-4">
        <Input v-model="groupForm.name" label="Name" placeholder="Critical Alerts" required />
        <Input v-model="groupForm.description" label="Description (optional)" placeholder="All critical notification channels" />

        <div>
          <label class="label">Channels</label>
          <div class="mt-2 space-y-2 max-h-48 overflow-y-auto">
            <label
              v-for="channel in channels"
              :key="channel.id"
              class="flex items-center p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <input
                type="checkbox"
                :value="channel.id"
                v-model="groupForm.channel_ids"
                class="form-checkbox text-primary-600 rounded"
              />
              <span class="ml-2 text-gray-700 dark:text-gray-300">{{ channel.name }}</span>
              <span class="ml-2 text-xs text-gray-500">({{ channel.channel_type }})</span>
            </label>
          </div>
        </div>

        <div class="flex items-center">
          <Toggle v-model="groupForm.enabled" label="Enable group" />
        </div>
      </form>

      <template #footer>
        <Button variant="secondary" @click="showGroupModal = false">Cancel</Button>
        <Button variant="primary" @click="saveGroup" :loading="saving" :disabled="groupForm.channel_ids.length === 0">
          {{ editingGroup ? 'Update' : 'Create' }}
        </Button>
      </template>
    </Modal>

    <!-- Delete Confirmation Modal -->
    <Modal v-model="showDeleteConfirm" title="Confirm Delete">
      <p class="text-gray-600 dark:text-gray-400">
        Are you sure you want to delete "{{ deletingItem?.name }}"? This action cannot be undone.
      </p>
      <template #footer>
        <Button variant="secondary" @click="showDeleteConfirm = false">Cancel</Button>
        <Button variant="danger" @click="executeDelete" :loading="deleting">Delete</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import notificationsService from '@/services/notifications'
import { useNotificationStore } from '@/stores/notifications'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'
import Modal from '@/components/common/Modal.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

const notifications = useNotificationStore()

const tabs = [
  { id: 'channels', name: 'Channels' },
  { id: 'groups', name: 'Groups' },
  { id: 'history', name: 'History' },
]

const activeTab = ref('channels')
const loading = ref(true)
const saving = ref(false)
const deleting = ref(false)

const channels = ref([])
const groups = ref([])
const history = ref([])

// Modals
const showChannelModal = ref(false)
const showGroupModal = ref(false)
const showDeleteConfirm = ref(false)

const editingChannel = ref(null)
const editingGroup = ref(null)
const deletingItem = ref(null)
const deleteType = ref(null)

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

// Computed
const activeChannels = computed(() => channels.value.filter(c => c.enabled).length)
const recentSentCount = computed(() => history.value.filter(h => h.success).length)

// Lifecycle
onMounted(async () => {
  await loadData()
})

// Methods
async function loadData() {
  loading.value = true
  try {
    const [channelsData, groupsData, historyData] = await Promise.all([
      notificationsService.getChannels(),
      notificationsService.getGroups(),
      notificationsService.getHistory(50),
    ])
    channels.value = channelsData
    groups.value = groupsData
    history.value = historyData
  } catch {
    notifications.error('Failed to load notifications data')
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleString()
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
      toAddressesInput.value = channel.config.to_addresses.join(', ')
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
      notifications.success('Channel updated')
    } else {
      await notificationsService.createChannel(channelForm.value)
      notifications.success('Channel created')
    }
    showChannelModal.value = false
    await loadData()
  } catch {
    notifications.error('Failed to save channel')
  } finally {
    saving.value = false
  }
}

async function testChannel(channel) {
  try {
    const result = await notificationsService.testChannel(channel.id)
    if (result.success) {
      notifications.success('Test notification sent')
    } else {
      notifications.error(result.error || 'Test failed')
    }
    // Refresh history
    history.value = await notificationsService.getHistory(50)
  } catch {
    notifications.error('Failed to test channel')
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
      notifications.success('Group updated')
    } else {
      await notificationsService.createGroup(groupForm.value)
      notifications.success('Group created')
    }
    showGroupModal.value = false
    await loadData()
  } catch {
    notifications.error('Failed to save group')
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
      notifications.success('Channel deleted')
    } else {
      await notificationsService.deleteGroup(deletingItem.value.id)
      notifications.success('Group deleted')
    }
    showDeleteConfirm.value = false
    await loadData()
  } catch {
    notifications.error('Failed to delete')
  } finally {
    deleting.value = false
  }
}
</script>
