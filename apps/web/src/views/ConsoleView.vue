<template>
  <div class="flex h-full flex-col">
    <div class="flex shrink-0 flex-wrap items-end justify-between gap-3 pb-4">
      <div>
        <p class="eyebrow mb-1.5">CONSOLE / 消息控制台</p>
        <h1 class="text-[24px] font-extrabold leading-none tracking-[-0.025em]">实时会话</h1>
        <p class="mt-2 text-[12px] text-muted-foreground">消息经归一化后落库，并通过事件流实时推送到这里。BETA 回复由演示引擎生成。</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="status-capsule">
          <span class="h-1.5 w-1.5 rounded-full" :class="store.socketState === 'live' ? 'bg-success live-dot' : 'bg-muted-foreground'" />
          <span class="mono text-[10px]">{{ store.socketState === 'live' ? 'EVENT STREAM LIVE' : 'EVENT STREAM IDLE' }}</span>
        </span>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="reload">刷新</Button>
      </div>
    </div>

    <div class="grid min-h-0 flex-1 grid-cols-1 gap-3 xl:grid-cols-[286px_minmax(0,1fr)_310px]">
      <!-- Streams -->
      <section class="flex min-h-0 flex-col overflow-hidden rounded-[var(--radius)] border border-border bg-background">
        <div class="border-b border-border p-3">
          <div class="flex items-center justify-between">
            <h2 class="text-[13px] font-semibold">会话</h2>
            <span class="mono text-[10px] text-muted-foreground">{{ filteredStreams.length }} STREAMS</span>
          </div>
          <label class="search-box mt-2.5">
            <Search :size="13" />
            <input v-model="store.search" type="search" placeholder="搜索会话" aria-label="搜索会话" />
          </label>
          <div class="mt-2.5">
            <Segmented v-model="scene" :options="sceneOptions" size="sm" block />
          </div>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto p-1.5">
          <button
            v-for="item in filteredStreams"
            :key="item.id"
            class="group flex w-full items-start gap-2.5 rounded-[calc(var(--radius)-2px)] border border-transparent px-2.5 py-2.5 text-left transition-colors"
            :class="selectedId === item.id ? 'border-border bg-secondary' : 'hover:bg-accent'"
            @click="selectStream(item)"
          >
            <span
              class="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-border text-[12px] font-semibold"
              :class="item.scene === 'group' ? 'bg-secondary' : 'bg-background'"
            >
              {{ item.title.slice(0, 1) }}
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex items-center justify-between gap-2">
                <span class="truncate text-[12.5px] font-medium">{{ item.title }}</span>
                <span class="mono shrink-0 text-[9.5px] text-muted-foreground">{{ formatTime(item.last_message_at) }}</span>
              </span>
              <span class="mt-0.5 flex items-center gap-1.5">
                <span class="truncate text-[11px] text-muted-foreground">{{ item.last_sender ? `${item.last_sender}：` : '' }}{{ item.last_text || '暂无消息' }}</span>
              </span>
            </span>
            <span
              v-if="item.unread"
              class="mt-0.5 grid h-4 min-w-4 shrink-0 place-items-center rounded-full bg-foreground px-1 text-[9px] font-semibold text-background"
            >
              {{ item.unread > 99 ? '99+' : item.unread }}
            </span>
          </button>
          <Empty v-if="!filteredStreams.length" size="sm" title="没有匹配的会话" description="尝试切换场景筛选或清空搜索。" />
        </div>
      </section>

      <!-- Thread -->
      <section class="flex min-h-0 flex-col overflow-hidden rounded-[var(--radius)] border border-border bg-background">
        <div class="flex shrink-0 items-center justify-between gap-3 border-b border-border px-4 py-2.5">
          <div class="flex min-w-0 items-center gap-2.5">
            <span class="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-border bg-secondary text-[12px] font-semibold">
              {{ selected?.title.slice(0, 1) || '—' }}
            </span>
            <div class="min-w-0">
              <p class="truncate text-[13px] font-semibold">{{ selected?.title || '选择会话' }}</p>
              <p class="mono mt-0.5 truncate text-[10px] text-muted-foreground">
                {{ selected ? `${sceneLabel(selected.scene)} · ${selected.peer_id} · ${instanceName(selected.instance_id)}` : 'NO STREAM' }}
              </p>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <StatusDot :status="instanceStatus(selected?.instance_id)" :size="11" show-label />
            <Chip v-if="selected && selected.unread" size="sm" variant="secondary">{{ selected.unread }} 未读</Chip>
          </div>
        </div>

        <div ref="scrollRef" class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <div v-if="messagesLoading" class="space-y-3">
            <div v-for="i in 5" :key="i" class="h-14 animate-pulse rounded-[var(--radius)] bg-muted/60" :class="i % 2 ? 'ml-16' : 'mr-16'" />
          </div>
          <Empty
            v-else-if="!selected"
            title="选择一个会话"
            description="左侧列表会随事件流更新，选择后即可查看消息并人工接管。"
            :icon="MessagesSquare"
          />
          <Empty
            v-else-if="!messages.length"
            title="这个会话还没有消息"
            description="可以在下方输入框发送第一条消息，或等待演示管线产生事件。"
            :icon="Inbox"
          />
          <div v-else class="space-y-3.5">
            <div v-for="(msg, idx) in messages" :key="msg.id">
              <div v-if="idx === 0 || dayKey(messages[idx - 1].created_at) !== dayKey(msg.created_at)" class="my-3 flex items-center gap-3">
                <span class="h-px flex-1 bg-border" />
                <span class="mono text-[10px] text-muted-foreground">{{ dayKey(msg.created_at) }}</span>
                <span class="h-px flex-1 bg-border" />
              </div>
              <div class="message-row-in flex items-start gap-2.5" :class="msg.is_bot ? 'flex-row-reverse' : ''">
                <span
                  class="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-border text-[10px] font-semibold"
                  :class="msg.is_bot ? 'bg-foreground text-background' : 'bg-secondary text-foreground'"
                >
                  {{ msg.sender_name.slice(0, 1) }}
                </span>
                <div class="min-w-0 max-w-[78%]">
                  <div class="flex items-center gap-2" :class="msg.is_bot ? 'justify-end' : ''">
                    <span class="text-[11px] font-medium">{{ msg.sender_name }}</span>
                    <span v-if="msg.is_bot" class="mono rounded-[3px] border border-border px-1 py-0.5 text-[8px] uppercase tracking-[0.08em] text-muted-foreground">BOT</span>
                    <span class="mono text-[9.5px] text-muted-foreground">{{ formatTime(msg.created_at) }}</span>
                  </div>
                  <div
                    class="mt-1 whitespace-pre-wrap break-words rounded-[var(--radius)] border px-3 py-2 text-[12.5px] leading-relaxed"
                    :class="msg.is_bot ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-secondary text-secondary-foreground'"
                  >{{ msg.text }}</div>
                </div>
              </div>
            </div>
            <div v-if="thinking" class="message-row-in flex items-start gap-2.5 flex-row-reverse">
              <span class="grid h-7 w-7 place-items-center rounded-full bg-foreground text-[10px] font-semibold text-background">风</span>
              <div class="rounded-[var(--radius)] border border-border bg-secondary px-3 py-2 text-[12px]">
                <span class="stream-sweep font-medium">正在生成演示回复</span><span class="caret">_</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="selected" class="shrink-0 border-t border-border bg-background p-3">
          <div class="rounded-[var(--radius)] border border-border focus-within:border-ring focus-within:shadow-[var(--app-focus-ring)]">
            <Textarea
              v-model="draft"
              :rows="2"
              :auto-size="{ minRows: 2, maxRows: 5 }"
              :maxlength="2000"
              resize="none"
              placeholder="以风箱身份发送，Enter 发送，Shift + Enter 换行"
              class="border-0 shadow-none"
              @keydown="onKeydown"
            />
            <div class="flex items-center justify-between gap-2 border-t border-border px-2.5 py-1.5">
              <label class="flex cursor-pointer items-center gap-2 text-[11px] text-muted-foreground">
                <Switch v-model="useAi" size="sm" />
                发送后走演示 AI 回复
              </label>
              <div class="flex items-center gap-1.5">
                <span class="mono hidden text-[10px] text-muted-foreground sm:inline">{{ draft.length }} / 2000</span>
                <Button variant="primary" size="sm" :icon="Send" :loading="sending" :disabled="!draft.trim()" @click="send">发送</Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Inspector -->
      <section class="hidden min-h-0 flex-col overflow-y-auto rounded-[var(--radius)] border border-border bg-background xl:flex">
        <div class="border-b border-border px-4 py-3">
          <p class="eyebrow">INSPECTOR / 会话</p>
          <p class="mt-1.5 text-[13px] font-semibold">{{ selected?.title || '未选择会话' }}</p>
        </div>
        <div class="space-y-4 p-4">
          <div class="space-y-2.5">
            <p class="eyebrow">触发策略</p>
            <ToggleRow label="群聊被 @ 时回复" v-model="triggers.at" />
            <ToggleRow label="私聊白名单" v-model="triggers.privateWhitelist" />
            <ToggleRow label="上下文写入记忆" v-model="triggers.memory" />
            <p class="text-[10.5px] leading-relaxed text-muted-foreground">BETA 开关仅作用于当前界面演示，不写入实例配置。</p>
          </div>

          <div class="h-px bg-border" />

          <div>
            <p class="eyebrow mb-2">绑定人格</p>
            <Select v-model="personaId" :options="personaOptions" size="sm" placeholder="选择人格" />
            <p class="mt-2 text-[10.5px] leading-relaxed text-muted-foreground">
              人格页可编辑系统提示与语气；BETA 的回复引擎暂不读取人格提示。
            </p>
          </div>

          <div class="h-px bg-border" />

          <div>
            <p class="eyebrow mb-2.5">运行参数</p>
            <div class="space-y-2 text-[11px]">
              <div class="flex items-center justify-between"><span class="text-muted-foreground">触发判定</span><span class="mono">@ / 关键词</span></div>
              <div class="flex items-center justify-between"><span class="text-muted-foreground">冷却</span><span class="mono">10 s</span></div>
              <div class="flex items-center justify-between"><span class="text-muted-foreground">上下文窗口</span><span class="mono">12 条</span></div>
              <div class="flex items-center justify-between"><span class="text-muted-foreground">回复引擎</span><span class="mono">DEMO</span></div>
              <div class="flex items-center justify-between"><span class="text-muted-foreground">消息落库</span><span class="mono">SQLite WAL</span></div>
            </div>
          </div>

          <div class="h-px bg-border" />

          <div>
            <p class="eyebrow mb-2">最近请求</p>
            <div class="rounded-[calc(var(--radius)-2px)] border border-border bg-secondary p-3">
              <div class="flex items-center justify-between text-[10.5px]">
                <span class="text-muted-foreground">TRACE</span>
                <span class="mono">{{ selected?.id || '—' }}</span>
              </div>
              <p class="mono mt-2 text-[10px] leading-relaxed text-muted-foreground">
                pipeline: normalize → gate → demo-reply<br />
                storage: messages + stats_daily<br />
                transport: /api/events
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { Button, Chip, Empty, Segmented, Select, Switch, Textarea } from 'fuxsto-design'
import { Inbox, MessagesSquare, RefreshCw, Search, Send } from 'lucide-vue-next'
import StatusDot from '../components/StatusDot.vue'
import ToggleRow from '../components/ToggleRow.vue'
import { useAppStore } from '../stores/app'
import { api } from '../api'
import type { Message, Persona, Stream } from '../types'
import { formatTime, sceneLabel } from '../utils'

