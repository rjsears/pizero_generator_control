<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/GenSlaveView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 18th, 2026

  Dedicated view for GenSlave health monitoring with detailed
  system metrics, network info, relay control, and real-time status.

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
        <h1 class="text-2xl font-bold text-primary">GenSlave</h1>
        <p class="text-secondary mt-1">
          Remote generator controller health, status, and relay control
        </p>
      </div>
    </div>

    <!-- Loading State -->
    <HeartbeatLoader v-if="slaveLoading" :text="slaveLoadingMessages[slaveLoadingMessageIndex]" color="blue" class="py-16 mt-8" />

    <template v-else>
      <!-- GenSlave Status Banner -->
      <div :class="['rounded-xl p-6 border-2 relative overflow-hidden', slaveInfo.online ? 'bg-gradient-to-r from-emerald-500/10 to-emerald-500/5 border-emerald-500/50' : 'bg-gradient-to-r from-red-500/10 to-red-500/5 border-red-500/50']">
        <div class="relative flex items-center justify-between flex-wrap gap-4">
          <div class="flex items-center gap-4">
            <div :class="['p-4 rounded-2xl', slaveInfo.online ? 'bg-emerald-500/20' : 'bg-red-500/20']">
              <ServerIcon :class="['h-10 w-10', slaveInfo.online ? 'text-emerald-500' : 'text-red-500']" />
            </div>
            <div>
              <h2 class="text-2xl font-bold text-primary">
                GenSlave: <span :class="slaveInfo.online ? 'text-emerald-500' : 'text-red-500'">{{ slaveInfo.online ? 'ONLINE' : 'OFFLINE' }}</span>
              </h2>
              <p class="text-secondary mt-1">
                {{ slaveSystemInfo?.hostname || 'genslave' }} • {{ slaveSystemInfo?.platform || 'Raspberry Pi' }}
              </p>
            </div>
          </div>

          <div class="flex items-center gap-3">
            <button
              @click="loadSlaveInfo"
              :disabled="slaveLoading"
              class="btn-secondary flex items-center gap-2"
            >
              <ArrowPathIcon :class="['h-4 w-4', slaveLoading ? 'animate-spin' : '']" />
              Refresh
            </button>
            <button
              @click="testSlaveConnection"
              :disabled="testingConnection"
              class="btn-secondary flex items-center gap-2"
            >
              <BoltIcon :class="['h-4 w-4', testingConnection ? 'animate-pulse' : '']" />
              Test
            </button>
          </div>
        </div>
      </div>

      <!-- ARM/DISARM Banner -->
      <div
        :class="[
          'rounded-xl p-4 border-2 relative overflow-hidden transition-all',
          relayArmed
            ? 'bg-gradient-to-r from-red-500/20 to-red-500/10 border-red-500'
            : 'bg-gradient-to-r from-gray-500/20 to-gray-500/10 border-gray-400 dark:border-gray-600'
        ]"
      >
        <div class="flex items-center justify-between flex-wrap gap-4">
          <div class="flex items-center gap-4">
            <div
              :class="[
                'p-3 rounded-xl',
                relayArmed ? 'bg-red-500/30' : 'bg-gray-500/30'
              ]"
            >
              <ShieldExclamationIcon
                :class="[
                  'h-8 w-8',
                  relayArmed ? 'text-red-500' : 'text-gray-500'
                ]"
              />
            </div>
            <div>
              <h3 class="text-lg font-bold text-primary">
                Relay Status:
                <span :class="relayArmed ? 'text-red-500' : 'text-gray-500'">
                  {{ relayArmed ? 'ARMED' : 'DISARMED' }}
                </span>
              </h3>
              <p class="text-sm text-secondary">
                {{ relayArmed ? 'Generator can be started via relay control' : 'Relay is disabled - generator cannot be started remotely' }}
              </p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <button
              @click="toggleRelayArm"
              :disabled="armingRelay || !slaveInfo.online"
              :class="[
                'relative inline-flex h-8 w-16 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                relayArmed
                  ? 'bg-red-500 focus:ring-red-500'
                  : 'bg-gray-400 focus:ring-gray-500',
                (armingRelay || !slaveInfo.online) ? 'opacity-50 cursor-not-allowed' : ''
              ]"
            >
              <span
                :class="[
                  'inline-block h-6 w-6 transform rounded-full bg-white shadow-lg transition-transform',
                  relayArmed ? 'translate-x-9' : 'translate-x-1'
                ]"
              />
            </button>
            <span
              :class="[
                'px-3 py-1 rounded-full text-sm font-bold',
                relayArmed
                  ? 'bg-red-500 text-white'
                  : 'bg-gray-400 text-white'
              ]"
            >
              {{ relayArmed ? 'ARMED' : 'SAFE' }}
            </span>
          </div>
        </div>
      </div>

      <!-- System Resources Grid -->
      <div v-if="slaveSystemInfo" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <!-- CPU -->
        <Card :padding="false">
          <div class="p-4 text-center">
            <div class="relative inline-block">
              <svg class="w-20 h-20" viewBox="0 0 100 100">
                <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="10" fill="transparent" r="40" cx="50" cy="50" />
                <circle
                  :class="[
                    (slaveSystemInfo.cpu_percent || 0) >= 90 ? 'text-red-500' :
                    (slaveSystemInfo.cpu_percent || 0) >= 75 ? 'text-amber-500' : 'text-blue-500'
                  ]"
                  stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                  :stroke-dasharray="`${(slaveSystemInfo.cpu_percent || 0) * 2.51} 251`" transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.cpu_percent || 0) }}%</span>
              </div>
            </div>
            <p class="text-sm text-secondary mt-2">CPU</p>
          </div>
        </Card>

        <!-- Memory -->
        <Card :padding="false">
          <div class="p-4 text-center">
            <div class="relative inline-block">
              <svg class="w-20 h-20" viewBox="0 0 100 100">
                <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="10" fill="transparent" r="40" cx="50" cy="50" />
                <circle
                  :class="[
                    (slaveSystemInfo.ram_percent || 0) >= 90 ? 'text-red-500' :
                    (slaveSystemInfo.ram_percent || 0) >= 75 ? 'text-amber-500' : 'text-purple-500'
                  ]"
                  stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                  :stroke-dasharray="`${(slaveSystemInfo.ram_percent || 0) * 2.51} 251`" transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.ram_percent || 0) }}%</span>
              </div>
            </div>
            <p class="text-sm text-secondary mt-2">Memory</p>
            <p class="text-xs text-muted">{{ slaveSystemInfo.ram_used_mb || 0 }}MB / {{ slaveSystemInfo.ram_total_mb || 0 }}MB</p>
          </div>
        </Card>

        <!-- Disk -->
        <Card :padding="false">
          <div class="p-4 text-center">
            <div class="relative inline-block">
              <svg class="w-20 h-20" viewBox="0 0 100 100">
                <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="10" fill="transparent" r="40" cx="50" cy="50" />
                <circle
                  :class="[
                    (slaveSystemInfo.disk_percent || 0) >= 90 ? 'text-red-500' :
                    (slaveSystemInfo.disk_percent || 0) >= 75 ? 'text-amber-500' : 'text-emerald-500'
                  ]"
                  stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                  :stroke-dasharray="`${(slaveSystemInfo.disk_percent || 0) * 2.51} 251`" transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.disk_percent || 0) }}%</span>
              </div>
            </div>
            <p class="text-sm text-secondary mt-2">Disk</p>
            <p class="text-xs text-muted">{{ ((slaveSystemInfo.disk_total_gb || 0) - (slaveSystemInfo.disk_used_gb || 0)).toFixed(1) }}GB free</p>
          </div>
        </Card>

        <!-- Temperature -->
        <Card :padding="false">
          <div class="p-4 text-center">
            <div class="relative inline-block">
              <svg class="w-20 h-20" viewBox="0 0 100 100">
                <circle class="text-gray-200 dark:text-gray-700" stroke="currentColor" stroke-width="10" fill="transparent" r="40" cx="50" cy="50" />
                <circle
                  :class="[
                    (slaveSystemInfo.temperature_celsius || 0) >= 80 ? 'text-red-500' :
                    (slaveSystemInfo.temperature_celsius || 0) >= 60 ? 'text-amber-500' : 'text-cyan-500'
                  ]"
                  stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                  :stroke-dasharray="`${Math.min((slaveSystemInfo.temperature_celsius || 0), 100) * 2.51} 251`" transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.temperature_celsius || 0) }}°</span>
              </div>
            </div>
            <p class="text-sm text-secondary mt-2">Temp</p>
            <p class="text-xs text-muted">{{ (slaveSystemInfo.temperature_celsius || 0) >= 60 ? 'Warm' : 'Normal' }}</p>
          </div>
        </Card>
      </div>

      <!-- Detail Cards Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- System Info Card -->
        <Card title="System Information">
          <div v-if="slaveSystemInfo" class="space-y-3">
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Hostname</span>
              <span class="font-medium text-primary">{{ slaveSystemInfo.hostname || 'Unknown' }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Platform</span>
              <span class="font-medium text-primary">{{ slaveSystemInfo.platform || 'Unknown' }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">IP Address</span>
              <span class="font-medium text-primary font-mono">{{ slaveSystemInfo.ip_address || 'Unknown' }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Uptime</span>
              <span class="font-medium text-primary">{{ formatSeconds(slaveSystemInfo.uptime_seconds) }}</span>
            </div>
            <div v-if="slaveHealthStatus?.version" class="flex justify-between py-2">
              <span class="text-secondary">Version</span>
              <span class="font-medium text-primary">{{ slaveHealthStatus.version }}</span>
            </div>
          </div>
          <div v-else class="text-center py-4 text-muted">
            System information not available
          </div>
        </Card>

        <!-- Relay & Health Card -->
        <Card title="Relay & Health Status">
          <div class="space-y-3">
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Relay State</span>
              <span :class="['font-medium', slaveRelayState?.relay_on ? 'text-emerald-500' : 'text-gray-500']">
                {{ slaveRelayState?.relay_on ? 'ON' : 'OFF' }}
              </span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Armed</span>
              <span :class="['font-medium', relayArmed ? 'text-red-500' : 'text-emerald-500']">
                {{ relayArmed ? 'Yes' : 'No' }}
              </span>
            </div>
            <div v-if="slaveRelayState?.armed_at" class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Armed At</span>
              <span class="font-medium text-primary text-sm">{{ new Date(slaveRelayState.armed_at * 1000).toLocaleString() }}</span>
            </div>
            <div v-if="slaveRelayState?.change_count !== undefined" class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">State Changes</span>
              <span class="font-medium text-primary">{{ slaveRelayState.change_count }}</span>
            </div>
            <div class="flex justify-between py-2">
              <span class="text-secondary">Mock Mode</span>
              <span :class="['font-medium', slaveHealthStatus?.mock_mode ? 'text-amber-500' : 'text-emerald-500']">
                {{ slaveHealthStatus?.mock_mode ? 'Enabled' : 'Disabled' }}
              </span>
            </div>
          </div>
        </Card>

        <!-- Failsafe Monitoring Card -->
        <Card title="Failsafe Monitoring">
          <div v-if="slaveFailsafeStatus" class="space-y-3">
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Failsafe Running</span>
              <span :class="['font-medium', slaveFailsafeStatus.running ? 'text-emerald-500' : 'text-red-500']">
                {{ slaveFailsafeStatus.running ? 'Yes' : 'No' }}
              </span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Last Heartbeat</span>
              <span class="font-medium text-primary text-sm">
                {{ slaveFailsafeStatus.last_heartbeat ? new Date(slaveFailsafeStatus.last_heartbeat * 1000).toLocaleTimeString() : 'Never' }}
              </span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Since Heartbeat</span>
              <span :class="['font-medium', (slaveFailsafeStatus.seconds_since_heartbeat || 0) > 60 ? 'text-amber-500' : 'text-primary']">
                {{ formatSeconds(slaveFailsafeStatus.seconds_since_heartbeat) }}
              </span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Heartbeat Count</span>
              <span class="font-medium text-primary">{{ slaveFailsafeStatus.heartbeat_count || 0 }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-200 dark:border-gray-700">
              <span class="text-secondary">Timeout</span>
              <span class="font-medium text-primary">{{ slaveFailsafeStatus.timeout_seconds || 60 }}s</span>
            </div>
            <div class="flex justify-between py-2">
              <span class="text-secondary">Failsafe Triggered</span>
              <span :class="['font-medium', slaveFailsafeStatus.failsafe_triggered ? 'text-red-500' : 'text-emerald-500']">
                {{ slaveFailsafeStatus.failsafe_triggered ? 'Yes' : 'No' }}
              </span>
            </div>
          </div>
          <div v-else class="text-center py-4 text-muted">
            Failsafe status not available
          </div>
        </Card>

        <!-- Network & WiFi Card -->
        <Card title="Network & WiFi">
          <div v-if="slaveSystemInfo?.network_interfaces?.length" class="space-y-4">
            <div
              v-for="iface in slaveSystemInfo.network_interfaces"
              :key="iface.interface"
              class="p-3 rounded-lg bg-surface-hover"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <WifiIcon v-if="iface.is_wifi" class="h-4 w-4 text-blue-500" />
                  <GlobeAltIcon v-else class="h-4 w-4 text-emerald-500" />
                  <span class="font-medium text-primary">{{ iface.interface }}</span>
                </div>
                <span v-if="iface.ip_address" class="font-mono text-sm text-secondary">{{ iface.ip_address }}</span>
              </div>
              <!-- WiFi Signal if available -->
              <div v-if="iface.is_wifi && iface.wifi_ssid" class="mt-2">
                <div class="flex justify-between items-center text-sm mb-1">
                  <span class="text-muted">WiFi Signal</span>
                  <span class="font-medium text-primary">{{ iface.wifi_ssid }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      :class="[
                        'h-full rounded-full transition-all',
                        (iface.wifi_signal_percent || 0) >= 75 ? 'bg-emerald-500' :
                        (iface.wifi_signal_percent || 0) >= 50 ? 'bg-amber-500' : 'bg-red-500'
                      ]"
                      :style="{ width: `${iface.wifi_signal_percent || 0}%` }"
                    ></div>
                  </div>
                  <span class="text-xs text-muted w-12 text-right">{{ iface.wifi_signal_percent || 0 }}%</span>
                </div>
                <div v-if="iface.wifi_signal_dbm" class="text-xs text-muted mt-1">
                  {{ iface.wifi_signal_dbm }} dBm
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-4 text-muted">
            Network information not available
          </div>
        </Card>
      </div>

      <!-- Connection Settings Card -->
      <Card title="Connection Settings" subtitle="Configure GenSlave communication and network">
        <div class="space-y-6">
          <!-- Host Resolution Section -->
          <div class="p-4 rounded-lg bg-surface-hover">
            <h4 class="text-sm font-medium text-primary mb-3">Host Resolution (Container /etc/hosts)</h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-secondary mb-1">GenSlave Hostname</label>
                <input
                  v-model="slaveConfig.genslave_hostname"
                  type="text"
                  placeholder="genslave"
                  class="input"
                  @focus="isEditingConfig = true"
                  @blur="isEditingConfig = false"
                />
                <p class="text-xs text-muted mt-1">Hostname used in URL (e.g., genslave)</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-secondary mb-1">GenSlave IP Address</label>
                <input
                  v-model="slaveConfig.genslave_ip"
                  type="text"
                  placeholder="192.168.1.100"
                  class="input"
                  @focus="isEditingConfig = true"
                  @blur="isEditingConfig = false"
                />
                <p class="text-xs text-muted mt-1">IP address for hostname resolution</p>
              </div>
            </div>
            <p class="text-xs text-amber-600 dark:text-amber-400 mt-3">
              Note: Changes to hostname/IP require a container restart to update /etc/hosts
            </p>
          </div>

          <!-- URL and Connection Section -->
          <div class="flex gap-3 items-end flex-wrap">
            <div class="flex-1 min-w-[250px]">
              <label class="block text-sm font-medium text-secondary mb-1">GenSlave URL</label>
              <input
                v-model="slaveConfig.slave_api_url"
                type="text"
                placeholder="http://genslave:8001"
                class="input"
                @focus="isEditingConfig = true"
                @blur="isEditingConfig = false"
              />
              <p class="text-xs text-muted mt-1">Full URL to GenSlave API (uses hostname above)</p>
            </div>
            <button
              @click="testSlaveConnection"
              :disabled="testingConnection"
              class="btn-secondary flex items-center gap-2"
            >
              <BoltIcon v-if="!testingConnection" class="h-4 w-4" />
              <ArrowPathIcon v-else class="h-4 w-4 animate-spin" />
              Test
            </button>
          </div>

          <!-- Heartbeat Section -->
          <div>
            <label class="block text-sm font-medium text-secondary mb-1">Heartbeat Interval (seconds)</label>
            <input
              v-model.number="slaveConfig.heartbeat_interval_seconds"
              type="number"
              min="5"
              max="60"
              class="input w-48"
              @focus="isEditingConfig = true"
              @blur="isEditingConfig = false"
            />
            <p class="text-xs text-muted mt-1">How often GenMaster sends heartbeat to GenSlave</p>
          </div>
        </div>
        <div class="flex justify-end mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <button @click="saveSlaveConfig" :disabled="savingSlaveConfig" class="btn-primary flex items-center gap-2">
            <ArrowPathIcon v-if="savingSlaveConfig" class="h-4 w-4 animate-spin" />
            <CheckCircleIcon v-else class="h-4 w-4" />
            Save Settings
          </button>
        </div>
      </Card>

      <!-- Warnings if any -->
      <div v-if="slaveSystemInfo?.warnings?.length">
        <Card title="Warnings" :padding="false">
          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="(warning, index) in slaveSystemInfo.warnings"
              :key="index"
              class="p-4 flex items-start gap-3"
            >
              <ExclamationTriangleIcon class="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <p class="text-sm text-amber-700 dark:text-amber-400">{{ warning }}</p>
            </div>
          </div>
        </Card>
      </div>

      <!-- No data state -->
      <Card v-if="!slaveSystemInfo && !slaveInfo.online">
        <div class="text-center py-8 text-muted">
          <ServerIcon class="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>GenSlave is offline or unreachable</p>
          <p class="text-sm mt-1">Check the connection settings and ensure GenSlave is running</p>
          <button
            @click="testSlaveConnection"
            :disabled="testingConnection"
            class="mt-4 btn-primary"
          >
            <BoltIcon class="h-4 w-4 mr-2" />
            Test Connection
          </button>
        </div>
      </Card>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import api, { genslaveApi, configApi } from '@/services/api'
import Card from '@/components/common/Card.vue'
import HeartbeatLoader from '@/components/common/HeartbeatLoader.vue'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  GlobeAltIcon,
  WifiIcon,
  BoltIcon,
  ServerIcon,
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
} from '@heroicons/vue/24/outline'

const notificationStore = useNotificationStore()

// Loading state
const slaveLoading = ref(false)
const testingConnection = ref(false)
const slaveLoadingMessages = [
  'Connecting to GenSlave...',
  'Fetching system info...',
  'Checking relay status...',
  'Reading failsafe state...',
]
const slaveLoadingMessageIndex = ref(0)
let slaveLoadingInterval = null

// GenSlave state
const slaveInfo = ref({ online: false, last_heartbeat: null, details: null })

// GenSlave comprehensive data
const slaveSystemInfo = ref(null)  // GET /api/system
const slaveHealthStatus = ref(null)  // GET /api/health
const slaveFailsafeStatus = ref(null)  // GET /api/failsafe
const slaveRelayState = ref(null)  // GET /api/relay/state
const relayArmed = ref(false)
const armingRelay = ref(false)

// GenSlave connection settings
const slaveConfig = ref({
  slave_api_url: 'http://genslave:8001',
  heartbeat_interval_seconds: 30,
  genslave_ip: '',
  genslave_hostname: 'genslave',
})
const savingSlaveConfig = ref(false)
const isEditingConfig = ref(false)  // Prevent polling from overwriting user input

// Polling
let pollInterval = null

// Load GenSlave info (comprehensive)
async function loadSlaveInfo() {
  slaveLoading.value = true
  slaveLoadingMessageIndex.value = 0

  // Start rotating loading messages
  slaveLoadingInterval = setInterval(() => {
    slaveLoadingMessageIndex.value = (slaveLoadingMessageIndex.value + 1) % slaveLoadingMessages.length
  }, 1500)

  try {
    // Load config first (skip if user is actively editing to prevent overwriting their input)
    if (!isEditingConfig.value) {
      try {
        const configRes = await configApi.get()
        if (configRes.data) {
          slaveConfig.value.slave_api_url = configRes.data.slave_api_url || slaveConfig.value.slave_api_url
          slaveConfig.value.heartbeat_interval_seconds = configRes.data.heartbeat_interval_seconds || 30
          slaveConfig.value.genslave_ip = configRes.data.genslave_ip || ''
          slaveConfig.value.genslave_hostname = configRes.data.genslave_hostname || 'genslave'
        }
      } catch (e) {
        console.warn('Failed to load config for GenSlave:', e)
      }
    }

    // Load all GenSlave data in parallel with better error tracking
    let systemError = null
    let healthStatusError = null

    const [healthRes, systemRes, healthStatusRes, failsafeRes, relayRes] = await Promise.all([
      api.get('/health/slave').catch((e) => {
        console.warn('Failed to get /health/slave:', e.response?.data || e.message)
        return { data: { connection_status: 'disconnected' } }
      }),
      genslaveApi.getSystemInfo().catch((e) => {
        systemError = e.response?.data?.detail || e.message
        console.warn('Failed to get GenSlave system info:', systemError)
        return { data: null }
      }),
      genslaveApi.getHealthStatus().catch((e) => {
        healthStatusError = e.response?.data?.detail || e.message
        console.warn('Failed to get GenSlave health status:', healthStatusError)
        return { data: null }
      }),
      genslaveApi.getFailsafeStatus().catch((e) => {
        console.warn('Failed to get GenSlave failsafe status:', e.response?.data?.detail || e.message)
        return { data: null }
      }),
      genslaveApi.getRelayState().catch((e) => {
        console.warn('Failed to get GenSlave relay state:', e.response?.data?.detail || e.message)
        return { data: null }
      }),
    ])

    // Check if we got system data - if not, GenSlave is likely unreachable
    const isOnline = systemRes.data !== null

    // Basic connection info
    slaveInfo.value = {
      online: isOnline,
      last_heartbeat: healthRes.data?.last_heartbeat_received,
      details: systemRes.data,
      error: systemError,
    }

    // Comprehensive data
    slaveSystemInfo.value = systemRes.data
    slaveHealthStatus.value = healthStatusRes.data
    slaveFailsafeStatus.value = failsafeRes.data
    slaveRelayState.value = relayRes.data

    // Update armed state from relay state or health status
    relayArmed.value = relayRes.data?.armed || healthStatusRes.data?.armed || false

    // Show error notification if we couldn't reach GenSlave (only on manual refresh)
    if (!isOnline && systemError && !pollInterval) {
      notificationStore.error(`GenSlave unreachable: ${systemError}`)
    }
  } catch (error) {
    console.error('GenSlave info load failed:', error)
    slaveInfo.value = { online: false, last_heartbeat: null, details: null, error: error.message }
    slaveSystemInfo.value = null
    slaveHealthStatus.value = null
    slaveFailsafeStatus.value = null
    slaveRelayState.value = null
  } finally {
    if (slaveLoadingInterval) {
      clearInterval(slaveLoadingInterval)
      slaveLoadingInterval = null
    }
    slaveLoading.value = false
  }
}

// Test GenSlave connection
async function testSlaveConnection() {
  testingConnection.value = true
  try {
    const response = await api.post('/health/test-slave')
    if (response.data?.success) {
      notificationStore.success(`Connection successful (${response.data.latency_ms || response.data.response_time_ms || 0}ms)`)
      await loadSlaveInfo()
    } else {
      notificationStore.error(`Connection failed: ${response.data?.error || 'Unknown error'}`)
    }
  } catch (error) {
    notificationStore.error(`Connection failed: ${error.response?.data?.detail || error.message}`)
  } finally {
    testingConnection.value = false
  }
}

// Toggle relay ARM/DISARM
async function toggleRelayArm() {
  armingRelay.value = true
  try {
    if (relayArmed.value) {
      await genslaveApi.disarm()
      relayArmed.value = false
      notificationStore.success('Relay disarmed')
    } else {
      await genslaveApi.arm()
      relayArmed.value = true
      notificationStore.success('Relay armed - generator can now be started')
    }
  } catch (err) {
    notificationStore.error('Failed to toggle relay arm state')
    console.error('Failed to toggle relay arm state:', err)
  } finally {
    armingRelay.value = false
  }
}

// Save GenSlave connection settings
async function saveSlaveConfig() {
  savingSlaveConfig.value = true
  try {
    await configApi.update({
      slave_api_url: slaveConfig.value.slave_api_url,
      heartbeat_interval_seconds: slaveConfig.value.heartbeat_interval_seconds,
      genslave_ip: slaveConfig.value.genslave_ip,
      genslave_hostname: slaveConfig.value.genslave_hostname,
    })
    notificationStore.success('GenSlave settings saved')
    notificationStore.warning('Note: IP changes require container restart to update /etc/hosts')
  } catch (error) {
    notificationStore.error('Failed to save GenSlave settings')
  } finally {
    savingSlaveConfig.value = false
  }
}

// Format seconds to human readable
function formatSeconds(seconds) {
  if (!seconds || seconds <= 0) return '0s'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${mins}m`
}

// Lifecycle
onMounted(() => {
  loadSlaveInfo()
  // Poll every 30 seconds
  pollInterval = setInterval(loadSlaveInfo, 30000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
  if (slaveLoadingInterval) {
    clearInterval(slaveLoadingInterval)
  }
})
</script>
