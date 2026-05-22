<template>
  <template v-if="!dialogVisible">
    <div class="apple-card p-6">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold text-gray-700">员工档案管理</h3>
        <div class="flex gap-3">
          <el-select v-model="filterField" placeholder="筛选字段" class="w-32">
            <el-option label="姓名" value="name" />
            <el-option label="编号" value="no" />
            <el-option label="部门" value="department" />
            <el-option label="公司" value="company" />
            <el-option label="状态" value="status" />
          </el-select>
          <el-input v-model="filterValue" placeholder="输入筛选值" clearable class="w-44" @input="fetchData" />
          <el-button type="primary" :icon="Plus" @click="showDialog(null)">新增员工</el-button>
          <el-button :icon="Upload" @click="showImport">批量导入</el-button>
          <el-button type="success" :icon="Download" @click="handleExport">导出</el-button>
          <el-button type="danger" :icon="Delete" :disabled="!selectedRows.length" @click="handleBatchDelete">
            批量删除 {{ selectedRows.length ? `(${selectedRows.length})` : '' }}
          </el-button>
          <el-divider direction="vertical" />
          <el-button
            :type="editMode ? 'warning' : 'default'"
            @click="toggleEditMode"
          >
            {{ editMode ? '退出编辑模式' : '开启编辑模式' }}
          </el-button>
          <template v-if="editMode">
            <el-button type="primary" :loading="savingEdits" :disabled="changedSet.size === 0" @click="confirmEdits">
              保存修改 {{ changedSet.size ? `(${changedSet.size})` : '' }}
            </el-button>
            <el-button :disabled="changedSet.size === 0" @click="cancelEdits">取消修改</el-button>
          </template>
        </div>
      </div>

      <el-table :data="employees" border stripe v-loading="loading" class="w-full" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="employee_no" label="员工编号" width="100" fixed />
        <el-table-column prop="name" label="姓名" width="100" fixed>
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input v-model="editCache[row.id].name" size="small" class="cell-input" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.name }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="gender" label="性别" width="70">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-select v-model="editCache[row.id].gender" size="small" class="cell-select" @change="markChanged(row.id)">
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </template>
            <template v-else>{{ row.gender }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="contract_company_name" label="合同公司" width="110">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-select v-model="editCache[row.id].contract_company_id" size="small" class="cell-select" @change="markChanged(row.id)">
                <el-option v-for="c in companies" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </template>
            <template v-else>{{ row.contract_company_name }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="department_name" label="部门" width="100">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-select v-model="editCache[row.id].department_id" size="small" class="cell-select" @change="markChanged(row.id)">
                <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </template>
            <template v-else>{{ row.department_name }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="position_name" label="职务" width="90">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-select v-model="editCache[row.id].position_id" size="small" class="cell-select" @change="markChanged(row.id)">
                <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </template>
            <template v-else>{{ row.position_name }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="status_name" label="状态" width="80">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-select v-model="editCache[row.id].status_id" size="small" class="cell-select" @change="markChanged(row.id)">
                <el-option v-for="s in statuses" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </template>
            <template v-else>{{ row.status_name }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="cost_owner" label="费用负责人" width="100">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input v-model="editCache[row.id].cost_owner" size="small" class="cell-input" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.cost_owner }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="联系电话" width="120">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input v-model="editCache[row.id].phone" size="small" class="cell-input" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.phone }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="home_address" label="家庭住址" width="180">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input v-model="editCache[row.id].home_address" size="small" class="cell-input" @change="markChanged(row.id)" />
            </template>
            <template v-else>
              <span class="text-ellipsis">{{ row.home_address }}</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column prop="entry_date" label="入职时间" width="120">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-date-picker v-model="editCache[row.id].entry_date" type="date" size="small" class="cell-date" value-format="YYYY-MM-DD" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.entry_date }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="regular_date" label="转正时间" width="120">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-date-picker v-model="editCache[row.id].regular_date" type="date" size="small" class="cell-date" value-format="YYYY-MM-DD" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.regular_date || '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="base_salary" label="基本工资" width="100">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].base_salary" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.base_salary != null ? row.base_salary : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="performance_standard" label="绩效标准" width="100">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].performance_standard" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.performance_standard != null ? row.performance_standard : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="meal_allowance" label="餐补" width="85">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].meal_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.meal_allowance != null ? row.meal_allowance : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="transport_allowance" label="交通补贴" width="95">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].transport_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.transport_allowance != null ? row.transport_allowance : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="communication_allowance" label="通讯补贴" width="95">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].communication_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.communication_allowance != null ? row.communication_allowance : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="computer_allowance" label="电脑补贴" width="95">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].computer_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.computer_allowance != null ? row.computer_allowance : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="housing_allowance" label="住房补贴" width="95">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].housing_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.housing_allowance != null ? row.housing_allowance : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column label="月薪标准" width="100">
          <template #default="{ row }">
            {{ monthlyStandard(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="salary_effective_date" label="薪资生效日" width="120">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-date-picker v-model="editCache[row.id].salary_effective_date" type="date" size="small" class="cell-date" value-format="YYYY-MM-DD" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.salary_effective_date || '' }}</template>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showDialog(row)">详细编辑</el-button>
            <el-button type="success" link size="small" @click="showSalaryHistory(row)">薪资历史</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    </template>

    <template v-else>
      <div class="mb-4 flex items-center gap-3">
        <el-button :icon="ArrowLeft" @click="closeDialog">返回列表</el-button>
        <h3 class="text-lg font-semibold text-gray-700">{{ isEdit ? '编辑员工' : '新增员工' }}</h3>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
          <el-form-item label="姓名" prop="name">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="性别" prop="gender">
            <el-select v-model="form.gender" class="w-full">
              <el-option label="男" value="男" />
              <el-option label="女" value="女" />
            </el-select>
          </el-form-item>
          <el-form-item label="身份证号" prop="id_card">
            <el-input v-model="form.id_card" />
          </el-form-item>
          <el-form-item label="联系方式">
            <el-input v-model="form.phone" />
          </el-form-item>
          <el-form-item label="合同公司" prop="contract_company_id">
            <el-select v-model="form.contract_company_id" class="w-full">
              <el-option v-for="c in companies" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="部门" prop="department_id">
            <el-select v-model="form.department_id" class="w-full">
              <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="职务" prop="position_id">
            <el-select v-model="form.position_id" class="w-full">
              <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="用工状态" prop="status_id">
            <el-select v-model="form.status_id" class="w-full">
              <el-option v-for="s in statuses" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="入职时间" prop="entry_date">
            <el-date-picker v-model="form.entry_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="转正时间">
            <el-date-picker v-model="form.regular_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="家庭地址">
            <el-input v-model="form.home_address" />
          </el-form-item>
          <el-form-item label="费用负责人">
            <el-input v-model="form.cost_owner" placeholder="请输入费用负责人姓名" />
          </el-form-item>
        </div>

        <el-divider content-position="left">薪资信息</el-divider>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
          <el-form-item label="基本工资">
            <el-input-number v-model="salaryEditForm.base_salary" :min="0" :precision="2" class="w-full" />
          </el-form-item>
          <el-form-item label="绩效标准">
            <el-input-number v-model="salaryEditForm.performance_standard" :min="0" :precision="2" class="w-full" />
          </el-form-item>
          <el-form-item label="餐补">
            <el-input-number v-model="salaryEditForm.meal_allowance" :min="0" :precision="2" class="w-full" />
          </el-form-item>
          <el-form-item label="交通补贴">
            <el-input-number v-model="salaryEditForm.transport_allowance" :min="0" :precision="2" class="w-full" />
          </el-form-item>
          <el-form-item label="通讯补贴">
            <el-input-number v-model="salaryEditForm.communication_allowance" :min="0" :precision="2" class="w-full" />
          </el-form-item>
          <el-form-item label="电脑补贴">
            <el-input-number v-model="salaryEditForm.computer_allowance" :min="0" :precision="2" class="w-full" />
          </el-form-item>
          <el-form-item label="住房补贴">
            <el-input-number v-model="salaryEditForm.housing_allowance" :min="0" :precision="2" class="w-full" />
          </el-form-item>
          <el-form-item label="生效日期">
            <el-date-picker v-model="salaryEditForm.effective_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="变更原因">
            <el-input v-model="salaryEditForm.change_reason" placeholder="如：调薪、转正等" />
          </el-form-item>
        </div>
      </el-form>

      <div class="mt-6 flex gap-3">
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </div>
    </template>

    <el-dialog v-model="salaryHistoryVisible" :title="'薪资历史 - ' + salaryHistoryName" width="800px" append-to-body>
      <el-table :data="salaryHistory" border stripe max-height="400" v-loading="salaryHistoryLoading">
        <el-table-column prop="base_salary" label="基本工资" width="100" />
        <el-table-column prop="performance_standard" label="绩效标准" width="100" />
        <el-table-column prop="meal_allowance" label="餐补" width="80" />
        <el-table-column prop="transport_allowance" label="交通补贴" width="90" />
        <el-table-column prop="communication_allowance" label="通讯补贴" width="90" />
        <el-table-column prop="computer_allowance" label="电脑补贴" width="90" />
        <el-table-column prop="housing_allowance" label="住房补贴" width="90" />
        <el-table-column prop="effective_date" label="生效日期" width="110" />
        <el-table-column prop="change_reason" label="变更原因" min-width="120">
          <template #default="{ row }">{{ row.change_reason || '-' }}</template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="salaryHistoryVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入员工" width="700px" append-to-body>
      <div class="mb-4">
        <div class="flex gap-3 mb-3">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".xlsx,.xls"
            :on-change="handleFileChange"
            :file-list="fileList"
          >
            <el-button type="primary">选择 Excel 文件</el-button>
          </el-upload>
          <el-button type="success" :loading="importing" :disabled="!importFile" @click="doImport">
            开始导入
          </el-button>
        </div>
        <div class="text-sm text-gray-500">
          支持 .xlsx / .xls 格式，表头需包含：姓名、性别、身份证号、联系电话、合同公司、部门、职务、用工状态、入职时间、转正时间、家庭住址、费用负责人
        </div>
        <div v-if="importResult" class="mt-3">
          <el-alert
            :type="importResult.errors.length ? 'warning' : 'success'"
            :title="importResult.message"
            :closable="false"
          />
          <div v-if="importResult.errors.length" class="mt-2 text-sm text-red-500">
            <div v-for="(err, i) in importResult.errors" :key="i">{{ err }}</div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="confirmVisible" title="确认保存修改" width="600px" append-to-body>
      <div class="mb-2 text-gray-600">以下员工信息将被更新，请确认：</div>
      <el-table :data="confirmList" border stripe max-height="400">
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column label="修改字段" min-width="200">
          <template #default="{ row }">
            <div v-for="(change, idx) in row.changes" :key="idx" class="text-sm">
              <span class="text-gray-500">{{ change.label }}：</span>
              <span class="text-red-400 line-through mr-1">{{ change.old }}</span>
              <span class="text-green-600 font-medium">{{ change.new }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="confirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdits" @click="saveAllEdits">确认保存</el-button>
      </template>
    </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Delete, ArrowLeft } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const savingEdits = ref(false)
const importing = ref(false)
const dialogVisible = ref(false)
const importVisible = ref(false)
const isEdit = ref(false)
const filterField = ref('name')
const filterValue = ref('')
const employees = ref([])
const selectedRows = ref([])
const importFile = ref(null)
const fileList = ref([])
const importResult = ref(null)
const uploadRef = ref(null)
const companies = ref([])
const departments = ref([])
const positions = ref([])
const statuses = ref([])
const formRef = ref(null)
const editId = ref(null)
const salaryHistoryVisible = ref(false)
const salaryHistory = ref([])
const salaryHistoryName = ref('')
const salaryHistoryLoading = ref(false)

const editMode = ref(false)
const editCache = reactive({})
const changedSet = ref(new Set())
const confirmVisible = ref(false)
const confirmList = ref([])

const fieldLabels = {
  name: '姓名',
  gender: '性别',
  contract_company_id: '合同公司',
  department_id: '部门',
  position_id: '职务',
  status_id: '状态',
  cost_owner: '费用负责人',
  phone: '联系电话',
  home_address: '家庭住址',
  entry_date: '入职时间',
  regular_date: '转正时间',
  base_salary: '基本工资',
  performance_standard: '绩效标准',
  meal_allowance: '餐补',
  transport_allowance: '交通补贴',
  communication_allowance: '通讯补贴',
  computer_allowance: '电脑补贴',
  housing_allowance: '住房补贴',
  salary_effective_date: '薪资生效日'
}

const dictFields = ['contract_company_id', 'department_id', 'position_id', 'status_id']

const form = reactive({
  name: '', gender: '男', id_card: '', phone: '',
  contract_company_id: null, department_id: null, position_id: null, status_id: null,
  cost_owner: '', entry_date: '', regular_date: null, home_address: ''
})

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  id_card: [{ required: true, message: '请输入身份证号', trigger: 'blur' }],
  contract_company_id: [{ required: true, message: '请选择合同公司', trigger: 'change' }],
  department_id: [{ required: true, message: '请选择部门', trigger: 'change' }],
  position_id: [{ required: true, message: '请选择职务', trigger: 'change' }],
  status_id: [{ required: true, message: '请选择用工状态', trigger: 'change' }],
  entry_date: [{ required: true, message: '请选择入职时间', trigger: 'change' }]
}

async function fetchDicts() {
  const res = await api.get('/system/dict')
  const dicts = res.data
  companies.value = dicts.filter(d => d.category === 'contract_company')
  departments.value = dicts.filter(d => d.category === 'department')
  positions.value = dicts.filter(d => d.category === 'position')
  statuses.value = dicts.filter(d => d.category === 'employee_status')
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filterField.value && filterValue.value) {
      params.filter_field = filterField.value
      params.filter_value = filterValue.value
    }
    const res = await api.get('/employees/', { params })
    employees.value = res.data
    if (editMode.value) {
      initEditCache()
    }
  } finally {
    loading.value = false
  }
}

