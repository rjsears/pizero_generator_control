<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/system/SystemTerminal.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 17th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import { useThemeStore } from '@/stores/theme'
import Card from '@/components/common/Card.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import {
  CommandLineIcon,
  ServerStackIcon,
  ComputerDesktopIcon,
  PlayIcon,
  StopIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
} from '@heroicons/vue/24/outline'
import 'xterm/css/xterm.css'

const themeStore = useThemeStore()

const terminalRef = ref(null)
const terminal = ref(null)
const fitAddon = ref(null)
const websocket = ref(null)
const connected = ref(false)
const connecting = ref(false)
const error = ref(null)

// Target selection
const targets = ref({ containers: [], host_available: true })
const loadingTargets = ref(false)
const selectedTarget = ref(null)
const selectedType = ref('container') // 'container' or 'host'

// Terminal themes
const terminalThemes = {
  dark: {
    background: '#1a1b26',
    foreground: '#a9b1d6',
    cursor: '#c0caf5',
    black: '#32344a',
    red: '#f7768e',
    green: '#9ece6a',
    yellow: '#e0af68',
    blue: '#7aa2f7',
    magenta: '#bb9af7',
    cyan: '#7dcfff',
    white: '#a9b1d6',
    brightBlack: '#444b6a',
    brightRed: '#ff7a93',
    brightGreen: '#b9f27c',
    brightYellow: '#ff9e64',
    brightBlue: '#7da6ff',
    brightMagenta: '#c0a8e6',
    brightCyan: '#0db9d7',
    brightWhite: '#c0caf5',
  },
  light: {
    background: '#f8fafc',
    foreground: '#1e293b',
    cursor: '#475569',
    black: '#e2e8f0',
    red: '#dc2626',
    green: '#16a34a',
    yellow: '#ca8a04',
    blue: '#2563eb',
    magenta: '#9333ea',
    cyan: '#0891b2',
    white: '#1e293b',
    brightBlack: '#cbd5e1',
    brightRed: '#ef4444',
    brightGreen: '#22c55e',
    brightYellow: '#eab308',
    brightBlue: '#3b82f6',
    brightMagenta: '#a855f7',
    brightCyan: '#06b6d4',
    brightWhite: '#0f172a',
  },
}

const currentTheme = computed(() =>
  themeStore.colorMode === 'dark' ? terminalThemes.dark : terminalThemes.light
)

// Get WebSocket URL
function getWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const target = selectedType.value === 'host' ? 'host' : selectedTarget.value
  return `${protocol}//${host}/api/terminal/ws?target=${encodeURIComponent(target)}&target_type=${selectedType.value}`
}

// Load available targets
async function loadTargets() {
  loadingTargets.value = true
  try {
    const response = await fetch('/api/terminal/targets')
    const data = await response.json()
    targets.value = data
  } catch (e) {
    console.error('Failed to load terminal targets:', e)
  } finally {
    loadingTargets.value = false
  }
}

// Initialize terminal
function initTerminal() {
  if (terminal.value) {
    terminal.value.dispose()
  }

  terminal.value = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: currentTheme.value,
    scrollback: 5000,
    convertEol: true,
  })

  fitAddon.value = new FitAddon()
  terminal.value.loadAddon(fitAddon.value)

  if (terminalRef.value) {
    terminal.value.open(terminalRef.value)
    nextTick(() => {
      fitAddon.value.fit()
    })
  }

  // Handle input
  terminal.value.onData(data => {
    sendInput(data)
  })

  // Handle resize
  terminal.value.onResize(({ rows, cols }) => {
    sendResize(rows, cols)
  })
}

