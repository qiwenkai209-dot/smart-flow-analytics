import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './views/Dashboard.vue'
import ZoneDetail from './views/ZoneDetail.vue'
import CameraConfig from './views/CameraConfig.vue'
import './style.css'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/',        component: Dashboard,    meta: { title: '实时大屏' } },
    { path: '/zones',   component: ZoneDetail,   meta: { title: '展台分析' } },
    { path: '/cameras', component: CameraConfig, meta: { title: '摄像头配置' } },
  ],
})

router.afterEach((to) => {
  document.title = `${to.meta.title} · Smart Flow Analytics`
})

createApp(App).use(router).mount('#app')
