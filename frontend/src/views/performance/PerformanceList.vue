<template>
  <div class="apple-card p-6">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold text-gray-700">绩效数据管理</h3>
      <div class="flex gap-3">
        <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" class="w-36" value-format="YYYYMM" @change="onPeriodChange" />
        <el-select v-model="filterField" placeholder="筛选字段" class="w-28">
          <el-option label="员工编号" value="employee_no" />
          <el-option label="员工姓名" value="employee_name" />
        </el-select>
        <el-input v-model="filterValue" placeholder="输入筛选值" clearable class="w-40" @input="applyFilter" />
        <el-button type="primary" :icon="Plus" @click="showDialog(null)">录入绩效</el-button>
        <el-button :icon="Upload" @click="showImport">批量导入</el-button>
        <el-button type="success" :icon="Download" @click="handleExport">导出</el-button>
        <el-button type="danger" :icon="Delete" :disabled="!selectedRows.length" @click="handleBatchDelete">
          批量删除 {{ selectedRows.length ? `(${selectedRows.length})` : '' }}
        </el-button>
        <el-divider direction="vertical" />
        <el-button
          :type="editMode ? 'warning' : 'default'"
          @click="toggleEditMode"
        >
          {{ editMode ? '退出编辑模式' : '开启编辑模式' }}
        </el-button>
        <template v-if="editMode">
          <el-button type="primary" :loading="savingEdits" :disabled="changedSet.size === 0" @click="confirmEdits">
            保存修改 {{ changedSet.size ? `(${changedSet.size})` : '' }}
          </el-button>
          <el-button :disabled="changedSet.size === 0" @click="cancelEdits">取消修改</el-button>
        </template>
      </div>
    </div>

    <el-table :data="filteredRecords" border stripe v-loading="loading" max-height="600" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="employee_no" label="员工编号" width="100" fixed />
      <el-table-column prop="employee_name" label="员工姓名" width="80" fixed />
      <el-table-column prop="initial_score" label="初评分数" width="100">
        <template #default="{ row }">
          <template v-if="editMode && row.id">
            <el-input-number v-model="editCache[row.id].initial_score" :min="0" :max="100" :precision="1" size="small" :controls="false" class="cell-input" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.initial_score != null ? row.initial_score : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="final_score" label="复评分数" width="100">
        <template #default="{ row }">
          <template v-if="editMode && row.id">
            <el-input-number v-model="editCache[row.id].final_score" :min="0" :max="100" :precision="1" size="small" :controls="false" class="cell-input" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.final_score != null ? row.final_score : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="coefficient" label="绩效系数" width="100">
        <template #default="{ row }">
          <template v-if="editMode && row.id">
            <el-input-number v-model="editCache[row.id].coefficient" :min="0" :max="3" :precision="2" :step="0.1" size="small" :controls="false" class="cell-input" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="row.coefficient >= 1 ? 'text-green-600' : 'text-red-600'" class="font-semibold">
              {{ row.coefficient != null ? row.coefficient.toFixed(2) : '1.00' }}
            </span>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.id && !editMode" type="primary" link size="small" @click="showDialog(row)">编辑</el-button>
          <el-button v-else-if="!row.id && !editMode" type="success" link size="small" @click="showDialogForEmployee(row)">录入</el-button>
          <el-button v-if="row.id && !editMode" type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑绩效' : '录入绩效'" width="550px" append-to-body>
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-form-item label="核算周期" required>
          <el-input :model-value="form.period" disabled />
        </el-form-item>
        <el-form-item label="员工编号">
          <el-input :model-value="formEmployeeNo" disabled />
        </el-form-item>
        <el-form-item label="初评分数">
          <el-input-number v-model="form.initial_score" :min="0" :max="100" :precision="1" class="w-full" />
        </el-form-item>
        <el-form-item label="复评分数">
          <el-input-number v-model="form.final_score" :min="0" :max="100" :precision="1" class="w-full" />
        </el-form-item>
        <el-form-item label="绩效系数" required>
          <el-input-number v-model="form.coefficient" :min="0" :max="3" :precision="2" :step="0.1" class="w-full" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入绩效数据" width="700px" append-to-body>
      <div class="mb-4">
        <div class="flex gap-3 mb-3">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".xlsx,.xls"
            :on-change="handleFileChange"
            :file-list="fileList"
          >
            <el-button type="primary">选择 Excel 文件</el-button>
          </el-upload>
          <el-button type="success" :loading="importing" :disabled="!importFile" @click="doImport">
            开始导入
          </el-button>
        </div>
        <div class="text-sm text-gray-500">
          支持 .xlsx / .xls 格式，表头需包含：员工编号、初评分数、复评分数、绩效系数
        </div>
        <div v-if="importResult" class="mt-3">
          <el-alert
            :type="importResult.errors && importResult.errors.length ? 'warning' : 'success'"
            :title="importResult.message"
            :closable="false"
          />
          <div v-if="importResult.errors && importResult.errors.length" class="mt-2 text-sm text-red-500">
            <div v-for="(err, i) in importResult.errors" :key="i">{{ err }}</div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editConfirmVisible" title="确认保存修改" width="600px" append-to-body>
      <div class="mb-2 text-gray-600">以下绩效数据将被更新，请确认：</div>
      <el-table :data="confirmList" border stripe max-height="400">
        <el-table-column prop="employee_name" label="姓名" width="80" />
        <el-table-column label="修改字段" min-width="200">
          <template #default="{ row }">
            <div v-for="(change, idx) in row.changes" :key="idx" class="text-sm">
              <span class="text-gray-500">{{ change.label }}：</span>
              <span class="text-red-400 line-through mr-1">{{ change.old }}</span>
              <span class="text-green-600 font-medium">{{ change.new }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="editConfirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdits" @click="saveAllEdits">确认保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Delete } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const savingEdits = ref(false)