// Connect to WebSocket
function connect() {
  if (connecting.value || connected.value) return
  if (!selectedTarget.value && selectedType.value !== 'host') {
    error.value = 'Please select a container'
    return
  }

  connecting.value = true
  error.value = null

  // Initialize terminal if not already
  if (!terminal.value) {
    initTerminal()
  } else {
    terminal.value.clear()
  }

  const url = getWebSocketUrl()
  websocket.value = new WebSocket(url)

  websocket.value.onopen = () => {
    console.log('Terminal WebSocket connected')
  }

  websocket.value.onmessage = event => {
    try {
      const msg = JSON.parse(event.data)

      switch (msg.type) {
        case 'connected':
          connected.value = true
          connecting.value = false
          terminal.value?.focus()
          // Send initial resize
          if (terminal.value) {
            sendResize(terminal.value.rows, terminal.value.cols)
          }
          break

        case 'output':
          if (msg.data && terminal.value) {
            const decoded = atob(msg.data)
            terminal.value.write(decoded)
          }
          break

        case 'disconnected':
          connected.value = false
          terminal.value?.write('\r\n\x1b[31m[Disconnected]\x1b[0m\r\n')
          break

        case 'error':
          error.value = msg.message
          connecting.value = false
          terminal.value?.write(`\r\n\x1b[31m[Error: ${msg.message}]\x1b[0m\r\n`)
          break

        case 'pong':
          // Heartbeat response
          break
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e)
    }
  }

  websocket.value.onerror = event => {
    console.error('Terminal WebSocket error:', event)
    error.value = 'WebSocket connection failed'
    connecting.value = false
  }

  websocket.value.onclose = event => {
    console.log('Terminal WebSocket closed:', event.code, event.reason)
    connected.value = false
    connecting.value = false
    if (!error.value && event.code !== 1000) {
      terminal.value?.write('\r\n\x1b[31m[Connection closed]\x1b[0m\r\n')
    }
  }
}

// Send input to terminal
function sendInput(data) {
  if (websocket.value?.readyState === WebSocket.OPEN) {
    websocket.value.send(JSON.stringify({
      type: 'input',
      data: btoa(data),
    }))
  }
}

// Send resize event
function sendResize(rows, cols) {
  if (websocket.value?.readyState === WebSocket.OPEN) {
    websocket.value.send(JSON.stringify({
      type: 'resize',
      rows,
      cols,
    }))
  }
}

// Disconnect from WebSocket
function disconnect() {
  if (websocket.value) {
    websocket.value.close(1000)
    websocket.value = null
  }
  connected.value = false
  connecting.value = false
}

// Handle window resize
function handleResize() {
  if (fitAddon.value && terminal.value) {
    fitAddon.value.fit()
  }
}

// Watch theme changes
watch(() => themeStore.colorMode, () => {
  if (terminal.value) {
    terminal.value.options.theme = currentTheme.value
  }
})

// Watch target type changes
watch(selectedType, () => {
  if (selectedType.value === 'host') {
    selectedTarget.value = 'host'
  } else {
    selectedTarget.value = null
  }
})

onMounted(async () => {
  await loadTargets()
  window.addEventListener('resize', handleResize)
  // Initialize terminal on mount so it's ready when user connects
  await nextTick()
  initTerminal()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  disconnect()
  if (terminal.value) {
    terminal.value.dispose()
    terminal.value = null
  }
})
</script>

