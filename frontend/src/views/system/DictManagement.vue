<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">数据字典</h3>
      <el-select v-model="category" placeholder="选择分类" size="small" class="!w-32" @change="fetchData">
        <el-option label="合同公司" value="contract_company" />
        <el-option label="部门" value="department" />
        <el-option label="职务" value="position" />
        <el-option label="用工状态" value="employee_status" />
        <el-option label="假期类型" value="leave_type" />
        <el-option label="薪资项目" value="salary_item" />
      </el-select>
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">新增</el-button>
      <el-button type="success" :icon="Upload" size="small" @click="showImport">导入</el-button>
      <el-button type="info" :icon="Download" size="small" :disabled="!items.length" @click="handleExport">导出</el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}</el-button>
      <el-button v-if="category === 'department'" type="primary" size="small" @click="handleSyncRootDepts" :loading="syncingDepts">
        <el-icon class="mr-1"><Refresh /></el-icon>数据同步
      </el-button>
    </div>

    <el-table :data="displayItems" border stripe v-loading="loading" row-key="id" :tree-props="treeProps" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="code" label="编码" width="150" />
      <el-table-column prop="name" label="名称" width="200" />
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column prop="is_enabled" label="启动" width="100">
        <template #default="{ row }">
          <template v-if="category === 'department'">
            <el-switch
              v-model="row.is_enabled"
              size="small"
              @change="handleToggle(row)"
            />
          </template>
          <template v-else>
            <el-button
              :type="row.is_enabled ? 'success' : 'info'"
              link
              size="small"
              @click="handleToggle(row)"
            >{{ row.is_enabled ? '启用' : '禁用' }}</el-button>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDialog(row)">编辑</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="category === 'department'" class="mt-3 text-sm text-gray-500 flex items-center gap-1">
      <el-icon><InfoFilled /></el-icon>
      <span>启动的部门，在员工档案「同步钉钉」时才会同步该部门员工数据</span>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑字典项' : '新增字典项'" width="520px" append-to-body>
      <el-form :model="form" label-width="80px">
        <el-form-item label="编码" required>
          <el-input v-model="form.code" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入字典项" width="700px" append-to-body>
      <div class="mb-4 text-sm text-gray-500">
        请选择 Excel 文件（.xlsx/.xls），表头需包含：编码、名称、排序、启用
      </div>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleFileChange"
        :file-list="fileList"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">将 Excel 文件拖到此处，或<em>点击上传</em></div>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!uploadFile" @click="handleImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, Delete, InfoFilled, Refresh } from '@element-plus/icons-vue'
import api from '../../api'

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const category = ref(route.query.category || 'contract_company')
const items = ref([])
const selectedRows = ref([])
const editId = ref(null)

// 树形展示配置（仅部门分类使用）
const treeProps = computed(() => {
  if (category.value === 'department') {
    return { children: 'children' }
  }
  return {}
})

// 构建部门树形结构
function buildDeptTree(flatList) {
  const map = {}
  const roots = []
  flatList.forEach(item => {
    map[item.id] = { ...item, children: [] }
  })
  flatList.forEach(item => {
    const node = map[item.id]
    if (item.parent_id && map[item.parent_id]) {
      map[item.parent_id].children.push(node)
    } else {
      roots.push(node)
    }
  })
  // 清理空的 children 数组
  function cleanChildren(nodes) {
    nodes.forEach(node => {
      if (node.children && node.children.length === 0) {
        delete node.children
      } else if (node.children) {
        cleanChildren(node.children)
      }
    })
  }
  cleanChildren(roots)
  return roots
}

const displayItems = computed(() => {
  if (category.value === 'department') {
    return buildDeptTree(items.value)
  }
  return items.value
})

const importVisible = ref(false)
const importing = ref(false)
const uploadFile = ref(null)
const fileList = ref([])
const uploadRef = ref(null)

const syncingDepts = ref(false)

const form = reactive({ code: '', name: '', sort_order: 0, is_enabled: true })

async function fetchData() {
  if (!category.value) return
  loading.value = true
  try {
    const res = await api.get(`/system/dict/${category.value}`)
    items.value = res.data
  } finally {
    loading.value = false
  }
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  if (row) {
    Object.assign(form, { code: row.code, name: row.name, sort_order: row.sort_order, is_enabled: row.is_enabled })
  } else {
    Object.assign(form, { code: '', name: '', sort_order: items.value.length + 1, is_enabled: true })
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const data = { ...form, category: category.value }
    if (isEdit.value) {
      await api.put(`/system/dict/${editId.value}`, data)
      ElMessage.success('编辑成功')
    } else {
      await api.post('/system/dict', data)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '删除确认', {
    type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消'
  })
  await api.delete(`/system/dict/${row.id}`)
  ElMessage.success('删除成功')
  fetchData()
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的字典项')
    return
  }
  await ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 个字典项吗？此操作不可恢复。`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.map(r => r.id)
    await api.post('/system/dict/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 个字典项`)
    selectedRows.value = []
    fetchData()
  } catch (e) {
    ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

function showImport() {
  uploadFile.value = null
  fileList.value = []
  importVisible.value = true
}

function handleFileChange(file) {
  uploadFile.value = file.raw
  fileList.value = [file]
}

async function handleImport() {
  if (!uploadFile.value) {
    ElMessage.warning('请先选择 Excel 文件')
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    formData.append('category', category.value)
    const res = await api.post('/system/dict/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success(res.data.message)
    importVisible.value = false
    uploadFile.value = null
    fileList.value = []
    fetchData()
  } catch (e) {
    ElMessage.error('导入失败：' + (e.response?.data?.detail || '请稍后重试'))
  } finally {
    importing.value = false
  }
}

async function handleExport() {
  try {
    const res = await api.get(`/system/dict/export/${category.value}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `数据字典_${category.value}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

async function handleToggle(row) {
  try {
    const res = await api.put(`/system/dict/${row.id}/toggle`)
    row.is_enabled = res.data.is_enabled
    ElMessage.success(res.data.is_enabled ? `已启用「${row.name}」` : `已禁用「${row.name}」`)
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

async function handleSyncRootDepts() {
  syncingDepts.value = true
  try {
    const res = await api.post('/dingtalk/sync/root-depts')
    ElMessage.success(res.data.message)
    fetchData()
  } catch (e) {
    ElMessage.error('同步失败：' + (e.response?.data?.detail || '请稍后重试'))
  } finally {
    syncingDepts.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>