function initEditCache() {
  for (const emp of employees.value) {
    if (!editCache[emp.id]) {
      editCache[emp.id] = reactive({
        name: emp.name,
        gender: emp.gender,
        contract_company_id: emp.contract_company_id,
        department_id: emp.department_id,
        position_id: emp.position_id,
        status_id: emp.status_id,
        cost_owner: emp.cost_owner || '',
        phone: emp.phone || '',
        home_address: emp.home_address || '',
        entry_date: emp.entry_date || '',
        regular_date: emp.regular_date || '',
        base_salary: emp.base_salary != null ? emp.base_salary : 0,
        performance_standard: emp.performance_standard != null ? emp.performance_standard : 0,
        meal_allowance: emp.meal_allowance != null ? emp.meal_allowance : 0,
        transport_allowance: emp.transport_allowance != null ? emp.transport_allowance : 0,
        communication_allowance: emp.communication_allowance != null ? emp.communication_allowance : 0,
        computer_allowance: emp.computer_allowance != null ? emp.computer_allowance : 0,
        housing_allowance: emp.housing_allowance != null ? emp.housing_allowance : 0,
        salary_effective_date: emp.salary_effective_date || ''
      })
    }
  }
}

function getDictName(category, id) {
  if (id == null) return ''
  const map = { contract_company: companies, department: departments, position: positions, employee_status: statuses }
  const list = map[category] || []
  const item = list.find(d => d.id === id)
  return item ? item.name : String(id)
}

