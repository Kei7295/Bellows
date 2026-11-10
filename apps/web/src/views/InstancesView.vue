<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="CONNECTIONS / 实例"
      title="实例与协议端"
      description="每个实例对应一个 QQ 账号与一个协议端连接。支持反向 WS（NapCat / SnowLuma 连入）与正向 WS（风箱主动外连 ORBIT 星轨）。"
    >
      <template #actions>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="reload">刷新</Button>
        <Button variant="outline" size="sm" :icon="Orbit" @click="openOrbit">接入 ORBIT</Button>
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
      description="反向 WS：在 NapCat / SnowLuma 中指向 ws://127.0.0.1:6199/onebot/v11/ws/<实例 ID>。正向 WS：启动 ORBIT 后点右上角「接入 ORBIT」，风箱会主动外连。"
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
          <Input v-model="form.endpoint" :placeholder="endpointPlaceholder" />
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
        <div v-else-if="form.mode === 'reverse_ws'" class="rounded-[var(--radius)] border border-border bg-secondary p-3">
          <p class="eyebrow mb-2">PROTOCOL ENDPOINT</p>
          <p class="mono break-all text-[11px] text-muted-foreground">
            ws://127.0.0.1:6199/onebot/v11/ws/{{ editing?.id || '<实例 ID>' }}
          </p>
        </div>
        <div v-else class="rounded-[var(--radius)] border border-border bg-secondary p-3">
          <p class="eyebrow mb-2">ORBIT FORWARD WS</p>
          <p class="mono break-all text-[11px] text-muted-foreground">
            由风箱主动连接 {{ form.endpoint || 'ws://127.0.0.1:8787/onebot/ws' }}
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

    <Drawer
      v-model:open="orbitOpen"
      title="接入星轨 ORBIT"
      description="风箱作为 OneBot 客户端主动外连 ORBIT 的正向 WebSocket，类似 MaiBot 的连接方式。"
      size="md"
      :show-confirm="false"
      cancel-text="关闭"
    >
      <div class="space-y-5">
        <div>
          <label class="eyebrow mb-2 block">ORBIT 地址</label>
          <Input v-model="orbit.base_url" placeholder="http://127.0.0.1:8787" />
          <p class="mt-1.5 text-[11px] text-muted-foreground">
            默认端口 8787；填 http:// 或 ws://.../onebot/ws 均可，风箱会自动归一化。
          </p>
        </div>
        <div>
          <label class="eyebrow mb-2 block">Access Token</label>
          <Input v-model="orbit.access_token" type="password" placeholder="orbit-demo-token" />
          <p class="mt-1.5 text-[11px] text-muted-foreground">
            对应 ORBIT 的 ORBIT_ACCESS_TOKEN，默认 orbit-demo-token。
          </p>
        </div>

        <div v-if="orbitProbe" class="space-y-3 rounded-[var(--radius)] border border-border bg-secondary p-4">
          <div class="flex items-center justify-between gap-3">
            <div class="flex min-w-0 items-center gap-2">
              <StatusDot status="online" :size="10" />
              <span class="truncate text-[13px] font-semibold">{{ orbitAccountLabel }}</span>
            </div>
            <Chip size="sm" variant="secondary">{{ orbitProbe.latency_ms }} ms</Chip>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <p class="eyebrow">SELF ID</p>
              <p class="mono mt-1 text-[12px]">{{ orbitProbe.account.uin || '未上报' }}</p>
            </div>
            <div>
              <p class="eyebrow">ORBIT 版本</p>
              <p class="mono mt-1 text-[12px]">{{ orbitVersionLabel }}</p>
            </div>
          </div>
          <div>
            <p class="eyebrow">FORWARD WS</p>
            <p class="mono mt-1 break-all text-[11px] text-muted-foreground">{{ orbitProbe.ws_url }}</p>
          </div>
        </div>

        <Alert
          type="info"
          title="如何启动 ORBIT"
          description="在 ORBIT 仓库执行 npm install && npm run build && npm start，默认监听 127.0.0.1:8787；接入后风箱会自动重连并订阅消息事件。"
        />
      </div>
      <template #footer>
        <Button variant="secondary" @click="orbitOpen = false">取消</Button>
        <Button variant="outline" :loading="orbitProbing" @click="probeOrbit">探测</Button>
        <Button variant="primary" :loading="orbitSaving" @click="connectOrbit">接入并连接</Button>
      </template>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Alert, Button, Card, Chip, Drawer, Input, Segmented, Select, Table, Tooltip } from 'fuxsto-design'
