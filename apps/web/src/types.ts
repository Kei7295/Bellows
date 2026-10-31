export interface Instance {
  id: string
  name: string
  platform: string
  self_id: string
  mode: string
  endpoint: string
  access_token: string
  status: 'unconfigured' | 'connecting' | 'online' | 'degraded' | 'offline' | 'error'
  latency_ms: number | null
  config: Record<string, unknown>
  created_at: string
  updated_at: string
  account?: { uin?: string } | null
}

export interface Stream {
  id: string
  instance_id: string
  scene: 'private' | 'group' | 'channel'
  peer_id: string
  group_id: string | null
  title: string
  subtitle: string | null
  last_message_at: string | null
  unread: number
  last_text?: string | null
  last_sender?: string | null
}

export interface Segment {
  type: string
  text?: string
  data?: Record<string, unknown>
}

export interface Message {
  id: string
  stream_id: string
  instance_id: string
  message_id: string | null
  direction: 'in' | 'out'
  sender_id: string
  sender_name: string
  segments: Segment[]
  text: string
  is_bot: boolean
  created_at: string
}

export interface Overview {
  version: string
  build: string
  uptime: number
  data_dir: string
  stats: {
    online_instances: number
    total_instances: number
    today_messages: number
    today_replies: number
    today_tokens: number
    streams: number
    memories: number
  }
  series: { date: string; messages: number; replies: number; tokens: number }[]
  instances: Instance[]
  recent: (Message & { stream_title?: string })[]
  alerts: { level: 'error' | 'warning' | 'info'; title: string; detail: string; instance_id?: string }[]
}

export interface Persona {
  id: string
  name: string
  description: string
  prompt: string
  style: { tone?: string; max_chars?: number; typing_speed?: number }
  scope: string
  enabled: boolean
  updated_at: string
}

export interface Provider {
  id: string
  name: string
  type: string
  base_url: string
  model: string
  params: Record<string, unknown>
  secret_ref: string
  enabled: boolean
  has_key: boolean
  last_test: string | null
  latency_ms: number | null
  updated_at: string
}

export interface Memory {
  id: string
  scope: string
  owner_id: string | null
  owner_name: string | null
  text: string
  importance: number
  created_at: string
}

export interface Plugin {
  id: string
  name: string
  version: string
  author: string
  description: string
  trust: string
  status: 'active' | 'inactive' | 'error'
  permissions: string[]
  installed_at: string
}

export interface LogEntry {
  id: number
  level: 'info' | 'warn' | 'error' | 'debug'
  source: string
  message: string
  detail: unknown
  created_at: string
}

export interface BellowsEvent {
  type: string
  ts: number
  data: Record<string, unknown>
}