function monthlyStandard(row) {
  const base = Number(row.base_salary) || 0
  const perf = Number(row.performance_standard) || 0
  const meal = Number(row.meal_allowance) || 0
  const transport = Number(row.transport_allowance) || 0
  const comm = Number(row.communication_allowance) || 0
  const computer = Number(row.computer_allowance) || 0
  const housing = Number(row.housing_allowance) || 0
  const total = base + perf + meal + transport + comm + computer + housing
  return total.toFixed(2)
}

function getFieldDisplayValue(emp, field) {
  if (dictFields.includes(field)) {
    const categoryMap = {
      contract_company_id: 'contract_company',
      department_id: 'department',
      position_id: 'position',
      status_id: 'employee_status'
    }
    return getDictName(categoryMap[field], emp[field])
  }
  const val = emp[field]
  return val != null ? String(val) : ''
}

function toggleEditMode() {
  if (editMode.value) {
    if (changedSet.value.size > 0) {
      ElMessageBox.confirm('有未保存的修改，确定退出编辑模式吗？修改将丢失。', '确认退出', {
        type: 'warning', confirmButtonText: '确定退出', cancelButtonText: '继续编辑'
      }).then(() => {
        editMode.value = false
        changedSet.value = new Set()
        for (const key of Object.keys(editCache)) {
          delete editCache[key]
        }
      }).catch(() => {})
    } else {
      editMode.value = false
      changedSet.value = new Set()
      for (const key of Object.keys(editCache)) {
        delete editCache[key]
      }
    }
  } else {
    editMode.value = true
    initEditCache()
    changedSet.value = new Set()
  }
}

