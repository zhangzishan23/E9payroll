<template>
  <template v-if="!dialogVisible">
    <div class="apple-card p-6">
      <div class="flex items-center gap-1.5 mb-4 flex-wrap">
        <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">员工档案管理</h3>
        <el-select v-model="filterField" placeholder="筛选字段" size="small" class="!w-24" @change="onFilterChange">
          <el-option label="姓名" value="name" />
          <el-option label="编号" value="no" />
          <el-option label="部门" value="department" />
          <el-option label="公司" value="company" />
          <el-option label="状态" value="status" />
        </el-select>
        <el-input v-model="filterValue" placeholder="筛选值" size="small" clearable class="!w-36" @input="fetchData" @clear="fetchData" />
        <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">新增</el-button>
        <el-button :icon="Upload" size="small" @click="showImport">导入</el-button>
        <el-button type="success" :icon="Download" size="small" @click="handleExport">导出</el-button>
        <el-tooltip content="仅同步「数据字典-部门」中已启动的部门员工" placement="bottom">
          <el-button type="warning" size="small" :loading="syncingRoster" @click="syncRoster">
            <el-icon class="mr-1"><Refresh /></el-icon>同步钉钉
          </el-button>
        </el-tooltip>
        <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
          删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
        </el-button>
        <el-divider direction="vertical" />
        <el-tooltip content="勾选后，已禁用部门的员工也会显示在列表中" placement="bottom">
          <el-checkbox v-model="showDisabledDept" size="small" @change="fetchData">
            显示已禁用部门员工
          </el-checkbox>
        </el-tooltip>
        <el-divider direction="vertical" />
        <el-tooltip content="选择要隐藏的员工状态，隐藏后该状态员工不在列表中显示" placement="bottom">
          <el-select v-model="hideStatusId" placeholder="隐藏状态" size="small" clearable class="!w-32" @change="onHideStatusChange">
            <el-option v-for="s in statuses" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-tooltip>
        <el-divider direction="vertical" />
        <el-button size="small" :type="editMode ? 'warning' : 'default'" @click="toggleEditMode">
          {{ editMode ? '退出编辑' : '编辑' }}
        </el-button>
        <template v-if="editMode">
          <el-button type="primary" size="small" :loading="savingEdits" :disabled="changedSet.size === 0" @click="confirmEdits">
            保存{{ changedSet.size ? `(${changedSet.size})` : '' }}
          </el-button>
          <el-button size="small" :disabled="changedSet.size === 0" @click="cancelEdits">取消</el-button>
        </template>
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
                <el-option v-for="d in enabledDepartments" :key="d.id" :label="d.name" :value="d.id" />
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
        <!-- 钉钉同步字段（只读） -->
        <el-table-column prop="id_card" label="证件号码" width="180" />
        <el-table-column prop="birth_date" label="出生日期" width="110" />
        <el-table-column prop="nation" label="民族" width="70" />
        <el-table-column prop="education" label="学历" width="80" />
        <el-table-column prop="graduate_school" label="毕业院校" width="150" />
        <el-table-column prop="graduate_date" label="毕业时间" width="110" />
        <el-table-column prop="major" label="所学专业" width="130" />
        <el-table-column prop="cert1" label="资格证/职称证1" width="140" />
        <el-table-column prop="cert2" label="资格证/职称证2" width="140" />
        <el-table-column prop="marital_status" label="婚姻状况" width="80" />
        <el-table-column prop="children_status" label="子女情况" width="90" />
        <el-table-column prop="political_status" label="政治面貌" width="90" />
        <el-table-column prop="native_place" label="籍贯" width="100" />
        <el-table-column prop="residence_type" label="户籍类型" width="90" />
        <el-table-column prop="census_address" label="户籍地址" width="180" />
        <el-table-column prop="emergency_contact_name" label="紧急联系人" width="110" />
        <el-table-column prop="emergency_contact_relation" label="联系人关系" width="100" />
        <el-table-column prop="emergency_contact_phone" label="联系人电话" width="120" />
        <el-table-column prop="contract_start_date" label="现合同起始日" width="120" />
        <el-table-column prop="contract_end_date" label="现合同到期日" width="120" />
        <el-table-column prop="insurance_start_date" label="五险一金起购日" width="130" />
        <el-table-column prop="insurance_location" label="社保公积金地" width="120" />
        <el-table-column prop="recruitment_channel" label="招聘渠道" width="100" />
        <el-table-column prop="hobby" label="特长爱好" width="120" />
        <el-table-column prop="commercial_insurance_type" label="商业保险类型" width="120" />
        <el-table-column prop="first_work_date" label="首次工作时间" width="120" />
        <el-table-column prop="bank_branch_detail" label="开户行支行" width="130" />
        <el-table-column prop="contract_type" label="合同类型" width="90" />
        <el-table-column prop="remark" label="备注" width="150" />
        <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button type="primary" link size="small" @click="showDialog(row)">详细编辑</el-button>
            <el-button type="success" link size="small" @click="showSalaryHistory(row)">薪资历史</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </div>
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

      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-tabs v-model="dialogTab">
          <el-tab-pane label="基本信息" name="basic">
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
              <el-form-item label="邮箱">
                <el-input v-model="form.email" />
              </el-form-item>
              <el-form-item label="办公地点">
                <el-input v-model="form.work_place" />
              </el-form-item>
              <el-form-item label="出生日期">
                <el-date-picker v-model="form.birth_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="民族">
                <el-input v-model="form.nation" />
              </el-form-item>
              <el-form-item label="婚姻状况">
                <el-select v-model="form.marital_status" class="w-full" clearable>
                  <el-option label="未婚" value="未婚" />
                  <el-option label="已婚" value="已婚" />
                  <el-option label="离异" value="离异" />
                  <el-option label="丧偶" value="丧偶" />
                </el-select>
              </el-form-item>
              <el-form-item label="子女情况">
                <el-input v-model="form.children_status" placeholder="如：1子1女" />
              </el-form-item>
              <el-form-item label="政治面貌">
                <el-select v-model="form.political_status" class="w-full" clearable>
                  <el-option label="群众" value="群众" />
                  <el-option label="党员" value="党员" />
                  <el-option label="团员" value="团员" />
                  <el-option label="民主党派" value="民主党派" />
                </el-select>
              </el-form-item>
              <el-form-item label="籍贯">
                <el-input v-model="form.native_place" />
              </el-form-item>
              <el-form-item label="户籍类型">
                <el-select v-model="form.residence_type" class="w-full" clearable>
                  <el-option label="城镇" value="城镇" />
                  <el-option label="农村" value="农村" />
                </el-select>
              </el-form-item>
              <el-form-item label="户籍地址">
                <el-input v-model="form.census_address" />
              </el-form-item>
              <el-form-item label="住址">
                <el-input v-model="form.home_address" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane label="工作信息" name="work">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
              <el-form-item label="合同公司" prop="contract_company_id">
                <el-select v-model="form.contract_company_id" class="w-full">
                  <el-option v-for="c in companies" :key="c.id" :label="c.name" :value="c.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="部门" prop="department_id">
                <el-select v-model="form.department_id" class="w-full">
                  <el-option v-for="d in enabledDepartments" :key="d.id" :label="d.name" :value="d.id" />
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
              <el-form-item label="员工类型">
                <el-input v-model="form.employee_type" />
              </el-form-item>
              <el-form-item label="岗位职级">
                <el-input v-model="form.position_level" />
              </el-form-item>
              <el-form-item label="岗位级别">
                <el-input v-model="form.job_level" />
              </el-form-item>
              <el-form-item label="直属主管">
                <el-input v-model="form.report_manager" />
              </el-form-item>
              <el-form-item label="费用负责人">
                <el-input v-model="form.cost_owner" />
              </el-form-item>
              <el-form-item label="入职时间" prop="entry_date">
                <el-date-picker v-model="form.entry_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="转正时间">
                <el-date-picker v-model="form.regular_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="离职日期">
                <el-date-picker v-model="form.resign_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="招聘渠道">
                <el-input v-model="form.recruitment_channel" />
              </el-form-item>
              <el-form-item label="特长爱好">
                <el-input v-model="form.hobby" />
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="form.remark" type="textarea" :rows="2" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane label="学历信息" name="edu">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
              <el-form-item label="学历">
                <el-select v-model="form.education" class="w-full" clearable>
                  <el-option label="小学" value="小学" />
                  <el-option label="初中" value="初中" />
                  <el-option label="高中" value="高中" />
                  <el-option label="中专" value="中专" />
                  <el-option label="大专" value="大专" />
                  <el-option label="本科" value="本科" />
                  <el-option label="硕士" value="硕士" />
                  <el-option label="博士" value="博士" />
                </el-select>
              </el-form-item>
              <el-form-item label="毕业院校">
                <el-input v-model="form.graduate_school" />
              </el-form-item>
              <el-form-item label="毕业时间">
                <el-date-picker v-model="form.graduate_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="所学专业">
                <el-input v-model="form.major" />
              </el-form-item>
              <el-form-item label="资格证/职称证1">
                <el-input v-model="form.cert1" />
              </el-form-item>
              <el-form-item label="资格证/职称证2">
                <el-input v-model="form.cert2" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane label="合同与社保" name="contract">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
              <el-form-item label="合同类型">
                <el-select v-model="form.contract_type" class="w-full" clearable>
                  <el-option label="固定期限" value="固定期限" />
                  <el-option label="无固定期限" value="无固定期限" />
                  <el-option label="完成一定任务" value="完成一定任务" />
                </el-select>
              </el-form-item>
              <el-form-item label="现合同起始日">
                <el-date-picker v-model="form.contract_start_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="现合同到期日">
                <el-date-picker v-model="form.contract_end_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="首次工作时间">
                <el-date-picker v-model="form.first_work_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="五险一金起购日">
                <el-date-picker v-model="form.insurance_start_date" type="date" class="w-full" value-format="YYYY-MM-DD" />
              </el-form-item>
              <el-form-item label="社保公积金购买地">
                <el-input v-model="form.insurance_location" />
              </el-form-item>
              <el-form-item label="商业保险类型">
                <el-input v-model="form.commercial_insurance_type" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane label="银行卡" name="bank">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
              <el-form-item label="银行卡号">
                <el-input v-model="form.bank_card" />
              </el-form-item>
              <el-form-item label="开户行">
                <el-input v-model="form.bank_branch" />
              </el-form-item>
              <el-form-item label="开户行支行">
                <el-input v-model="form.bank_branch_detail" />
              </el-form-item>
            </div>
          </el-tab-pane>

          <el-tab-pane label="紧急联系人" name="emergency">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0">
              <el-form-item label="联系人姓名">
                <el-input v-model="form.emergency_contact_name" />
              </el-form-item>
              <el-form-item label="联系人关系">
                <el-input v-model="form.emergency_contact_relation" placeholder="如：配偶、父母" />
              </el-form-item>
              <el-form-item label="联系人电话">
                <el-input v-model="form.emergency_contact_phone" />
              </el-form-item>
            </div>
          </el-tab-pane>
        </el-tabs>

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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Delete, ArrowLeft, Refresh } from '@element-plus/icons-vue'
import api from '../../api'

