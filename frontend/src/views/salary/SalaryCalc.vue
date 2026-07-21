<template>
  <div class="space-y-4">
    <div class="apple-card p-6">
      <div class="flex items-center justify-between mb-4 salary-toolbar">
        <div class="flex items-center gap-2">
          <h3 class="text-base font-semibold text-gray-700 shrink-0">薪资计算</h3>
          <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" class="!w-28 shrink-0" size="small" value-format="YYYYMM" @change="onPeriodChange" />
          <el-select v-model="filterField" placeholder="字段" class="!w-20 shrink-0" size="small">
            <el-option label="姓名" value="employee_name" />
          </el-select>
          <el-input v-model="filterValue" placeholder="筛选" clearable class="!w-24 shrink-0" size="small" @input="fetchResults" />
        </div>
        <div class="flex items-center gap-1">
          <el-button type="primary" size="small" :loading="checking" @click="checkCompleteness" v-permission="'salary:check'">检查</el-button>
          <el-button
            size="small"
            :type="editMode ? 'danger' : 'primary'"
            :disabled="!hasResults"
            @click="toggleEditMode"
            v-permission="'salary:edit'"
          >
            {{ editMode ? '退出' : '编辑' }}
          </el-button>
          <template v-if="editMode">
            <el-button type="success" size="small" :loading="savingEdits" @click="confirmEdits" v-permission="'salary:edit'">确认</el-button>
            <el-button size="small" @click="cancelEdits">取消</el-button>
          </template>
          <el-button type="danger" size="small" :disabled="!hasResults || isSubmitting" @click="batchSubmitApproval" v-permission="'approval:submit'">审核</el-button>
          <el-button type="info" size="small" :disabled="!hasResults" @click="handleExport" v-permission="'salary:export'">导出</el-button>
          <el-button type="danger" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete" v-permission="'salary:delete'">
            删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
          </el-button>
          <el-button type="warning" size="small" :disabled="!hasResults" @click="showTaxImport" v-permission="['salary:tax_import', 'salary:travel_import']">报税导入</el-button>
          <el-button type="success" size="small" :disabled="!hasResults" @click="handleExportTaxTemplate" v-permission="'salary:tax_export'">导出报税模板</el-button>
          <ColumnSetting
            :columns="SALARY_TABLE_COLUMNS"
            :default-visible-keys="SALARY_DEFAULT_VISIBLE"
            v-model="salaryVisibleColumns"
            storage-key="salary_table_columns"
          />
        </div>
      </div>

      <div v-if="formulaVisible" class="bg-gray-50 rounded-xl p-4 mb-4 text-sm">
        <h4 class="font-semibold text-gray-700 mb-2">计算公式说明</h4>
        <div class="grid grid-cols-2 gap-2 text-gray-600">
          <div>月薪标准 = 基本工资 + 绩效奖金标准 + 补贴合计</div>
          <div>（如有月中调薪，基本工资和绩效奖金标准使用折算后值）</div>
          <div>折算后基本工资 = ROUND(调前天数×调前基本工资/应计薪天数 + 调后基本工资×调后天数/应计薪天数, 2)</div>
          <div>实发绩效奖金标准 = 绩效奖金标准 × 实发绩效奖金系数</div>
          <div>实发绩效奖金 = 实发绩效奖金标准 × 出勤率</div>
          <div>总应发工资 = (基本工资 + 补贴合计 + 提成/项目奖金/补发) × 出勤率 + 实发绩效奖金</div>
          <div>补贴合计 = 餐补 + 交通补 + 通讯补 + 电脑补贴 + 住房补</div>
          <div>社保、公积金（个人）合计 = 养老(个人) + 失业(个人) + 医疗(个人) + 公积金(个人)</div>
          <div>实发工资 = 总应发工资 - 社保、公积金合计 - 本月应扣个税额 + 税后调整金额 + 实发离职补偿金</div>
          <div>本月实际报税金额 = 总应发工资 + 上月未报税 + 临时性差旅补贴未报税费用 + 补偿金报税 + 未报税年终奖 + 实发离职补偿金</div>
          <div>电脑补贴为非固定收入，仅当月有效，不纳入薪酬固定部分</div>
        </div>
      </div>
    </div>

    <div class="apple-card p-6">
      <div class="flex justify-between items-center mb-3">
        <h4 class="text-md font-semibold text-gray-700">
          核算结果明细
          <span v-if="editMode" class="text-orange-500 text-sm font-normal ml-2">🔴 编辑模式已开启 - 仅可编辑导入/手动录入的字段</span>
        </h4>
        <el-button link type="primary" @click="formulaVisible = !formulaVisible">
          {{ formulaVisible ? '收起公式' : '查看计算公式' }}
        </el-button>
      </div>
      <el-table :data="results" border stripe :max-height="tableMaxHeight" v-loading="loading" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
        <el-table-column v-if="isSalaryColumnVisible('__selection')" type="selection" width="55" />
        <el-table-column v-if="isSalaryColumnVisible('__index')" type="index" label="序号" width="50" fixed="left" />
        <el-table-column
          v-for="col in visibleSalaryColumns"
          :key="col.key"
          :prop="col.key"
          :label="col.label"
          :width="col.width"
          :fixed="col.fixed || false"
          :class-name="col.summary ? 'col-summary' : ''"
        >
          <template #header>
            <el-tooltip :content="col.tooltip || ''" placement="top" :show-after="400">
              <span>{{ col.label }}</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <template v-if="editMode && col.editable && editCache[getCacheKey(row)]">
              <el-input
                v-if="col.type === 'text'"
                v-model="editCache[getCacheKey(row)][col.key]"
                size="small"
                class="cell-text"
                @change="markChanged(row.id, col.key)"
              />
              <el-input-number
                v-else
                v-model="editCache[getCacheKey(row)][col.key]"
                :min="0"
                :precision="2"
                size="small"
                controls-position="right"
                class="cell-number"
                @change="markChanged(row.id, col.key)"
              />
            </template>
            <template v-else>
              <template v-if="col.key === 'contract_company'">
                <span :class="row.record_type === 'contract' ? 'text-orange-600 font-medium' : 'text-blue-600 font-medium'">{{ row[col.key] || '' }}</span>
              </template>
              <template v-else-if="col.type === 'percent'">
                {{ formatPercent(row[col.key]) }}
              </template>
              <template v-else-if="col.type === 'money'">
                <span
                  v-if="!isEmptyValue(row[col.key])"
                  :class="{
                    'font-semibold text-blue-600': col.key === 'gross_salary',
                    'font-semibold text-green-600': col.key === 'net_salary'
                  }"
                >{{ formatMoney(row[col.key]) }}</span>
              </template>
              <template v-else-if="col.type === 'number' || col.type === 'int'">
                {{ formatNumber(row[col.key]) }}
              </template>
              <template v-else>
                {{ formatText(row[col.key]) }}
              </template>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="editConfirmVisible" title="确认修改内容" width="700px" append-to-body>
      <div class="text-sm text-gray-600 mb-3">以下 {{ changedRows.length }} 条记录发生了修改，确认后将重新计算应发/实发工资：</div>
      <el-table :data="changedRows" border stripe max-height="400" size="small">
        <el-table-column type="index" label="序号" width="50" />
        <el-table-column prop="employee_name" label="员工" width="80" />
        <el-table-column label="修改字段" min-width="200">
          <template #default="{ row }">
            <div v-for="(chg, idx) in row.changes" :key="idx" class="text-sm">
              <span class="text-gray-500">{{ chg.label }}：</span>
              <span class="text-red-400 line-through mr-1">{{ chg.old }}</span>
              <span class="text-green-600 font-semibold">{{ chg.new }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="editConfirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdits" @click="saveAllEdits">确认保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taxImportVisible" title="报税数据导入" width="700px" append-to-body>
      <el-tabs v-model="taxImportTab" class="mb-4">
        <el-tab-pane v-if="authStore.hasPermission('salary:tax_import')" label="个税Excel导入" name="excel">
          <div class="mb-3 text-sm text-gray-500">
            上传税务局导出的「个人所得税扣缴申报表」Excel文件（支持.xls/.xlsx格式），系统将自动提取姓名和应补/退税额
          </div>
          <el-upload
            ref="taxUploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".xls,.xlsx"
            :on-change="handleTaxFileChange"
            :on-exceed="() => ElMessage.warning('只能上传一个文件')"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将Excel文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip text-left">
                仅支持从个税系统导出的「个人所得税扣缴申报表」格式
              </div>
            </template>
          </el-upload>
          <div v-if="taxFile" class="mt-2 text-sm text-green-600">
            已选择文件：{{ taxFile.name }}
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="authStore.hasPermission('salary:travel_import')" label="临时性差旅补贴导入" name="travel">
          <div class="mb-3 text-sm text-gray-500">
            上传财务提供的差旅补贴Excel文件（支持.xls/.xlsx格式），系统自动识别「明细」（Sheet1）或「数据透视表」（Sheet2）工作表，按员工汇总报税应纳税所得额
          </div>
          <el-upload
            ref="travelUploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".xls,.xlsx"
            :on-change="handleTravelFileChange"
            :on-exceed="() => ElMessage.warning('只能上传一个文件')"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将Excel文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip text-left">
                支持两种格式：明细表（Sheet1）或数据透视表（Sheet2），系统自动识别
              </div>
            </template>
          </el-upload>
          <div v-if="travelFile" class="mt-2 text-sm text-green-600">
            已选择文件：{{ travelFile.name }}
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="authStore.hasAnyPermission('salary:tax_import', 'salary:travel_import')" label="手动粘贴数据" name="manual">
          <div class="mb-3 text-sm text-gray-500">
            请粘贴财务提供的报税数据（格式：员工编号,上月未报税,差旅未报税,补偿金报税），每行一条
          </div>
          <el-input v-model="taxData" type="textarea" :rows="8" placeholder="E001,0,0,0&#10;E002,0,0,0" />
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="taxImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="taxImporting" @click="doTaxImport">
          {{ taxImportTab === 'excel' ? '解析并导入个税' : taxImportTab === 'travel' ? '解析并导入差旅补贴' : '导入数据' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="checkResultVisible" title="数据完整性检查" width="650px" append-to-body>
      <div v-if="completeness" class="space-y-4">
        <div class="flex items-center gap-4 text-sm">
          <el-tag :type="completeness.missing_count === 0 ? 'success' : 'warning'" effect="dark" size="large">
            {{ completeness.missing_count === 0 ? '✓ 数据完整' : `⚠ ${completeness.missing_count} 人数据缺失` }}
          </el-tag>
          <span class="text-gray-500">共 {{ completeness.total_employees }} 名在职员工，{{ completeness.complete_count }} 人数据完整</span>
        </div>
        <div class="space-y-2">
          <div v-for="src in completeness.sources" :key="src.source_key" class="p-3 rounded-lg" :class="getSourceBgClass(src.status)">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <el-icon :size="16" :class="getSourceIconClass(src.status)">
                  <CircleCheckFilled v-if="src.status === '完整'" />
                  <WarningFilled v-else-if="src.status === '部分缺失'" />
                  <InfoFilled v-else />
                </el-icon>
                <span class="font-medium text-sm">{{ src.source_name }}</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-sm text-gray-500">{{ src.count }}/{{ completeness.total_employees }}</span>
                <el-tag :type="getSourceTagType(src.status)" size="small">{{ src.status }}</el-tag>
              </div>
            </div>
            <div v-if="src.description" class="mt-1 ml-6 text-xs text-gray-500">
              {{ src.description }}
            </div>
          </div>
        </div>
        <div v-if="hasMissingEmployees" class="mt-4">
          <div class="text-sm font-medium text-gray-700 mb-2">缺失数据人员名单：</div>
          <div class="max-h-40 overflow-y-auto bg-gray-50 rounded-lg p-3">
            <div v-for="src in completeness.sources.filter(s => s.missing_employees && s.missing_employees.length > 0)" :key="src.source_key" class="mb-2 last:mb-0">
              <span class="text-xs text-red-500 font-medium">{{ src.source_name }}缺失：</span>
              <span class="text-xs text-gray-600">{{ src.missing_employees.join('、') }}</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="checkResultVisible = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Download, Delete, UploadFilled, Setting, CircleCheckFilled, WarningFilled, InfoFilled } from '@element-plus/icons-vue'
import api from '../../api'
import { SALARY_COLUMNS, SALARY_EDITABLE_FIELDS, getSalaryFieldLabel } from '../../config/columns'
import ColumnSetting from '../../components/ColumnSetting.vue'
import { formatMoney, formatNumber, formatPercent, formatText, isEmptyValue } from '../../utils/format'
import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()

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

const periodDate = ref(defaultPeriod)
const filterField = ref('')
const filterValue = ref('')
const checking = ref(false)
const savingEdits = ref(false)
const loading = ref(false)
const isSubmitting = ref(false)
const completeness = ref(null)
const checkResultVisible = ref(false)
const results = ref([])
const selectedRows = ref([])
const formulaVisible = ref(false)
const tableMaxHeight = ref(500)

const hasMissingEmployees = computed(() => {
  if (!completeness.value) return false
  return completeness.value.sources.some(s => s.missing_employees && s.missing_employees.length > 0)
})

function getSourceBgClass(status) {
  if (status === '完整') return 'bg-green-50'
  if (status === '部分缺失') return 'bg-amber-50'
  return 'bg-blue-50'
}

function getSourceIconClass(status) {
  if (status === '完整') return 'text-green-500'
  if (status === '部分缺失') return 'text-amber-500'
  return 'text-blue-500'
}

function getSourceTagType(status) {
  if (status === '完整') return 'success'
  if (status === '部分缺失') return 'warning'
  return 'info'
}

function updateTableHeight() {
  tableMaxHeight.value = Math.max(400, window.innerHeight - 260)
}

const SALARY_TABLE_COLUMNS = [
  { key: '__selection', label: '选择', required: true },
  { key: '__index', label: '序号', required: true },
  ...SALARY_COLUMNS.map(c => ({ key: c.key, label: c.label, required: ['contract_company', 'employee_name', 'gross_salary', 'net_salary'].includes(c.key) }))
]

const SALARY_DEFAULT_VISIBLE = [
  '__selection', '__index', 'contract_company', 'employee_name', 'department', 'base_salary',
  'performance_standard', 'actual_performance', 'effective_performance',
  'allowance_total', 'gross_salary', 'si_hf_total', 'tax_deduction', 'net_salary'
]

const salaryVisibleColumns = ref([])

const visibleSalaryColumns = computed(() => {
  return SALARY_COLUMNS.filter(c => salaryVisibleColumns.value.includes(c.key))
})

function isSalaryColumnVisible(key) {
  if (key === '__selection') return salaryVisibleColumns.value.includes('__selection')
  return salaryVisibleColumns.value.includes(key)
}

const editMode = ref(false)
const editCache = reactive({})
const changedSet = reactive({})
const editConfirmVisible = ref(false)
const changedRows = ref([])

const editableFields = SALARY_EDITABLE_FIELDS

function getFieldLabel(key) {
  return getSalaryFieldLabel(key)
}

function getCacheKey(row) {
  return row.id || `_emp_${row.employee_id}`
}

const hasResults = computed(() => results.value.length > 0)

async function ensureRecordsExist() {
  const hasUncreated = results.value.some(r => r.id == null)
  if (!hasUncreated) return true
  const loading = ElLoading.service({ text: '正在准备数据...' })
  try {
    const params = {}
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) params.hide_status_id = Number(hideStatusId)
    await api.post(`/salary/ensure-records/${periodDate.value}`, null, { params })
    await fetchResults()
    return true
  } catch (e) {
    ElMessage.error('准备数据失败：' + (e.response?.data?.detail || e.message))
    return false
  } finally {
    loading.close()
  }
}

function tableRowClassName({ row }) {
  const classes = []
  if (editMode.value && row.id && changedSet[row.id]) classes.push('row-changed')
  if (row.record_type === 'contract') classes.push('row-contract-company')
  if (row.record_type === 'payroll') classes.push('row-payroll-company')
  return classes.join(' ')
}

function initEditCache() {
  Object.keys(changedSet).forEach(k => delete changedSet[k])
  // 从列配置动态获取所有可编辑字段
  const editableCols = SALARY_COLUMNS.filter(c => c.editable)
  results.value.forEach(row => {
    if (!row) return
    const cacheKey = getCacheKey(row)
    const cache = {}
    editableCols.forEach(col => {
      const val = row[col.key]
      cache[col.key] = col.type === 'text' ? (val ?? '') : (val ?? null)
    })
    editCache[cacheKey] = reactive(cache)
  })
}

function markChanged(rowId, field) {
  const row = results.value.find(r => r.id === rowId)
  if (!row) return
  const oldVal = row[field]
  const newVal = editCache[getCacheKey(row)]?.[field]
  const changed = (() => {
    if (oldVal == null && newVal == null) return false
    if (oldVal == null || newVal == null) return oldVal !== newVal
    if (typeof oldVal === 'number' && typeof newVal === 'number') {
      return Math.abs(oldVal - newVal) >= 0.001
    }
    return String(oldVal) !== String(newVal)
  })()
  const cacheKey = getCacheKey(row)
  if (!changed) {
    if (changedSet[cacheKey]) {
      delete changedSet[cacheKey][field]
      if (Object.keys(changedSet[cacheKey]).length === 0) delete changedSet[cacheKey]
    }
  } else {
    if (!changedSet[cacheKey]) changedSet[cacheKey] = {}
    changedSet[cacheKey][field] = true
  }
}

async function toggleEditMode() {
  try {
    if (editMode.value) {
      editMode.value = false
      for (const key of Object.keys(editCache)) {
        delete editCache[key]
      }
      for (const key of Object.keys(changedSet)) {
        delete changedSet[key]
      }
      return
    }
    const ok = await ensureRecordsExist()
    if (!ok) return
    initEditCache()
    editMode.value = true
  } catch (e) {
    console.error('切换编辑模式失败：', e)
    ElMessage.error('切换编辑模式失败，请刷新页面后重试')
  }
}

function cancelEdits() {
  editMode.value = false
  for (const key of Object.keys(editCache)) {
    delete editCache[key]
  }
  for (const key of Object.keys(changedSet)) {
    delete changedSet[key]
  }
}

async function confirmEdits() {
  const changedKeys = Object.keys(changedSet)
  if (!changedKeys.length) {
    ElMessage.warning('没有检测到任何修改')
    return
  }

  function findRowByCacheKey(key) {
    const numKey = Number(key)
    if (!isNaN(numKey)) return results.value.find(r => r.id === numKey)
    // 字符串键：_emp_{employee_id}
    const empId = parseInt(key.replace('_emp_', ''), 10)
    return results.value.find(r => r.employee_id === empId)
  }

  const rows = []
  changedKeys.forEach(cacheKey => {
    const row = findRowByCacheKey(cacheKey)
    if (!row) return
    const changes = []
    Object.keys(changedSet[cacheKey]).forEach(field => {
      const oldVal = row[field]
      const newVal = editCache[cacheKey]?.[field]
      changes.push({
        field,
        label: getFieldLabel(field) || field,
        old: oldVal == null ? '(空)' : (typeof oldVal === 'number' ? oldVal.toFixed(2) : String(oldVal)),
        new: newVal == null ? '(空)' : (typeof newVal === 'number' ? newVal.toFixed(2) : String(newVal))
      })
    })
    if (changes.length) {
      rows.push({
        id: row.id,
        cacheKey,
        employee_name: row.employee_name,
        employee_no: row.employee_no,
        changes
      })
    }
  })

  changedRows.value = rows
  editConfirmVisible.value = true
}

async function saveAllEdits() {
  savingEdits.value = true
  const changedKeys = Object.keys(changedSet)
  let successCount = 0
  let failCount = 0

  function findRowByCacheKey(key) {
    const numKey = Number(key)
    if (!isNaN(numKey)) return results.value.find(r => r.id === numKey)
    const empId = parseInt(key.replace('_emp_', ''), 10)
    return results.value.find(r => r.employee_id === empId)
  }

  try {
    for (const cacheKey of changedKeys) {
      const cache = editCache[cacheKey]
      if (!cache) continue
      const row = findRowByCacheKey(cacheKey)
      if (!row || !row.id) continue
      const payload = {}
      Object.keys(changedSet[cacheKey] || {}).forEach(field => {
        const val = cache[field]
        payload[field] = val === undefined ? null : val
      })
      try {
        await api.put(`/salary/results/${row.id}`, payload)
        successCount++
      } catch {
        failCount++
      }
    }

    if (failCount === 0) {
      ElMessage.success(`修改成功！共更新 ${successCount} 条记录，应发/实发工资已重新计算`)
    } else {
      ElMessage.warning(`部分成功：${successCount} 条已更新，${failCount} 条失败`)
    }

    editConfirmVisible.value = false
    editMode.value = false
    for (const key of Object.keys(editCache)) {
      delete editCache[key]
    }
    for (const key of Object.keys(changedSet)) {
      delete changedSet[key]
    }
    await fetchResults()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    savingEdits.value = false
  }
}

function onPeriodChange(val) {
  periodDate.value = val
  fetchResults()
}

async function checkCompleteness() {
  checking.value = true
  try {
    const params = {}
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get(`/salary/check-completeness/${periodDate.value}`, { params })
    completeness.value = res.data
    checkResultVisible.value = true
  } catch (e) {
    ElMessage.error('检查失败：' + (e.response?.data?.detail || e.message))
  } finally {
    checking.value = false
  }
}

async function fetchResults() {
  loading.value = true
  try {
    const params = {}
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get(`/salary/results/${periodDate.value}`, { params })
    let data = res.data
    
    data.sort((a, b) => {
      if (a.employee_id !== b.employee_id) {
        return (a.employee_id || 0) - (b.employee_id || 0)
      }
      const typeOrder = { contract: 0, single: 1, payroll: 2 }
      return (typeOrder[a.record_type] ?? 1) - (typeOrder[b.record_type] ?? 1)
    })
    
    if (filterField.value && filterValue.value) {
      const fv = filterValue.value.toLowerCase()
      data = data.filter(r => {
        if (filterField.value === 'employee_name') return (r.employee_name || '').toLowerCase().includes(fv)
        return true
      })
    }
    results.value = data
  } catch (e) {
    results.value = []
  } finally {
    loading.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function calculateNet() {
  await ElMessageBox.confirm('确认计算实发工资？将根据个税数据更新实发金额。', '确认操作', {
    type: 'info', confirmButtonText: '确认', cancelButtonText: '取消'
  })
  try {
    const res = await api.post(`/salary/calculate-net/${periodDate.value}`)
    summary.value = res.data
    ElMessage.success('实发工资计算完成')
    await fetchResults()
  } catch (e) {
    ElMessage.error('计算失败：' + (e.response?.data?.detail || e.message))
  }
}

async function submitReview(row) {
  await ElMessageBox.confirm(
    `确认将「${row.employee_name}」的核算结果提交审核？`,
    '提交审核',
    { type: 'info', confirmButtonText: '确认提交', cancelButtonText: '取消' }
  )
  try {
    await api.put(`/salary/results/${row.id}`, { review_status: '审核中' })
    ElMessage.success('已提交审核')
    await fetchResults()
  } catch (e) {
    ElMessage.error('提交失败')
  }
}

async function batchSubmitApproval() {
  const pendingCount = results.value.filter(r => r.review_status === '待审核' || !r.review_status).length
  if (pendingCount === 0) {
    ElMessage.warning('没有待审核的记录')
    return
  }

  await ElMessageBox.confirm(
    `确认将 ${periodDate.value} 月份共 ${pendingCount} 条核算记录批量提交审核？\n提交后将生成审批流水，核算数据将不可修改。`,
    '批量提交审核',
    { type: 'warning', confirmButtonText: '确认提交', cancelButtonText: '取消' }
  )

  isSubmitting.value = true
  try {
    const ok = await ensureRecordsExist()
    if (!ok) {
      isSubmitting.value = false
      return
    }
    const res = await api.post('/approval/submit', { period: periodDate.value })
    ElMessage.success(`提交成功！审批流水号：${res.data.approval_no}`)
    await fetchResults()
  } catch (e) {
    ElMessage.error('提交失败：' + (e.response?.data?.detail || e.message))
  } finally {
    isSubmitting.value = false
  }
}

async function handleExport() {
  try {
    const params = {}
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get(`/salary/export/${periodDate.value}`, { params, responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `薪酬核算_${periodDate.value}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的核算记录')
    return
  }
  await ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 条核算记录吗？此操作不可恢复。`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.filter(r => r.id).map(r => r.id)
    if (!ids.length) {
      ElMessage.warning('选中的记录中没有可删除的数据')
      return
    }
    await api.post('/salary/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 条核算记录`)
    selectedRows.value = []
    await fetchResults()
  } catch (e) {
    ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

onMounted(() => {
  updateTableHeight()
  window.addEventListener('resize', updateTableHeight)
  fetchResults()
})

onUnmounted(() => {
  window.removeEventListener('resize', updateTableHeight)
})

const taxImportVisible = ref(false)
const taxImporting = ref(false)
const taxData = ref('')
const taxImportTab = ref('excel')
const taxFile = ref(null)
const taxUploadRef = ref(null)
const travelFile = ref(null)
const travelUploadRef = ref(null)

function showTaxImport() {
  if (!authStore.hasAnyPermission('salary:tax_import', 'salary:travel_import')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  taxData.value = ''
  taxFile.value = null
  travelFile.value = null
  if (authStore.hasPermission('salary:tax_import')) {
    taxImportTab.value = 'excel'
  } else {
    taxImportTab.value = 'travel'
  }
  if (taxUploadRef.value) {
    taxUploadRef.value.clearFiles()
  }
  if (travelUploadRef.value) {
    travelUploadRef.value.clearFiles()
  }
  taxImportVisible.value = true
}

function handleTaxFileChange(file) {
  taxFile.value = file.raw
}

function handleTravelFileChange(file) {
  travelFile.value = file.raw
}

async function downloadSingleTaxFile(type, filename) {
  const params = { type }
  const hideStatusId = localStorage.getItem('employee_hide_status_id')
  if (hideStatusId) {
    params.hide_status_id = Number(hideStatusId)
  }
  const res = await api.get(`/salary/export-tax-template/${periodDate.value}`, { params, responseType: 'blob' })
  const contentType = res.headers['content-type'] || ''
  if (contentType.includes('application/json')) {
    const text = await res.data.text()
    const json = JSON.parse(text)
    throw new Error(json.detail || '导出失败')
  }
  const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

async function handleExportTaxTemplate() {
  if (!authStore.hasPermission('salary:tax_export')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  const period = periodDate.value
  const files = [
    { type: 'salary', filename: `正常工资薪金_${period}.xlsx` },
    { type: 'bonus', filename: `全年一次性奖金_${period}.xlsx` },
    { type: 'severance', filename: `解除劳动合同一次性补偿金_${period}.xlsx` }
  ]
  for (let i = 0; i < files.length; i++) {
    const { type, filename } = files[i]
    try {
      await downloadSingleTaxFile(type, filename)
      if (i < files.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 300))
      }
    } catch (e) {
      if (!e.response) {
        ElMessage.error(e.message || `导出${filename}失败`)
      }
      return
    }
  }
  ElMessage.success('报税模板导出成功，共3个文件')
}

async function doTaxImport() {
  if (taxImportTab.value === 'excel') {
    if (!authStore.hasPermission('salary:tax_import')) {
      ElMessage.warning('您没有该操作权限，请联系管理员')
      return
    }
    if (!taxFile.value) {
      ElMessage.warning('请先选择要上传的Excel文件')
      return
    }
    const formData = new FormData()
    formData.append('file', taxFile.value)
    taxImporting.value = true
    try {
      const res = await api.post(`/salary/upload-tax-excel/${periodDate.value}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      ElMessage.success(res.data.message)
      taxImportVisible.value = false
      await fetchResults()
    } catch (e) {
    } finally {
      taxImporting.value = false
    }
  } else if (taxImportTab.value === 'travel') {
    if (!authStore.hasPermission('salary:travel_import')) {
      ElMessage.warning('您没有该操作权限，请联系管理员')
      return
    }
    if (!travelFile.value) {
      ElMessage.warning('请先选择要上传的Excel文件')
      return
    }
    const formData = new FormData()
    formData.append('file', travelFile.value)
    taxImporting.value = true
    try {
      const res = await api.post(`/salary/import-travel-untaxed/${periodDate.value}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      ElMessage.success(res.data.message)
      taxImportVisible.value = false
      await fetchResults()
    } catch (e) {
    } finally {
      taxImporting.value = false
    }
  } else {
    if (!authStore.hasAnyPermission('salary:tax_import', 'salary:travel_import')) {
      ElMessage.warning('您没有该操作权限，请联系管理员')
      return
    }
    if (!taxData.value.trim()) {
      ElMessage.warning('请输入报税数据')
      return
    }
    const lines = taxData.value.trim().split('\n').filter(l => l.trim())
    const items = []
    for (const line of lines) {
      const parts = line.split(',').map(s => s.trim())
      if (parts.length < 2) continue
      items.push({
        employee_no: parts[0],
        last_month_untaxed: parseFloat(parts[1]) || 0,
        travel_untaxed: parseFloat(parts[2]) || 0,
        compensation_tax: parseFloat(parts[3]) || 0
      })
    }
    if (!items.length) {
      ElMessage.warning('未能解析到有效数据')
      return
    }
    taxImporting.value = true
    try {
      const res = await api.post(`/salary/import-tax/${periodDate.value}`, items)
      ElMessage.success(res.data.message)
      taxImportVisible.value = false
      await fetchResults()
    } catch (e) {
    } finally {
      taxImporting.value = false
    }
  }
}
</script>

<style scoped>
.salary-toolbar {
  width: 100%;
}
.salary-toolbar :deep(.el-button) {
  flex-shrink: 0;
  padding-left: 12px;
  padding-right: 12px;
}
.salary-toolbar :deep(.el-button span) {
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
.cell-text {
  width: 100%;
}
.cell-text :deep(.el-input__wrapper) {
  padding: 0 4px;
}
:deep(.el-table__body tr) > td {
  background-color: transparent !important;
}
:deep(.el-table__body tr.el-table__row--striped) > td {
  background-color: transparent !important;
}
:deep(.el-table__fixed .el-table__body tr) > td,
:deep(.el-table__fixed-right .el-table__body tr) > td {
  background-color: transparent !important;
}

:deep(.el-table__body tr.row-contract-company) {
  background-color: #ffedd5 !important;
}
:deep(.el-table__body tr.row-contract-company) > td {
  background-color: #ffedd5 !important;
}
:deep(.el-table__body tr.row-contract-company.el-table__row--striped) > td {
  background-color: #ffedd5 !important;
}
:deep(.el-table__body tr.row-contract-company:hover) > td {
  background-color: #fed7aa !important;
}
:deep(.el-table__fixed .el-table__body tr.row-contract-company) > td,
:deep(.el-table__fixed-right .el-table__body tr.row-contract-company) > td {
  background-color: #ffedd5 !important;
}
:deep(.el-table__fixed .el-table__body tr.row-contract-company:hover) > td,
:deep(.el-table__fixed-right .el-table__body tr.row-contract-company:hover) > td {
  background-color: #fed7aa !important;
}
:deep(.el-table__body tr.row-contract-company) td:first-child {
  border-left: 3px solid #f97316;
}

:deep(.el-table__body tr.row-payroll-company) {
  background-color: #ffffff !important;
}
:deep(.el-table__body tr.row-payroll-company) > td {
  background-color: #ffffff !important;
}
:deep(.el-table__body tr.row-payroll-company.el-table__row--striped) > td {
  background-color: #ffffff !important;
}
:deep(.el-table__body tr.row-payroll-company:hover) > td {
  background-color: #f5f5f5 !important;
}
:deep(.el-table__fixed .el-table__body tr.row-payroll-company) > td,
:deep(.el-table__fixed-right .el-table__body tr.row-payroll-company) > td {
  background-color: #ffffff !important;
}
:deep(.el-table__fixed .el-table__body tr.row-payroll-company:hover) > td,
:deep(.el-table__fixed-right .el-table__body tr.row-payroll-company:hover) > td {
  background-color: #f5f5f5 !important;
}

:deep(.el-table__body tr.row-changed) {
  background-color: #fef3c7 !important;
}
:deep(.el-table__body tr.row-changed) > td {
  background-color: #fef3c7 !important;
}
:deep(.el-table__body tr.row-changed.el-table__row--striped) > td {
  background-color: #fef3c7 !important;
}
:deep(.el-table__body tr.row-changed:hover) > td {
  background-color: #fde68a !important;
}
:deep(.el-table__fixed .el-table__body tr.row-changed) > td,
:deep(.el-table__fixed-right .el-table__body tr.row-changed) > td {
  background-color: #fef3c7 !important;
}
:deep(.el-table__fixed .el-table__body tr.row-changed:hover) > td,
:deep(.el-table__fixed-right .el-table__body tr.row-changed:hover) > td {
  background-color: #fde68a !important;
}

:deep(.el-table__body tr) > td.col-summary {
  background-color: #fef9c3 !important;
}
:deep(.el-table__body tr.el-table__row--striped) > td.col-summary {
  background-color: #fef9c3 !important;
}
:deep(.el-table__body tr:hover) > td.col-summary {
  background-color: #fef08a !important;
}
:deep(.el-table__body tr.row-contract-company) > td.col-summary {
  background-color: #fef9c3 !important;
}
:deep(.el-table__body tr.row-contract-company:hover) > td.col-summary {
  background-color: #fef08a !important;
}
:deep(.el-table__body tr.row-payroll-company) > td.col-summary {
  background-color: #fef9c3 !important;
}
:deep(.el-table__body tr.row-payroll-company:hover) > td.col-summary {
  background-color: #fef08a !important;
}
:deep(.el-table__body tr.row-changed) > td.col-summary {
  background-color: #fef9c3 !important;
}
:deep(.el-table__body tr.row-changed:hover) > td.col-summary {
  background-color: #fef08a !important;
}
:deep(.el-table__fixed .el-table__body tr) > td.col-summary,
:deep(.el-table__fixed-right .el-table__body tr) > td.col-summary {
  background-color: #fef9c3 !important;
}
:deep(.el-table__fixed .el-table__body tr:hover) > td.col-summary,
:deep(.el-table__fixed-right .el-table__body tr:hover) > td.col-summary {
  background-color: #fef08a !important;
}
</style>