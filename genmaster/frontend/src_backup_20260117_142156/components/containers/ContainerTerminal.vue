<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/containers/ContainerTerminal.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 17th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import Modal from '@/components/common/Modal.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import 'xterm/css/xterm.css'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  container: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue'])

const terminalRef = ref(null)
const terminal = ref(null)
const fitAddon = ref(null)
const websocket = ref(null)
const connected = ref(false)
const connecting = ref(false)
const error = ref(null)

// Get WebSocket URL
function getWebSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const containerName = props.container?.name || props.container?.id
  return `${protocol}//${host}/api/terminal/ws?target=${encodeURIComponent(containerName)}&target_type=container`
}

// Initialize terminal
function initTerminal() {
  if (terminal.value || !terminalRef.value) return

  terminal.value = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
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
    scrollback: 1000,
    convertEol: true,
  })

  fitAddon.value = new FitAddon()
  terminal.value.loadAddon(fitAddon.value)

  terminal.value.open(terminalRef.value)

  // Fit to container size
  nextTick(() => {
    fitAddon.value.fit()
  })

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

  connecting.value = true
  error.value = null

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

// Cleanup terminal
function cleanupTerminal() {
  disconnect()
  if (terminal.value) {
    terminal.value.dispose()
    terminal.value = null
  }
  fitAddon.value = null
}

// Handle modal visibility
watch(() => props.modelValue, async (isOpen) => {
  if (isOpen && props.container) {
    // Modal is opening
    error.value = null
    await nextTick()
    initTerminal()
    connect()
  } else {
    // Modal is closing
    cleanupTerminal()
  }
})

// Handle window resize
function handleResize() {
  if (fitAddon.value && terminal.value) {
    fitAddon.value.fit()
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  cleanupTerminal()
})

// Close modal
function closeModal() {
  emit('update:modelValue', false)
}
</script>

<template>
  <Modal
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    :title="`Terminal: ${container?.name || 'Container'}`"
    size="full"
  >
    <div class="flex flex-col h-[500px]">
      <!-- Status bar -->
      <div class="flex items-center justify-between px-3 py-2 bg-gray-800 border-b border-gray-700 text-sm">
        <div class="flex items-center gap-2">
          <span
            class="w-2 h-2 rounded-full"
            :class="{
              'bg-emerald-500': connected,
              'bg-amber-500 animate-pulse': connecting,
              'bg-red-500': error,
              'bg-gray-500': !connected && !connecting && !error,
            }"
          />
          <span class="text-gray-300">
            <span v-if="connecting">Connecting...</span>
            <span v-else-if="connected">Connected to {{ container?.name }}</span>
            <span v-else-if="error" class="text-red-400">{{ error }}</span>
            <span v-else>Disconnected</span>
          </span>
        </div>
        <div class="flex items-center gap-2 text-gray-400">
          <span class="text-xs">{{ container?.image }}</span>
        </div>
      </div>

      <!-- Terminal container -->
      <div class="flex-1 bg-[#1a1b26] p-2 overflow-hidden relative">
        <!-- Loading state -->
        <div
          v-if="connecting"
          class="absolute inset-0 flex items-center justify-center bg-[#1a1b26]"
        >
          <LoadingSpinner text="Connecting to container..." />
        </div>

        <!-- Error state -->
        <div
          v-else-if="error && !connected"
          class="absolute inset-0 flex flex-col items-center justify-center bg-[#1a1b26] text-gray-400"
        >
          <ExclamationTriangleIcon class="h-12 w-12 text-red-500 mb-4" />
          <p class="text-lg font-medium text-red-400">Connection Failed</p>
          <p class="text-sm mt-2">{{ error }}</p>
          <button @click="connect" class="btn-primary mt-4">
            Try Again
          </button>
        </div>

        <!-- Terminal element -->
        <div
          ref="terminalRef"
          class="h-full w-full"
          :class="{ 'opacity-0': connecting || (error && !connected) }"
        />
      </div>
    </div>

    <template #footer>
      <div class="flex justify-between items-center w-full">
        <div class="text-sm text-muted">
          <span v-if="connected">Press Ctrl+D or type 'exit' to close shell</span>
          <span v-else-if="error">Terminal connection failed</span>
        </div>
        <div class="flex gap-2">
          <button
            v-if="!connected && !connecting"
            @click="connect"
            class="btn-primary"
          >
            Reconnect
          </button>
          <button @click="closeModal" class="btn-secondary">
            Close
          </button>
        </div>
      </div>
    </template>
  </Modal>
</template>

<style>
/* Override xterm.js default styles for better integration */
.xterm {
  height: 100%;
}

.xterm-viewport {
  overflow-y: auto !important;
}
</style>
