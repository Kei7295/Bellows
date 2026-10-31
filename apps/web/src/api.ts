const TOKEN_KEY = 'bellows.token'

export function getToken(): string {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token: string): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* ignore */
  }
}

const CORE = (import.meta.env.VITE_CORE_URL as string | undefined) || ''

function url(path: string): string {
  return CORE ? `${CORE.replace(/\/$/, '')}${path}` : path
}

export function coreWsUrl(path: string): string {
  const base = CORE || `${location.protocol}//${location.host}`
  const ws = base.replace(/^http/, 'ws')
  const token = getToken()
  return `${ws}${path}${token ? `?token=${encodeURIComponent(token)}` : ''}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const res = await fetch(url(path), { ...init, headers })
  const text = await res.text()
  let data: unknown = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const message =
      typeof data === 'object' && data && 'message' in data
        ? String((data as { message: unknown }).message)
        : `请求失败 ${res.status}`
    throw new Error(message)
  }
  return data as T
}

function json(body: unknown): RequestInit {
  return { method: 'POST', body: JSON.stringify(body) }
}

export const api = {
  health: () => request('/api/health'),
  meta: () => request('/api/meta'),
  overview: () => request('/api/overview'),
  instances: () => request('/api/instances'),
  createInstance: (body: Record<string, unknown>) => request('/api/instances', json(body)),
  updateInstance: (id: string, body: Record<string, unknown>) =>
    request(`/api/instances/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteInstance: (id: string) => request(`/api/instances/${id}`, { method: 'DELETE' }),
  connectInstance: (id: string) => request(`/api/instances/${id}/connect`, { method: 'POST' }),
  disconnectInstance: (id: string) => request(`/api/instances/${id}/disconnect`, { method: 'POST' }),
  capabilities: (id: string) => request(`/api/instances/${id}/capabilities`),
  streams: (params = '') => request(`/api/streams${params}`),
  stream: (id: string) => request(`/api/streams/${id}`),
  messages: (id: string, limit = 80) => request(`/api/streams/${id}/messages?limit=${limit}`),
  rawMessage: (sid: string, mid: string) => request(`/api/streams/${sid}/messages/raw/${mid}`),
  send: (id: string, text: string, useAi = false) =>
    request(`/api/streams/${id}/send`, json({ text, use_ai: useAi })),
  personas: () => request('/api/personas'),
  createPersona: (body: Record<string, unknown>) => request('/api/personas', json(body)),
  updatePersona: (id: string, body: Record<string, unknown>) =>
    request(`/api/personas/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deletePersona: (id: string) => request(`/api/personas/${id}`, { method: 'DELETE' }),
  providers: () => request('/api/providers'),
  createProvider: (body: Record<string, unknown>) => request('/api/providers', json(body)),
  updateProvider: (id: string, body: Record<string, unknown>) =>
    request(`/api/providers/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteProvider: (id: string) => request(`/api/providers/${id}`, { method: 'DELETE' }),
  testProvider: (id: string) => request(`/api/providers/${id}/test`, { method: 'POST' }),
  memories: (query = '') => request(`/api/memories${query}`),
  deleteMemory: (id: string) => request(`/api/memories/${id}`, { method: 'DELETE' }),
  plugins: () => request('/api/plugins'),
  togglePlugin: (id: string, enabled: boolean) =>
    request(`/api/plugins/${id}/toggle`, json({ enabled })),
  reloadPlugin: (id: string) => request(`/api/plugins/${id}/reload`, { method: 'POST' }),
  pluginMarket: () => request('/api/plugins/market'),
  logs: (query = '') => request(`/api/logs${query}`),
  audit: () => request('/api/audit'),
  settings: () => request('/api/settings'),
  saveSettings: (body: Record<string, unknown>) =>
    request('/api/settings', { method: 'PUT', body: JSON.stringify(body) }),
}
