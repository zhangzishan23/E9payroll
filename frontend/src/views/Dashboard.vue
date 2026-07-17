<template>
  <div class="space-y-4">
    <div class="apple-card p-4 bg-gradient-to-r from-blue-50 via-white to-blue-50">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-200">
            <el-icon class="text-white text-2xl"><Money /></el-icon>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-xl font-bold bg-gradient-to-r from-blue-700 to-blue-500 bg-clip-text text-transparent">工资计算管家</h1>
              <span class="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded-full font-medium">智能化薪资核算</span>
            </div>
            <p class="text-gray-600 mt-1 text-sm">你好，{{ authStore.user?.display_name || '用户' }} 👋 今天是 {{ today }}</p>
            <p class="text-blue-600 text-sm mt-0.5 font-medium">{{ currentPeriodDisplay }} 工资计算进行中</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <el-date-picker v-model="statsPeriod" type="month" placeholder="选择月份" size="default" class="!w-40" value-format="YYYYMM" @change="fetchStats" />
        </div>
      </div>
    </div>

    <div class="apple-card p-4">
      <h3 class="text-base font-semibold text-gray-700 mb-3">⚡ 快捷入口</h3>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        <div class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-blue-300" @click="goTo('/salary')">
          <el-icon class="text-3xl text-blue-500 mb-1"><Money /></el-icon>
          <div class="font-semibold text-sm">薪资计算</div>
          <div class="text-xs text-gray-500">计算当月工资</div>
        </div>
        <div class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-green-300" @click="goTo('/attendance')">
          <el-icon class="text-3xl text-green-500 mb-1"><Calendar /></el-icon>
          <div class="font-semibold text-sm">考勤管理</div>
          <div class="text-xs text-gray-500">管理考勤数据</div>
        </div>
        <div class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-orange-300" @click="goTo('/insurance')">
          <el-icon class="text-3xl text-orange-500 mb-1"><CreditCard /></el-icon>
          <div class="font-semibold text-sm">社保公积金</div>
          <div class="text-xs text-gray-500">管理社保数据</div>
        </div>
        <div class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-purple-300" @click="goTo('/performance')">
          <el-icon class="text-3xl text-purple-500 mb-1"><TrendCharts /></el-icon>
          <div class="font-semibold text-sm">绩效评分</div>
          <div class="text-xs text-gray-500">录入绩效系数</div>
        </div>
        <div class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-red-300" @click="goTo('/approval')">
          <el-icon class="text-3xl text-red-500 mb-1"><Checked /></el-icon>
          <div class="font-semibold text-sm">审批流程</div>
          <div class="text-xs text-gray-500">审核薪资数据</div>
        </div>
        <div class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-cyan-300" @click="goTo('/reports')">
          <el-icon class="text-3xl text-cyan-500 mb-1"><Document /></el-icon>
          <div class="font-semibold text-sm">报表导出</div>
          <div class="text-xs text-gray-500">导出工资条等</div>
        </div>
        <div class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-indigo-300" @click="goTo('/employees')">
          <el-icon class="text-3xl text-indigo-500 mb-1"><User /></el-icon>
          <div class="font-semibold text-sm">档案管理</div>
          <div class="text-xs text-gray-500">管理员工信息</div>
        </div>
        <div class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-gray-300" @click="goTo('/insurance-template')">
          <el-icon class="text-3xl text-gray-500 mb-1"><Setting /></el-icon>
          <div class="font-semibold text-sm">导入模板</div>
          <div class="text-xs text-gray-500">配置导入模板</div>
        </div>
      </div>
    </div>

    <div class="apple-card p-4">
      <h3 class="text-base font-semibold text-gray-700 mb-2">📋 本月算薪进度</h3>
      <div class="relative">
        <div class="absolute top-4 left-0 right-0 h-1 bg-gray-200 rounded"></div>
        <div class="flex justify-between relative z-10">
          <div
            v-for="(step, index) in salarySteps"
            :key="step.key"
            class="flex flex-col items-center cursor-pointer group"
            style="width: 14.28%;"
          >
            <div class="relative">
              <div
                v-if="!step.is_confirmed && step.data_ready"
                class="absolute top-0 left-0 w-8 h-8 rounded-full animate-ping-ring bg-green-400"
              ></div>
              <div
                class="step-circle w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold text-sm transition-all duration-300 relative z-10"
                :class="[getStepCircleClass(step), !step.is_confirmed && step.data_ready ? 'animate-green-blink' : '']"
                @click.stop="handleStepClick(step)"
              >
                <el-icon v-if="step.is_confirmed" :size="16"><Check /></el-icon>
                <span v-else>{{ index + 1 }}</span>
              </div>
            </div>
            <div
              class="mt-2 text-center"
              @click="goTo(step.route)"
            >
              <div class="font-semibold text-sm" :class="step.is_confirmed ? 'text-green-600' : 'text-gray-700'">
                {{ step.title }}
              </div>
              <div class="text-xs mt-1" :class="getStepDescClass(step)">
                {{ getStepDesc(step) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="apple-card p-4 bg-gradient-to-r from-amber-50 via-white to-amber-50" v-if="hasAnyTaxPermission">
      <h3 class="text-base font-semibold text-gray-700 mb-2">🧾 报税快捷操作</h3>
      <div class="flex flex-wrap gap-2">
        <el-button v-permission="'salary:tax_export'" type="primary" size="default" @click="handleExportTaxTemplates">
          <el-icon class="mr-1"><Download /></el-icon>导出报税模板
        </el-button>
        <el-button v-permission="'salary:travel_import'" type="warning" size="default" @click="showTravelImport">
          <el-icon class="mr-1"><UploadFilled /></el-icon>导入临时性差旅补贴
        </el-button>
        <el-button v-permission="'salary:tax_import'" type="success" size="default" @click="showTaxImport">
          <el-icon class="mr-1"><UploadFilled /></el-icon>导入个税申报结果
        </el-button>
      </div>
      <p class="text-xs text-gray-500 mt-1">提示：先导出报税模板去报税系统申报，报税后导入「个税申报结果」回填应扣个税额</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="apple-card p-6">
        <h3 class="text-lg font-semibold text-gray-700 mb-4">📊 数据概览</h3>
        <div class="grid grid-cols-3 gap-4">
          <div class="text-center p-4 bg-blue-50 rounded-lg">
            <div class="text-3xl font-bold text-blue-600">{{ formatInt(stats.total_employees) }}</div>
            <div class="text-sm text-gray-500 mt-1">在职员工</div>
          </div>
          <div class="text-center p-4 bg-purple-50 rounded-lg">
            <div class="text-2xl font-bold text-purple-600">{{ fmtMoney(stats.avg_gross) }}</div>
            <div class="text-sm text-gray-500 mt-1">人均应发</div>
          </div>
          <div class="text-center p-4 bg-orange-50 rounded-lg">
            <div class="text-2xl font-bold text-orange-600">{{ formatPercent(stats.attend_rate / 100) }}</div>
            <div class="text-sm text-gray-500 mt-1">本月出勤率</div>
          </div>
        </div>
      </div>

      <div class="apple-card p-6">
        <h3 class="text-lg font-semibold text-gray-700 mb-4">⚠️ 待办提醒</h3>
        <div class="space-y-3">
          <div v-if="stats.salary_total > 0 && stats.tax_missing > 0" class="flex items-center gap-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
            <el-icon class="text-amber-500 text-xl"><Document /></el-icon>
            <div class="flex-1">
              <div class="font-medium text-sm">个税待申报导入</div>
              <div class="text-xs text-gray-500">还有 {{ stats.tax_missing }} 人未导入个税申报结果，请先导出报税模板申报，再导入结果</div>
            </div>
            <el-button type="warning" size="small" text @click="goTo('/salary')">去处理</el-button>
          </div>
          <div v-if="stats.salary_total > 0 && stats.tax_missing === 0 && stats.review_passed < stats.salary_total" class="flex items-center gap-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
            <el-icon class="text-orange-500 text-xl"><Clock /></el-icon>
            <div class="flex-1">
              <div class="font-medium text-sm">薪资待审批</div>
              <div class="text-xs text-gray-500">{{ stats.salary_total - stats.review_passed }} 人薪资待审核</div>
            </div>
            <el-button type="primary" size="small" text @click="goTo('/approval')">去审批</el-button>
          </div>
          <div v-if="contractWarning.list.length > 0" class="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
            <el-icon class="text-red-500 text-xl"><CircleClose /></el-icon>
            <div class="flex-1">
              <div class="font-medium text-sm">合同即将到期</div>
              <div class="text-xs text-gray-500">{{ contractWarning.total_count }} 人合同即将到期，{{ contractWarning.expired_count }} 人已过期</div>
            </div>
            <el-button type="danger" size="small" text @click="goTo('/reports')">查看详情</el-button>
          </div>
          <div v-if="stats.salary_total > 0 && stats.tax_missing === 0 && stats.review_passed === stats.salary_total" class="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
            <el-icon class="text-green-500 text-xl"><CircleCheck /></el-icon>
            <div class="flex-1">
              <div class="font-medium text-sm">🎉 本月薪资已完成审批</div>
              <div class="text-xs text-gray-500">可以去报表中心导出工资表了</div>
            </div>
            <el-button type="success" size="small" text @click="goTo('/reports')">去导出</el-button>
          </div>
          <div v-if="!hasAnyTodo" class="text-center py-8 text-gray-400">
            <el-icon class="text-4xl mb-2"><Finished /></el-icon>
            <div>目前没有待办事项</div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="travelImportVisible" title="导入临时性差旅补贴未报税费用" width="600px" append-to-body>
      <div class="mb-3 text-sm text-gray-500">
        上传财务提供的差旅补贴Excel文件（支持.xls/.xlsx格式），系统自动识别「明细」或「数据透视表」工作表，按员工汇总报税应纳税所得额
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
      <template #footer>
        <el-button @click="travelImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="travelImporting" @click="doTravelImport">解析并导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taxImportVisible" title="导入个税申报结果" width="600px" append-to-body>
      <div class="mb-3 text-sm text-gray-500">
        上传从个税申报系统导出的「个人所得税扣缴申报表」，系统自动提取姓名和应补/退税额回填到应扣个税额
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
      <template #footer>
        <el-button @click="taxImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="taxImporting" @click="doTaxImport">解析并导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Money, Calendar, CreditCard, TrendCharts, Checked, Document, User, Setting, Clock, CircleClose, CircleCheck, Finished, Check, Download, UploadFilled } from '@element-plus/icons-vue'
import api from '../api'
import { getDefaultPeriod, formatPeriodDisplay } from '../utils/date.js'
import { useAuthStore } from '../stores/auth'
import { formatMoney, formatInt, formatPercent } from '../utils/format'

const router = useRouter()
const authStore = useAuthStore()

const statsPeriod = ref(getDefaultPeriod())
const currentPeriodDisplay = computed(() => formatPeriodDisplay(statsPeriod.value))

const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const stats = reactive({
  total_employees: 0,
  salary_total: 0,
  salary_completed: 0,
  tax_imported: 0,
  tax_missing: 0,
  review_passed: 0,
  review_rejected: 0,
  attend_rate: 0,
  avg_gross: 0,
  avg_net: 0
})

const salarySteps = ref([])
const currentPeriod = ref(null)

const contractWarning = reactive({
  total_count: 0,
  expired_count: 0,
  list: []
})

const hasAnyTodo = computed(() => {
  return (stats.salary_total > 0 && stats.tax_missing > 0) ||
    (stats.salary_total > 0 && stats.tax_missing === 0 && stats.review_passed < stats.salary_total) ||
    contractWarning.list.length > 0 ||
    (stats.salary_total > 0 && stats.tax_missing === 0 && stats.review_passed === stats.salary_total)
})

const hasAnyTaxPermission = computed(() => {
  return authStore.hasAnyPermission('salary:tax_export', 'salary:tax_import', 'salary:travel_import')
})

function fmtMoney(val) {
  if (val == null || val === 0) return ''
  return '¥' + Number(val).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function goTo(path) {
  router.push(path)
}

function getStepCircleClass(step) {
  if (step.is_confirmed) {
    if (step.is_force_confirmed) {
      return 'bg-orange-500 shadow-lg shadow-orange-200 cursor-pointer hover:scale-110 hover:bg-orange-600'
    }
    return 'bg-green-500 shadow-lg shadow-green-200 cursor-pointer hover:scale-110 hover:bg-green-600'
  }
  if (step.key === 'salary' && step.prerequisites_met === false) {
    return 'bg-gray-300 shadow-none cursor-not-allowed'
  }
  if (step.data_ready) {
    return 'bg-green-500 shadow-lg shadow-green-200 cursor-pointer hover:scale-110 hover:bg-green-600'
  }
  return 'bg-red-500 shadow-lg shadow-red-200 cursor-pointer hover:scale-110 hover:bg-red-600'
}

function getStepDescClass(step) {
  if (step.is_confirmed) {
    return step.is_force_confirmed ? 'text-orange-500' : 'text-green-600'
  }
  if (step.key === 'salary' && step.prerequisites_met === false) {
    return 'text-gray-400'
  }
  if (step.data_ready) {
    return 'text-green-600 font-medium'
  }
  return 'text-red-500 font-medium'
}

function getStepDesc(step) {
  if (step.is_confirmed) {
    return step.is_force_confirmed ? '已确认（数据不全）' : '已确认'
  }
  if (step.key === 'salary' && step.prerequisites_met === false) {
    return '请先确认前序步骤'
  }
  if (step.data_ready) {
    return '✓ 可以确认'
  }
  if (step.missing_count > 0) {
    return `⚠ ${step.missing_count}人数据不全`
  }
  return step.description
}

async function handleStepClick(step) {
  if (!step.can_confirm) {
    if (step.key === 'salary' && step.prerequisites_met === false) {
      ElMessage.warning('请先确认前序步骤（员工档案、考勤数据、绩效评分、社保数据、个税申报）后再确认薪资计算')
    } else {
      ElMessage.warning('暂无员工数据，请先添加员工')
    }
    return
  }

  if (step.is_confirmed) {
    try {
      await ElMessageBox.confirm(
        `确定要取消确认「${step.title}」吗？`,
        '取消确认',
        {
          confirmButtonText: '确定取消',
          cancelButtonText: '返回',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        }
      )
      await api.post('/reports/steps/confirm', {
        period: currentPeriod.value,
        step_key: step.key,
        is_confirmed: false
      })
      ElMessage.success('已取消确认')
      fetchStats()
    } catch {
    }
  } else {
    let confirmMsg = `确定要确认「${step.title}」吗？`
    let confirmType = 'success'
    let isForce = false

    if (!step.data_ready) {
      isForce = true
      if (step.missing_count > 0) {
        confirmMsg = `「${step.title}」还有 ${step.missing_count} 名员工数据不全，确定要强制确认吗？`
      } else {
        confirmMsg = `「${step.title}」暂无数据，确定要强制确认吗？`
      }
      confirmType = 'warning'
    }

    try {
      await ElMessageBox.confirm(
        confirmMsg,
        isForce ? '强制确认' : '确认步骤',
        {
          confirmButtonText: isForce ? '仍然确认' : '确定',
          cancelButtonText: '取消',
          type: confirmType,
          confirmButtonClass: isForce ? 'el-button--warning' : 'el-button--success'
        }
      )
      await api.post('/reports/steps/confirm', {
        period: currentPeriod.value,
        step_key: step.key,
        is_confirmed: true
      })
      ElMessage.success(isForce ? '已强制确认' : '确认成功')
      fetchStats()
    } catch {
    }
  }
}

async function fetchStats() {
  try {
    const res = await api.get('/reports/stats', { params: { period: statsPeriod.value } })
    const d = res.data
    stats.total_employees = d.total_employees || 0
    currentPeriod.value = d.period
    salarySteps.value = d.steps || []
    if (d.salary_stats) {
      stats.salary_total = d.salary_stats.total || 0
      stats.salary_completed = d.salary_stats.completed || 0
      stats.tax_imported = d.salary_stats.tax_imported || 0
      stats.tax_missing = d.salary_stats.tax_missing || 0
      stats.review_passed = d.salary_stats.review_passed || 0
      stats.review_rejected = d.salary_stats.review_rejected || 0
      stats.avg_gross = d.salary_stats.avg_gross_salary || 0
      stats.avg_net = d.salary_stats.avg_net_salary || 0
    }
    if (d.attendance_stats) {
      stats.attend_rate = d.attendance_stats.avg_rate || 0
    }
  } catch {
  }
}

async function fetchContractWarning() {
  try {
    const res = await api.get('/reports/contract-expiry-warning', { params: { days_ahead: 30 } })
    const d = res.data
    contractWarning.total_count = d.total_count
    contractWarning.expired_count = d.expired_count
    contractWarning.list = d.list
  } catch {
  }
}

const travelImportVisible = ref(false)
const travelImporting = ref(false)
const travelFile = ref(null)
const travelUploadRef = ref(null)
const taxImportVisible = ref(false)
const taxImporting = ref(false)
const taxFile = ref(null)
const taxUploadRef = ref(null)

function showTravelImport() {
  if (!authStore.hasPermission('salary:travel_import')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  travelFile.value = null
  if (travelUploadRef.value) {
    travelUploadRef.value.clearFiles()
  }
  travelImportVisible.value = true
}

function showTaxImport() {
  if (!authStore.hasPermission('salary:tax_import')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  taxFile.value = null
  if (taxUploadRef.value) {
    taxUploadRef.value.clearFiles()
  }
  taxImportVisible.value = true
}

function handleTravelFileChange(file) {
  travelFile.value = file.raw
}

function handleTaxFileChange(file) {
  taxFile.value = file.raw
}

async function extractBlobError(blob) {
  try {
    const text = await blob.text()
    const json = JSON.parse(text)
    return json.detail || '请求失败'
  } catch {
    return '请求失败'
  }
}

async function handleExportTaxTemplates() {
  if (!authStore.hasPermission('salary:tax_export')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  const period = statsPeriod.value
  const files = [
    { type: 'salary', filename: `正常工资薪金_${period}.xlsx` },
    { type: 'bonus', filename: `全年一次性奖金_${period}.xlsx` },
    { type: 'severance', filename: `解除劳动合同一次性补偿金_${period}.xlsx` }
  ]
  for (let i = 0; i < files.length; i++) {
    const { type, filename } = files[i]
    try {
      const res = await api.get(`/salary/export-tax-template/${period}`, { params: { type }, responseType: 'blob' })
      const contentType = res.headers['content-type'] || ''
      if (contentType.includes('application/json')) {
        const errMsg = await extractBlobError(res.data)
        ElMessage.error(errMsg)
        return
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
      if (i < files.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 300))
      }
    } catch (e) {
      return
    }
  }
  ElMessage.success('报税模板导出成功，共3个文件')
}

async function doTravelImport() {
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
  travelImporting.value = true
  try {
    const res = await api.post(`/salary/import-travel-untaxed/${statsPeriod.value}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success(res.data.message)
    travelImportVisible.value = false
    await fetchStats()
  } catch (e) {
  } finally {
    travelImporting.value = false
  }
}

async function doTaxImport() {
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
    const res = await api.post(`/salary/upload-tax-excel/${statsPeriod.value}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success(res.data.message)
    taxImportVisible.value = false
    await fetchStats()
  } catch (e) {
  } finally {
    taxImporting.value = false
  }
}

onMounted(() => {
  fetchStats()
  fetchContractWarning()
})
</script>

<style scoped>
.step-circle {
  border: 2px solid white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.step-circle:hover {
  transform: scale(1.1);
}
</style>
