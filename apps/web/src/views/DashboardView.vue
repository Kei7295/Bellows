<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="WORKBENCH / 总览"
      title="今天的炉火"
      description="协议进风，人格出火。这里汇总实例连接、消息吞吐与运行异常；BETA 数据来自本地 SQLite 与演示管线。"
    >
      <template #actions>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="refresh">刷新</Button>
        <Button variant="primary" size="sm" :icon="MessagesSquare" @click="router.push('/console')">进入控制台</Button>
      </template>
    </PageHeader>

    <div v-if="overview?.alerts.length" class="space-y-2">
      <Alert
        v-for="alert in overview.alerts"
        :key="alert.title"
        :type="alert.level === 'error' ? 'error' : 'warning'"
        :title="alert.title"
        :description="alert.detail"
      >
        <template #extra>
          <Button variant="outline" size="sm" @click="router.push('/instances')">去处理</Button>
        </template>
      </Alert>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard
        label="在线实例"
        :value="stats.online_instances"
        :suffix="`/ ${stats.total_instances}`"
        :hint="stats.online_instances ? '事件流正常' : '等待协议端连接'"
        :icon="Server"
        :tone="stats.online_instances ? 'success' : 'warning'"
        :spark="instanceSpark"
      />
      <StatCard
        label="今日消息"
        :value="stats.today_messages.toLocaleString('zh-CN')"
        suffix="条"
        hint="含入站与人工发送"
        :icon="MessagesSquare"
        :spark="messageSpark"
      />
      <StatCard
        label="今日回复"
        :value="stats.today_replies.toLocaleString('zh-CN')"
        suffix="条"
        :hint="`回复率 ${replyRate}%`"
        :icon="Reply"
        tone="success"
        :spark="replySpark"
      />
      <StatCard
        label="Token 消耗"
        :value="compact(stats.today_tokens)"
        suffix="tokens"
        hint="BETA 为估算值"
        :icon="Zap"
        :spark="tokenSpark"
      />
    </div>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-12">
      <Card padding="lg" class="xl:col-span-8">
        <template #header>
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="eyebrow">ACTIVITY / 近 14 天</p>
              <p class="mt-1.5 text-[16px] font-semibold tracking-[-0.01em]">消息与回复吞吐</p>
            </div>
            <div class="flex items-center gap-4 text-[11px] text-muted-foreground">
              <span class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-[1px] bg-foreground/80" />消息</span>
              <span class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-[1px] bg-foreground/20" />回复</span>
            </div>
          </div>
        </template>
        <div class="mt-2 flex h-[220px] items-end gap-2 border-b border-[var(--app-grid-line)] pb-0">
          <div
            v-for="day in series"
            :key="day.date"
            class="group flex h-full flex-1 items-end justify-center gap-[3px]"
            :title="`${day.date} 消息 ${day.messages} / 回复 ${day.replies}`"
          >
            <span class="chart-bar w-[38%]" :style="{ height: `${barHeight(day.messages)}%` }" />
            <span class="chart-bar chart-bar-muted w-[38%]" :style="{ height: `${barHeight(day.replies)}%` }" />
          </div>
        </div>
        <div class="mt-2 flex gap-2">
          <span
            v-for="(day, i) in series"
            :key="day.date"
            class="mono flex-1 text-center text-[10px] text-muted-foreground"
          >
            {{ i % 2 === 0 ? day.date.slice(5) : '' }}
          </span>
        </div>
        <div class="mt-5 grid grid-cols-3 divide-x divide-border border-t border-border pt-4">
          <div class="pr-4">
            <p class="eyebrow">TOTAL 14D</p>
            <p class="mt-2 text-[18px] font-bold tabular-nums">{{ totalMessages.toLocaleString('zh-CN') }}</p>
            <p class="mt-1 text-[11px] text-muted-foreground">全部入库消息</p>
          </div>
          <div class="px-4">
            <p class="eyebrow">AVG / DAY</p>
            <p class="mt-2 text-[18px] font-bold tabular-nums">{{ avgMessages }}</p>
            <p class="mt-1 text-[11px] text-muted-foreground">日均消息量</p>
          </div>
          <div class="pl-4">
            <p class="eyebrow">STREAMS</p>
            <p class="mt-2 text-[18px] font-bold tabular-nums">{{ stats.streams }}</p>
            <p class="mt-1 text-[11px] text-muted-foreground">活跃会话数</p>
          </div>
        </div>
      </Card>

      <Card padding="lg" class="xl:col-span-4">
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="eyebrow">FEED / 实时</p>
              <p class="mt-1.5 text-[16px] font-semibold tracking-[-0.01em]">事件流</p>
            </div>
            <span class="status-capsule">
              <span class="h-1.5 w-1.5 rounded-full" :class="store.socketState === 'live' ? 'bg-success live-dot' : 'bg-muted-foreground'" />
              {{ store.socketState === 'live' ? 'LIVE' : 'IDLE' }}
            </span>
          </div>
        </template>
        <div class="space-y-1">
          <button
            v-for="item in feed"
            :key="item.id"
            class="flex w-full items-start gap-3 rounded-[calc(var(--radius)-2px)] px-2 py-2.5 text-left transition-colors hover:bg-accent"
            @click="router.push(item.to)"
          >
            <span class="mt-1 grid h-6 w-6 shrink-0 place-items-center rounded-[4px] border border-border bg-background">
              <component :is="item.icon" :size="12" :class="item.tone" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate text-[12.5px] font-medium">{{ item.title }}</span>
              <span class="mt-0.5 block truncate text-[11px] text-muted-foreground">{{ item.detail }}</span>
            </span>
            <span class="mono mt-0.5 shrink-0 text-[10px] text-muted-foreground">{{ item.time }}</span>
          </button>
          <div v-if="!feed.length" class="py-10 text-center text-[12px] text-muted-foreground">
            等待消息事件，演示管线每 11–18 秒产生一条。
          </div>
        </div>
      </Card>
    </div>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-12">
      <Card padding="none" class="xl:col-span-8">
        <div class="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <p class="eyebrow">RUNTIME / 实例</p>
            <p class="mt-1 text-[15px] font-semibold">连接状态</p>
          </div>
          <Button variant="ghost" size="sm" :icon="ArrowUpRight" @click="router.push('/instances')">管理实例</Button>
        </div>
        <Table :columns="instanceColumns" :data="store.instances" row-key="id" size="sm" :bordered="false" hover>
          <template #cell-name="{ row }">
            <div class="flex items-center gap-2.5">
              <span class="grid h-7 w-7 place-items-center rounded-[4px] border border-border bg-secondary text-muted-foreground">
                <Server :size="13" />
              </span>
              <div class="min-w-0">
                <p class="truncate text-[12.5px] font-medium">{{ row.name }}</p>
                <p class="mono text-[10px] text-muted-foreground">{{ row.self_id || 'NO UIN' }}</p>
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
            <span class="mono block max-w-[220px] truncate text-[11px] text-muted-foreground">{{ row.endpoint || '未设置' }}</span>
          </template>
          <template #cell-latency="{ row }">
            <span class="mono text-[11px]">{{ row.latency_ms ? `${row.latency_ms} ms` : '—' }}</span>
          </template>
          <template #cell-action="{ row }">
            <Button v-if="row.status !== 'online'" variant="ghost" size="sm" :icon="Play" @click.stop="connect(row.id)">连接</Button>
            <Button v-else variant="ghost" size="sm" :icon="Square" @click.stop="disconnect(row.id)">断开</Button>
          </template>
        </Table>
      </Card>

      <Card padding="lg" class="xl:col-span-4">
        <template #header>
          <div>
            <p class="eyebrow">CHECKLIST / 接入</p>
            <p class="mt-1.5 text-[16px] font-semibold tracking-[-0.01em]">下一步建议</p>
          </div>
        </template>
        <div class="space-y-3">
          <div v-for="item in checklist" :key="item.title" class="flex items-start gap-3">
            <CheckCircle2 v-if="item.done" :size="16" class="mt-0.5 shrink-0 text-success" />
            <Circle v-else :size="16" class="mt-0.5 shrink-0 text-muted-foreground" />
            <div class="min-w-0">
              <p class="text-[12.5px] font-medium">{{ item.title }}</p>
              <p class="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">{{ item.detail }}</p>
            </div>
          </div>
        </div>
        <div class="mt-5 grid grid-cols-2 gap-2">
          <Button variant="outline" size="sm" :icon="UserRound" @click="router.push('/personas')">配置人格</Button>
          <Button variant="outline" size="sm" :icon="Cpu" @click="router.push('/models')">配置模型</Button>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Alert, Button, Card, Chip, Table } from 'fuxsto-design'