function markChanged(empId) {
  const emp = employees.value.find(e => e.id === empId)
  if (!emp) return
  const cache = editCache[empId]
  if (!cache) return

  let hasChange = false
  const fields = Object.keys(fieldLabels)
  for (const field of fields) {
    const oldVal = emp[field]
    const newVal = cache[field]
    if (oldVal == null && (newVal === '' || newVal === 0)) continue
    if (newVal == null && (oldVal === '' || oldVal === 0)) continue
    if (String(oldVal ?? '') !== String(newVal ?? '')) {
      hasChange = true
      break
    }
  }

  const newSet = new Set(changedSet.value)
  if (hasChange) {
    newSet.add(empId)
  } else {
    newSet.delete(empId)
  }
  changedSet.value = newSet
}

function cancelEdits() {
  initEditCache()
  changedSet.value = new Set()
  ElMessage.info('已撤销所有修改')
}

function confirmEdits() {
  if (changedSet.value.size === 0) {
    ElMessage.warning('没有需要保存的修改')
    return
  }

  confirmList.value = []
  for (const empId of changedSet.value) {
    const emp = employees.value.find(e => e.id === empId)
    const cache = editCache[empId]
    if (!emp || !cache) continue

    const changes = []
    const fields = Object.keys(fieldLabels)
    for (const field of fields) {
      const oldVal = emp[field]
      const newVal = cache[field]
      if (oldVal == null && (newVal === '' || newVal === 0)) continue
      if (newVal == null && (oldVal === '' || oldVal === 0)) continue
      if (String(oldVal ?? '') !== String(newVal ?? '')) {
        changes.push({
          field,
          label: fieldLabels[field],
          old: getFieldDisplayValue(emp, field),
          new: dictFields.includes(field) ? getDictName(
            { contract_company_id: 'contract_company', department_id: 'department', position_id: 'position', status_id: 'employee_status' }[field],
            newVal
          ) : String(newVal ?? '')
        })
      }
    }

    if (changes.length > 0) {
      confirmList.value.push({ id: empId, name: emp.name, changes })
    }
  }

  confirmVisible.value = true
}

