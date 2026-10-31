<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="PLUGIN / 插件"
      title="把火用在具体的事上"
      description="内置插件在此开关。BETA 的插件运行时尚未实现：状态切换会落库并记录日志，热重载与市场安装为只读预览。"
    >
      <template #actions>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="load">刷新</Button>
      </template>
    </PageHeader>

    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard label="已安装" :value="plugins.length" suffix="个" hint="内置插件" :icon="Blocks" />
      <StatCard label="启用中" :value="activeCount" suffix="个" hint="状态 active" :icon="Power" tone="success" />
      <StatCard label="已停用" :value="plugins.length - activeCount" suffix="个" hint="状态 inactive" :icon="PowerOff" />
      <StatCard label="运行时" :value="'STUB'" suffix="" hint="后续版本接入" :icon="Cpu" tone="warning" />
    </div>

    <Card padding="none" class="overflow-hidden">
      <div class="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 class="text-[13px] font-semibold">已安装插件</h2>
        <span class="mono text-[10px] text-muted-foreground">{{ plugins.length }} INSTALLED</span>
      </div>
      <Table :columns="columns" :data="plugins" row-key="id" size="sm" hover>
        <template #cell-name="{ row }">
          <div class="flex items-center gap-2.5">
            <span class="grid h-7 w-7 shrink-0 place-items-center rounded-[calc(var(--radius)-2px)] border border-border bg-secondary">
              <Puzzle :size="13" />
            </span>
            <div class="min-w-0">
              <p class="truncate text-[12.5px] font-medium">{{ row.name }}</p>
              <p class="mono mt-0.5 truncate text-[9.5px] text-muted-foreground">{{ row.id }} · v{{ row.version }}</p>
            </div>
          </div>
        </template>
        <template #cell-description="{ row }">
          <p class="max-w-md text-[12px] leading-relaxed text-muted-foreground">{{ row.description }}</p>
        </template>
        <template #cell-trust="{ row }">
          <Chip size="sm" :variant="row.trust === 'builtin' ? 'secondary' : 'outline'">{{ row.trust }}</Chip>
        </template>
        <template #cell-permissions="{ row }">
          <div class="flex flex-wrap gap-1">
            <Chip v-for="perm in row.permissions" :key="perm" size="sm" variant="outline">{{ perm }}</Chip>
          </div>
        </template>
        <template #cell-status="{ row }">
          <Chip size="sm" :variant="row.status === 'active' ? 'primary' : 'outline'">
            {{ row.status === 'active' ? '启用' : row.status === 'inactive' ? '停用' : '异常' }}
          </Chip>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex items-center justify-end gap-1">
            <Switch
              :model-value="row.status === 'active'"
              size="sm"
              @update:model-value="(v: boolean) => toggle(row, v)"
            />
            <Tooltip content="热重载（BETA 未实现）" placement="top">
              <Button variant="ghost" size="sm" :icon="RotateCw" @click="reload(row)" />
            </Tooltip>
          </div>
        </template>
      </Table>
      <div v-if="!plugins.length" class="p-6">
        <Empty title="没有已安装插件" description="BETA 内置插件由种子数据写入；安装流程将在后续版本开放。" :icon="Blocks" />
      </div>
    </Card>

    <Card padding="none" class="overflow-hidden">
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
        <div>
          <h2 class="text-[13px] font-semibold">插件市场</h2>
          <p class="mt-0.5 text-[11px] text-muted-foreground">{{ marketNote }}</p>
        </div>
        <Chip size="sm" variant="outline">只读预览</Chip>
      </div>
      <div class="grid grid-cols-1 gap-3 p-4 lg:grid-cols-3">
        <div v-for="item in market" :key="item.id" class="rounded-[var(--radius)] border border-border p-3.5">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="truncate text-[12.5px] font-semibold">{{ item.name }}</p>
              <p class="mono mt-0.5 text-[9.5px] text-muted-foreground">{{ item.id }} · v{{ item.version }}</p>
            </div>
            <Chip size="sm" variant="secondary">{{ item.author }}</Chip>
          </div>
          <p class="mt-2.5 min-h-[32px] text-[11.5px] leading-relaxed text-muted-foreground">{{ item.description }}</p>
          <div class="mt-2.5 flex flex-wrap gap-1">
            <Chip v-for="perm in item.permissions" :key="perm" size="sm" variant="outline">{{ perm }}</Chip>
          </div>
          <Button variant="outline" size="sm" block class="mt-3" disabled>安装（暂未开放）</Button>
        </div>
        <div v-if="!market.length" class="lg:col-span-3">
          <Empty size="sm" title="市场索引为空" description="市场为只读预览，稍后重试。" :icon="Store" />
        </div>
      </div>
    </Card>

    <Alert
      type="info"
      title="BETA 边界"
      description="插件运行时、权限授予、进程隔离与 SDK 尚未实现。当前页面的开关只更新数据库状态并写入审计日志，不会加载任何插件代码。"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Alert, Button, Card, Chip, Empty, Switch, Table, Tooltip } from 'fuxsto-design'
import type { TableColumn } from 'fuxsto-design'
import { Blocks, Cpu, Power, PowerOff, Puzzle, RefreshCw, RotateCw, Store } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import { useAppStore } from '../stores/app'
import { api } from '../api'
import type { Plugin } from '../types'

interface MarketItem {
  id: string
  name: string
  version: string
  author: string
  description: string
  permissions: string[]
}

const store = useAppStore()
const plugins = ref<Plugin[]>([])
const market = ref<MarketItem[]>([])
const marketNote = ref('正在读取市场索引…')
const activeCount = computed(() => plugins.value.filter((p) => p.status === 'active').length)

const columns: TableColumn[] = [
  { key: 'name', title: '插件', width: 260 },
  { key: 'description', title: '说明' },
  { key: 'trust', title: '来源', width: 84 },
  { key: 'permissions', title: '权限', width: 240 },
  { key: 'status', title: '状态', width: 80 },
  { key: 'actions', title: '', width: 88, align: 'right' },
]

async function load(): Promise<void> {
  try {
    plugins.value = (await api.plugins()) as Plugin[]
  } catch (e) {
    store.toast('插件加载失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

async function loadMarket(): Promise<void> {
  try {
    const data = (await api.pluginMarket()) as { items: MarketItem[]; note: string }
    market.value = data.items || []
    marketNote.value = data.note || '只读预览'
  } catch {
    marketNote.value = '市场索引读取失败'
  }
}

async function toggle(plugin: Plugin, enabled: boolean): Promise<void> {
  try {
    await api.togglePlugin(plugin.id, enabled)
    plugin.status = enabled ? 'active' : 'inactive'
    store.toast(enabled ? '插件已启用' : '插件已停用', 'success', plugin.name)
  } catch (e) {
    store.toast('状态切换失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

async function reload(plugin: Plugin): Promise<void> {
  try {
    const res = (await api.reloadPlugin(plugin.id)) as { ok: boolean; message?: string }
    store.toast('热重载未执行', 'warning', res.message || 'BETA 尚未实现插件运行时')
  } catch (e) {
    store.toast('重载请求失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

onMounted(() => {
  void load()
  void loadMarket()
})
</script>
