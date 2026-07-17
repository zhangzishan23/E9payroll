<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">用户管理</h3>
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)" v-permission="'system:user'">新增用户</el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete" v-permission="'system:user'">
        删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
      </el-button>
    </div>

    <el-table :data="users" border stripe v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" v-permission="'system:user'" />
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="display_name" label="显示名称" width="120" />
      <el-table-column prop="role_names" label="所属角色" min-width="180">
        <template #default="{ row }">
          <el-tag v-for="role in row.role_names" :key="role" size="small" class="mr-1 mb-1" type="info">{{ role }}</el-tag>
          <span v-if="!row.role_names?.length" class="text-gray-400">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="is_admin" label="超级管理员" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_admin ? 'danger' : 'info'" size="small">{{ row.is_admin ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_active"
            :disabled="row.username === 'admin' || !hasPerm('system:user')"
            @change="(val) => toggleActive(row, val)"
            active-text="启用"
            inactive-text="禁用"
            inline-prompt
          />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDialog(row)" v-permission="'system:user'">编辑</el-button>
          <el-button type="warning" link size="small" @click="handleResetPassword(row)" v-permission="'system:user'">重置密码</el-button>
          <el-button v-if="row.username !== 'admin'" type="danger" link size="small" @click="handleDelete(row)" v-permission="'system:user'">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="580px" append-to-body>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" :prop="isEdit ? '' : 'password'">
          <el-input v-model="form.password" type="password" show-password :placeholder="isEdit ? '不修改密码请留空' : '请输入密码'" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="请输入显示名称" />
        </el-form-item>
        <el-form-item label="账号状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" inline-prompt />
        </el-form-item>
        <el-form-item label="超级管理员">
          <el-switch v-model="form.is_admin" @change="onAdminChange" />
          <span class="text-xs text-gray-400 ml-2">超级管理员拥有所有权限，无需分配角色</span>
        </el-form-item>
        <el-form-item label="分配角色" v-if="!form.is_admin">
          <el-select v-model="form.role_ids" multiple class="w-full" placeholder="请选择角色">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="pwdVisible" title="重置密码" width="450px" append-to-body>
      <el-form label-width="100px">
        <el-form-item label="用户">
          <span>{{ pwdUser?.username }} ({{ pwdUser?.display_name }})</span>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" show-password placeholder="默认密码123456" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSaving" @click="confirmResetPwd">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import api from '../../api'
import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const pwdSaving = ref(false)
const dialogVisible = ref(false)
const pwdVisible = ref(false)
const isEdit = ref(false)
const users = ref([])
const selectedRows = ref([])
const roles = ref([])
const formRef = ref(null)
const editId = ref(null)
const pwdUser = ref(null)
const newPassword = ref('123456')

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
}

const form = reactive({
  username: '', password: '', display_name: '', is_admin: false, is_active: true, role_ids: []
})

function hasPerm(perm) {
  return authStore.hasPermission(perm)
}

function formatTime(isoStr) {
  if (!isoStr) return '-'
  return isoStr.replace('T', ' ').substring(0, 19)
}

async function fetchData() {
  loading.value = true
  try {
    const [usersRes, rolesRes] = await Promise.all([
      api.get('/system/users'),
      api.get('/system/roles')
    ])
    users.value = usersRes.data
    roles.value = rolesRes.data.filter(r => r.name !== '超级管理员')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载数据失败')
  } finally {
    loading.value = false
  }
}

function onAdminChange(val) {
  if (val) {
    form.role_ids = []
  }
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  if (row) {
    Object.assign(form, {
      username: row.username,
      password: '',
      display_name: row.display_name,
      is_admin: row.is_admin,
      is_active: row.is_active !== false,
      role_ids: row.role_ids || []
    })
  } else {
    Object.assign(form, {
      username: '',
      password: '',
      display_name: '',
      is_admin: false,
      is_active: true,
      role_ids: []
    })
  }
  dialogVisible.value = true
  setTimeout(() => formRef.value?.clearValidate(), 0)
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  if (!isEdit.value && form.password.length < 6) {
    ElMessage.warning('密码长度不能少于6位')
    return
  }

  saving.value = true
  try {
    const data = { ...form }
    if (isEdit.value) {
      if (!data.password) delete data.password
      await api.put(`/system/users/${editId.value}`, data)
      ElMessage.success('编辑成功')
    } else {
      await api.post('/system/users', data)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleActive(row, val) {
  try {
    await api.put(`/system/users/${row.id}`, { is_active: val })
    ElMessage.success(val ? '已启用账号' : '已禁用账号')
  } catch (e) {
    row.is_active = !val
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

function handleResetPassword(row) {
  pwdUser.value = row
  newPassword.value = '123456'
  pwdVisible.value = true
}

async function confirmResetPwd() {
  if (newPassword.value.length < 6) {
    ElMessage.warning('新密码长度不能少于6位')
    return
  }
  pwdSaving.value = true
  try {
    const res = await api.post(`/system/users/${pwdUser.value.id}/reset-password`, { new_password: newPassword.value })
    ElMessage.success(res.data.message || '密码重置成功')
    pwdVisible.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置密码失败')
  } finally {
    pwdSaving.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '删除确认', {
    type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消'
  })
  try {
    await api.delete(`/system/users/${row.id}`)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的用户')
    return
  }
  const adminNames = selectedRows.value.filter(r => r.username === 'admin').map(r => r.username)
  const selfSelected = selectedRows.value.find(r => r.id === authStore.user?.id)
  if (adminNames.length) {
    ElMessage.warning('超级管理员账号不可删除，请先取消选择')
    return
  }
  if (selfSelected) {
    ElMessage.warning('不能删除当前登录用户，请先取消选择')
    return
  }
  const names = selectedRows.value.map(r => r.username).join('、')
  await ElMessageBox.confirm(
    `确定要删除以下 ${selectedRows.value.length} 个用户吗？\n${names}`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.map(r => r.id)
    await api.post('/system/users/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 个用户`)
    selectedRows.value = []
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '批量删除失败')
  }
}

onMounted(fetchData)
</script>