async function saveAllEdits() {
  savingEdits.value = true
  let successCount = 0
  let failCount = 0

  try {
    for (const item of confirmList.value) {
      try {
        const cache = editCache[item.id]
        const empPayload = {
          name: cache.name,
          gender: cache.gender,
          contract_company_id: cache.contract_company_id,
          department_id: cache.department_id,
          position_id: cache.position_id,
          status_id: cache.status_id,
          cost_owner: cache.cost_owner || null,
          phone: cache.phone || null,
          home_address: cache.home_address || null,
          entry_date: cache.entry_date || null,
          regular_date: cache.regular_date || null
        }
        await api.put(`/employees/${item.id}`, empPayload)

        const emp = employees.value.find(e => e.id === item.id)
        const salaryFields = ['base_salary', 'performance_standard', 'meal_allowance', 'transport_allowance', 'communication_allowance', 'computer_allowance', 'housing_allowance']
        let salaryChanged = false
        for (const f of salaryFields) {
          const oldV = emp[f]
          const newV = cache[f]
          if (oldV == null && (newV === 0 || newV === '')) continue
          if (String(oldV ?? '') !== String(newV ?? '')) {
            salaryChanged = true
            break
          }
        }
        if (String(emp.salary_effective_date ?? '') !== String(cache.salary_effective_date ?? '')) {
          salaryChanged = true
        }

        if (salaryChanged) {
          const salaryData = {
            employee_id: item.id,
            base_salary: cache.base_salary,
            performance_standard: cache.performance_standard,
            meal_allowance: cache.meal_allowance,
            transport_allowance: cache.transport_allowance,
            communication_allowance: cache.communication_allowance,
            computer_allowance: cache.computer_allowance,
            housing_allowance: cache.housing_allowance,
            effective_date: cache.salary_effective_date || new Date().toISOString().slice(0, 10),
            change_reason: '内联编辑批量修改'
          }
          await api.post('/employees/salaries', salaryData)
        }

        successCount++
      } catch (e) {
        failCount++
        console.error(`保存员工 ${item.id} 失败:`, e)
      }
    }

    confirmVisible.value = false
    changedSet.value = new Set()
    for (const key of Object.keys(editCache)) {
      delete editCache[key]
    }

    if (failCount === 0) {
      ElMessage.success(`成功保存 ${successCount} 名员工的修改`)
    } else {
      ElMessage.warning(`保存完成：成功 ${successCount} 人，失败 ${failCount} 人`)
    }

    await fetchData()
    if (editMode.value) {
      initEditCache()
    }
  } finally {
    savingEdits.value = false
  }
}

