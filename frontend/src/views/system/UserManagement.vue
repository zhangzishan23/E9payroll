<template>
  <div class="apple-card p-6">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold text-gray-700">用户管理</h3>
      <el-button type="primary" :icon="Plus" @click="showDialog(null)">新增用户</el-button>
    </div>

    <el-table :data="users" border stripe v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="username" label="用户名" width="120" />
      <el-table-column prop="display_name" label="显示名称" width="120" />
      <el-table-column prop="is_admin" label="管理员" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_admin ? 'danger' : 'info'">{{ row.is_admin ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDialog(row)">编辑</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="580px" append-to-body>
      <el-form ref="formRef" :model="form" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="密码" :required="!isEdit">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="显示名称" required>
          <el-input v-model="form.display_name" />
        </el-form-item>
        <el-form-item label="管理员">
          <el-switch v-model="form.is_admin" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple class="w-full" placeholder="选择角色">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const users = ref([])
const selectedRows = ref([])
const roles = ref([])
const formRef = ref(null)
const editId = ref(null)

const form = reactive({
  username: '', password: '', display_name: '', is_admin: false, role_ids: []
})

async function fetchData() {
  loading.value = true
  try {
    const [usersRes, rolesRes] = await Promise.all([
      api.get('/system/users'),
      api.get('/system/roles')
    ])
    users.value = usersRes.data
    roles.value = rolesRes.data
  } finally {
    loading.value = false
  }
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  if (row) {
    Object.assign(form, {
      username: row.username, password: '', display_name: row.display_name,
      is_admin: row.is_admin, role_ids: []
    })
  } else {
    Object.assign(form, {
      username: '', password: '', display_name: '', is_admin: false, role_ids: []
    })
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const data = { ...form }
    if (isEdit.value && !data.password) delete data.password
    if (isEdit.value) {
      await api.put(`/system/users/${editId.value}`, data)
      ElMessage.success('编辑成功')
    } else {
      await api.post('/system/users', data)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '删除确认', {
    type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消'
  })
  await api.delete(`/system/users/${row.id}`)
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(fetchData)
</script>