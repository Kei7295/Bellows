<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="PERSONA / 人格"
      title="说话的炉火"
      description="人格由系统提示、语气与边界组成。BETA 支持创建与编辑，演示回复引擎暂不读取提示词，绑定关系在控制台 Inspector 中预留。"
    >
      <template #actions>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="load">刷新</Button>
        <Button variant="primary" size="sm" :icon="Plus" @click="openCreate">新建人格</Button>
      </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
      <Card v-for="persona in personas" :key="persona.id" padding="lg" class="flex flex-col">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-3">
            <span class="grid h-9 w-9 place-items-center rounded-full border border-border bg-secondary text-[13px] font-bold">
              {{ persona.name.slice(0, 1) }}
            </span>
            <div>
              <p class="text-[14px] font-semibold">{{ persona.name }}</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">{{ persona.description || '未填写描述' }}</p>
            </div>
          </div>
          <Chip size="sm" :variant="persona.enabled ? 'primary' : 'outline'">
            {{ persona.enabled ? '启用中' : '已停用' }}
          </Chip>
        </div>
        <p class="mt-4 line-clamp-3 text-[12px] leading-relaxed text-muted-foreground">{{ persona.prompt }}</p>
        <div class="mt-3 flex flex-wrap gap-1.5">
          <Chip v-if="persona.style?.tone" size="sm" variant="secondary">语气 · {{ persona.style.tone }}</Chip>
          <Chip size="sm" variant="secondary">{{ scopeLabel(persona.scope) }}</Chip>
          <Chip v-if="persona.style?.max_chars" size="sm" variant="secondary">≤ {{ persona.style.max_chars }} 字</Chip>
        </div>
        <div class="mt-4 flex items-center justify-between border-t border-border pt-3.5">
          <span class="mono text-[10px] text-muted-foreground">UPDATED {{ formatDateTime(persona.updated_at) }}</span>
          <div class="flex items-center gap-1">
            <Switch
              :model-value="persona.enabled"
              size="sm"
              @update:model-value="(v: boolean) => toggle(persona, v)"
            />
            <Tooltip content="编辑" placement="top">
              <Button variant="ghost" size="sm" :icon="Pencil" @click="openEdit(persona)" />
            </Tooltip>
            <Tooltip content="删除" placement="top">
              <Button variant="ghost" size="sm" :icon="Trash2" danger @click="remove(persona)" />
            </Tooltip>
          </div>
        </div>
      </Card>
      <Card v-if="!personas.length" padding="lg" class="lg:col-span-2 2xl:col-span-3">
        <Empty title="还没有人格" description="创建第一个人格，为它写一段系统提示。" :icon="UserRound">
          <template #extra>
            <Button variant="primary" size="sm" :icon="Plus" @click="openCreate">新建人格</Button>
          </template>
        </Empty>
      </Card>
    </div>

    <Alert
      type="info"
      title="BETA 边界"
      description="人格编辑会立即写入 SQLite；上下文拼装、风格评分与多群绑定将在后续版本接入。"
    />

    <Drawer
      v-model:open="drawerOpen"
      :title="editingId ? '编辑人格' : '新建人格'"
      description="提示词会作为系统消息拼进上下文（规划能力）。"
      size="lg"
      :show-confirm="false"
    >
      <div class="space-y-5">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="eyebrow mb-2 block">人格名称</label>
            <Input v-model="form.name" placeholder="例如：风箱管家" />
          </div>
          <div>
            <label class="eyebrow mb-2 block">作用范围</label>
            <Select v-model="form.scope" :options="scopeOptions" />
          </div>
        </div>
        <div>
          <label class="eyebrow mb-2 block">一句话描述</label>
          <Input v-model="form.description" placeholder="简短说明人格定位" />
        </div>
        <div>
          <label class="eyebrow mb-2 block">系统提示词</label>
          <Textarea v-model="form.prompt" :rows="7" :auto-size="{ minRows: 6, maxRows: 12 }" placeholder="你是风箱，一个运行在本地的 QQ 群聊助手……" />
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="eyebrow mb-2 block">语气</label>
            <Input v-model="form.tone" placeholder="冷静" />
          </div>
          <div>
            <label class="eyebrow mb-2 block">回复上限（字）</label>
            <Input v-model="form.maxChars" type="number" placeholder="180" />
          </div>
          <div>
            <label class="eyebrow mb-2 block">打字速度（字/秒）</label>
            <Input v-model="form.speed" type="number" placeholder="28" />
          </div>
        </div>
        <div class="flex items-center justify-between rounded-[var(--radius)] border border-border p-3.5">
          <div>
            <p class="text-[12.5px] font-medium">创建后立即启用</p>
            <p class="mt-0.5 text-[11px] text-muted-foreground">禁用的人格不会参与默认路由。</p>
          </div>
          <Switch v-model="form.enabled" />
        </div>
      </div>
      <template #footer>
        <Button variant="secondary" @click="drawerOpen = false">取消</Button>
        <Button variant="primary" :loading="saving" @click="save">保存人格</Button>
      </template>
    </Drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Alert, Button, Card, Chip, Drawer, Empty, Input, Select, Switch, Textarea, Tooltip } from 'fuxsto-design'
