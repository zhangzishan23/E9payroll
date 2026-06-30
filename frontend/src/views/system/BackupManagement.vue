<template>
  <div class="backup-management">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">数据备份</h3>
      <el-button type="primary" size="small" :loading="backingUp" @click="doBackup">
        立即备份
      </el-button>
    </div>

    <el-alert
      title="备份说明"
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <p class="text-sm">备份文件保存在项目 <code>backups/</code> 目录下。建议在执行重要操作（如同步钉钉数据、批量修改）前先备份。</p>
    </el-alert>

    <el-table :data="backups" stripe size="small" v-loading="loading" empty-text="暂无备份记录">
      <el-table-column prop="filename" label="文件名" min-width="260" />
      <el-table-column prop="size_display" label="大小" width="100" align="center" />
      <el-table-column label="备份时间" width="180" align="center">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const loading = ref(false)
const backingUp = ref(false)
const backups = ref([])

function formatTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function fetchBackups() {
  loading.value = true
  try {
    const res = await api.get('/system/backups')
    backups.value = res.data.backups
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}

async function doBackup() {
  backingUp.value = true
  try {
    const res = await api.post('/system/backup')
    ElMessage.success(res.data.message || '备份成功')
    await fetchBackups()
  } catch {
    // 错误已在拦截器中处理
  } finally {
    backingUp.value = false
  }
}

onMounted(fetchBackups)
</script>
