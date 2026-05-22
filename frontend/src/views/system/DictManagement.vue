<template>
  <div class="apple-card p-6">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold text-gray-700">数据字典</h3>
      <div class="flex gap-3">
        <el-select v-model="category" placeholder="选择分类" class="w-40" @change="fetchData">
          <el-option label="合同公司" value="contract_company" />
          <el-option label="部门" value="department" />
          <el-option label="职务" value="position" />
          <el-option label="用工状态" value="employee_status" />
          <el-option label="假期类型" value="leave_type" />
          <el-option label="薪资项目" value="salary_item" />
        </el-select>
        <el-button type="primary" :icon="Plus" @click="showDialog(null)">新增</el-button>
        <el-button type="success" :icon="Upload" @click="showImport">导入</el-button>
        <el-button type="info" :icon="Download" :disabled="!items.length" @click="handleExport">导出</el-button>
        <el-button type="danger" :icon="Delete" :disabled="!selectedRows.length" @click="handleBatchDelete">
          批量删除 {{ selectedRows.length ? `(${selectedRows.length})` : '' }}
        </el-button>
      </div>
    </div>

    <el-table :data="items" border stripe v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="code" label="编码" width="150" />
      <el-table-column prop="name" label="名称" width="200" />
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column prop="is_enabled" label="启用" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_enabled ? 'success' : 'danger'">{{ row.is_enabled ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDialog(row)">编辑</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, Delete } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const category = ref('contract_company')
const items = ref([])
const selectedRows = ref([])
const editId = ref(null)

const importVisible = ref(false)
const importing = ref(false)
const uploadFile = ref(null)
const fileList = ref([])
const uploadRef = ref(null)

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

onMounted(() => {
  fetchData()
})
</script>