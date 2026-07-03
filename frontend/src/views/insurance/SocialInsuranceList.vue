<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-2 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">社保公积金管理</h3>
      <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" @change="onPeriodChange" />
      <el-select v-model="filterField" placeholder="筛选字段" size="small" class="!w-24">
        <el-option label="员工编号" value="employee_no" />
        <el-option label="员工姓名" value="employee_name" />
      </el-select>
      <el-input v-model="filterValue" placeholder="筛选值" size="small" clearable class="!w-36" @input="fetchData" />
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">录入</el-button>
      <el-button :icon="Upload" size="small" @click="showImport">导入</el-button>
      <el-button type="success" :icon="Download" size="small" @click="handleExport">导出</el-button>
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

    <div class="bg-blue-50 rounded-lg p-3 mb-4 text-sm text-gray-600 flex items-center gap-2">
      <el-icon><InfoFilled /></el-icon>
      <span>提示：不同城市的社保公积金基数、比例不同（北京/广州/邯郸/上海），请按各公司实际情况填写。</span>
    </div>

    <el-table :data="filteredRecords" border stripe v-loading="loading" max-height="600" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="employee_no" label="员工编号" width="100" fixed />
      <el-table-column prop="employee_name" label="员工姓名" width="80" fixed />
      <el-table-column prop="si_base" label="社保基数" width="110">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].si_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.si_base != null ? row.si_base : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="pension_personal" label="养老保险" width="95">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].pension_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.pension_personal != null ? row.pension_personal : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="unemployment_personal" label="失业保险" width="95">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].unemployment_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.unemployment_personal != null ? row.unemployment_personal : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="medical_personal" label="医疗保险" width="95">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].medical_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.medical_personal != null ? row.medical_personal : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="si_personal" label="社保个人" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].si_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.si_personal != null ? row.si_personal : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="si_company" label="社保公司" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].si_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.si_company != null ? row.si_company : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="pension_company" label="养老公司" width="95">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].pension_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.pension_company != null ? row.pension_company : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="unemployment_company" label="失业公司" width="95">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].unemployment_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.unemployment_company != null ? row.unemployment_company : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="medical_company" label="医疗公司" width="95">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].medical_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.medical_company != null ? row.medical_company : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="hf_base" label="公积金基数" width="110">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].hf_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.hf_base != null ? row.hf_base : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="hf_personal" label="公积金个人" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].hf_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.hf_personal != null ? row.hf_personal : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="hf_company" label="公积金公司" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].hf_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.hf_company != null ? row.hf_company : '' }}</template>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑社保公积金' : '录入社保公积金'" width="600px" append-to-body>
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-form-item label="核算周期" required>
          <el-input v-model="form.period" placeholder="YYYYMM" />
        </el-form-item>
        <el-form-item label="员工编号">
          <el-input :model-value="formEmployeeNo" disabled />
        </el-form-item>
        <el-form-item label="社保基数">
          <el-input-number v-model="form.si_base" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="养老保险个人">
          <el-input-number v-model="form.pension_personal" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="失业保险个人">
          <el-input-number v-model="form.unemployment_personal" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="医疗保险个人">
          <el-input-number v-model="form.medical_personal" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="社保个人合计">
          <el-input-number v-model="form.si_personal" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="养老保险公司">
          <el-input-number v-model="form.pension_company" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="失业保险公司">
          <el-input-number v-model="form.unemployment_company" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="医疗保险公司">
          <el-input-number v-model="form.medical_company" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="社保公司合计">
          <el-input-number v-model="form.si_company" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="公积金基数">
          <el-input-number v-model="form.hf_base" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="公积金个人">
          <el-input-number v-model="form.hf_personal" :min="0" :precision="2" class="w-full" />
        </el-form-item>
        <el-form-item label="公积金公司">
          <el-input-number v-model="form.hf_company" :min="0" :precision="2" class="w-full" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入社保公积金" width="700px" append-to-body>
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
          支持 .xlsx / .xls 格式，表头需包含：员工编号、社保基数、养老保险个人、失业保险个人、医疗保险个人、社保个人合计、养老保险公司、失业保险公司、医疗保险公司、社保公司合计、公积金基数、公积金个人、公积金公司
        </div>
        <div v-if="importResult" class="mt-3">
          <el-alert
            :type="importResult.created || importResult.updated ? 'success' : 'warning'"
            :title="importResult.message"
            :closable="false"
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editConfirmVisible" title="确认保存修改" width="600px" append-to-body>
      <div class="mb-2 text-gray-600">以下社保公积金数据将被更新，请确认：</div>
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
import { Plus, Download, Upload, Delete, InfoFilled } from '@element-plus/icons-vue'
import api from '../../api'