const originalSalary = ref(null)

const salaryEditForm = reactive({
  base_salary: 0, performance_standard: 0,
  meal_allowance: 0, transport_allowance: 0,
  communication_allowance: 0, computer_allowance: 0,
  housing_allowance: 0, effective_date: '', change_reason: ''
})

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  if (row) {
    Object.assign(form, {
      name: row.name, gender: row.gender, id_card: row.id_card,
      phone: row.phone || '', contract_company_id: row.contract_company_id,
      department_id: row.department_id, position_id: row.position_id,
      status_id: row.status_id, cost_owner: row.cost_owner || '',
      entry_date: row.entry_date,
      regular_date: row.regular_date || null, home_address: row.home_address || ''
    })
    Object.assign(salaryEditForm, {
      base_salary: row.base_salary || 0,
      performance_standard: row.performance_standard || 0,
      meal_allowance: row.meal_allowance || 0,
      transport_allowance: row.transport_allowance || 0,
      communication_allowance: row.communication_allowance || 0,
      computer_allowance: row.computer_allowance || 0,
      housing_allowance: row.housing_allowance || 0,
      effective_date: row.salary_effective_date || '',
      change_reason: ''
    })
    originalSalary.value = { ...salaryEditForm }
  } else {
    Object.assign(form, {
      name: '', gender: '男', id_card: '', phone: '',
      contract_company_id: companies.value[0]?.id || null,
      department_id: departments.value[0]?.id || null,
      position_id: positions.value[0]?.id || null,
      status_id: statuses.value[0]?.id || null,
      cost_owner: '', entry_date: '', regular_date: null, home_address: ''
    })
    Object.assign(salaryEditForm, {
      base_salary: 0, performance_standard: 0,
      meal_allowance: 0, transport_allowance: 0,
      communication_allowance: 0, computer_allowance: 0,
      housing_allowance: 0, effective_date: '', change_reason: ''
    })
    originalSalary.value = null
  }
  dialogVisible.value = true
}

function closeDialog() {
  dialogVisible.value = false
}

