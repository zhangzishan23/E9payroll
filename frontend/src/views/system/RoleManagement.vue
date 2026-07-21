<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">角色管理</h3>
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)" v-permission="'system:role'">新增角色</el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete" v-permission="'system:role'">
        删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
      </el-button>
    </div>

    <el-table :data="roles" border stripe v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" v-permission="'system:role'" />
      <el-table-column prop="name" label="角色名称" width="180" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column label="权限数量" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" type="primary">{{ getPermCount(row.id) }} 项</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_preset" label="预置" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_preset ? 'warning' : 'info'" size="small">{{ row.is_preset ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="data_scope" label="数据范围" width="130" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.data_scope === 'all' ? 'success' : row.data_scope === 'dept' ? 'primary' : 'info'">
            {{ scopeLabels[row.data_scope] || row.data_scope }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDialog(row)" v-permission="'system:role'">编辑/权限</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)" v-permission="'system:role'">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? `编辑角色 - ${form.name}` : '新增角色'"
      width="850px"
      append-to-body
      :close-on-click-modal="false"
      destroy-on-close
      class="role-dialog"
    >
      <el-tabs v-model="activeTab" class="permission-tabs">
        <el-tab-pane label="基本信息" name="basic">
          <el-form :model="form" label-width="100px" class="mt-4">
            <el-form-item label="角色名称" required>
              <el-input v-model="form.name" placeholder="请输入角色名称" />
            </el-form-item>
            <el-form-item label="角色描述">
              <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入角色描述" />
            </el-form-item>
            <el-form-item label="数据范围">
              <el-select v-model="form.data_scope" class="w-full" placeholder="请选择数据范围">
                <el-option label="全部数据（可查看所有部门数据）" value="all" />
                <el-option label="本部门及下级（仅可查看本部门数据）" value="dept" />
                <el-option label="仅本人（仅可查看自己的数据）" value="self" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="权限配置" name="permission">
          <div class="permission-config mt-2">
            <div class="perm-toolbar flex items-center gap-2 flex-wrap pb-3 mb-3 border-b border-gray-200">
              <span class="text-sm text-gray-500 mr-2">快捷操作：</span>
              <el-button size="small" @click="selectAllPerms">全选所有权限</el-button>
              <el-button size="small" @click="clearAllPerms">清空所有</el-button>
              <el-divider direction="vertical" />
              <span class="text-sm text-gray-500">快速套用模板：</span>
              <el-button size="small" type="primary" plain @click="selectPreset('hr_specialist')">人事专员</el-button>
              <el-button size="small" type="success" plain @click="selectPreset('hr_supervisor')">人事主管</el-button>
              <el-button size="small" type="warning" plain @click="selectPreset('accountant')">会计</el-button>
              <el-button size="small" type="info" plain @click="selectPreset('employee')">普通员工</el-button>
            </div>
            <div class="perm-count-bar text-sm text-gray-600 mb-3">
              已选择权限：<span class="text-blue-600 font-semibold">{{ permForm.selected.length }}</span> / {{ totalPermCount }} 项
            </div>
            <div class="max-h-[480px] overflow-y-auto pr-2 perm-list">
              <div v-for="module in permModules" :key="module.key" class="module-card mb-4">
                <div class="module-header flex items-center justify-between mb-2 px-3 py-2 bg-blue-50 rounded-t-lg border border-blue-100">
                  <div class="flex items-center gap-3">
                    <el-checkbox
                      :model-value="isModuleFullySelected(module)"
                      :indeterminate="isModuleIndeterminate(module)"
                      @change="(val) => toggleModule(module, val)"
                      size="large"
                    />
                    <span class="font-semibold text-blue-800 text-base">{{ module.label }}</span>
                  </div>
                  <span class="text-sm text-blue-500">
                    {{ getModuleSelectedCount(module) }} / {{ module.actions.length }}
                  </span>
                </div>
                <div class="module-body px-3 py-3 bg-white rounded-b-lg border border-t-0 border-gray-200">
                  <div class="flex gap-2 flex-wrap">
                    <div
                      v-for="act in module.actions"
                      :key="`${module.key}:${act.key}`"
                      :class="[
                        'perm-item px-3 py-1.5 rounded-md cursor-pointer text-sm border transition-all duration-150 select-none',
                        isPermSelected(module.key, act.key)
                          ? 'bg-blue-500 text-white border-blue-600 shadow-sm'
                          : 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600'
                      ]"
                      @click="togglePerm(module.key, act.key)"
                    >
                      <span class="flex items-center gap-1.5">
                        <el-icon v-if="isPermSelected(module.key, act.key)" size="14"><Check /></el-icon>
                        {{ act.label }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Check } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const activeTab = ref('basic')
