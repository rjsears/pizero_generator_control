// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// /genmaster/frontend/src/stores/notifications.js
//
// Part of the "RPi Generator Control" suite
// Version 1.0.0 - January 15th, 2026
//
// Richard J. Sears
// richardjsears@protonmail.com
// https://github.com/rjsears
// -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

let notificationId = 0

export const useNotificationStore = defineStore('notifications', () => {
  // State
  const notifications = ref([])

  // Getters
  const activeNotifications = computed(() => notifications.value)
  const hasNotifications = computed(() => notifications.value.length > 0)

  // Actions
  function add(notification) {
    const id = ++notificationId
    const defaults = {
      id,
      type: 'info',
      title: '',
      message: '',
      duration: 5000,
      dismissible: true,
    }

    const newNotification = { ...defaults, ...notification }
    notifications.value.push(newNotification)

    // Auto-dismiss after duration
    if (newNotification.duration > 0) {
      setTimeout(() => {
        remove(id)
      }, newNotification.duration)
    }

    return id
  }

  function remove(id) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  function clear() {
    notifications.value = []
  }

  // Convenience methods
  function success(message, title = 'Success') {
    return add({ type: 'success', title, message })
  }

  function error(message, title = 'Error') {
    return add({ type: 'error', title, message, duration: 8000 })
  }

  function warning(message, title = 'Warning') {
    return add({ type: 'warning', title, message, duration: 6000 })
  }

  function info(message, title = 'Info') {
    return add({ type: 'info', title, message })
  }

  return {
    // State
    notifications,

    // Getters
    activeNotifications,
    hasNotifications,

    // Actions
    add,
    remove,
    clear,
    success,
    error,
    warning,
    info,
  }
})
