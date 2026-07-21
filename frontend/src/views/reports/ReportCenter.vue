<template>
  <div class="space-y-6">
    <div class="apple-card p-6" v-if="canViewContractWarning">
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
          <el-button type="primary" size="small" text @click="exportContractWarning" v-if="canExportContractWarning">导出预警名单</el-button>
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
      <div class="flex items-center gap-4 mb-6">
        <el-button type="primary" class="!text-base !px-6 !py-5 !rounded-lg" @click="showConfigDialog" v-permission="'report:export'">
          <el-icon class="!text-xl mr-1"><Setting /></el-icon>
          导出表配置
        </el-button>
        <h3 class="text-lg font-semibold text-gray-700">报表导出中心</h3>
      </div>

      <div class="mb-6">
        <h4 class="text-base font-medium text-gray-700 mb-4">薪资表导出</h4>
        <div class="apple-card p-6">
          <div class="flex flex-wrap items-center gap-4">
            <div class="flex items-center gap-2">
              <span class="text-sm text-gray-600">月份：</span>
              <el-date-picker v-model="salaryPeriod" type="month" placeholder="选择月份" size="default" class="!w-40" value-format="YYYYMM" />
            </div>
            <div class="flex items-center gap-2">
              <span class="text-sm text-gray-600">模板：</span>
              <el-select v-model="selectedTemplate" placeholder="选择模板" size="default" class="!w-48" clearable>
                <el-option v-for="tpl in salaryTemplates" :key="tpl.id" :label="tpl.name + (tpl.is_default ? ' (默认)' : '')" :value="tpl.id" />
              </el-select>
            </div>
            <el-button type="primary" size="default" @click="exportSalaryByTemplate" v-permission="'report:export'">
              <el-icon><Download /></el-icon>
              导出Excel
            </el-button>
          </div>
        </div>
      </div>

      <div v-if="hasExportPermission">
        <div class="flex items-center justify-between mb-4">
          <h4 class="text-base font-medium text-gray-700">常用导出</h4>
          <el-button type="primary" link size="small" @click="showAddCommonDialog" v-permission="'report:export'">
            <el-icon><Plus /></el-icon>
            添加常用
          </el-button>
        </div>
        <div v-if="commonTemplateList.length > 0" class="flex flex-wrap items-center gap-3">
          <div
            v-for="tpl in commonTemplateList"
            :key="tpl.id"
            class="group relative inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-50 border border-blue-200 text-blue-700 cursor-pointer hover:bg-blue-100 hover:border-blue-300 hover:shadow-sm transition-all text-sm font-medium"
            @click="exportByTemplate(tpl)"
          >
            <el-icon :class="getTemplateIconColor(tpl.template_type)" class="text-base">
              <component :is="getTemplateIcon(tpl.template_type)" />
            </el-icon>
            <span>{{ tpl.name }}</span>
            <el-icon
              class="ml-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
              @click.stop="removeCommonTemplate(tpl.id)"
            ><Close /></el-icon>
          </div>
        </div>
        <div v-else class="text-center py-6 text-gray-400 text-sm">
          暂无常用导出模板，点击右上角「添加常用」选择需要的模板
        </div>
      </div>
      <div v-else class="text-center py-6 text-gray-400 text-sm">
        您没有报表导出权限，请联系管理员分配
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

    <el-dialog v-model="addCommonVisible" title="添加常用导出模板" width="500px" append-to-body>
      <div class="text-sm text-gray-500 mb-3">选择要添加到常用导出的模板：</div>
      <div v-if="availableToAdd.length > 0" class="space-y-2 max-h-80 overflow-y-auto">
        <div
          v-for="tpl in availableToAdd"
          :key="tpl.id"
          class="flex items-center justify-between p-3 border rounded-lg hover:bg-blue-50 hover:border-blue-300 cursor-pointer"
          @click="addCommonTemplate(tpl)"
        >
          <div class="flex items-center gap-3">
            <el-icon :class="getTemplateIconColor(tpl.template_type)">
              <component :is="getTemplateIcon(tpl.template_type)" />
            </el-icon>
            <div>
              <div class="font-medium text-sm">{{ tpl.name }}</div>
              <div class="text-xs text-gray-500">{{ getTypeLabel(tpl.template_type) }}{{ tpl.description ? ' · ' + tpl.description : '' }}</div>
            </div>
          </div>
          <el-icon class="text-green-500"><Plus /></el-icon>
        </div>
      </div>
      <div v-else class="text-center py-8 text-gray-400">
        <el-icon class="text-3xl mb-2"><CircleCheck /></el-icon>
        <div>所有已启用的模板都已添加到常用</div>
      </div>
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
import { Document, Calendar, Setting, Plus, Close, Rank, CircleCheck, Top, Bottom, Download, Money, OfficeBuilding, User, Wallet } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import { getDefaultPeriod } from '../../utils/date.js'
import { ALL_EXPORT_FIELDS } from '../../config/columns'
import { useAuthStore } from '../../stores/auth'

const authStore = useAuthStore()

const hasExportPermission = computed(() => authStore.isAdmin || authStore.hasPermission('report:export'))
const canViewContractWarning = computed(() => authStore.isAdmin || authStore.hasPermission('report:contract_warning_view'))
const canExportContractWarning = computed(() => authStore.isAdmin || authStore.hasPermission('report:contract_warning_export'))

const TAB_TYPE_MAP = {
  salary: ['salary_finance', 'salary_slip', 'custom'],
  roster: ['roster'],
  attendance: ['attendance'],
  social_insurance: ['social_insurance']
}

