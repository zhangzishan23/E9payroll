<template>
  <div class="space-y-6">
    <div class="apple-card p-6">
      <div class="flex items-center gap-2 mb-4">
        <h3 class="text-lg font-semibold text-gray-700 shrink-0">数据统计中心</h3>
        <el-date-picker v-model="statsPeriod" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" @change="fetchStats" />
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div class="apple-card p-4 text-center">
          <div class="text-3xl font-bold text-blue-600">{{ stats.total_employees }}</div>
          <div class="text-sm text-gray-500 mt-1">在职员工总数</div>
        </div>
        <div class="apple-card p-4 text-center">
          <div class="text-3xl font-bold text-green-600">{{ stats.salary_completed }}/{{ stats.salary_total }}</div>
          <div class="text-sm text-gray-500 mt-1">薪资核算完成</div>
        </div>
        <div class="apple-card p-4 text-center">
          <div class="text-3xl font-bold text-orange-600">{{ stats.review_passed }}/{{ stats.review_rejected }}</div>
          <div class="text-sm text-gray-500 mt-1">审核通过/驳回</div>
        </div>
        <div class="apple-card p-4 text-center">
          <div class="text-3xl font-bold text-purple-600">{{ stats.attend_rate }}%</div>
          <div class="text-sm text-gray-500 mt-1">考勤出勤率</div>
        </div>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="apple-card p-4 text-center">
          <div class="text-xl font-semibold text-blue-600">{{ fmtMoney(stats.avg_gross) }}</div>
          <div class="text-xs text-gray-400 mt-1">人均应发工资</div>
        </div>
        <div class="apple-card p-4 text-center">
          <div class="text-xl font-semibold text-green-600">{{ fmtMoney(stats.avg_net) }}</div>
          <div class="text-xs text-gray-400 mt-1">人均实发工资</div>
        </div>
        <div class="apple-card p-4 text-center">
          <div class="text-xl font-semibold text-red-600">{{ stats.total_late }}</div>
          <div class="text-xs text-gray-400 mt-1">迟到总次数</div>
        </div>
        <div class="apple-card p-4 text-center">
          <div class="text-xl font-semibold text-gray-600">{{ stats.total_leave.toFixed(1) }}</div>
          <div class="text-xs text-gray-400 mt-1">请假总天数</div>
        </div>
      </div>
    </div>

    <div class="apple-card p-6">
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-lg font-semibold text-gray-700">报表导出中心</h3>
        <el-button type="primary" @click="showConfigDialog">
          <el-icon><Setting /></el-icon>
          导出表配置
        </el-button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="apple-card p-6 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-dashed border-blue-200 hover:border-blue-400" @click="exportReport('roster')">
          <el-icon class="text-5xl text-blue-500 mb-4"><Document /></el-icon>
          <div class="font-semibold text-lg">员工花名册</div>
          <div class="text-sm text-gray-500 mt-2">导出全量员工基本信息</div>
          <el-button type="primary" class="mt-4" size="default">立即导出</el-button>
        </div>

        <div class="apple-card p-6 text-center border-2 border-dashed border-green-200 hover:border-green-400 hover:shadow-lg transition-shadow">
          <div class="flex items-center gap-2 justify-center mb-4">
            <el-icon class="text-4xl text-green-500"><Document /></el-icon>
            <span class="font-semibold text-lg">薪资核算表</span>
          </div>
          <div class="flex items-center gap-2 justify-center mb-3">
            <el-date-picker v-model="salaryPeriod" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" />
          </div>
          <div class="flex items-center gap-2 justify-center">
            <el-select v-model="selectedTemplate" placeholder="选择模板" size="small" class="!w-32" clearable>
              <el-option v-for="tpl in salaryTemplates" :key="tpl.id" :label="tpl.name + (tpl.is_default ? ' (默认)' : '')" :value="tpl.id" />
            </el-select>
            <el-button type="primary" size="small" @click="exportSalaryByTemplate">导出Excel</el-button>
          </div>
        </div>

        <div class="apple-card p-6 text-center border-2 border-dashed border-orange-200 hover:border-orange-400 hover:shadow-lg transition-shadow">
          <div class="flex items-center gap-2 justify-center mb-4">
            <el-icon class="text-4xl text-orange-500"><Calendar /></el-icon>
            <span class="font-semibold text-lg">考勤统计表</span>
          </div>
          <div class="flex items-center gap-2 justify-center mb-4">
            <el-date-picker v-model="attPeriod" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" />
            <el-button type="primary" size="small" @click="exportReport('attendance')">导出Excel</el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="configVisible" title="导出表配置" width="900px" append-to-body>
      <el-tabs v-model="configTab">
        <el-tab-pane label="薪资表模板" name="salary">
          <div class="mb-4 flex justify-between items-center">
            <div class="text-sm text-gray-500">配置不同用途的薪资导出表字段，财务表和工资条可分别配置</div>
            <el-button type="primary" size="small" @click="createNewTemplate">
              <el-icon><Plus /></el-icon>
              新建模板
            </el-button>
          </div>
          <el-table :data="templates" border stripe size="small">
            <el-table-column prop="name" label="模板名称" width="150" />
            <el-table-column prop="template_type" label="类型" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="getTypeTagType(row.template_type)">{{ getTypeLabel(row.template_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="150" show-overflow-tooltip />
            <el-table-column prop="fields.length" label="字段数" width="80" align="center" />
            <el-table-column label="默认" width="70" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.is_enabled" @change="toggleTemplateEnabled(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-link type="primary" size="small" @click="editTemplate(row)">编辑</el-link>
                <el-link v-if="!row.is_default" type="success" size="small" class="ml-2" @click="setDefaultTemplate(row)">设为默认</el-link>
                <el-link v-if="!row.is_default" type="danger" size="small" class="ml-2" @click="deleteTemplate(row)">删除</el-link>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <el-dialog v-model="editVisible" :title="editingTemplate.id ? '编辑模板' : '新建模板'" width="800px" append-to-body>
      <el-form :model="editingTemplate" label-width="100px" size="small">
        <el-form-item label="模板名称" required>
          <el-input v-model="editingTemplate.name" placeholder="如：财务导出表、工资条表" />
        </el-form-item>
        <el-form-item label="模板类型" required>
          <el-select v-model="editingTemplate.template_type" placeholder="选择类型" class="!w-full">
            <el-option label="财务薪资表" value="salary_finance" />
            <el-option label="工资条表" value="salary_slip" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="模板说明">
          <el-input v-model="editingTemplate.description" type="textarea" :rows="2" placeholder="模板用途说明" />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="editingTemplate.is_default" />
          <span class="text-xs text-gray-500 ml-2">设为默认后，导出时将默认使用此模板</span>
        </el-form-item>
      </el-form>

      <div class="border rounded-lg p-4 mt-4">
        <div class="font-semibold text-sm mb-3">字段选择（拖拽可调整顺序）</div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <div class="text-xs text-gray-500 mb-2">可选字段</div>
            <div class="border rounded p-2 max-h-80 overflow-y-auto bg-gray-50">
              <div
                v-for="f in availableFields.filter(f => !selectedFieldKeys.includes(f.key))"
                :key="f.key"
                class="px-2 py-1.5 mb-1 bg-white rounded border cursor-move hover:bg-blue-50 hover:border-blue-300 text-sm flex items-center justify-between"
                @click="addField(f)"
              >
                <span>{{ f.label }}</span>
                <el-icon class="text-green-500"><Plus /></el-icon>
              </div>
            </div>
          </div>
          <div>
            <div class="text-xs text-gray-500 mb-2">已选字段（点击 × 移除）</div>
            <div class="border rounded p-2 max-h-80 overflow-y-auto bg-blue-50">
              <div
                v-for="(f, idx) in selectedFields"
                :key="f.key"
                class="px-2 py-1.5 mb-1 bg-white rounded border cursor-move hover:bg-orange-50 hover:border-orange-300 text-sm flex items-center justify-between"
              >
                <span class="flex items-center gap-2">
                  <el-icon class="text-gray-400 cursor-move"><Rank /></el-icon>
                  <span>{{ idx + 1 }}. {{ f.label }}</span>
                </span>
                <el-icon class="text-red-500 cursor-pointer" @click="removeField(f.key)"><Close /></el-icon>
              </div>
              <div v-if="!selectedFields.length" class="text-center text-gray-400 py-8 text-sm">
                点击左侧字段添加
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate">保存模板</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Document, Calendar, Setting, Plus, Close, Rank } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import { getDefaultPeriod } from '../../utils/date.js'

const defaultPeriod = getDefaultPeriod()
const salaryPeriod = ref(defaultPeriod)
const attPeriod = ref(defaultPeriod)
const statsPeriod = ref(defaultPeriod)
const selectedTemplate = ref(null)

const stats = reactive({
  total_employees: 0,
  salary_total: 0,
  salary_completed: 0,
  review_passed: 0,
  review_rejected: 0,
  attend_rate: 0,
  avg_gross: 0,
  avg_net: 0,
  total_late: 0,
  total_leave: 0
})

const configVisible = ref(false)
const configTab = ref('salary')
const templates = ref([])
const availableFields = ref([])

const editVisible = ref(false)
const editingTemplate = reactive({
  id: null,
  name: '',
  template_type: 'salary_finance',
  description: '',
  fields: [],
  is_default: false,
  is_enabled: true
})

const salaryTemplates = computed(() => templates.value.filter(t => t.is_enabled && ['salary_finance', 'salary_slip', 'custom'].includes(t.template_type)))

const selectedFields = computed({
  get: () => editingTemplate.fields,
  set: (val) => { editingTemplate.fields = val }
})

const selectedFieldKeys = computed(() => selectedFields.value.map(f => f.key))

function fmtMoney(val) {
  if (val == null || val === 0) return '¥0'
  return '¥' + Number(val).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function getTypeLabel(type) {
  const map = { salary_finance: '财务薪资表', salary_slip: '工资条表', tax: '报税表', roster: '花名册', attendance: '考勤表', custom: '自定义' }
  return map[type] || type
}

function getTypeTagType(type) {
  const map = { salary_finance: 'success', salary_slip: 'warning', tax: 'danger', custom: 'info' }
  return map[type] || ''
}

async function fetchStats() {
  try {
    const res = await api.get('/reports/stats', { params: { period: statsPeriod.value } })
    const d = res.data
    stats.total_employees = d.total_employees || 0
    if (d.salary_stats) {
      stats.salary_total = d.salary_stats.total || 0
      stats.salary_completed = d.salary_stats.completed || 0
      stats.review_passed = d.salary_stats.review_passed || 0
      stats.review_rejected = d.salary_stats.review_rejected || 0
      stats.avg_gross = d.salary_stats.avg_gross_salary || 0
      stats.avg_net = d.salary_stats.avg_net_salary || 0
    }
    if (d.attendance_stats) {
      stats.attend_rate = d.attendance_stats.avg_rate || 0
      stats.total_late = d.attendance_stats.total_late || 0
      stats.total_leave = d.attendance_stats.total_leave || 0
    }
  } catch {
    ElMessage.error('加载统计数据失败')
  }
}

async function fetchTemplates() {
  try {
    const res = await api.get('/reports/export/templates')
    templates.value = res.data
  } catch {
    ElMessage.error('加载模板列表失败')
  }
}

async function fetchAvailableFields() {
  try {
    const res = await api.get('/reports/export/available-fields')
    availableFields.value = res.data.salary || []
  } catch {}
}

function showConfigDialog() {
  fetchTemplates()
  fetchAvailableFields()
  configVisible.value = true
}

function createNewTemplate() {
  editingTemplate.id = null
  editingTemplate.name = ''
  editingTemplate.template_type = 'salary_finance'
  editingTemplate.description = ''
  editingTemplate.fields = []
  editingTemplate.is_default = false
  editingTemplate.is_enabled = true
  editVisible.value = true
}

function editTemplate(row) {
  editingTemplate.id = row.id
  editingTemplate.name = row.name
  editingTemplate.template_type = row.template_type
  editingTemplate.description = row.description || ''
  editingTemplate.fields = [...(row.fields || [])]
  editingTemplate.is_default = row.is_default
  editingTemplate.is_enabled = row.is_enabled
  editVisible.value = true
}

function addField(field) {
  if (selectedFieldKeys.value.includes(field.key)) return
  editingTemplate.fields.push({ ...field })
}

function removeField(key) {
  const idx = editingTemplate.fields.findIndex(f => f.key === key)
  if (idx >= 0) editingTemplate.fields.splice(idx, 1)
}

async function saveTemplate() {
  if (!editingTemplate.name.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }
  if (!editingTemplate.fields.length) {
    ElMessage.warning('请至少选择一个字段')
    return
  }
  try {
    const payload = {
      name: editingTemplate.name,
      template_type: editingTemplate.template_type,
      description: editingTemplate.description,
      fields: editingTemplate.fields,
      is_default: editingTemplate.is_default,
      is_enabled: editingTemplate.is_enabled
    }
    if (editingTemplate.id) {
      await api.put(`/reports/export/templates/${editingTemplate.id}`, payload)
      ElMessage.success('模板已更新')
    } else {
      await api.post('/reports/export/templates', payload)
      ElMessage.success('模板已创建')
    }
    editVisible.value = false
    await fetchTemplates()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function toggleTemplateEnabled(row) {
  try {
    await api.put(`/reports/export/templates/${row.id}`, {
      name: row.name,
      template_type: row.template_type,
      description: row.description,
      fields: row.fields,
      is_default: row.is_default,
      is_enabled: row.is_enabled
    })
  } catch (e) {
    row.is_enabled = !row.is_enabled
    ElMessage.error('操作失败')
  }
}

async function setDefaultTemplate(row) {
  try {
    await api.put(`/reports/export/templates/${row.id}`, {
      name: row.name,
      template_type: row.template_type,
      description: row.description,
      fields: row.fields,
      is_default: true,
      is_enabled: row.is_enabled
    })
    ElMessage.success(`已将「${row.name}」设为默认模板`)
    await fetchTemplates()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

async function deleteTemplate(row) {
  await ElMessageBox.confirm(`确定要删除模板「${row.name}」吗？`, '确认删除', { type: 'warning' })
  try {
    await api.delete(`/reports/export/templates/${row.id}`)
    ElMessage.success('模板已删除')
    await fetchTemplates()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function exportReport(type) {
  try {
    let url = ''
    let filename = ''
    if (type === 'roster') {
      url = '/reports/roster'
      filename = '花名册.xlsx'
    } else if (type === 'salary') {
      url = `/reports/salary/${salaryPeriod.value}`
      filename = `薪资核算表_${salaryPeriod.value}.xlsx`
    } else if (type === 'attendance') {
      url = `/reports/attendance/${attPeriod.value}`
      filename = `考勤表_${attPeriod.value}.xlsx`
    }

    const res = await api.get(url, { responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

async function exportSalaryByTemplate() {
  try {
    const params = {}
    if (selectedTemplate.value) {
      params.template_id = selectedTemplate.value
    }
    const res = await api.get(`/reports/salary-by-template/${salaryPeriod.value}`, { params, responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `薪资表_${salaryPeriod.value}.xlsx`
    link.click()
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchStats()
  fetchTemplates()
  fetchAvailableFields()
})
</script>
