<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">操作日志</h3>
      <el-select v-model="logType" placeholder="日志类型" size="small" class="!w-28" @change="fetchData">
        <el-option label="全部" value="" />
        <el-option label="登录日志" value="login" />
        <el-option label="操作日志" value="operation" />
        <el-option label="数据变更" value="data_change" />
      </el-select>
      <el-button size="small" @click="fetchData">刷新</el-button>
    </div>

    <el-table :data="logs" border stripe v-loading="loading" max-height="600">
      <el-table-column prop="log_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.log_type === 'login' ? 'info' : row.log_type === 'operation' ? 'warning' : 'danger'" size="small">
            {{ row.log_type === 'login' ? '登录' : row.log_type === 'operation' ? '操作' : '数据变更' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="username" label="用户" width="100" />
      <el-table-column prop="module" label="模块" width="100" />
      <el-table-column prop="action" label="操作" width="80" />
      <el-table-column prop="target" label="操作对象" show-overflow-tooltip />
      <el-table-column prop="result" label="结果" width="80" />
      <el-table-column prop="ip_address" label="IP地址" width="140" />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api'

const loading = ref(false)
const logType = ref('')
const logs = ref([])

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (logType.value) params.log_type = logType.value
    const res = await api.get('/system/logs', { params })
    logs.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>