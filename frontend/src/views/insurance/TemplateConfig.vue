<template>
  <el-card class="template-config-card">
    <template #header>
      <div class="flex justify-between items-center">
        <span class="text-lg font-semibold">社保公积金导入模板配置</span>
        <div class="flex gap-2">
          <el-button type="success" :icon="Upload" size="small" @click="triggerUpload">上传文件自动识别</el-button>
          <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">新增模板</el-button>
        </div>
      </div>
    </template>

    <div class="bg-blue-50 rounded-lg p-3 mb-4 text-sm text-gray-600">
      <el-icon class="mr-1"><InfoFilled /></el-icon>
      配置不同政务平台导出的社保/公积金文件解析规则。配置后，「智能导入」即可自动识别并解析对应格式的文件。
      <span class="text-green-600 font-medium ml-2">推荐：上传一份样本文件，系统自动识别配置，您只需核对微调即可。</span>
    </div>

    <el-table :data="templates" border stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="模板名称" width="160" />
      <el-table-column prop="source_category" label="数据类别" width="110">
        <template #default="{ row }">
          <el-tag :type="row.source_category === 'social_insurance' ? '' : 'success'" size="small">
            {{ row.source_category === 'social_insurance' ? '社保' : '公积金' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="file_type" label="文件类型" width="80">
        <template #default="{ row }">
          <el-tag :type="row.file_type === 'excel' ? 'warning' : 'danger'" size="small">
            {{ row.file_type.toUpperCase() }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="city" label="城市" width="80" />
      <el-table-column prop="description" label="说明" min-width="150" show-overflow-tooltip />
      <el-table-column prop="data_start_row" label="数据起始行" width="90" />
      <el-table-column label="映射字段数" width="90">
        <template #default="{ row }">
          {{ row.column_mappings ? Object.keys(row.column_mappings).length : 0 }}
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="启用" width="65">
        <template #default="{ row }">
          <el-switch :model-value="row.is_active" size="small" disabled />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-link type="primary" :underline="false" class="mr-2" @click="showDialog(row)">编辑</el-link>
          <el-link type="danger" :underline="false" @click="handleDelete(row)">删除</el-link>
        </template>
      </el-table-column>
    </el-table>

    <!-- 隐藏的文件上传 -->
    <input
      ref="fileInputRef"
      type="file"
      accept=".xlsx,.xls,.pdf"
      style="display: none"
      @change="handleFileChange"
    />

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑模板' : (isAutoDetected ? '核对自动识别结果' : '新增模板')"
      width="750px"
      append-to-body
      @close="resetForm"
    >
      <!-- 自动识别结果提示 -->
      <el-alert
        v-if="isAutoDetected"
        title="已根据上传文件自动识别配置，请核对以下信息是否正确，可手动调整后保存。"
        type="success"
        :closable="false"
        show-icon
        class="mb-4"
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="right">
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="模板名称" prop="name">
              <el-input v-model="form.name" placeholder="如：广州公积金" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="数据类别" prop="source_category">
              <el-select v-model="form.source_category" class="w-full">
                <el-option label="社保" value="social_insurance" />
                <el-option label="公积金" value="housing_fund" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="文件类型" prop="file_type">
              <el-select v-model="form.file_type" class="w-full">
                <el-option label="Excel" value="excel" />
                <el-option label="PDF" value="pdf" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="城市">
              <el-input v-model="form.city" placeholder="如：广州" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="文件名匹配">
              <el-input v-model="form.file_pattern" placeholder="正则，如：公积金|CI_EXCEL" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="工作表匹配">
              <el-input v-model="form.sheet_pattern" placeholder="工作表名正则" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="说明">
              <el-input v-model="form.description" placeholder="模板用途说明" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">解析配置</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="表头行号" prop="header_rows_str">
              <el-input v-model="form.header_rows_str" placeholder="如：6,7（第7-8行为表头）" />
              <div class="text-xs text-gray-400 mt-1">0-based行号，逗号分隔。多层表头用多行</div>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数据起始行" prop="data_start_row">
              <el-input-number v-model="form.data_start_row" :min="0" class="w-full" />
              <div class="text-xs text-gray-400 mt-1">0-based，数据从第几行开始</div>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="跳过末尾行">
              <el-input-number v-model="form.skip_footer_rows" :min="0" class="w-full" />
              <div class="text-xs text-gray-400 mt-1">跳过文件末尾的合计行等</div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">字段映射（文件列名 → 系统字段）</el-divider>
        <div class="mb-2">
          <el-button size="small" type="primary" :icon="Plus" @click="addMapping">添加映射</el-button>
          <span class="text-xs text-gray-400 ml-2">将政务平台文件中的列名，对应到系统数据库字段</span>
          <el-tag v-if="hasLevel2Headers" size="small" type="info" class="ml-2">已识别两级表头，按一级分组展示</el-tag>
        </div>

        <template v-if="mappingGroups.length > 0">
          <!-- 单层字段：直接罗列 -->
          <template v-if="singleLevelMappings.length > 0">
            <div v-for="item in singleLevelMappings" :key="'s' + item.flatIndex" class="flex gap-2 mb-2 items-center">
              <el-input v-model="item.header_name" placeholder="文件中的列名" class="flex-1" size="small" />
              <span class="text-gray-400">→</span>
              <el-select v-model="item.db_field" placeholder="系统字段" class="flex-1" size="small" filterable clearable>
                <el-option label="未映射（留空，手动调整）" :value="null" />
                <el-option v-for="(label, value) in fieldLabels" :key="value" :label="`${label} (${value})`" :value="value" />
              </el-select>
              <el-button :icon="Delete" size="small" type="danger" circle @click="removeMapping(item.flatIndex)" />
            </div>
          </template>

          <!-- 双层字段：按一级分组展示 -->
          <div v-for="(group, gIdx) in level2Groups" :key="'g' + gIdx" class="mb-3 border border-blue-100 rounded-lg overflow-hidden">
            <div class="flex items-center gap-2 px-2 py-1.5 cursor-pointer bg-blue-50 hover:bg-blue-100 transition-colors" @click="toggleGroup(gIdx)">
              <el-icon :size="14" class="transition-transform duration-200" :class="{ 'rotate-90': group.expanded }">
                <ArrowRight />
              </el-icon>
              <span class="text-sm font-medium text-blue-700">{{ group.parent }}</span>
              <span class="text-xs text-gray-400">({{ group.items.length }} 列)</span>
            </div>
            <div v-show="group.expanded" class="px-2 py-1">
              <div v-for="item in group.items" :key="'gi' + item.flatIndex" class="flex gap-2 mb-2 items-center pl-4">
                <el-input v-model="item.header_name" placeholder="文件中的列名" class="flex-1" size="small" />
                <span class="text-gray-400">→</span>
                <el-select v-model="item.db_field" placeholder="系统字段" class="flex-1" size="small" filterable clearable>
                  <el-option label="未映射（留空，手动调整）" :value="null" />
                  <el-option v-for="(label, value) in fieldLabels" :key="value" :label="`${label} (${value})`" :value="value" />
                </el-select>
                <el-button :icon="Delete" size="small" type="danger" circle @click="removeMapping(item.flatIndex)" />
              </div>
            </div>
          </div>
        </template>
        <el-empty v-if="form.mapping_list.length === 0" description="暂无字段映射，请点击「添加映射」" :image-size="40" />

        <el-divider content-position="left">高级配置</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="行过滤条件">
              <div class="w-full">
                <div v-for="(item, index) in form.filter_list" :key="index" class="flex gap-2 mb-1">
                  <el-input v-model="item.col" placeholder="列名" size="small" class="w-1/3" />
                  <el-select v-model="item.op" size="small" class="w-1/4">
                    <el-option label="等于" value="=" />
                    <el-option label="不等于" value="!=" />
                  </el-select>
                  <el-input v-model="item.val" placeholder="值" size="small" class="flex-1" />
                  <el-button :icon="Delete" size="small" type="danger" circle @click="form.filter_list.splice(index, 1)" />
                </div>
                <el-button size="small" :icon="Plus" @click="form.filter_list.push({ col: '', op: '=', val: '' })">添加过滤条件</el-button>
                <div class="text-xs text-gray-400 mt-1">仅导入满足条件的行，如：缴存状态 = 正常</div>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数值解析">
              <el-input v-model="form.remove_chars" placeholder="需去除的字符，逗号分隔" size="small" />
              <div class="text-xs text-gray-400 mt-1">如：,（去除金额中的逗号和百分号）</div>
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, InfoFilled, Upload, ArrowRight } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const isAutoDetected = ref(false)
const editId = ref(null)
const templates = ref([])
const fieldLabels = ref({})
const formRef = ref(null)
const fileInputRef = ref(null)

const rules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  source_category: [{ required: true, message: '请选择数据类别', trigger: 'change' }],
  file_type: [{ required: true, message: '请选择文件类型', trigger: 'change' }],
  header_rows_str: [{ required: true, message: '请输入表头行号', trigger: 'blur' }],
  data_start_row: [{ required: true, message: '请输入数据起始行', trigger: 'blur' }],
}

const form = reactive({
  name: '',
  source_category: 'social_insurance',
  file_type: 'excel',
  city: '',
  description: '',
  file_pattern: '',
  sheet_pattern: '',
  header_rows_str: '',
  data_start_row: 0,
  skip_footer_rows: 0,
  mapping_list: [],
  filter_list: [],
  remove_chars: '',
  is_active: true,
})

// ── 加载数据 ──
async function fetchTemplates() {
  loading.value = true
  try {
    const res = await api.get('/social-insurance/templates')
    templates.value = res.data
  } finally {
    loading.value = false
  }
}

async function fetchFieldLabels() {
  try {
    const res = await api.get('/social-insurance/field-labels')
    fieldLabels.value = res.data
  } catch {
    // 字段标签获取失败不影响模板管理
  }
}

onMounted(() => {
  fetchTemplates()
  fetchFieldLabels()
})

// ── 上传文件自动识别 ──
function triggerUpload() {
  fileInputRef.value?.click()
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  loading.value = true
  try {
    const res = await api.post('/social-insurance/templates/auto-detect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const detected = res.data
    applyDetectedConfig(detected)
    ElMessage.success(`自动识别完成，识别到 ${Object.keys(detected.column_mappings || {}).length} 个字段映射，请核对`)
  } catch (e) {
    // error handled by interceptor
  } finally {
    loading.value = false
    // 重置文件选择器，允许重复上传同一文件
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
  }
}

function applyDetectedConfig(detected) {
  isEdit.value = false
  isAutoDetected.value = true
  editId.value = null

  form.name = detected.name || ''
  form.source_category = detected.source_category || 'social_insurance'
  form.file_type = detected.file_type || 'excel'
  form.city = detected.city || ''
  form.description = detected.description || ''
  form.file_pattern = detected.file_pattern || ''
  form.sheet_pattern = detected.sheet_pattern || ''
  form.header_rows_str = (detected.header_rows || []).join(',')
  form.data_start_row = detected.data_start_row || 0
  form.skip_footer_rows = detected.skip_footer_rows || 0
  form.is_active = true

  // 列映射
  form.mapping_list = Object.entries(detected.column_mappings || {}).map(([k, v]) => ({
    header_name: k,
    db_field: v,
  }))

  // 行过滤
  form.filter_list = Object.entries(detected.row_filters || {}).map(([k, v]) => ({
    col: k,
    op: '=',
    val: v,
  }))

  // 数值解析
  form.remove_chars = (detected.number_format?.remove_chars || []).join(',')

  dialogVisible.value = true
}

// ── 弹窗操作 ──
function showDialog(row) {
  isEdit.value = !!row
  isAutoDetected.value = false
  editId.value = row?.id || null

  if (row) {
    form.name = row.name
    form.source_category = row.source_category
    form.file_type = row.file_type
    form.city = row.city || ''
    form.description = row.description || ''
    form.file_pattern = row.file_pattern || ''
    form.sheet_pattern = row.sheet_pattern || ''
    form.header_rows_str = (row.header_rows || []).join(',')
    form.data_start_row = row.data_start_row
    form.skip_footer_rows = row.skip_footer_rows || 0
    form.is_active = row.is_active

    // 列映射 → mapping_list
    form.mapping_list = Object.entries(row.column_mappings || {}).map(([k, v]) => ({
      header_name: k,
      db_field: v,
    }))

    // 行过滤 → filter_list
    form.filter_list = Object.entries(row.row_filters || {}).map(([k, v]) => ({
      col: k,
      op: '=',
      val: v,
    }))

    // number_format → remove_chars
    form.remove_chars = (row.number_format?.remove_chars || []).join(',')
  } else {
    resetForm()
  }
  dialogVisible.value = true
}

function resetForm() {
  form.name = ''
  form.source_category = 'social_insurance'
  form.file_type = 'excel'
  form.city = ''
  form.description = ''
  form.file_pattern = ''
  form.sheet_pattern = ''
  form.header_rows_str = ''
  form.data_start_row = 0
  form.skip_footer_rows = 0
  form.mapping_list = []
  form.filter_list = []
  form.remove_chars = ''
  form.is_active = true
  isAutoDetected.value = false
  formRef.value?.resetFields()
}

// ── 两级表头分组展示 ──
const mappingGroups = computed(() => {
  const groups = []
  form.mapping_list.forEach((item, idx) => {
    groups.push({ ...item, flatIndex: idx })
  })
  return groups
})

// 单层字段（不含 " - " 分隔符）
const singleLevelMappings = computed(() => {
  return mappingGroups.value.filter(item => !item.header_name.includes(' - '))
})

// 双层字段，按一级分组
const level2Groups = computed(() => {
  const groupMap = {}
  mappingGroups.value.forEach(item => {
    const parts = item.header_name.split(' - ')
    if (parts.length >= 2) {
      const parent = parts[0]
      if (!groupMap[parent]) {
        groupMap[parent] = []
      }
      groupMap[parent].push(item)
    }
  })
  const result = []
  for (const parent of Object.keys(groupMap)) {
    const existing = _groupExpanded[parent]
    result.push({
      parent,
      expanded: existing !== undefined ? existing : true,
      items: groupMap[parent],
    })
  }
  return result
})

const hasLevel2Headers = computed(() => {
  return form.mapping_list.some(item => item.header_name.includes(' - '))
})

const _groupExpanded = reactive({})

function toggleGroup(gIdx) {
  const group = level2Groups.value[gIdx]
  if (group) {
    _groupExpanded[group.parent] = !group.expanded
  }
}

// ── 映射操作 ──
function addMapping() {
  form.mapping_list.push({ header_name: '', db_field: 'employee_name' })
}

function removeMapping(flatIndex) {
  form.mapping_list.splice(flatIndex, 1)
}

// ── 保存 ──
async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (form.mapping_list.length === 0) {
    ElMessage.warning('请至少添加一个字段映射')
    return
  }

  // 构建 column_mappings（含 null 值，方便后续编辑时再映射）
  const column_mappings = {}
  form.mapping_list.forEach(item => {
    if (item.header_name) {
      column_mappings[item.header_name] = item.db_field || null
    }
  })
  if (Object.keys(column_mappings).length === 0) {
    ElMessage.warning('字段映射不完整，请检查')
    return
  }
  // 至少有一个有效映射（非 null）
  const hasValidMapping = Object.values(column_mappings).some(v => v !== null)
  if (!hasValidMapping) {
    ElMessage.warning('请至少为一个字段设置系统映射')
    return
  }

  // 构建 row_filters
  const row_filters = {}
  form.filter_list.forEach(item => {
    if (item.col && item.val) {
      row_filters[item.col] = item.val
    }
  })

  // 构建 number_format
  const remove_chars = form.remove_chars.split(',').map(s => s.trim()).filter(Boolean)
  const number_format = remove_chars.length > 0 ? { remove_chars } : null

  // 解析 header_rows
  const header_rows = form.header_rows_str.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))

  const payload = {
    name: form.name,
    source_category: form.source_category,
    file_type: form.file_type,
    city: form.city || null,
    description: form.description || null,
    file_pattern: form.file_pattern || null,
    sheet_pattern: form.sheet_pattern || null,
    header_rows,
    data_start_row: form.data_start_row,
    skip_footer_rows: form.skip_footer_rows,
    column_mappings,
    row_filters: Object.keys(row_filters).length > 0 ? row_filters : null,
    number_format,
    is_active: form.is_active,
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/social-insurance/templates/${editId.value}`, payload)
      ElMessage.success('模板更新成功')
    } else {
      await api.post('/social-insurance/templates', payload)
      ElMessage.success('模板创建成功')
    }
    dialogVisible.value = false
    await fetchTemplates()
  } catch (e) {
    // error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  const confirmTitle = `确认删除模板「${row.name}」?`
  const confirmMsg = '删除后，依赖此模板的导入功能将无法使用。'

  try {
    await ElMessageBox.confirm(confirmMsg, confirmTitle, {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    })
    await api.delete(`/social-insurance/templates/${row.id}`)
    ElMessage.success('模板已删除')
    await fetchTemplates()
  } catch {
    // 取消删除
  }
}
</script>

<style scoped>
.template-config-card {
  max-width: 1200px;
  margin: 0 auto;
}
.template-config-card :deep(.el-card__header) {
  padding: 16px 20px;
}
</style>
