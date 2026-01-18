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
  GlobeAltIcon,
  DocumentTextIcon,
  PlusIcon,
  TrashIcon,
  PencilIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
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
  { id: 'access', name: 'Access Control', icon: GlobeAltIcon, iconColor: 'text-cyan-500', bgActive: 'bg-cyan-500/15 dark:bg-cyan-500/20', textActive: 'text-cyan-700 dark:text-cyan-400', borderActive: 'border-cyan-500/30' },
  { id: 'environment', name: 'Environment', icon: DocumentTextIcon, iconColor: 'text-indigo-500', bgActive: 'bg-indigo-500/15 dark:bg-indigo-500/20', textActive: 'text-indigo-700 dark:text-indigo-400', borderActive: 'border-indigo-500/30' },
  { id: 'account', name: 'Account', icon: UserIcon, iconColor: 'text-purple-500', bgActive: 'bg-purple-500/15 dark:bg-purple-500/20', textActive: 'text-purple-700 dark:text-purple-400', borderActive: 'border-purple-500/30' },
  { id: 'advanced', name: 'Advanced', icon: BugAntIcon, iconColor: 'text-amber-500', bgActive: 'bg-amber-500/15 dark:bg-amber-500/20', textActive: 'text-amber-700 dark:text-amber-400', borderActive: 'border-amber-500/30' },
]

// Generator config state (field names match backend ConfigResponse)
const config = ref({
  heartbeat_interval_seconds: 30,
})
const savingConfig = ref(false)

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

// Access Control state
const ipRanges = ref([])
const loadingIpRanges = ref(false)
const savingIpRanges = ref(false)
const newIpRange = ref({ ip_range: '', description: '' })
const editingIpRange = ref(null)
const commonNetworks = [
  { name: 'Tailscale', range: '100.64.0.0/10', description: 'Tailscale VPN network' },
  { name: 'Local (192.168.x.x)', range: '192.168.0.0/16', description: 'Local network' },
  { name: 'Local (10.x.x.x)', range: '10.0.0.0/8', description: 'Local network' },
]

// Environment variables state
const envVars = ref([])
const loadingEnvVars = ref(false)
const savingEnvVars = ref(false)
const envRestartRequired = ref(false)
const editingEnvVar = ref(null)

// User profile state
const userProfile = ref(null)
const loadingProfile = ref(false)

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

// Load IP ranges for Access Control
async function loadIpRanges() {
  loadingIpRanges.value = true
  try {
    const response = await settingsApi.get('ip_ranges')
    ipRanges.value = response.data?.value || []
  } catch {
    ipRanges.value = []
  } finally {
    loadingIpRanges.value = false
  }
}

// Add new IP range
async function addIpRange() {
  if (!newIpRange.value.ip_range) {
    notificationStore.error('IP range is required')
    return
  }

  // Basic CIDR validation
  const cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/
  if (!cidrPattern.test(newIpRange.value.ip_range)) {
    notificationStore.error('Invalid CIDR format (e.g., 192.168.1.0/24)')
    return
  }

  savingIpRanges.value = true
  try {
    const updatedRanges = [...ipRanges.value, { ...newIpRange.value }]
    await settingsApi.update('ip_ranges', { value: updatedRanges })
    ipRanges.value = updatedRanges
    newIpRange.value = { ip_range: '', description: '' }
    notificationStore.success('IP range added')
  } catch (error) {
    notificationStore.error('Failed to add IP range')
  } finally {
    savingIpRanges.value = false
  }
}

// Add common network
async function addCommonNetwork(network) {
  // Check if already exists
  if (ipRanges.value.some(r => r.ip_range === network.range)) {
    notificationStore.warning('This network is already added')
    return
  }

  savingIpRanges.value = true
  try {
    const updatedRanges = [...ipRanges.value, { ip_range: network.range, description: network.description }]
    await settingsApi.update('ip_ranges', { value: updatedRanges })
    ipRanges.value = updatedRanges
    notificationStore.success(`${network.name} network added`)
  } catch {
    notificationStore.error('Failed to add network')
  } finally {
    savingIpRanges.value = false
  }
}