function getDefaultPeriod() {
  const now = new Date()
  const bjOffset = 8 * 60
  const localOffset = now.getTimezoneOffset()
  const bjTime = new Date(now.getTime() + (bjOffset + localOffset) * 60 * 1000)
  const year = bjTime.getFullYear()
  const month = bjTime.getMonth() + 1
  const day = bjTime.getDate()
  let targetYear, targetMonth
  if (day < 15) {
    if (month === 1) {
      targetYear = year - 1
      targetMonth = 12
    } else {
      targetYear = year
      targetMonth = month - 1
    }
  } else {
    targetYear = year
    targetMonth = month
  }
  return `${targetYear}${String(targetMonth).padStart(2, '0')}`
}

const defaultPeriod = getDefaultPeriod()

const loading = ref(false)
const saving = ref(false)
const savingEdits = ref(false)
const importing = ref(false)
const dialogVisible = ref(false)
const importVisible = ref(false)
const isEdit = ref(false)
const periodDate = ref(defaultPeriod)
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
  si_base: '社保基数', pension_personal: '养老保险个人', unemployment_personal: '失业保险个人',
  medical_personal: '医疗保险个人', si_personal: '社保个人合计',
  pension_company: '养老保险公司', unemployment_company: '失业保险公司', medical_company: '医疗保险公司',
  si_company: '社保公司合计',
  hf_base: '公积金基数', hf_personal: '公积金个人', hf_company: '公积金公司'
}

const editFields = ['si_base', 'pension_personal', 'unemployment_personal', 'medical_personal', 'si_personal',
  'pension_company', 'unemployment_company', 'medical_company', 'si_company',
  'hf_base', 'hf_personal', 'hf_company']

const form = reactive({
  period: defaultPeriod, employee_id: null,
  si_base: 0, pension_personal: 0, unemployment_personal: 0, medical_personal: 0,
  si_personal: 0, pension_company: 0, unemployment_company: 0, medical_company: 0,
  si_company: 0, hf_base: 0, hf_personal: 0, hf_company: 0
})