import { Dialog } from 'fuxsto-design/dialog'
import { Pencil, Plus, RefreshCw, Trash2, UserRound } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { useAppStore } from '../stores/app'
import { api } from '../api'
import type { Persona } from '../types'
import { formatDateTime, scopeLabel } from '../utils'

const store = useAppStore()
const personas = ref<Persona[]>([])
const drawerOpen = ref(false)
const saving = ref(false)
const editingId = ref('')
const form = reactive({ name: '', description: '', prompt: '', scope: 'global', tone: '冷静', maxChars: '180', speed: '28', enabled: true })
const scopeOptions = [
  { label: '全局', value: 'global' },
  { label: '群聊', value: 'group' },
  { label: '用户', value: 'user' },
]

async function load(): Promise<void> {
  try {
    personas.value = (await api.personas()) as Persona[]
  } catch (e) {
    store.toast('人格加载失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

function openCreate(): void {
  editingId.value = ''
  Object.assign(form, { name: '', description: '', prompt: '', scope: 'global', tone: '冷静', maxChars: '180', speed: '28', enabled: true })
  drawerOpen.value = true
}

function openEdit(persona: Persona): void {
  editingId.value = persona.id
  Object.assign(form, {
    name: persona.name, description: persona.description, prompt: persona.prompt, scope: persona.scope,
    tone: persona.style?.tone || '冷静', maxChars: String(persona.style?.max_chars || 180),
    speed: String(persona.style?.typing_speed || 28), enabled: persona.enabled,
  })
  drawerOpen.value = true
}

async function save(): Promise<void> {
  if (!form.name.trim()) {
    store.toast('请填写人格名称', 'warning')
    return
  }
  saving.value = true
  try {
    const body = {
      name: form.name.trim(), description: form.description.trim(), prompt: form.prompt,
      scope: form.scope, enabled: form.enabled,
      style: { tone: form.tone, max_chars: Number(form.maxChars) || 180, typing_speed: Number(form.speed) || 28 },
    }
    if (editingId.value) await api.updatePersona(editingId.value, body)
    else await api.createPersona(body)
    store.toast(editingId.value ? '人格已更新' : '人格已创建', 'success', form.name)
    drawerOpen.value = false
    await load()
  } catch (e) {
    store.toast('保存失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    saving.value = false
  }
}

async function toggle(persona: Persona, enabled: boolean): Promise<void> {
  try {
    await api.updatePersona(persona.id, { enabled })
    persona.enabled = enabled
    store.toast(enabled ? '人格已启用' : '人格已停用', 'success', persona.name)
  } catch (e) {
    store.toast('更新失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

function remove(persona: Persona): void {
  Dialog.confirm({
    title: '删除人格',
    description: `将删除「${persona.name}」。已绑定该人格的会话需要重新选择。`,
    type: 'warning',
    danger: true,
    confirmText: '删除',
    onConfirm: async () => {
      try {
        await api.deletePersona(persona.id)
        store.toast('人格已删除', 'warning', persona.name)
        await load()
      } catch (e) {
        store.toast('删除失败', 'error', e instanceof Error ? e.message : String(e))
      }
    },
  })
}

onMounted(load)
</script>
