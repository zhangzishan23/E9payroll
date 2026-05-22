<template>
  <div class="space-y-6">
    <div class="apple-card p-6">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-gray-700">数据统计中心</h3>
        <el-date-picker v-model="statsPeriod" type="month" placeholder="选择月份" class="w-36" value-format="YYYYMM" @change="fetchStats" />
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
      <h3 class="text-lg font-semibold text-gray-700 mb-6">报表导出中心</h3>

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
          <el-date-picker v-model="salaryPeriod" type="month" placeholder="选择月份" class="w-48 mx-auto mb-4" size="default" value-format="YYYYMM" />
          <el-button type="primary" size="default" @click="exportReport('salary')">导出Excel</el-button>
        </div>

        <div class="apple-card p-6 text-center border-2 border-dashed border-orange-200 hover:border-orange-400 hover:shadow-lg transition-shadow">
          <div class="flex items-center gap-2 justify-center mb-4">
            <el-icon class="text-4xl text-orange-500"><Calendar /></el-icon>
            <span class="font-semibold text-lg">考勤统计表</span>
          </div>
          <el-date-picker v-model="attPeriod" type="month" placeholder="选择月份" class="w-48 mx-auto mb-4" size="default" value-format="YYYYMM" />
          <el-button type="primary" size="default" @click="exportReport('attendance')">导出Excel</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Document, Calendar } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const salaryPeriod = ref('202604')
const attPeriod = ref('202604')
const statsPeriod = ref('202604')

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

function fmtMoney(val) {
  if (val == null || val === 0) return '¥0'
  return '¥' + Number(val).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
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

onMounted(() => {
  fetchStats()
})
</script>