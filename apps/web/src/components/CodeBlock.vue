<template>
  <div class="relative">
    <div v-if="label" class="mb-2 flex items-center justify-between">
      <span class="eyebrow">{{ label }}</span>
      <button class="pressable flex items-center gap-1 rounded-[4px] px-1.5 py-1 text-[11px] text-muted-foreground hover:text-foreground" @click="copy">
        <Check v-if="copied" :size="12" />
        <Copy v-else :size="12" />
        {{ copied ? '已复制' : '复制' }}
      </button>
    </div>
    <pre class="code-block max-h-[360px] overflow-auto">{{ content }}</pre>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Check, Copy } from 'lucide-vue-next'

const props = defineProps<{ content: string; label?: string }>()
const copied = ref(false)

async function copy(): Promise<void> {
  try {
    await navigator.clipboard.writeText(props.content)
    copied.value = true
    window.setTimeout(() => (copied.value = false), 1600)
  } catch {
    /* clipboard may be unavailable */
  }
}
</script>
