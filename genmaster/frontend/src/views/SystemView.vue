<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/SystemView.vue

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
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">System</h1>
        <p class="text-gray-600 dark:text-gray-400 mt-1">System information and health monitoring</p>
      </div>

      <!-- Health Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- CPU -->
        <Card>
          <div class="text-center">
            <div class="relative inline-block">
              <svg class="w-24 h-24" viewBox="0 0 100 100">
                <circle
                  class="text-gray-200 dark:text-gray-700"
                  stroke="currentColor"
                  stroke-width="8"
                  fill="transparent"
                  r="42"
                  cx="50"
                  cy="50"
                />
                <circle
                  :class="getProgressColorClass(cpuPercent)"
                  stroke="currentColor"
                  stroke-width="8"
                  stroke-linecap="round"
                  fill="transparent"
                  r="42"
                  cx="50"
                  cy="50"
                  :stroke-dasharray="`${cpuPercent * 2.64} 264`"
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-2xl font-bold">{{ cpuPercent }}%</span>
              </div>
            </div>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">CPU Usage</p>
          </div>
        </Card>

        <!-- Memory -->
        <Card>
          <div class="text-center">
            <div class="relative inline-block">
              <svg class="w-24 h-24" viewBox="0 0 100 100">
                <circle
                  class="text-gray-200 dark:text-gray-700"
                  stroke="currentColor"
                  stroke-width="8"
                  fill="transparent"
                  r="42"
                  cx="50"
                  cy="50"
                />
                <circle
                  :class="getProgressColorClass(memoryPercent)"
                  stroke="currentColor"
                  stroke-width="8"
                  stroke-linecap="round"
                  fill="transparent"
                  r="42"
                  cx="50"
                  cy="50"
                  :stroke-dasharray="`${memoryPercent * 2.64} 264`"
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-2xl font-bold">{{ memoryPercent }}%</span>
              </div>
            </div>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Memory Usage</p>
          </div>
        </Card>

        <!-- Disk -->
        <Card>
          <div class="text-center">
            <div class="relative inline-block">
              <svg class="w-24 h-24" viewBox="0 0 100 100">
                <circle
                  class="text-gray-200 dark:text-gray-700"
                  stroke="currentColor"
                  stroke-width="8"
                  fill="transparent"
                  r="42"
                  cx="50"
                  cy="50"
                />
                <circle
                  :class="getProgressColorClass(diskPercent)"
                  stroke="currentColor"
                  stroke-width="8"
                  stroke-linecap="round"
                  fill="transparent"
                  r="42"
                  cx="50"
                  cy="50"
                  :stroke-dasharray="`${diskPercent * 2.64} 264`"
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-2xl font-bold">{{ diskPercent }}%</span>
              </div>
            </div>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Disk Usage</p>
          </div>
        </Card>

        <!-- Temperature -->
        <Card>
          <div class="text-center">
            <div class="relative inline-block">
              <svg class="w-24 h-24" viewBox="0 0 100 100">
                <circle
                  class="text-gray-200 dark:text-gray-700"
                  stroke="currentColor"
                  stroke-width="8"
                  fill="transparent"
                  r="42"
                  cx="50"
                  cy="50"
                />
                <circle
                  :class="getTempColorClass(temperature)"
                  stroke="currentColor"
                  stroke-width="8"
                  stroke-linecap="round"
                  fill="transparent"
                  r="42"
                  cx="50"
                  cy="50"
                  :stroke-dasharray="`${Math.min(temperature, 100) * 2.64} 264`"
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-2xl font-bold">{{ temperature }}°C</span>
              </div>
            </div>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Temperature</p>
          </div>
        </Card>
      </div>

      <!-- GenSlave Status -->
      <Card title="GenSlave Status">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-4">
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', slaveOnline ? 'bg-green-500' : 'bg-red-500']">
              <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
            </div>
            <div>
              <p class="font-medium text-gray-900 dark:text-white">
                {{ slaveOnline ? 'Online' : 'Offline' }}
              </p>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Last heartbeat: {{ lastHeartbeat }}
              </p>
            </div>
          </div>
          <Button variant="secondary" @click="testSlaveConnection" :loading="testingConnection">
            Test Connection
          </Button>
        </div>
      </Card>

      <!-- Victron Status -->
      <Card title="Victron Status">
        <div class="flex items-center space-x-4">
          <div :class="['w-12 h-12 rounded-full flex items-center justify-center', victronActive ? 'bg-green-500' : 'bg-gray-500']">
            <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <p class="font-medium text-gray-900 dark:text-white">
              {{ victronActive ? 'Input Active' : 'Input Inactive' }}
            </p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              GPIO17 signal detection status
            </p>
          </div>
        </div>
      </Card>

      <!-- System Info -->
      <Card title="System Information">
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">Uptime</dt>
            <dd class="font-medium text-gray-900 dark:text-white">{{ formatUptime(uptime) }}</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">Version</dt>
            <dd class="font-medium text-gray-900 dark:text-white">1.0.0</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">Platform</dt>
            <dd class="font-medium text-gray-900 dark:text-white">Raspberry Pi 5</dd>
          </div>
          <div>
            <dt class="text-sm text-gray-500 dark:text-gray-400">Mode</dt>
            <dd class="font-medium text-gray-900 dark:text-white">
              {{ systemStore.status?.mock_gpio ? 'Development (Mock)' : 'Production' }}
            </dd>
          </div>
        </dl>
      </Card>

      <!-- SSL Certificate Status -->
      <Card title="SSL Certificate">
        <div v-if="sslLoading" class="flex items-center justify-center py-4">
          <svg class="animate-spin h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <div v-else-if="sslInfo.error" class="text-red-500">
          {{ sslInfo.error }}
        </div>
        <div v-else-if="sslInfo.certificates?.length > 0" class="space-y-4">
          <div v-for="cert in sslInfo.certificates" :key="cert.domain" class="border-b border-gray-200 dark:border-gray-700 pb-4 last:border-0 last:pb-0">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center space-x-3">
                <div :class="['w-10 h-10 rounded-full flex items-center justify-center', getCertStatusColor(cert)]">
                  <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <div>
                  <p class="font-medium text-gray-900 dark:text-white">{{ cert.domain }}</p>
                  <p class="text-sm text-gray-500 dark:text-gray-400">{{ cert.type }}</p>
                </div>
              </div>
              <div class="text-right">
                <p :class="['font-medium', getCertStatusTextColor(cert)]">
                  {{ cert.days_until_expiry !== undefined ? `${cert.days_until_expiry} days left` : 'Unknown' }}
                </p>
                <p v-if="cert.warning" class="text-sm text-amber-500">{{ cert.warning }}</p>
              </div>
            </div>
            <dl class="grid grid-cols-2 gap-2 text-sm">
              <div>
                <dt class="text-gray-500 dark:text-gray-400">Valid From</dt>
                <dd class="text-gray-900 dark:text-white">{{ cert.valid_from || 'N/A' }}</dd>
              </div>
              <div>
                <dt class="text-gray-500 dark:text-gray-400">Valid Until</dt>
                <dd class="text-gray-900 dark:text-white">{{ cert.valid_until || 'N/A' }}</dd>
              </div>
            </dl>
          </div>
          <div class="flex justify-end pt-2">
            <Button variant="secondary" @click="forceRenewCert" :loading="renewingCert">
              <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Force Renew
            </Button>
          </div>
        </div>
        <div v-else class="text-gray-500 dark:text-gray-400">
          No SSL certificates configured
        </div>
      </Card>

      <!-- External Services -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Cloudflare Tunnel -->
        <Card title="Cloudflare Tunnel">
          <div v-if="servicesLoading" class="flex items-center justify-center py-4">
            <svg class="animate-spin h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <div v-else-if="!externalServices.cloudflare?.enabled" class="text-gray-500 dark:text-gray-400">
            Not configured
          </div>
          <div v-else class="flex items-center space-x-4">
            <div :class="['w-12 h-12 rounded-full flex items-center justify-center', externalServices.cloudflare?.healthy ? 'bg-green-500' : externalServices.cloudflare?.running ? 'bg-amber-500' : 'bg-red-500']">
              <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p class="font-medium text-gray-900 dark:text-white">
                {{ externalServices.cloudflare?.healthy ? 'Connected' : externalServices.cloudflare?.running ? 'Running' : 'Disconnected' }}
              </p>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                {{ externalServices.cloudflare?.version || 'Cloudflare Tunnel' }}
              </p>
            </div>
          </div>
        </Card>

        <!-- Tailscale -->
        <Card title="Tailscale VPN">
          <div v-if="servicesLoading" class="flex items-center justify-center py-4">
            <svg class="animate-spin h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <div v-else-if="!externalServices.tailscale?.enabled" class="text-gray-500 dark:text-gray-400">
            Not configured
          </div>
          <div v-else class="space-y-2">
            <div class="flex items-center space-x-4">
              <div :class="['w-12 h-12 rounded-full flex items-center justify-center', externalServices.tailscale?.connected ? 'bg-green-500' : externalServices.tailscale?.running ? 'bg-amber-500' : 'bg-red-500']">
                <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <p class="font-medium text-gray-900 dark:text-white">
                  {{ externalServices.tailscale?.connected ? 'Connected' : externalServices.tailscale?.running ? 'Running' : 'Disconnected' }}
                </p>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  {{ externalServices.tailscale?.hostname || 'Tailscale VPN' }}
                </p>
              </div>
            </div>
            <div v-if="externalServices.tailscale?.ip_addresses?.length" class="text-sm text-gray-500 dark:text-gray-400">
              IPs: {{ externalServices.tailscale.ip_addresses.join(', ') }}
            </div>
          </div>
        </Card>
      </div>

      <!-- Docker & Network Info -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Docker Info -->
        <Card title="Docker">
          <div v-if="dockerLoading" class="flex items-center justify-center py-4">
            <svg class="animate-spin h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <div v-else-if="dockerInfo.error" class="text-red-500">
            {{ dockerInfo.error }}
          </div>
          <dl v-else class="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt class="text-gray-500 dark:text-gray-400">Version</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ dockerInfo.version || 'N/A' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500 dark:text-gray-400">Containers</dt>
              <dd class="font-medium text-gray-900 dark:text-white">
                {{ dockerInfo.containers?.running || 0 }}/{{ dockerInfo.containers?.total || 0 }} running
              </dd>
            </div>
            <div>
              <dt class="text-gray-500 dark:text-gray-400">Images</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ dockerInfo.images || 0 }}</dd>
            </div>
            <div>
              <dt class="text-gray-500 dark:text-gray-400">Storage</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ dockerInfo.storage_driver || 'N/A' }}</dd>
            </div>
          </dl>
        </Card>

        <!-- Network Info -->
        <Card title="Network">
          <div v-if="networkLoading" class="flex items-center justify-center py-4">
            <svg class="animate-spin h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <div v-else-if="networkInfo.error" class="text-red-500">
            {{ networkInfo.error }}
          </div>
          <dl v-else class="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt class="text-gray-500 dark:text-gray-400">Hostname</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ networkInfo.hostname || 'N/A' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500 dark:text-gray-400">Gateway</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ networkInfo.gateway || 'N/A' }}</dd>
            </div>
            <div class="col-span-2">
              <dt class="text-gray-500 dark:text-gray-400">DNS</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ networkInfo.dns_servers?.join(', ') || 'N/A' }}</dd>
            </div>
            <div v-for="iface in (networkInfo.interfaces || []).slice(0, 2)" :key="iface.name" class="col-span-2">
              <dt class="text-gray-500 dark:text-gray-400">{{ iface.name }}</dt>
              <dd class="font-medium text-gray-900 dark:text-white">{{ iface.ipv4 || 'No IP' }}</dd>
            </div>
          </dl>
        </Card>
      </div>

      <!-- System Actions -->
      <Card title="System Actions">
        <div class="flex flex-wrap gap-3">
          <Button variant="warning" @click="confirmReboot">
            <svg class="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reboot System
          </Button>
        </div>
      </Card>
    </div>

    <!-- Reboot Confirmation Modal -->
    <Modal v-model="showRebootConfirm" title="Reboot System">
      <p class="text-gray-600 dark:text-gray-400">
        Are you sure you want to reboot the system? This will temporarily interrupt all services.
      </p>
      <template #footer>
        <Button variant="secondary" @click="showRebootConfirm = false">Cancel</Button>
        <Button variant="warning" @click="rebootSystem">Reboot</Button>
      </template>
    </Modal>
  </MainLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useNotificationStore } from '@/stores/notifications'
