export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const diff = Math.max(0, (Date.now() - d.getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
}

export function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

export function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 10_000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

export const statusMeta: Record<string, { label: string; tone: string; icon: string }> = {
  online: { label: '在线', tone: 'text-success', icon: 'online' },
  connecting: { label: '连接中', tone: 'text-warning', icon: 'connecting' },
  degraded: { label: '降级', tone: 'text-warning', icon: 'degraded' },
  offline: { label: '离线', tone: 'text-muted-foreground', icon: 'offline' },
  error: { label: '异常', tone: 'text-destructive', icon: 'error' },
  unconfigured: { label: '未配置', tone: 'text-muted-foreground', icon: 'offline' },
}

export function modeLabel(mode: string): string {
  return (
    {
      demo: '演示管线',
      reverse_ws: '反向 WS',
      forward_ws: '正向 WS',
      http: 'HTTP',
    }[mode] || mode
  )
}

export function scopeLabel(scope: string): string {
  return ({ global: '全局', group: '群聊', user: '用户' }[scope] || scope)
}

export function sceneLabel(scene: string): string {
  return ({ group: '群聊', private: '私聊', channel: '频道' }[scene] || scene)
}

export function levelLabel(level: string): string {
  return ({ info: 'INFO', warn: 'WARN', error: 'ERROR', debug: 'DEBUG' }[level] || level.toUpperCase())
}

export function todayDate(): string {
  const d = new Date()
  return d.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
}
