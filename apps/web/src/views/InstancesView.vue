<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="CONNECTIONS / 实例"
      title="实例与协议端"
      description="每个实例对应一个 QQ 账号与一个协议端连接。BETA 内置演示管线，并开放 OneBot v11 反向 WS 的真实接入路径。"
    >
      <template #actions>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="reload">刷新</Button>
        <Button variant="primary" size="sm" :icon="Plus" @click="openCreate">新建实例</Button>
      </template>
    </PageHeader>

    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <button
        v-for="(item, i) in summary"
        :key="item.label"
        class="flex items-center gap-3 rounded-[var(--radius)] border border-border bg-background p-4 text-left transition-colors hover:bg-accent"
        @click="filter = i === 0 ? 'all' : item.filter"
      >
        <span class="grid h-9 w-9 place-items-center rounded-[calc(var(--radius)-2px)] border border-border bg-secondary">
          <component :is="item.icon" :size="16" :class="item.tone" />
        </span>
        <span>
          <span class="block text-[19px] font-bold leading-none tabular-nums">{{ item.value }}</span>
          <span class="mt-1.5 block text-[11px] text-muted-foreground">{{ item.label }}</span>
        </span>
      </button>
    </div>

    <Card padding="none">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3.5">
        <div class="flex items-center gap-2">
          <h2 class="text-[14px] font-semibold">全部实例</h2>
          <Chip size="sm" variant="secondary">{{ filtered.length }}</Chip>
        </div>
        <div class="flex items-center gap-2">
          <Input v-model="keyword" size="sm" placeholder="搜索名称 / 账号 / 地址" :prefix-icon="Search" class="w-[230px]" />
          <Segmented v-model="filter" :options="filterOptions" size="sm" />
        </div>
      </div>
      <Table
        :columns="columns"
        :data="filtered"
        row-key="id"
        size="md"
        :bordered="false"
        hover
        empty-text="还没有实例。新建一个，或使用演示管线。"
        @row-click="openDetail"
      >
        <template #cell-name="{ row }">
          <div class="flex items-center gap-3">
            <span class="grid h-8 w-8 place-items-center rounded-[4px] border border-border bg-secondary text-muted-foreground">
              <Server :size="14" />
            </span>
            <div class="min-w-0">
              <p class="truncate text-[13px] font-medium">{{ row.name }}</p>
              <p class="mono mt-0.5 text-[10px] text-muted-foreground">
                {{ row.self_id || 'NO UIN' }} · {{ row.config?.protocol || '未知协议端' }}
              </p>
            </div>
          </div>
        </template>
        <template #cell-status="{ row }">
          <StatusDot :status="row.status" :size="12" show-label />
        </template>
        <template #cell-mode="{ row }">
          <Chip size="sm" variant="outline">{{ modeLabel(row.mode) }}</Chip>
        </template>
        <template #cell-endpoint="{ row }">
          <span class="mono block max-w-[260px] truncate text-[11px] text-muted-foreground">{{ row.endpoint || '未配置' }}</span>
        </template>
        <template #cell-latency="{ row }">
          <span class="mono text-[11px]">{{ row.latency_ms ? `${row.latency_ms} ms` : '—' }}</span>
        </template>
        <template #cell-heartbeat="{ row }">
          <span class="text-[11px] text-muted-foreground">{{ relativeTime(row.updated_at) }}</span>
        </template>
        <template #cell-action="{ row }">
          <div class="flex items-center justify-end gap-1" @click.stop>
            <Tooltip content="详情" placement="top">
              <Button variant="ghost" size="sm" :icon="PanelRightOpen" @click="openDetail(row)" />
            </Tooltip>
            <Button v-if="row.status !== 'online'" variant="ghost" size="sm" :icon="Play" @click="connect(row)">连接</Button>
            <Button v-else variant="ghost" size="sm" :icon="Square" @click="disconnect(row)">断开</Button>
            <Tooltip content="删除" placement="top">
              <Button variant="ghost" size="sm" :icon="Trash2" danger @click="remove(row)" />
            </Tooltip>
          </div>
        </template>
      </Table>
    </Card>

    <Alert
      type="info"
      title="如何让真实账号上线"
      description="在 NapCat 或 SnowLuma 中启用反向 WebSocket，指向 ws://127.0.0.1:6199/onebot/v11/ws/<实例 ID>；本机演示无需协议端。"
    />

    <Drawer
      v-model:open="drawerOpen"
      :title="editing ? '编辑实例' : '新建实例'"
      description="创建后可在实例详情中查看能力探测与原始配置。"
      size="md"
      :show-confirm="false"
    >
      <div class="space-y-5">
        <div>
          <label class="eyebrow mb-2 block">实例名称</label>
          <Input v-model="form.name" placeholder="例如：风箱主号 · 10001" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="eyebrow mb-2 block">连接模式</label>
            <Select v-model="form.mode" :options="modeOptions" />
          </div>
          <div>
            <label class="eyebrow mb-2 block">协议端</label>
            <Select v-model="form.protocol" :options="protocolOptions" />
          </div>
        </div>
        <div>
          <label class="eyebrow mb-2 block">QQ 账号（self_id）</label>
          <Input v-model="form.self_id" placeholder="留空则由协议端握手时上报" />
        </div>
        <div v-if="form.mode !== 'demo'">
          <label class="eyebrow mb-2 block">连接地址</label>
          <Input v-model="form.endpoint" placeholder="ws://127.0.0.1:6199/onebot/v11/ws/..." />
        </div>
        <div v-if="form.mode !== 'demo'">
          <label class="eyebrow mb-2 block">Access Token（可选）</label>
          <Input v-model="form.access_token" type="password" placeholder="与协议端配置保持一致" />
        </div>
        <Alert
          v-if="form.mode === 'demo'"
          type="info"
          title="演示管线"
          description="不连接真实 QQ。内核每 11–18 秒生成一条消息，用于验证控制台、事件流与落库。"
        />
        <div v-else class="rounded-[var(--radius)] border border-border bg-secondary p-3">
          <p class="eyebrow mb-2">PROTOCOL ENDPOINT</p>
          <p class="mono break-all text-[11px] text-muted-foreground">
            ws://127.0.0.1:6199/onebot/v11/ws/{{ editing?.id || '<实例 ID>' }}
          </p>
        </div>
      </div>
      <template #footer>
        <Button variant="secondary" @click="drawerOpen = false">取消</Button>
        <Button variant="primary" :loading="saving" @click="saveInstance">保存</Button>
      </template>
    </Drawer>

    <Drawer
      v-model:open="detailOpen"
      :title="selected?.name || '实例详情'"
      :description="selected ? `${modeLabel(selected.mode)} · ${selected.endpoint || '未配置地址'}` : ''"
      size="lg"
      :show-confirm="false"
      cancel-text="关闭"
    >
      <div v-if="selected" class="space-y-5">
        <div class="flex items-center justify-between rounded-[var(--radius)] border border-border bg-secondary p-4">
          <div class="flex items-center gap-3">
            <StatusDot :status="selected.status" :size="14" />
            <div>
              <p class="text-[13px] font-semibold">{{ statusMeta(selected.status) }}</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">延迟 {{ selected.latency_ms ? `${selected.latency_ms} ms` : '未测量' }}</p>
            </div>
          </div>
          <div class="flex gap-2">
            <Button v-if="selected.status !== 'online'" variant="outline" size="sm" :icon="Play" @click="connect(selected)">连接</Button>
            <Button v-else variant="outline" size="sm" :icon="Square" @click="disconnect(selected)">断开</Button>
            <Button variant="ghost" size="sm" :icon="Pencil" @click="openEdit(selected)">编辑</Button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-[var(--radius)] border border-border p-3.5">
            <p class="eyebrow">SELF ID</p>
            <p class="mono mt-2 text-[13px]">{{ selected.self_id || '未上报' }}</p>
          </div>
          <div class="rounded-[var(--radius)] border border-border p-3.5">
            <p class="eyebrow">CREATED</p>
            <p class="mono mt-2 text-[13px]">{{ formatDateTime(selected.created_at) }}</p>
          </div>
        </div>

        <div>
          <div class="mb-2 flex items-center justify-between">
            <p class="eyebrow">CAPABILITIES / 能力探测</p>
            <span v-if="capabilities" class="mono text-[10px] text-muted-foreground">{{ capabilities.probed_at }}</span>
          </div>
          <div v-if="capabilities" class="grid grid-cols-2 gap-2">
            <div
              v-for="(value, key) in capabilities.capabilities"
              :key="key"
              class="flex items-center justify-between rounded-[4px] border border-border px-3 py-2"
            >
              <span class="mono text-[11px]">{{ key }}</span>
              <CheckCircle2 v-if="value" :size="13" class="text-success" />
              <XCircle v-else :size="13" class="text-muted-foreground" />
            </div>
          </div>
          <p v-else class="text-[12px] text-muted-foreground">正在读取能力表…</p>
        </div>

        <CodeBlock label="CONFIG / 原始配置" :content="JSON.stringify(selected.config, null, 2)" />
      </div>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Alert, Button, Card, Chip, Drawer, Input, Segmented, Select, Table, Tooltip } from 'fuxsto-design'