// Remove IP range
async function removeIpRange(index) {
  savingIpRanges.value = true
  try {
    const updatedRanges = ipRanges.value.filter((_, i) => i !== index)
    await settingsApi.update('ip_ranges', { value: updatedRanges })
    ipRanges.value = updatedRanges
    notificationStore.success('IP range removed')
  } catch {
    notificationStore.error('Failed to remove IP range')
  } finally {
    savingIpRanges.value = false
  }
}

// Update IP range description
async function updateIpRangeDescription(index) {
  savingIpRanges.value = true
  try {
    await settingsApi.update('ip_ranges', { value: ipRanges.value })
    editingIpRange.value = null
    notificationStore.success('Description updated')
  } catch {
    notificationStore.error('Failed to update description')
  } finally {
    savingIpRanges.value = false
  }
}

// Load environment variables
async function loadEnvVars() {
  loadingEnvVars.value = true
  try {
    const response = await settingsApi.get('environment')
    envVars.value = response.data?.value || []
    envRestartRequired.value = false
  } catch {
    // Default environment variables if not configured
    envVars.value = [
      { key: 'APP_DEBUG', value: 'false', description: 'Enable debug mode', sensitive: false },
      { key: 'DATABASE_URL', value: '***', description: 'Database connection string', sensitive: true },
      { key: 'SECRET_KEY', value: '***', description: 'Application secret key', sensitive: true },
    ]
  } finally {
    loadingEnvVars.value = false
  }
}

// Update environment variable
async function updateEnvVar(index) {
  if (envVars.value[index].sensitive && envVars.value[index].value === '***') {
    editingEnvVar.value = null
    return
  }

  savingEnvVars.value = true
  try {
    await settingsApi.update('environment', { value: envVars.value })
    envRestartRequired.value = true
    editingEnvVar.value = null
    notificationStore.success('Environment variable updated')
  } catch {
    notificationStore.error('Failed to update environment variable')
  } finally {
    savingEnvVars.value = false
  }
}

// Load user profile
async function loadUserProfile() {
  loadingProfile.value = true
  try {
    const response = await authApi.getProfile()
    userProfile.value = response.data
  } catch {
    userProfile.value = {
      username: authStore.user?.username || 'admin',
      role: authStore.user?.role || 'admin',
      created_at: null,
    }
  } finally {
    loadingProfile.value = false
  }
}

onMounted(() => {
  loadSettings()
})

