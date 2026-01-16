<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/SettingsView.vue

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
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">System configuration and preferences</p>
      </div>

      <!-- Generator Settings -->
      <Card title="Generator Settings">
        <div class="space-y-4">
          <Input
            v-model.number="config.warmup_seconds"
            type="number"
            label="Warmup Duration (seconds)"
            hint="Time to wait after starting before considering the generator 'running'"
            :min="0"
            :max="300"
          />
          <Input
            v-model.number="config.cooldown_seconds"
            type="number"
            label="Cooldown Duration (seconds)"
            hint="Time to run unloaded after stopping"
            :min="0"
            :max="600"
          />
          <Input
            v-model.number="config.min_run_minutes"
            type="number"
            label="Minimum Run Time (minutes)"
            hint="Minimum duration for each generator run"
            :min="1"
            :max="120"
          />
          <Input
            v-model.number="config.max_run_minutes"
            type="number"
            label="Maximum Run Time (minutes)"
            hint="Maximum duration before automatic shutdown"
            :min="30"
            :max="1440"
          />
          <div class="flex justify-end pt-4">
            <Button variant="primary" @click="saveConfig" :loading="savingConfig">
              Save Settings
            </Button>
          </div>
        </div>
      </Card>

      <!-- GenSlave Settings -->
      <Card title="GenSlave Connection">
        <div class="space-y-4">
          <Input
            v-model="config.slave_url"
            label="GenSlave URL"
            placeholder="http://genslave.local:8001"
            hint="URL of the GenSlave API"
          />
          <Input
            v-model.number="config.heartbeat_interval_seconds"
            type="number"
            label="Heartbeat Interval (seconds)"
            hint="How often to check GenSlave connectivity"
            :min="5"
            :max="60"
          />
          <div class="flex justify-end pt-4">
            <Button variant="primary" @click="saveConfig" :loading="savingConfig">
              Save Settings
            </Button>
          </div>
        </div>
      </Card>

      <!-- Webhook Notifications -->
      <Card title="Webhook Notifications">
        <div class="space-y-6">
          <!-- Master Enable Toggle -->
          <div class="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50">
            <div>
              <p class="font-medium text-gray-900 dark:text-white">Enable Webhooks</p>
              <p class="text-sm text-gray-500 dark:text-gray-400">Send notifications to external webhook URL</p>
            </div>
            <Toggle v-model="webhookConfig.enabled" />
          </div>

          <!-- Webhook URL and Secret -->
          <div :class="{ 'opacity-50 pointer-events-none': !webhookConfig.enabled }">
            <Input
              v-model="webhookConfig.base_url"
              label="Webhook URL"
              placeholder="https://n8n.example.com/webhook/generator"
              hint="URL will receive POST requests with event data"
            />
            <div class="mt-4">
              <Input
                v-model="webhookConfig.secret"
                type="password"
                label="Webhook Secret"
                placeholder="Enter secret for X-Webhook-Secret header"
                hint="Sent in X-Webhook-Secret header for verification"
              />
            </div>
          </div>

          <!-- Event Types -->
          <div :class="{ 'opacity-50 pointer-events-none': !webhookConfig.enabled }">
            <h4 class="font-medium text-gray-900 dark:text-white mb-3">Event Types</h4>
            <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">Select which events trigger webhook notifications</p>
            <div class="space-y-2">
              <div
                v-for="event in eventTypes"
                :key="event.key"
                class="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <input
                  type="checkbox"
                  :id="event.key"
                  v-model="webhookConfig.events[event.key]"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label :for="event.key" class="flex-1 cursor-pointer">
                  <p class="text-sm font-medium text-gray-900 dark:text-white">{{ event.label }}</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400">{{ event.description }}</p>
                </label>
              </div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              variant="secondary"
              :disabled="!webhookConfig.enabled || !webhookConfig.base_url"
              @click="testWebhook"
              :loading="testingWebhook"
            >
              Test Webhook
            </Button>
            <Button variant="primary" @click="saveWebhookConfig" :loading="savingWebhook">
              Save Webhook Settings
            </Button>
          </div>
        </div>
      </Card>

      <!-- Account Settings -->
      <Card title="Account Settings">
        <div class="space-y-4">
          <h3 class="font-medium text-gray-900 dark:text-white">Change Password</h3>
          <Input
            v-model="passwordForm.current"
            type="password"
            label="Current Password"
          />
          <Input
            v-model="passwordForm.new"
            type="password"
            label="New Password"
          />
          <Input
            v-model="passwordForm.confirm"
            type="password"
            label="Confirm New Password"
          />
          <div class="flex justify-end pt-4">
            <Button variant="primary" @click="changePassword" :loading="changingPassword">
              Change Password
            </Button>
          </div>
        </div>
      </Card>
    </div>
  </MainLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notifications'
