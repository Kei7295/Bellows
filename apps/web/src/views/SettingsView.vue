<template>
  <div class="space-y-5">
    <PageHeader
      eyebrow="SETTINGS / 设置"
      title="调校风箱"
      description="外观与行为设置写入本地 SQLite，重启后保留。主题立即生效；其余开关在保存后写入。"
    >
      <template #actions>
        <Button variant="outline" size="sm" :icon="RefreshCw" @click="load">重新读取</Button>
        <Button variant="primary" size="sm" :icon="Save" :loading="saving" @click="save">保存设置</Button>
      </template>
    </PageHeader>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card padding="lg">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-[14px] font-semibold">外观</h2>
            <p class="mt-1 text-[11.5px] text-muted-foreground">主题即时生效，并同步到服务端设置。</p>
          </div>
          <Palette :size="16" class="text-muted-foreground" />
        </div>
        <div class="mt-5 space-y-4">
          <div>
            <label class="eyebrow mb-2 block">主题</label>
            <Segmented v-model="theme" :options="themeOptions" size="sm" block @update:model-value="onTheme" />
          </div>
          <div>
            <label class="eyebrow mb-2 block">信息密度</label>
            <Select v-model="density" :options="densityOptions" />
          </div>
          <div class="flex items-center justify-between rounded-[var(--radius)] border border-border p-3.5">
            <div>
              <p class="text-[12.5px] font-medium">界面动效</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">关闭后仍遵循系统减少动态效果偏好。</p>
            </div>
            <Switch v-model="animations" />
          </div>
        </div>
      </Card>

      <Card padding="lg">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-[14px] font-semibold">通用</h2>
            <p class="mt-1 text-[11.5px] text-muted-foreground">桌面外壳相关选项；BETA 未打包 Tauri，仅保存偏好。</p>
          </div>
          <Settings2 :size="16" class="text-muted-foreground" />
        </div>
        <div class="mt-5 divide-y divide-border">
          <div class="flex items-center justify-between gap-4 py-3">
            <div>
              <p class="text-[12.5px] font-medium">开机自启</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">登录系统后自动拉起 Bellows。</p>
            </div>
            <Switch v-model="launchAtLogin" size="sm" />
          </div>
          <div class="flex items-center justify-between gap-4 py-3">
            <div>
              <p class="text-[12.5px] font-medium">关闭到托盘</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">点关闭按钮时保留后台连接。</p>
            </div>
            <Switch v-model="closeToTray" size="sm" />
          </div>
          <div class="flex items-center justify-between gap-4 py-3">
            <div>
              <p class="text-[12.5px] font-medium">最小化而非关闭</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">最小化到任务栏，不断开协议端。</p>
            </div>
            <Switch v-model="minimizeOnClose" size="sm" />
          </div>
        </div>
      </Card>

      <Card padding="lg">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-[14px] font-semibold">触发规则</h2>
            <p class="mt-1 text-[11.5px] text-muted-foreground">决定何时允许回复；演示管线同样遵循这些开关。</p>
          </div>
          <Zap :size="16" class="text-muted-foreground" />
        </div>
        <div class="mt-5 divide-y divide-border">
          <div class="flex items-center justify-between gap-4 py-3">
            <div>
              <p class="text-[12.5px] font-medium">群聊仅响应 @</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">未 @ 机器人时不进入回复流程。</p>
            </div>
            <Switch v-model="groupAt" size="sm" />
          </div>
          <div class="flex items-center justify-between gap-4 py-3">
            <div>
              <p class="text-[12.5px] font-medium">关键词触发</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">消息包含触发词时也允许回复。</p>
            </div>
            <Switch v-model="groupKeyword" size="sm" />
          </div>
          <div class="flex items-center justify-between gap-4 py-3">
            <div>
              <p class="text-[12.5px] font-medium">私聊白名单</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">仅白名单用户可触发私聊回复。</p>
            </div>
            <Switch v-model="privateWhitelist" size="sm" />
          </div>
          <div class="flex items-center justify-between gap-4 py-3">
            <div>
              <p class="text-[12.5px] font-medium">回复冷却（秒）</p>
              <p class="mt-0.5 text-[11px] text-muted-foreground">同一会话两次回复的最小间隔。</p>
            </div>
            <div class="w-24">
              <Input v-model="cooldown" type="number" size="sm" />
            </div>
          </div>
        </div>
      </Card>

      <Card padding="lg">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h2 class="text-[14px] font-semibold">内核信息</h2>
            <p class="mt-1 text-[11.5px] text-muted-foreground">只读。数据目录与版本由 Python core 上报。</p>
          </div>
          <Cpu :size="16" class="text-muted-foreground" />
        </div>
        <div class="mt-4 space-y-0 divide-y divide-border">
          <div class="flex items-center justify-between gap-4 py-2.5">
            <span class="eyebrow">VERSION</span>
            <span class="mono text-[11.5px]">{{ overview?.version || '—' }}</span>
          </div>
          <div class="flex items-center justify-between gap-4 py-2.5">
            <span class="eyebrow">BUILD</span>
            <span class="mono text-[11.5px]">{{ overview?.build || '—' }}</span>
          </div>
          <div class="flex items-center justify-between gap-4 py-2.5">
            <span class="eyebrow">UPTIME</span>
            <span class="mono text-[11.5px]">{{ overview ? formatUptime(overview.uptime) : '—' }}</span>
          </div>
          <div class="flex items-start justify-between gap-4 py-2.5">
            <span class="eyebrow shrink-0">DATA DIR</span>
            <span class="mono max-w-[68%] break-all text-right text-[10.5px] text-muted-foreground">{{ overview?.data_dir || '—' }}</span>
          </div>
          <div class="flex items-center justify-between gap-4 py-2.5">
            <span class="eyebrow">EVENT STREAM</span>
            <span class="mono text-[10px] uppercase" :class="store.socketState === 'live' ? 'text-success' : 'text-muted-foreground'">
              {{ store.socketState }}
            </span>
          </div>
        </div>
        <Alert
          class="mt-4"
          type="info"
          title="BETA 说明"
          description="开机自启、托盘与最小化由 Tauri 外壳实现；当前交付为浏览器加载的 SPA + Python core，选项仅持久化偏好。"
        />
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Alert, Button, Card, Input, Segmented, Select, Switch } from 'fuxsto-design'
import { Cpu, Palette, RefreshCw, Save, Settings2, Zap } from 'lucide-vue-next'
import PageHeader from '../components/PageHeader.vue'
import { useAppStore, type ThemeMode } from '../stores/app'
import { api } from '../api'
import { formatUptime } from '../utils'