import systemService from '@/services/system'
import MainLayout from '@/components/layout/MainLayout.vue'
import Card from '@/components/common/Card.vue'
import Button from '@/components/common/Button.vue'
import Modal from '@/components/common/Modal.vue'

const systemStore = useSystemStore()
const notifications = useNotificationStore()

const showRebootConfirm = ref(false)
const testingConnection = ref(false)

// SSL state
const sslInfo = ref({ certificates: [] })
const sslLoading = ref(true)
const renewingCert = ref(false)

// External services state
const externalServices = ref({ cloudflare: null, tailscale: null })
const servicesLoading = ref(true)

// Docker state
const dockerInfo = ref({})
const dockerLoading = ref(true)

// Network state
const networkInfo = ref({})
const networkLoading = ref(true)

// Computed properties
const cpuPercent = computed(() => systemStore.cpuPercent || 0)
const memoryPercent = computed(() => systemStore.memoryPercent || 0)
const diskPercent = computed(() => systemStore.diskPercent || 0)
const temperature = computed(() => systemStore.temperature || 0)
const uptime = computed(() => systemStore.uptime || 0)
const slaveOnline = computed(() => systemStore.isSlaveOnline)
const victronActive = computed(() => systemStore.victronInputActive)

const lastHeartbeat = computed(() => {
  const last = systemStore.slaveLastSeen
  if (!last) return 'Never'
  return new Date(last * 1000).toLocaleString()
})