async function showSalaryHistory(row) {
  salaryHistoryName.value = row.name
  salaryHistoryVisible.value = true
  salaryHistoryLoading.value = true
  try {
    const res = await api.get(`/employees/${row.id}/salaries`)
    salaryHistory.value = res.data
  } catch (e) {
    ElMessage.error('获取薪资历史失败')
    salaryHistory.value = []
  } finally {
    salaryHistoryLoading.value = false
  }
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true

  const payload = {}
  for (const [key, value] of Object.entries(form)) {
    if (value === '') {
      payload[key] = null
    } else {
      payload[key] = value
    }
  }

  try {
    if (isEdit.value) {
      await api.put(`/employees/${editId.value}`, payload)
      ElMessage.success('编辑成功')
    } else {
      const res = await api.post('/employees/', payload)
      editId.value = res.data.id
      ElMessage.success('新增成功')
    }

    const salaryChanged = originalSalary.value
      ? (
        salaryEditForm.base_salary !== originalSalary.value.base_salary
        || salaryEditForm.performance_standard !== originalSalary.value.performance_standard
        || salaryEditForm.meal_allowance !== originalSalary.value.meal_allowance
        || salaryEditForm.transport_allowance !== originalSalary.value.transport_allowance
        || salaryEditForm.communication_allowance !== originalSalary.value.communication_allowance
        || salaryEditForm.computer_allowance !== originalSalary.value.computer_allowance
        || salaryEditForm.housing_allowance !== originalSalary.value.housing_allowance
        || salaryEditForm.effective_date !== originalSalary.value.effective_date
        || salaryEditForm.change_reason !== originalSalary.value.change_reason
      )
      : (
        salaryEditForm.base_salary > 0
        || salaryEditForm.performance_standard > 0
        || salaryEditForm.meal_allowance > 0
        || salaryEditForm.transport_allowance > 0
        || salaryEditForm.communication_allowance > 0
        || salaryEditForm.computer_allowance > 0
        || salaryEditForm.housing_allowance > 0
        || salaryEditForm.effective_date
      )

    if (salaryChanged) {
      const salaryData = {
        employee_id: editId.value,
        base_salary: salaryEditForm.base_salary,
        performance_standard: salaryEditForm.performance_standard,
        meal_allowance: salaryEditForm.meal_allowance,
        transport_allowance: salaryEditForm.transport_allowance,
        communication_allowance: salaryEditForm.communication_allowance,
        computer_allowance: salaryEditForm.computer_allowance,
        housing_allowance: salaryEditForm.housing_allowance,
        effective_date: salaryEditForm.effective_date || new Date().toISOString().slice(0, 10),
        change_reason: salaryEditForm.change_reason || undefined
      }
      try {
        await api.post('/employees/salaries', salaryData)
      } catch (salaryErr) {
        ElMessage.warning('员工信息已保存，但薪资记录创建失败：' + (salaryErr.response?.data?.detail || '请稍后重试'))
      }
    }

    closeDialog()
    fetchData()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || '请稍后重试'))
  } finally {
    saving.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除员工「${row.name}」吗？`, '删除确认', {
    type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消'
  })
  await api.delete(`/employees/${row.id}`)
  ElMessage.success('删除成功')
  fetchData()
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的员工')
    return
  }
  const names = selectedRows.value.map(r => r.name).join('、')
  await ElMessageBox.confirm(
    `确定要删除以下 ${selectedRows.value.length} 名员工吗？\n${names}`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.map(r => r.id)
    await api.post('/employees/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 名员工`)
    selectedRows.value = []
    fetchData()
  } catch (e) {
    ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

async function handleExport() {
  try {
    if (selectedRows.value.length > 0) {
      const ids = selectedRows.value.map(r => r.id)
      const res = await api.post('/employees/export-selected', ids, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `员工数据_已选${ids.length}人_${new Date().toISOString().slice(0, 10)}.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      ElMessage.success(`已导出 ${ids.length} 名员工`)
      return
    }
    const params = {}
    if (filterField.value && filterValue.value) {
      params.filter_field = filterField.value
      params.filter_value = filterValue.value
    }
    const res = await api.get('/employees/export', { params, responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `员工数据_${new Date().toISOString().slice(0, 10)}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

function showImport() {
  importFile.value = null
  fileList.value = []
  importResult.value = null
  importVisible.value = true
}

function handleFileChange(file) {
  importFile.value = file.raw
  importResult.value = null
}

async function doImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择 Excel 文件')
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    const res = await api.post('/employees/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    importResult.value = res.data
    if (!res.data.errors || !res.data.errors.length) {
      ElMessage.success(res.data.message)
      importVisible.value = false
      fetchData()
    }
  } catch (e) {
    ElMessage.error('导入失败：' + (e.response?.data?.detail || '请检查文件格式'))
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  fetchDicts()
  fetchData()
})
</script>

<style scoped>
.cell-input :deep(.el-input__wrapper) {
  padding: 0 4px;
}
.cell-input :deep(.el-input__inner) {
  text-align: left;
}
.cell-select {
  width: 100%;
}
.cell-select :deep(.el-input__wrapper) {
  padding: 0 4px;
}
.cell-number {
  width: 100%;
}
.cell-number :deep(.el-input__wrapper) {
  padding: 0 4px;
}
.cell-number :deep(.el-input__inner) {
  text-align: right;
}
.cell-date {
  width: 100%;
}
.cell-date :deep(.el-input__wrapper) {
  padding: 0 4px;
}
.text-ellipsis {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>