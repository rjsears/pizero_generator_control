<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/notifications/ConfigureNotifications.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref, onMounted, computed } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import notificationsService from '@/services/notifications'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'
import Select from '@/components/common/Select.vue'
import Modal from '@/components/common/Modal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import {
  Cog6ToothIcon,
  BellIcon,
  BellSlashIcon,
  ClockIcon,
  MoonIcon,
  ShieldCheckIcon,
  PlayIcon,
  StopIcon,
  SignalIcon,
  SignalSlashIcon,
  CpuChipIcon,
  ServerIcon,
  CubeIcon,
  ShieldExclamationIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  PencilSquareIcon,
  ArrowPathIcon,
  DocumentTextIcon,
  CheckIcon,
} from '@heroicons/vue/24/outline'

const notifications = useNotificationStore()
const emit = defineEmits(['refresh-channels'])

// Props
const props = defineProps({
  channels: {
    type: Array,
    default: () => [],
  },
  groups: {
    type: Array,
    default: () => [],
  },
})

// State
const loading = ref(true)
const saving = ref(false)
const events = ref([])
const globalSettings = ref(null)
const categories = ref([])

// Section expansion
const globalSettingsExpanded = ref(true)
const categoryExpanded = ref({})

// Category config
const categoryConfig = {
  generator: {
    label: 'Generator Events',
    icon: CubeIcon,
    color: 'blue',
    description: 'Start, stop, relay, and runtime events',
  },
  genslave: {
    label: 'GenSlave Events',
    icon: SignalIcon,
    color: 'purple',
    description: 'Communication and failsafe events',
  },
  genmaster: {
    label: 'GenMaster Events',
    icon: ServerIcon,
    color: 'emerald',
    description: 'System resource monitoring',
  },
  ssl: {
    label: 'SSL Certificate Events',
    icon: ShieldCheckIcon,
    color: 'amber',
    description: 'Certificate expiration and renewal',
  },
  container: {
    label: 'Container Events',
    icon: CubeIcon,
    color: 'rose',
    description: 'Docker container health monitoring',
  },
}

// Severity options
const severityOptions = [
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'critical', label: 'Critical' },
]

// Frequency options
const frequencyOptions = [
  { value: 'every_time', label: 'Every Time' },
  { value: 'once_per_15m', label: 'Once per 15 minutes' },
  { value: 'once_per_30m', label: 'Once per 30 minutes' },
  { value: 'once_per_hour', label: 'Once per hour' },
  { value: 'once_per_4h', label: 'Once per 4 hours' },
  { value: 'once_per_12h', label: 'Once per 12 hours' },
  { value: 'once_per_day', label: 'Once per day' },
]

// Event modal
const showEventModal = ref(false)
const editingEvent = ref(null)
const eventForm = ref({})

// Template modal
const showTemplateModal = ref(false)
const templateEvent = ref(null)
const templateForm = ref({
  custom_title: '',
  custom_message: '',
})

// Filter events by category
const eventsByCategory = computed(() => {
  const grouped = {}
  for (const event of events.value) {
    if (!grouped[event.category]) {
      grouped[event.category] = []
    }
    grouped[event.category].push(event)
  }
  return grouped
})

// Load data
onMounted(async () => {
  await loadData()
})

async function loadData() {
  loading.value = true
  try {
    const [eventsData, settingsData] = await Promise.all([
      notificationsService.getSystemEvents(),
      notificationsService.getGlobalSettings(),
    ])
    events.value = eventsData.events || []
    categories.value = eventsData.categories || []
    globalSettings.value = settingsData

    // Initialize category expansion
    for (const cat of categories.value) {
      if (categoryExpanded.value[cat] === undefined) {
        categoryExpanded.value[cat] = true
      }
    }
  } catch (error) {
    console.error('Failed to load notification config:', error)
    notifications.error('Failed to load notification configuration')
  } finally {
    loading.value = false
  }
}