const loading = ref(false)
const saving = ref(false)
const savingEdits = ref(false)
const importing = ref(false)
const syncingRoster = ref(false)
const showDisabledDept = ref(false)
const hideStatusId = ref(null)
const dialogVisible = ref(false)
const dialogTab = ref('basic')
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
  name: '', gender: '男', id_card: '', phone: '', email: '', work_place: '',
  contract_company_id: null, department_id: null, position_id: null, status_id: null,
  position_level: '', employee_type: '', job_level: '', cost_owner: '', report_manager: '',
  entry_date: '', regular_date: null, resign_date: null, birth_date: null,
  nation: '', marital_status: '', children_status: '', political_status: '',
  native_place: '', residence_type: '', census_address: '', home_address: '',
  first_work_date: null, education: '', graduate_school: '', graduate_date: null, major: '',
  cert1: '', cert2: '',
  emergency_contact_name: '', emergency_contact_relation: '', emergency_contact_phone: '',
  contract_start_date: null, contract_end_date: null, contract_type: '',
  insurance_start_date: null, insurance_location: '', commercial_insurance_type: '',
  recruitment_channel: '', hobby: '', remark: '',
  bank_card: '', bank_branch: '', bank_branch_detail: ''
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

// 仅启用的部门（用于下拉选择）
const enabledDepartments = computed(() => {
  return departments.value.filter(d => d.is_enabled !== false)
})

