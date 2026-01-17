<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/terminal/TerminalDialog.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 16th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/75" @click="close"></div>

    <!-- Dialog -->
    <div class="relative w-full max-w-5xl bg-gray-900 rounded-lg shadow-2xl overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div class="flex items-center space-x-3">
          <svg class="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span class="text-white font-medium">{{ title }}</span>
          <span :class="['px-2 py-0.5 text-xs rounded-full', statusClass]">
            {{ statusText }}
          </span>
        </div>
        <button
          @click="close"
          class="text-gray-400 hover:text-white transition-colors"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Terminal Container -->
      <div ref="terminalContainer" class="h-96 bg-black"></div>

      <!-- Footer -->
      <div class="px-4 py-2 bg-gray-800 border-t border-gray-700 text-xs text-gray-400">
        Press Ctrl+C to interrupt, Ctrl+D to exit
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import terminalService from '@/services/terminal'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  target: {
    type: String,
    required: true,
  },
  targetType: {
    type: String,
    default: 'container',
  },
  targetName: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])

const terminalContainer = ref(null)
const status = ref('disconnected') // disconnected, connecting, connected, error

let terminal = null
let fitAddon = null
let websocket = null

const isOpen = computed(() => props.modelValue)

const title = computed(() => {
  if (props.targetType === 'host') {
    return 'Host Terminal'
  }
  return props.targetName || props.target
})

const statusText = computed(() => {
  switch (status.value) {
    case 'connected': return 'Connected'
    case 'connecting': return 'Connecting...'
    case 'error': return 'Error'
    default: return 'Disconnected'
  }
})

const statusClass = computed(() => {
  switch (status.value) {
    case 'connected': return 'bg-green-600 text-white'
    case 'connecting': return 'bg-yellow-600 text-white'
    case 'error': return 'bg-red-600 text-white'
    default: return 'bg-gray-600 text-white'
  }
})

function close() {
  emit('update:modelValue', false)
}

function initTerminal() {
  if (!terminalContainer.value) return

  // Create terminal
  terminal = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
      background: '#000000',
      foreground: '#ffffff',
      cursor: '#ffffff',
      cursorAccent: '#000000',
      selection: 'rgba(255, 255, 255, 0.3)',
    },
  })

  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)

  terminal.open(terminalContainer.value)
  fitAddon.fit()

  // Handle input
  terminal.onData((data) => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      const encoded = btoa(data)
      websocket.send(JSON.stringify({ type: 'input', data: encoded }))
    }
  })

  // Handle resize
  terminal.onResize(({ rows, cols }) => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({ type: 'resize', rows, cols }))
    }
  })

  // Connect to WebSocket
  connect()
}

function connect() {
  status.value = 'connecting'
  terminal.write('\x1b[33mConnecting to terminal...\x1b[0m\r\n')

  websocket = terminalService.connect(props.target, props.targetType)

  websocket.onopen = () => {
    // Send initial resize
    if (terminal) {
      websocket.send(JSON.stringify({
        type: 'resize',
        rows: terminal.rows,
        cols: terminal.cols,
      }))
    }
  }

  websocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'connected':
          status.value = 'connected'
          terminal.write('\x1b[32m' + data.message + '\x1b[0m\r\n')
          break

        case 'output':
          if (data.data) {
            const decoded = atob(data.data)
            terminal.write(decoded)
          }
          break

        case 'disconnected':
          status.value = 'disconnected'
          terminal.write('\r\n\x1b[31m' + data.message + '\x1b[0m\r\n')
          break

        case 'error':
          status.value = 'error'
          terminal.write('\r\n\x1b[31mError: ' + data.message + '\x1b[0m\r\n')
          break
      }
    } catch {
      // Ignore parse errors
    }
  }

  websocket.onerror = () => {
    status.value = 'error'
    terminal.write('\r\n\x1b[31mWebSocket error\x1b[0m\r\n')
  }

  websocket.onclose = () => {
    if (status.value === 'connected') {
      status.value = 'disconnected'
      terminal.write('\r\n\x1b[31mConnection closed\x1b[0m\r\n')
    }
  }
}

function cleanup() {
  if (websocket) {
    websocket.close()
    websocket = null
  }

  if (terminal) {
    terminal.dispose()
    terminal = null
  }

  fitAddon = null
  status.value = 'disconnected'
}

// Watch for dialog open/close
watch(isOpen, async (open) => {
  if (open) {
    await nextTick()
    initTerminal()
  } else {
    cleanup()
  }
})

// Handle window resize
function handleResize() {
  if (fitAddon && terminal) {
    fitAddon.fit()
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  cleanup()
})
</script>

<style>
.xterm {
  padding: 8px;
}
</style>
