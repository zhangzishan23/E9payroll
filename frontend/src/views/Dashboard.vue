<template>
  <div class="space-y-6">
    <div class="apple-card p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl font-bold text-gray-800">你好，{{ authStore.user?.display_name || '用户' }} 👋</h2>
          <p class="text-gray-500 mt-1">今天是 {{ today }}，{{ currentPeriodDisplay }} 工资核算进行中</p>
        </div>
        <el-date-picker v-model="statsPeriod" type="month" placeholder="选择月份" size="default" class="!w-40" value-format="YYYYMM" @change="fetchStats" />
      </div>
    </div>

    <div class="apple-card p-6">
      <h3 class="text-lg font-semibold text-gray-700 mb-4">📋 本月算薪进度</h3>
      <p class="text-sm text-gray-500 mb-4">点击圆形图标可确认/取消确认步骤，点击标题可跳转至对应页面；绿色闪烁表示数据齐全可确认，红色表示有员工数据不全（仍可强制确认）</p>
      <div class="relative">
        <div class="absolute top-5 left-0 right-0 h-1 bg-gray-200 rounded"></div>
        <div class="flex justify-between relative z-10">
          <div
            v-for="(step, index) in salarySteps"
            :key="step.key"
            class="flex flex-col items-center cursor-pointer group"
            style="width: 14%;"
          >
            <div class="relative">
              <div
                class="step-circle w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-lg transition-all duration-300"
                :class="getStepCircleClass(step)"
                @click.stop="handleStepClick(step)"
              >
                <el-icon v-if="step.is_confirmed" :size="20"><Check /></el-icon>
                <span v-else>{{ index + 1 }}</span>
              </div>
              <div
                v-if="!step.is_confirmed && step.data_ready && step.has_data"
                class="absolute inset-0 w-10 h-10 rounded-full animate-ping bg-green-400 opacity-50"
              ></div>
            </div>
            <div
              class="mt-3 text-center"
              @click="goTo(step.route)"
            >
              <div class="font-semibold text-sm" :class="step.is_confirmed ? 'text-green-600' : 'text-gray-700'">
                {{ step.title }}
              </div>
              <div class="text-xs mt-1" :class="getStepDescClass(step)">
                {{ getStepDesc(step) }}
              </div>
              <div v-if="step.is_force_confirmed" class="text-xs text-orange-500 mt-0.5">
                （强制确认）
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="apple-card p-6">
      <h3 class="text-lg font-semibold text-gray-700 mb-4">⚡ 快捷入口</h3>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <div class="apple-card p-5 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-blue-300" @click="goTo('/salary')">
          <el-icon class="text-4xl text-blue-500 mb-3"><Money /></el-icon>
          <div class="font-semibold">薪资核算</div>
          <div class="text-xs text-gray-500 mt-1">计算当月工资</div>
        </div>
        <div class="apple-card p-5 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-green-300" @click="goTo('/attendance')">
          <el-icon class="text-4xl text-green-500 mb-3"><Calendar /></el-icon>
          <div class="font-semibold">考勤管理</div>
          <div class="text-xs text-gray-500 mt-1">管理考勤数据</div>
        </div>
        <div class="apple-card p-5 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-orange-300" @click="goTo('/insurance')">
          <el-icon class="text-4xl text-orange-500 mb-3"><CreditCard /></el-icon>
          <div class="font-semibold">社保公积金</div>
          <div class="text-xs text-gray-500 mt-1">管理社保数据</div>
        </div>
        <div class="apple-card p-5 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-purple-300" @click="goTo('/performance')">
          <el-icon class="text-4xl text-purple-500 mb-3"><TrendCharts /></el-icon>
          <div class="font-semibold">绩效评分</div>
          <div class="text-xs text-gray-500 mt-1">录入绩效系数</div>
        </div>
        <div class="apple-card p-5 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-red-300" @click="goTo('/approval')">
          <el-icon class="text-4xl text-red-500 mb-3"><Checked /></el-icon>
          <div class="font-semibold">审批流程</div>
          <div class="text-xs text-gray-500 mt-1">审核薪资数据</div>
        </div>
        <div class="apple-card p-5 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-cyan-300" @click="goTo('/reports')">
          <el-icon class="text-4xl text-cyan-500 mb-3"><Document /></el-icon>
          <div class="font-semibold">报表导出</div>
          <div class="text-xs text-gray-500 mt-1">导出工资条等</div>
        </div>
        <div class="apple-card p-5 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-indigo-300" @click="goTo('/employees')">
          <el-icon class="text-4xl text-indigo-500 mb-3"><User /></el-icon>
          <div class="font-semibold">档案管理</div>
          <div class="text-xs text-gray-500 mt-1">管理员工信息</div>
        </div>
        <div class="apple-card p-5 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-gray-300" @click="goTo('/insurance-template')">
          <el-icon class="text-4xl text-gray-500 mb-3"><Setting /></el-icon>
          <div class="font-semibold">导入模板</div>
          <div class="text-xs text-gray-500 mt-1">配置导入模板</div>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="apple-card p-6">
        <h3 class="text-lg font-semibold text-gray-700 mb-4">📊 数据概览</h3>
        <div class="grid grid-cols-2 gap-4">
          <div class="text-center p-4 bg-blue-50 rounded-lg">
            <div class="text-3xl font-bold text-blue-600">{{ stats.total_employees }}</div>
            <div class="text-sm text-gray-500 mt-1">在职员工</div>
          </div>
          <div class="text-center p-4 bg-green-50 rounded-lg">
            <div class="text-3xl font-bold text-green-600">{{ stats.salary_completed }}/{{ stats.salary_total }}</div>
            <div class="text-sm text-gray-500 mt-1">薪资已核算</div>
          </div>
          <div class="text-center p-4 bg-purple-50 rounded-lg">
            <div class="text-2xl font-bold text-purple-600">{{ fmtMoney(stats.avg_gross) }}</div>
            <div class="text-sm text-gray-500 mt-1">人均应发</div>
          </div>
          <div class="text-center p-4 bg-orange-50 rounded-lg">
            <div class="text-2xl font-bold text-orange-600">{{ stats.attend_rate }}%</div>
            <div class="text-sm text-gray-500 mt-1">本月出勤率</div>
          </div>
        </div>
      </div>

      <div class="apple-card p-6">
        <h3 class="text-lg font-semibold text-gray-700 mb-4">⚠️ 待办提醒</h3>
        <div class="space-y-3">
          <div v-if="stats.salary_completed < stats.salary_total && stats.salary_total > 0" class="flex items-center gap-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
            <el-icon class="text-yellow-500 text-xl"><WarningFilled /></el-icon>
            <div class="flex-1">
              <div class="font-medium text-sm">薪资核算未完成</div>
              <div class="text-xs text-gray-500">还有 {{ stats.salary_total - stats.salary_completed }} 人未计算工资</div>
            </div>
            <el-button type="primary" size="small" text @click="goTo('/salary')">去处理</el-button>
          </div>
          <div v-if="stats.review_passed < stats.salary_completed && stats.salary_completed > 0" class="flex items-center gap-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
            <el-icon class="text-orange-500 text-xl"><Clock /></el-icon>
            <div class="flex-1">
              <div class="font-medium text-sm">薪资待审批</div>
              <div class="text-xs text-gray-500">{{ stats.salary_completed - stats.review_passed }} 人薪资待审核</div>
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
          <div v-if="stats.salary_completed === stats.salary_total && stats.salary_total > 0 && stats.review_passed === stats.salary_completed" class="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Money, Calendar, CreditCard, TrendCharts, Checked, Document, User, Setting, WarningFilled, Clock, CircleClose, CircleCheck, Finished, Check } from '@element-plus/icons-vue'
