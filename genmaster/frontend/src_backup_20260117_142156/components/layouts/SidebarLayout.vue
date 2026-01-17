<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/layouts/SidebarLayout.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'
import { useDebugStore } from '../../stores/debug'
import {
  HomeIcon,
  BoltIcon,
  GlobeAltIcon,
  CalendarIcon,
  ClockIcon,
  BellIcon,
  ServerStackIcon,
  CpuChipIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  SunIcon,
  MoonIcon,
  Bars3Icon,
  XMarkIcon,
  InformationCircleIcon,
  QuestionMarkCircleIcon,
  BugAntIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const debugStore = useDebugStore()

// Dialog states
const showAbout = ref(false)
const showHelp = ref(false)

// Load debug mode on mount
onMounted(() => {
  debugStore.loadDebugMode()
})

const navItems = [
  { name: 'Dashboard', route: 'dashboard', icon: HomeIcon, color: 'text-blue-500' },
  { name: 'Generator', route: 'generator', icon: BoltIcon, color: 'text-emerald-500' },
  { name: 'GenSlave', route: 'genslave', icon: GlobeAltIcon, color: 'text-purple-500' },
  { name: 'Schedule', route: 'schedule', icon: CalendarIcon, color: 'text-amber-500' },
  { name: 'History', route: 'history', icon: ClockIcon, color: 'text-cyan-500' },
  { name: 'Notifications', route: 'notifications', icon: BellIcon, color: 'text-orange-500' },
  { name: 'Containers', route: 'containers', icon: ServerStackIcon, color: 'text-rose-500' },
  { name: 'System', route: 'system', icon: CpuChipIcon, color: 'text-indigo-500' },
  { name: 'Settings', route: 'settings', icon: Cog6ToothIcon, color: 'text-gray-500' },
]

const isActive = (routeName) => route.name === routeName

const sidebarWidth = computed(() =>
  themeStore.sidebarCollapsed ? 'w-16' : 'w-64'
)

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-screen bg-background-primary flex">
    <!-- Sidebar -->
    <aside
      :class="[
        sidebarWidth,
        'fixed inset-y-0 left-0 z-50 flex flex-col transition-all duration-300',
        'bg-background-secondary border-r border-gray-400 dark:border-black'
      ]"
    >
      <!-- Logo -->
      <div class="flex h-16 items-center justify-between px-4 border-b border-gray-400 dark:border-black">
        <div v-if="!themeStore.sidebarCollapsed" class="flex items-center">
          <span class="text-xl font-bold text-primary">Gen</span>
          <span class="text-xl font-light text-secondary ml-1">Master</span>
        </div>
        <button
          @click="themeStore.toggleSidebar"
          class="p-1.5 rounded-lg text-secondary hover:text-primary hover:bg-surface-hover transition-colors"
        >
          <XMarkIcon v-if="!themeStore.sidebarCollapsed" class="h-5 w-5" />
          <Bars3Icon v-else class="h-5 w-5" />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
        <router-link
          v-for="item in navItems"
          :key="item.route"
          :to="{ name: item.route }"
          :class="[
            'flex items-center rounded-lg transition-all duration-200',
            themeStore.sidebarCollapsed ? 'justify-center px-2 py-3' : 'px-3 py-2.5',
            isActive(item.route)
              ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-l-2 border-blue-500'
              : 'text-secondary hover:text-primary hover:bg-surface-hover'
          ]"
          :title="themeStore.sidebarCollapsed ? item.name : ''"
        >
          <component
            :is="item.icon"
            :class="[
              'h-5 w-5 flex-shrink-0',
              isActive(item.route) ? item.color : ''
            ]"
          />
          <span
            v-if="!themeStore.sidebarCollapsed"
            class="ml-3 text-sm font-medium"
          >
            {{ item.name }}
          </span>
        </router-link>
      </nav>

      <!-- Bottom section -->
      <div class="border-t border-gray-400 dark:border-black p-2 space-y-1">
        <!-- Debug indicator -->
        <div v-if="debugStore.isEnabled" :class="['flex items-center', themeStore.sidebarCollapsed ? 'justify-center' : 'px-2']">
          <button
            @click="router.push({ name: 'settings' })"
            class="flex items-center p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors"
            title="Debug mode enabled"
          >
            <BugAntIcon class="h-5 w-5" />
            <span v-if="!themeStore.sidebarCollapsed" class="ml-2 text-sm font-medium">Debug</span>
          </button>
        </div>

        <!-- Controls -->
        <div :class="['flex items-center', themeStore.sidebarCollapsed ? 'flex-col space-y-2' : 'justify-between px-2']">
          <button
            @click="showHelp = true"
            class="p-2 rounded-lg text-secondary hover:text-primary hover:bg-surface-hover transition-colors"
            title="Help"
          >
            <QuestionMarkCircleIcon class="h-5 w-5" />
          </button>

          <button
            @click="showAbout = true"
            class="p-2 rounded-lg text-secondary hover:text-primary hover:bg-surface-hover transition-colors"
            title="About"
          >
            <InformationCircleIcon class="h-5 w-5" />
          </button>

          <button
            @click="themeStore.toggleColorMode"
            class="p-2 rounded-lg text-secondary hover:text-primary hover:bg-surface-hover transition-colors"
            title="Toggle dark mode"
          >
            <SunIcon v-if="themeStore.isDark" class="h-5 w-5" />
            <MoonIcon v-else class="h-5 w-5" />
          </button>
        </div>

        <!-- User & Logout -->
        <div :class="['flex items-center', themeStore.sidebarCollapsed ? 'justify-center' : 'px-2']">
          <span v-if="!themeStore.sidebarCollapsed" class="text-sm text-secondary truncate mr-2">
            {{ authStore.username }}
          </span>
          <button
            @click="handleLogout"
            class="p-2 rounded-lg text-secondary hover:text-red-500 hover:bg-red-500/10 transition-colors"
            title="Logout"
          >
            <ArrowRightOnRectangleIcon class="h-5 w-5" />
          </button>
        </div>

        <!-- Version -->
        <div v-if="!themeStore.sidebarCollapsed" class="px-2 pt-2 text-xs text-muted">
          GenMaster v1.0.0
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main
      :class="[
        'flex-1 transition-all duration-300',
        themeStore.sidebarCollapsed ? 'ml-16' : 'ml-64'
      ]"
    >
      <div class="p-6 lg:p-8">
        <slot />
      </div>
    </main>

    <!-- About Dialog -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showAbout"
          class="fixed inset-0 z-[100] flex items-center justify-center p-4"
        >
          <div class="absolute inset-0 bg-black/50" @click="showAbout = false" />
          <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full border border-gray-400 dark:border-gray-700">
            <div class="px-6 py-4 border-b border-gray-400 dark:border-gray-700">
              <div class="flex items-center gap-3">
                <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                  <BoltIcon class="h-6 w-6 text-blue-500" />
                </div>
                <div>
                  <h3 class="text-lg font-semibold text-primary">GenMaster</h3>
                  <p class="text-sm text-secondary">RPi Generator Control Suite</p>
                </div>
              </div>
            </div>
            <div class="px-6 py-4 space-y-3">
              <p class="text-sm text-secondary">Version 1.0.0</p>
              <p class="text-sm text-secondary">January 2026</p>
              <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
                <p class="text-sm text-primary font-medium">Richard J. Sears</p>
                <p class="text-sm text-secondary">richardjsears@protonmail.com</p>
              </div>
              <div class="pt-2">
                <a
                  href="https://github.com/rjsears/pizero_generator_control"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="inline-flex items-center text-sm text-blue-500 hover:text-blue-600"
                >
                  <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                    <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd" />
                  </svg>
                  GitHub Repository
                </a>
              </div>
            </div>
            <div class="px-6 py-4 border-t border-gray-400 dark:border-gray-700">
              <button @click="showAbout = false" class="w-full btn-secondary">Close</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Help Dialog -->
    <Teleport to="body">
      <Transition name="modal">
        <div
          v-if="showHelp"
          class="fixed inset-0 z-[100] flex items-center justify-center p-4"
        >
          <div class="absolute inset-0 bg-black/50" @click="showHelp = false" />
          <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden border border-gray-400 dark:border-gray-700">
            <div class="px-6 py-4 border-b border-gray-400 dark:border-gray-700">
              <div class="flex items-center gap-3">
                <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-500/20">
                  <QuestionMarkCircleIcon class="h-6 w-6 text-blue-500" />
                </div>
                <div>
                  <h3 class="text-lg font-semibold text-primary">Help</h3>
                  <p class="text-sm text-secondary">Quick reference guide</p>
                </div>
              </div>
            </div>
            <div class="px-6 py-4 overflow-y-auto max-h-[60vh]">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 class="text-sm font-medium text-primary mb-2">Generator Control</h4>
                  <ul class="space-y-1 text-sm text-secondary">
                    <li>Start/Stop from Generator page</li>
                    <li>Timed runs with auto-stop</li>
                    <li>Emergency stop skips cooldown</li>
                    <li>Manual override disables Victron</li>
                  </ul>
                </div>
                <div>
                  <h4 class="text-sm font-medium text-primary mb-2">Scheduling</h4>
                  <ul class="space-y-1 text-sm text-secondary">
                    <li>Create schedules for auto-runs</li>
                    <li>Set days, time, and duration</li>
                    <li>Enable/disable schedules</li>
                  </ul>
                </div>
                <div>
                  <h4 class="text-sm font-medium text-primary mb-2">Notifications</h4>
                  <ul class="space-y-1 text-sm text-secondary">
                    <li>Apprise for Discord, Slack, etc.</li>
                    <li>Email for SMTP alerts</li>
                    <li>Groups for bulk notifications</li>
                  </ul>
                </div>
                <div>
                  <h4 class="text-sm font-medium text-primary mb-2">System</h4>
                  <ul class="space-y-1 text-sm text-secondary">
                    <li>Health tab for status</li>
                    <li>Network for connectivity</li>
                    <li>GenSlave for relay controller</li>
                  </ul>
                </div>
              </div>
              <div class="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                <h4 class="text-sm font-medium text-primary mb-2">API Documentation</h4>
                <div class="flex gap-2">
                  <a href="/api/docs" target="_blank" class="btn-secondary text-sm">Swagger UI</a>
                  <a href="/api/redoc" target="_blank" class="btn-secondary text-sm">ReDoc</a>
                </div>
              </div>
            </div>
            <div class="px-6 py-4 border-t border-gray-400 dark:border-gray-700">
              <button @click="showHelp = false" class="w-full btn-secondary">Close</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
