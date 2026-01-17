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
<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from '../stores/theme'
import { useAuthStore } from '../stores/auth'
import { useNotificationStore } from '../stores/notifications'
import { useDebugStore } from '../stores/debug'
import { settingsApi, authApi } from '../services/api'
import Card from '../components/common/Card.vue'
import LoadingSpinner from '../components/common/LoadingSpinner.vue'
import {
  Cog6ToothIcon,
  PaintBrushIcon,
  ShieldCheckIcon,
  UserIcon,
  KeyIcon,
  EyeIcon,
  EyeSlashIcon,
  CheckIcon,
  SunIcon,
  MoonIcon,
  Bars3Icon,
  ViewColumnsIcon,
  ArrowPathIcon,
  BoltIcon,
  LockClosedIcon,
  BugAntIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const notificationStore = useNotificationStore()
const debugStore = useDebugStore()

const loading = ref(true)
const saving = ref(false)
const activeTab = ref(route.query.tab || 'appearance')

// Watch for tab query changes
watch(() => route.query.tab, (newTab) => {
  if (newTab) activeTab.value = newTab
})

// Tab definitions
const tabs = [
  { id: 'appearance', name: 'Appearance', icon: PaintBrushIcon, iconColor: 'text-pink-500', bgActive: 'bg-pink-500/15 dark:bg-pink-500/20', textActive: 'text-pink-700 dark:text-pink-400', borderActive: 'border-pink-500/30' },
  { id: 'generator', name: 'Generator', icon: BoltIcon, iconColor: 'text-emerald-500', bgActive: 'bg-emerald-500/15 dark:bg-emerald-500/20', textActive: 'text-emerald-700 dark:text-emerald-400', borderActive: 'border-emerald-500/30' },
  { id: 'security', name: 'Security', icon: ShieldCheckIcon, iconColor: 'text-red-500', bgActive: 'bg-red-500/15 dark:bg-red-500/20', textActive: 'text-red-700 dark:text-red-400', borderActive: 'border-red-500/30' },
  { id: 'account', name: 'Account', icon: UserIcon, iconColor: 'text-purple-500', bgActive: 'bg-purple-500/15 dark:bg-purple-500/20', textActive: 'text-purple-700 dark:text-purple-400', borderActive: 'border-purple-500/30' },
  { id: 'advanced', name: 'Advanced', icon: BugAntIcon, iconColor: 'text-amber-500', bgActive: 'bg-amber-500/15 dark:bg-amber-500/20', textActive: 'text-amber-700 dark:text-amber-400', borderActive: 'border-amber-500/30' },
]

// Generator config state
const config = ref({
  warmup_seconds: 30,
  cooldown_seconds: 60,
  min_run_minutes: 5,
  max_run_minutes: 480,
  slave_url: 'http://genslave.local:8001',
  heartbeat_interval_seconds: 30,
})
const savingConfig = ref(false)
const testingConnection = ref(false)

// Security settings
const securitySettings = ref({
  session_timeout: 60,
  max_login_attempts: 5,
  lockout_duration: 15,
})
const savingSecurity = ref(false)

// Password state
const passwordForm = ref({ current: '', new: '', confirm: '' })
const showPasswords = ref({ current: false, new: false, confirm: false })
const changingPassword = ref(false)

// Theme selection
function selectTheme(mode) {
  themeStore.setColorMode(mode)
  const modeNames = { light: 'Light', dark: 'Dark' }
  notificationStore.success(`Theme changed to ${modeNames[mode] || mode} mode`)
}

// Load settings
async function loadSettings() {
  loading.value = true
  try {
    // Load generator config
    try {
      const configRes = await settingsApi.getConfig()
      if (configRes.data) {
        Object.assign(config.value, configRes.data)
      }
    } catch {
      // Use defaults
    }

    // Load debug mode
    await debugStore.loadDebugMode()

    // Load security settings
    try {
      const securityRes = await settingsApi.get('security')
      if (securityRes.data?.value) {
        Object.assign(securitySettings.value, securityRes.data.value)
      }
    } catch {
      // Use defaults
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  } finally {
    loading.value = false
  }
}

// Save generator config
async function saveConfig() {
  savingConfig.value = true
  try {
    await settingsApi.updateConfig(config.value)
    notificationStore.success('Generator settings saved')
  } catch {
    notificationStore.error('Failed to save generator settings')
  } finally {
    savingConfig.value = false
  }
}

// Test GenSlave connection
async function testConnection() {
  testingConnection.value = true
  try {
    const response = await fetch('/api/health/test-slave', { method: 'POST' })
    const result = await response.json()
    if (result.success) {
      notificationStore.success(`Connection successful (${result.latency_ms || 0}ms)`)
    } else {
      notificationStore.error(`Connection failed: ${result.error || 'Unknown error'}`)
    }
  } catch (err) {
    notificationStore.error(`Connection failed: ${err.message}`)
  } finally {
    testingConnection.value = false
  }
}

// Save security settings
async function saveSecuritySettings() {
  savingSecurity.value = true
  try {
    await settingsApi.update('security', { value: securitySettings.value })
    notificationStore.success('Security settings saved')
  } catch {
    notificationStore.error('Failed to save security settings')
  } finally {
    savingSecurity.value = false
  }
}

// Change password
async function changePassword() {
  if (passwordForm.value.new !== passwordForm.value.confirm) {
    notificationStore.error('Passwords do not match')
    return
  }

  if (passwordForm.value.new.length < 8) {
    notificationStore.error('Password must be at least 8 characters')
    return
  }

  changingPassword.value = true
  try {
    await authApi.changePassword({
      current_password: passwordForm.value.current,
      new_password: passwordForm.value.new,
    })
    notificationStore.success('Password changed successfully')
    passwordForm.value = { current: '', new: '', confirm: '' }
  } catch (error) {
    notificationStore.error(error.response?.data?.detail || 'Failed to change password')
  } finally {
    changingPassword.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div>
      <h1 class="text-2xl font-bold text-primary">Settings</h1>
      <p class="text-secondary mt-1">Configure your generator control system</p>
    </div>

    <!-- Loading Animation -->
    <div v-if="loading" class="py-16 flex flex-col items-center justify-center">
      <div class="relative flex items-center gap-2">
        <Cog6ToothIcon class="h-14 w-14 text-blue-500 animate-spin" style="animation-duration: 3s;" />
        <Cog6ToothIcon class="h-8 w-8 text-indigo-400 animate-spin" style="animation-duration: 2s; animation-direction: reverse;" />
      </div>
      <p class="mt-6 text-sm font-medium text-secondary">Loading settings...</p>
    </div>

    <template v-else>
      <!-- Tabs -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-400 dark:border-gray-700 p-1.5 flex gap-1.5 overflow-x-auto">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap border',
            activeTab === tab.id
              ? `${tab.bgActive} ${tab.textActive} ${tab.borderActive}`
              : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50 border-transparent'
          ]"
        >
          <component :is="tab.icon" :class="['h-4 w-4', activeTab === tab.id ? '' : tab.iconColor]" />
          {{ tab.name }}
        </button>
      </div>

      <!-- Appearance Tab -->
      <div v-if="activeTab === 'appearance'" class="space-y-6">
        <Card title="Theme" subtitle="Choose your preferred color scheme and navigation layout">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Light Theme Card -->
            <div
              :class="[
                'relative rounded-xl border-2 overflow-hidden transition-all cursor-pointer',
                themeStore.colorMode === 'light'
                  ? 'border-blue-500 ring-2 ring-blue-500/20'
                  : 'border-gray-400 hover:border-gray-400'
              ]"
              @click="selectTheme('light')"
            >
              <div class="bg-white p-4 border-b border-gray-400">
                <div class="flex items-center gap-3 mb-3">
                  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-300 to-orange-400 flex items-center justify-center">
                    <SunIcon class="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p class="font-semibold text-gray-900">Modern Light</p>
                    <p class="text-xs text-gray-500">Clean and bright interface</p>
                  </div>
                  <CheckIcon v-if="themeStore.colorMode === 'light'" class="h-6 w-6 text-blue-500 ml-auto" />
                </div>
                <div class="bg-gray-50 rounded-lg p-2 space-y-1">
                  <div class="h-2 w-3/4 bg-gray-200 rounded"></div>
                  <div class="h-2 w-1/2 bg-gray-200 rounded"></div>
                  <div class="h-2 w-2/3 bg-gray-200 rounded"></div>
                </div>
              </div>
              <div class="bg-gray-50 p-3" @click.stop>
                <div class="flex items-center justify-between">
                  <span class="text-sm font-medium text-gray-700">Navigation</span>
                  <div class="flex items-center gap-2 bg-white rounded-lg p-1 border border-gray-400">
                    <button
                      @click="themeStore.setLayoutMode('horizontal')"
                      :class="[
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                        themeStore.layout === 'horizontal' ? 'bg-blue-500 text-white' : 'text-gray-600 hover:bg-gray-100'
                      ]"
                    >
                      <Bars3Icon class="h-4 w-4" />
                      Top
                    </button>
                    <button
                      @click="themeStore.setLayoutMode('sidebar')"
                      :class="[
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                        themeStore.layout === 'sidebar' ? 'bg-blue-500 text-white' : 'text-gray-600 hover:bg-gray-100'
                      ]"
                    >
                      <ViewColumnsIcon class="h-4 w-4" />
                      Side
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Dark Theme Card -->
            <div
              :class="[
                'relative rounded-xl border-2 overflow-hidden transition-all cursor-pointer',
                themeStore.colorMode === 'dark'
                  ? 'border-blue-500 ring-2 ring-blue-500/20'
                  : 'border-gray-400 hover:border-gray-400'
              ]"
              @click="selectTheme('dark')"
            >
              <div class="bg-slate-900 p-4 border-b border-slate-700">
                <div class="flex items-center gap-3 mb-3">
                  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                    <MoonIcon class="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p class="font-semibold text-white">Modern Dark</p>
                    <p class="text-xs text-slate-400">Easy on the eyes at night</p>
                  </div>
                  <CheckIcon v-if="themeStore.colorMode === 'dark'" class="h-6 w-6 text-blue-400 ml-auto" />
                </div>
                <div class="bg-slate-800 rounded-lg p-2 space-y-1">
                  <div class="h-2 w-3/4 bg-slate-700 rounded"></div>
                  <div class="h-2 w-1/2 bg-slate-700 rounded"></div>
                  <div class="h-2 w-2/3 bg-slate-700 rounded"></div>
                </div>
              </div>
              <div class="bg-slate-800 p-3" @click.stop>
                <div class="flex items-center justify-between">
                  <span class="text-sm font-medium text-slate-300">Navigation</span>
                  <div class="flex items-center gap-2 bg-slate-900 rounded-lg p-1 border border-slate-700">
                    <button
                      @click="themeStore.setLayoutMode('horizontal')"
                      :class="[
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                        themeStore.layout === 'horizontal' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:bg-slate-800'
                      ]"
                    >
                      <Bars3Icon class="h-4 w-4" />
                      Top
                    </button>
                    <button
                      @click="themeStore.setLayoutMode('sidebar')"
                      :class="[
                        'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all',
                        themeStore.layout === 'sidebar' ? 'bg-blue-500 text-white' : 'text-slate-400 hover:bg-slate-800'
                      ]"
                    >
                      <ViewColumnsIcon class="h-4 w-4" />
                      Side
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- Generator Tab -->
      <div v-if="activeTab === 'generator'" class="space-y-6">
        <Card title="Generator Settings" subtitle="Configure generator timing and behavior">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Warmup Duration (seconds)</label>
              <input
                v-model.number="config.warmup_seconds"
                type="number"
                min="0"
                max="300"
                class="input"
              />
              <p class="text-xs text-muted mt-1">Time to wait after starting before considering 'running'</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Cooldown Duration (seconds)</label>
              <input
                v-model.number="config.cooldown_seconds"
                type="number"
                min="0"
                max="600"
                class="input"
              />
              <p class="text-xs text-muted mt-1">Time to run unloaded after stopping</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Minimum Run Time (minutes)</label>
              <input
                v-model.number="config.min_run_minutes"
                type="number"
                min="1"
                max="120"
                class="input"
              />
              <p class="text-xs text-muted mt-1">Minimum duration for each generator run</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Maximum Run Time (minutes)</label>
              <input
                v-model.number="config.max_run_minutes"
                type="number"
                min="30"
                max="1440"
                class="input"
              />
              <p class="text-xs text-muted mt-1">Maximum duration before automatic shutdown</p>
            </div>
          </div>
          <div class="flex justify-end mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button @click="saveConfig" :disabled="savingConfig" class="btn-primary">
              <ArrowPathIcon v-if="savingConfig" class="h-4 w-4 mr-2 animate-spin" />
              <CheckIcon v-else class="h-4 w-4 mr-2" />
              Save Settings
            </button>
          </div>
        </Card>

        <Card title="GenSlave Connection" subtitle="Configure GenSlave communication">
          <div class="space-y-4">
            <div class="flex gap-3 items-end">
              <div class="flex-1">
                <label class="block text-sm font-medium text-secondary mb-1">GenSlave URL</label>
                <input
                  v-model="config.slave_url"
                  type="text"
                  placeholder="http://genslave.local:8001"
                  class="input"
                />
              </div>
              <button
                @click="testConnection"
                :disabled="testingConnection"
                class="btn-secondary"
              >
                <BoltIcon v-if="!testingConnection" class="h-4 w-4 mr-2" />
                <ArrowPathIcon v-else class="h-4 w-4 mr-2 animate-spin" />
                Test
              </button>
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Heartbeat Interval (seconds)</label>
              <input
                v-model.number="config.heartbeat_interval_seconds"
                type="number"
                min="5"
                max="60"
                class="input w-48"
              />
              <p class="text-xs text-muted mt-1">How often to check GenSlave connectivity</p>
            </div>
          </div>
          <div class="flex justify-end mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button @click="saveConfig" :disabled="savingConfig" class="btn-primary">
              <CheckIcon class="h-4 w-4 mr-2" />
              Save Settings
            </button>
          </div>
        </Card>
      </div>

      <!-- Security Tab -->
      <div v-if="activeTab === 'security'" class="space-y-6">
        <!-- Header Banner -->
        <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-violet-500 via-purple-500 to-fuchsia-500 p-6 text-white shadow-lg">
          <div class="absolute inset-0 bg-black/10"></div>
          <div class="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="absolute -bottom-8 -left-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="relative flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
              <ShieldCheckIcon class="h-8 w-8" />
            </div>
            <div>
              <h2 class="text-2xl font-bold">Security Settings</h2>
              <p class="text-white/80">Configure session and authentication security</p>
            </div>
          </div>
        </div>

        <Card>
          <div class="space-y-6">
            <!-- Session Timeout -->
            <div class="group relative rounded-xl border border-gray-200 dark:border-gray-700 p-5 transition-all hover:border-violet-300 dark:hover:border-violet-600 hover:shadow-md">
              <div class="flex items-start gap-4">
                <div class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-400 to-blue-600 text-white shadow-lg shadow-blue-500/25">
                  <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <h4 class="font-semibold text-primary">Session Timeout</h4>
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">
                      {{ securitySettings.session_timeout }} min
                    </span>
                  </div>
                  <p class="mt-1 text-sm text-muted">Automatically log out users after this period of inactivity.</p>
                  <div class="mt-4 flex items-center gap-4">
                    <input
                      type="range"
                      v-model.number="securitySettings.session_timeout"
                      min="5"
                      max="480"
                      step="5"
                      class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <input
                      type="number"
                      v-model.number="securitySettings.session_timeout"
                      min="5"
                      max="480"
                      class="w-20 px-3 py-2 text-center font-mono text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-primary"
                    />
                    <span class="text-sm text-muted w-10">min</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Max Login Attempts -->
            <div class="group relative rounded-xl border border-gray-200 dark:border-gray-700 p-5 transition-all hover:border-violet-300 dark:hover:border-violet-600 hover:shadow-md">
              <div class="flex items-start gap-4">
                <div class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-lg shadow-orange-500/25">
                  <LockClosedIcon class="h-6 w-6" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <h4 class="font-semibold text-primary">Max Login Attempts</h4>
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">
                      {{ securitySettings.max_login_attempts }} attempts
                    </span>
                  </div>
                  <p class="mt-1 text-sm text-muted">Number of failed login attempts before account lockout.</p>
                  <div class="mt-4 flex items-center gap-2">
                    <button
                      v-for="n in [3, 5, 7, 10]"
                      :key="n"
                      @click="securitySettings.max_login_attempts = n"
                      :class="[
                        'px-4 py-2 rounded-lg text-sm font-medium transition-all',
                        securitySettings.max_login_attempts === n
                          ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/25'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                      ]"
                    >
                      {{ n }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Lockout Duration -->
            <div class="group relative rounded-xl border border-gray-200 dark:border-gray-700 p-5 transition-all hover:border-violet-300 dark:hover:border-violet-600 hover:shadow-md">
              <div class="flex items-start gap-4">
                <div class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-red-400 to-rose-600 text-white shadow-lg shadow-red-500/25">
                  <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <h4 class="font-semibold text-primary">Lockout Duration</h4>
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400">
                      {{ securitySettings.lockout_duration }} min
                    </span>
                  </div>
                  <p class="mt-1 text-sm text-muted">How long to lock an account after exceeding login attempts.</p>
                  <div class="mt-4 flex items-center gap-4">
                    <input
                      type="range"
                      v-model.number="securitySettings.lockout_duration"
                      min="5"
                      max="60"
                      step="5"
                      class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-red-500"
                    />
                    <input
                      type="number"
                      v-model.number="securitySettings.lockout_duration"
                      min="5"
                      max="60"
                      class="w-20 px-3 py-2 text-center font-mono text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-900 text-primary"
                    />
                    <span class="text-sm text-muted w-10">min</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-end mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button @click="saveSecuritySettings" :disabled="savingSecurity" class="btn-primary">
              <CheckIcon class="h-4 w-4 mr-2" />
              Save Security Settings
            </button>
          </div>
        </Card>
      </div>

      <!-- Account Tab -->
      <div v-if="activeTab === 'account'" class="space-y-6">
        <Card title="Change Password" subtitle="Update your account password">
          <div class="max-w-md space-y-4">
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Current Password</label>
              <div class="relative">
                <input
                  v-model="passwordForm.current"
                  :type="showPasswords.current ? 'text' : 'password'"
                  class="input pr-10"
                />
                <button
                  type="button"
                  @click="showPasswords.current = !showPasswords.current"
                  class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                >
                  <EyeSlashIcon v-if="showPasswords.current" class="h-5 w-5" />
                  <EyeIcon v-else class="h-5 w-5" />
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">New Password</label>
              <div class="relative">
                <input
                  v-model="passwordForm.new"
                  :type="showPasswords.new ? 'text' : 'password'"
                  class="input pr-10"
                />
                <button
                  type="button"
                  @click="showPasswords.new = !showPasswords.new"
                  class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                >
                  <EyeSlashIcon v-if="showPasswords.new" class="h-5 w-5" />
                  <EyeIcon v-else class="h-5 w-5" />
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Confirm New Password</label>
              <div class="relative">
                <input
                  v-model="passwordForm.confirm"
                  :type="showPasswords.confirm ? 'text' : 'password'"
                  class="input pr-10"
                />
                <button
                  type="button"
                  @click="showPasswords.confirm = !showPasswords.confirm"
                  class="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                >
                  <EyeSlashIcon v-if="showPasswords.confirm" class="h-5 w-5" />
                  <EyeIcon v-else class="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
          <div class="flex justify-end mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
            <button @click="changePassword" :disabled="changingPassword" class="btn-primary">
              <KeyIcon class="h-4 w-4 mr-2" />
              Change Password
            </button>
          </div>
        </Card>
      </div>

      <!-- Advanced Tab -->
      <div v-if="activeTab === 'advanced'" class="space-y-6">
        <!-- Header Banner -->
        <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-amber-500 via-orange-500 to-red-500 p-6 text-white shadow-lg">
          <div class="absolute inset-0 bg-black/10"></div>
          <div class="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="absolute -bottom-8 -left-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="relative flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
              <BugAntIcon class="h-8 w-8" />
            </div>
            <div>
              <h2 class="text-2xl font-bold">Advanced Settings</h2>
              <p class="text-white/80">Developer and debugging options</p>
            </div>
          </div>
        </div>

        <Card>
          <div class="space-y-6">
            <!-- Debug Mode Toggle -->
            <div class="group relative rounded-xl border border-gray-200 dark:border-gray-700 p-5 transition-all hover:border-amber-300 dark:hover:border-amber-600 hover:shadow-md">
              <div class="flex items-start gap-4">
                <div class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 text-white shadow-lg shadow-orange-500/25">
                  <BugAntIcon class="h-6 w-6" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between">
                    <div>
                      <div class="flex items-center gap-2">
                        <h4 class="font-semibold text-primary">Debug Mode</h4>
                        <span
                          v-if="debugStore.isEnabled"
                          class="px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400"
                        >
                          Enabled
                        </span>
                      </div>
                      <p class="mt-1 text-sm text-muted">Enable verbose logging and debugging features for development and troubleshooting.</p>
                    </div>
                    <button
                      @click="debugStore.toggleDebugMode"
                      :disabled="debugStore.loading"
                      :class="[
                        'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2',
                        debugStore.isEnabled ? 'bg-amber-500' : 'bg-gray-200 dark:bg-gray-700'
                      ]"
                    >
                      <span
                        :class="[
                          'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                          debugStore.isEnabled ? 'translate-x-5' : 'translate-x-0'
                        ]"
                      />
                    </button>
                  </div>
                  <div v-if="debugStore.isEnabled" class="mt-4 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                    <p class="text-sm text-amber-800 dark:text-amber-300">
                      Debug mode is active. Additional logging will appear in the browser console and server logs.
                      A debug indicator will also be shown in the sidebar.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Info Section -->
            <div class="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <div class="flex gap-3">
                <svg class="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h5 class="font-medium text-blue-800 dark:text-blue-300">About Advanced Settings</h5>
                  <p class="mt-1 text-sm text-blue-700 dark:text-blue-400">
                    These settings are intended for development and troubleshooting purposes.
                    Enable debug mode when reporting issues or diagnosing problems.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </template>
  </div>
</template>