const roles = ref([])
const permModules = ref([])
const selectedRows = ref([])
const editId = ref(null)
const rolePermMap = ref({})

const scopeLabels = {
  all: '全部数据',
  dept: '本部门及下级',
  self: '仅本人'
}

const presetTemplates = {
  hr_specialist: [
    'dashboard:view', 'dashboard:work_view',
    'employee:view', 'employee:create', 'employee:edit', 'employee:export', 'employee:import', 'employee:sync',
    'attendance:view', 'attendance:create', 'attendance:edit', 'attendance:export', 'attendance:import', 'attendance:sync', 'attendance:writeoff',
    'performance:view', 'performance:create', 'performance:edit', 'performance:export', 'performance:import',
    'insurance:view', 'insurance:create', 'insurance:edit', 'insurance:export', 'insurance:import', 'insurance:template',
    'report:view', 'report:export', 'report:contract_warning_view', 'report:contract_warning_export'
  ],
  hr_supervisor: [
    'dashboard:view', 'dashboard:work_view', 'dashboard:leader_view',
    'employee:view', 'employee:create', 'employee:edit', 'employee:delete', 'employee:export', 'employee:import', 'employee:sync',
    'attendance:view', 'attendance:create', 'attendance:edit', 'attendance:delete', 'attendance:export', 'attendance:import', 'attendance:sync', 'attendance:writeoff',
    'performance:view', 'performance:create', 'performance:edit', 'performance:export', 'performance:import',
    'insurance:view', 'insurance:create', 'insurance:edit', 'insurance:delete', 'insurance:export', 'insurance:import', 'insurance:template',
    'salary:view', 'salary:edit', 'salary:delete', 'salary:check', 'salary:step_confirm', 'salary:export',
    'approval:view', 'approval:approve',
    'report:view', 'report:export', 'report:contract_warning_view', 'report:contract_warning_export'
  ],
  accountant: [
    'dashboard:view', 'dashboard:work_view', 'dashboard:leader_view',
    'employee:view', 'employee:export',
    'attendance:view', 'attendance:export',
    'performance:view',
    'insurance:view',
    'salary:view', 'salary:edit', 'salary:delete', 'salary:check', 'salary:step_confirm', 'salary:tax_export', 'salary:tax_import', 'salary:travel_import', 'salary:export',
    'approval:view',
    'report:view', 'report:export', 'report:contract_warning_view', 'report:contract_warning_export'
  ],
  employee: [
    'dashboard:view', 'dashboard:work_view'
  ]
}

const form = reactive({ name: '', description: '', data_scope: 'all', is_preset: false })
const permForm = reactive({ selected: [] })

const totalPermCount = computed(() => {
  return permModules.value.reduce((sum, m) => sum + m.actions.length, 0)
})

