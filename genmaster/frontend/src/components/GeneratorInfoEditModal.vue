<!--
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
  /genmaster/frontend/src/components/GeneratorInfoEditModal.vue

  Part of the "RPi Generator Control" suite
  Version 1.0.0 - January 19th, 2026

  Richard J. Sears
  richardjsears@protonmail.com
  https://github.com/rjsears
  -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
-->

<template>
  <Modal v-model="isOpen" title="Edit Generator Information" size="lg">
    <form @submit.prevent="handleSave" class="space-y-6">
      <!-- Generator Identity -->
      <div>
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Generator Identity</h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Input
            v-model="form.manufacturer"
            label="Manufacturer"
            placeholder="e.g., Generac"
          />
          <Input
            v-model="form.model_number"
            label="Model Number"
            placeholder="e.g., 7043"
          />
          <Input
            v-model="form.serial_number"
            label="Serial Number"
            placeholder="e.g., ABC123456"
          />
        </div>
      </div>

      <!-- Fuel Configuration -->
      <div class="border-t border-gray-200 dark:border-gray-700 pt-6">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Fuel Configuration</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Fuel Type
            </label>
            <select
              v-model="form.fuel_type"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select fuel type...</option>
              <option value="lpg">LPG (Propane)</option>
              <option value="natural_gas">Natural Gas</option>
              <option value="diesel">Diesel</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Expected Load
            </label>
            <div class="flex gap-4 mt-2">
              <label class="flex items-center">
                <input
                  type="radio"
                  v-model.number="form.load_expected"
                  :value="50"
                  class="h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 focus:ring-blue-500"
                >
                <span class="ml-2 text-gray-900 dark:text-white">50%</span>
              </label>
              <label class="flex items-center">
                <input
                  type="radio"
                  v-model.number="form.load_expected"
                  :value="100"
                  class="h-4 w-4 text-blue-600 border-gray-300 dark:border-gray-600 focus:ring-blue-500"
                >
                <span class="ml-2 text-gray-900 dark:text-white">100%</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Fuel Consumption Rates -->
      <div class="border-t border-gray-200 dark:border-gray-700 pt-6">
        <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Fuel Consumption Rates</h4>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
          Enter the fuel consumption rates from your generator's specifications.
        </p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            v-model.number="form.fuel_consumption_50"
            type="number"
            step="0.1"
            min="0"
            max="100"
            label="At 50% Load (gal/hr)"
            placeholder="e.g., 1.6"
          />
          <Input
            v-model.number="form.fuel_consumption_100"
            type="number"
            step="0.1"
            min="0"
            max="100"
            label="At 100% Load (gal/hr)"
            placeholder="e.g., 2.8"
          />
        </div>
      </div>
    </form>

    <template #footer>
      <Button variant="secondary" @click="isOpen = false">
        Cancel
      </Button>
      <Button :loading="saving" @click="handleSave">
        Save Changes
      </Button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import Modal from '@/components/common/Modal.vue'
import Button from '@/components/common/Button.vue'
import Input from '@/components/common/Input.vue'
import generatorInfoService from '@/services/generatorInfo'
import { useNotificationStore } from '@/stores/notifications'

const props = defineProps({
  modelValue: Boolean,
  info: {
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
  manufacturer: '',
  model_number: '',
  serial_number: '',
  fuel_type: '',
  load_expected: null,
  fuel_consumption_50: null,
  fuel_consumption_100: null,
})

// Initialize form when info changes
watch(() => props.info, (newInfo) => {
  form.value = {
    manufacturer: newInfo.manufacturer || '',
    model_number: newInfo.model_number || '',
    serial_number: newInfo.serial_number || '',
    fuel_type: newInfo.fuel_type || '',
    load_expected: newInfo.load_expected || null,
    fuel_consumption_50: newInfo.fuel_consumption_50 ?? null,
    fuel_consumption_100: newInfo.fuel_consumption_100 ?? null,
  }
}, { immediate: true })

async function handleSave() {
  saving.value = true
  try {
    // Build update payload with only changed fields
    const payload = {}
    if (form.value.manufacturer !== props.info.manufacturer) {
      payload.manufacturer = form.value.manufacturer || null
    }
    if (form.value.model_number !== props.info.model_number) {
      payload.model_number = form.value.model_number || null
    }
    if (form.value.serial_number !== props.info.serial_number) {
      payload.serial_number = form.value.serial_number || null
    }
    if (form.value.fuel_type !== props.info.fuel_type) {
      payload.fuel_type = form.value.fuel_type || null
    }
    if (form.value.load_expected !== props.info.load_expected) {
      payload.load_expected = form.value.load_expected
    }
    if (form.value.fuel_consumption_50 !== props.info.fuel_consumption_50) {
      payload.fuel_consumption_50 = form.value.fuel_consumption_50
    }
    if (form.value.fuel_consumption_100 !== props.info.fuel_consumption_100) {
      payload.fuel_consumption_100 = form.value.fuel_consumption_100
    }

    // Only send if there are changes
    if (Object.keys(payload).length === 0) {
      isOpen.value = false
      return
    }

    const response = await generatorInfoService.update(payload)
    emit('saved', response.data)
    notificationStore.success('Generator information updated')
    isOpen.value = false
  } catch (error) {
    console.error('Failed to update generator info:', error)
    notificationStore.error('Failed to update generator information')
  } finally {
    saving.value = false
  }
}
</script>