import api from '../api'
import { getDefaultPeriod, formatPeriodDisplay } from '../utils/date.js'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const statsPeriod = ref(getDefaultPeriod())
const currentPeriodDisplay = computed(() => formatPeriodDisplay(statsPeriod.value))

const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const stats = reactive({
  total_employees: 0,
  salary_total: 0,
  salary_completed: 0,
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
  return (stats.salary_completed < stats.salary_total && stats.salary_total > 0) ||
    (stats.review_passed < stats.salary_completed && stats.salary_completed > 0) ||
    contractWarning.list.length > 0 ||
    (stats.salary_completed === stats.salary_total && stats.salary_total > 0 && stats.review_passed === stats.salary_completed)
})

function fmtMoney(val) {
  if (val == null || val === 0) return '¥0'
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
  if (step.data_ready) {
    return 'bg-green-500 shadow-lg shadow-green-200 cursor-pointer hover:scale-110 hover:bg-green-600'
  }
  return 'bg-red-500 shadow-lg shadow-red-200 cursor-pointer hover:scale-110 hover:bg-red-600'
}

function getStepDescClass(step) {
  if (step.is_confirmed) {
    return step.is_force_confirmed ? 'text-orange-500' : 'text-green-600'
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
    ElMessage.warning('暂无员工数据，请先添加员工')
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
