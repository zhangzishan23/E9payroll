<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">考勤管理</h3>
      <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" @change="onPeriodChange" />
      <el-select v-model="filterField" placeholder="筛选字段" size="small" class="!w-24">
        <el-option label="员工编号" value="employee_no" />
        <el-option label="员工姓名" value="employee_name" />
      </el-select>
      <el-input v-model="filterValue" placeholder="筛选值" size="small" clearable class="!w-36" @input="fetchData" />
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">录入</el-button>
      <el-button :icon="Upload" size="small" @click="showImport">导入</el-button>
      <el-button type="success" :icon="Download" size="small" @click="handleExport">导出</el-button>
      <el-button type="warning" size="small" :loading="syncingAttendance" @click="syncAttendance">
        <el-icon class="mr-1"><Refresh /></el-icon>同步钉钉
      </el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
        删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
      </el-button>
      <el-divider direction="vertical" />
      <el-button size="small" :type="editMode ? 'warning' : 'default'" @click="toggleEditMode">
        {{ editMode ? '退出编辑' : '编辑' }}
      </el-button>
      <template v-if="editMode">
        <el-button type="primary" size="small" :loading="savingEdits" :disabled="changedSet.size === 0" @click="confirmEdits">
          保存{{ changedSet.size ? `(${changedSet.size})` : '' }}
        </el-button>
        <el-button size="small" :disabled="changedSet.size === 0" @click="cancelEdits">取消</el-button>
      </template>
    </div>

    <el-table :data="records" border stripe v-loading="loading" max-height="600" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="employee_no" label="员工编号" width="100" fixed />
      <el-table-column prop="employee_name" label="员工姓名" width="80" fixed />
      <el-table-column prop="total_work_days" label="总计薪天数" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].total_work_days" :min="0" :max="31" :precision="1" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.total_work_days != null ? row.total_work_days : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="actual_work_days" label="实际计薪天数" width="110">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].actual_work_days" :min="0" :max="31" :precision="1" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.actual_work_days != null ? row.actual_work_days : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="attendance_rate" label="出勤率" width="80">
        <template #default="{ row }">{{ row.attendance_rate != null ? (row.attendance_rate * 100).toFixed(1) + '%' : '' }}</template>
      </el-table-column>
      <el-table-column prop="late_count" label="迟到次数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].late_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.late_count != null ? row.late_count : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="early_count" label="早退次数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].early_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.early_count != null ? row.early_count : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="missed_punch_count" label="缺卡次数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].missed_punch_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.missed_punch_count != null ? row.missed_punch_count : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="sick_leave_days" label="病假天数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].sick_leave_days" :min="0" :precision="1" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.sick_leave_days != null ? row.sick_leave_days : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="personal_leave_days" label="事假天数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].personal_leave_days" :min="0" :precision="1" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.personal_leave_days != null ? row.personal_leave_days : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="annual_leave_days" label="年假天数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].annual_leave_days" :min="0" :precision="1" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.annual_leave_days != null ? row.annual_leave_days : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="other_leave_days" label="其他假天数" width="90">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].other_leave_days" :min="0" :precision="1" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.other_leave_days != null ? row.other_leave_days : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="verify_status" label="核实状态" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-select v-model="editCache[row.id].verify_status" size="small" class="cell-select" @change="markChanged(row.id)">
              <el-option label="待核实" value="待核实" />
              <el-option label="已核实" value="已核实" />
              <el-option label="异常已确认" value="异常已确认" />
            </el-select>
          </template>
          <template v-else>{{ row.verify_status || '' }}</template>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
      <template #default="{ row }">
        <div class="action-cell">
          <el-button v-if="row.id && !editMode" type="primary" link size="small" @click="showDialog(row)">编辑</el-button>
          <el-button v-else-if="!row.id && !editMode" type="success" link size="small" @click="showDialogForEmployee(row)">录入</el-button>
        </div>
      </template>
    </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑考勤' : '录入考勤'" width="600px" append-to-body>
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-form-item label="核算周期" required>
          <el-input v-model="form.period" placeholder="YYYYMM" />
        </el-form-item>
        <el-form-item label="员工编号">
          <el-input :model-value="formEmployeeNo" disabled />
        </el-form-item>
        <el-form-item label="总计薪天数" required>
          <el-input-number v-model="form.total_work_days" :min="0" :precision="1" class="w-full" />
        </el-form-item>
        <el-form-item label="实际计薪天数" required>
          <el-input-number v-model="form.actual_work_days" :min="0" :precision="1" class="w-full" />
        </el-form-item>
        <el-form-item label="迟到次数">
          <el-input-number v-model="form.late_count" :min="0" class="w-full" />
        </el-form-item>
        <el-form-item label="早退次数">
          <el-input-number v-model="form.early_count" :min="0" class="w-full" />
        </el-form-item>
        <el-form-item label="缺卡次数">
          <el-input-number v-model="form.missed_punch_count" :min="0" class="w-full" />
        </el-form-item>
        <el-form-item label="病假天数">
          <el-input-number v-model="form.sick_leave_days" :min="0" :precision="1" class="w-full" />
        </el-form-item>
        <el-form-item label="事假天数">
          <el-input-number v-model="form.personal_leave_days" :min="0" :precision="1" class="w-full" />
        </el-form-item>
        <el-form-item label="年假天数">
          <el-input-number v-model="form.annual_leave_days" :min="0" :precision="1" class="w-full" />
        </el-form-item>
        <el-form-item label="其他假天数">
          <el-input-number v-model="form.other_leave_days" :min="0" :precision="1" class="w-full" />
        </el-form-item>
        <el-form-item label="核实状态">
          <el-select v-model="form.verify_status" class="w-full">
            <el-option label="待核实" value="待核实" />
            <el-option label="已核实" value="已核实" />
            <el-option label="异常已确认" value="异常已确认" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入考勤" width="700px" append-to-body>
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
          支持 .xlsx / .xls 格式，表头需包含：员工编号、总计薪天数、实际计薪天数、迟到次数、早退次数、缺卡次数、病假天数、事假天数、年假天数、其他假天数、核实状态、备注
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
      <div class="mb-2 text-gray-600">以下考勤数据将被更新，请确认：</div>
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
import { Plus, Download, Upload, Delete, Refresh } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const savingEdits = ref(false)
const importing = ref(false)
const syncingAttendance = ref(false)
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
  total_work_days: '总计薪天数',
  actual_work_days: '实际计薪天数',
  late_count: '迟到次数',
  early_count: '早退次数',
  missed_punch_count: '缺卡次数',
  sick_leave_days: '病假天数',
  personal_leave_days: '事假天数',
  annual_leave_days: '年假天数',
  other_leave_days: '其他假天数',
  verify_status: '核实状态',
  remark: '备注'
}