const store = useAppStore()
const scene = ref<'all' | 'group' | 'private'>('all')
const selectedId = ref('')
const messages = ref<Message[]>([])
const messagesLoading = ref(false)
const draft = ref('')
const useAi = ref(false)
const sending = ref(false)
const thinking = ref(false)
const scrollRef = ref<HTMLElement | null>(null)
const personas = ref<Persona[]>([])
const personaId = ref('per_main')
const triggers = reactive({ at: true, privateWhitelist: true, memory: true })

const sceneOptions = [
  { label: '全部', value: 'all' },
  { label: '群聊', value: 'group' },
  { label: '私聊', value: 'private' },
]

const filteredStreams = computed(() => {
  let list = store.streams
  if (scene.value !== 'all') list = list.filter((s) => s.scene === scene.value)
  const q = store.search.trim().toLowerCase()
  if (q) list = list.filter((s) => [s.title, s.last_text, s.peer_id].some((v) => String(v || '').toLowerCase().includes(q)))
  return list
})
const selected = computed(() => store.streams.find((s) => s.id === selectedId.value) || null)
const personaOptions = computed(() => personas.value.map((p) => ({ label: p.name, value: p.id })))

function instanceStatus(id?: string): string {
  return store.instances.find((i) => i.id === id)?.status || 'offline'
}
function instanceName(id?: string): string {
  return store.instances.find((i) => i.id === id)?.name || '未知实例'
}
function dayKey(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}
function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void send()
  }
}