<template>
  <div class="space-y-4">
    <!-- Connection Controls -->
    <Card :padding="false">
      <div class="p-4">
        <div class="flex flex-col md:flex-row md:items-center gap-4">
          <!-- Target Type Selection -->
          <div class="flex items-center gap-2">
            <button
              @click="selectedType = 'container'"
              :class="[
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                selectedType === 'container'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              <ServerStackIcon class="h-4 w-4" />
              Container
            </button>
            <button
              @click="selectedType = 'host'"
              :disabled="!targets.host_available"
              :class="[
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                selectedType === 'host'
                  ? 'bg-amber-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600',
                !targets.host_available && 'opacity-50 cursor-not-allowed'
              ]"
            >
              <ComputerDesktopIcon class="h-4 w-4" />
              Host
            </button>
          </div>

          <!-- Container Selection -->
          <div v-if="selectedType === 'container'" class="flex-1">
            <select
              v-model="selectedTarget"
              :disabled="connected || loadingTargets"
              class="input w-full"
            >
              <option :value="null" disabled>Select a container...</option>
              <option
                v-for="container in targets.containers"
                :key="container.id"
                :value="container.name"
              >
                {{ container.name }} ({{ container.image }})
              </option>
            </select>
          </div>

          <!-- Host indicator -->
          <div v-else class="flex-1">
            <div class="flex items-center gap-2 px-4 py-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg text-amber-700 dark:text-amber-300">
              <ExclamationTriangleIcon class="h-5 w-5" />
              <span class="text-sm font-medium">Host shell access (privileged)</span>
            </div>
          </div>

          <!-- Connect/Disconnect Button -->
          <div class="flex items-center gap-2">
            <button
              v-if="!connected"
              @click="connect"
              :disabled="connecting || (!selectedTarget && selectedType !== 'host')"
              class="btn-primary flex items-center gap-2"
            >
              <ArrowPathIcon v-if="connecting" class="h-4 w-4 animate-spin" />
              <PlayIcon v-else class="h-4 w-4" />
              {{ connecting ? 'Connecting...' : 'Connect' }}
            </button>
            <button
              v-else
              @click="disconnect"
              class="btn-danger flex items-center gap-2"
            >
              <StopIcon class="h-4 w-4" />
              Disconnect
            </button>
            <button
              @click="loadTargets"
              :disabled="loadingTargets"
              class="btn-secondary flex items-center gap-1"
              title="Refresh container list"
            >
              <ArrowPathIcon :class="['h-4 w-4', loadingTargets && 'animate-spin']" />
            </button>
          </div>
        </div>

        <!-- Status indicator -->
        <div class="mt-3 flex items-center gap-2 text-sm">
          <span
            class="w-2 h-2 rounded-full"
            :class="{
              'bg-emerald-500': connected,
              'bg-amber-500 animate-pulse': connecting,
              'bg-red-500': error && !connected,
              'bg-gray-400': !connected && !connecting && !error,
            }"
          />
          <span class="text-secondary">
            <span v-if="connecting">Connecting to {{ selectedType === 'host' ? 'host' : selectedTarget }}...</span>
            <span v-else-if="connected" class="text-emerald-600 dark:text-emerald-400">
              <CheckCircleIcon class="h-4 w-4 inline" />
              Connected to {{ selectedType === 'host' ? 'host shell' : selectedTarget }}
            </span>
            <span v-else-if="error" class="text-red-500">{{ error }}</span>
            <span v-else>Select a target and click Connect</span>
          </span>
        </div>
      </div>
    </Card>

    <!-- Terminal -->
    <Card :padding="false">
      <div
        :class="[
          'rounded-lg overflow-hidden relative',
          themeStore.colorMode === 'dark' ? 'bg-[#1a1b26]' : 'bg-[#f8fafc]'
        ]"
      >
        <!-- Terminal container -->
        <div
          ref="terminalRef"
          class="h-[500px] p-2"
          :class="{ 'opacity-20': !connected && !connecting }"
        />

        <!-- Placeholder when not connected -->
        <div
          v-if="!connected && !connecting"
          class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
        >
          <CommandLineIcon class="h-16 w-16 text-gray-400 dark:text-gray-600 mb-4" />
          <p class="text-gray-500 dark:text-gray-400 text-center px-4">Select a target and connect to start a terminal session</p>
        </div>
      </div>

      <!-- Terminal footer -->
      <div class="px-4 py-2 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-xs text-muted">
        <div>
          <span v-if="connected">Press Ctrl+D or type 'exit' to close shell</span>
          <span v-else>Terminal ready</span>
        </div>
        <div class="flex items-center gap-4">
          <span v-if="terminal">
            {{ terminal.rows }}x{{ terminal.cols }}
          </span>
          <span>
            Theme: {{ themeStore.colorMode }}
          </span>
        </div>
      </div>
    </Card>
  </div>
</template>

<style>
/* Override xterm.js default styles for better integration */
.xterm {
  height: 100%;
  padding: 8px;
}

.xterm-viewport {
  overflow-y: auto !important;
}

.xterm-screen {
  height: 100%;
}
</style>