function getPermCount(roleId) {
  return rolePermMap.value[roleId] || 0
}

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/system/roles')
    roles.value = res.data
    rolePermMap.value = {}
    roles.value.forEach(role => {
      if (role.is_preset && role.name === '超级管理员') {
        rolePermMap.value[role.id] = totalPermCount.value
      } else {
        rolePermMap.value[role.id] = 0
        api.get(`/system/roles/${role.id}/permissions`).then(pRes => {
          rolePermMap.value[role.id] = pRes.data.length
        }).catch(() => {})
      }
    })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function fetchPermModules() {
  try {
    const res = await api.get('/system/permissions')
    permModules.value = res.data
  } catch (e) {
    permModules.value = [
      { key: 'dashboard', label: '工作台', actions: [{ key: 'view', label: '查看工作台' }, { key: 'leader_view', label: '管理视角/数据看板' }] },
      { key: 'employee', label: '人事档案', actions: [
        { key: 'view', label: '查看档案' }, { key: 'create', label: '新增员工' }, { key: 'edit', label: '编辑档案' },
        { key: 'delete', label: '删除员工' }, { key: 'export', label: '导出花名册' }, { key: 'import', label: '批量导入' }, { key: 'sync', label: '同步钉钉' }
      ]},
      { key: 'attendance', label: '考勤管理', actions: [
        { key: 'view', label: '查看考勤' }, { key: 'create', label: '新增记录' }, { key: 'edit', label: '编辑考勤' },
        { key: 'delete', label: '删除记录' }, { key: 'export', label: '导出考勤' }, { key: 'import', label: '导入考勤' },
        { key: 'sync', label: '同步钉钉' }, { key: 'writeoff', label: '缺卡核销' }
      ]},
      { key: 'performance', label: '绩效评分', actions: [
        { key: 'view', label: '查看绩效' }, { key: 'create', label: '新增评分' }, { key: 'edit', label: '编辑评分' },
        { key: 'delete', label: '删除评分' }, { key: 'export', label: '导出绩效' }, { key: 'import', label: '导入绩效' }
      ]},
      { key: 'insurance', label: '社保公积金', actions: [
        { key: 'view', label: '查看社保' }, { key: 'create', label: '新增记录' }, { key: 'edit', label: '编辑社保' },
        { key: 'delete', label: '删除记录' }, { key: 'export', label: '导出社保' }, { key: 'import', label: '导入社保' },
        { key: 'template', label: '管理导入模板' }
      ]},
      { key: 'salary', label: '薪资计算', actions: [
        { key: 'view', label: '查看薪资' }, { key: 'edit', label: '编辑薪资' },
        { key: 'delete', label: '删除薪资' }, { key: 'check', label: '数据检查' }, { key: 'step_confirm', label: '步骤确认' },
        { key: 'tax_export', label: '导出报税模板' }, { key: 'tax_import', label: '导入个税申报结果' },
        { key: 'travel_import', label: '导入临时性差旅补贴' }, { key: 'export', label: '导出薪资' }
      ]},
      { key: 'approval', label: '审批流程', actions: [
        { key: 'view', label: '查看审批' }, { key: 'submit', label: '提交审批' }, { key: 'approve', label: '审核操作' }
      ]},
      { key: 'report', label: '报表导出', actions: [
        { key: 'view', label: '查看报表' }, { key: 'export', label: '导出报表' }
      ]},
      { key: 'system', label: '系统管理', actions: [
        { key: 'user', label: '用户管理' }, { key: 'role', label: '角色权限' },
        { key: 'dict', label: '数据字典' }, { key: 'log', label: '操作日志' }, { key: 'backup', label: '数据备份' }
      ]}
    ]
  }
}

function isPermSelected(moduleKey, actionKey) {
  return permForm.selected.includes(`${moduleKey}:${actionKey}`)
}

function togglePerm(moduleKey, actionKey) {
  const code = `${moduleKey}:${actionKey}`
  const idx = permForm.selected.indexOf(code)
  if (idx >= 0) {
    permForm.selected.splice(idx, 1)
  } else {
    permForm.selected.push(code)
  }
}

function isModuleFullySelected(module) {
  const allPerms = module.actions.map(a => `${module.key}:${a.key}`)
  return allPerms.every(p => permForm.selected.includes(p))
}

