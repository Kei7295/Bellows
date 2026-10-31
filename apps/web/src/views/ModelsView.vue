<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="MODEL / 模型供应商"
      title="给炉火添柴"
      description="登记 OpenAI 兼容、DeepSeek、Ollama 等 Provider。BETA 不发起真实推理请求，连通性测试为模拟探测。"
    >
      <template #actions>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="load">刷新</Button>
        <Button variant="primary" size="sm" :icon="Plus" @click="openCreate">登记 Provider</Button>
      </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
      <Card v-for="provider in providers" :key="provider.id" padding="lg" class="flex flex-col">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-3">
            <span class="grid h-9 w-9 place-items-center rounded-[calc(var(--radius)-2px)] border border-border bg-secondary">
              <ServerCog :size="16" />
            </span>
            <div>
              <p class="text-[14px] font-semibold">{{ provider.name }}</p>
              <p class="mono mt-0.5 text-[10px] uppercase tracking-[0.06em] text-muted-foreground">{{ provider.type }}</p>
            </div>
          </div>
          <Chip size="sm" :variant="provider.enabled ? 'primary' : 'outline'">
            {{ provider.enabled ? '启用中' : '已停用' }}
          </Chip>
        </div>

        <div class="mt-4 space-y-2 rounded-[calc(var(--radius)-2px)] border border-border bg-secondary/40 p-3">
          <div class="flex items-center justify-between gap-3">
            <span class="eyebrow">MODEL</span>
            <span class="mono truncate text-[11px]">{{ provider.model || '未填写' }}</span>
          </div>
          <div class="flex items-center justify-between gap-3">
            <span class="eyebrow">ENDPOINT</span>
            <span class="mono max-w-[62%] truncate text-[11px] text-muted-foreground">{{ provider.base_url || '—' }}</span>
          </div>
          <div class="flex items-center justify-between gap-3">
            <span class="eyebrow">SECRET</span>
            <span class="mono text-[11px]" :class="provider.has_key ? 'text-success' : 'text-muted-foreground'">
              {{ provider.has_key ? provider.secret_ref : '未绑定' }}
            </span>
          </div>
        </div>

        <div class="mt-3 flex flex-wrap items-center gap-1.5">
          <Chip size="sm" variant="secondary">温度 {{ provider.params?.temperature ?? '—' }}</Chip>
          <Chip size="sm" variant="secondary">上限 {{ provider.params?.max_tokens ?? '—' }} tokens</Chip>
          <Chip v-if="provider.latency_ms" size="sm" variant="outline">{{ provider.latency_ms }} ms</Chip>
        </div>

        <p class="mt-3 text-[11px] text-muted-foreground">
          最近测试：{{ provider.last_test ? formatDateTime(provider.last_test) : '尚未测试' }}
        </p>

        <div class="mt-4 flex items-center justify-between border-t border-border pt-3.5">
          <div class="flex items-center gap-2">
            <Switch :model-value="provider.enabled" size="sm" @update:model-value="(v: boolean) => toggle(provider, v)" />
            <span class="text-[11px] text-muted-foreground">{{ provider.enabled ? '参与路由' : '不参与路由' }}</span>
          </div>
          <div class="flex items-center gap-1">
            <Button variant="outline" size="sm" :loading="testingId === provider.id" @click="test(provider)">测试</Button>
            <Tooltip content="编辑" placement="top">
              <Button variant="ghost" size="sm" :icon="Pencil" @click="openEdit(provider)" />
            </Tooltip>
            <Tooltip content="删除" placement="top">
              <Button variant="ghost" size="sm" :icon="Trash2" danger @click="remove(provider)" />
            </Tooltip>
          </div>
        </div>
      </Card>

      <Card v-if="!providers.length" padding="lg" class="lg:col-span-2 2xl:col-span-3">
        <Empty title="还没有 Provider" description="登记一个 OpenAI 兼容服务，配置模型与参数。" :icon="ServerCog">
          <template #extra>
            <Button variant="primary" size="sm" :icon="Plus" @click="openCreate">登记 Provider</Button>
          </template>
        </Empty>
      </Card>
    </div>

    <Alert
      type="warning"
      title="BETA 边界"
      description="Provider 配置会写入 SQLite，但不会发起真实推理；「测试」返回模拟延迟并标注 mode=simulated。密钥引用仅保存标识，钥匙串接入在后续版本实现。"
    />

    <Drawer
      v-model:open="drawerOpen"
      :title="editingId ? '编辑 Provider' : '登记 Provider'"
      description="这些字段会用于后续的模型路由；BETA 不会发起真实请求。"
      size="lg"
      :show-confirm="false"
    >
      <div class="space-y-5">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="eyebrow mb-2 block">显示名称</label>
            <Input v-model="form.name" placeholder="例如：DeepSeek" />
          </div>
          <div>
            <label class="eyebrow mb-2 block">Provider 类型</label>
            <Select v-model="form.type" :options="typeOptions" />
          </div>
        </div>
        <div>
          <label class="eyebrow mb-2 block">Base URL</label>
          <Input v-model="form.baseUrl" placeholder="https://api.deepseek.com/v1" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="eyebrow mb-2 block">模型名</label>
            <Input v-model="form.model" placeholder="deepseek-chat" />
          </div>
          <div>
            <label class="eyebrow mb-2 block">温度</label>
            <Input v-model="form.temperature" type="number" placeholder="0.6" />
          </div>
        </div>
        <div>
          <label class="eyebrow mb-2 block">最大输出 tokens</label>
          <Input v-model="form.maxTokens" type="number" placeholder="1024" />
        </div>
        <div class="flex items-center justify-between rounded-[var(--radius)] border border-border p-3.5">
          <div>
            <p class="text-[12.5px] font-medium">登记后立即启用</p>
            <p class="mt-0.5 text-[11px] text-muted-foreground">禁用的 Provider 不参与默认路由。</p>
          </div>
          <Switch v-model="form.enabled" />
        </div>
      </div>
      <template #footer>
        <Button variant="secondary" @click="drawerOpen = false">取消</Button>
        <Button variant="primary" :loading="saving" @click="save">保存</Button>
      </template>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Alert, Button, Card, Chip, Drawer, Empty, Input, Select, Switch, Tooltip } from 'fuxsto-design'