import { Dialog } from 'fuxsto-design/dialog'
import {
  CheckCircle2, CircleAlert, Orbit, PanelRightOpen, Pencil, Play, Plus, RefreshCw, Search, Server, Square,
  Trash2, Wifi, WifiOff, XCircle,
} from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import StatusDot from '../components/StatusDot.vue'
import CodeBlock from '../components/CodeBlock.vue'
import { useAppStore } from '../stores/app'
import { api } from '../api'
import type { Instance, OrbitConnectResult, OrbitProbe } from '../types'
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
const orbitOpen = ref(false)
const orbitProbing = ref(false)
const orbitSaving = ref(false)
const orbitProbe = ref<OrbitProbe | null>(null)
const orbit = ref({ base_url: 'http://127.0.0.1:8787', access_token: 'orbit-demo-token' })

const orbitAccountLabel = computed(() => {
  const account = orbitProbe.value?.account
  if (!account) return 'ORBIT'
  return account.nickname ? `${account.nickname} · ${account.uin || '未知 UIN'}` : account.uin || 'ORBIT 账号'
})

const orbitVersionLabel = computed(() => {
  const version = orbitProbe.value?.version || {}
  return String(version.app_version || version.app_name || '未知')
})

const form = ref({ name: '', mode: 'reverse_ws', protocol: 'NapCat', self_id: '', endpoint: '', access_token: '' })

const endpointPlaceholder = computed(() =>
  form.value.mode === 'forward_ws'
    ? 'ws://127.0.0.1:8787/onebot/ws（ORBIT 地址）'
    : 'ws://127.0.0.1:6199/onebot/v11/ws/...',
)

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
  { label: '反向 WS（协议端连入）', value: 'reverse_ws' },
  { label: '正向 WS（风箱外连 ORBIT）', value: 'forward_ws' },
  { label: '演示管线', value: 'demo' },
]
const protocolOptions = [
  { label: 'NapCat', value: 'NapCat' },
  { label: 'SnowLuma', value: 'SnowLuma' },
  { label: 'ORBIT / 星轨', value: 'ORBIT' },
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

function openOrbit(): void {
  orbitProbe.value = null
  orbitOpen.value = true
}

async function probeOrbit(): Promise<void> {
  orbitProbing.value = true
  try {
    orbitProbe.value = (await api.orbitProbe({
      base_url: orbit.value.base_url.trim(),
      access_token: orbit.value.access_token,
    })) as OrbitProbe
    store.toast('ORBIT 探测成功', 'success', orbitAccountLabel.value)
  } catch (e) {
    orbitProbe.value = null
    store.toast('探测失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    orbitProbing.value = false
  }
}

async function connectOrbit(): Promise<void> {
  if (!orbit.value.base_url.trim()) {
    store.toast('请填写 ORBIT 地址', 'warning')
    return
  }
  orbitSaving.value = true
  try {
    const out = (await api.orbitConnect({
      base_url: orbit.value.base_url.trim(),
      access_token: orbit.value.access_token,
      name: '',
    })) as OrbitConnectResult
    orbitProbe.value = out.probe
    orbitOpen.value = false
    store.toast('ORBIT 已接入，正在建立连接', 'success', orbitAccountLabel.value)
    await store.loadCore()
    const latest = store.instances.find((item) => item.id === out.instance.id) || out.instance
    await openDetail(latest)
  } catch (e) {
    store.toast('接入失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    orbitSaving.value = false
  }
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