import configService from '@/services/config'
import MainLayout from '@/components/layout/MainLayout.vue'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'

const authStore = useAuthStore()
const notifications = useNotificationStore()

// Webhook event types
const eventTypes = [
  { key: 'generator_started', label: 'Generator Started', description: 'When generator starts running' },
  { key: 'generator_stopped', label: 'Generator Stopped', description: 'When generator stops (any reason)' },
  { key: 'generator_failed', label: 'Generator Failed', description: 'When generator fails to start/stop' },
  { key: 'heartbeat_lost', label: 'Heartbeat Lost', description: 'When GenSlave connection is lost' },
  { key: 'heartbeat_restored', label: 'Heartbeat Restored', description: 'When GenSlave connection is restored' },
  { key: 'failsafe_triggered', label: 'Failsafe Triggered', description: 'When GenSlave triggers failsafe stop' },
  { key: 'schedule_executed', label: 'Schedule Executed', description: 'When scheduled run starts' },
  { key: 'override_enabled', label: 'Override Enabled', description: 'When manual override is enabled' },
  { key: 'override_disabled', label: 'Override Disabled', description: 'When manual override is disabled' },
  { key: 'system_warning', label: 'System Warning', description: 'High temp, low disk, etc.' },
  { key: 'system_error', label: 'System Error', description: 'Critical system errors' },
]

// Config state
const config = ref({
  warmup_seconds: 30,
  cooldown_seconds: 60,
  min_run_minutes: 5,
  max_run_minutes: 480,
  slave_url: 'http://genslave.local:8001',
  heartbeat_interval_seconds: 30,
})
const savingConfig = ref(false)

// Webhook state
const webhookConfig = ref({
  base_url: '',
  secret: '',
  enabled: false,
  events: {
    generator_started: true,
    generator_stopped: true,
    generator_failed: true,
    heartbeat_lost: true,
    heartbeat_restored: true,
    failsafe_triggered: true,
    schedule_executed: true,
    override_enabled: true,
    override_disabled: true,
    system_warning: true,
    system_error: true,
  },
})
const savingWebhook = ref(false)
const testingWebhook = ref(false)

// Password state
const passwordForm = ref({
  current: '',
  new: '',
  confirm: '',
})
const changingPassword = ref(false)

onMounted(async () => {
  await Promise.all([
    loadConfig(),
    loadWebhookConfig(),
  ])
})

async function loadConfig() {
  try {
    const data = await configService.get()
    Object.assign(config.value, data)
  } catch {
    // Use defaults
  }
}

async function saveConfig() {
  savingConfig.value = true
  try {
    await configService.update(config.value)
    notifications.success('Settings saved')
  } catch {
    notifications.error('Failed to save settings')
  } finally {
    savingConfig.value = false
  }
}

async function loadWebhookConfig() {
  try {
    const data = await configService.getWebhookConfig()
    // Merge with defaults to ensure all event types exist
    webhookConfig.value = {
      ...webhookConfig.value,
      ...data,
      events: {
        ...webhookConfig.value.events,
        ...(data.events || {}),
      },
    }
  } catch {
    // Use defaults
  }
}

async function saveWebhookConfig() {
  savingWebhook.value = true
  try {
    await configService.updateWebhookConfig(webhookConfig.value)
    notifications.success('Webhook settings saved')
  } catch {
    notifications.error('Failed to save webhook settings')
  } finally {
    savingWebhook.value = false
  }
}

async function testWebhook() {
  testingWebhook.value = true
  try {
    const result = await configService.testWebhook()
    if (result.success) {
      notifications.success(`Webhook test successful (${result.response_time_ms}ms)`)
    } else {
      notifications.error(`Webhook test failed: ${result.error}`)
    }
  } catch {
    notifications.error('Failed to test webhook')
  } finally {
    testingWebhook.value = false
  }
}

async function changePassword() {
  if (passwordForm.value.new !== passwordForm.value.confirm) {
    notifications.error('Passwords do not match')
    return
  }

  if (passwordForm.value.new.length < 8) {
    notifications.error('Password must be at least 8 characters')
    return
  }

  changingPassword.value = true
  const success = await authStore.changePassword(
    passwordForm.value.current,
    passwordForm.value.new
  )

  if (success) {
    notifications.success('Password changed successfully')
    passwordForm.value = { current: '', new: '', confirm: '' }
  } else {
    notifications.error(authStore.error || 'Failed to change password')
  }
  changingPassword.value = false
}
</script>