async function fetchDicts() {
  const res = await api.get('/system/dict')
  const dicts = res.data
  companies.value = dicts.filter(d => d.category === 'contract_company')
  departments.value = dicts.filter(d => d.category === 'department')
  positions.value = dicts.filter(d => d.category === 'position')
  statuses.value = dicts.filter(d => d.category === 'employee_status')
}

function onFilterChange() {
  // 切换筛选字段时，如果已有筛选值则立即刷新
  if (filterValue.value) {
    fetchData()
  }
}

function onHideStatusChange() {
  // 切换隐藏状态时，保存偏好设置并刷新
  localStorage.setItem('employee_hide_status_id', hideStatusId.value || '')
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    const params = {}
    if (filterField.value && filterValue.value) {
      params.filter_field = filterField.value
      params.filter_value = filterValue.value
    }
    if (showDisabledDept.value) {
      params.include_disabled_dept = true
    }
    if (hideStatusId.value) {
      params.hide_status_id = hideStatusId.value
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
    if (!emp || !emp.id) continue
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
  try {
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
      initEditCache()
      editMode.value = true
      changedSet.value = new Set()
    }
  } catch (e) {
    console.error('切换编辑模式失败：', e)
    ElMessage.error('切换编辑模式失败，请刷新页面后重试')
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

  // 预校验：检查是否有员工被分配到已禁用的部门
  const disabledDeptIds = new Set(
    departments.value.filter(d => d.is_enabled === false).map(d => d.id)
  )
  const invalidItems = []
  for (const item of confirmList.value) {
    const cache = editCache[item.id]
    if (cache.department_id && disabledDeptIds.has(cache.department_id)) {
      const deptName = departments.value.find(d => d.id === cache.department_id)?.name || '未知'
      invalidItems.push(`「${item.name}」的部门「${deptName}」已被禁用`)
    }
  }
  if (invalidItems.length > 0) {
    ElMessage.error('以下员工的部门已被禁用，无法保存：\n' + invalidItems.join('；'))
    savingEdits.value = false
    return
  }

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
  dialogTab.value = 'basic'
  if (row) {
    Object.assign(form, {
      name: row.name, gender: row.gender, id_card: row.id_card,
      phone: row.phone || '', email: row.email || '', work_place: row.work_place || '',
      contract_company_id: row.contract_company_id,
      department_id: row.department_id, position_id: row.position_id,
      status_id: row.status_id,
      position_level: row.position_level || '', employee_type: row.employee_type || '',
      job_level: row.job_level || '', cost_owner: row.cost_owner || '',
      report_manager: row.report_manager || '',
      entry_date: row.entry_date, regular_date: row.regular_date || null,
      resign_date: row.resign_date || null, birth_date: row.birth_date || null,
      nation: row.nation || '', marital_status: row.marital_status || '',
      children_status: row.children_status || '', political_status: row.political_status || '',
      native_place: row.native_place || '', residence_type: row.residence_type || '',
      census_address: row.census_address || '', home_address: row.home_address || '',
      first_work_date: row.first_work_date || null, education: row.education || '',
      graduate_school: row.graduate_school || '', graduate_date: row.graduate_date || null,
      major: row.major || '', cert1: row.cert1 || '', cert2: row.cert2 || '',
      emergency_contact_name: row.emergency_contact_name || '',
      emergency_contact_relation: row.emergency_contact_relation || '',
      emergency_contact_phone: row.emergency_contact_phone || '',
      contract_start_date: row.contract_start_date || null,
      contract_end_date: row.contract_end_date || null,
      contract_type: row.contract_type || '',
      insurance_start_date: row.insurance_start_date || null,
      insurance_location: row.insurance_location || '',
      commercial_insurance_type: row.commercial_insurance_type || '',
      recruitment_channel: row.recruitment_channel || '',
      hobby: row.hobby || '', remark: row.remark || '',
      bank_card: row.bank_card || '', bank_branch: row.bank_branch || '',
      bank_branch_detail: row.bank_branch_detail || ''
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
      name: '', gender: '男', id_card: '', phone: '', email: '', work_place: '',
      contract_company_id: companies.value[0]?.id || null,
      department_id: enabledDepartments.value[0]?.id || null,
      position_id: positions.value[0]?.id || null,
      status_id: statuses.value[0]?.id || null,
      position_level: '', employee_type: '', job_level: '', cost_owner: '', report_manager: '',
      entry_date: '', regular_date: null, resign_date: null, birth_date: null,
      nation: '', marital_status: '', children_status: '', political_status: '',
      native_place: '', residence_type: '', census_address: '', home_address: '',
      first_work_date: null, education: '', graduate_school: '', graduate_date: null, major: '',
      cert1: '', cert2: '',
      emergency_contact_name: '', emergency_contact_relation: '', emergency_contact_phone: '',
      contract_start_date: null, contract_end_date: null, contract_type: '',
      insurance_start_date: null, insurance_location: '', commercial_insurance_type: '',
      recruitment_channel: '', hobby: '', remark: '',
      bank_card: '', bank_branch: '', bank_branch_detail: ''
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

  // 校验：不允许选择已禁用的部门
  if (form.department_id) {
    const selectedDept = departments.value.find(d => d.id === form.department_id)
    if (selectedDept && selectedDept.is_enabled === false) {
      ElMessage.error('所选部门「' + selectedDept.name + '」已被禁用，请选择启用的部门')
      return
    }
  }

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

async function syncRoster() {
  syncingRoster.value = true
  try {
    const res = await api.post('/dingtalk/sync/roster')
    const data = res.data
    if (data.errors && data.errors.length) {
      ElMessage.warning(`同步完成：新增${data.created}人，更新${data.updated}人，但有${data.errors.length}个错误`)
    } else {
      ElMessage.success(`钉钉花名册同步完成：新增${data.created}人，更新${data.updated}人`)
    }
    await fetchData()
  } catch (e) {
    ElMessage.error('同步失败：' + (e.response?.data?.detail || e.message))
  } finally {
    syncingRoster.value = false
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

onMounted(async () => {
  await fetchDicts()
  // 从 localStorage 恢复偏好设置
  const saved = localStorage.getItem('employee_hide_status_id')
  if (saved) {
    hideStatusId.value = Number(saved)
  }
  fetchData()
})
</script>

<style scoped>
.action-cell {
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}
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