const editFields = [
  'total_work_days', 'actual_work_days', 'late_count', 'early_count',
  'missed_punch_count', 'sick_leave_days', 'personal_leave_days',
  'annual_leave_days', 'other_leave_days', 'verify_status', 'remark'
]

const form = reactive({
  period: '202604', employee_id: null, total_work_days: 22, actual_work_days: 22,
  late_count: 0, early_count: 0, missed_punch_count: 0,
  sick_leave_days: 0, personal_leave_days: 0, annual_leave_days: 0, other_leave_days: 0,
  is_home_checkin: false, need_verify: false, verify_status: '已核实', remark: ''
})

function onPeriodChange(val) {
  periodDate.value = val
  fetchData()
}

function tableRowClassName({ row }) {
  if (editMode.value && row.id && changedSet.value.has(row.id)) return 'row-changed'
  return ''
}

function initEditCache() {
  records.value.forEach(row => {
    if (!row || !row.id) return
    editCache[row.id] = reactive({
      total_work_days: row.total_work_days ?? '',
      actual_work_days: row.actual_work_days ?? '',
      late_count: row.late_count ?? '',
      early_count: row.early_count ?? '',
      missed_punch_count: row.missed_punch_count ?? '',
      sick_leave_days: row.sick_leave_days ?? '',
      personal_leave_days: row.personal_leave_days ?? '',
      annual_leave_days: row.annual_leave_days ?? '',
      other_leave_days: row.other_leave_days ?? '',
      verify_status: row.verify_status ?? '',
      remark: row.remark ?? ''
    })
  })
}

function markChanged(rowId) {
  changedSet.value = new Set(changedSet.value)
  changedSet.value.add(rowId)
}

