<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <rect x="2.75" y="3.75" width="12.5" height="16.5" rx="1.6" stroke="currentColor" stroke-width="1.7" />
    <path d="M15.25 8h3.1M15.25 12h5.25M15.25 16h3.1" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
    <path d="M6.6 9.2h4.6M6.6 12h4.6M6.6 14.8h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" opacity="0.55" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 24 })
</script>