const importing = ref(false)
const dialogVisible = ref(false)
const importVisible = ref(false)
const isEdit = ref(false)
const periodDate = ref('202604')
const filterField = ref('')
const filterValue = ref('')
const records = ref([])
const selectedRows = ref([])
const importFile = ref(null)
const fileList = ref([])
const importResult = ref(null)
const uploadRef = ref(null)
const formRef = ref(null)
const editId = ref(null)
const formEmployeeId = ref(null)
const formEmployeeNo = ref('')

const editMode = ref(false)
const editCache = reactive({})
const changedSet = ref(new Set())
const editConfirmVisible = ref(false)
const confirmList = ref([])

const fieldLabels = {
  initial_score: '初评分数',
  final_score: '复评分数',
  coefficient: '绩效系数'
}

const form = reactive({
  period: '202604', employee_id: null,
  initial_score: null, final_score: null, coefficient: 1.00
})

const filteredRecords = computed(() => {
  if (!filterField.value || !filterValue.value) return records.value
  const fv = filterValue.value.toLowerCase()
  return records.value.filter(r => {
    if (filterField.value === 'employee_no') return (r.employee_no || '').toLowerCase().includes(fv)
    if (filterField.value === 'employee_name') return (r.employee_name || '').toLowerCase().includes(fv)
    return true
  })
})

function onPeriodChange(val) {
  periodDate.value = val
  fetchData()
}

function applyFilter() {
}

function tableRowClassName({ row }) {
  if (editMode.value && row.id && changedSet.value.has(row.id)) return 'row-changed'
  return ''
}

function initEditCache() {
  Object.keys(editCache).forEach(k => delete editCache[k])
  changedSet.value = new Set()
  records.value.forEach(row => {
    if (!row.id) return
    editCache[row.id] = {
      initial_score: row.initial_score ?? null,
      final_score: row.final_score ?? null,
      coefficient: row.coefficient ?? 0
    }
  })
}

function markChanged(rowId) {
  changedSet.value = new Set(changedSet.value)
  changedSet.value.add(rowId)
}

function toggleEditMode() {
  if (editMode.value) {
    editMode.value = false
    Object.keys(editCache).forEach(k => delete editCache[k])
    changedSet.value = new Set()
    return
  }
  initEditCache()
  editMode.value = true
}

function cancelEdits() {
  editMode.value = false
  Object.keys(editCache).forEach(k => delete editCache[k])
  changedSet.value = new Set()
}