// Helper functions
function getProgressColorClass(percent) {
  if (percent >= 90) return 'text-red-500'
  if (percent >= 70) return 'text-amber-500'
  return 'text-green-500'
}

function getTempColorClass(temp) {
  if (temp >= 80) return 'text-red-500'
  if (temp >= 60) return 'text-amber-500'
  return 'text-green-500'
}

function formatUptime(seconds) {
  if (!seconds) return '0s'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  const parts = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  if (minutes > 0) parts.push(`${minutes}m`)

  return parts.join(' ') || '< 1m'
}

// Actions
async function testSlaveConnection() {
  testingConnection.value = true
  await systemStore.testSlaveConnection()
  testingConnection.value = false
}

function confirmReboot() {
  showRebootConfirm.value = true
}

async function rebootSystem() {
  showRebootConfirm.value = false
  const success = await systemStore.rebootSystem()
  if (success) {
    notifications.warning('System is rebooting...')
  }
}

// SSL functions
function getCertStatusColor(cert) {
  if (!cert.days_until_expiry || cert.days_until_expiry <= 0) return 'bg-red-500'
  if (cert.days_until_expiry <= 7) return 'bg-amber-500'
  if (cert.days_until_expiry <= 30) return 'bg-yellow-500'
  return 'bg-green-500'
}

