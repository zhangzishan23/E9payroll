<template>
  <div class="min-h-screen flex items-center justify-center" style="background: linear-gradient(135deg, #0c4a6e 0%, #0369a1 30%, #0284c7 60%, #38bdf8 100%);">
    <div class="apple-card p-10 w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-blue-700">工资计算管家</h1>
        <p class="text-gray-400 mt-2 text-sm">创建新账号</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0" @submit.prevent="handleRegister">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名（至少3位）" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="display_name">
          <el-input v-model="form.display_name" placeholder="显示名称（如：张三）" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码（至少6位）" size="large" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" placeholder="确认密码" size="large" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" class="w-full" :loading="loading" @click="handleRegister">
            注 册
          </el-button>
        </el-form-item>
      </el-form>
      <div class="text-center text-sm text-gray-500 mt-4">
        已有账号？
        <el-link type="primary" @click="goLogin">返回登录</el-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import api from '../api'

const router = useRouter()
const loading = ref(false)
const formRef = ref(null)

const form = reactive({
  username: '',
  display_name: '',
  password: '',
  confirm_password: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名长度不能少于3位', trigger: 'blur' }
  ],
  display_name: [
    { required: true, message: '请输入显示名称', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function handleRegister() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await api.post('/auth/register', {
      username: form.username,
      password: form.password,
      display_name: form.display_name
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function goLogin() {
  router.push('/login')
}
</script>