const store = useAppStore()
const overview = computed(() => store.overview)
const saving = ref(false)
const theme = ref<ThemeMode>(store.theme)
const density = ref('comfortable')
const animations = ref(true)
const launchAtLogin = ref(false)
const closeToTray = ref(true)
const minimizeOnClose = ref(false)
const groupAt = ref(true)
const groupKeyword = ref(false)
const privateWhitelist = ref(true)
const cooldown = ref('10')

const themeOptions = [
  { label: '跟随系统', value: 'system' },
  { label: '亮色', value: 'light' },
  { label: '暗色', value: 'dark' },
]
const densityOptions = [
  { label: '舒适', value: 'comfortable' },
  { label: '紧凑', value: 'compact' },
]

function onTheme(value: string | number): void {
  store.setTheme(value as ThemeMode)
}

interface SettingsShape {
  appearance?: { theme?: ThemeMode; density?: string; animations?: boolean }
  general?: { launch_at_login?: boolean; close_to_tray?: boolean; minimize_on_close?: boolean }
  triggers?: { group_at?: boolean; group_keyword?: boolean; private_whitelist?: boolean; cooldown?: number }
}

async function load(): Promise<void> {
  try {
    const data = (await api.settings()) as SettingsShape
    theme.value = data.appearance?.theme || store.theme
    density.value = data.appearance?.density || 'comfortable'
    animations.value = data.appearance?.animations ?? true
    launchAtLogin.value = data.general?.launch_at_login ?? false
    closeToTray.value = data.general?.close_to_tray ?? true
    minimizeOnClose.value = data.general?.minimize_on_close ?? false
    groupAt.value = data.triggers?.group_at ?? true
    groupKeyword.value = data.triggers?.group_keyword ?? false
    privateWhitelist.value = data.triggers?.private_whitelist ?? true
    cooldown.value = String(data.triggers?.cooldown ?? 10)
  } catch (e) {
    store.toast('设置读取失败', 'error', e instanceof Error ? e.message : String(e))
  }
}

async function save(): Promise<void> {
  saving.value = true
  try {
    await api.saveSettings({
      appearance: { theme: theme.value, density: density.value, animations: animations.value },
      general: { launch_at_login: launchAtLogin.value, close_to_tray: closeToTray.value, minimize_on_close: minimizeOnClose.value },
      triggers: {
        group_at: groupAt.value, group_keyword: groupKeyword.value,
        private_whitelist: privateWhitelist.value, cooldown: Number(cooldown.value) || 10,
      },
    })
    theme.value = store.theme
    store.toast('设置已保存', 'success', '外观与触发规则已写入 SQLite')
  } catch (e) {
    store.toast('保存失败', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
