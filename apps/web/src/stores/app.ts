import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, coreWsUrl } from '../api'
import type { BellowsEvent, Instance, Overview, Stream } from '../types'

export type ThemeMode = 'system' | 'light' | 'dark'

export interface Toast {
  id: number
  title: string
  description?: string
  tone: 'default' | 'success' | 'warning' | 'error'
}

export const useAppStore = defineStore('app', () => {
  const theme = ref<ThemeMode>((localStorage.getItem('bellows.theme') as ThemeMode) || 'system')
  const systemDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches)
  const resolvedDark = computed(() => theme.value === 'dark' || (theme.value === 'system' && systemDark.value))

  const overview = ref<Overview | null>(null)
  const instances = ref<Instance[]>([])
  const streams = ref<Stream[]>([])
  const activeInstanceId = ref(localStorage.getItem('bellows.instance') || '')
  const loading = ref(true)
  const error = ref('')
  const events = ref<BellowsEvent[]>([])
  const lastEvent = ref<BellowsEvent | null>(null)
  const socketState = ref<'connecting' | 'live' | 'offline'>('connecting')
  const toasts = ref<Toast[]>([])
  const search = ref('')
  let ws: WebSocket | null = null
  let retry = 0
  let retryTimer: number | undefined
  let toastSeq = 0

  const activeInstance = computed(
    () => instances.value.find((i) => i.id === activeInstanceId.value) || instances.value[0] || null,
  )
  const onlineCount = computed(() => instances.value.filter((i) => i.status === 'online').length)

  function applyTheme(): void {
    const root = document.documentElement
    root.classList.toggle('dark', resolvedDark.value)
    localStorage.setItem('bellows.theme', theme.value)
  }

  function setTheme(mode: ThemeMode): void {
    theme.value = mode
    applyTheme()
  }

  function setActiveInstance(id: string): void {
    activeInstanceId.value = id
    localStorage.setItem('bellows.instance', id)
  }

  function toast(title: string, tone: Toast['tone'] = 'default', description = ''): void {
    const id = ++toastSeq
    toasts.value.push({ id, title, tone, description })
    window.setTimeout(() => {
      toasts.value = toasts.value.filter((t) => t.id !== id)
    }, 4200)
  }

  function dismissToast(id: number): void {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  async function loadCore(): Promise<void> {
    try {
      error.value = ''
      const [ov, ins, st] = await Promise.all([
        api.overview() as Promise<Overview>,
        api.instances() as Promise<Instance[]>,
        api.streams() as Promise<Stream[]>,
      ])
      overview.value = ov
      instances.value = ins
      streams.value = st
      if (!activeInstanceId.value || !ins.some((i) => i.id === activeInstanceId.value)) {
        const first = ins.find((i) => i.status === 'online') || ins[0]
        if (first) setActiveInstance(first.id)
      }
      loading.value = false
    } catch (e) {
      loading.value = false
      error.value = e instanceof Error ? e.message : String(e)
    }
  }

  async function refreshOverview(): Promise<void> {
    try {
      const [ov, ins] = await Promise.all([
        api.overview() as Promise<Overview>,
        api.instances() as Promise<Instance[]>,
      ])
      overview.value = ov
      instances.value = ins
    } catch {
      /* keep last snapshot */
    }
  }

  async function refreshStreams(): Promise<void> {
    try {
      streams.value = (await api.streams(
        activeInstanceId.value ? `?instance_id=${activeInstanceId.value}` : '',
      )) as Stream[]
    } catch {
      /* ignore */
    }
  }

  function handleEvent(event: BellowsEvent): void {
    lastEvent.value = event
    events.value = [event, ...events.value].slice(0, 160)
    if (event.type === 'instance.status') {
      const id = String(event.data.id || '')
      const status = event.data.status as Instance['status']
      const inst = instances.value.find((i) => i.id === id)
      if (inst) {
        inst.status = status
        if (typeof event.data.latency_ms === 'number') inst.latency_ms = event.data.latency_ms
        else if (status !== 'online') inst.latency_ms = null
      }
      if (status === 'offline') toast('实例已断开', 'warning', inst?.name)
      if (status === 'error') toast('实例异常', 'error', inst?.name)
      if (overview.value) {
        overview.value.stats.online_instances = instances.value.filter((i) => i.status === 'online').length
      }
    }
    if (event.type === 'message.created') {
      const data = event.data as { stream_id?: string; text?: string; sender_name?: string; created_at?: string; is_bot?: boolean }
      const stream = streams.value.find((s) => s.id === data.stream_id)
      if (stream) {
        stream.last_text = data.text || ''
        stream.last_sender = data.sender_name || ''
        stream.last_message_at = data.created_at || stream.last_message_at
        if (!data.is_bot) stream.unread = (stream.unread || 0) + 1
      }
    }
    if (event.type === 'log.appended' && event.data.level === 'error') {
      toast('运行日志出现错误', 'error', String(event.data.message || ''))
    }
    if (event.type === 'stats.tick' && overview.value) {
      if (typeof event.data.messages === 'number') overview.value.stats.today_messages = event.data.messages
      if (typeof event.data.replies === 'number') overview.value.stats.today_replies = event.data.replies
    }
  }

  function connectEvents(): void {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
    socketState.value = 'connecting'
    try {
      ws = new WebSocket(coreWsUrl('/api/events'))
    } catch {
      scheduleReconnect()
      return
    }
    ws.onopen = () => {
      socketState.value = 'live'
      retry = 0
    }
    ws.onmessage = (msg) => {
      try {
        const envelope = JSON.parse(msg.data) as BellowsEvent
        if (envelope.type !== 'ping') handleEvent(envelope)
      } catch {
        /* ignore malformed frames */
      }
    }
    ws.onclose = () => {
      socketState.value = 'offline'
      ws = null
      scheduleReconnect()
    }
    ws.onerror = () => {
      socketState.value = 'offline'
    }
  }

  function scheduleReconnect(): void {
    if (retryTimer) return
    retry = Math.min(retry + 1, 8)
    const delay = Math.min(1000 * 2 ** (retry - 1), 30000)
    retryTimer = window.setTimeout(() => {
      retryTimer = undefined
      connectEvents()
    }, delay)
  }

  function init(): void {
    applyTheme()
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    media.addEventListener('change', (e) => {
      systemDark.value = e.matches
      if (theme.value === 'system') applyTheme()
    })
    connectEvents()
    void loadCore()
    window.setInterval(() => {
      if (socketState.value !== 'live') void refreshOverview()
    }, 30000)
  }

  return {
    theme,
    resolvedDark,
    overview,
    instances,
    streams,
    activeInstanceId,
    activeInstance,
    onlineCount,
    loading,
    error,
    events,
    lastEvent,
    socketState,
    toasts,
    search,
    init,
    setTheme,
    setActiveInstance,
    toast,
    dismissToast,
    loadCore,
    refreshOverview,
    refreshStreams,
    connectEvents,
  }
})
