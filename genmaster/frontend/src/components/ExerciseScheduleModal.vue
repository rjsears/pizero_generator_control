<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/ExerciseScheduleModal.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <Modal v-model="isOpen" title="Edit Exercise Schedule" size="md">
    <form @submit.prevent="handleSave" class="space-y-6">
      <!-- Enable Toggle -->
      <div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
        <div>
          <p class="text-sm font-medium text-gray-900 dark:text-white">Enable Exercise Scheduling</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Automatically run the generator at the scheduled time
          </p>
        </div>
        <Toggle v-model="form.enabled" />
      </div>

      <!-- Frequency -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Frequency (days)
        </label>
        <div class="flex items-center gap-4">
          <Input
            v-model.number="form.frequency_days"
            type="number"
            min="1"
            max="365"
            class="w-24"
          />
          <div class="flex gap-2">
            <button
              type="button"
              @click="form.frequency_days = 7"
              :class="[
                'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                form.frequency_days === 7
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              Weekly
            </button>
            <button
              type="button"
              @click="form.frequency_days = 14"
              :class="[
                'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                form.frequency_days === 14
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              Bi-weekly
            </button>
            <button
              type="button"
              @click="form.frequency_days = 30"
              :class="[
                'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                form.frequency_days === 30
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              Monthly
            </button>
          </div>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Run the generator every {{ form.frequency_days }} day{{ form.frequency_days !== 1 ? 's' : '' }}
        </p>
      </div>

      <!-- Start Time -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Start Time
        </label>
        <input
          v-model="form.start_time"
          type="time"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Time of day when the exercise run will start
        </p>
      </div>

      <!-- Duration -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Duration (minutes)
        </label>
        <div class="flex items-center gap-4">
          <Input
            v-model.number="form.duration_minutes"
            type="number"
            min="1"
            max="480"
            class="w-24"
          />
          <div class="flex gap-2">
            <button
              type="button"
              @click="form.duration_minutes = 15"
              :class="[
                'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                form.duration_minutes === 15
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              15 min
            </button>
            <button
              type="button"
              @click="form.duration_minutes = 30"
              :class="[
                'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                form.duration_minutes === 30
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              30 min
            </button>
            <button
              type="button"
              @click="form.duration_minutes = 60"
              :class="[
                'px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                form.duration_minutes === 60
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              ]"
            >
              60 min
            </button>
          </div>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          How long the generator will run during each exercise
        </p>
      </div>
    </form>

    <template #footer>
      <Button variant="secondary" @click="isOpen = false">
        Cancel
      </Button>
      <Button :loading="saving" @click="handleSave">
        Save Schedule
      </Button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import Modal from '@/components/common/Modal.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import Toggle from '@/components/common/Toggle.vue'
import exerciseService from '@/services/exercise'
import { useNotificationStore } from '@/stores/notifications'

const props = defineProps({
  modelValue: Boolean,
  schedule: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const notificationStore = useNotificationStore()
const saving = ref(false)

const isOpen = ref(props.modelValue)

watch(() => props.modelValue, (val) => {
  isOpen.value = val
})

watch(isOpen, (val) => {
  emit('update:modelValue', val)
})

const form = ref({
  enabled: false,
  frequency_days: 7,
  start_time: '10:00',
  duration_minutes: 15,
})

// Initialize form when schedule changes
watch(() => props.schedule, (newSchedule) => {
  form.value = {
    enabled: newSchedule.enabled || false,
    frequency_days: newSchedule.frequency_days || 7,
    start_time: newSchedule.start_time || '10:00',
    duration_minutes: newSchedule.duration_minutes || 15,
  }
}, { immediate: true })

async function handleSave() {
  saving.value = true
  try {
    const payload = {
      enabled: form.value.enabled,
      frequency_days: form.value.frequency_days,
      start_time: form.value.start_time,
      duration_minutes: form.value.duration_minutes,
    }

    const response = await exerciseService.updateSchedule(payload)
    emit('saved', response.data)
    notificationStore.success('Exercise schedule updated')
    isOpen.value = false
  } catch (error) {
    console.error('Failed to update exercise schedule:', error)
    notificationStore.error('Failed to update exercise schedule')
  } finally {
    saving.value = false
  }
}
</script>