// Global settings methods
async function saveGlobalSettings() {
  saving.value = true
  try {
    await notificationsService.updateGlobalSettings(globalSettings.value)
    notifications.success('Global settings saved')
  } catch (error) {
    console.error('Failed to save global settings:', error)
    notifications.error('Failed to save settings')
  } finally {
    saving.value = false
  }
}

// Event methods
function openEventModal(event) {
  editingEvent.value = event
  eventForm.value = {
    enabled: event.enabled,
    severity: event.severity,
    frequency: event.frequency,
    cooldown_minutes: event.cooldown_minutes,
    escalation_enabled: event.escalation_enabled,
    escalation_timeout_minutes: event.escalation_timeout_minutes,
    flapping_enabled: event.flapping_enabled,
    flapping_threshold_count: event.flapping_threshold_count,
    flapping_threshold_minutes: event.flapping_threshold_minutes,
    include_in_digest: event.include_in_digest,
    l1_targets: event.targets?.filter(t => t.escalation_level === 1) || [],
    l2_targets: event.targets?.filter(t => t.escalation_level === 2) || [],
  }
  showEventModal.value = true
}

async function saveEvent() {
  if (!editingEvent.value) return
  saving.value = true
  try {
    await notificationsService.updateSystemEvent(editingEvent.value.id, eventForm.value)
    notifications.success(`Event "${editingEvent.value.display_name}" updated`)
    showEventModal.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to save event:', error)
    notifications.error('Failed to save event configuration')
  } finally {
    saving.value = false
  }
}

async function toggleEvent(event) {
  try {
    await notificationsService.updateSystemEvent(event.id, { enabled: !event.enabled })
    event.enabled = !event.enabled
    notifications.success(`Event ${event.enabled ? 'enabled' : 'disabled'}`)
  } catch (error) {
    console.error('Failed to toggle event:', error)
    notifications.error('Failed to update event')
  }
}

async function testEvent(event) {
  try {
    const result = await notificationsService.testEventNotification(event.event_type)
    if (result.success) {
      notifications.success('Test notification sent!')
    } else {
      notifications.warning(result.message || 'Notification suppressed')
    }
  } catch (error) {
    console.error('Failed to test event:', error)
    notifications.error('Failed to send test notification')
  }
}

// Template methods
function openTemplateModal(event) {
  templateEvent.value = event
  templateForm.value = {
    custom_title: event.custom_title || '',
    custom_message: event.custom_message || '',
  }
  showTemplateModal.value = true
}

async function saveTemplate() {
  if (!templateEvent.value) return
  saving.value = true
  try {
    await notificationsService.updateSystemEvent(templateEvent.value.id, {
      custom_title: templateForm.value.custom_title || null,
      custom_message: templateForm.value.custom_message || null,
    })
    notifications.success('Template updated')
    showTemplateModal.value = false
    await loadData()
  } catch (error) {
    console.error('Failed to save template:', error)
    notifications.error('Failed to save template')
  } finally {
    saving.value = false
  }
}

async function resetTemplate() {
  if (!templateEvent.value) return
  saving.value = true
  try {
    await notificationsService.resetEventTemplate(templateEvent.value.id)
    templateForm.value = {
      custom_title: '',
      custom_message: '',
    }
    notifications.success('Template reset to default')
    await loadData()
  } catch (error) {
    console.error('Failed to reset template:', error)
    notifications.error('Failed to reset template')
  } finally {
    saving.value = false
  }
}

// Helpers
function getSeverityColor(severity) {
  const colors = {
    info: 'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
    warning: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300',
    critical: 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-300',
  }
  return colors[severity] || colors.info
}

function getCategoryColor(category) {
  const config = categoryConfig[category]
  if (!config) return 'gray'
  return config.color
}
</script>

