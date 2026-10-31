import { createRouter, createWebHashHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('./views/DashboardView.vue'), meta: { title: '总览' } },
    { path: '/instances', name: 'instances', component: () => import('./views/InstancesView.vue'), meta: { title: '实例' } },
    { path: '/console', name: 'console', component: () => import('./views/ConsoleView.vue'), meta: { title: '消息控制台' } },
    { path: '/personas', name: 'personas', component: () => import('./views/PersonasView.vue'), meta: { title: '人格' } },
    { path: '/memory', name: 'memory', component: () => import('./views/MemoryView.vue'), meta: { title: '记忆' } },
    { path: '/models', name: 'models', component: () => import('./views/ModelsView.vue'), meta: { title: '模型' } },
    { path: '/plugins', name: 'plugins', component: () => import('./views/PluginsView.vue'), meta: { title: '插件' } },
    { path: '/logs', name: 'logs', component: () => import('./views/LogsView.vue'), meta: { title: '日志与审计' } },
    { path: '/settings', name: 'settings', component: () => import('./views/SettingsView.vue'), meta: { title: '设置' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · Bellows 风箱` : 'Bellows · 风箱'
})
