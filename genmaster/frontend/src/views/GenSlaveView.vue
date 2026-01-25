<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/GenSlaveView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 18th, 2026

  Dedicated view for GenSlave health monitoring with detailed
  system metrics, network info, and real-time status.

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
          Remote generator controller health and status monitoring
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
              @click="loadSlaveInfo(true)"
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
            <button
              @click="handleReboot"
              :disabled="rebooting || !slaveInfo.online"
              class="btn-secondary flex items-center gap-2 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-500/10"
            >
              <ArrowPathIcon :class="['h-4 w-4', rebooting ? 'animate-spin' : '']" />
              Reboot
            </button>
            <button
              @click="handleShutdown"
              :disabled="shuttingDown || !slaveInfo.online"
              class="btn-secondary flex items-center gap-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10"
            >
              <PowerIcon :class="['h-4 w-4', shuttingDown ? 'animate-pulse' : '']" />
              Shutdown
            </button>
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
                    (slaveSystemInfo.temperature_fahrenheit || 0) >= 176 ? 'text-red-500' :
                    (slaveSystemInfo.temperature_fahrenheit || 0) >= 140 ? 'text-amber-500' : 'text-cyan-500'
                  ]"
                  stroke="currentColor" stroke-width="10" stroke-linecap="round" fill="transparent" r="40" cx="50" cy="50"
                  :stroke-dasharray="`${Math.min((slaveSystemInfo.temperature_fahrenheit || 0) / 2.12, 100) * 2.51} 251`" transform="rotate(-90 50 50)"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center">
                <span class="text-xl font-bold text-primary">{{ Math.round(slaveSystemInfo.temperature_fahrenheit || 0) }}°F</span>
              </div>
            </div>
            <p class="text-sm text-secondary mt-2">Temp</p>
            <p class="text-xs text-muted">{{ (slaveSystemInfo.temperature_fahrenheit || 0) >= 140 ? 'Warm' : 'Normal' }}</p>
          </div>
        </Card>
      </div>

      <!-- System Information Collapsible Section -->
      <Card :padding="false">
        <button
          @click="systemInfoSectionExpanded = !systemInfoSectionExpanded"
          class="w-full p-4 flex items-center gap-4 hover:bg-surface-hover transition-colors rounded-lg"
        >
          <div class="p-3 rounded-xl bg-gradient-to-br from-blue-500 to-teal-500 shadow-lg">
            <CpuChipIcon class="h-6 w-6 text-white" />
          </div>
          <div class="flex-1 text-left">
            <h3 class="text-lg font-semibold text-primary">System Information</h3>
            <p class="text-sm text-secondary">GenSlave system details, relay status, failsafe, and network</p>
          </div>
          <div :class="['p-2 rounded-lg transition-colors', systemInfoSectionExpanded ? 'bg-blue-100 dark:bg-blue-500/20' : 'bg-gray-100 dark:bg-gray-700']">
            <ChevronDownIcon :class="['h-5 w-5 transition-transform duration-200', systemInfoSectionExpanded ? 'rotate-180 text-blue-600 dark:text-blue-400' : 'text-gray-500']" />
          </div>
        </button>
        <div v-show="systemInfoSectionExpanded" class="p-4 pt-2 border-t border-gray-200 dark:border-gray-700">
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
        <Card :padding="false">
          <template #header>
            <div class="flex items-center justify-between w-full px-4 py-3">
              <h3 class="font-semibold text-primary">Network & WiFi</h3>
              <div class="flex items-center gap-2">
                <button
                  @click="openAddNetworkModal"
                  :disabled="!slaveInfo.online"
                  class="px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <PlusIcon class="h-3.5 w-3.5" />
                  Add Network
                </button>
                <button
                  @click="openWifiConfigModal"
                  :disabled="!slaveInfo.online"
                  class="px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm flex items-center gap-1.5 bg-cyan-500 hover:bg-cyan-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <WifiIcon class="h-3.5 w-3.5" />
                  Scan & Connect
                </button>
              </div>
            </div>
          </template>
          <div class="p-4">
          <div v-if="slaveSystemInfo?.network_interfaces?.length" class="space-y-4">
            <div
              v-for="iface in slaveSystemInfo.network_interfaces"
              :key="iface.interface"
              class="p-3 rounded-lg bg-surface-hover"
            >
              <!-- Interface Header -->
              <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                  <WifiIcon v-if="iface.is_wifi" class="h-5 w-5 text-blue-500" />
                  <GlobeAltIcon v-else class="h-5 w-5 text-emerald-500" />
                  <span class="font-bold text-primary">{{ iface.interface }}</span>
                  <span v-if="iface.is_wifi && iface.wifi_ssid" class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400">
                    {{ iface.wifi_ssid }}
                  </span>
                </div>
              </div>

              <!-- IP and Netmask -->
              <div class="grid grid-cols-2 gap-2 text-sm mb-2">
                <div>
                  <span class="text-muted">IP Address</span>
                  <p class="font-mono font-medium text-primary">{{ iface.ip_address || 'N/A' }}</p>
                </div>
                <div>
                  <span class="text-muted">Netmask</span>
                  <p class="font-mono font-medium text-primary">{{ iface.netmask || 'N/A' }}</p>
                </div>
              </div>

              <!-- MAC Address -->
              <div v-if="iface.mac_address" class="text-sm mb-2">
                <span class="text-muted">MAC Address</span>
                <p class="font-mono font-medium text-primary">{{ iface.mac_address }}</p>
              </div>

              <!-- WiFi Signal if available -->
              <div v-if="iface.is_wifi && iface.wifi_ssid" class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between text-sm mb-2">
                  <span class="text-muted">WiFi Signal</span>
                  <span class="font-medium text-primary">{{ iface.wifi_signal_dbm }} dBm ({{ iface.wifi_signal_percent || 0 }}%)</span>
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
                  <span :class="[
                    'text-xs font-medium w-16 text-right',
                    (iface.wifi_signal_percent || 0) >= 75 ? 'text-emerald-500' :
                    (iface.wifi_signal_percent || 0) >= 50 ? 'text-amber-500' : 'text-red-500'
                  ]">
                    {{ (iface.wifi_signal_percent || 0) >= 75 ? 'Excellent' : (iface.wifi_signal_percent || 0) >= 50 ? 'Good' : 'Weak' }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Gateway and DNS -->
            <div v-if="slaveSystemInfo.default_gateway || slaveSystemInfo.dns_servers?.length" class="p-3 rounded-lg bg-surface-hover">
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div v-if="slaveSystemInfo.default_gateway">
                  <span class="text-muted">Default Gateway</span>
                  <p class="font-mono font-medium text-primary">{{ slaveSystemInfo.default_gateway }}</p>
                </div>
                <div v-if="slaveSystemInfo.dns_servers?.length">
                  <span class="text-muted">DNS Servers</span>
                  <p class="font-mono font-medium text-primary">{{ slaveSystemInfo.dns_servers.join(', ') }}</p>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-4 text-muted">
            Network information not available
          </div>
          </div>
        </Card>
          </div>
        </div>
      </Card>

      <!-- Notification Settings Card (Collapsible) -->
      <Card :padding="false">
        <button
          @click="notificationSectionExpanded = !notificationSectionExpanded"
          class="w-full p-4 flex items-center gap-4 hover:bg-surface-hover transition-colors rounded-lg"
        >
          <div class="p-3 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 shadow-lg">
            <BellIcon class="h-6 w-6 text-white" />
          </div>
          <div class="flex-1 text-left">
            <h3 class="text-lg font-semibold text-primary">Notification Settings</h3>
            <p class="text-sm text-secondary">Configure GenSlave failsafe notifications (Apprise)</p>
          </div>
          <div :class="['p-2 rounded-lg transition-colors', notificationSectionExpanded ? 'bg-purple-100 dark:bg-purple-500/20' : 'bg-gray-100 dark:bg-gray-700']">
            <ChevronDownIcon :class="['h-5 w-5 transition-transform duration-200', notificationSectionExpanded ? 'rotate-180 text-purple-600 dark:text-purple-400' : 'text-gray-500']" />
          </div>
        </button>
        <div v-show="notificationSectionExpanded" class="p-4 pt-2 space-y-6 border-t border-gray-200 dark:border-gray-700">
          <!-- Loading state -->
          <div v-if="loadingNotifications" class="text-center py-4">
            <ArrowPathIcon class="h-6 w-6 animate-spin mx-auto text-primary" />
            <p class="text-sm text-muted mt-2">Loading notification settings...</p>
          </div>

          <template v-else>
            <!-- Enable/Disable Toggle -->
            <div class="flex items-center justify-between p-4 rounded-lg bg-surface-hover">
              <div>
                <h4 class="text-sm font-medium text-primary">Notifications Enabled</h4>
                <p class="text-xs text-muted mt-1">
                  When enabled, GenSlave sends notifications on failsafe events
                </p>
              </div>
              <button
                @click="toggleNotificationsEnabled"
                :disabled="savingNotificationEnabled"
                :class="[
                  'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                  notificationConfig.enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                ]"
              >
                <span
                  :class="[
                    'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                    notificationConfig.enabled ? 'translate-x-5' : 'translate-x-0'
                  ]"
                />
              </button>
            </div>

            <!-- Apprise URLs -->
            <div class="p-4 rounded-lg bg-surface-hover">
              <div class="flex items-center justify-between mb-3">
                <div>
                  <h4 class="text-sm font-medium text-primary">Notification Services (Apprise URLs)</h4>
                  <p class="text-xs text-muted mt-1">
                    Configure notification endpoints -
                    <a href="https://github.com/caronc/apprise/wiki" target="_blank" class="text-blue-500 hover:underline">
                      See Apprise docs
                    </a>
                  </p>
                </div>
                <span :class="['text-xs px-2 py-1 rounded-full', notificationConfig.configured ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-500']">
                  {{ notificationConfig.apprise_urls?.length || 0 }} configured
                </span>
              </div>

              <!-- URL List -->
              <div v-if="editableAppriseUrls.length" class="space-y-2 mb-3">
                <div
                  v-for="(url, index) in editableAppriseUrls"
                  :key="index"
                  class="flex items-center gap-2"
                >
                  <input
                    v-model="editableAppriseUrls[index]"
                    type="text"
                    :placeholder="getUrlPlaceholder(index)"
                    class="input flex-1 font-mono text-sm"
                  />
                  <button
                    @click="removeAppriseUrl(index)"
                    class="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-500/20 rounded"
                    title="Remove URL"
                  >
                    <TrashIcon class="h-4 w-4" />
                  </button>
                </div>
              </div>

              <!-- Add URL Button -->
              <button
                @click="addAppriseUrl"
                class="btn-secondary text-sm flex items-center gap-1"
              >
                <PlusIcon class="h-4 w-4" />
                Add Notification URL
              </button>

              <!-- Save URLs Button -->
              <div v-if="appriseUrlsChanged" class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  @click="saveAppriseUrls"
                  :disabled="savingAppriseUrls"
                  class="btn-primary flex items-center gap-2"
                >
                  <ArrowPathIcon v-if="savingAppriseUrls" class="h-4 w-4 animate-spin" />
                  <CheckCircleIcon v-else class="h-4 w-4" />
                  Save Notification URLs
                </button>
              </div>
            </div>

            <!-- Cooldown Settings -->
            <div class="p-4 rounded-lg bg-surface-hover">
              <h4 class="text-sm font-medium text-primary mb-3">Cooldown Settings</h4>
              <p class="text-xs text-muted mb-4">
                Prevent notification flapping by setting minimum time between repeated notifications
              </p>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-secondary mb-1">
                    Failsafe Cooldown (minutes)
                  </label>
                  <input
                    v-model.number="cooldownSettings.failsafe_cooldown_minutes"
                    type="number"
                    min="1"
                    max="60"
                    class="input w-full"
                  />
                  <p class="text-xs text-muted mt-1">
                    Last sent: {{ formatCooldownTime(cooldownSettings.last_failsafe_notification_at) }}
                  </p>
                </div>
                <div>
                  <label class="block text-sm font-medium text-secondary mb-1">
                    Restored Cooldown (minutes)
                  </label>
                  <input
                    v-model.number="cooldownSettings.restored_cooldown_minutes"
                    type="number"
                    min="1"
                    max="60"
                    class="input w-full"
                  />
                  <p class="text-xs text-muted mt-1">
                    Last sent: {{ formatCooldownTime(cooldownSettings.last_restored_notification_at) }}
                  </p>
                </div>
              </div>

              <div class="flex items-center gap-3 mt-4">
                <button
                  @click="saveCooldownSettings"
                  :disabled="savingCooldownSettings"
                  class="btn-primary flex items-center gap-2"
                >
                  <ArrowPathIcon v-if="savingCooldownSettings" class="h-4 w-4 animate-spin" />
                  <CheckCircleIcon v-else class="h-4 w-4" />
                  Save Cooldown Settings
                </button>
                <button
                  @click="clearAllCooldowns"
                  :disabled="clearingCooldown"
                  class="btn-secondary flex items-center gap-2"
                  title="Clear cooldown timers to allow immediate notifications"
                >
                  <ArrowPathIcon v-if="clearingCooldown" class="h-4 w-4 animate-spin" />
                  <ClockIcon v-else class="h-4 w-4" />
                  Clear Cooldowns
                </button>
              </div>
            </div>

            <!-- Test Notification -->
            <div class="flex items-center justify-between p-4 rounded-lg bg-surface-hover">
              <div>
                <h4 class="text-sm font-medium text-primary">Test Notification</h4>
                <p class="text-xs text-muted mt-1">
                  Send a test message to all configured notification services
                </p>
              </div>
              <button
                @click="sendTestNotification"
                :disabled="sendingTestNotification || !notificationConfig.configured"
                class="btn-secondary flex items-center gap-2"
              >
                <ArrowPathIcon v-if="sendingTestNotification" class="h-4 w-4 animate-spin" />
                <BellIcon v-else class="h-4 w-4" />
                Send Test
              </button>
            </div>
          </template>
        </div>
      </Card>

      <!-- Connection Settings Card (Collapsible) -->
      <Card :padding="false">
        <button
          @click="connectionSectionExpanded = !connectionSectionExpanded"
          class="w-full p-4 flex items-center gap-4 hover:bg-surface-hover transition-colors rounded-lg"
        >
          <div class="p-3 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-600 shadow-lg">
            <Cog6ToothIcon class="h-6 w-6 text-white" />
          </div>
          <div class="flex-1 text-left">
            <h3 class="text-lg font-semibold text-primary">Connection Settings</h3>
            <p class="text-sm text-secondary">Configure GenSlave communication and network</p>
          </div>
          <div :class="['p-2 rounded-lg transition-colors', connectionSectionExpanded ? 'bg-cyan-100 dark:bg-cyan-500/20' : 'bg-gray-100 dark:bg-gray-700']">
            <ChevronDownIcon :class="['h-5 w-5 transition-transform duration-200', connectionSectionExpanded ? 'rotate-180 text-cyan-600 dark:text-cyan-400' : 'text-gray-500']" />
          </div>
        </button>
        <div v-show="connectionSectionExpanded" class="p-4 pt-2 space-y-6 border-t border-gray-200 dark:border-gray-700">
          <!-- GenSlave Connection Section -->
          <div class="p-4 rounded-lg bg-surface-hover">
            <h4 class="text-sm font-medium text-primary mb-3">GenSlave Connection</h4>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-secondary mb-1">GenSlave IP Address</label>
                <input
                  v-model="slaveConfig.genslave_ip"
                  type="text"
                  :placeholder="currentConfiguredIp || '192.168.1.100'"
                  class="input"
                  @focus="isEditingConfig = true"
                  @blur="isEditingConfig = false"
                />
                <p class="text-xs text-muted mt-1">IP address of the GenSlave device</p>
              </div>
              <div>
                <label class="block text-sm font-medium text-secondary mb-1">API URL (auto-generated)</label>
                <div class="input bg-gray-100 dark:bg-gray-800 text-primary font-mono text-sm">
                  http://{{ slaveConfig.genslave_ip || currentConfiguredIp || '&lt;IP&gt;' }}:8001
                </div>
                <p class="text-xs text-muted mt-1">URL used to communicate with GenSlave</p>
              </div>
            </div>
            <p class="text-xs text-emerald-600 dark:text-emerald-400 mt-3">
              IP changes take effect immediately - no restart required
            </p>
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

          <!-- API Key Section -->
          <div class="p-4 rounded-lg bg-surface-hover">
            <div class="flex items-center gap-2 mb-3">
              <KeyIcon class="h-5 w-5 text-primary" />
              <h4 class="text-sm font-medium text-primary">API Authentication</h4>
            </div>

            <!-- Current API Key (masked) -->
            <div v-if="apiSecret" class="mb-4">
              <label class="block text-sm font-medium text-secondary mb-1">Current API Secret</label>
              <div class="flex items-center gap-2">
                <div class="input flex-1 font-mono bg-gray-100 dark:bg-gray-800 flex items-center justify-between">
                  <span>{{ showApiSecret ? apiSecret : '••••••••••••••••••••••••••••••••' }}</span>
                  <div class="flex items-center gap-1">
                    <button
                      @click="showApiSecret = !showApiSecret"
                      class="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                      title="Toggle visibility"
                    >
                      <EyeIcon v-if="!showApiSecret" class="h-4 w-4 text-secondary" />
                      <EyeSlashIcon v-else class="h-4 w-4 text-secondary" />
                    </button>
                    <button
                      @click="copyApiSecret"
                      class="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
                      title="Copy to clipboard"
                    >
                      <ClipboardDocumentIcon class="h-4 w-4 text-secondary" />
                    </button>
                  </div>
                </div>
              </div>
              <p class="text-xs text-muted mt-1">This key must match the API_SECRET in GenSlave's .env file</p>
            </div>

            <!-- Set New API Key -->
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Change API Secret</label>
              <div class="flex items-center gap-2">
                <input
                  v-model="newApiSecret"
                  type="text"
                  placeholder="Enter new API secret"
                  class="input flex-1 font-mono"
                  @focus="isEditingConfig = true"
                  @blur="isEditingConfig = false"
                />
                <button
                  @click="generateApiSecret"
                  class="btn-secondary"
                  title="Generate random secret"
                >
                  Generate
                </button>
                <button
                  @click="rotateApiKey"
                  :disabled="savingApiSecret || !newApiSecret"
                  class="btn-primary flex items-center gap-2"
                >
                  <ArrowPathIcon v-if="savingApiSecret" class="h-4 w-4 animate-spin" />
                  <span v-else>Save</span>
                </button>
              </div>
              <p class="text-xs text-muted mt-2">
                Updates API key on both GenMaster and GenSlave simultaneously
              </p>
            </div>
          </div>

          <!-- Save Settings Button (inside collapsible) -->
          <div class="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
            <button @click="saveSlaveConfig" :disabled="savingSlaveConfig" class="btn-primary flex items-center gap-2">
              <ArrowPathIcon v-if="savingSlaveConfig" class="h-4 w-4 animate-spin" />
              <CheckCircleIcon v-else class="h-4 w-4" />
              Save Settings
            </button>
          </div>
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

    <!-- Reboot Window Banner (shown during intentional reboot) -->
    <div
      v-if="inRebootWindow"
      class="rounded-xl p-4 border-2 border-blue-500 bg-gradient-to-r from-blue-500/10 to-blue-500/5"
    >
      <div class="flex items-center gap-4">
        <div class="p-3 rounded-xl bg-blue-500/30">
          <ArrowPathIcon class="h-8 w-8 text-blue-500 animate-spin" />
        </div>
        <div>
          <h2 class="text-xl font-bold text-blue-700 dark:text-blue-300">
            GenSlave Rebooting...
          </h2>
          <p class="text-sm text-blue-600 dark:text-blue-400">
            System will be back online in ~{{ rebootRemainingSeconds }}s. Warnings suppressed during reboot.
          </p>
        </div>
      </div>
    </div>

    <!-- Shutdown Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showShutdownConfirm" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
          <div class="flex items-center gap-4 mb-4">
            <div class="p-3 rounded-full bg-red-100 dark:bg-red-500/20">
              <ExclamationTriangleIcon class="h-8 w-8 text-red-500" />
            </div>
            <h3 class="text-xl font-bold text-primary">Shutdown GenSlave</h3>
          </div>
          <div class="space-y-3 mb-6">
            <p class="text-secondary">
              Are you sure you want to <strong>shut down</strong> the GenSlave Raspberry Pi?
            </p>
            <div class="p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30">
              <p class="text-sm text-red-700 dark:text-red-300 font-medium">
                ⚠️ Warning: This will make GenSlave completely unreachable!
              </p>
              <ul class="text-sm text-red-600 dark:text-red-400 mt-2 list-disc list-inside">
                <li>The generator relay will be turned OFF</li>
                <li>You will need physical access to power it back on</li>
                <li>All remote control capability will be lost</li>
              </ul>
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button
              @click="showShutdownConfirm = false"
              class="btn-secondary"
            >
              Cancel
            </button>
            <button
              @click="executeShutdown"
              :disabled="shuttingDown"
              class="px-4 py-2 rounded-lg font-medium text-white bg-red-500 hover:bg-red-600 transition-colors disabled:opacity-50"
            >
              <span v-if="shuttingDown">Shutting down...</span>
              <span v-else>Shutdown Now</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Reboot Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showRebootConfirm" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6">
          <div class="flex items-center gap-4 mb-4">
            <div class="p-3 rounded-full bg-amber-100 dark:bg-amber-500/20">
              <ArrowPathIcon class="h-8 w-8 text-amber-500" />
            </div>
            <h3 class="text-xl font-bold text-primary">Reboot GenSlave</h3>
          </div>
          <div class="space-y-3 mb-6">
            <p class="text-secondary">
              Are you sure you want to <strong>reboot</strong> the GenSlave Raspberry Pi?
            </p>
            <div class="p-3 rounded-lg bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30">
              <p class="text-sm text-amber-700 dark:text-amber-300 font-medium">
                ℹ️ GenSlave will be temporarily unavailable
              </p>
              <ul class="text-sm text-amber-600 dark:text-amber-400 mt-2 list-disc list-inside">
                <li>The generator relay will be turned OFF during reboot</li>
                <li>System will restart automatically (~60-90 seconds)</li>
                <li>"GenSlave down" warnings will be suppressed</li>
              </ul>
            </div>
          </div>
          <div class="flex justify-end gap-3">
            <button
              @click="showRebootConfirm = false"
              class="btn-secondary"
            >
              Cancel
            </button>
            <button
              @click="executeReboot"
              :disabled="rebooting"
              class="px-4 py-2 rounded-lg font-medium text-white bg-amber-500 hover:bg-amber-600 transition-colors disabled:opacity-50"
            >
              <span v-if="rebooting">Rebooting...</span>
              <span v-else>Reboot Now</span>
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- WiFi Configuration Modal -->
    <Teleport to="body">
      <div v-if="showWifiConfigModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="p-3 rounded-full bg-cyan-100 dark:bg-cyan-500/20">
                <WifiIcon class="h-6 w-6 text-cyan-500" />
              </div>
              <h3 class="text-xl font-bold text-primary">Configure GenSlave WiFi</h3>
            </div>
            <button
              @click="closeWifiConfigModal"
              class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <XCircleIcon class="h-5 w-5 text-gray-500" />
            </button>
          </div>

          <!-- Error display -->
          <div v-if="wifiError" class="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30">
            <p class="text-sm text-red-700 dark:text-red-300">{{ wifiError }}</p>
          </div>

          <!-- Network List -->
          <div class="mb-4">
            <div class="flex items-center justify-between mb-2">
              <label class="text-sm font-medium text-secondary">Available Networks</label>
              <button
                @click="scanSlaveWifiNetworks"
                :disabled="wifiScanning"
                class="btn-secondary text-xs flex items-center gap-1"
              >
                <ArrowPathIcon :class="['h-3.5 w-3.5', wifiScanning ? 'animate-spin' : '']" />
                Refresh
              </button>
            </div>

            <div v-if="wifiScanning" class="py-8 text-center">
              <ArrowPathIcon class="h-8 w-8 animate-spin mx-auto text-cyan-500" />
              <p class="text-sm text-muted mt-2">Scanning for networks...</p>
            </div>

            <div v-else-if="wifiNetworks.length === 0" class="py-8 text-center text-muted">
              <WifiIcon class="h-8 w-8 mx-auto opacity-50 mb-2" />
              <p class="text-sm">No networks found</p>
            </div>

            <div v-else class="max-h-64 overflow-y-auto space-y-1 border border-gray-200 dark:border-gray-700 rounded-lg">
              <button
                v-for="network in wifiNetworks"
                :key="network.ssid"
                @click="selectWifiNetwork(network)"
                :class="[
                  'w-full p-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors',
                  selectedWifiNetwork?.ssid === network.ssid ? 'bg-cyan-50 dark:bg-cyan-500/10 border-l-4 border-cyan-500' : ''
                ]"
              >
                <div class="flex items-center gap-3">
                  <WifiIcon :class="[
                    'h-5 w-5',
                    network.signal_percent >= 70 ? 'text-emerald-500' :
                    network.signal_percent >= 40 ? 'text-amber-500' : 'text-red-500'
                  ]" />
                  <div class="text-left">
                    <p class="font-medium text-primary">{{ network.ssid }}</p>
                    <p class="text-xs text-muted">{{ network.security }}</p>
                  </div>
                </div>
                <div class="text-right">
                  <p class="text-sm font-medium text-primary">{{ network.signal_percent }}%</p>
                </div>
              </button>
            </div>
          </div>

          <!-- Password Input (shown when network is selected) -->
          <div v-if="selectedWifiNetwork" class="mb-4">
            <div class="p-3 rounded-lg bg-cyan-50 dark:bg-cyan-500/10 mb-3">
              <p class="text-sm font-medium text-cyan-700 dark:text-cyan-300">
                Selected: {{ selectedWifiNetwork.ssid }}
              </p>
            </div>

            <div v-if="selectedWifiNetwork.security !== 'Open'">
              <label class="block text-sm font-medium text-secondary mb-1">Password</label>
              <input
                v-model="wifiPassword"
                type="password"
                placeholder="Enter WiFi password"
                class="input w-full"
                @keyup.enter="connectToSlaveWifi"
              />
            </div>
            <p v-else class="text-sm text-muted">
              This is an open network (no password required)
            </p>
          </div>

          <!-- Action Buttons -->
          <div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              @click="closeWifiConfigModal"
              class="btn-secondary"
            >
              Cancel
            </button>
            <button
              @click="connectToSlaveWifi"
              :disabled="wifiConnecting || !selectedWifiNetwork"
              class="px-4 py-2 rounded-lg font-medium text-white bg-cyan-500 hover:bg-cyan-600 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowPathIcon v-if="wifiConnecting" class="h-4 w-4 animate-spin" />
              <WifiIcon v-else class="h-4 w-4" />
              {{ wifiConnecting ? 'Connecting...' : 'Connect' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Add Known Network Modal -->
    <Teleport to="body">
      <div v-if="showAddNetworkModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="p-3 rounded-full bg-emerald-100 dark:bg-emerald-500/20">
                <PlusIcon class="h-6 w-6 text-emerald-500" />
              </div>
              <h3 class="text-xl font-bold text-primary">Add Known Network</h3>
            </div>
            <button
              @click="closeAddNetworkModal"
              class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <XCircleIcon class="h-5 w-5 text-gray-500" />
            </button>
          </div>

          <p class="text-sm text-secondary mb-4">
            Add a WiFi network that GenSlave will automatically connect to when available.
            Useful for pre-configuring networks before deployment.
          </p>

          <!-- Error display -->
          <div v-if="addNetworkError" class="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30">
            <p class="text-sm text-red-700 dark:text-red-300">{{ addNetworkError }}</p>
          </div>

          <!-- Add Network Form -->
          <div class="space-y-4 mb-6">
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Network Name (SSID)</label>
              <input
                v-model="addNetworkSsid"
                type="text"
                placeholder="Enter WiFi network name"
                class="input w-full"
                maxlength="32"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-secondary mb-1">Password</label>
              <input
                v-model="addNetworkPassword"
                type="password"
                placeholder="Enter WiFi password (min 8 characters)"
                class="input w-full"
                @keyup.enter="addKnownNetwork"
              />
            </div>
            <div class="flex items-center gap-2">
              <input
                v-model="addNetworkAutoConnect"
                type="checkbox"
                id="autoConnect"
                class="rounded border-gray-300 text-emerald-500 focus:ring-emerald-500"
              />
              <label for="autoConnect" class="text-sm text-secondary">
                Auto-connect when network is available
              </label>
            </div>
          </div>

          <!-- Saved Networks List -->
          <div v-if="savedNetworks.length > 0" class="mb-6">
            <h4 class="text-sm font-medium text-secondary mb-2">Saved Networks</h4>
            <div class="space-y-2 max-h-40 overflow-y-auto">
              <div
                v-for="network in savedNetworks"
                :key="network.name"
                class="flex items-center justify-between p-3 rounded-lg bg-surface-hover"
              >
                <div class="flex items-center gap-2">
                  <WifiIcon class="h-4 w-4 text-emerald-500" />
                  <span class="text-sm font-medium text-primary">{{ network.name }}</span>
                  <span v-if="network.auto_connect" class="text-xs px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                    Auto
                  </span>
                </div>
                <button
                  @click="deleteSavedNetwork(network.name)"
                  :disabled="deletingNetwork === network.name"
                  class="p-1.5 text-red-500 hover:bg-red-100 dark:hover:bg-red-500/20 rounded transition-colors"
                  title="Delete network"
                >
                  <TrashIcon v-if="deletingNetwork !== network.name" class="h-4 w-4" />
                  <ArrowPathIcon v-else class="h-4 w-4 animate-spin" />
                </button>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              @click="closeAddNetworkModal"
              class="btn-secondary"
            >
              Close
            </button>
            <button
              @click="addKnownNetwork"
              :disabled="addingNetwork || !addNetworkSsid.trim() || addNetworkPassword.length < 8"
              class="px-4 py-2 rounded-lg font-medium text-white bg-emerald-500 hover:bg-emerald-600 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <ArrowPathIcon v-if="addingNetwork" class="h-4 w-4 animate-spin" />
              <PlusIcon v-else class="h-4 w-4" />
              {{ addingNetwork ? 'Adding...' : 'Add Network' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import api, { genslaveApi, configApi } from '@/services/api'
import Card from '@/components/common/Card.vue'
import HeartbeatLoader from '@/components/common/HeartbeatLoader.vue'
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  Cog6ToothIcon,
  CpuChipIcon,
  GlobeAltIcon,
  WifiIcon,
  BoltIcon,
  ServerIcon,
  ExclamationTriangleIcon,
  ClipboardDocumentIcon,
  EyeIcon,
  EyeSlashIcon,
  KeyIcon,
  BellIcon,
  TrashIcon,
  PlusIcon,
  ClockIcon,
  PowerIcon,
  XCircleIcon,
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
const relayArmed = ref(false)  // Read-only display, control is on Generator page

// GenSlave connection settings
const slaveConfig = ref({
  heartbeat_interval_seconds: 30,
  genslave_ip: '',
})
const currentConfiguredIp = ref('')  // Current IP from database (for display)
const savingSlaveConfig = ref(false)
const isEditingConfig = ref(false)  // Prevent polling from overwriting user input


// API Key management
const apiSecret = ref('')  // Current API secret from database
const newApiSecret = ref('')  // New API secret to set
const showApiSecret = ref(false)  // Toggle visibility
const savingApiSecret = ref(false)

// Collapsible sections
const systemInfoSectionExpanded = ref(false)  // Start collapsed
const notificationSectionExpanded = ref(false)
const connectionSectionExpanded = ref(false)

// System power control
const showShutdownConfirm = ref(false)
const showRebootConfirm = ref(false)
const shuttingDown = ref(false)
const rebooting = ref(false)
const inRebootWindow = ref(false)
const rebootRemainingSeconds = ref(0)

// WiFi configuration modal state
const showWifiConfigModal = ref(false)
const wifiNetworks = ref([])
const wifiScanning = ref(false)
const wifiConnecting = ref(false)
const selectedWifiNetwork = ref(null)
const wifiPassword = ref('')
const wifiError = ref(null)

// Add known network state
const showAddNetworkModal = ref(false)
const addNetworkSsid = ref('')
const addNetworkPassword = ref('')
const addNetworkAutoConnect = ref(true)
const addingNetwork = ref(false)
const addNetworkError = ref(null)

// Saved networks state
const savedNetworks = ref([])
const loadingSavedNetworks = ref(false)
const deletingNetwork = ref(null)

// Notification management
const loadingNotifications = ref(false)
const notificationConfig = ref({
  apprise_urls: [],
  configured: false,
  enabled: false,
})
const editableAppriseUrls = ref([])  // Editable copy of URLs
const originalAppriseUrls = ref([])  // Track original for change detection
const cooldownSettings = ref({
  failsafe_cooldown_minutes: 5,
  restored_cooldown_minutes: 5,
  last_failsafe_notification_at: null,
  last_restored_notification_at: null,
})
const savingAppriseUrls = ref(false)
const savingCooldownSettings = ref(false)
const savingNotificationEnabled = ref(false)
const sendingTestNotification = ref(false)
const clearingCooldown = ref(false)

// Polling
let pollInterval = null

// Load GenSlave info using cached data from unified SlaveStatusService
// This ensures consistent status with the Generator Tab
async function loadSlaveInfo(forceRefresh = false) {
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
          slaveConfig.value.heartbeat_interval_seconds = configRes.data.heartbeat_interval_seconds || 30
          slaveConfig.value.genslave_ip = configRes.data.genslave_ip || ''
          currentConfiguredIp.value = configRes.data.genslave_ip || ''
          apiSecret.value = configRes.data.slave_api_secret || ''
        }
      } catch (e) {
        console.warn('Failed to load config for GenSlave:', e)
      }
    }

    // If force refresh requested (manual button), refresh the cache first
    if (forceRefresh) {
      try {
        await genslaveApi.refreshCache()
      } catch (e) {
        console.warn('Failed to refresh cache:', e)
      }
    }

    // Use cached data from the unified SlaveStatusService
    // This provides instant response and consistent status with Generator Tab
    const cachedRes = await genslaveApi.getStatusCached().catch((e) => {
      console.warn('Failed to get cached status:', e)
      return { data: null }
    })

    if (cachedRes.data) {
      const cached = cachedRes.data

      // Update connection status from cache
      slaveInfo.value = {
        online: cached.is_online,
        last_heartbeat: cached.heartbeat?.last_success,
        details: cached.data?.system_info,
        error: cached.last_error,
        is_stale: cached.is_stale,
        cache_age: cached.cache_age_seconds,
      }

      // Extract data from cache
      slaveSystemInfo.value = cached.data?.system_info || null
      slaveHealthStatus.value = cached.data?.health || null
      slaveFailsafeStatus.value = cached.data?.failsafe || null
      slaveRelayState.value = cached.data?.relay_state || null

      // Update armed state from cached relay state or health
      relayArmed.value = cached.data?.relay_state?.armed || cached.data?.health?.armed || false

      // Show warning if data is stale
      if (cached.is_stale && !pollInterval) {
        console.warn('GenSlave data is stale - cache age:', cached.cache_age_seconds, 'seconds')
      }
    } else {
      // Fallback: no cached data available
      slaveInfo.value = { online: false, last_heartbeat: null, details: null, error: 'No cached data available' }
      slaveSystemInfo.value = null
      slaveHealthStatus.value = null
      slaveFailsafeStatus.value = null
      slaveRelayState.value = null
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

// Save GenSlave connection settings
async function saveSlaveConfig() {
  savingSlaveConfig.value = true

  try {
    await configApi.update({
      heartbeat_interval_seconds: slaveConfig.value.heartbeat_interval_seconds,
      genslave_ip: slaveConfig.value.genslave_ip,
    })
    // Update the displayed current IP
    currentConfiguredIp.value = slaveConfig.value.genslave_ip
    notificationStore.success('GenSlave settings saved - changes take effect immediately')
  } catch (error) {
    notificationStore.error('Failed to save GenSlave settings')
  } finally {
    savingSlaveConfig.value = false
  }
}

// Rotate API key on both GenMaster and GenSlave
async function rotateApiKey() {
  if (!newApiSecret.value.trim()) {
    notificationStore.error('Please enter a new API secret')
    return
  }

  if (newApiSecret.value.length < 16) {
    notificationStore.error('API secret must be at least 16 characters')
    return
  }

  savingApiSecret.value = true
  try {
    await api.post('/health/rotate-api-key', { new_key: newApiSecret.value })
    apiSecret.value = newApiSecret.value
    newApiSecret.value = ''
    notificationStore.success('API key rotated successfully on both GenMaster and GenSlave')
  } catch (error) {
    const detail = error.response?.data?.detail || 'Failed to rotate API key'
    notificationStore.error(detail)
  } finally {
    savingApiSecret.value = false
  }
}

// Generate random API secret
function generateApiSecret() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let secret = ''
  for (let i = 0; i < 32; i++) {
    secret += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  newApiSecret.value = secret
}

// Copy API secret to clipboard
async function copyApiSecret() {
  try {
    await navigator.clipboard.writeText(apiSecret.value || newApiSecret.value)
    notificationStore.success('API secret copied to clipboard')
  } catch (error) {
    notificationStore.error('Failed to copy to clipboard')
  }
}

// =========================================================================
// Notification Management
// =========================================================================

// Load notification configuration from GenSlave
async function loadNotificationConfig() {
  loadingNotifications.value = true
  try {
    const [configRes, settingsRes] = await Promise.all([
      genslaveApi.getNotifications().catch((e) => {
        console.warn('Failed to get GenSlave notifications:', e)
        return { data: null }
      }),
      genslaveApi.getNotificationSettings().catch((e) => {
        console.warn('Failed to get GenSlave notification settings:', e)
        return { data: null }
      }),
    ])

    if (configRes.data) {
      notificationConfig.value = configRes.data
      // Initialize editable URLs from masked URLs (user will replace with real ones)
      editableAppriseUrls.value = [...(configRes.data.apprise_urls || [])]
      originalAppriseUrls.value = [...(configRes.data.apprise_urls || [])]
    }

    if (settingsRes.data) {
      cooldownSettings.value = settingsRes.data
    }
  } catch (error) {
    console.error('Failed to load notification config:', error)
  } finally {
    loadingNotifications.value = false
  }
}

// Toggle notifications enabled/disabled
async function toggleNotificationsEnabled() {
  savingNotificationEnabled.value = true
  const newState = !notificationConfig.value.enabled
  try {
    await genslaveApi.setNotificationsEnabled(newState)
    notificationConfig.value.enabled = newState
    notificationStore.success(`GenSlave notifications ${newState ? 'enabled' : 'disabled'}`)
  } catch (error) {
    notificationStore.error(`Failed to ${newState ? 'enable' : 'disable'} notifications`)
  } finally {
    savingNotificationEnabled.value = false
  }
}

// Add a new Apprise URL field
function addAppriseUrl() {
  editableAppriseUrls.value.push('')
}

// Remove an Apprise URL
function removeAppriseUrl(index) {
  editableAppriseUrls.value.splice(index, 1)
}

// Get placeholder text for URL input
function getUrlPlaceholder(index) {
  const examples = [
    'tgram://bottoken/chatid',
    'slack://token/channel',
    'discord://webhook_id/token',
    'mailto://user:pass@gmail.com',
  ]
  return examples[index % examples.length]
}

// Check if Apprise URLs have changed
const appriseUrlsChanged = computed(() => {
  const current = editableAppriseUrls.value.filter(u => u.trim())
  const original = originalAppriseUrls.value
  if (current.length !== original.length) return true
  return current.some((url, i) => url !== original[i])
})

// Save Apprise URLs to GenSlave
async function saveAppriseUrls() {
  savingAppriseUrls.value = true
  try {
    // Filter out empty URLs
    const urls = editableAppriseUrls.value.filter(u => u.trim())
    await genslaveApi.setNotifications(urls)
    originalAppriseUrls.value = [...urls]
    editableAppriseUrls.value = [...urls]
    notificationConfig.value.configured = urls.length > 0
    notificationStore.success('Notification URLs saved to GenSlave')
    // Reload to get masked URLs
    await loadNotificationConfig()
  } catch (error) {
    notificationStore.error('Failed to save notification URLs')
  } finally {
    savingAppriseUrls.value = false
  }
}

// Save cooldown settings
async function saveCooldownSettings() {
  savingCooldownSettings.value = true
  try {
    await genslaveApi.setNotificationSettings({
      failsafe_cooldown_minutes: cooldownSettings.value.failsafe_cooldown_minutes,
      restored_cooldown_minutes: cooldownSettings.value.restored_cooldown_minutes,
    })
    notificationStore.success('Cooldown settings saved')
  } catch (error) {
    notificationStore.error('Failed to save cooldown settings')
  } finally {
    savingCooldownSettings.value = false
  }
}

// Clear all cooldowns
async function clearAllCooldowns() {
  clearingCooldown.value = true
  try {
    await genslaveApi.clearNotificationCooldown(null)  // null = clear both
    cooldownSettings.value.last_failsafe_notification_at = null
    cooldownSettings.value.last_restored_notification_at = null
    notificationStore.success('Notification cooldowns cleared')
  } catch (error) {
    notificationStore.error('Failed to clear cooldowns')
  } finally {
    clearingCooldown.value = false
  }
}

// Send test notification
async function sendTestNotification() {
  sendingTestNotification.value = true
  try {
    const response = await genslaveApi.testNotifications()
    if (response.data?.success) {
      notificationStore.success(`Test notification sent to ${response.data.configured_services || 0} services`)
    } else {
      notificationStore.warning(response.data?.message || 'Test notification may have failed')
    }
  } catch (error) {
    notificationStore.error('Failed to send test notification')
  } finally {
    sendingTestNotification.value = false
  }
}

// Format cooldown timestamp
function formatCooldownTime(timestamp) {
  if (!timestamp) return 'Never'
  return new Date(timestamp * 1000).toLocaleString()
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

// =========================================================================
// WiFi Configuration
// =========================================================================

async function openWifiConfigModal() {
  showWifiConfigModal.value = true
  wifiError.value = null
  wifiPassword.value = ''
  selectedWifiNetwork.value = null
  await scanSlaveWifiNetworks()
}

function closeWifiConfigModal() {
  showWifiConfigModal.value = false
  wifiNetworks.value = []
  wifiPassword.value = ''
  selectedWifiNetwork.value = null
  wifiError.value = null
}

async function scanSlaveWifiNetworks() {
  wifiScanning.value = true
  wifiError.value = null
  try {
    const response = await genslaveApi.scanWifiNetworks()
    if (response.data?.success) {
      wifiNetworks.value = response.data.networks || []
    } else {
      wifiError.value = response.data?.error || 'Failed to scan networks'
    }
  } catch (error) {
    wifiError.value = error.response?.data?.detail || 'Failed to scan WiFi networks'
  } finally {
    wifiScanning.value = false
  }
}

function selectWifiNetwork(network) {
  selectedWifiNetwork.value = network
  wifiPassword.value = ''
  wifiError.value = null
}

async function connectToSlaveWifi() {
  if (!selectedWifiNetwork.value) {
    wifiError.value = 'Please select a network'
    return
  }

  wifiConnecting.value = true
  wifiError.value = null

  try {
    const response = await genslaveApi.connectWifi({
      ssid: selectedWifiNetwork.value.ssid,
      password: wifiPassword.value || null,
    })

    if (response.data?.success) {
      notificationStore.success(response.data.message || `GenSlave connected to ${selectedWifiNetwork.value.ssid}`)
      closeWifiConfigModal()
      // Refresh slave info after a short delay
      setTimeout(() => {
        loadSlaveInfo(true)
      }, 2000)
    } else {
      wifiError.value = response.data?.error || 'Failed to connect'
    }
  } catch (error) {
    wifiError.value = error.response?.data?.detail || 'Failed to connect to WiFi'
  } finally {
    wifiConnecting.value = false
  }
}

// =========================================================================
// Add Known Network
// =========================================================================

function openAddNetworkModal() {
  showAddNetworkModal.value = true
  addNetworkSsid.value = ''
  addNetworkPassword.value = ''
  addNetworkAutoConnect.value = true
  addNetworkError.value = null
  loadSavedNetworks()
}

function closeAddNetworkModal() {
  showAddNetworkModal.value = false
  addNetworkSsid.value = ''
  addNetworkPassword.value = ''
  addNetworkError.value = null
}

async function loadSavedNetworks() {
  loadingSavedNetworks.value = true
  try {
    const response = await genslaveApi.listSavedWifiNetworks()
    if (response.data?.success) {
      savedNetworks.value = response.data.networks || []
    }
  } catch (error) {
    console.warn('Failed to load saved networks:', error)
  } finally {
    loadingSavedNetworks.value = false
  }
}

async function addKnownNetwork() {
  if (!addNetworkSsid.value.trim()) {
    addNetworkError.value = 'SSID is required'
    return
  }
  if (!addNetworkPassword.value || addNetworkPassword.value.length < 8) {
    addNetworkError.value = 'Password must be at least 8 characters'
    return
  }

  addingNetwork.value = true
  addNetworkError.value = null

  try {
    const response = await genslaveApi.addWifiNetwork({
      ssid: addNetworkSsid.value.trim(),
      password: addNetworkPassword.value,
      auto_connect: addNetworkAutoConnect.value,
    })

    if (response.data?.success) {
      notificationStore.success(response.data.message || `Network '${addNetworkSsid.value}' added`)
      addNetworkSsid.value = ''
      addNetworkPassword.value = ''
      loadSavedNetworks()
    } else {
      addNetworkError.value = response.data?.error || 'Failed to add network'
    }
  } catch (error) {
    addNetworkError.value = error.response?.data?.detail || 'Failed to add network'
  } finally {
    addingNetwork.value = false
  }
}

async function deleteSavedNetwork(name) {
  deletingNetwork.value = name
  try {
    const response = await genslaveApi.deleteWifiNetwork({ name })
    if (response.data?.success) {
      notificationStore.success(`Network '${name}' deleted`)
      loadSavedNetworks()
    } else {
      notificationStore.error(response.data?.error || 'Failed to delete network')
    }
  } catch (error) {
    notificationStore.error(error.response?.data?.detail || 'Failed to delete network')
  } finally {
    deletingNetwork.value = null
  }
}

// =========================================================================
// System Power Control
// =========================================================================

// Check if we're in an intentional reboot window
async function checkRebootStatus() {
  try {
    const response = await genslaveApi.getRebootStatus()
    inRebootWindow.value = response.data?.in_reboot_window || false
    rebootRemainingSeconds.value = response.data?.remaining_seconds || 0
  } catch {
    // Ignore errors
  }
}

// Handle shutdown button click
function handleShutdown() {
  showShutdownConfirm.value = true
}

// Execute shutdown
async function executeShutdown() {
  showShutdownConfirm.value = false
  shuttingDown.value = true
  try {
    await genslaveApi.shutdown()
    notificationStore.success('GenSlave shutdown initiated. System will power off shortly.')
    // Mark as offline after a short delay
    setTimeout(() => {
      slaveInfo.value.online = false
    }, 3000)
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to initiate shutdown'
    notificationStore.error(message)
  } finally {
    shuttingDown.value = false
  }
}

// Handle reboot button click
function handleReboot() {
  showRebootConfirm.value = true
}

// Execute reboot
async function executeReboot() {
  showRebootConfirm.value = false
  rebooting.value = true
  try {
    await genslaveApi.reboot()
    notificationStore.success('GenSlave reboot initiated. System will restart in ~60-90 seconds.')
    // Set local reboot window flag to suppress warnings
    inRebootWindow.value = true
    rebootRemainingSeconds.value = 120
    // Start countdown
    const countdownInterval = setInterval(() => {
      rebootRemainingSeconds.value--
      if (rebootRemainingSeconds.value <= 0) {
        inRebootWindow.value = false
        clearInterval(countdownInterval)
        // Refresh data after reboot window
        loadSlaveInfo(true)
      }
    }, 1000)
    // Mark as offline after a short delay
    setTimeout(() => {
      slaveInfo.value.online = false
    }, 3000)
  } catch (error) {
    const message = error.response?.data?.detail || 'Failed to initiate reboot'
    notificationStore.error(message)
  } finally {
    rebooting.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadSlaveInfo()
  loadNotificationConfig()
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
