<template>
  <header class="flex flex-col gap-4 pb-5 sm:flex-row sm:items-end sm:justify-between">
    <div class="min-w-0">
      <p class="eyebrow mb-2">{{ eyebrow }}</p>
      <h1 class="text-[30px] font-extrabold leading-tight tracking-[-0.025em] text-foreground">{{ title }}</h1>
      <p v-if="description" class="mt-2 max-w-2xl text-[13px] leading-relaxed text-muted-foreground">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ eyebrow: string; title: string; description?: string }>()
</script>
