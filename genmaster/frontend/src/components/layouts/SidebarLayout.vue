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
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'
import {
  HomeIcon,
  BoltIcon,
  GlobeAltIcon,
  CalendarIcon,
  ClockIcon,
  ServerStackIcon,
  CpuChipIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  SunIcon,
  MoonIcon,
  Bars3Icon,
  XMarkIcon,
  InformationCircleIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

// Dialog states
const showAbout = ref(false)

const navItems = [
  { name: 'Dashboard', route: 'dashboard', icon: HomeIcon, color: 'text-blue-500' },
  { name: 'Generator', route: 'generator', icon: BoltIcon, color: 'text-emerald-500' },
  { name: 'GenSlave', route: 'genslave', icon: GlobeAltIcon, color: 'text-purple-500' },
  { name: 'Schedule', route: 'schedule', icon: CalendarIcon, color: 'text-amber-500' },
  { name: 'History', route: 'history', icon: ClockIcon, color: 'text-cyan-500' },
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
        <!-- Controls -->
        <div :class="['flex items-center', themeStore.sidebarCollapsed ? 'flex-col space-y-2' : 'justify-between px-2']">
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
              <p class="text-sm text-secondary">January 15th, 2026</p>
              <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
                <p class="text-sm text-primary font-medium">Richard J. Sears</p>
                <p class="text-sm text-secondary">richardjsears@protonmail.com</p>
              </div>
            </div>
            <div class="px-6 py-4 border-t border-gray-400 dark:border-gray-700">
              <button @click="showAbout = false" class="w-full btn-secondary">Close</button>
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
