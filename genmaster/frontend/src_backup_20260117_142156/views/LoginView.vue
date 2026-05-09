<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/views/LoginView.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 15th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 px-4">
    <div class="max-w-md w-full">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-2xl mb-4">
          <svg class="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">GenMaster</h1>
        <p class="text-gray-600 dark:text-gray-400 mt-2">Generator Control System</p>
      </div>

      <!-- Login form -->
      <div class="card">
        <div class="p-6">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-6">Sign in to your account</h2>

          <form @submit.prevent="handleLogin">
            <!-- Error message -->
            <div
              v-if="error"
              class="mb-4 p-3 bg-red-50 dark:bg-red-900/50 border border-red-200 dark:border-red-800 rounded-lg"
            >
              <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
            </div>

            <!-- Username -->
            <div class="mb-4">
              <Input
                v-model="username"
                label="Username"
                placeholder="Enter your username"
                required
                :disabled="loading"
              />
            </div>

            <!-- Password -->
            <div class="mb-6">
              <Input
                v-model="password"
                type="password"
                label="Password"
                placeholder="Enter your password"
                required
                :disabled="loading"
              />
            </div>

            <!-- Submit button -->
            <Button
              type="submit"
              variant="primary"
              :loading="loading"
              block
            >
              Sign in
            </Button>
          </form>
        </div>
      </div>

      <!-- Footer -->
      <div class="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
        <p>GenMaster v1.0.0</p>
        <p class="mt-1">Richard J. Sears</p>
        <p>richardjsears@protonmail.com</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Input from '@/components/common/Input.vue'
import Button from '@/components/common/Button.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

onMounted(() => {
  authStore.clearError()
})

async function handleLogin() {
  error.value = ''
  loading.value = true

  const success = await authStore.login({
    username: username.value,
    password: password.value,
  })

  loading.value = false

  if (success) {
    // Redirect to requested page or dashboard
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } else {
    error.value = authStore.error || 'Login failed'
  }
}
</script>
