<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="MEMORY / 长期记忆"
      title="记住该记住的"
      description="记忆按群聊或用户归档，供回复上下文检索。BETA 支持浏览、搜索与删除，自动抽取与向量检索尚未接入。"
    >
      <template #actions>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="load">刷新</Button>
      </template>
    </PageHeader>

    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard label="记忆条目" :value="memories.length" suffix="条" hint="当前结果集" :icon="BrainCircuit" />
      <StatCard label="群聊记忆" :value="scopeCount('group')" suffix="条" hint="按群归档" :icon="Users" />
      <StatCard label="用户记忆" :value="scopeCount('user')" suffix="条" hint="按用户归档" :icon="UserRound" />
      <StatCard label="高权重" :value="importantCount" suffix="条" hint="importance ≥ 4" :icon="Star" tone="warning" />
    </div>

    <Card padding="md">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Segmented v-model="scope" :options="scopeOptions" size="sm" @change="load" />
        <label class="search-box sm:w-64">
          <Search :size="13" />
          <input v-model="query" type="search" placeholder="搜索记忆内容" aria-label="搜索记忆内容" @keyup.enter="load" />
        </label>
      </div>
    </Card>

    <Card v-if="memories.length" padding="none" class="overflow-hidden">
      <Table :columns="columns" :data="memories" row-key="id" size="sm" hover>
        <template #cell-scope="{ row }">
          <Chip size="sm" :variant="row.scope === 'group' ? 'secondary' : 'outline'">{{ scopeLabel(row.scope) }}</Chip>
        </template>
        <template #cell-owner="{ row }">
          <div class="min-w-0">
            <p class="truncate text-[12.5px] font-medium">{{ row.owner_name || '未命名' }}</p>
            <p class="mono mt-0.5 truncate text-[10px] text-muted-foreground">{{ row.owner_id || '—' }}</p>
          </div>
        </template>
        <template #cell-text="{ row }">
          <p class="max-w-xl text-[12.5px] leading-relaxed">{{ row.text }}</p>
        </template>
        <template #cell-importance="{ row }">
          <div class="flex items-center gap-1.5">
            <span
              v-for="i in 5"
              :key="i"
              class="h-1.5 w-1.5 rounded-full"
              :class="i <= row.importance ? 'bg-foreground' : 'bg-border'"
            />
            <span class="mono ml-1 text-[10px] text-muted-foreground">{{ row.importance }}</span>
          </div>
        </template>
        <template #cell-created_at="{ row }">
          <span class="mono text-[10px] text-muted-foreground">{{ formatDateTime(row.created_at) }}</span>
        </template>
        <template #cell-actions="{ row }">
          <Tooltip content="删除记忆" placement="top">
            <Button variant="ghost" size="sm" :icon="Trash2" danger @click="remove(row)" />
          </Tooltip>
        </template>
      </Table>
    </Card>

    <Card v-else padding="lg">
      <Empty title="没有匹配的记忆" description="清空搜索词或切换范围。记忆条目会在线程回复中逐步积累。" :icon="BrainCircuit" />
    </Card>

    <Alert
      type="info"
      title="存储位置"
      description="记忆写入本地 SQLite（data.db）。删除即从库中移除，不保留副本。"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Alert, Button, Card, Chip, Empty, Segmented, Table, Tooltip } from 'fuxsto-design'
import type { TableColumn } from 'fuxsto-design'
import { Dialog } from 'fuxsto-design/dialog'
import { BrainCircuit, RefreshCw, Search, Star, Trash2, UserRound, Users } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { useAppStore } from '../stores/app'
import { api } from '../api'
import type { Memory } from '../types'
import { formatDateTime, scopeLabel } from '../utils'

const store = useAppStore()
const memories = ref<Memory[]>([])
const scope = ref('all')
const query = ref('')

const scopeOptions = [
  { label: '全部', value: 'all' },
  { label: '群聊', value: 'group' },
  { label: '用户', value: 'user' },
]

const columns: TableColumn[] = [
  { key: 'scope', title: '范围', width: 92 },
  { key: 'owner', title: '归属', width: 150 },
  { key: 'text', title: '记忆内容' },
  { key: 'importance', title: '权重', width: 110 },
  { key: 'created_at', title: '创建时间', width: 150 },
  { key: 'actions', title: '', width: 56, align: 'right' },
]

const importantCount = computed(() => memories.value.filter((m) => m.importance >= 4).length)
function scopeCount(kind: string): number {
  return memories.value.filter((m) => m.scope === kind).length
}

async function load(): Promise<void> {
  try {
    const params = new URLSearchParams()
    if (scope.value !== 'all') params.set('scope', scope.value)
    if (query.value.trim()) params.set('q', query.value.trim())
    const qs = params.toString()
    memories.value = (await api.memories(qs ? `?${qs}` : '')) as Memory[]
  } catch (e) {
    store.toast('记忆加载失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

function remove(memory: Memory): void {
  Dialog.confirm({
    title: '删除记忆',
    description: `将删除「${memory.text.slice(0, 40)}${memory.text.length > 40 ? '…' : ''}」。此操作不可撤销。`,
    type: 'warning',
    danger: true,
    confirmText: '删除',
    onConfirm: async () => {
      try {
        await api.deleteMemory(memory.id)
        store.toast('记忆已删除', 'warning')
        await load()
      } catch (e) {
        store.toast('删除失败', 'error', e instanceof Error ? e.message : String(e))
      }
    },
  })
}

onMounted(load)
</script>
