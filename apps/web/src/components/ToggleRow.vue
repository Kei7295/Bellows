<template>
  <div class="flex items-center justify-between gap-3">
    <span class="text-[11px] text-muted-foreground">{{ label }}</span>
    <Switch :model-value="modelValue" size="sm" @update:model-value="onChange" />
  </div>
</template>

<script setup lang="ts">
import { Switch } from 'fuxsto-design'
defineProps<{ label: string; modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
function onChange(value: boolean): void {
  emit('update:modelValue', value)
}
</script>