import { Dialog } from 'fuxsto-design/dialog'
import { Pencil, Plus, RefreshCw, ServerCog, Trash2 } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { useAppStore } from '../stores/app'
import { api } from '../api'
import type { Provider } from '../types'
import { formatDateTime } from '../utils'

const store = useAppStore()
const providers = ref<Provider[]>([])
const drawerOpen = ref(false)
const saving = ref(false)
const testingId = ref('')
const editingId = ref('')
const form = ref({ name: '', type: 'openai-compatible', baseUrl: '', model: '', temperature: '0.6', maxTokens: '1024', enabled: true })

const typeOptions = [
  { label: 'OpenAI 兼容', value: 'openai-compatible' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Ollama 本地', value: 'ollama' },
  { label: '自定义', value: 'custom' },
]

async function load(): Promise<void> {
  try {
    providers.value = (await api.providers()) as Provider[]
  } catch (e) {
    store.toast('Provider 加载失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

function openCreate(): void {
  editingId.value = ''
  Object.assign(form.value, { name: '', type: 'openai-compatible', baseUrl: '', model: '', temperature: '0.6', maxTokens: '1024', enabled: true })
  drawerOpen.value = true
}

function openEdit(provider: Provider): void {
  editingId.value = provider.id
  Object.assign(form.value, {
    name: provider.name, type: provider.type, baseUrl: provider.base_url, model: provider.model,
    temperature: String(provider.params?.temperature ?? '0.6'),
    maxTokens: String(provider.params?.max_tokens ?? '1024'),
    enabled: provider.enabled,
  })
  drawerOpen.value = true
}

async function save(): Promise<void> {
  if (!form.value.name.trim()) {
    store.toast('请填写 Provider 名称', 'warning')
    return
  }
  saving.value = true
  try {
    const body = {
      name: form.value.name.trim(), type: form.value.type, base_url: form.value.baseUrl.trim(), model: form.value.model.trim(),
      enabled: form.value.enabled,
      params: { temperature: Number(form.value.temperature) || 0.6, max_tokens: Number(form.value.maxTokens) || 1024 },
    }
    if (editingId.value) await api.updateProvider(editingId.value, body)
    else await api.createProvider(body)
    store.toast(editingId.value ? 'Provider 已更新' : 'Provider 已登记', 'success', form.value.name)
    drawerOpen.value = false
    await load()
  } catch (e) {
    store.toast('保存失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    saving.value = false
  }
}

async function toggle(provider: Provider, enabled: boolean): Promise<void> {
  try {
    await api.updateProvider(provider.id, { enabled })
    provider.enabled = enabled
    store.toast(enabled ? 'Provider 已启用' : 'Provider 已停用', 'success', provider.name)
  } catch (e) {
    store.toast('更新失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

async function test(provider: Provider): Promise<void> {
  testingId.value = provider.id
  try {
    const result = (await api.testProvider(provider.id)) as { latency_ms?: number; mode?: string; message?: string }
    store.toast('模拟探测完成', 'success', `${provider.name} · ${result.latency_ms}ms · ${result.mode}`)
    await load()
  } catch (e) {
    store.toast('测试失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    testingId.value = ''
  }
}

function remove(provider: Provider): void {
  Dialog.confirm({
    title: '删除 Provider',
    description: `将删除「${provider.name}」。使用该 Provider 的会话需要重新配置。`,
    type: 'warning',
    danger: true,
    confirmText: '删除',
    onConfirm: async () => {
      try {
        await api.deleteProvider(provider.id)
        store.toast('Provider 已删除', 'warning', provider.name)
        await load()
      } catch (e) {
        store.toast('删除失败', 'error', e instanceof Error ? e.message : String(e))
      }
    },
  })
}

onMounted(load)
</script>
