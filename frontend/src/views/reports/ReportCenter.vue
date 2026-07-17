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
        <h3 class="text-lg font-semibold text-gray-700">合同到期预警</h3>
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-500">提前预警天数：</span>
          <el-input-number v-model="warningDays" :min="1" :max="365" size="small" @change="fetchContractWarning" />
        </div>
      </div>
      <div v-if="contractWarning.list.length > 0">
        <div class="mb-3 flex items-center gap-2">
          <el-tag type="warning" size="small">共 {{ contractWarning.total_count }} 人合同即将到期</el-tag>
          <el-tag v-if="contractWarning.expired_count > 0" type="danger" size="small">{{ contractWarning.expired_count }} 人已过期</el-tag>
          <el-button type="primary" size="small" text @click="exportContractWarning" v-permission="'report:export'">导出预警名单</el-button>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <div
            v-for="item in contractWarning.list"
            :key="item.id"
            class="p-3 rounded-lg border"
            :class="item.is_expired ? 'bg-red-50 border-red-200' : 'bg-orange-50 border-orange-200'"
          >
            <div class="flex items-center gap-2">
              <el-tag :type="item.is_expired ? 'danger' : 'warning'" size="small">
                {{ item.is_expired ? '已过期' : `剩余${item.days_remaining}天` }}
              </el-tag>
              <span class="font-medium text-sm">{{ item.display_text }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-center py-8 text-gray-400">
        <el-icon class="text-4xl mb-2"><CircleCheck /></el-icon>
        <div>暂无合同到期预警</div>
      </div>
    </div>

    <div class="apple-card p-6">
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-lg font-semibold text-gray-700">报表导出中心</h3>
        <el-button type="primary" @click="showConfigDialog" v-permission="'report:export'">
          <el-icon><Setting /></el-icon>
          导出表配置
        </el-button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="apple-card p-6 text-center cursor-pointer hover:shadow-lg transition-shadow border-2 border-dashed border-blue-200 hover:border-blue-400" @click="exportReport('roster')">
          <el-icon class="text-5xl text-blue-500 mb-4"><Document /></el-icon>
          <div class="font-semibold text-lg">员工花名册</div>
          <div class="text-sm text-gray-500 mt-2">导出全量员工基本信息</div>
          <el-button type="primary" class="mt-4" size="default" @click.stop="exportReport('roster')" v-permission="'report:export'">立即导出</el-button>
        </div>

        <div class="apple-card p-6 text-center border-2 border-dashed border-green-200 hover:border-green-400 hover:shadow-lg transition-shadow">
          <div class="flex items-center gap-2 justify-center mb-3">
            <el-date-picker v-model="salaryPeriod" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" />
          </div>
          <div class="flex items-center gap-2 justify-center">
            <el-select v-model="selectedTemplate" placeholder="选择模板" size="small" class="!w-32" clearable>
              <el-option v-for="tpl in salaryTemplates" :key="tpl.id" :label="tpl.name + (tpl.is_default ? ' (默认)' : '')" :value="tpl.id" />
            </el-select>
            <el-button type="primary" size="small" @click="exportSalaryByTemplate" v-permission="'report:export'">导出Excel</el-button>
          </div>
        </div>

        <div class="apple-card p-6 text-center border-2 border-dashed border-orange-200 hover:border-orange-400 hover:shadow-lg transition-shadow">
          <div class="flex items-center gap-2 justify-center mb-4">
            <el-icon class="text-4xl text-orange-500"><Calendar /></el-icon>
            <span class="font-semibold text-lg">考勤统计表</span>
          </div>
          <div class="flex items-center gap-2 justify-center mb-4">
            <el-date-picker v-model="attPeriod" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" />
            <el-button type="primary" size="small" @click="exportReport('attendance')" v-permission="'report:export'">导出Excel</el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="configVisible" title="导出表配置" width="900px" append-to-body>
      <el-tabs v-model="configTab" @tab-change="onConfigTabChange">
        <el-tab-pane label="薪资表模板" name="salary">
          <div class="mb-4 flex justify-between items-center">
            <div class="text-sm text-gray-500">配置不同用途的薪资导出表字段</div>
            <el-button type="primary" size="small" @click="createNewTemplate" v-permission="'report:export'">
              <el-icon><Plus /></el-icon>
              新建模板
            </el-button>
          </div>
          <el-table :data="filteredTemplates" border stripe size="small">
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
                <el-link type="primary" size="small" @click="editTemplate(row)" v-permission="'report:export'">编辑</el-link>
                <el-link v-if="!row.is_default" type="success" size="small" class="ml-2" @click="setDefaultTemplate(row)" v-permission="'report:export'">设为默认</el-link>
                <el-link v-if="!row.is_default" type="danger" size="small" class="ml-2" @click="deleteTemplate(row)" v-permission="'report:export'">删除</el-link>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="花名册模板" name="roster">
          <div class="mb-4 flex justify-between items-center">
            <div class="text-sm text-gray-500">配置员工花名册导出表字段</div>
            <el-button type="primary" size="small" @click="createNewTemplate" v-permission="'report:export'">
              <el-icon><Plus /></el-icon>
              新建模板
            </el-button>
          </div>
          <el-table :data="filteredTemplates" border stripe size="small">
            <el-table-column prop="name" label="模板名称" width="150" />
            <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
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
                <el-link type="primary" size="small" @click="editTemplate(row)" v-permission="'report:export'">编辑</el-link>
                <el-link v-if="!row.is_default" type="success" size="small" class="ml-2" @click="setDefaultTemplate(row)" v-permission="'report:export'">设为默认</el-link>
                <el-link v-if="!row.is_default" type="danger" size="small" class="ml-2" @click="deleteTemplate(row)" v-permission="'report:export'">删除</el-link>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="考勤表模板" name="attendance">
          <div class="mb-4 flex justify-between items-center">
            <div class="text-sm text-gray-500">配置考勤统计表导出表字段</div>
            <el-button type="primary" size="small" @click="createNewTemplate" v-permission="'report:export'">
              <el-icon><Plus /></el-icon>
              新建模板
            </el-button>
          </div>
          <el-table :data="filteredTemplates" border stripe size="small">
            <el-table-column prop="name" label="模板名称" width="150" />
            <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
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
                <el-link type="primary" size="small" @click="editTemplate(row)" v-permission="'report:export'">编辑</el-link>
                <el-link v-if="!row.is_default" type="success" size="small" class="ml-2" @click="setDefaultTemplate(row)" v-permission="'report:export'">设为默认</el-link>
                <el-link v-if="!row.is_default" type="danger" size="small" class="ml-2" @click="deleteTemplate(row)" v-permission="'report:export'">删除</el-link>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="社保表模板" name="social_insurance">
          <div class="mb-4 flex justify-between items-center">
            <div class="text-sm text-gray-500">配置社保公积金导出表字段</div>
            <el-button type="primary" size="small" @click="createNewTemplate" v-permission="'report:export'">
              <el-icon><Plus /></el-icon>
              新建模板
            </el-button>
          </div>
          <el-table :data="filteredTemplates" border stripe size="small">
            <el-table-column prop="name" label="模板名称" width="150" />
            <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
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
                <el-link type="primary" size="small" @click="editTemplate(row)" v-permission="'report:export'">编辑</el-link>
                <el-link v-if="!row.is_default" type="success" size="small" class="ml-2" @click="setDefaultTemplate(row)" v-permission="'report:export'">设为默认</el-link>
                <el-link v-if="!row.is_default" type="danger" size="small" class="ml-2" @click="deleteTemplate(row)" v-permission="'report:export'">删除</el-link>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <el-dialog v-model="editVisible" :title="editingTemplate.id ? '编辑模板' : '新建模板'" width="800px" append-to-body>
      <el-form :model="editingTemplate" label-width="100px" size="small">
        <el-form-item label="模板名称" required>
          <el-input v-model="editingTemplate.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item v-if="configTab === 'salary'" label="模板类型" required>
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
        <div class="font-semibold text-sm mb-3">字段选择</div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-gray-500">可选字段</span>
              <el-button type="primary" link size="small" @click="selectAllFields">全选</el-button>
            </div>
            <div class="border rounded p-2 max-h-80 overflow-y-auto bg-gray-50">
              <div
                v-for="f in currentAvailableFields.filter(f => !selectedFieldKeys.includes(f.key))"
                :key="f.key"
                class="px-2 py-1.5 mb-1 bg-white rounded border cursor-move hover:bg-blue-50 hover:border-blue-300 text-sm flex items-center justify-between"
                @click="addField(f)"
              >
                <span>{{ f.label }}</span>
                <el-icon class="text-green-500"><Plus /></el-icon>
              </div>
              <div v-if="currentAvailableFields.filter(f => !selectedFieldKeys.includes(f.key)).length === 0" class="text-center text-gray-400 py-4 text-sm">
                所有字段已添加
              </div>
            </div>
          </div>
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs text-gray-500">已选字段（拖拽或点击箭头调整顺序，点击 × 移除）</span>
              <el-button type="danger" link size="small" @click="clearAllFields" v-if="selectedFields.length > 0">清空</el-button>
            </div>
            <div class="border rounded p-2 max-h-80 overflow-y-auto bg-blue-50">
              <div
                v-for="(f, idx) in selectedFields"
                :key="f.key"
                class="px-2 py-1.5 mb-1 bg-white rounded border cursor-move hover:bg-orange-50 hover:border-orange-300 text-sm flex items-center justify-between select-none"
                :class="{ 'opacity-50': dragIndex === idx, 'border-blue-400 bg-blue-50': dragOverIndex === idx }"
                draggable="true"
                @dragstart="handleDragStart(idx)"
                @dragover.prevent="handleDragOver(idx)"
                @dragleave="handleDragLeave"
                @drop="handleDrop(idx)"
                @dragend="handleDragEnd"
              >
                <span class="flex items-center gap-2">
                  <el-icon class="text-gray-400 cursor-move"><Rank /></el-icon>
                  <span>{{ idx + 1 }}. {{ f.label }}</span>
                </span>
                <span class="flex items-center gap-1">
                  <el-icon
                    class="text-gray-400 hover:text-blue-500 cursor-pointer"
                    :class="{ 'opacity-30 cursor-not-allowed': idx === 0 }"
                    @click.stop="moveFieldUp(idx)"
                  ><Top /></el-icon>
                  <el-icon
                    class="text-gray-400 hover:text-blue-500 cursor-pointer"
                    :class="{ 'opacity-30 cursor-not-allowed': idx === selectedFields.length - 1 }"
                    @click.stop="moveFieldDown(idx)"
                  ><Bottom /></el-icon>
                  <el-icon class="text-red-500 cursor-pointer" @click="removeField(f.key)"><Close /></el-icon>
                </span>
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
import { Document, Calendar, Setting, Plus, Close, Rank, CircleCheck, Top, Bottom } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import { getDefaultPeriod } from '../../utils/date.js'
import { ALL_EXPORT_FIELDS } from '../../config/columns'

const TAB_TYPE_MAP = {
  salary: ['salary_finance', 'salary_slip', 'custom'],
  roster: ['roster'],
  attendance: ['attendance'],
  social_insurance: ['social_insurance']
}

const defaultPeriod = getDefaultPeriod()
const salaryPeriod = ref(defaultPeriod)
const attPeriod = ref(defaultPeriod)
const statsPeriod = ref(defaultPeriod)
const selectedTemplate = ref(null)
const warningDays = ref(30)

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

const contractWarning = reactive({
  total_count: 0,
  expired_count: 0,
  list: []
})

const configVisible = ref(false)
const configTab = ref('salary')
const templates = ref([])
const allAvailableFields = ref({ ...ALL_EXPORT_FIELDS })

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

const dragIndex = ref(-1)
const dragOverIndex = ref(-1)

const currentAvailableFields = computed(() => allAvailableFields.value[configTab.value] || [])

const filteredTemplates = computed(() => templates.value.filter(t => TAB_TYPE_MAP[configTab.value]?.includes(t.template_type)))

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
  const map = { salary_finance: '财务薪资表', salary_slip: '工资条表', tax: '报税表', roster: '花名册', attendance: '考勤表', social_insurance: '社保表', custom: '自定义' }
  return map[type] || type
}

