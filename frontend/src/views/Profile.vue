<template>
  <div class="apple-card p-6 max-w-lg mx-auto">
    <h3 class="text-lg font-semibold text-gray-700 mb-6">个人中心</h3>

    <el-descriptions :column="1" border class="mb-6">
      <el-descriptions-item label="用户名">{{ authStore.user?.username }}</el-descriptions-item>
      <el-descriptions-item label="显示名称">{{ authStore.user?.display_name }}</el-descriptions-item>
      <el-descriptions-item label="角色">{{ authStore.user?.is_admin ? '系统管理员' : '普通用户' }}</el-descriptions-item>
    </el-descriptions>

    <el-divider />

    <h4 class="text-md font-medium text-gray-600 mb-4">修改显示名称</h4>
    <el-form :model="profileForm" label-width="80px" class="mb-6">
      <el-form-item label="显示名称">
        <el-input v-model="profileForm.display_name" class="w-56" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="profileSaving" @click="handleUpdateProfile">保存</el-button>
      </el-form-item>
    </el-form>

    <el-divider />

    <h4 class="text-md font-medium text-gray-600 mb-4">修改密码</h4>
    <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="80px">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="pwdForm.old_password" type="password" show-password class="w-56" />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="pwdForm.new_password" type="password" show-password class="w-56" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm_password">
        <el-input v-model="pwdForm.confirm_password" type="password" show-password class="w-56" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="pwdSaving" @click="handleChangePassword">修改密码</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()

const profileForm = reactive({
  display_name: authStore.user?.display_name || ''
})
const profileSaving = ref(false)

const pwdFormRef = ref(null)
const pwdSaving = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirm = (rule, value, callback) => {
  if (value !== pwdForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const pwdRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

async function handleUpdateProfile() {
  profileSaving.value = true
  try {
    await api.put('/auth/profile', { display_name: profileForm.display_name })
    authStore.user.display_name = profileForm.display_name
    localStorage.setItem('user', JSON.stringify(authStore.user))
    ElMessage.success('显示名称已更新')
  } finally {
    profileSaving.value = false
  }
}

async function handleChangePassword() {
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return
  pwdSaving.value = true
  try {
    await api.put('/auth/change-password', {
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    ElMessage.success('密码修改成功，下次登录请使用新密码')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
    pwdFormRef.value.resetFields()
  } finally {
    pwdSaving.value = false
  }
}
</script>