function isModuleIndeterminate(module) {
  const allPerms = module.actions.map(a => `${module.key}:${a.key}`)
  const selectedCount = allPerms.filter(p => permForm.selected.includes(p)).length
  return selectedCount > 0 && selectedCount < allPerms.length
}

function getModuleSelectedCount(module) {
  const allPerms = module.actions.map(a => `${module.key}:${a.key}`)
  return allPerms.filter(p => permForm.selected.includes(p)).length
}

function toggleModule(module, checked) {
  const allPerms = module.actions.map(a => `${module.key}:${a.key}`)
  if (checked) {
    allPerms.forEach(p => {
      if (!permForm.selected.includes(p)) permForm.selected.push(p)
    })
  } else {
    permForm.selected = permForm.selected.filter(p => !allPerms.includes(p))
  }
}

function selectAllPerms() {
  const allPerms = []
  permModules.value.forEach(m => {
    m.actions.forEach(a => allPerms.push(`${m.key}:${a.key}`))
  })
  permForm.selected = allPerms
  ElMessage.success('已全选所有权限')
}

function clearAllPerms() {
  permForm.selected = []
  ElMessage.success('已清空所有权限')
}

function selectPreset(templateKey) {
  permForm.selected = [...(presetTemplates[templateKey] || [])]
  const names = { hr_specialist: '人事专员', hr_supervisor: '人事主管', accountant: '会计', employee: '普通员工' }
  ElMessage.success(`已套用「${names[templateKey]}」权限模板`)
}

async function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  activeTab.value = 'basic'
  if (row) {
    Object.assign(form, {
      name: row.name,
      description: row.description || '',
      data_scope: row.data_scope,
      is_preset: row.is_preset
    })
    try {
      const res = await api.get(`/system/roles/${row.id}/permissions`)
      permForm.selected = res.data.map(p => `${p.module}:${p.action}`)
    } catch (e) {
      permForm.selected = []
    }
  } else {
    Object.assign(form, { name: '', description: '', data_scope: 'all', is_preset: false })
    permForm.selected = []
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入角色名称')
    activeTab.value = 'basic'
    return
  }
  saving.value = true
  try {
    let roleId = editId.value
    if (isEdit.value) {
      await api.put(`/system/roles/${editId.value}`, {
        name: form.name,
        description: form.description,
        data_scope: form.data_scope
      })
      roleId = editId.value
    } else {
      const createRes = await api.post('/system/roles', {
        name: form.name,
        description: form.description,
        data_scope: form.data_scope
      })
      roleId = createRes.data.id
    }

    const permissions = permForm.selected.map(s => {
      const parts = s.split(':')
      return { module: parts[0], action: parts.slice(1).join(':') }
    })
    await api.post(`/system/roles/${roleId}/permissions`, { permissions })

    ElMessage.success(isEdit.value ? '角色修改成功' : '角色创建成功')
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除角色「${row.name}」吗？删除后该角色下的用户将失去对应权限。`, '删除确认', {
    type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消'
  })
  try {
    await api.delete(`/system/roles/${row.id}`)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的角色')
    return
  }
  const names = selectedRows.value.map(r => r.name).join('、')
  await ElMessageBox.confirm(
    `确定要删除以下 ${selectedRows.value.length} 个角色吗？\n${names}\n删除后这些角色下的用户将失去对应权限。若角色下还有用户将无法删除。`,
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
    ElMessage.error(e.response?.data?.detail || '批量删除失败')
  }
}

onMounted(() => {
  fetchPermModules().then(() => {
    fetchData()
  })
})
</script>

<style scoped>
.perm-item {
  min-width: 90px;
  text-align: center;
  user-select: none;
}
.perm-item:active {
  transform: scale(0.95);
}
.module-card {
  transition: box-shadow 0.2s;
}
.module-card:hover {
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
}
:deep(.permission-tabs .el-tabs__header) {
  margin-bottom: 0;
}
:deep(.permission-tabs .el-tabs__nav-wrap::after) {
  height: 1px;
}
</style>