function getCertStatusTextColor(cert) {
  if (!cert.days_until_expiry || cert.days_until_expiry <= 0) return 'text-red-500'
  if (cert.days_until_expiry <= 7) return 'text-amber-500'
  if (cert.days_until_expiry <= 30) return 'text-yellow-500'
  return 'text-green-500'
}

async function loadSslInfo() {
  sslLoading.value = true
  try {
    sslInfo.value = await systemService.getSslInfo()
  } catch (err) {
    sslInfo.value = { error: 'Failed to load SSL info' }
  } finally {
    sslLoading.value = false
  }
}

async function forceRenewCert() {
  renewingCert.value = true
  try {
    const result = await systemService.forceRenewSsl()
    if (result.success) {
      notifications.success('Certificate renewed successfully')
      await loadSslInfo()
    } else {
      notifications.error(result.message || 'Failed to renew certificate')
    }
  } catch (err) {
    notifications.error('Failed to renew certificate')
  } finally {
    renewingCert.value = false
  }
}

// Load external services
async function loadExternalServices() {
  servicesLoading.value = true
  try {
    externalServices.value = await systemService.getExternalServices()
  } catch {
    externalServices.value = { cloudflare: null, tailscale: null }
  } finally {
    servicesLoading.value = false
  }
}

// Load Docker info
async function loadDockerInfo() {
  dockerLoading.value = true
  try {
    dockerInfo.value = await systemService.getDockerInfo()
  } catch {
    dockerInfo.value = { error: 'Failed to load Docker info' }
  } finally {
    dockerLoading.value = false
  }
}

// Load Network info
async function loadNetworkInfo() {
  networkLoading.value = true
  try {
    networkInfo.value = await systemService.getNetworkInfo()
  } catch {
    networkInfo.value = { error: 'Failed to load network info' }
  } finally {
    networkLoading.value = false
  }
}

// Load all system info on mount
onMounted(() => {
  loadSslInfo()
  loadExternalServices()
  loadDockerInfo()
  loadNetworkInfo()
})
</script>
