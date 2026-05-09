<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/layout/MainLayout.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900">
    <!-- Sidebar -->
    <Sidebar :is-open="sidebarOpen" @close="sidebarOpen = false" />

    <!-- Mobile sidebar backdrop -->
    <Transition name="fade">
      <div
        v-if="sidebarOpen"
        class="fixed inset-0 z-30 bg-black/50 lg:hidden"
        @click="sidebarOpen = false"
      ></div>
    </Transition>

    <!-- Main content -->
    <div class="lg:pl-64">
      <!-- Header -->
      <Header @toggle-sidebar="sidebarOpen = !sidebarOpen" />

      <!-- Page content -->
      <main class="p-4 lg:p-6">
        <slot></slot>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useGeneratorStore } from '@/stores/generator'
import { useSystemStore } from '@/stores/system'
import { useAuthStore } from '@/stores/auth'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const sidebarOpen = ref(false)

const generatorStore = useGeneratorStore()
const systemStore = useSystemStore()
const authStore = useAuthStore()

let pollInterval = null

onMounted(async () => {
  // Fetch initial user data
  await authStore.fetchCurrentUser()

  // Fetch initial data
  await Promise.all([
    generatorStore.fetchState(),
    systemStore.fetchStatus(),
  ])

  // Start polling for updates
  pollInterval = setInterval(async () => {
    await Promise.all([
      generatorStore.fetchState(),
      systemStore.fetchStatus(),
    ])
  }, 5000) // Poll every 5 seconds
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
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
