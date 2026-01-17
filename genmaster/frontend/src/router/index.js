// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/router/index.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 15th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Lazy-loaded views
const DashboardView = () => import('@/views/DashboardView.vue')
const GeneratorView = () => import('@/views/GeneratorView.vue')
const GenSlaveView = () => import('@/views/GenSlaveView.vue')
const ScheduleView = () => import('@/views/ScheduleView.vue')
const HistoryView = () => import('@/views/HistoryView.vue')
const ContainersView = () => import('@/views/ContainersView.vue')
const SystemView = () => import('@/views/SystemView.vue')
const SettingsView = () => import('@/views/SettingsView.vue')
const LoginView = () => import('@/views/LoginView.vue')

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { requiresAuth: false, title: 'Login' },
  },
  {
    path: '/',
    name: 'dashboard',
    component: DashboardView,
    meta: { requiresAuth: true, title: 'Dashboard' },
  },
  {
    path: '/generator',
    name: 'generator',
    component: GeneratorView,
    meta: { requiresAuth: true, title: 'Generator Control' },
  },
  {
    path: '/genslave',
    name: 'genslave',
    component: GenSlaveView,
    meta: { requiresAuth: true, title: 'GenSlave' },
  },
  {
    path: '/schedule',
    name: 'schedule',
    component: ScheduleView,
    meta: { requiresAuth: true, title: 'Schedule' },
  },
  {
    path: '/history',
    name: 'history',
    component: HistoryView,
    meta: { requiresAuth: true, title: 'Run History' },
  },
  {
    path: '/containers',
    name: 'containers',
    component: ContainersView,
    meta: { requiresAuth: true, title: 'Containers' },
  },
  {
    path: '/system',
    name: 'system',
    component: SystemView,
    meta: { requiresAuth: true, title: 'System' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: { requiresAuth: true, title: 'Settings' },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // Update page title
  document.title = to.meta.title
    ? `${to.meta.title} - GenMaster`
    : 'GenMaster'

  // Check if route requires authentication
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.isAuthenticated) {
    // Redirect to login
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.name === 'login' && authStore.isAuthenticated) {
    // Already logged in, redirect to dashboard
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router
