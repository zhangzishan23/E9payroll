<template>
  <div class="min-h-screen flex items-center justify-center" style="background: linear-gradient(135deg, #0c4a6e 0%, #0369a1 30%, #0284c7 60%, #38bdf8 100%);">
    <div class="apple-card p-10 w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-blue-700">工资计算管家</h1>
        <p class="text-gray-400 mt-2 text-sm">请登录您的账号</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="w-full" :loading="loading" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
      <div class="text-center text-xs text-gray-400 mt-4">
        测试账号：admin / admin123 或 hr001 / 123456
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const formRef = ref(null)

const form = reactive({
  username: 'admin',
  password: 'admin123'
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>