import {
  Activity, ArrowUpRight, CheckCircle2, Circle, Cpu, Info, MessagesSquare, Play, RefreshCw, Reply, Server,
  Square, UserRound, Wifi, Zap,
} from 'lucide-vue-next'
import { api } from '../api'
import PageHeader from '../components/PageHeader.vue'
import StatCard from '../components/StatCard.vue'
import StatusDot from '../components/StatusDot.vue'
import { useAppStore } from '../stores/app'
import { compact, formatTime, modeLabel } from '../utils'

const store = useAppStore()
const router = useRouter()
const overview = computed(() => store.overview)
const stats = computed(() => overview.value?.stats ?? {
  online_instances: 0, total_instances: 0, today_messages: 0, today_replies: 0,
  today_tokens: 0, streams: 0, memories: 0,
})
const series = computed(() => {
  const data = overview.value?.series || []
  return data.length ? data : Array.from({ length: 14 }, (_, i) => ({ date: `0000-00-${String(i + 1).padStart(2, '0')}`, messages: 0, replies: 0, tokens: 0 }))
})
const maxValue = computed(() => Math.max(...series.value.map((d) => d.messages), 1))
const totalMessages = computed(() => series.value.reduce((sum, d) => sum + d.messages, 0))
const avgMessages = computed(() => Math.round(totalMessages.value / Math.max(series.value.length, 1)).toLocaleString('zh-CN'))
const replyRate = computed(() => {
  const m = stats.value.today_messages || 0
  return m ? Math.round((stats.value.today_replies / m) * 100) : 0
})
const messageSpark = computed(() => series.value.slice(-8).map((d) => d.messages))
const replySpark = computed(() => series.value.slice(-8).map((d) => d.replies))
const tokenSpark = computed(() => series.value.slice(-8).map((d) => d.tokens))
const instanceSpark = computed(() => series.value.slice(-8).map(() => stats.value.online_instances * 10))