import { Dialog } from 'fuxsto-design/dialog'
import {
  CheckCircle2, CircleAlert, PanelRightOpen, Pencil, Play, Plus, RefreshCw, Search, Server, Square,
  Trash2, Wifi, WifiOff, XCircle,
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import StatusDot from '../components/StatusDot.vue'
import CodeBlock from '../components/CodeBlock.vue'
import { useAppStore } from '../stores/app'
import { api } from '../api'
import type { Instance } from '../types'
import { formatDateTime, modeLabel, relativeTime, statusMeta as statusMap } from '../utils'

const store = useAppStore()
const keyword = ref('')
const filter = ref<'all' | 'online' | 'offline' | 'error'>('all')
const drawerOpen = ref(false)
const detailOpen = ref(false)
const editing = ref<Instance | null>(null)
const selected = ref<Instance | null>(null)
const capabilities = ref<{ probed_at: string; capabilities: Record<string, boolean>; protocol?: string } | null>(null)
const saving = ref(false)

const form = ref({ name: '', mode: 'reverse_ws', protocol: 'NapCat', self_id: '', endpoint: '', access_token: '' })

const filtered = computed(() => {
  let list = store.instances
  if (filter.value !== 'all') list = list.filter((i) => i.status === filter.value)
  const q = keyword.value.trim().toLowerCase()
  if (q) list = list.filter((i) => [i.name, i.self_id, i.endpoint].some((v) => String(v).toLowerCase().includes(q)))
  return list
})

const summary = computed(() => [
  { label: '全部实例', value: store.instances.length, icon: Server, tone: 'text-foreground', filter: 'all' as const },
  { label: '在线', value: store.instances.filter((i) => i.status === 'online').length, icon: Wifi, tone: 'text-success', filter: 'online' as const },
  { label: '离线 / 等待', value: store.instances.filter((i) => ['offline', 'connecting', 'unconfigured'].includes(i.status)).length, icon: WifiOff, tone: 'text-muted-foreground', filter: 'offline' as const },
  { label: '异常', value: store.instances.filter((i) => i.status === 'error').length, icon: CircleAlert, tone: 'text-destructive', filter: 'error' as const },
])

const columns = [
  { key: 'name', title: '实例' },
  { key: 'status', title: '状态' },
  { key: 'mode', title: '模式' },
  { key: 'endpoint', title: '地址' },
  { key: 'latency', title: '延迟', width: 90 },
  { key: 'heartbeat', title: '最后心跳', width: 110 },
  { key: 'action', title: '', width: 190, align: 'right' as const },
]

const modeOptions = [
  { label: '反向 WS（推荐）', value: 'reverse_ws' },
  { label: '演示管线', value: 'demo' },
  { label: '正向 WS（规划）', value: 'forward_ws', disabled: true },
  { label: 'HTTP（规划）', value: 'http', disabled: true },
]
const protocolOptions = [
  { label: 'NapCat', value: 'NapCat' },
  { label: 'SnowLuma', value: 'SnowLuma' },
  { label: '其他 / 演示', value: '演示' },
]
const filterOptions = [
  { label: '全部', value: 'all' },
  { label: '在线', value: 'online' },
  { label: '离线', value: 'offline' },
  { label: '异常', value: 'error' },
]

function statusMeta(status: string): string {
  return statusMap[status]?.label || status
}

function openCreate(): void {
  editing.value = null
  Object.assign(form.value, { name: '', mode: 'reverse_ws', protocol: 'NapCat', self_id: '', endpoint: '', access_token: '' })
  drawerOpen.value = true
}

function openEdit(row: Instance): void {
  editing.value = row
  Object.assign(form.value, {
    name: row.name,
    mode: row.mode,
    protocol: String(row.config?.protocol || 'NapCat'),
    self_id: row.self_id,
    endpoint: row.endpoint,
    access_token: row.access_token || '',
  })
  detailOpen.value = false
  drawerOpen.value = true
}

async function saveInstance(): Promise<void> {
  if (!form.value.name.trim()) {
    store.toast('请填写实例名称', 'warning')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await api.updateInstance(editing.value.id, {
        name: form.value.name.trim(), mode: form.value.mode, endpoint: form.value.endpoint.trim(),
        access_token: form.value.access_token, self_id: form.value.self_id.trim(),
      })
      store.toast('实例已更新', 'success', form.value.name)
    } else {
      await api.createInstance({
        name: form.value.name.trim(), mode: form.value.mode, endpoint: form.value.endpoint.trim(),
        access_token: form.value.access_token, self_id: form.value.self_id.trim(), protocol: form.value.protocol,
      })
      store.toast('实例已创建', 'success', form.value.name)
    }
    drawerOpen.value = false
    await store.loadCore()
  } catch (e) {
    store.toast('保存失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    saving.value = false
  }
}

async function openDetail(row: Instance): Promise<void> {
  selected.value = row
  capabilities.value = null
  detailOpen.value = true
  try {
    capabilities.value = (await api.capabilities(row.id)) as typeof capabilities.value
  } catch {
    capabilities.value = null
  }
}

async function connect(row: Instance): Promise<void> {
  try {
    const out = (await api.connectInstance(row.id)) as { message?: string; status?: string }
    store.toast(out.message || '连接请求已发送', out.status === 'error' ? 'warning' : 'success')
    await store.loadCore()
    if (selected.value?.id === row.id) await openDetail(row)
  } catch (e) {
    store.toast('连接失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

async function disconnect(row: Instance): Promise<void> {
  try {
    await api.disconnectInstance(row.id)
    store.toast('实例已断开', 'warning', row.name)
    await store.loadCore()
    if (selected.value?.id === row.id) await openDetail(row)
  } catch (e) {
    store.toast('断开失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

function remove(row: Instance): void {
  Dialog.confirm({
    title: '删除实例',
    description: `将删除「${row.name}」及其会话与消息记录，此操作不可撤销。`,
    type: 'warning',
    danger: true,
    confirmText: '删除',
    onConfirm: async () => {
      try {
        await api.deleteInstance(row.id)
        store.toast('实例已删除', 'warning', row.name)
        detailOpen.value = false
        await store.loadCore()
      } catch (e) {
        store.toast('删除失败', 'error', e instanceof Error ? e.message : String(e))
      }
    },
  })
}

async function reload(): Promise<void> {
  await store.loadCore()
  store.toast('实例列表已刷新', 'success')
}

onMounted(() => {
  if (!store.instances.length) void store.loadCore()
})
</script>
