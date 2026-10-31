<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="LOG / 运行日志"
      title="每一口气都有记录"
      description="核心、OneBot、消息、插件与审计日志统一落库。事件流到达时自动追加到列表顶部；筛选条件在服务端生效。"
    >
      <template #actions>
        <span class="status-capsule">
          <span class="h-1.5 w-1.5 rounded-full" :class="store.socketState === 'live' ? 'bg-success live-dot' : 'bg-muted-foreground'" />
          <span class="mono text-[10px]">{{ store.socketState === 'live' ? 'LIVE TAIL' : 'IDLE' }}</span>
        </span>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="load">刷新</Button>
      </template>
    </PageHeader>

    <Card padding="md">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <Segmented v-model="level" :options="levelOptions" size="sm" @change="load" />
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Select v-model="source" :options="sourceOptions" size="sm" class="sm:w-44" @update:model-value="load" />
          <label class="search-box sm:w-60">
            <Search :size="13" />
            <input v-model="query" type="search" placeholder="搜索日志内容" aria-label="搜索日志内容" @keyup.enter="load" />
          </label>
        </div>
      </div>
    </Card>

    <Card padding="none" class="overflow-hidden">
      <div class="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 class="text-[13px] font-semibold">日志流</h2>
        <span class="mono text-[10px] text-muted-foreground">{{ logs.length }} / {{ limit }} ENTRIES</span>
      </div>
      <Table :columns="columns" :data="logs" row-key="id" size="sm" hover :empty-text="'没有匹配的日志'">
        <template #cell-level="{ row }">
          <span
            class="mono inline-flex min-w-[42px] justify-center rounded-[3px] border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.06em]"
            :class="levelClass(row.level)"
          >
            {{ levelLabel(row.level) }}
          </span>
        </template>
        <template #cell-created_at="{ row }">
          <span class="mono text-[10px] text-muted-foreground">{{ formatDateTime(row.created_at) }}</span>
        </template>
        <template #cell-source="{ row }">
          <span class="mono text-[10.5px]">{{ row.source }}</span>
        </template>
        <template #cell-message="{ row }">
          <p class="max-w-2xl truncate text-[12.5px]" :title="row.message">{{ row.message }}</p>
        </template>
        <template #cell-detail="{ row }">
          <Button v-if="row.detail" variant="ghost" size="sm" @click="inspect(row)">查看</Button>
          <span v-else class="text-[11px] text-muted-foreground">—</span>
        </template>
      </Table>
    </Card>

    <Drawer v-model:open="drawerOpen" title="日志详情" size="lg" :show-confirm="false">
      <div v-if="selected" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-[var(--radius)] border border-border p-3">
            <p class="eyebrow">LEVEL</p>
            <p class="mt-1.5 text-[13px] font-semibold">{{ levelLabel(selected.level) }}</p>
          </div>
          <div class="rounded-[var(--radius)] border border-border p-3">
            <p class="eyebrow">SOURCE</p>
            <p class="mono mt-1.5 text-[12px]">{{ selected.source }}</p>
          </div>
        </div>
        <div>
          <p class="eyebrow mb-2">MESSAGE</p>
          <p class="text-[13px] leading-relaxed">{{ selected.message }}</p>
        </div>
        <div>
          <p class="eyebrow mb-2">TIMESTAMP</p>
          <p class="mono text-[11px] text-muted-foreground">{{ formatDateTime(selected.created_at) }}</p>
        </div>
        <div v-if="selected.detail">
          <p class="eyebrow mb-2">DETAIL</p>
          <CodeBlock :content="JSON.stringify(selected.detail, null, 2)" />
        </div>
      </div>
      <template #footer>
        <Button variant="secondary" @click="drawerOpen = false">关闭</Button>
      </template>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { Button, Card, Drawer, Segmented, Select, Table } from 'fuxsto-design'
import type { TableColumn } from 'fuxsto-design'
import { RefreshCw, Search } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import CodeBlock from '../components/CodeBlock.vue'
import { useAppStore } from '../stores/app'
import { api } from '../api'
import type { LogEntry } from '../types'
import { formatDateTime, levelLabel } from '../utils'

const store = useAppStore()
const logs = ref<LogEntry[]>([])
const level = ref('all')
const source = ref('all')
const query = ref('')
const limit = 120
const drawerOpen = ref(false)
const selected = ref<LogEntry | null>(null)

const levelOptions = [
  { label: '全部', value: 'all' },
  { label: 'INFO', value: 'info' },
  { label: 'WARN', value: 'warn' },
  { label: 'ERROR', value: 'error' },
  { label: 'DEBUG', value: 'debug' },
]
const sourceOptions = [
  { label: '全部来源', value: 'all' },
  { label: 'core', value: 'core' },
  { label: 'onebot', value: 'onebot' },
  { label: 'message', value: 'message' },
  { label: 'plugin', value: 'plugin' },
  { label: 'provider', value: 'provider' },
  { label: 'persona', value: 'persona' },
  { label: 'memory', value: 'memory' },
  { label: 'settings', value: 'settings' },
  { label: 'audit', value: 'audit' },
]
const columns: TableColumn[] = [
  { key: 'level', title: '级别', width: 74 },
  { key: 'created_at', title: '时间', width: 160 },
  { key: 'source', title: '来源', width: 96 },
  { key: 'message', title: '内容' },
  { key: 'detail', title: '', width: 64, align: 'right' },
]

function levelClass(value: string): string {
  return (
    {
      error: 'border-destructive/40 bg-destructive/10 text-destructive',
      warn: 'border-warning/40 bg-warning/10 text-warning',
      debug: 'border-border bg-secondary text-muted-foreground',
      info: 'border-border bg-secondary text-foreground',
    }[value] || 'border-border bg-secondary text-muted-foreground'
  )
}

async function load(): Promise<void> {
  try {
    const params = new URLSearchParams({ limit: String(limit) })
    if (level.value !== 'all') params.set('level', level.value)
    if (source.value !== 'all') params.set('source', source.value)
    if (query.value.trim()) params.set('q', query.value.trim())
    logs.value = (await api.logs(`?${params.toString()}`)) as LogEntry[]
  } catch (e) {
    store.toast('日志加载失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

function inspect(entry: LogEntry): void {
  selected.value = entry
  drawerOpen.value = true
}

watch(
  () => store.lastEvent,
  (event) => {
    if (!event || event.type !== 'log.appended') return
    const entry = event.data as unknown as LogEntry
    if (!entry.id) return
    if (level.value !== 'all' && entry.level !== level.value) return
    if (source.value !== 'all' && entry.source !== source.value) return
    if (query.value.trim() && !entry.message.includes(query.value.trim())) return
    if (logs.value.some((l) => l.id === entry.id)) return
    logs.value = [{ ...entry, detail: entry.detail ?? null }, ...logs.value].slice(0, limit)
  },
)

onMounted(load)
</script>