const instanceColumns = [
  { key: 'name', title: '实例' },
  { key: 'status', title: '状态' },
  { key: 'mode', title: '模式' },
  { key: 'endpoint', title: '地址' },
  { key: 'latency', title: '延迟', width: 90 },
  { key: 'action', title: '', width: 90, align: 'right' as const },
]

const feed = computed(() => {
  const list = store.events.slice(0, 8).map((event) => {
    if (event.type === 'message.created') {
      const data = event.data as { sender_name?: string; text?: string }
      return {
        id: `ev-${event.ts}-${Math.random()}`,
        icon: MessagesSquare,
        tone: 'text-foreground',
        title: `${data.sender_name || '消息'}：${(data.text || '').slice(0, 34)}`,
        detail: '消息事件 · 已入库并推送',
        time: formatTime(new Date(event.ts).toISOString()),
        to: '/console',
      }
    }
    if (event.type === 'instance.status') {
      return {
        id: `ev-${event.ts}-i`,
        icon: Wifi,
        tone: event.data.status === 'online' ? 'text-success' : 'text-warning',
        title: `实例状态更新：${event.data.status}`,
        detail: String(event.data.id || ''),
        time: formatTime(new Date(event.ts).toISOString()),
        to: '/instances',
      }
    }
    if (event.type === 'log.appended') {
      return {
        id: `ev-${event.ts}-l`,
        icon: Info,
        tone: 'text-muted-foreground',
        title: String(event.data.message || '日志'),
        detail: `${event.data.level || 'info'} · ${event.data.source || 'core'}`,
        time: formatTime(new Date(event.ts).toISOString()),
        to: '/logs',
      }
    }
    return {
      id: `ev-${event.ts}-x`,
      icon: Activity,
      tone: 'text-muted-foreground',
      title: event.type,
      detail: '内核事件',
      time: formatTime(new Date(event.ts).toISOString()),
      to: '/logs',
    }
  })
  return list.filter((x) => !x.id.includes('undefined'))
})

const checklist = computed(() => [
  {
    done: stats.value.total_instances > 0,
    title: '创建至少一个实例',
    detail: '实例 = 一个协议端连接 + 一个 QQ 账号 + 一套触发配置。',
  },
  {
    done: stats.value.online_instances > 0,
    title: '完成协议端握手',
    detail: 'NapCat / SnowLuma 开启反向 WS，或使用演示管线验证流程。',
  },
  {
    done: false,
    title: '配置真实模型 Provider',
    detail: 'BETA 只提供模拟探测，真实 LLM 请求将在后续版本接入。',
  },
])

function barHeight(value: number): number {
  return Math.max(4, Math.round((value / maxValue.value) * 100))
}

async function refresh(): Promise<void> {
  await store.refreshOverview()
  store.toast('总览已刷新', 'success')
}

async function connect(id: string): Promise<void> {
  try {
    const out = (await api.connectInstance(id)) as { message?: string; status?: string }
    store.toast(out.message || '连接请求已发送', out.status === 'error' ? 'warning' : 'success')
    await store.refreshOverview()
  } catch (e) {
    store.toast('连接失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

async function disconnect(id: string): Promise<void> {
  try {
    await api.disconnectInstance(id)
    store.toast('实例已断开', 'warning')
    await store.refreshOverview()
  } catch (e) {
    store.toast('断开失败', 'error', e instanceof Error ? e.message : String(e))
  }
}
</script>
