<template>
  <Card padding="md" :bordered="true" class="h-full">
    <div class="flex items-start justify-between gap-3">
      <div>
        <p class="eyebrow">{{ label }}</p>
        <p class="mt-3 flex items-baseline gap-1.5">
          <span class="metric-number text-[30px] font-bold leading-none">{{ display }}</span>
          <span v-if="suffix" class="text-[12px] text-muted-foreground">{{ suffix }}</span>
        </p>
      </div>
      <div class="grid h-8 w-8 place-items-center rounded-[calc(var(--radius)-2px)] border border-border text-muted-foreground">
        <component :is="icon" :size="16" />
      </div>
    </div>
    <div class="mt-4 flex items-end justify-between gap-3">
      <span class="text-[12px] leading-none" :class="toneClass">{{ hint }}</span>
      <div v-if="spark.length" class="flex h-6 items-end gap-[3px]" aria-hidden="true">
        <span
          v-for="(v, i) in spark"
          :key="i"
          class="w-[3px] rounded-[1px]"
          :class="i === spark.length - 1 ? 'bg-foreground/80' : 'bg-foreground/20'"
          :style="{ height: `${Math.max(3, Math.round((v / maxSpark) * 24))}px` }"
        />
      </div>
    </div>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Component } from 'vue'
import { Card } from 'fuxsto-design'

const props = withDefaults(
  defineProps<{
    label: string
    value: string | number
    suffix?: string
    hint?: string
    icon: Component
    tone?: 'default' | 'success' | 'warning' | 'error'
    spark?: number[]
  }>(),
  { suffix: '', hint: '', tone: 'default', spark: () => [] },
)
const display = computed(() => props.value)
const maxSpark = computed(() => Math.max(...props.spark, 1))
const toneClass = computed(
  () =>
    ({
      default: 'text-muted-foreground',
      success: 'text-success',
      warning: 'text-warning',
      error: 'text-destructive',
    })[props.tone],
)
</script>