async function selectStream(stream: Stream): Promise<void> {
  if (selectedId.value === stream.id) return
  selectedId.value = stream.id
  stream.unread = 0
  messagesLoading.value = true
  messages.value = []
  try {
    messages.value = (await api.messages(stream.id, 100)) as Message[]
  } catch (e) {
    store.toast('消息加载失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    messagesLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom(): void {
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

async function send(): Promise<void> {
  const text = draft.value.trim()
  if (!text || !selected.value) return
  sending.value = true
  try {
    const res = (await api.send(selected.value.id, text, useAi.value)) as { message: Message }
    messages.value.push(res.message)
    draft.value = ''
    if (useAi.value) {
      thinking.value = true
      window.setTimeout(() => (thinking.value = false), 1600)
    }
    await nextTick()
    scrollToBottom()
  } catch (e) {
    store.toast('发送失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    sending.value = false
  }
}

async function reload(): Promise<void> {
  await store.refreshStreams()
  if (selectedId.value) {
    messages.value = (await api.messages(selectedId.value, 100)) as Message[]
    await nextTick()
    scrollToBottom()
  }
  store.toast('控制台已刷新', 'success')
}

watch(
  () => store.lastEvent,
  async (event) => {
    if (!event || event.type !== 'message.created') return
    const data = event.data as unknown as Message
    if (!data.stream_id || data.stream_id !== selectedId.value) return
    if (messages.value.some((m) => m.id === data.id)) return
    messages.value.push(data)
    if (data.is_bot) thinking.value = false
    await nextTick()
    scrollToBottom()
  },
)

watch(
  () => store.activeInstanceId,
  () => {
    selectedId.value = ''
    messages.value = []
    void store.refreshStreams()
  },
)

onMounted(async () => {
  await store.refreshStreams()
  const first = store.streams[0]
  if (first) await selectStream(first)
  try {
    personas.value = (await api.personas()) as Persona[]
    if (!personas.value.some((p) => p.id === personaId.value) && personas.value[0]) {
      personaId.value = personas.value[0].id
    }
  } catch {
    /* personas are optional for the console */
  }
})
</script>
