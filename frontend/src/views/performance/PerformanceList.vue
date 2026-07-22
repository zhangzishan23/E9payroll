<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">绩效数据管理</h3>
      <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" @change="onPeriodChange" />
      <el-select v-model="filterField" placeholder="筛选字段" size="small" class="!w-24">
        <el-option label="员工姓名" value="employee_name" />
      </el-select>
      <el-input v-model="filterValue" placeholder="筛选值" size="small" clearable class="!w-36" @input="applyFilter" />
      <el-button :icon="Upload" size="small" @click="showImport" v-permission="'performance:import'">导入</el-button>
      <el-button type="success" :icon="Download" size="small" @click="handleExport" v-permission="'performance:export'">导出</el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete" v-permission="'performance:delete'">
        删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
      </el-button>
      <el-divider direction="vertical" />
      <el-button size="small" :type="editMode ? 'warning' : 'default'" @click="toggleEditMode" v-permission="'performance:edit'">
        {{ editMode ? '退出编辑' : '编辑' }}
      </el-button>
      <ColumnSetting
        :columns="TABLE_COLUMNS"
        :default-visible-keys="DEFAULT_VISIBLE_COLUMNS"
        v-model="visibleColumns"
        storage-key="performance_table_columns"
      />
      <template v-if="editMode">
        <el-button type="primary" size="small" :loading="savingEdits" :disabled="changedSet.size === 0" @click="confirmEdits" v-permission="'performance:edit'">
          保存{{ changedSet.size ? `(${changedSet.size})` : '' }}
        </el-button>
        <el-button size="small" :disabled="changedSet.size === 0" @click="cancelEdits">取消</el-button>
      </template>
    </div>

    <el-table :data="filteredRecords" border stripe v-loading="loading" max-height="600" table-layout="fixed" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
      <el-table-column v-if="isColumnVisible('selection')" type="selection" width="55" fixed="left" />
      <el-table-column v-if="isColumnVisible('index')" type="index" label="序号" width="50" fixed="left" />
      <el-table-column v-if="isColumnVisible('employee_name')" prop="employee_name" label="姓名" width="80" fixed="left" />
      <el-table-column v-if="isColumnVisible('contract_company')" prop="contract_company" label="合同公司" width="120" show-overflow-tooltip />
      <el-table-column v-if="isColumnVisible('department')" prop="department" label="部门" width="120" show-overflow-tooltip />
      <el-table-column v-if="isColumnVisible('position')" prop="position" label="职务" width="120" show-overflow-tooltip />
      <el-table-column v-if="isColumnVisible('total_work_days')" prop="total_work_days" label="应计薪天数" width="120" align="center">
        <template #default="{ row }">{{ formatInt(row.total_work_days) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('actual_work_days')" prop="actual_work_days" label="实际计薪天数" width="120" align="center">
        <template #default="{ row }">{{ formatInt(row.actual_work_days) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('attendance_rate')" label="出勤率" width="90" align="center">
        <template #default="{ row }">
          <span>{{ formatPercent(row.attendance_rate) }}</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('performance_standard')" prop="performance_standard" label="绩效奖金标准" width="120" align="right">
        <template #default="{ row }">{{ formatMoney(getRowPerfStd(row)) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('performance_category')" prop="performance_category" label="绩效类别" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.employee_id]">
            <el-input v-model="editCache[row.employee_id].performance_category" size="small" placeholder="类别" @change="markChanged(row.employee_id)" />
          </template>
          <template v-else>{{ row.performance_category || '' }}</template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('initial_score')" prop="initial_score" label="初评" width="90" align="center">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.employee_id]">
            <el-input-number v-model="editCache[row.employee_id].initial_score" :min="0" :max="3" :precision="2" :step="0.1" size="small" controls-position="right" class="cell-number" @change="(val) => onTableInitialScoreChange(row.employee_id, val)" />
          </template>
          <template v-else>{{ formatNumber(row.initial_score, 2) }}</template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('final_score')" prop="final_score" label="复评（绩效系数）" width="130" align="center">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.employee_id]">
            <el-input-number v-model="editCache[row.employee_id].final_score" :min="0" :max="3" :precision="2" :step="0.1" size="small" controls-position="right" class="cell-number" @change="markChanged(row.employee_id)" />
          </template>
          <template v-else>
            <span v-if="getRowCoefficient(row) != null" :class="(getRowCoefficient(row)) >= 1 ? 'text-green-600' : 'text-red-600'" class="font-semibold">
              {{ formatNumber(getRowCoefficient(row), 2) }}
            </span>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('evaluated')" label="评价后绩效标准" width="130" align="right">
        <template #default="{ row }">
          <span v-if="getRowEvaluated(row) != null" class="font-medium">{{ formatMoney(getRowEvaluated(row)) }}</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('diff')" label="差额" width="100" align="right">
        <template #default="{ row }">
          <span v-if="getRowDiff(row) != null" :class="getRowDiff(row) > 0 ? 'text-green-500' : getRowDiff(row) < 0 ? 'text-red-500' : ''">
            {{ formatMoney(getRowDiff(row)) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('actual_paid')" label="实发绩效金额" width="120" align="right">
        <template #default="{ row }">
          <span v-if="getRowActualPaid(row) != null" class="font-semibold text-purple-600">{{ formatMoney(getRowActualPaid(row)) }}</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('score_diff')" label="调整差异" width="100" align="center">
        <template #default="{ row }">
          <span :class="getRowScoreDiff(row) != null && getRowScoreDiff(row) !== 0 ? (getRowScoreDiff(row) > 0 ? 'text-green-500' : 'text-red-500') : ''">
            {{ formatNumber(getRowScoreDiff(row), 2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('score_reason')" prop="score_reason" label="评分理由" width="260">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.employee_id]">
            <el-input
              v-model="editCache[row.employee_id].score_reason"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              size="small"
              placeholder="评分理由"
              @change="markChanged(row.employee_id)"
              resize="none"
            />
          </template>
          <template v-else>
            <el-tooltip
              v-if="row.score_reason"
              :content="row.score_reason"
              placement="bottom"
              :show-after="300"
              popper-class="performance-tooltip"
              :offset="8"
            >
              <div class="text-ellipsis-cell">{{ row.score_reason }}</div>
            </el-tooltip>
            <span v-else></span>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('review_note')" prop="review_note" label="分管领导审核后调整" width="280">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.employee_id]">
            <el-input
              v-model="editCache[row.employee_id].review_note"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              size="small"
              placeholder="调整说明"
              @change="markChanged(row.employee_id)"
              resize="none"
            />
          </template>
          <template v-else>
            <el-tooltip
              v-if="row.review_note"
              :content="row.review_note"
              placement="bottom"
              :show-after="300"
              popper-class="performance-tooltip"
              :offset="8"
            >
              <div class="text-ellipsis-cell">{{ row.review_note }}</div>
            </el-tooltip>
            <span v-else></span>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('action')" label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button v-if="row.id && !editMode" type="primary" link size="small" @click="showDialog(row)" v-permission="'performance:edit'">编辑</el-button>
            <el-button v-else-if="!row.id && !editMode" type="success" link size="small" @click="showDialogForEmployee(row)" v-permission="'performance:create'">录入</el-button>
            <el-button v-if="row.id && !editMode" type="danger" link size="small" @click="handleDelete(row)" v-permission="'performance:delete'">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑绩效' : '录入绩效'" width="600px" append-to-body>
      <el-form ref="formRef" :model="form" label-width="140px">
        <el-form-item label="核算周期" required>
          <el-input :model-value="form.period" disabled />
        </el-form-item>
        <el-form-item label="员工姓名">
          <el-input :model-value="formEmployeeName" disabled />
        </el-form-item>
        <el-form-item label="绩效类别">
          <el-input v-model="form.performance_category" placeholder="如：A/B/C等" />
        </el-form-item>
        <el-form-item label="初评">
          <el-input-number v-model="form.initial_score" :min="0" :max="3" :precision="2" :step="0.1" class="w-full" @change="onInitialScoreChange" />
        </el-form-item>
        <el-form-item label="复评（绩效系数）">
          <el-input-number v-model="form.final_score" :min="0" :max="3" :precision="2" :step="0.1" class="w-full" />
        </el-form-item>
        <el-form-item label="绩效奖金标准">
          <el-input :model-value="(formRow?.performance_standard || 0).toFixed(2)" disabled />
        </el-form-item>
        <el-form-item label="评价后绩效标准">
          <el-input :model-value="form.final_score != null ? ((formRow?.performance_standard || 0) * form.final_score).toFixed(2) : ''" disabled />
        </el-form-item>
        <el-form-item label="差额">
          <el-input :model-value="form.final_score != null ? ((((formRow?.performance_standard || 0) * form.final_score) - (formRow?.performance_standard || 0))).toFixed(2) : ''" disabled />
        </el-form-item>
        <el-form-item label="出勤率">
          <el-input :model-value="formRow?.attendance_rate != null ? ((formRow.attendance_rate * 100).toFixed(1) + '%') : '暂无考勤数据'" disabled />
        </el-form-item>
        <el-form-item label="实发绩效金额">
          <el-input :model-value="getFormActualPaid().toFixed(2)" disabled />
        </el-form-item>
        <el-form-item v-if="form.initial_score != null && form.final_score != null" label="调整差异">
          <el-input :model-value="(form.final_score - (form.initial_score || 0)).toFixed(2)" disabled />
        </el-form-item>
        <el-form-item label="评分理由">
          <el-input v-model="form.score_reason" type="textarea" :rows="4" placeholder="请输入评分理由" />
        </el-form-item>
        <el-form-item label="分管领导审核后调整">
          <el-input v-model="form.review_note" type="textarea" :rows="4" placeholder="审核调整说明（可选）" />
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
          支持 .xlsx / .xls 格式，<span class="text-blue-600 font-medium">表头需在第一行</span>，需包含：姓名；可选列：初评、复评（绩效系数，留空则默认等于初评）、绩效类别、评分理由、分管领导审核后调整。
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

    <el-dialog v-model="editConfirmVisible" title="确认保存修改" width="650px" append-to-body>
      <div class="mb-2 text-gray-600">以下绩效数据将被更新，请确认：</div>
      <el-table :data="confirmList" border stripe max-height="400">
        <el-table-column prop="employee_name" label="姓名" width="80" />
        <el-table-column label="修改字段" min-width="300">
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
import { Download, Upload, Delete } from '@element-plus/icons-vue'
import api from '../../api'
import ColumnSetting from '../../components/ColumnSetting.vue'
import { formatNumber, formatInt, formatMoney, formatPercent } from '../../utils/format'

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
const formEmployeeName = ref('')
const formRow = ref(null)

const editMode = ref(false)
const editCache = reactive({})
const changedSet = ref(new Set())
const editConfirmVisible = ref(false)
const confirmList = ref([])

const TABLE_COLUMNS = [
  { key: 'selection', label: '选择', required: true },
  { key: 'index', label: '序号', required: true },
  { key: 'employee_name', label: '姓名', required: true },
  { key: 'contract_company', label: '合同公司' },
  { key: 'department', label: '部门' },
  { key: 'position', label: '职务' },
  { key: 'total_work_days', label: '应计薪天数' },
  { key: 'actual_work_days', label: '实际计薪天数' },
  { key: 'attendance_rate', label: '出勤率' },
  { key: 'performance_standard', label: '绩效奖金标准' },
  { key: 'performance_category', label: '绩效类别' },
  { key: 'initial_score', label: '初评' },
  { key: 'final_score', label: '复评绩效系数' },
  { key: 'evaluated', label: '评价后绩效标准' },
  { key: 'diff', label: '差额' },
  { key: 'actual_paid', label: '实发绩效金额' },
  { key: 'score_diff', label: '调整差异' },
  { key: 'score_reason', label: '评分理由' },
  { key: 'review_note', label: '分管领导审核后调整' },
  { key: 'action', label: '操作', required: true },
]

const DEFAULT_VISIBLE_COLUMNS = [
  'selection', 'index', 'employee_name', 'department',
  'total_work_days', 'attendance_rate', 'performance_standard',
  'performance_category', 'final_score', 'actual_paid', 'action'
]

const visibleColumns = ref([])

function isColumnVisible(key) {
  return visibleColumns.value.includes(key)
}

const fieldLabels = {
  initial_score: '初评',
  final_score: '复评（绩效系数）',
  performance_category: '绩效类别',
  score_reason: '评分理由',
  review_note: '分管领导审核后调整'
}

const form = reactive({
  period: defaultPeriod, employee_id: null,
  initial_score: null, final_score: null,
  performance_category: '', score_reason: '', review_note: ''
})

const filteredRecords = computed(() => {
  if (!filterField.value || !filterValue.value) return records.value
  const fv = filterValue.value.toLowerCase()
  return records.value.filter(r => {
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
  if (editMode.value && row.employee_id && changedSet.value.has(row.employee_id)) return 'row-changed'
  return ''
}

function getCurrentVals(row) {
  const cache = editMode.value && editCache[row.employee_id] ? editCache[row.employee_id] : null
  const initial = cache ? cache.initial_score : row.initial_score
  let final = cache ? cache.final_score : (row.final_score != null ? Number(row.final_score) : null)
  if (final == null && initial != null) {
    final = Number(initial)
  }
  const perfStd = Number(row.performance_standard) || 0
  return { initial: initial != null ? Number(initial) : null, final: final, perfStd }
}

function getRowPerfStd(row) {
  const val = Number(row.performance_standard)
  return val || null
}

function getRowCoefficient(row) {
  const { final } = getCurrentVals(row)
  return final != null ? Number(final) : null
}

function getRowEvaluated(row) {
  const { final, perfStd } = getCurrentVals(row)
  if (final == null) return null
  const result = perfStd * Number(final)
  return result === 0 ? null : result
}

function getRowDiff(row) {
  const { final, perfStd } = getCurrentVals(row)
  if (final == null) return null
  const result = perfStd * Number(final) - perfStd
  return result === 0 ? null : result
}

function getRowScoreDiff(row) {
  const { initial, final } = getCurrentVals(row)
  if (initial == null || final == null) return null
  return Number(final) - Number(initial)
}

function getRowAttendanceRate(row) {
  const total = Number(row.total_work_days) || 0
  const actual = Number(row.actual_work_days) || 0
  if (total <= 0) return row.attendance_rate != null ? Number(row.attendance_rate) : null
  return actual / total
}

function getRowActualPaid(row) {
  const evaluated = getRowEvaluated(row)
  if (evaluated == null) return null
  const attRate = getRowAttendanceRate(row)
  const result = evaluated * attRate
  return result === 0 ? null : result
}

function getFormActualPaid() {
  const perfStd = Number(formRow.value?.performance_standard) || 0
  const coef = form.final_score != null ? Number(form.final_score) : null
  if (coef == null) return 0
  const attRate = formRow.value?.attendance_rate != null ? Number(formRow.value.attendance_rate) : 0
  return perfStd * coef * attRate
}

function initEditCache() {
  records.value.forEach(row => {
    if (!row || !row.employee_id) return
    const finalVal = row.final_score != null ? row.final_score : (row.initial_score != null ? row.initial_score : null)
    editCache[row.employee_id] = reactive({
      initial_score: row.initial_score ?? null,
      final_score: finalVal,
      performance_category: row.performance_category ?? '',
      score_reason: row.score_reason ?? '',
      review_note: row.review_note ?? ''
    })
    if (row.final_score == null && finalVal != null) {
      changedSet.value.add(row.employee_id)
    }
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
    changedSet.value = new Set()
    initEditCache()
    editMode.value = true
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
  changedSet.value.forEach(empId => {
    const row = records.value.find(r => r.employee_id === empId)
    if (!row) return
    const changes = []
    Object.keys(fieldLabels).forEach(field => {
      const oldVal = row[field]
      const newVal = editCache[empId]?.[field]
      const oldStr = oldVal != null && oldVal !== '' ? String(oldVal) : '(空)'
      const newStr = newVal != null && newVal !== '' ? String(newVal) : '(空)'
      if (oldStr !== newStr) {
        changes.push({
          field,
          label: fieldLabels[field],
          old: oldStr,
          new: newStr
        })
      }
    })
    if (changes.length) {
      rows.push({
        id: row.id,
        employee_id: empId,
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
      const cache = editCache[row.employee_id]
      if (!cache) continue
      const payload = {}
      const changedFields = new Set(row.changes.map(c => c.field))
      Object.keys(fieldLabels).forEach(field => {
        if (!changedFields.has(field)) return
        const val = cache[field]
        if (val !== '' && val != null) {
          payload[field] = val
        }
      })
      let final_score = payload.final_score
      if (final_score == null && payload.initial_score != null) {
        final_score = payload.initial_score
        payload.final_score = final_score
      }
      if (!row.id && (payload.initial_score == null && payload.final_score == null)) {
        ElMessage.warning(`员工「${row.employee_name}」未填写初评或复评分数，跳过保存`)
        failCount++
        continue
      }
      try {
        if (row.id) {
          await api.put(`/performance/${row.id}`, payload)
        } else {
          await api.post('/performance/', {
            period: periodDate.value,
            employee_id: row.employee_id,
            ...payload
          })
        }
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
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get('/performance/', { params })
    records.value = res.data
  } finally {
    loading.value = false
  }
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  formEmployeeId.value = row?.employee_id || null
  formEmployeeName.value = row?.employee_name || ''
  formRow.value = row
  if (row) {
    const finalScore = row.final_score != null ? row.final_score : (row.initial_score != null ? row.initial_score : null)
    Object.assign(form, {
      period: row.period, employee_id: row.employee_id,
      initial_score: row.initial_score,
      final_score: finalScore,
      performance_category: row.performance_category || '',
      score_reason: row.score_reason || '',
      review_note: row.review_note || ''
    })
  } else {
    Object.assign(form, {
      period: periodDate.value, employee_id: null,
      initial_score: null, final_score: null,
      performance_category: '', score_reason: '', review_note: ''
    })
  }
  dialogVisible.value = true
}

function showDialogForEmployee(row) {
  isEdit.value = false
  editId.value = null
  formEmployeeId.value = row.employee_id
  formEmployeeName.value = row.employee_name
  formRow.value = row
  Object.assign(form, {
    period: periodDate.value, employee_id: row.employee_id,
    initial_score: null, final_score: null,
    performance_category: '', score_reason: '', review_note: ''
  })
  dialogVisible.value = true
}

function onInitialScoreChange(val) {
  if (val != null && form.final_score == null) {
    form.final_score = val
  }
}

function onTableInitialScoreChange(empId, val) {
  if (val != null && editCache[empId] && editCache[empId].final_score == null) {
    editCache[empId].final_score = val
  }
  markChanged(empId)
}

async function handleSave() {
  if (form.initial_score == null && form.final_score == null) {
    ElMessage.warning('请至少填写初评或复评分数')
    return
  }
  let final_score = form.final_score
  if (final_score == null && form.initial_score != null) {
    final_score = form.initial_score
  }
  saving.value = true
  try {
    const payload = {
      initial_score: form.initial_score,
      final_score: final_score,
      performance_category: form.performance_category || null,
      score_reason: form.score_reason || null,
      review_note: form.review_note || null
    }
    if (isEdit.value) {
      await api.put(`/performance/${editId.value}`, payload)
      ElMessage.success('编辑成功')
    } else {
      await api.post('/performance/', {
        period: form.period,
        employee_id: form.employee_id,
        ...payload
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
    const params = {}
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get(`/performance/export/${periodDate.value}`, { params, responseType: 'blob' })
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
.action-cell {
  white-space: nowrap;
}
.cell-number {
  width: 100%;
}
.cell-number :deep(.el-input__wrapper) {
  padding: 0 4px;
}
:deep(.row-changed) {
  background-color: #fef3c7 !important;
}
.text-ellipsis-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  width: 100%;
  display: block;
}
:deep(.el-textarea__inner) {
  line-height: 1.4;
}
</style>
