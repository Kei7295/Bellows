<template>
  <header class="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-[var(--app-titlebar)] px-3 app-drag-region">
    <div class="flex w-[196px] shrink-0 items-center gap-2.5 pl-1">
      <button
        class="app-no-drag grid h-8 w-8 place-items-center rounded-[calc(var(--radius)-2px)] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        :aria-label="collapsed ? '展开侧边栏' : '折叠侧边栏'"
        @click="$emit('toggle-sidebar')"
      >
        <PanelLeftOpen v-if="collapsed" :size="17" />
        <PanelLeftClose v-else :size="17" />
      </button>
      <div class="flex items-center gap-2">
        <BrandMark :size="22" class="text-foreground" />
        <div class="leading-none">
          <p class="text-[13px] font-bold tracking-[-0.01em]">Bellows</p>
          <p class="mt-1 text-[10px] font-medium tracking-[0.12em] text-muted-foreground">风箱 · BETA</p>
        </div>
      </div>
    </div>

    <div class="app-no-drag h-5 w-px bg-border" />

    <Menu
      :options="instanceOptions"
      placement="bottom-start"
      class="app-no-drag"
      @select="onSelectInstance"
    >
      <button class="pressable flex h-9 items-center gap-2 rounded-[calc(var(--radius)-2px)] border border-transparent px-2.5 text-left hover:border-border hover:bg-accent">
        <StatusDot :status="activeInstance?.status || 'offline'" :size="12" />
        <span class="max-w-[150px] truncate text-[12px] font-medium">
          {{ activeInstance?.name || '未选择实例' }}
        </span>
        <ChevronDown :size="13" class="text-muted-foreground" />
      </button>
    </Menu>

    <div class="app-no-drag flex min-w-0 flex-1 justify-center px-2">
      <label class="search-box w-full max-w-[380px]">
        <Search :size="14" />
        <input
          v-model="search"
          type="search"
          placeholder="搜索会话、实例或日志"
          aria-label="全局搜索"
          @keydown.enter="submitSearch"
        />
        <span class="kbd shrink-0">Enter</span>
      </label>
    </div>

    <div class="app-no-drag flex shrink-0 items-center gap-1.5">
      <span class="status-capsule mr-1">
        <span
          class="h-1.5 w-1.5 rounded-full"
          :class="socketState === 'live' ? 'bg-success' : socketState === 'connecting' ? 'bg-warning' : 'bg-muted-foreground'"
        />
        <span class="mono text-[11px]">{{ socketState === 'live' ? 'CORE LIVE' : socketState === 'connecting' ? 'CORE LINKING' : 'CORE OFFLINE' }}</span>
      </span>

      <Tooltip :content="themeHint" placement="bottom">
        <button
          class="grid h-8 w-8 place-items-center rounded-[calc(var(--radius)-2px)] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          aria-label="切换主题"
          @click="cycleTheme"
        >
          <Sun v-if="theme === 'light'" :size="16" />
          <Moon v-else-if="theme === 'dark'" :size="16" />
          <Monitor v-else :size="16" />
        </button>
      </Tooltip>

      <Tooltip content="通知与告警" placement="bottom">
        <button
          class="relative grid h-8 w-8 place-items-center rounded-[calc(var(--radius)-2px)] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          aria-label="通知与告警"
          @click="router.push('/logs')"
        >
          <Bell :size="16" />
          <span v-if="alertCount" class="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-destructive" />
        </button>
      </Tooltip>

      <div class="ml-1 hidden items-center gap-0.5 md:flex">
        <button class="window-btn" aria-label="最小化窗口" @click="desktopOnly">
          <Minus :size="14" />
        </button>
        <button class="window-btn" aria-label="最大化窗口" @click="desktopOnly">
          <Square :size="11" />
        </button>
        <button class="window-btn close" aria-label="关闭窗口" @click="desktopOnly">
          <X :size="14" />
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Menu, Tooltip } from 'fuxsto-design'
import {
  Bell, ChevronDown, Minus, Monitor, Moon, PanelLeftClose, PanelLeftOpen, Search, Square, Sun, X, Server,
} from 'lucide-vue-next'
import BrandMark from './BrandMark.vue'
import StatusDot from './StatusDot.vue'
import { useAppStore } from '../stores/app'

defineProps<{ collapsed: boolean }>()
defineEmits<{ 'toggle-sidebar': [] }>()

const store = useAppStore()
const router = useRouter()

const activeInstance = computed(() => store.activeInstance)
const socketState = computed(() => store.socketState)
const theme = computed(() => store.theme)
const search = computed({
  get: () => store.search,
  set: (v: string) => (store.search = v),
})
const themeHint = computed(
  () => ({ system: '跟随系统 · 点击切换', light: '亮色 · 点击切换', dark: '暗色 · 点击切换' })[store.theme],
)
const alertCount = computed(() => store.overview?.alerts.length || 0)
const instanceOptions = computed(() => [
  store.instances.map((i) => ({ label: `${i.name}${i.status === 'online' ? '' : ' · 离线'}`, value: i.id, icon: Server })),
])

function onSelectInstance(item: { value: string | number }): void {
  store.setActiveInstance(String(item.value))
  void store.refreshStreams()
}

function cycleTheme(): void {
  const next = { system: 'light', light: 'dark', dark: 'system' } as const
  store.setTheme(next[store.theme])
}

function submitSearch(): void {
  if (!store.search.trim()) return
  router.push('/console')
}

function desktopOnly(): void {
  store.toast('窗口控制仅在 Tauri 桌面壳中生效', 'default', '当前以浏览器方式运行 BETA 内核与界面')
}
</script>