function confirmEdits() {
  if (!changedSet.value.size) {
    ElMessage.warning('没有检测到任何修改')
    return
  }

  const rows = []
  changedSet.value.forEach(id => {
    const row = records.value.find(r => r.id === id)
    if (!row) return
    const changes = []
    Object.keys(fieldLabels).forEach(field => {
      const oldVal = row[field]
      const newVal = editCache[id]?.[field]
      if (oldVal !== newVal) {
        changes.push({
          field,
          label: fieldLabels[field],
          old: oldVal != null ? String(oldVal) : '(空)',
          new: newVal != null ? String(newVal) : '(空)'
        })
      }
    })
    if (changes.length) {
      rows.push({
        id,
        employee_name: row.employee_name,
        employee_no: row.employee_no,
        changes
      })
    }
  })

  confirmList.value = rows
  editConfirmVisible.value = true
}

async function saveAllEdits() {
  savingEdits.value = true
  let successCount = 0
  let failCount = 0

  try {
    for (const row of confirmList.value) {
      const cache = editCache[row.id]
      if (!cache) continue
      const payload = {}
      Object.keys(fieldLabels).forEach(field => {
        if (cache[field] != null) payload[field] = cache[field]
      })
      try {
        await api.put(`/performance/${row.id}`, payload)
        successCount++
      } catch {
        failCount++
      }
    }

    if (failCount === 0) {
      ElMessage.success(`修改成功！共更新 ${successCount} 条记录`)
    } else {
      ElMessage.warning(`部分成功：${successCount} 条已更新，${failCount} 条失败`)
    }

    editConfirmVisible.value = false
    editMode.value = false
    Object.keys(editCache).forEach(k => delete editCache[k])
    changedSet.value = new Set()
    await fetchData()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    savingEdits.value = false
  }
}

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get('/performance/', { params: { period: periodDate.value } })
    records.value = res.data
  } finally {
    loading.value = false
  }
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  formEmployeeId.value = row?.employee_id || null
  formEmployeeNo.value = row?.employee_no || ''
  if (row) {
    Object.assign(form, {
      period: row.period, employee_id: row.employee_id,
      initial_score: row.initial_score, final_score: row.final_score,
      coefficient: row.coefficient ?? 1.00
    })
  } else {
    Object.assign(form, {
      period: periodDate.value, employee_id: null,
      initial_score: null, final_score: null, coefficient: 1.00
    })
  }
  dialogVisible.value = true
}

function showDialogForEmployee(row) {
  isEdit.value = false
  editId.value = null
  formEmployeeId.value = row.employee_id
  formEmployeeNo.value = row.employee_no
  Object.assign(form, {
    period: periodDate.value, employee_id: row.employee_id,
    initial_score: null, final_score: null, coefficient: 1.00
  })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/performance/${editId.value}`, {
        initial_score: form.initial_score,
        final_score: form.final_score,
        coefficient: form.coefficient
      })
      ElMessage.success('编辑成功')
    } else {
      await api.post('/performance/', {
        period: form.period,
        employee_id: form.employee_id,
        initial_score: form.initial_score,
        final_score: form.final_score,
        coefficient: form.coefficient
      })
      ElMessage.success('录入成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.employee_name}」的绩效记录？`, '确认删除', {
    type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消'
  })
  try {
    await api.delete(`/performance/${row.id}`)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的绩效记录')
    return
  }
  await ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 条绩效记录吗？`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.filter(r => r.id).map(r => r.id)
    if (!ids.length) {
      ElMessage.warning('选中的记录中没有可删除的已录入数据')
      return
    }
    await api.post('/performance/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 条绩效记录`)
    selectedRows.value = []
    fetchData()
  } catch (e) {
    ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

function showImport() {
  importFile.value = null
  fileList.value = []
  importResult.value = null
  importVisible.value = true
}

function handleFileChange(file) {
  importFile.value = file.raw
  importResult.value = null
}

async function doImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择 Excel 文件')
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    formData.append('period', periodDate.value)
    const res = await api.post('/performance/import-excel', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    importResult.value = res.data
    if (!res.data.errors || !res.data.errors.length) {
      ElMessage.success(res.data.message)
      importVisible.value = false
      fetchData()
    }
  } catch (e) {
    ElMessage.error('导入失败：' + (e.response?.data?.detail || '请检查文件格式'))
  } finally {
    importing.value = false
  }
}

async function handleExport() {
  try {
    const res = await api.get(`/performance/export/${periodDate.value}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `绩效数据_${periodDate.value}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.cell-input {
  width: 100%;
}
.cell-input :deep(.el-input__wrapper) {
  padding: 0 4px;
}
:deep(.row-changed) {
  background-color: #fef3c7 !important;
}
</style>