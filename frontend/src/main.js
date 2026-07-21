import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

function checkPermission(el, binding) {
  const authStore = useAuthStore()
  const { value } = binding
  if (authStore.isAdmin) {
    el.style.display = ''
    return
  }

  let hasPerm = false
  if (Array.isArray(value)) {
    hasPerm = value.some(p => authStore.hasPermission(p))
  } else if (typeof value === 'string') {
    hasPerm = authStore.hasPermission(value)
  }

  if (hasPerm) {
    el.style.display = ''
  } else {
    el.style.display = 'none'
  }
}

app.directive('permission', {
  mounted(el, binding) {
    checkPermission(el, binding)
  },
  updated(el, binding) {
    checkPermission(el, binding)
  }
})

app.mount('#app')