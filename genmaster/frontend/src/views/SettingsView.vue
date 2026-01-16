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

      <!-- Webhook Settings -->
      <Card title="Webhook Notifications">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-medium text-gray-900 dark:text-white">Enable Webhooks</p>
              <p class="text-sm text-gray-500 dark:text-gray-400">Send notifications to external services</p>
            </div>
            <Toggle v-model="webhookConfig.enabled" />
          </div>

          <Input
            v-model="webhookConfig.base_url"
            label="Webhook URL"
            placeholder="https://n8n.example.com/webhook/generator"
            hint="URL to send webhook notifications"
            :disabled="!webhookConfig.enabled"
          />
          <Input
            v-model="webhookConfig.secret"
            type="password"
            label="Webhook Secret"
            placeholder="Enter secret for HMAC signing"
            hint="Used for HMAC signature verification"
            :disabled="!webhookConfig.enabled"
          />

          <div class="flex justify-between pt-4">
            <Button
              variant="secondary"
              :disabled="!webhookConfig.enabled"
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

      <!-- Backup & Restore -->
      <Card title="Backup & Restore">
        <div class="space-y-4">
          <p class="text-gray-600 dark:text-gray-400">
            Create and manage database backups.
          </p>

          <div class="flex space-x-3">
            <Button variant="primary" @click="createBackup" :loading="creatingBackup">
              <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Create Backup
            </Button>
            <Button variant="secondary" @click="loadBackups">
              <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh List
            </Button>
          </div>

          <!-- Backups list -->
          <div v-if="backups.length > 0" class="mt-4">
            <table class="table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Size</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="backup in backups" :key="backup.filename">
                  <td class="font-mono text-sm">{{ backup.filename }}</td>
                  <td>{{ formatBytes(backup.size_bytes) }}</td>
                  <td>{{ formatDate(backup.created_at) }}</td>
                  <td>
                    <div class="flex space-x-2">
                      <Button variant="ghost" size="sm" @click="downloadBackup(backup.filename)">
                        Download
                      </Button>
                      <Button variant="ghost" size="sm" class="text-red-600" @click="confirmDeleteBackup(backup)">
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
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

    <!-- Delete Backup Confirmation -->
    <Modal v-model="showDeleteConfirm" title="Delete Backup">
      <p class="text-gray-600 dark:text-gray-400">
        Are you sure you want to delete "{{ deletingBackup?.filename }}"? This action cannot be undone.
      </p>
      <template #footer>
        <Button variant="secondary" @click="showDeleteConfirm = false">Cancel</Button>
        <Button variant="danger" @click="deleteBackup" :loading="deletingBackupInProgress">Delete</Button>
      </template>
    </Modal>
  </MainLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notifications'
import configService from '@/services/config'
import backupService from '@/services/backup'
import MainLayout from '@/components/layout/MainLayout.vue'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'
import Modal from '@/components/common/Modal.vue'

const authStore = useAuthStore()
const notifications = useNotificationStore()

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
})
const savingWebhook = ref(false)
const testingWebhook = ref(false)

// Backup state
const backups = ref([])
const creatingBackup = ref(false)
const showDeleteConfirm = ref(false)
const deletingBackup = ref(null)
const deletingBackupInProgress = ref(false)

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
    loadBackups(),
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
    webhookConfig.value = data
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
      notifications.success('Webhook test successful')
    } else {
      notifications.error(`Webhook test failed: ${result.error}`)
    }
  } catch {
    notifications.error('Failed to test webhook')
  } finally {
    testingWebhook.value = false
  }
}

async function loadBackups() {
  try {
    const data = await backupService.list()
    backups.value = data.backups || []
  } catch {
    notifications.error('Failed to load backups')
  }
}

async function createBackup() {
  creatingBackup.value = true
  try {
    await backupService.create()
    notifications.success('Backup created')
    await loadBackups()
  } catch {
    notifications.error('Failed to create backup')
  } finally {
    creatingBackup.value = false
  }
}

function downloadBackup(filename) {
  window.open(backupService.getDownloadUrl(filename), '_blank')
}

function confirmDeleteBackup(backup) {
  deletingBackup.value = backup
  showDeleteConfirm.value = true
}

async function deleteBackup() {
  if (!deletingBackup.value) return

  deletingBackupInProgress.value = true
  try {
    await backupService.delete(deletingBackup.value.filename)
    notifications.success('Backup deleted')
    showDeleteConfirm.value = false
    await loadBackups()
  } catch {
    notifications.error('Failed to delete backup')
  } finally {
    deletingBackupInProgress.value = false
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

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleString()
}
</script>
