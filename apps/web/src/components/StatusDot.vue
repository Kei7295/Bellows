<template>
  <span class="inline-flex items-center gap-1.5" :class="meta.tone">
    <LoaderCircle v-if="icon === 'connecting'" :size="size" class="animate-spin" />
    <AlertTriangle v-else-if="icon === 'error'" :size="size" />
    <CircleAlert v-else-if="icon === 'degraded'" :size="size" />
    <span v-else-if="icon === 'online'" class="relative inline-flex" :style="{ width: `${size}px`, height: `${size}px` }">
      <span
        class="absolute inset-1/4 rounded-full"
        :class="[meta.tone, 'bg-current', pulse ? 'live-dot' : '']"
      />
    </span>
    <Circle v-else :size="size" />
    <span v-if="showLabel" class="text-[12px] font-medium leading-none">{{ meta.label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { AlertTriangle, Circle, CircleAlert, LoaderCircle } from 'lucide-vue-next'
import { statusMeta } from '../utils'

const props = withDefaults(
  defineProps<{ status?: string; size?: number; showLabel?: boolean; pulse?: boolean }>(),
  { status: 'offline', size: 14, showLabel: false, pulse: true },
)
const meta = computed(() => statusMeta[props.status] || statusMeta.offline)
const icon = computed(() => meta.value.icon)
</script>
