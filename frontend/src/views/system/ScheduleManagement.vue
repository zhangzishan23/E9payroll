<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">日程管理</h3>
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)" v-permission="'system:dict'">新增日程</el-button>
      <span class="text-xs text-gray-400 ml-2">配置每月算薪日程，工作台待办事项会根据此处配置自动生成</span>
    </div>

    <el-table
      :data="schedules"
      border stripe
      v-loading="loading"
      row-key="id"
    >
      <el-table-column prop="sort_order" label="排序" width="80" />
      <el-table-column prop="name" label="日程名称" width="180" />
      <el-table-column label="执行日期" width="120">
        <template #default="{ row }">每月{{ row.day_of_month }}日</template>
      </el-table-column>
      <el-table-column prop="step_key" label="关联步骤" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.step_key" size="small" type="info">{{ stepKeyMap[row.step_key] || row.step_key }}</el-tag>
          <span v-else class="text-gray-400">无</span>
        </template>
      </el-table-column>
      <el-table-column prop="route" label="跳转页面" width="150">
        <template #default="{ row }">
          <span v-if="row.route" class="text-blue-600 text-xs">{{ row.route }}</span>
          <span v-else class="text-gray-400">无</span>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.is_warning" type="danger" size="small">预警项</el-tag>
          <el-tag v-else type="primary" size="small">待办项</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="提前预警" width="100" v-if="false">
        <template #default="{ row }">
          {{ row.is_warning ? `${row.warning_days}天` : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="is_enabled" label="启用" width="100">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_enabled"
            size="small"
            @change="handleToggle(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showDialog(row)" v-permission="'system:dict'">编辑</el-button>
          <el-button type="danger" link size="small" @click="handleDelete(row)" v-permission="'system:dict'">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="mt-3 text-sm text-gray-500 flex items-center gap-1">
      <el-icon><InfoFilled /></el-icon>
      <span>日程配置修改后，工作台待办会立即更新。预警项会在指定日期前几天开始高亮提醒。</span>
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑日程' : '新增日程'" width="560px" append-to-body>
      <el-form :model="form" label-width="100px">
        <el-form-item label="日程名称" required>
          <el-input v-model="form.name" placeholder="例如：员工档案确认" />
        </el-form-item>
        <el-form-item label="执行日期" required>
          <el-input-number v-model="form.day_of_month" :min="1" :max="31" placeholder="几号" />
          <span class="ml-2 text-sm text-gray-500">每月该日执行</span>
        </el-form-item>
        <el-form-item label="关联步骤">
          <el-select v-model="form.step_key" placeholder="不关联算薪步骤（可选）" clearable class="w-full">
            <el-option label="员工档案" value="employee" />
            <el-option label="考勤数据" value="attendance" />
            <el-option label="绩效评分" value="performance" />
            <el-option label="社保数据" value="insurance" />
            <el-option label="个税申报" value="tax" />
            <el-option label="薪资计算" value="salary" />
            <el-option label="两级审批" value="approval" />
            <el-option label="工资发放" value="payment" />
          </el-select>
        </el-form-item>
        <el-form-item label="跳转页面">
          <el-select v-model="form.route" placeholder="点击待办时跳转的页面（可选）" clearable class="w-full">
            <el-option label="工作台" value="/dashboard" />
            <el-option label="档案管理" value="/employees" />
            <el-option label="考勤管理" value="/attendance" />
            <el-option label="绩效评分" value="/performance" />
            <el-option label="社保公积金" value="/insurance" />
            <el-option label="薪资计算" value="/salary" />
            <el-option label="审批流程" value="/approval" />
            <el-option label="报表导出" value="/reports" />
            <el-option label="数据字典" value="/system/dict" />
            <el-option label="日程管理" value="/system/schedules" />
          </el-select>
        </el-form-item>
        <el-form-item label="图标">
          <el-select v-model="form.icon" placeholder="选择图标" clearable class="w-full">
            <el-option label="日历" value="Calendar" />
            <el-icon><Calendar /></el-icon>
            <el-option label="用户" value="User" />
            <el-option label="金钱" value="Money" />
            <el-option label="信用卡" value="CreditCard" />
            <el-option label="趋势" value="TrendCharts" />
            <el-option label="文档" value="Document" />
            <el-option label="警告" value="Warning" />
            <el-option label="勾选" value="Checked" />
            <el-option label="设置" value="Setting" />
          </el-select>
        </el-form-item>
        <el-form-item label="主题颜色">
          <el-select v-model="form.color" placeholder="选择颜色" class="w-full">
            <el-option label="蓝色" value="blue" />
            <el-option label="绿色" value="green" />
            <el-option label="橙色" value="orange" />
            <el-option label="红色" value="red" />
            <el-option label="紫色" value="purple" />
            <el-option label="青色" value="cyan" />
            <el-option label="灰色" value="gray" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述说明">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="对该日程的简要说明（可选）" />
        </el-form-item>
        <el-form-item label="是否预警项">
          <el-switch v-model="form.is_warning" />
          <span class="ml-2 text-sm text-gray-500">预警项会显示在右侧预警待办区</span>
        </el-form-item>
        <el-form-item label="提前预警天数" v-if="form.is_warning">
          <el-input-number v-model="form.warning_days" :min="1" :max="30" />
          <span class="ml-2 text-sm text-gray-500">到期前几天开始预警提醒</span>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, InfoFilled } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const schedules = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({
  name: '',
  day_of_month: 1,
  step_key: null,
  route: null,
  icon: 'Calendar',
  color: 'blue',
  description: '',
  is_warning: false,
  warning_days: 3,
  sort_order: 0,
  is_enabled: true
})

const stepKeyMap = {
  employee: '员工档案',
  attendance: '考勤数据',
  performance: '绩效评分',
  insurance: '社保数据',
  tax: '个税申报',
  salary: '薪资计算',
  approval: '两级审批',
  payment: '工资发放'
}

async function fetchSchedules() {
  loading.value = true
  try {
    const res = await api.get('/dashboard/schedules')
    schedules.value = res.data
  } catch (e) {
    console.error('Failed to fetch schedules:', e)
  } finally {
    loading.value = false
  }
}

function showDialog(row) {
  isEdit.value = !!row
  currentEditId.value = row?.id || null
  if (row) {
    Object.assign(form, {
      name: row.name,
      day_of_month: row.day_of_month,
      step_key: row.step_key,
      route: row.route,
      icon: row.icon || 'Calendar',
      color: row.color || 'blue',
      description: row.description || '',
      is_warning: row.is_warning,
      warning_days: row.warning_days || 3,
      sort_order: row.sort_order || 0,
      is_enabled: row.is_enabled
    })
  } else {
    Object.assign(form, {
      name: '',
      day_of_month: 1,
      step_key: null,
      route: null,
      icon: 'Calendar',
      color: 'blue',
      description: '',
      is_warning: false,
      warning_days: 3,
      sort_order: schedules.value.length,
      is_enabled: true
    })
  }
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.name) {
    ElMessage.warning('请输入日程名称')
    return
  }
  if (!form.day_of_month || form.day_of_month < 1 || form.day_of_month > 31) {
    ElMessage.warning('请输入正确的执行日期（1-31）')
    return
  }

  saving.value = true
  try {
    if (isEdit.value && currentEditId.value) {
      await api.put(`/dashboard/schedules/${currentEditId.value}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/dashboard/schedules', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchSchedules()
  } catch (e) {
    console.error('Save failed:', e)
  } finally {
    saving.value = false
  }
}

const currentEditId = ref(null)

async function handleToggle(row) {
  try {
    await api.put(`/dashboard/schedules/${row.id}`, { is_enabled: row.is_enabled })
    ElMessage.success(row.is_enabled ? '已启用' : '已禁用')
  } catch (e) {
    row.is_enabled = !row.is_enabled
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除日程「${row.name}」吗？`, '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger'
    })
    await api.delete(`/dashboard/schedules/${row.id}`)
    ElMessage.success('删除成功')
    await fetchSchedules()
  } catch {}
}

onMounted(() => {
  fetchSchedules()
})
</script>
