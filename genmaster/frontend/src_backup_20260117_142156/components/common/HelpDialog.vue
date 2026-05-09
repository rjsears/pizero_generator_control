<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/common/HelpDialog.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 17th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
        @click.self="close"
      >
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
          <!-- Header -->
          <header class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
            <div class="flex items-center space-x-3">
              <div class="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Help</h2>
            </div>
            <button
              class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              @click="close"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </header>

          <!-- Content -->
          <div class="px-6 py-6 overflow-y-auto flex-1">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- Quick Start -->
              <div class="space-y-3">
                <h3 class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                  <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Quick Start
                </h3>
                <div class="space-y-2">
                  <HelpItem title="Start Generator" description="Go to Generator page and click Start" />
                  <HelpItem title="Stop Generator" description="Click Stop on the Generator page" />
                  <HelpItem title="Timed Run" description="Set duration and click 'Start for X minutes'" />
                  <HelpItem title="Emergency Stop" description="Skips cooldown, use only in emergencies" />
                </div>
              </div>

              <!-- Navigation -->
              <div class="space-y-3">
                <h3 class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                  <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                  Navigation
                </h3>
                <div class="space-y-2">
                  <HelpItem title="Dashboard" description="System overview and quick actions" />
                  <HelpItem title="Generator" description="Manual control and status" />
                  <HelpItem title="Schedule" description="Automated run schedules" />
                  <HelpItem title="History" description="Past generator runs" />
                </div>
              </div>

              <!-- System Features -->
              <div class="space-y-3">
                <h3 class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                  <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                  </svg>
                  System Features
                </h3>
                <div class="space-y-2">
                  <HelpItem title="GenSlave" description="Monitor the relay controller Pi" />
                  <HelpItem title="Notifications" description="Configure alert channels" />
                  <HelpItem title="Containers" description="Manage Docker containers" />
                  <HelpItem title="System" description="Health, network, and settings" />
                </div>
              </div>

              <!-- Tips -->
              <div class="space-y-3">
                <h3 class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                  <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  Tips
                </h3>
                <div class="space-y-2">
                  <HelpItem title="Manual Override" description="Disable Victron auto-start" />
                  <HelpItem title="Theme" description="Toggle dark/light in Settings" />
                  <HelpItem title="Heartbeat" description="GenSlave checks in every 60s" />
                  <HelpItem title="Failsafe" description="GenSlave stops if comms lost" />
                </div>
              </div>
            </div>

            <!-- API Documentation -->
            <div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <h3 class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3">
                <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                API Documentation
              </h3>
              <div class="flex flex-wrap gap-3">
                <button
                  class="inline-flex items-center px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  @click="openLink('/api/docs')"
                >
                  <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Swagger UI
                </button>
                <button
                  class="inline-flex items-center px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                  @click="openLink('/api/redoc')"
                >
                  <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                  ReDoc
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { h } from 'vue'

defineProps({
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close'])

// HelpItem sub-component
const HelpItem = (props) => {
  return h('div', { class: 'p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg' }, [
    h('p', { class: 'font-medium text-sm text-gray-900 dark:text-white' }, props.title),
    h('p', { class: 'text-xs text-gray-500 dark:text-gray-400' }, props.description),
  ])
}

function close() {
  emit('close')
}

function openLink(path) {
  window.open(path, '_blank')
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
