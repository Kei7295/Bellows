<template>
  <div class="flex h-full flex-col bg-background text-foreground">
    <AppTitleBar :collapsed="collapsed" @toggle-sidebar="toggleSidebar" />

    <div class="flex min-h-0 flex-1">
      <AppSidebar :collapsed="collapsed" />

      <main
        class="min-w-0 flex-1"
        :class="isConsole ? 'overflow-hidden' : 'overflow-y-auto'"
      >
        <div :class="isConsole ? 'h-full px-6 pt-5 pb-2' : 'mx-auto w-full max-w-[1440px] px-8 pb-12 pt-7'">
          <Alert
            v-if="store.error"
            type="error"
            title="无法连接 Bellows 内核"
            :description="`${store.error}。请确认 core 已启动，或检查 BELLOWS_TOKEN 配置。`"
            class="mb-5"
          >
            <template #extra>
              <Button variant="outline" size="sm" :icon="RefreshCw" @click="store.loadCore()">重试</Button>
            </template>
          </Alert>

          <div v-if="store.loading && !store.overview" class="space-y-4">
            <div class="h-8 w-64 animate-pulse rounded-md bg-muted" />
            <div class="grid grid-cols-2 gap-4 xl:grid-cols-4">
              <div v-for="i in 4" :key="i" class="h-[118px] animate-pulse rounded-[var(--radius)] border border-border bg-muted/50" />
            </div>
            <div class="h-[320px] animate-pulse rounded-[var(--radius)] border border-border bg-muted/50" />
          </div>

          <RouterView v-else v-slot="{ Component }">
            <component :is="Component" :key="$route.fullPath" class="page-enter" />
          </RouterView>
        </div>
      </main>
    </div>

    <div class="pointer-events-none fixed bottom-5 right-5 z-50 flex w-[340px] flex-col gap-2">
      <TransitionGroup name="toast">
        <div
          v-for="item in store.toasts"
          :key="item.id"
          class="pointer-events-auto flex items-start gap-3 rounded-[var(--radius)] border border-border bg-background p-3.5 shadow-[var(--app-overlay)]"
        >
          <component :is="toastIcon(item.tone)" :size="16" :class="toastTone(item.tone)" class="mt-0.5 shrink-0" />
          <div class="min-w-0 flex-1">
            <p class="text-[13px] font-semibold leading-snug">{{ item.title }}</p>
            <p v-if="item.description" class="mt-1 text-[12px] leading-relaxed text-muted-foreground">{{ item.description }}</p>
          </div>
          <button class="shrink-0 text-muted-foreground hover:text-foreground" aria-label="关闭提示" @click="store.dismissToast(item.id)">
            <X :size="14" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Alert, Button } from 'fuxsto-design'
import { AlertTriangle, CheckCircle2, Info, RefreshCw, X, XCircle } from 'lucide-vue-next'
import AppTitleBar from './components/AppTitleBar.vue'
import AppSidebar from './components/AppSidebar.vue'
import { useAppStore } from './stores/app'

const store = useAppStore()
const route = useRoute()
const collapsed = ref(window.innerWidth < 1180)
const manual = ref(false)

const isConsole = computed(() => route.name === 'console')

function toggleSidebar(): void {
  manual.value = true
  collapsed.value = !collapsed.value
}

function onResize(): void {
  if (!manual.value) collapsed.value = window.innerWidth < 1180
}

onMounted(() => {
  store.init()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))

function toastIcon(tone: string) {
  return { success: CheckCircle2, warning: AlertTriangle, error: XCircle, default: Info }[tone] || Info
}
function toastTone(tone: string): string {
  return (
    {
      success: 'text-success',
      warning: 'text-warning',
      error: 'text-destructive',
      default: 'text-muted-foreground',
    }[tone] || 'text-muted-foreground'
  )
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 250ms cubic-bezier(0.25, 1, 0.5, 1), transform 250ms cubic-bezier(0.25, 1, 0.5, 1);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