function getTypeTagType(type) {
  const map = { salary_finance: 'success', salary_slip: 'warning', tax: 'danger', roster: 'primary', attendance: 'warning', social_insurance: '', custom: 'info' }
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

async function fetchContractWarning() {
  try {
    const res = await api.get('/reports/contract-expiry-warning', { params: { days_ahead: warningDays.value } })
    const d = res.data
    contractWarning.total_count = d.total_count
    contractWarning.expired_count = d.expired_count
    contractWarning.list = d.list
  } catch {
    ElMessage.error('加载合同预警失败')
  }
}

async function fetchTemplates() {
  try {
    const res = await api.get('/reports/export/templates')
    templates.value = (res.data || []).map(tpl => syncTemplateFieldLabels(tpl))
  } catch {
    ElMessage.error('加载模板列表失败')
  }
}

function syncTemplateFieldLabels(tpl) {
  const typeKey = tpl.template_type?.startsWith('salary') ? 'salary'
    : tpl.template_type === 'roster' ? 'roster'
    : tpl.template_type === 'attendance' ? 'attendance'
    : tpl.template_type === 'social_insurance' ? 'social_insurance'
    : configTab.value
  const fieldDefs = ALL_EXPORT_FIELDS[typeKey] || []
  const labelMap = {}
  fieldDefs.forEach(f => { labelMap[f.key] = f.label })
  const syncedFields = (tpl.fields || []).map(f => {
    if (labelMap[f.key]) {
      return { ...f, label: labelMap[f.key] }
    }
    return f
  })
  return { ...tpl, fields: syncedFields }
}

function fetchAvailableFields() {
  allAvailableFields.value = { ...ALL_EXPORT_FIELDS }
}

function showConfigDialog() {
  fetchTemplates()
  fetchAvailableFields()
  configVisible.value = true
}

function onConfigTabChange(tab) {
  configTab.value = tab
  if (tab === 'salary') {
    editingTemplate.template_type = 'salary_finance'
  } else {
    editingTemplate.template_type = tab
  }
}

function createNewTemplate() {
  editingTemplate.id = null
  editingTemplate.name = ''
  if (configTab.value === 'salary') {
    editingTemplate.template_type = 'salary_finance'
  } else {
    editingTemplate.template_type = configTab.value
  }
  editingTemplate.description = ''
  editingTemplate.fields = []
  editingTemplate.is_default = false
  editingTemplate.is_enabled = true
  editVisible.value = true
}

function editTemplate(row) {
  const synced = syncTemplateFieldLabels(row)
  editingTemplate.id = synced.id
  editingTemplate.name = synced.name
  editingTemplate.template_type = synced.template_type
  editingTemplate.description = synced.description || ''
  editingTemplate.fields = [...(synced.fields || [])]
  editingTemplate.is_default = synced.is_default
  editingTemplate.is_enabled = synced.is_enabled
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

function selectAllFields() {
  const existingKeys = new Set(selectedFieldKeys.value)
  currentAvailableFields.value.forEach(f => {
    if (!existingKeys.has(f.key)) {
      editingTemplate.fields.push({ ...f })
    }
  })
}

function clearAllFields() {
  editingTemplate.fields = []
}

function moveFieldUp(idx) {
  if (idx === 0) return
  const fields = editingTemplate.fields
  const temp = fields[idx]
  fields[idx] = fields[idx - 1]
  fields[idx - 1] = temp
}

function moveFieldDown(idx) {
  const fields = editingTemplate.fields
  if (idx === fields.length - 1) return
  const temp = fields[idx]
  fields[idx] = fields[idx + 1]
  fields[idx + 1] = temp
}

function handleDragStart(idx) {
  dragIndex.value = idx
}

function handleDragOver(idx) {
  dragOverIndex.value = idx
}

function handleDragLeave() {
  dragOverIndex.value = -1
}

function handleDrop(targetIdx) {
  const fromIdx = dragIndex.value
  if (fromIdx === -1 || fromIdx === targetIdx) {
    dragIndex.value = -1
    dragOverIndex.value = -1
    return
  }
  const fields = editingTemplate.fields
  const [movedItem] = fields.splice(fromIdx, 1)
  fields.splice(targetIdx, 0, movedItem)
  dragIndex.value = -1
  dragOverIndex.value = -1
}

function handleDragEnd() {
  dragIndex.value = -1
  dragOverIndex.value = -1
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

function exportContractWarning() {
  const headers = ['员工姓名', '部门', '合同到期日', '剩余天数', '状态']
  let csvContent = headers.join(',') + '\n'
  contractWarning.list.forEach(item => {
    csvContent += `"${item.name}","${item.department}","${item.contract_end_date}",${item.days_remaining},"${item.is_expired ? '已过期' : '即将到期'}"\n`
  })
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `合同到期预警_${new Date().toISOString().slice(0,10)}.csv`
  link.click()
  ElMessage.success('导出成功')
}

onMounted(() => {
  fetchStats()
  fetchContractWarning()
  fetchTemplates()
  fetchAvailableFields()
})
</script>