// Watch for tab changes to load data
watch(activeTab, (tab) => {
  if (tab === 'access' && ipRanges.value.length === 0) {
    loadIpRanges()
  } else if (tab === 'environment' && envVars.value.length === 0) {
    loadEnvVars()
  } else if (tab === 'account' && !userProfile.value) {
    loadUserProfile()
  }
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
        <Card>
          <div class="text-center py-8 text-muted">
            <p>Generator settings have been moved to:</p>
            <ul class="mt-4 space-y-2">
              <li><strong>Generator Control page</strong> - Min/Max run time settings</li>
              <li><strong>System → GenSlave tab</strong> - Connection and heartbeat settings</li>
            </ul>
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

      <!-- Access Control Tab -->
      <div v-if="activeTab === 'access'" class="space-y-6">
        <!-- Header Banner -->
        <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-cyan-500 via-teal-500 to-emerald-500 p-6 text-white shadow-lg">
          <div class="absolute inset-0 bg-black/10"></div>
          <div class="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="absolute -bottom-8 -left-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="relative flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
              <GlobeAltIcon class="h-8 w-8" />
            </div>
            <div>
              <h2 class="text-2xl font-bold">Access Control</h2>
              <p class="text-white/80">Manage IP ranges and network access</p>
            </div>
          </div>
        </div>

        <Card title="Allowed IP Ranges" subtitle="Configure which networks can access the system">
          <LoadingSpinner v-if="loadingIpRanges" size="sm" text="Loading IP ranges..." />
          <template v-else>
            <!-- Quick Add Common Networks -->
            <div class="mb-6">
              <h4 class="text-sm font-medium text-secondary mb-2">Quick Add Common Networks</h4>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="network in commonNetworks"
                  :key="network.range"
                  @click="addCommonNetwork(network)"
                  :disabled="savingIpRanges || ipRanges.some(r => r.ip_range === network.range)"
                  :class="[
                    'px-3 py-1.5 text-sm rounded-lg border transition-colors',
                    ipRanges.some(r => r.ip_range === network.range)
                      ? 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-400 cursor-not-allowed'
                      : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
                  ]"
                >
                  <CheckIcon v-if="ipRanges.some(r => r.ip_range === network.range)" class="h-4 w-4 inline mr-1" />
                  <PlusIcon v-else class="h-4 w-4 inline mr-1" />
                  {{ network.name }}
                </button>
              </div>
            </div>

            <!-- Current IP Ranges -->
            <div class="space-y-3 mb-6">
              <div
                v-for="(range, index) in ipRanges"
                :key="index"
                class="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700"
              >
                <div class="flex-1">
                  <div class="flex items-center gap-2">
                    <code class="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-sm font-mono text-primary">
                      {{ range.ip_range }}
                    </code>
                  </div>
                  <div v-if="editingIpRange === index" class="mt-2 flex items-center gap-2">
                    <input
                      v-model="ipRanges[index].description"
                      type="text"
                      class="input text-sm flex-1"
                      placeholder="Description"
                      @keyup.enter="updateIpRangeDescription(index)"
                    />
                    <button @click="updateIpRangeDescription(index)" class="btn-primary btn-sm">
                      <CheckIcon class="h-4 w-4" />
                    </button>
                    <button @click="editingIpRange = null" class="btn-secondary btn-sm">
                      <XMarkIcon class="h-4 w-4" />
                    </button>
                  </div>
                  <p v-else class="text-sm text-muted mt-1">
                    {{ range.description || 'No description' }}
                    <button @click="editingIpRange = index" class="ml-2 text-blue-500 hover:underline">
                      <PencilIcon class="h-3 w-3 inline" /> Edit
                    </button>
                  </p>
                </div>
                <button
                  @click="removeIpRange(index)"
                  :disabled="savingIpRanges"
                  class="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                >
                  <TrashIcon class="h-5 w-5" />
                </button>
              </div>

              <div v-if="ipRanges.length === 0" class="text-center py-8 text-muted">
                <GlobeAltIcon class="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No IP ranges configured</p>
                <p class="text-sm">Add networks to allow access</p>
              </div>
            </div>

            <!-- Add New IP Range -->
            <div class="pt-4 border-t border-gray-200 dark:border-gray-700">
              <h4 class="text-sm font-medium text-secondary mb-3">Add Custom IP Range</h4>
              <div class="flex gap-3">
                <input
                  v-model="newIpRange.ip_range"
                  type="text"
                  class="input flex-1"
                  placeholder="e.g., 192.168.1.0/24"
                />
                <input
                  v-model="newIpRange.description"
                  type="text"
                  class="input flex-1"
                  placeholder="Description (optional)"
                />
                <button @click="addIpRange" :disabled="savingIpRanges || !newIpRange.ip_range" class="btn-primary">
                  <PlusIcon class="h-4 w-4 mr-2" />
                  Add
                </button>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Environment Tab -->
      <div v-if="activeTab === 'environment'" class="space-y-6">
        <!-- Header Banner -->
        <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-indigo-500 via-blue-500 to-cyan-500 p-6 text-white shadow-lg">
          <div class="absolute inset-0 bg-black/10"></div>
          <div class="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="absolute -bottom-8 -left-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="relative flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
              <DocumentTextIcon class="h-8 w-8" />
            </div>
            <div>
              <h2 class="text-2xl font-bold">Environment Variables</h2>
              <p class="text-white/80">View and configure application environment</p>
            </div>
          </div>
        </div>

        <!-- Restart Warning -->
        <div v-if="envRestartRequired" class="p-4 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
          <div class="flex items-start gap-3">
            <ExclamationTriangleIcon class="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <h5 class="font-medium text-amber-800 dark:text-amber-300">Restart Required</h5>
              <p class="mt-1 text-sm text-amber-700 dark:text-amber-400">
                Environment changes require a container restart to take effect.
              </p>
            </div>
          </div>
        </div>

        <Card title="Environment Variables" subtitle="Application configuration values">
          <LoadingSpinner v-if="loadingEnvVars" size="sm" text="Loading environment..." />
          <template v-else>
            <div class="space-y-3">
              <div
                v-for="(envVar, index) in envVars"
                :key="envVar.key"
                class="group relative rounded-xl border border-gray-200 dark:border-gray-700 p-4 transition-all hover:border-indigo-300 dark:hover:border-indigo-600"
              >
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <div class="flex items-center gap-2">
                      <code class="px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 rounded text-sm font-mono text-indigo-700 dark:text-indigo-400">
                        {{ envVar.key }}
                      </code>
                      <span v-if="envVar.sensitive" class="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                        Sensitive
                      </span>
                    </div>
                    <p class="text-sm text-muted mt-1">{{ envVar.description }}</p>
                  </div>
                </div>

                <div v-if="editingEnvVar === index" class="mt-3 flex items-center gap-2">
                  <input
                    v-model="envVars[index].value"
                    :type="envVar.sensitive ? 'password' : 'text'"
                    class="input text-sm flex-1 font-mono"
                    :placeholder="envVar.sensitive ? 'Enter new value' : envVar.value"
                    @keyup.enter="updateEnvVar(index)"
                  />
                  <button @click="updateEnvVar(index)" class="btn-primary btn-sm">
                    <CheckIcon class="h-4 w-4" />
                  </button>
                  <button @click="editingEnvVar = null" class="btn-secondary btn-sm">
                    <XMarkIcon class="h-4 w-4" />
                  </button>
                </div>
                <div v-else class="mt-2 flex items-center justify-between">
                  <code class="px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded text-sm font-mono text-gray-700 dark:text-gray-300">
                    {{ envVar.sensitive ? '••••••••' : envVar.value }}
                  </code>
                  <button
                    @click="editingEnvVar = index"
                    class="text-sm text-blue-500 hover:underline flex items-center gap-1"
                  >
                    <PencilIcon class="h-3 w-3" /> Edit
                  </button>
                </div>
              </div>
            </div>

            <!-- Info Section -->
            <div class="mt-6 p-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <div class="flex gap-3">
                <svg class="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h5 class="font-medium text-blue-800 dark:text-blue-300">About Environment Variables</h5>
                  <p class="mt-1 text-sm text-blue-700 dark:text-blue-400">
                    Sensitive values are masked for security. Changes to environment variables require a container restart.
                    Edit with caution as incorrect values may prevent the application from starting.
                  </p>
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Account Tab -->
      <div v-if="activeTab === 'account'" class="space-y-6">
        <!-- Header Banner -->
        <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-500 via-violet-500 to-indigo-500 p-6 text-white shadow-lg">
          <div class="absolute inset-0 bg-black/10"></div>
          <div class="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="absolute -bottom-8 -left-8 h-32 w-32 rounded-full bg-white/10 blur-2xl"></div>
          <div class="relative flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
              <UserIcon class="h-8 w-8" />
            </div>
            <div>
              <h2 class="text-2xl font-bold">Account Settings</h2>
              <p class="text-white/80">Manage your profile and credentials</p>
            </div>
          </div>
        </div>

        <!-- User Profile Card -->
        <Card title="User Profile" subtitle="Your account information">
          <LoadingSpinner v-if="loadingProfile" size="sm" text="Loading profile..." />
          <template v-else>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Avatar and Name -->
              <div class="flex items-center gap-4">
                <div class="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white text-2xl font-bold">
                  {{ (userProfile?.username || 'A').charAt(0).toUpperCase() }}
                </div>
                <div>
                  <h3 class="text-lg font-semibold text-primary">{{ userProfile?.username || 'admin' }}</h3>
                  <p class="text-sm text-muted capitalize">{{ userProfile?.role || 'Administrator' }}</p>
                </div>
              </div>

              <!-- Profile Details -->
              <div class="space-y-3">
                <div class="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-700">
                  <span class="text-sm text-secondary">Username</span>
                  <span class="font-medium text-primary">{{ userProfile?.username || 'admin' }}</span>
                </div>
                <div class="flex justify-between items-center py-2 border-b border-gray-100 dark:border-gray-700">
                  <span class="text-sm text-secondary">Role</span>
                  <span class="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 capitalize">
                    {{ userProfile?.role || 'admin' }}
                  </span>
                </div>
                <div class="flex justify-between items-center py-2">
                  <span class="text-sm text-secondary">Account Created</span>
                  <span class="font-medium text-primary">
                    {{ userProfile?.created_at ? new Date(userProfile.created_at).toLocaleDateString() : 'N/A' }}
                  </span>
                </div>
              </div>
            </div>
          </template>
        </Card>

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
