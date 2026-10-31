<template>
  <aside
    class="flex h-full shrink-0 flex-col border-r border-border bg-[var(--app-sidebar)] transition-[width] duration-300 ease-[cubic-bezier(.25,1,.5,1)]"
    :style="{ width: collapsed ? '72px' : '232px' }"
  >
    <nav class="flex-1 overflow-y-auto overflow-x-hidden px-3 pb-3">
      <template v-for="group in groups" :key="group.label">
        <p v-if="!collapsed" class="nav-section-label">{{ group.label }}</p>
        <div v-else class="my-4 h-px bg-border" />
        <div class="space-y-0.5">
          <Tooltip
            v-for="item in group.items"
            :key="item.to"
            :content="collapsed ? item.label : ''"
            placement="right"
            :disabled="!collapsed"
          >
            <RouterLink
              :to="item.to"
              class="sidebar-link"
              :class="{ active: isActive(item.to), 'justify-center px-0': collapsed }"
            >
              <component :is="item.icon" :size="17" class="shrink-0" />
              <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
              <span
                v-if="!collapsed && item.badge"
                class="ml-auto rounded-[3px] border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground"
              >
                {{ item.badge }}
              </span>
            </RouterLink>
          </Tooltip>
        </div>
      </template>
    </nav>

    <div class="border-t border-border p-3">
      <RouterLink
        to="/settings"
        class="sidebar-link"
        :class="{ active: isActive('/settings'), 'justify-center px-0': collapsed }"
        :title="collapsed ? '设置' : undefined"
      >
        <Settings :size="17" class="shrink-0" />
        <span v-if="!collapsed">设置</span>
      </RouterLink>

      <div v-if="!collapsed" class="mt-3 rounded-[calc(var(--radius)-2px)] border border-border bg-background px-3 py-2.5">
        <div class="flex items-center justify-between">
          <span class="eyebrow">STATUS</span>
          <StatusDot :status="onlineCount ? 'online' : 'offline'" :size="10" />
        </div>
        <p class="mt-2 text-[12px] font-medium">{{ onlineCount }} / {{ store.instances.length }} 实例在线</p>
        <p class="mt-1 text-[11px] text-muted-foreground">
          {{ store.socketState === 'live' ? '事件流已连接' : store.socketState === 'connecting' ? '正在连接内核' : '事件流离线' }}
        </p>
      </div>

      <div v-if="!collapsed" class="mt-3 flex items-center justify-between px-1">
        <span class="mono text-[10px] tracking-[0.08em] text-muted-foreground">v0.0.1 BETA</span>
        <span class="mono text-[10px] text-muted-foreground">BUILD {{ store.overview?.build || '—' }}</span>
      </div>
      <div v-else class="mt-3 text-center">
        <span class="mono text-[9px] text-muted-foreground">BETA</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Tooltip } from 'fuxsto-design'
import {
  Blocks, Brain, Cpu, LayoutDashboard, MessagesSquare, ScrollText, Server, Settings, UserRound,
} from 'lucide-vue-next'
import StatusDot from './StatusDot.vue'
import { useAppStore } from '../stores/app'

defineProps<{ collapsed: boolean }>()
const store = useAppStore()
const route = useRoute()
const onlineCount = computed(() => store.onlineCount)

const groups = [
  {
    label: '工作台',
    items: [
      { to: '/', label: '总览', icon: LayoutDashboard },
      { to: '/instances', label: '实例', icon: Server },
      { to: '/console', label: '消息控制台', icon: MessagesSquare },
    ],
  },
  {
    label: '智能',
    items: [
      { to: '/personas', label: '人格', icon: UserRound },
      { to: '/memory', label: '记忆', icon: Brain },
      { to: '/models', label: '模型', icon: Cpu },
    ],
  },
  {
    label: '扩展与运维',
    items: [
      { to: '/plugins', label: '插件', icon: Blocks, badge: 'BETA' },
      { to: '/logs', label: '日志与审计', icon: ScrollText },
    ],
  },
]

function isActive(path: string): boolean {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}
</script>
