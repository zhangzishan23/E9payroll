<template>
  <div class="dashboard-container space-y-4">
    <div class="apple-card p-4 bg-gradient-to-r from-blue-50 via-white to-blue-50">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div class="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg shadow-blue-200">
            <el-icon class="text-white text-2xl"><component :is="viewMode === 'leader' ? 'DataAnalysis' : 'Money'" /></el-icon>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-xl font-bold bg-gradient-to-r from-blue-700 to-blue-500 bg-clip-text text-transparent">
                {{ viewMode === 'leader' ? 'E9 数据看板' : 'E9 智能工作台' }}
              </h1>
              <span class="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded-full font-medium">{{ viewMode === 'leader' ? '管理视角' : '工作视角' }}</span>
            </div>
            <p class="text-gray-600 mt-1 text-sm">你好，{{ authStore.user?.display_name || '用户' }} 👋 欢迎使用<strong class="text-blue-600">工资计算管家</strong>，今天是 {{ today }}</p>
            <p class="text-blue-600 text-sm mt-0.5 font-medium">{{ currentPeriodDisplay }} {{ viewMode === 'leader' ? '管理视角数据概览' : '工资计算进行中' }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <el-date-picker v-model="statsPeriod" type="month" placeholder="选择月份" size="default" class="!w-40" value-format="YYYYMM" @change="fetchAllData" />
          <el-tooltip v-if="canSwitchView" :content="viewMode === 'leader' ? '切换到工作视角' : '切换到管理视角'">
            <el-button type="primary" circle @click="toggleViewMode">
              <el-icon><component :is="viewMode === 'leader' ? 'User' : 'DataAnalysis'" /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </div>

    <div class="apple-card p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold text-gray-700 flex items-center gap-2">
          <el-icon class="text-yellow-500"><Star /></el-icon> 我的常用
        </h3>
        <el-button type="primary" link @click="showAddFavorite = true">
          <el-icon class="mr-1"><Plus /></el-icon>添加常用
        </el-button>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div
          v-for="fav in favorites"
          :key="fav.id"
          class="apple-card p-3 text-center cursor-pointer hover:shadow-lg transition-all duration-200 border-2 border-transparent hover:border-blue-300 group relative"
          @click="handleFavoriteClick(fav)"
        >
          <el-button
            type="danger"
            link
            size="small"
            class="absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-opacity"
            @click.stop="removeFavorite(fav.id)"
          >
            <el-icon><Close /></el-icon>
          </el-button>
          <el-icon class="text-3xl mb-1" :class="getColorClass(fav.color)"><component :is="fav.icon || 'Menu'" /></el-icon>
          <div class="font-semibold text-sm">{{ fav.name }}</div>
        </div>
      </div>
    </div>

    <div class="apple-card p-4 bg-gradient-to-r from-amber-50 via-white to-amber-50" v-if="hasAnyTaxPermission && viewMode !== 'leader'">
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

    <div v-if="viewMode === 'employee' && hasSalaryPermission" class="apple-card p-4">
      <h3 class="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <el-icon class="text-blue-500"><List /></el-icon> 算薪进度追踪
      </h3>
      <p class="text-xs text-gray-500 mb-3">点击圆形图标可确认/取消确认步骤，点击标题可跳转至对应页面；绿色闪烁表示数据齐全可确认，红色表示有员工数据不全（仍可强制确认）</p>
      <div class="relative">
        <div class="absolute top-5 left-0 right-0 h-1 bg-gray-200 rounded"></div>
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
                class="absolute top-0 left-0 w-10 h-10 rounded-full animate-ping-ring bg-green-400"
              ></div>
              <div
                class="step-circle w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-base transition-all duration-300 relative z-10"
                :class="[getStepCircleClass(step), !step.is_confirmed && step.data_ready ? 'animate-green-blink' : '']"
                @click.stop="handleStepClick(step)"
              >
                <el-icon v-if="step.is_confirmed" :size="18"><Check /></el-icon>
                <span v-else>{{ index + 1 }}</span>
              </div>
            </div>
            <div class="mt-2 text-center" @click="goTo(step.route)">
              <div class="font-semibold text-xs" :class="getStepDescClass(step)">
                {{ step.title }}
              </div>
              <div v-if="step.is_force_confirmed" class="text-xs text-orange-500 mt-0.5">
                （强制确认）
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="viewMode === 'employee' && hasBusinessPermission" class="todo-container">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div class="lg:col-span-2 apple-card p-4">
          <h3 class="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <el-icon class="text-blue-500"><Calendar /></el-icon> 本月日程待办
          </h3>
          <div class="space-y-2">
            <div
              v-for="todo in todos"
              :key="todo.id"
              class="flex items-center gap-3 p-3 rounded-lg transition-all cursor-pointer hover:shadow-md"
              :class="getTodoBgClass(todo.status)"
              @click="todo.route && goTo(todo.route)"
            >
              <div
                class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                :class="getTodoIconBgClass(todo.status, todo.color)"
              >
                <el-icon v-if="todo.is_completed" class="text-white" :size="20"><Check /></el-icon>
                <el-icon v-else class="text-white" :size="20"><component :is="todo.icon || 'Calendar'" /></el-icon>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-sm" :class="todo.is_completed ? 'text-gray-400 line-through' : 'text-gray-800'">{{ todo.name }}</span>
                  <el-tag v-if="todo.status === 'overdue'" type="danger" size="small">已逾期</el-tag>
                  <el-tag v-else-if="todo.status === 'today'" type="warning" size="small">今天</el-tag>
                </div>
                <div class="text-xs text-gray-500 mt-0.5">
                  每月{{ todo.day_of_month }}日 · {{ todo.description }}
                  <span v-if="todo.days_until > 0" class="text-blue-500 ml-1">还有{{ todo.days_until }}天</span>
                </div>
              </div>
              <div class="flex-shrink-0">
                <el-icon class="text-gray-400"><ArrowRight /></el-icon>
              </div>
            </div>
            <div v-if="todos.length === 0" class="text-center py-8 text-gray-400">
              <el-icon class="text-4xl mb-2"><Finished /></el-icon>
              <div>🎉 本月所有待办已完成</div>
            </div>
          </div>
        </div>

        <div class="apple-card p-4">
          <h3 class="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <el-icon class="text-red-500"><Warning /></el-icon> 预警待办
          </h3>
          <div class="space-y-2">
            <div
              v-for="warn in warnings"
              :key="'warn-' + warn.id"
              class="flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors"
              :class="getWarnBgClass(warn.color)"
              @click="warn.route && goTo(warn.route)"
            >
              <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 animate-pulse" :class="getWarnIconBgClass(warn.color)">
                <el-icon class="text-white" :size="16"><component :is="warn.icon || 'Warning'" /></el-icon>
              </div>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-sm" :class="getWarnTitleClass(warn.color)">{{ warn.name }}</div>
                <div class="text-xs mt-0.5" :class="getWarnDescClass(warn.color)">{{ warn.description }}</div>
              </div>
            </div>
            <div v-if="warnings.length === 0" class="text-center py-8 text-gray-400">
              <el-icon class="text-4xl mb-2"><CircleCheck /></el-icon>
              <div>暂无预警事项</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="viewMode === 'leader'" class="leader-view">
      <div class="apple-card p-4 mb-4">
        <div class="flex flex-wrap items-center gap-3">
          <div class="flex items-center gap-2">
            <el-icon class="text-gray-500"><Filter /></el-icon>
            <span class="text-sm text-gray-600 font-medium">筛选条件：</span>
          </div>
          <el-select v-model="chartFilter.dept_id" placeholder="选择部门" clearable class="!w-40" @change="fetchCharts">
            <el-option v-for="dept in departments" :key="dept.id" :label="dept.name" :value="dept.id" />
          </el-select>
          <el-input v-model="chartFilter.employee_name" placeholder="搜索员工姓名" clearable class="!w-44" @keyup.enter="fetchCharts" @clear="fetchCharts">
            <template #prefix><el-icon class="text-gray-400"><Search /></el-icon></template>
          </el-input>
          <el-select v-model="chartFilter.months" placeholder="时间范围" class="!w-28" @change="fetchCharts">
            <el-option label="近3个月" :value="3" />
            <el-option label="近6个月" :value="6" />
            <el-option label="近12个月" :value="12" />
          </el-select>
          <el-button type="primary" @click="fetchCharts" :loading="chartsLoading">
            <el-icon class="mr-1"><Refresh /></el-icon>刷新数据
          </el-button>
          <el-button v-if="chartFilter.dept_id || chartFilter.employee_name" @click="resetFilters">
            <el-icon class="mr-1"><RefreshLeft /></el-icon>重置筛选
          </el-button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
        <div class="apple-card p-4 bg-gradient-to-br from-blue-50 to-blue-100">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm text-blue-600 font-medium">在职员工</div>
              <div class="text-3xl font-bold text-blue-700 mt-1">{{ charts.summary.total_employees }}</div>
            </div>
            <div class="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center">
              <el-icon class="text-white text-xl"><User /></el-icon>
            </div>
          </div>
        </div>
        <div class="apple-card p-4 bg-gradient-to-br from-green-50 to-green-100">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm text-green-600 font-medium">本月用人成本</div>
              <div class="text-3xl font-bold text-green-700 mt-1">¥{{ formatMoney(charts.summary.total_cost) }}</div>
            </div>
            <div class="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center">
              <el-icon class="text-white text-xl"><Wallet /></el-icon>
            </div>
          </div>
        </div>
        <div class="apple-card p-4 bg-gradient-to-br from-purple-50 to-purple-100">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm text-purple-600 font-medium">人均工资</div>
              <div class="text-3xl font-bold text-purple-700 mt-1">¥{{ formatMoney(charts.summary.avg_cost) }}</div>
            </div>
            <div class="w-12 h-12 rounded-full bg-purple-500 flex items-center justify-center">
              <el-icon class="text-white text-xl"><TrendCharts /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div class="apple-card p-4">
          <h3 class="text-base font-semibold text-gray-700 mb-3">📈 月度用人成本趋势</h3>
          <v-chart class="chart" :option="monthlyCostOption" autoresize />
        </div>
        <div class="apple-card p-4">
          <h3 class="text-base font-semibold text-gray-700 mb-3">🏢 各部门用人成本占比</h3>
          <v-chart class="chart" :option="deptCostOption" autoresize />
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div class="apple-card p-4">
          <h3 class="text-base font-semibold text-gray-700 mb-3">📊 绩效趋势</h3>
          <v-chart class="chart" :option="perfTrendOption" autoresize />
        </div>
        <div class="apple-card p-4">
          <h3 class="text-base font-semibold text-gray-700 mb-3">🎯 各部门平均绩效</h3>
          <v-chart class="chart" :option="deptPerfOption" autoresize />
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div class="lg:col-span-2 apple-card p-4">
          <h3 class="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <el-icon class="text-blue-500"><List /></el-icon> 算薪进度追踪
          </h3>
          <div class="relative">
            <div class="absolute top-5 left-0 right-0 h-1 bg-gray-200 rounded"></div>
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
                    class="absolute top-0 left-0 w-10 h-10 rounded-full animate-ping-ring bg-green-400"
                  ></div>
                  <div
                    class="step-circle w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-base transition-all duration-300 relative z-10"
                    :class="[getStepCircleClass(step), !step.is_confirmed && step.data_ready ? 'animate-green-blink' : '']"
                    @click.stop="handleStepClick(step)"
                  >
                    <el-icon v-if="step.is_confirmed" :size="18"><Check /></el-icon>
                    <span v-else>{{ index + 1 }}</span>
                  </div>
                </div>
                <div class="mt-2 text-center" @click="goTo(step.route)">
                  <div class="font-semibold text-xs" :class="getStepDescClass(step)">
                    {{ step.title }}
                  </div>
                  <div v-if="step.is_force_confirmed" class="text-xs text-orange-500 mt-0.5">
                    （强制确认）
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="apple-card p-4">
          <h3 class="text-base font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <el-icon class="text-red-500"><Warning /></el-icon> 预警事项
          </h3>
          <div class="space-y-2">
            <div
              v-for="warn in warnings"
              :key="'warn2-' + warn.id"
              class="flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors"
              :class="getWarnBgClass(warn.color, true)"
              @click="warn.route && goTo(warn.route)"
            >
              <el-icon class="flex-shrink-0" :size="16" :class="getWarnIconClass(warn.color)"><component :is="warn.icon || 'Warning'" /></el-icon>
              <span class="text-xs truncate" :class="getWarnTitleClass(warn.color)">{{ warn.name }}: {{ warn.description }}</span>
            </div>
            <div v-if="warnings.length === 0" class="text-center py-4 text-gray-400 text-sm">
              暂无预警事项
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showAddFavorite" title="添加常用功能" width="500px" append-to-body>
      <el-form label-width="80px">
        <el-form-item label="功能名称">
          <el-input v-model="newFav.name" placeholder="请输入功能名称" />
        </el-form-item>
        <el-form-item label="选择功能">
          <el-select v-model="newFav.route" placeholder="请选择要添加的功能" class="w-full" @change="onFavRouteChange">
            <el-option
              v-for="item in availableMenuItems"
              :key="item.route"
              :label="item.label"
              :value="item.route"
            >
              <div class="flex items-center gap-2">
                <el-icon><component :is="item.icon" /></el-icon>
                <span>{{ item.label }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddFavorite = false">取消</el-button>
        <el-button type="primary" @click="addFavorite">添加</el-button>
      </template>
    </el-dialog>

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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Money, Calendar, CreditCard, TrendCharts, Checked, Document, User, Setting,
  Clock, CircleClose, CircleCheck, Finished, Check, Download, UploadFilled,
  Star, Plus, Close, List, Warning, ArrowRight, UserFilled, Menu, Wallet, DataAnalysis,
  Filter, Search, Refresh, RefreshLeft
} from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent, GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import api from '../api'
import { getDefaultPeriod, formatPeriodDisplay } from '../utils/date.js'
import { useAuthStore } from '../stores/auth'

use([CanvasRenderer, BarChart, LineChart, PieChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const router = useRouter()
const authStore = useAuthStore()

const statsPeriod = ref(getDefaultPeriod())
const currentPeriodDisplay = computed(() => formatPeriodDisplay(statsPeriod.value))
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const viewMode = ref('employee')
const canAccessLeaderView = ref(false)
const canAccessWorkView = ref(false)
const canSwitchView = ref(false)
const charts = reactive({
  summary: { total_employees: 0, total_cost: 0, avg_cost: 0, avg_attend_rate: 0 },
  charts: { dept_costs: [], monthly_costs: [], dept_perf: [], perf_trend: [] }
})
const departments = ref([{ id: 0, name: '全部部门' }])
const chartFilter = reactive({
  dept_id: 0,
  employee_name: '',
  months: 6
})
const chartsLoading = ref(false)
const favorites = ref([])
const todos = ref([])
const warnings = ref([])
const salarySteps = ref([])

const showAddFavorite = ref(false)
const newFav = reactive({ name: '', route: '', module_key: '', icon: 'Menu', color: 'blue' })

const travelImportVisible = ref(false)
const travelImporting = ref(false)
const travelFile = ref(null)
const travelUploadRef = ref(null)
const taxImportVisible = ref(false)
const taxImporting = ref(false)
const taxFile = ref(null)
const taxUploadRef = ref(null)

const hasAnyTaxPermission = computed(() => {
  return authStore.hasAnyPermission('salary:tax_export', 'salary:tax_import', 'salary:travel_import')
})

const hasSalaryPermission = computed(() => {
  return authStore.hasAnyPermission(
    'salary:view', 'salary:create', 'salary:edit', 'salary:delete', 'salary:check', 'salary:step_confirm', 'salary:export',
    'salary:tax_export', 'salary:tax_import', 'salary:travel_import'
  )
})

const hasBusinessPermission = computed(() => {
  return authStore.hasAnyPermission(
    'employee:view', 'attendance:view', 'performance:view', 'insurance:view',
    'salary:view', 'approval:view', 'report:view'
  )
})

const availableMenuItems = [
  { route: '/employees', label: '档案管理', module_key: 'employee', icon: 'User', color: 'indigo' },
  { route: '/attendance', label: '考勤管理', module_key: 'attendance', icon: 'Calendar', color: 'green' },
  { route: '/performance', label: '绩效评分', module_key: 'performance', icon: 'TrendCharts', color: 'purple' },
  { route: '/insurance', label: '社保公积金', module_key: 'insurance', icon: 'CreditCard', color: 'orange' },
  { route: '/salary', label: '薪资计算', module_key: 'salary', icon: 'Money', color: 'blue' },
  { route: '/approval', label: '审批流程', module_key: 'approval', icon: 'Checked', color: 'cyan' },
  { route: '/reports', label: '报表导出', module_key: 'report', icon: 'Document', color: 'teal' },
  { route: '/system/users', label: '用户管理', module_key: 'system', icon: 'UserFilled', color: 'gray' },
  { route: '/system/roles', label: '角色管理', module_key: 'system', icon: 'Setting', color: 'gray' },
  { route: '/system/dict', label: '数据字典', module_key: 'system', icon: 'Menu', color: 'gray' },
  { route: '/system/logs', label: '操作日志', module_key: 'system', icon: 'Document', color: 'gray' },
  { route: '/system/backup', label: '数据备份', module_key: 'system', icon: 'Wallet', color: 'gray' },
]

const chartBaseStyle = {
  textStyle: { fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }
}

const monthlyCostOption = computed(() => ({
  ...chartBaseStyle,
  tooltip: { trigger: 'axis', formatter: '{b}: ¥{c}', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e5e7eb', textStyle: { color: '#374151' } },
  grid: { left: 60, right: 20, top: 30, bottom: 40 },
  xAxis: { type: 'category', data: charts.charts.monthly_costs.map(i => i.label), axisLine: { lineStyle: { color: '#e5e7eb' } }, axisLabel: { color: '#6b7280' } },
  yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f3f4f6' } }, axisLabel: { color: '#6b7280', formatter: (val) => val >= 10000 ? (val/10000).toFixed(1) + '万' : val } },
  series: [{
    data: charts.charts.monthly_costs.map(i => i.value),
    type: 'line',
    smooth: true,
    areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(37, 99, 235, 0.3)' }, { offset: 1, color: 'rgba(37, 99, 235, 0.05)' }] } },
    lineStyle: { color: '#2563eb', width: 3 },
    itemStyle: { color: '#2563eb' },
    symbol: 'circle',
    symbolSize: 8
  }]
}))

const deptCostOption = computed(() => {
  const data = charts.charts.dept_costs
  const colors = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16', '#f97316']
  return {
    ...chartBaseStyle,
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e5e7eb', textStyle: { color: '#374151' } },
    color: colors,
    series: [{
      type: 'pie',
      radius: ['40%', '62%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
      label: {
        show: true,
        position: 'outer',
        margin: 8,
        formatter: '{b}\n¥{c} ({d}%)',
        fontSize: 12,
        fontWeight: 500,
        color: '#374151',
        lineHeight: 18
      },
      labelLine: {
        show: true,
        length: 10,
        length2: 8,
        smooth: false
      },
      labelLayout: {
        hideOverlap: false
      },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#111827' },
        itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.2)' }
      },
      data: data.length ? data : [{ name: '暂无数据', value: 1, itemStyle: { color: '#e5e7eb' }, label: { formatter: '暂无数据' } }]
    }]
  }
})

const perfTrendOption = computed(() => ({
  ...chartBaseStyle,
  tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e5e7eb', textStyle: { color: '#374151' } },
  grid: { left: 50, right: 20, top: 30, bottom: 40 },
  xAxis: { type: 'category', data: charts.charts.perf_trend.map(i => i.label), axisLine: { lineStyle: { color: '#e5e7eb' } }, axisLabel: { color: '#6b7280' } },
  yAxis: { type: 'value', min: 0.8, max: 1.2, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f3f4f6' } }, axisLabel: { color: '#6b7280' } },
  series: [{
    data: charts.charts.perf_trend.map(i => i.value),
    type: 'line',
    smooth: true,
    areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(139, 92, 246, 0.3)' }, { offset: 1, color: 'rgba(139, 92, 246, 0.05)' }] } },
    lineStyle: { color: '#8b5cf6', width: 3 },
    itemStyle: { color: '#8b5cf6' },
    symbol: 'circle',
    symbolSize: 8,
    connectNulls: true
  }]
}))

const deptPerfOption = computed(() => ({
  ...chartBaseStyle,
  tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.95)', borderColor: '#e5e7eb', textStyle: { color: '#374151' } },
  grid: { left: 50, right: 20, top: 30, bottom: 60 },
  xAxis: { type: 'category', data: charts.charts.dept_perf.map(i => i.name), axisLine: { lineStyle: { color: '#e5e7eb' } }, axisLabel: { color: '#6b7280', rotate: 30, fontSize: 11 } },
  yAxis: { type: 'value', min: 0.8, max: 1.2, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f3f4f6' } }, axisLabel: { color: '#6b7280' } },
  series: [{
    data: charts.charts.dept_perf.map(i => i.value),
    type: 'bar',
    itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#10b981' }, { offset: 1, color: '#34d399' }] }, borderRadius: [6, 6, 0, 0] },
    barWidth: '50%'
  }]
}))

function formatMoney(val) {
  if (val == null || val === 0) return '0'
  return Number(val).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function getColorClass(color) {
  const map = {
    blue: 'text-blue-500', green: 'text-green-500', orange: 'text-orange-500',
    red: 'text-red-500', purple: 'text-purple-500', cyan: 'text-cyan-500',
    indigo: 'text-indigo-500', amber: 'text-amber-500', teal: 'text-teal-500', gray: 'text-gray-500'
  }
  return map[color] || map.blue
}

function getTodoBgClass(status) {
  if (status === 'completed') return 'bg-gray-50'
  if (status === 'overdue') return 'bg-red-50 border border-red-200'
  if (status === 'today') return 'bg-amber-50 border border-amber-200'
  return 'bg-white border border-gray-100'
}

function getTodoIconBgClass(status, color) {
  if (status === 'completed') return 'bg-green-500'
  if (status === 'overdue') return 'bg-red-500'
  if (status === 'today') return 'bg-amber-500'
  const map = {
    blue: 'bg-blue-500', green: 'bg-green-500', orange: 'bg-orange-500',
    red: 'bg-red-500', purple: 'bg-purple-500', cyan: 'bg-cyan-500',
    indigo: 'bg-indigo-500', amber: 'bg-amber-500', teal: 'bg-teal-500', gray: 'bg-gray-500'
  }
  return map[color] || map.blue
}

function getWarnBgClass(color, compact = false) {
  const map = {
    red: compact ? 'bg-red-50 hover:bg-red-100' : 'bg-red-50 border border-red-100 hover:bg-red-100',
    orange: compact ? 'bg-orange-50 hover:bg-orange-100' : 'bg-orange-50 border border-orange-100 hover:bg-orange-100',
    pink: compact ? 'bg-pink-50 hover:bg-pink-100' : 'bg-pink-50 border border-pink-100 hover:bg-pink-100',
    gray: compact ? 'bg-gray-50 hover:bg-gray-100' : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
  }
  return map[color] || map.red
}

function getWarnIconBgClass(color) {
  const map = {
    red: 'bg-red-500',
    orange: 'bg-orange-500',
    pink: 'bg-pink-500',
    gray: 'bg-gray-500'
  }
  return map[color] || map.red
}

function getWarnIconClass(color) {
  const map = {
    red: 'text-red-500',
    orange: 'text-orange-500',
    pink: 'text-pink-500',
    gray: 'text-gray-500'
  }
  return map[color] || map.red
}

function getWarnTitleClass(color) {
  const map = {
    red: 'text-red-700',
    orange: 'text-orange-700',
    pink: 'text-pink-700',
    gray: 'text-gray-700'
  }
  return map[color] || map.red
}

function getWarnDescClass(color) {
  const map = {
    red: 'text-red-500',
    orange: 'text-orange-500',
    pink: 'text-pink-500',
    gray: 'text-gray-500'
  }
  return map[color] || map.red
}

function getStepCircleClass(step) {
  if (step.is_confirmed) {
    if (step.is_force_confirmed) return 'bg-orange-500 shadow-lg shadow-orange-200 cursor-pointer hover:scale-110 hover:bg-orange-600'
    return 'bg-green-500 shadow-lg shadow-green-200 cursor-pointer hover:scale-110 hover:bg-green-600'
  }
  if (step.key === 'salary' && step.prerequisites_met === false) return 'bg-gray-300 shadow-none cursor-not-allowed'
  if (step.data_ready) return 'bg-green-500 shadow-lg shadow-green-200 cursor-pointer hover:scale-110 hover:bg-green-600'
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

function goTo(path) {
  if (path) router.push(path)
}

async function toggleViewMode() {
  if (!canSwitchView.value) {
    return
  }
  const oldMode = viewMode.value
  const newMode = oldMode === 'leader' ? 'employee' : 'leader'
  if (newMode === 'leader' && !canAccessLeaderView.value) {
    ElMessage.warning('您没有管理视角权限')
    return
  }
  if (newMode === 'employee' && !canAccessWorkView.value) {
    ElMessage.warning('您没有工作视角权限')
    return
  }
  try {
    await api.put('/dashboard/preferences', { dashboard_view: newMode }, { silent: true })
    viewMode.value = newMode
    if (newMode === 'leader') {
      fetchCharts()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '切换视角失败，请稍后重试')
  }
}

async function fetchOverview() {
  try {
    const res = await api.get('/dashboard/overview', { params: { period: statsPeriod.value } })
    const d = res.data
    canAccessLeaderView.value = d.can_access_leader_view || false
    canAccessWorkView.value = d.can_access_work_view || false
    canSwitchView.value = d.can_switch_view || false
    viewMode.value = d.view_mode || 'employee'
    todos.value = d.todos || []
    warnings.value = d.warnings || []
    favorites.value = d.favorites || []
  } catch (e) {
    console.error('Failed to fetch overview:', e)
  }
}

async function fetchCharts() {
  chartsLoading.value = true
  try {
    const params = { period: statsPeriod.value, months: chartFilter.months }
    if (chartFilter.dept_id && chartFilter.dept_id !== 0) {
      params.dept_id = chartFilter.dept_id
    }
    if (chartFilter.employee_name && chartFilter.employee_name.trim()) {
      params.employee_name = chartFilter.employee_name.trim()
    }
    const res = await api.get('/dashboard/charts', { params })
    Object.assign(charts, res.data)
    if (res.data.departments) {
      departments.value = res.data.departments
    }
  } catch (e) {
    console.error('Failed to fetch charts:', e)
  } finally {
    chartsLoading.value = false
  }
}

function resetFilters() {
  chartFilter.dept_id = 0
  chartFilter.employee_name = ''
  chartFilter.months = 6
  fetchCharts()
}

async function fetchSteps() {
  try {
    const res = await api.get('/reports/stats', { params: { period: statsPeriod.value } })
    salarySteps.value = res.data.steps || []
  } catch (e) {}
}

async function fetchAllData() {
  const tasks = [fetchOverview()]
  if (hasSalaryPermission.value) {
    tasks.push(fetchSteps())
  } else {
    salarySteps.value = []
  }
  await Promise.all(tasks)
  if (viewMode.value === 'leader' && canAccessLeaderView.value) {
    await fetchCharts()
  }
}

watch(viewMode, (newVal) => {
  if (newVal === 'leader' && canAccessLeaderView.value) {
    fetchCharts()
  }
})

function onFavRouteChange(route) {
  const item = availableMenuItems.find(i => i.route === route)
  if (item) {
    newFav.name = item.label
    newFav.module_key = item.module_key
    newFav.icon = item.icon
    newFav.color = item.color
  }
}

async function addFavorite() {
  if (!newFav.route) {
    ElMessage.warning('请选择要添加的功能')
    return
  }
  try {
    await api.post('/dashboard/favorites', newFav)
    ElMessage.success('添加成功')
    showAddFavorite.value = false
    newFav.name = ''
    newFav.route = ''
    await fetchOverview()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  }
}

async function removeFavorite(id) {
  try {
    await ElMessageBox.confirm('确定要从常用中移除吗？', '移除确认', { type: 'warning' })
    await api.delete(`/dashboard/favorites/${id}`)
    ElMessage.success('已移除')
    await fetchOverview()
  } catch {}
}

async function handleFavoriteClick(fav) {
  goTo(fav.route)
  try {
    await api.post(`/dashboard/favorites/${fav.id}/click`)
  } catch (e) {}
}

async function handleStepClick(step) {
  if (!authStore.hasPermission('salary:step_confirm')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
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
      await ElMessageBox.confirm(`确定要取消确认「${step.title}」吗？`, '取消确认', {
        confirmButtonText: '确定取消', cancelButtonText: '返回', type: 'warning', confirmButtonClass: 'el-button--danger'
      })
      await api.post('/reports/steps/confirm', { period: statsPeriod.value, step_key: step.key, is_confirmed: false })
      ElMessage.success('已取消确认')
      fetchAllData()
    } catch {}
  } else {
    let confirmMsg = `确定要确认「${step.title}」吗？`
    let confirmType = 'success'
    let isForce = false
    if (!step.data_ready) {
      isForce = true
      confirmMsg = step.missing_count > 0 ? `「${step.title}」还有 ${step.missing_count} 名员工数据不全，确定要强制确认吗？` : `「${step.title}」暂无数据，确定要强制确认吗？`
      confirmType = 'warning'
    }
    try {
      await ElMessageBox.confirm(confirmMsg, isForce ? '强制确认' : '确认步骤', {
        confirmButtonText: isForce ? '仍然确认' : '确定', cancelButtonText: '取消', type: confirmType,
        confirmButtonClass: isForce ? 'el-button--warning' : 'el-button--success'
      })
      await api.post('/reports/steps/confirm', { period: statsPeriod.value, step_key: step.key, is_confirmed: true })
      ElMessage.success(isForce ? '已强制确认' : '确认成功')
      fetchAllData()
    } catch {}
  }
}

async function extractBlobError(blob) {
  try {
    const text = await blob.text()
    const json = JSON.parse(text)
    return json.detail || '请求失败'
  } catch { return '请求失败' }
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
      if (i < files.length - 1) await new Promise(resolve => setTimeout(resolve, 300))
    } catch (e) { return }
  }
  ElMessage.success('报税模板导出成功，共3个文件')
}

function showTravelImport() {
  if (!authStore.hasPermission('salary:travel_import')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  travelFile.value = null
  if (travelUploadRef.value) travelUploadRef.value.clearFiles()
  travelImportVisible.value = true
}

function showTaxImport() {
  if (!authStore.hasPermission('salary:tax_import')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  taxFile.value = null
  if (taxUploadRef.value) taxUploadRef.value.clearFiles()
  taxImportVisible.value = true
}

function handleTravelFileChange(file) { travelFile.value = file.raw }
function handleTaxFileChange(file) { taxFile.value = file.raw }

async function doTravelImport() {
  if (!authStore.hasPermission('salary:travel_import')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  if (!travelFile.value) { ElMessage.warning('请先选择要上传的Excel文件'); return }
  const formData = new FormData()
  formData.append('file', travelFile.value)
  travelImporting.value = true
  try {
    const res = await api.post(`/salary/import-travel-untaxed/${statsPeriod.value}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(res.data.message)
    travelImportVisible.value = false
    await fetchAllData()
  } catch (e) {} finally { travelImporting.value = false }
}

async function doTaxImport() {
  if (!authStore.hasPermission('salary:tax_import')) {
    ElMessage.warning('您没有该操作权限，请联系管理员')
    return
  }
  if (!taxFile.value) { ElMessage.warning('请先选择要上传的Excel文件'); return }
  const formData = new FormData()
  formData.append('file', taxFile.value)
  taxImporting.value = true
  try {
    const res = await api.post(`/salary/upload-tax-excel/${statsPeriod.value}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(res.data.message)
    taxImportVisible.value = false
    await fetchAllData()
  } catch (e) {} finally { taxImporting.value = false }
}

onMounted(() => {
  fetchAllData()
})
</script>

<style scoped>
.dashboard-container .chart {
  height: 300px;
}
.step-circle {
  border: 2px solid white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}
.step-circle:hover {
  transform: scale(1.1);
}
</style>
