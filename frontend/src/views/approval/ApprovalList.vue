<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-2 mb-4">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0">审批流程</h3>
      <el-date-picker v-model="period" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" @change="fetchData" />
      <el-button type="primary" size="small" @click="fetchData">查询</el-button>
    </div>

    <div v-if="status" class="mb-6">
      <div class="grid grid-cols-4 gap-4 mb-4">
        <div class="bg-blue-50 rounded-xl p-4">
          <div class="text-sm text-gray-500">审批流水号</div>
          <div class="text-lg font-semibold text-blue-600">{{ status.approval_no || '未提交' }}</div>
        </div>
        <div class="bg-green-50 rounded-xl p-4">
          <div class="text-sm text-gray-500">提交人</div>
          <div class="text-lg font-semibold text-green-600">{{ status.submitter_name || '-' }}</div>
        </div>
        <div class="bg-purple-50 rounded-xl p-4">
          <div class="text-sm text-gray-500">提交时间</div>
          <div class="text-lg font-semibold text-purple-600">{{ status.submit_time ? formatDateTime(status.submit_time) : '-' }}</div>
        </div>
        <div class="bg-orange-50 rounded-xl p-4">
          <div class="text-sm text-gray-500">参与人数 / 总应发</div>
          <div class="text-lg font-semibold text-orange-600">{{ status.employee_count }}人 / {{ (status.total_gross / 10000).toFixed(2) }}万</div>
        </div>
      </div>

      <div class="mb-4">
        <div class="text-sm text-gray-500 mb-2">审批进度</div>
        <el-steps :active="getProgressStep(status.progress)" finish-status="success" align-center>
          <el-step title="提交审核" />
          <el-step title="主管审核" />
          <el-step title="经理审核" />
          <el-step title="完成" />
        </el-steps>
        <div class="text-center mt-2">
          <el-tag :type="getStatusType(status.status)" size="large">{{ status.progress }}</el-tag>
        </div>
      </div>

      <div v-if="canApprove" class="flex gap-3 mb-4 p-4 bg-gray-50 rounded-xl">
        <el-button type="success" @click="showApprovalDialog('主管审核', '通过')">主管审核通过</el-button>
        <el-button type="danger" @click="showApprovalDialog('主管审核', '驳回')">主管审核驳回</el-button>
        <el-button type="success" @click="showApprovalDialog('经理审核', '通过')">经理审核通过</el-button>
        <el-button type="danger" @click="showApprovalDialog('经理审核', '驳回')">经理审核驳回</el-button>
      </div>
    </div>

    <div class="mb-3">
      <h4 class="text-md font-semibold text-gray-700">审批记录</h4>
    </div>
    <el-table :data="records" border stripe v-loading="loading" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="approval_no" label="审批流水号" width="180" />
      <el-table-column prop="submitter_name" label="提交人" width="100" />
      <el-table-column prop="submit_time" label="提交时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.submit_time) }}</template>
      </el-table-column>
      <el-table-column prop="approval_level" label="审核级别" width="100" />
      <el-table-column prop="approver_name" label="审核人" width="100" />
      <el-table-column prop="action" label="操作" width="80">
        <template #default="{ row }">
          <el-tag :type="row.action === '通过' ? 'success' : row.action === '驳回' ? 'danger' : 'info'">{{ row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="opinion" label="审核意见" show-overflow-tooltip />
      <el-table-column prop="approval_time" label="审核时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.approval_time) }}</template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="approvalDialogVisible" :title="dialogTitle" width="600px" append-to-body>
      <el-form label-width="100px">
        <el-form-item label="审批流水号">
          <span>{{ status?.approval_no }}</span>
        </el-form-item>
        <el-form-item label="审核级别">
          <span>{{ currentLevel }}</span>
        </el-form-item>
        <el-form-item label="审核意见" v-if="currentAction === '驳回'">
          <el-input v-model="approvalOpinion" type="textarea" :rows="3" placeholder="请输入驳回意见（必填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approvalDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="confirmApproval">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const period = ref('202604')
const loading = ref(false)
const submitting = ref(false)
const status = ref(null)
const records = ref([])
const selectedRows = ref([])

const approvalDialogVisible = ref(false)
const currentLevel = ref('')
const currentAction = ref('')
const approvalOpinion = ref('')

const canApprove = computed(() => {
  if (!status.value || status.value.status === '已通过' || status.value.status === '已驳回') return false
  if (status.value.progress === '待主管审核') return true
  if (status.value.progress === '主管已通过，待经理审核') return true
  return false
})

const dialogTitle = computed(() => {
  return `${currentLevel.value} - ${currentAction.value}`
})

function formatDateTime(dt) {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 19)
}

function getProgressStep(progress) {
  if (progress === '未提交') return 0
  if (progress === '待主管审核') return 1
  if (progress === '主管已通过，待经理审核') return 2
  if (progress === '经理已通过') return 4
  return 1
}

function getStatusType(status) {
  if (status === '已通过') return 'success'
  if (status === '已驳回') return 'danger'
  if (status === '审核中') return 'warning'
  return 'info'
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function fetchData() {
  loading.value = true
  try {
    const res = await api.get(`/approval/status/${period.value}`)
    status.value = res.data
    records.value = res.data.records || []
  } finally {
    loading.value = false
  }
}

function showApprovalDialog(level, action) {
  currentLevel.value = level
  currentAction.value = action
  approvalOpinion.value = ''
  approvalDialogVisible.value = true
}

async function confirmApproval() {
  if (currentAction.value === '驳回' && !approvalOpinion.value.trim()) {
    ElMessage.warning('驳回时必须填写审核意见')
    return
  }

  submitting.value = true
  try {
    await api.post('/approval/action', {
      approval_no: status.value.approval_no,
      approval_level: currentLevel.value,
      action: currentAction.value,
      opinion: approvalOpinion.value.trim() || null
    })
    ElMessage.success(`${currentLevel.value}${currentAction.value}成功`)
    approvalDialogVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

fetchData()
</script>