const filteredRecords = computed(() => {
  if (!filterField.value || !filterValue.value) return records.value
  const keyword = filterValue.value.toLowerCase()
  return records.value.filter(r => {
    const val = String(r[filterField.value] || '').toLowerCase()
    return val.includes(keyword)
  })
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
      si_base: row.si_base ?? 0,
      pension_personal: row.pension_personal ?? 0,
      unemployment_personal: row.unemployment_personal ?? 0,
      medical_personal: row.medical_personal ?? 0,
      si_personal: row.si_personal ?? 0,
      pension_company: row.pension_company ?? 0,
      unemployment_company: row.unemployment_company ?? 0,
      medical_company: row.medical_company ?? 0,
      si_company: row.si_company ?? 0,
      hf_base: row.hf_base ?? 0,
      hf_personal: row.hf_personal ?? 0,
      hf_company: row.hf_company ?? 0
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

  const items = []
  changedSet.value.forEach(id => {
    const row = records.value.find(r => r.id === id)
    if (!row) return
    const changes = []
    editFields.forEach(f => {
      const oldVal = row[f] ?? 0
      const newVal = editCache[id]?.[f] ?? 0
      if (Math.abs(oldVal - newVal) > 0.001) {
        changes.push({
          field: f,
          label: fieldLabels[f] || f,
          old: oldVal.toFixed(2),
          new: newVal.toFixed(2)
        })
      }
    })
    if (changes.length) {
      items.push({ id, employee_name: row.employee_name, employee_no: row.employee_no, changes })
    }
  })

  if (!items.length) {
    ElMessage.warning('没有检测到实际修改')
    return
  }

  confirmList.value = items
  editConfirmVisible.value = true
}

async function saveAllEdits() {
  savingEdits.value = true
  let successCount = 0
  let failCount = 0

  try {
    for (const item of confirmList.value) {
      const cache = editCache[item.id]
      if (!cache) continue
      const payload = {}
      editFields.forEach(f => {
        payload[f] = cache[f]
      })
      try {
        await api.put(`/social-insurance/${item.id}`, payload)
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
  } finally {
    savingEdits.value = false
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params = { period: periodDate.value }
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get('/social-insurance/', { params })
    records.value = res.data
  } catch {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedRows.value.length} 条社保公积金记录？此操作不可恢复`, '批量删除', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  loading.value = true
  let successCount = 0
  for (const row of selectedRows.value) {
    try {
      await api.delete(`/social-insurance/${row.id}`)
      successCount++
    } catch {
      // skip
    }
  }
  ElMessage.success(`成功删除 ${successCount} 条记录`)
  await fetchData()
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  formEmployeeId.value = row?.employee_id || null
  formEmployeeNo.value = row?.employee_no || ''

  if (row) {
    form.period = row.period || periodDate.value
    form.employee_id = row.employee_id
    editFields.forEach(f => { form[f] = row[f] ?? 0 })
  } else {
    form.period = periodDate.value
    form.employee_id = null
    editFields.forEach(f => { form[f] = 0 })
  }
  dialogVisible.value = true
}

function showDialogForEmployee(row) {
  isEdit.value = false
  editId.value = null
  formEmployeeId.value = row.employee_id
  formEmployeeNo.value = row.employee_no
  form.period = periodDate.value
  form.employee_id = row.employee_id
  editFields.forEach(f => { form[f] = 0 })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.period) {
    ElMessage.warning('请输入核算周期')
    return
  }
  saving.value = true
  try {
    const payload = {
      period: form.period,
      employee_id: form.employee_id,
      si_base: form.si_base,
      pension_personal: form.pension_personal,
      unemployment_personal: form.unemployment_personal,
      medical_personal: form.medical_personal,
      si_personal: form.si_personal,
      pension_company: form.pension_company,
      unemployment_company: form.unemployment_company,
      medical_company: form.medical_company,
      si_company: form.si_company,
      hf_base: form.hf_base,
      hf_personal: form.hf_personal,
      hf_company: form.hf_company
    }

    if (isEdit.value) {
      await api.put(`/social-insurance/${editId.value}`, payload)
      ElMessage.success('修改成功')
    } else {
      await api.post('/social-insurance/', payload)
      ElMessage.success('录入成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e) {
    const msg = e.response?.data?.detail || '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
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
}

async function doImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    const res = await api.post(`/social-insurance/import/${periodDate.value}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    importResult.value = res.data
    ElMessage.success(res.data.message)
    await fetchData()
  } catch (e) {
    const msg = e.response?.data?.detail || '导入失败'
    ElMessage.error(msg)
  } finally {
    importing.value = false
  }
}

async function handleExport() {
  try {
    const params = {}
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get(`/social-insurance/export/${periodDate.value}`, { params, responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `社保公积金_${periodDate.value}.xlsx`
    link.click()
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
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
.cell-number :deep(.el-input__inner) {
  text-align: right;
}
:deep(.row-changed) {
  background-color: #fef3c7 !important;
}
</style>