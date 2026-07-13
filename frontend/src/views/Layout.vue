<template>
  <div class="min-h-screen flex relative" @mouseleave="handleMouseLeave">
    <div 
      class="fixed left-0 top-0 h-full w-2 z-50"
      @mouseenter="handleEdgeEnter"
    ></div>

    <div 
      class="fixed left-0 top-0 h-full z-40 transition-all duration-300 ease-in-out overflow-hidden"
      :class="sidebarVisible ? 'w-56' : 'w-0'"
      @mouseenter="handleSidebarEnter"
      @mouseleave="handleSidebarLeave"
    >
      <el-menu
        :default-active="activeMenu"
        :default-openeds="defaultOpeneds"
        class="w-56 h-screen overflow-y-auto apple-header flex-shrink-0 relative"
        background-color="transparent"
        router
        @select="handleSelect"
      >
        <div class="absolute top-3 right-3 z-50">
          <el-button 
            :type="sidebarPinned ? 'primary' : 'default'"
            size="small" 
            circle
            @click.stop="togglePin"
            :title="sidebarPinned ? '取消固定' : '固定侧边栏'"
          >
            <el-icon><Paperclip /></el-icon>
          </el-button>
        </div>

        <div class="px-5 py-5 text-center pr-10">
          <h2 class="text-lg font-bold text-blue-700">工资计算管家</h2>
          <p class="text-xs text-gray-400 mt-1">{{ authStore.user?.display_name }}</p>
        </div>

        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>工作台</span>
        </el-menu-item>
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
          <span>绩效评分</span>
        </el-menu-item>
        <el-menu-item index="/insurance">
          <el-icon><CreditCard /></el-icon>
          <span>社保公积金</span>
        </el-menu-item>
        <el-menu-item index="/insurance-template">
          <el-icon><Setting /></el-icon>
          <span>导入模板</span>
        </el-menu-item>
        <el-menu-item index="/salary">
          <el-icon><Money /></el-icon>
          <span>薪资核算</span>
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
          <el-menu-item index="/system/dict?category=department">部门管理</el-menu-item>
          <el-menu-item index="/system/logs">操作日志</el-menu-item>
          <el-menu-item index="/system/backup">数据备份</el-menu-item>
        </el-sub-menu>

        <div class="px-4 pt-6 pb-4 space-y-2">
          <div 
            class="w-full px-4 py-2 text-center cursor-pointer border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
            @click="router.push('/profile')"
          >
            个人中心
          </div>
          <div 
            class="w-full px-4 py-2 text-center cursor-pointer border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
            @click="handleLogout"
          >
            退出登录
          </div>
        </div>
      </el-menu>
    </div>

    <div 
      class="flex-1 p-6 overflow-auto transition-all duration-300 ease-in-out"
      :class="(sidebarVisible && !sidebarPinned) ? 'ml-56' : (sidebarPinned ? 'ml-56' : 'ml-4')"
    >
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Calendar, Money, Checked, Document, Setting, TrendCharts, SwitchButton, CreditCard, HomeFilled, Paperclip } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const STORAGE_KEY = 'e9salary_sidebar_pinned'

const sidebarVisible = ref(false)
const sidebarPinned = ref(false)
let hideTimer = null

onMounted(() => {
  const savedPinned = localStorage.getItem(STORAGE_KEY)
  if (savedPinned === 'true') {
    sidebarPinned.value = true
    sidebarVisible.value = true
  }
})

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/system')) return '/system/users'
  return path
})

const defaultOpeneds = ['system']

function handleEdgeEnter() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
  if (!sidebarPinned.value) {
    sidebarVisible.value = true
  }
}

function handleSidebarEnter() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}

function handleSidebarLeave() {
  if (!sidebarPinned.value) {
    hideTimer = setTimeout(() => {
      sidebarVisible.value = false
    }, 300)
  }
}

function handleMouseLeave() {
  if (!sidebarPinned.value) {
    hideTimer = setTimeout(() => {
      sidebarVisible.value = false
    }, 300)
  }
}

function togglePin() {
  sidebarPinned.value = !sidebarPinned.value
  localStorage.setItem(STORAGE_KEY, String(sidebarPinned.value))
  if (sidebarPinned.value) {
    sidebarVisible.value = true
  }
}

function handleSelect(index) {
  if (index === '/system') return
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

