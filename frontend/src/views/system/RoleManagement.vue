<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">角色管理</h3>
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">新增</el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
        删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
      </el-button>
    </div>

    <el-table :data="roles" border stripe v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="name" label="角色名称" width="150" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column prop="is_preset" label="预置" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_preset ? 'warning' : 'info'">{{ row.is_preset ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="data_scope" label="数据范围" width="100" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDialog(row)">编辑</el-button>
          <el-button type="warning" link size="small" @click="showPermission(row)">权限</el-button>
          <el-button v-if="!row.is_preset" type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '新增角色'" width="550px" append-to-body>
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="数据范围">
          <el-select v-model="form.data_scope" class="w-full">
            <el-option label="全部数据" value="all" />
            <el-option label="本部门及下级" value="dept" />
            <el-option label="仅本人" value="self" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="permVisible" title="权限配置" width="700px" append-to-body>
      <div v-for="module in modules" :key="module.key" class="mb-3">
        <div class="font-semibold text-sm mb-1">{{ module.label }}</div>
        <el-checkbox-group v-model="permForm.selected" class="flex gap-3 flex-wrap">
          <el-checkbox v-for="act in actions" :key="`${module.key}-${act}`" :label="`${module.key}:${act}`" :value="`${module.key}:${act}`">
            {{ actLabels[act] }}
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <el-button @click="permVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingPerm" @click="savePermission">保存权限</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const savingPerm = ref(false)
const dialogVisible = ref(false)
const permVisible = ref(false)
const isEdit = ref(false)
const roles = ref([])
const selectedRows = ref([])
const editId = ref(null)
const permRoleId = ref(null)

const modules = [
  { key: 'employee', label: '人事信息' },
  { key: 'attendance', label: '考勤管理' },
  { key: 'salary', label: '薪资核算' },
  { key: 'approval', label: '审批流程' },
  { key: 'report', label: '报表导出' },
  { key: 'system', label: '系统管理' }
]
const actions = ['view', 'create', 'edit', 'delete', 'export', 'use']
const actLabels = { view: '查看', create: '新增', edit: '编辑', delete: '删除', export: '导出', use: '使用' }

const form = reactive({ name: '', description: '', data_scope: 'all' })
const permForm = reactive({ selected: [] })

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/system/roles')
    roles.value = res.data
  } finally {
    loading.value = false
  }
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  if (row) {
    Object.assign(form, { name: row.name, description: row.description || '', data_scope: row.data_scope })
  } else {
    Object.assign(form, { name: '', description: '', data_scope: 'all' })
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/system/roles/${editId.value}`, form)
      ElMessage.success('编辑成功')
    } else {
      await api.post('/system/roles', form)
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
  await ElMessageBox.confirm(`确定删除角色「${row.name}」吗？`, '删除确认', {
    type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消'
  })
  await api.delete(`/system/roles/${row.id}`)
  ElMessage.success('删除成功')
  fetchData()
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的角色')
    return
  }
  const presetNames = selectedRows.value.filter(r => r.is_preset).map(r => r.name)
  if (presetNames.length) {
    ElMessage.warning(`预置角色不可删除：${presetNames.join('、')}，请先取消选择`)
    return
  }
  const names = selectedRows.value.map(r => r.name).join('、')
  await ElMessageBox.confirm(
    `确定要删除以下 ${selectedRows.value.length} 个角色吗？\n${names}`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.map(r => r.id)
    await api.post('/system/roles/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 个角色`)
    selectedRows.value = []
    fetchData()
  } catch (e) {
    ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

async function showPermission(row) {
  permRoleId.value = row.id
  const res = await api.get(`/system/roles/${row.id}/permissions`)
  permForm.selected = res.data.map(p => `${p.module}:${p.action}`)
  permVisible.value = true
}

async function savePermission() {
  savingPerm.value = true
  try {
    const permissions = permForm.selected.map(s => {
      const [module, action] = s.split(':')
      return { module, action }
    })
    await api.post(`/system/roles/${permRoleId.value}/permissions`, { permissions })
    ElMessage.success('权限配置成功')
    permVisible.value = false
  } finally {
    savingPerm.value = false
  }
}

onMounted(fetchData)
</script>