function toggleEditMode() {
  try {
    if (editMode.value) {
      editMode.value = false
      changedSet.value = new Set()
      for (const key of Object.keys(editCache)) {
        delete editCache[key]
      }
      return
    }
    initEditCache()
    editMode.value = true
    changedSet.value = new Set()
  } catch (e) {
    console.error('切换编辑模式失败：', e)
    ElMessage.error('切换编辑模式失败，请刷新页面后重试')
  }
}

function cancelEdits() {
  editMode.value = false
  changedSet.value = new Set()
  for (const key of Object.keys(editCache)) {
    delete editCache[key]
  }
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
    editFields.forEach(field => {
      const oldVal = row[field]
      const newVal = editCache[id]?.[field]
      if (String(oldVal ?? '') !== String(newVal ?? '')) {
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
      editFields.forEach(field => {
        if (cache[field] != null && cache[field] !== '') payload[field] = cache[field]
      })
      try {
        await api.put(`/attendance/${row.id}`, payload)
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
    changedSet.value = new Set()
    for (const key of Object.keys(editCache)) {
      delete editCache[key]
    }
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
    const params = { period: periodDate.value }
    if (filterField.value && filterValue.value) {
      params.filter_field = filterField.value
      params.filter_value = filterValue.value
    }
    const res = await api.get('/attendance/', { params })
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
      total_work_days: row.total_work_days, actual_work_days: row.actual_work_days,
      late_count: row.late_count ?? 0, early_count: row.early_count ?? 0,
      missed_punch_count: row.missed_punch_count ?? 0,
      sick_leave_days: row.sick_leave_days ?? 0, personal_leave_days: row.personal_leave_days ?? 0,
      annual_leave_days: row.annual_leave_days ?? 0, other_leave_days: row.other_leave_days ?? 0,
      is_home_checkin: row.is_home_checkin ?? false, need_verify: row.need_verify ?? false,
      verify_status: row.verify_status || '已核实', remark: row.remark || ''
    })
  } else {
    Object.assign(form, {
      period: periodDate.value, employee_id: null, total_work_days: 22, actual_work_days: 22,
      late_count: 0, early_count: 0, missed_punch_count: 0,
      sick_leave_days: 0, personal_leave_days: 0, annual_leave_days: 0, other_leave_days: 0,
      is_home_checkin: false, need_verify: false, verify_status: '已核实', remark: ''
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
    period: periodDate.value, employee_id: row.employee_id, total_work_days: 22, actual_work_days: 22,
    late_count: 0, early_count: 0, missed_punch_count: 0,
    sick_leave_days: 0, personal_leave_days: 0, annual_leave_days: 0, other_leave_days: 0,
    is_home_checkin: false, need_verify: false, verify_status: '已核实', remark: ''
  })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/attendance/${editId.value}`, form)
      ElMessage.success('编辑成功')
    } else {
      await api.post('/attendance/', form)
      ElMessage.success('录入成功')
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

async function handleExport() {
  try {
    const res = await api.get('/attendance/export', { params: { period: periodDate.value }, responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `考勤数据_${periodDate.value}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

async function syncAttendance() {
  syncingAttendance.value = true
  try {
    const period = periodDate.value
    const res = await api.post('/dingtalk/sync/attendance', null, { params: { period } })
    const data = res.data
    if (data.errors && data.errors.length) {
      ElMessage.warning(`同步完成：${data.message}，但有${data.errors.length}个错误`)
    } else {
      ElMessage.success(`钉钉考勤同步完成：${data.message}`)
    }
    await fetchData()
  } catch (e) {
    ElMessage.error('同步失败：' + (e.response?.data?.detail || e.message))
  } finally {
    syncingAttendance.value = false
  }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的考勤记录')
    return
  }
  await ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 条考勤记录吗？`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.filter(r => r.id).map(r => r.id)
    if (!ids.length) {
      ElMessage.warning('选中的记录中没有可删除的已录入数据')
      return
    }
    await api.post('/attendance/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 条考勤记录`)
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
    const res = await api.post('/attendance/import', formData, {
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

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.action-cell {
  white-space: nowrap;
}
.cell-number {
  width: 100%;
}
.cell-number :deep(.el-input__wrapper) {
  padding: 0 4px;
}
.cell-select {
  width: 100%;
}
:deep(.row-changed) {
  background-color: #fef3c7 !important;
}
</style>