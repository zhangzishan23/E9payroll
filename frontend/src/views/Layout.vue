<template>
  <div class="min-h-screen flex">
    <el-menu
      :default-active="activeMenu"
      class="w-56 min-h-screen apple-header"
      background-color="transparent"
      router
      @select="handleSelect"
    >
      <div class="px-5 py-5 text-center">
        <h2 class="text-lg font-bold text-blue-700">E9 Payroll</h2>
        <p class="text-xs text-gray-400 mt-1">{{ authStore.user?.display_name }}</p>
      </div>

      <el-menu-item index="/employees">
        <el-icon><User /></el-icon>
        <span>档案管理</span>
      </el-menu-item>
      <el-menu-item index="/attendance">
        <el-icon><Calendar /></el-icon>
        <span>考勤管理</span>
      </el-menu-item>
      <el-menu-item index="/performance">
        <el-icon><TrendCharts /></el-icon>
        <span>绩效管理</span>
      </el-menu-item>
      <el-menu-item index="/salary">
        <el-icon><Money /></el-icon>
        <span>薪资核算</span>
      </el-menu-item>
      <el-menu-item index="/insurance">
        <el-icon><CreditCard /></el-icon>
        <span>社保公积金</span>
      </el-menu-item>
      <el-menu-item index="/approval">
        <el-icon><Checked /></el-icon>
        <span>审批流程</span>
      </el-menu-item>
      <el-menu-item index="/reports">
        <el-icon><Document /></el-icon>
        <span>报表导出</span>
      </el-menu-item>

      <el-sub-menu index="system" v-if="authStore.user?.is_admin">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </template>
        <el-menu-item index="/system/users">用户管理</el-menu-item>
        <el-menu-item index="/system/roles">角色管理</el-menu-item>
        <el-menu-item index="/system/dict">数据字典</el-menu-item>
        <el-menu-item index="/system/logs">操作日志</el-menu-item>
      </el-sub-menu>

      <div class="absolute bottom-4 left-0 w-full px-4">
        <div class="space-y-3">
          <el-button class="w-full" size="default" @click="router.push('/profile')">
            <el-icon><User /></el-icon>
            个人中心
          </el-button>
          <el-button class="w-full" size="default" type="danger" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出登录
          </el-button>
        </div>
      </div>
    </el-menu>

    <div class="flex-1 p-6 overflow-auto">
      <router-view />
    </div>

    <AIAssistant />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Calendar, Money, Checked, Document, Setting, TrendCharts, SwitchButton, CreditCard } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import AIAssistant from './AIAssistant.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/system')) return '/system/users'
  return path
})

function handleSelect(index) {
  if (index === '/system') return
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>