const TEMPLATE_ICONS = {
  salary_finance: Money,
  salary_slip: Wallet,
  roster: User,
  attendance: Calendar,
  social_insurance: OfficeBuilding,
  custom: Document
}

const TEMPLATE_ICON_COLORS = {
  salary_finance: 'text-blue-500',
  salary_slip: 'text-green-500',
  roster: 'text-orange-500',
  attendance: 'text-purple-500',
  social_insurance: 'text-cyan-500',
  custom: 'text-gray-500'
}

const defaultPeriod = getDefaultPeriod()
const salaryPeriod = ref(defaultPeriod)
const selectedTemplate = ref(null)
const warningDays = ref(30)

const commonTemplateIds = ref([])
const addCommonVisible = ref(false)

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

const enabledTemplates = computed(() => templates.value.filter(t => t.is_enabled))

const commonTemplateList = computed(() => {
  return commonTemplateIds.value
    .map(id => enabledTemplates.value.find(t => t.id === id))
    .filter(Boolean)
})

const availableToAdd = computed(() => {
  return enabledTemplates.value.filter(t => !commonTemplateIds.value.includes(t.id))
})

const selectedFields = computed({
  get: () => editingTemplate.fields,
  set: (val) => { editingTemplate.fields = val }
})

const selectedFieldKeys = computed(() => selectedFields.value.map(f => f.key))

function getTypeLabel(type) {
  const map = { salary_finance: '财务薪资表', salary_slip: '工资条表', tax: '报税表', roster: '花名册', attendance: '考勤表', social_insurance: '社保表', custom: '自定义' }
  return map[type] || type
}

function getTypeTagType(type) {
  const map = { salary_finance: 'success', salary_slip: 'warning', tax: 'danger', roster: 'primary', attendance: 'warning', social_insurance: '', custom: 'info' }
  return map[type] || ''
}

function getTemplateIcon(type) {
  return TEMPLATE_ICONS[type] || Document
}

function getTemplateIconColor(type) {
  return TEMPLATE_ICON_COLORS[type] || 'text-gray-500'
}

function getCommonStorageKey() {
  const userId = authStore.user?.id || 'default'
  return `e9_common_export_templates_${userId}`
}

function loadCommonTemplates() {
  try {
    const stored = localStorage.getItem(getCommonStorageKey())
    if (stored) {
      commonTemplateIds.value = JSON.parse(stored)
    } else {
      const defaultSalaryTpl = templates.value.find(t => t.template_type === 'salary_finance' && t.is_default && t.is_enabled)
        || templates.value.find(t => t.template_type === 'salary_finance' && t.is_enabled)
      const defaultSlipTpl = templates.value.find(t => t.template_type === 'salary_slip' && t.is_default && t.is_enabled)
        || templates.value.find(t => t.template_type === 'salary_slip' && t.is_enabled)
      const defaults = []
      if (defaultSlipTpl) defaults.push(defaultSlipTpl.id)
      if (defaultSalaryTpl) defaults.push(defaultSalaryTpl.id)
      commonTemplateIds.value = defaults
    }
  } catch {
    commonTemplateIds.value = []
  }
}

function saveCommonTemplates() {
  localStorage.setItem(getCommonStorageKey(), JSON.stringify(commonTemplateIds.value))
}

function showAddCommonDialog() {
  addCommonVisible.value = true
}

function addCommonTemplate(tpl) {
  if (!commonTemplateIds.value.includes(tpl.id)) {
    commonTemplateIds.value.push(tpl.id)
    saveCommonTemplates()
    ElMessage.success(`已添加「${tpl.name}」到常用导出`)
  }
  if (availableToAdd.value.length === 0) {
    addCommonVisible.value = false
  }
}

function removeCommonTemplate(tplId) {
  const idx = commonTemplateIds.value.indexOf(tplId)
  if (idx >= 0) {
    const tpl = templates.value.find(t => t.id === tplId)
    commonTemplateIds.value.splice(idx, 1)
    saveCommonTemplates()
    ElMessage.success(`已从常用导出移除「${tpl?.name || '模板'}」`)
  }
}

async function exportByTemplate(tpl) {
  if (!hasExportPermission.value) {
    ElMessage.error('您没有报表导出权限，请联系管理员分配')
    return
  }
  try {
    let url = ''
    let filename = ''
    let params = {}
    const period = salaryPeriod.value

    if (tpl.template_type === 'roster') {
      url = '/reports/roster'
      filename = `${tpl.name}.xlsx`
    } else if (tpl.template_type === 'attendance') {
      url = `/reports/attendance/${period}`
      filename = `${tpl.name}_${period}.xlsx`
    } else if (tpl.template_type === 'social_insurance') {
      url = `/reports/social-insurance/${period}`
      filename = `${tpl.name}_${period}.xlsx`
    } else {
      url = `/reports/salary-by-template/${period}`
      params.template_id = tpl.id
      filename = `${tpl.name}_${period}.xlsx`
    }

    const res = await api.get(url, { params, responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导出失败')
  }
}

async function fetchContractWarning() {
  if (!canViewContractWarning.value) return
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

async function exportSalaryByTemplate() {
  if (!hasExportPermission.value) {
    ElMessage.error('您没有报表导出权限，请联系管理员分配')
    return
  }
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
  if (!canExportContractWarning.value) {
    ElMessage.error('您没有合同到期预警导出权限，请联系管理员分配')
    return
  }
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

onMounted(async () => {
  fetchContractWarning()
  await fetchTemplates()
  loadCommonTemplates()
  fetchAvailableFields()
})
</script>