<template>
  <div class="space-y-6">
    <!-- Loading -->
    <div v-if="loading" class="py-16 flex flex-col items-center justify-center">
      <LoadingSpinner size="lg" />
      <p class="mt-4 text-sm text-secondary">Loading notification configuration...</p>
    </div>

    <template v-else>
      <!-- Global Settings Card -->
      <Card :padding="false">
        <div
          @click="globalSettingsExpanded = !globalSettingsExpanded"
          class="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        >
          <div class="flex items-center gap-3">
            <div class="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-500/20">
              <Cog6ToothIcon class="h-5 w-5 text-indigo-500" />
            </div>
            <div>
              <h3 class="font-semibold text-primary">Global Settings</h3>
              <p class="text-sm text-secondary">Maintenance mode, quiet hours, rate limiting</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="globalSettings?.maintenance_mode" class="text-xs px-2 py-1 rounded-full bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300">
              Maintenance Mode
            </span>
            <ChevronDownIcon v-if="globalSettingsExpanded" class="h-5 w-5 text-secondary" />
            <ChevronRightIcon v-else class="h-5 w-5 text-secondary" />
          </div>
        </div>

        <Transition name="collapse">
          <div v-if="globalSettingsExpanded && globalSettings" class="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
              <!-- Maintenance Mode -->
              <div class="space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div class="flex items-center gap-2">
                  <ShieldExclamationIcon class="h-5 w-5 text-amber-500" />
                  <h4 class="font-medium text-primary">Maintenance Mode</h4>
                </div>
                <Toggle v-model="globalSettings.maintenance_mode" label="Enable maintenance mode (mute all)" />
                <Input
                  v-if="globalSettings.maintenance_mode"
                  v-model="globalSettings.maintenance_reason"
                  label="Reason (optional)"
                  placeholder="Scheduled maintenance"
                />
              </div>

              <!-- Quiet Hours -->
              <div class="space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div class="flex items-center gap-2">
                  <MoonIcon class="h-5 w-5 text-purple-500" />
                  <h4 class="font-medium text-primary">Quiet Hours</h4>
                </div>
                <Toggle v-model="globalSettings.quiet_hours_enabled" label="Enable quiet hours" />
                <div v-if="globalSettings.quiet_hours_enabled" class="grid grid-cols-2 gap-3">
                  <Input v-model="globalSettings.quiet_hours_start" label="Start" type="time" />
                  <Input v-model="globalSettings.quiet_hours_end" label="End" type="time" />
                </div>
                <Toggle
                  v-if="globalSettings.quiet_hours_enabled"
                  v-model="globalSettings.quiet_hours_reduce_priority"
                  label="Reduce priority (uncheck to suppress)"
                />
              </div>

              <!-- Blackout Hours -->
              <div class="space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div class="flex items-center gap-2">
                  <BellSlashIcon class="h-5 w-5 text-red-500" />
                  <h4 class="font-medium text-primary">Blackout Hours</h4>
                </div>
                <Toggle v-model="globalSettings.blackout_enabled" label="Enable blackout (full suppression)" />
                <div v-if="globalSettings.blackout_enabled" class="grid grid-cols-2 gap-3">
                  <Input v-model="globalSettings.blackout_start" label="Start" type="time" />
                  <Input v-model="globalSettings.blackout_end" label="End" type="time" />
                </div>
              </div>

              <!-- Rate Limiting -->
              <div class="space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                <div class="flex items-center gap-2">
                  <ClockIcon class="h-5 w-5 text-blue-500" />
                  <h4 class="font-medium text-primary">Rate Limiting</h4>
                </div>
                <Input
                  v-model.number="globalSettings.max_notifications_per_hour"
                  label="Max notifications per hour"
                  type="number"
                  min="1"
                  max="500"
                />
                <p class="text-xs text-muted">
                  Current: {{ globalSettings.notifications_this_hour || 0 }} sent this hour
                </p>
              </div>

              <!-- Daily Digest -->
              <div class="space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg md:col-span-2">
                <div class="flex items-center gap-2">
                  <DocumentTextIcon class="h-5 w-5 text-emerald-500" />
                  <h4 class="font-medium text-primary">Daily Digest</h4>
                </div>
                <div class="flex items-center gap-4">
                  <Toggle v-model="globalSettings.digest_enabled" label="Enable daily digest" />
                  <Input
                    v-if="globalSettings.digest_enabled"
                    v-model="globalSettings.digest_time"
                    label="Send time"
                    type="time"
                    class="w-32"
                  />
                </div>
              </div>
            </div>

            <div class="mt-4 flex justify-end">
              <Button variant="primary" @click="saveGlobalSettings" :loading="saving">
                <CheckIcon class="h-4 w-4 mr-2" />
                Save Global Settings
              </Button>
            </div>
          </div>
        </Transition>
      </Card>

      <!-- Event Categories -->
      <Card
        v-for="category in categories"
        :key="category"
        :padding="false"
      >
        <div
          @click="categoryExpanded[category] = !categoryExpanded[category]"
          class="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        >
          <div class="flex items-center gap-3">
            <div :class="[
              'p-2 rounded-lg',
              `bg-${getCategoryColor(category)}-100 dark:bg-${getCategoryColor(category)}-500/20`
            ]">
              <component
                :is="categoryConfig[category]?.icon || BellIcon"
                :class="[`h-5 w-5 text-${getCategoryColor(category)}-500`]"
              />
            </div>
            <div>
              <h3 class="font-semibold text-primary">{{ categoryConfig[category]?.label || category }}</h3>
              <p class="text-sm text-secondary">{{ categoryConfig[category]?.description || '' }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
              {{ eventsByCategory[category]?.length || 0 }} events
            </span>
            <ChevronDownIcon v-if="categoryExpanded[category]" class="h-5 w-5 text-secondary" />
            <ChevronRightIcon v-else class="h-5 w-5 text-secondary" />
          </div>
        </div>

        <Transition name="collapse">
          <div v-if="categoryExpanded[category]" class="px-4 pb-4 border-t border-gray-200 dark:border-gray-700">
            <div class="space-y-2 pt-3">
              <div
                v-for="event in eventsByCategory[category]"
                :key="event.id"
                class="flex items-center justify-between p-4 rounded-lg bg-surface-hover border border-gray-200 dark:border-gray-700"
              >
                <div class="flex items-center space-x-4">
                  <div :class="['p-2 rounded-lg', event.enabled ? 'bg-blue-100 dark:bg-blue-500/20' : 'bg-gray-100 dark:bg-gray-600']">
                    <BellIcon :class="['w-5 h-5', event.enabled ? 'text-blue-600' : 'text-gray-400']" />
                  </div>
                  <div>
                    <h4 class="font-semibold text-primary">{{ event.display_name }}</h4>
                    <p class="text-sm text-secondary">{{ event.description }}</p>
                    <div class="flex items-center gap-2 mt-1">
                      <span :class="['text-xs px-2 py-0.5 rounded-full', getSeverityColor(event.severity)]">
                        {{ event.severity }}
                      </span>
                      <span v-if="event.escalation_enabled" class="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300">
                        L1/L2 Escalation
                      </span>
                      <span v-if="event.flapping_enabled" class="text-xs px-2 py-0.5 rounded-full bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-300">
                        Flapping Detection
                      </span>
                    </div>
                  </div>
                </div>
                <div class="flex items-center space-x-2">
                  <button
                    class="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-500/10 rounded-lg transition-colors"
                    @click="testEvent(event)"
                    title="Send test notification"
                  >
                    <PlayIcon class="w-5 h-5" />
                  </button>
                  <button
                    class="p-2 text-gray-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-500/10 rounded-lg transition-colors"
                    @click="openTemplateModal(event)"
                    title="Edit template"
                  >
                    <DocumentTextIcon class="w-5 h-5" />
                  </button>
                  <button
                    class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-lg transition-colors"
                    @click="openEventModal(event)"
                    title="Configure event"
                  >
                    <Cog6ToothIcon class="w-5 h-5" />
                  </button>
                  <label class="relative inline-flex items-center cursor-pointer ml-2">
                    <input
                      type="checkbox"
                      :checked="event.enabled"
                      @change.stop="toggleEvent(event)"
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

    <!-- Event Configuration Modal -->
    <Modal v-model="showEventModal" :title="`Configure: ${editingEvent?.display_name}`" size="lg">
      <div v-if="editingEvent" class="space-y-6">
        <!-- Basic Settings -->
        <div class="space-y-4">
          <h4 class="font-medium text-primary border-b border-gray-200 dark:border-gray-700 pb-2">Basic Settings</h4>
          <div class="grid grid-cols-2 gap-4">
            <Select
              v-model="eventForm.severity"
              label="Severity"
              :options="severityOptions"
            />
            <Select
              v-model="eventForm.frequency"
              label="Rate Limit"
              :options="frequencyOptions"
            />
          </div>
          <Input
            v-model.number="eventForm.cooldown_minutes"
            label="Additional cooldown (minutes)"
            type="number"
            min="0"
            max="1440"
          />
          <Toggle v-model="eventForm.include_in_digest" label="Include in daily digest" />
        </div>

        <!-- Escalation Settings -->
        <div class="space-y-4">
          <h4 class="font-medium text-primary border-b border-gray-200 dark:border-gray-700 pb-2">L1/L2 Escalation</h4>
          <Toggle v-model="eventForm.escalation_enabled" label="Enable escalation to L2" />
          <Input
            v-if="eventForm.escalation_enabled"
            v-model.number="eventForm.escalation_timeout_minutes"
            label="Escalation timeout (minutes)"
            type="number"
            min="1"
            max="1440"
          />
        </div>

        <!-- Flapping Detection -->
        <div class="space-y-4">
          <h4 class="font-medium text-primary border-b border-gray-200 dark:border-gray-700 pb-2">Flapping Detection</h4>
          <Toggle v-model="eventForm.flapping_enabled" label="Enable flapping detection" />
          <div v-if="eventForm.flapping_enabled" class="grid grid-cols-2 gap-4">
            <Input
              v-model.number="eventForm.flapping_threshold_count"
              label="Threshold count"
              type="number"
              min="2"
              max="20"
            />
            <Input
              v-model.number="eventForm.flapping_threshold_minutes"
              label="Time window (minutes)"
              type="number"
              min="1"
              max="60"
            />
          </div>
        </div>
      </div>

      <template #footer>
        <Button variant="secondary" @click="showEventModal = false">Cancel</Button>
        <Button variant="primary" @click="saveEvent" :loading="saving">Save Configuration</Button>
      </template>
    </Modal>

    <!-- Template Modal -->
    <Modal v-model="showTemplateModal" :title="`Edit Template: ${templateEvent?.display_name}`" size="lg">
      <div v-if="templateEvent" class="space-y-4">
        <div class="p-3 bg-blue-50 dark:bg-blue-500/10 rounded-lg">
          <p class="text-sm text-blue-700 dark:text-blue-300">
            Use placeholders like <code class="bg-blue-100 dark:bg-blue-800 px-1 rounded">{'{'}variable{'}'}</code> for dynamic content.
            Leave empty to use the default template.
          </p>
        </div>

        <div>
          <label class="label mb-1">Default Title</label>
          <p class="text-sm text-muted bg-gray-50 dark:bg-gray-800 p-2 rounded font-mono">
            {{ templateEvent.default_title }}
          </p>
        </div>

        <Input
          v-model="templateForm.custom_title"
          label="Custom Title (optional)"
          :placeholder="templateEvent.default_title"
        />

        <div>
          <label class="label mb-1">Default Message</label>
          <pre class="text-sm text-muted bg-gray-50 dark:bg-gray-800 p-2 rounded font-mono whitespace-pre-wrap">{{ templateEvent.default_message }}</pre>
        </div>

        <div>
          <label class="label mb-1">Custom Message (optional)</label>
          <textarea
            v-model="templateForm.custom_message"
            class="input w-full h-32 font-mono text-sm"
            :placeholder="templateEvent.default_message"
          ></textarea>
        </div>
      </div>

      <template #footer>
        <Button variant="secondary" @click="resetTemplate" :loading="saving">
          <ArrowPathIcon class="h-4 w-4 mr-2" />
          Reset to Default
        </Button>
        <Button variant="primary" @click="saveTemplate" :loading="saving">Save Template</Button>
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
