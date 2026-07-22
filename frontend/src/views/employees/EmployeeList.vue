<template>
  <template v-if="!dialogVisible">
    <div class="apple-card p-6">
      <div class="flex items-center gap-1.5 mb-4 flex-wrap toolbar-sticky">
        <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">员工档案管理</h3>
        <el-select v-model="filterField" placeholder="筛选字段" size="small" class="!w-24" @change="onFilterChange">
          <el-option label="姓名" value="name" />
          <el-option label="编号" value="no" />
          <el-option label="部门" value="department" />
          <el-option label="公司" value="company" />
          <el-option label="状态" value="status" />
        </el-select>
        <el-input v-model="filterValue" placeholder="筛选值" size="small" clearable class="!w-36" @input="fetchData" @clear="fetchData" />
        <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)" v-permission="'employee:create'">新增</el-button>
        <el-button :icon="Upload" size="small" @click="showImport" v-permission="'employee:import'">导入</el-button>
        <el-button type="info" :icon="Download" size="small" @click="downloadTemplate" v-permission="'employee:import'">下载模板</el-button>
        <el-button type="success" :icon="Download" size="small" @click="handleExport" v-permission="'employee:export'">导出</el-button>
        <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete" v-permission="'employee:delete'">
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
        <el-button size="small" :type="editMode ? 'warning' : 'default'" @click="toggleEditMode" v-permission="'employee:edit'">
          {{ editMode ? '退出编辑' : '编辑' }}
        </el-button>
        <ColumnSetting
          :columns="TABLE_COLUMNS"
          :default-visible-keys="DEFAULT_VISIBLE_COLUMNS"
          v-model="visibleColumns"
          storage-key="employee_table_columns"
        />
        <template v-if="editMode">
          <el-button type="primary" size="small" :loading="savingEdits" :disabled="changedSet.size === 0" @click="confirmEdits" v-permission="'employee:edit'">
            保存{{ changedSet.size ? `(${changedSet.size})` : '' }}
          </el-button>
          <el-button size="small" :disabled="changedSet.size === 0" @click="cancelEdits">取消</el-button>
        </template>
        <div class="ml-auto">
          <el-tooltip content="一键从钉钉同步部门和员工信息（已禁用的部门不同步）" placement="bottom">
            <el-button type="success" class="!text-base !px-5 !py-4 !rounded-lg" :loading="syncingRoster" @click="syncRoster" v-permission="'employee:sync'">
              <el-icon class="!text-lg mr-1"><Refresh /></el-icon>同步钉钉
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <el-table :data="employees" border stripe v-loading="loading" class="w-full" :max-height="tableMaxHeight" table-layout="fixed" @selection-change="handleSelectionChange">
        <el-table-column v-if="isColumnVisible('selection')" type="selection" width="55" />
        <el-table-column v-if="isColumnVisible('employee_no')" prop="employee_no" label="员工编号" width="100" fixed />
        <el-table-column v-if="isColumnVisible('name')" prop="name" label="姓名" width="100" fixed />
        <el-table-column v-if="isColumnVisible('gender')" prop="gender" label="性别" width="70" />
        <el-table-column v-if="isColumnVisible('contract_company_name')" prop="contract_company_name" label="合同公司" width="110" />
        <el-table-column v-if="isColumnVisible('department_name')" prop="department_name" label="部门" width="100" />
        <el-table-column v-if="isColumnVisible('position_name')" prop="position_name" label="职务" width="90" />
        <el-table-column v-if="isColumnVisible('status_name')" prop="status_name" label="状态" width="80" />
        <el-table-column v-if="isColumnVisible('cost_owner')" prop="cost_owner" label="费用负责人" width="100" />
        <el-table-column v-if="isColumnVisible('phone')" prop="phone" label="联系电话" width="120" />
        <el-table-column v-if="isColumnVisible('home_address')" prop="home_address" label="家庭住址" width="180">
          <template #default="{ row }">
            <span class="text-ellipsis">{{ row.home_address }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('entry_date')" prop="entry_date" label="入职时间" width="120" />
        <el-table-column v-if="isColumnVisible('regular_date')" prop="regular_date" label="转正时间" width="120">
          <template #default="{ row }">
            {{ row.regular_date || '' }}
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('base_salary')" prop="base_salary" label="基本工资" width="100">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].base_salary" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ formatMoney(row.base_salary) }}</template>
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('performance_standard')" prop="performance_standard" label="绩效标准" width="100">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].performance_standard" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ formatMoney(row.performance_standard) }}</template>
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('meal_allowance')" prop="meal_allowance" label="餐补" width="85">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].meal_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ formatMoney(row.meal_allowance) }}</template>
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('transport_allowance')" prop="transport_allowance" label="交通补贴" width="95">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].transport_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ formatMoney(row.transport_allowance) }}</template>
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('communication_allowance')" prop="communication_allowance" label="通讯补贴" width="95">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].communication_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ formatMoney(row.communication_allowance) }}</template>
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('computer_allowance')" prop="computer_allowance" label="电脑补贴" width="95">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].computer_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ formatMoney(row.computer_allowance) }}</template>
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('housing_allowance')" prop="housing_allowance" label="住房补贴" width="95">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-input-number v-model="editCache[row.id].housing_allowance" :min="0" :precision="2" size="small" class="cell-number" controls-position="right" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ formatMoney(row.housing_allowance) }}</template>
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('monthly_standard')" label="月薪标准" width="100">
          <template #default="{ row }">
            {{ formatMoney(monthlyStandard(row)) }}
          </template>
        </el-table-column>
        <el-table-column v-if="isColumnVisible('salary_effective_date')" prop="salary_effective_date" label="薪资生效日" width="120">
          <template #default="{ row }">
            <template v-if="editMode">
              <el-date-picker v-model="editCache[row.id].salary_effective_date" type="date" size="small" class="cell-date" value-format="YYYY-MM-DD" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.salary_effective_date || '' }}</template>
          </template>
        </el-table-column>
        <!-- 钉钉同步字段（只读） -->
        <el-table-column v-if="isColumnVisible('id_card')" prop="id_card" label="证件号码" width="180" />
        <el-table-column v-if="isColumnVisible('birth_date')" prop="birth_date" label="出生日期" width="110" />
        <el-table-column v-if="isColumnVisible('nation')" prop="nation" label="民族" width="70" />
        <el-table-column v-if="isColumnVisible('education')" prop="education" label="学历" width="80" />
        <el-table-column v-if="isColumnVisible('graduate_school')" prop="graduate_school" label="毕业院校" width="150" />
        <el-table-column v-if="isColumnVisible('graduate_date')" prop="graduate_date" label="毕业时间" width="110" />
        <el-table-column v-if="isColumnVisible('major')" prop="major" label="所学专业" width="130" />
        <el-table-column v-if="isColumnVisible('cert1')" prop="cert1" label="资格证/职称证1" width="140" />
        <el-table-column v-if="isColumnVisible('cert2')" prop="cert2" label="资格证/职称证2" width="140" />
        <el-table-column v-if="isColumnVisible('marital_status')" prop="marital_status" label="婚姻状况" width="80" />
        <el-table-column v-if="isColumnVisible('children_status')" prop="children_status" label="子女情况" width="90" />
        <el-table-column v-if="isColumnVisible('political_status')" prop="political_status" label="政治面貌" width="90" />
        <el-table-column v-if="isColumnVisible('native_place')" prop="native_place" label="籍贯" width="100" />
        <el-table-column v-if="isColumnVisible('residence_type')" prop="residence_type" label="户籍类型" width="90" />
        <el-table-column v-if="isColumnVisible('census_address')" prop="census_address" label="户籍地址" width="180" />
        <el-table-column v-if="isColumnVisible('emergency_contact_name')" prop="emergency_contact_name" label="紧急联系人" width="110" />
        <el-table-column v-if="isColumnVisible('emergency_contact_relation')" prop="emergency_contact_relation" label="联系人关系" width="100" />
        <el-table-column v-if="isColumnVisible('emergency_contact_phone')" prop="emergency_contact_phone" label="联系人电话" width="120" />
        <el-table-column v-if="isColumnVisible('contract_start_date')" prop="contract_start_date" label="现合同起始日" width="120" />
        <el-table-column v-if="isColumnVisible('contract_end_date')" prop="contract_end_date" label="现合同到期日" width="120" />
        <el-table-column v-if="isColumnVisible('insurance_start_date')" prop="insurance_start_date" label="五险一金起购日" width="130" />
        <el-table-column v-if="isColumnVisible('insurance_location')" prop="insurance_location" label="社保公积金地" width="120" />
        <el-table-column v-if="isColumnVisible('recruitment_channel')" prop="recruitment_channel" label="招聘渠道" width="100" />
        <el-table-column v-if="isColumnVisible('hobby')" prop="hobby" label="特长爱好" width="120" />
        <el-table-column v-if="isColumnVisible('commercial_insurance_type')" prop="commercial_insurance_type" label="商业保险类型" width="120" />
        <el-table-column v-if="isColumnVisible('first_work_date')" prop="first_work_date" label="首次工作时间" width="120" />
        <el-table-column v-if="isColumnVisible('bank_branch_detail')" prop="bank_branch_detail" label="开户行支行" width="130" />
        <el-table-column v-if="isColumnVisible('contract_type')" prop="contract_type" label="合同类型" width="90" />
        <el-table-column v-if="isColumnVisible('remark')" prop="remark" label="备注" width="150" />
        <el-table-column v-if="isColumnVisible('action')" label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button type="primary" link size="small" @click="showDialog(row)" v-permission="'employee:edit'">详细编辑</el-button>
            <el-button type="success" link size="small" @click="showSalaryHistory(row)">薪资历史</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)" v-permission="'employee:delete'">删除</el-button>
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

    <el-dialog v-model="salaryHistoryVisible" :title="'薪资历史 - ' + salaryHistoryName" width="900px" append-to-body>
      <el-table :data="salaryHistory" border stripe max-height="400" v-loading="salaryHistoryLoading">
        <el-table-column prop="effective_date" label="生效日期" width="110" />
        <el-table-column prop="base_salary" label="基本工资" width="100" align="right">
          <template #default="{ row }">{{ formatMoney(row.base_salary) }}</template>
        </el-table-column>
        <el-table-column prop="performance_standard" label="绩效标准" width="100" align="right">
          <template #default="{ row }">{{ formatMoney(row.performance_standard) }}</template>
        </el-table-column>
        <el-table-column prop="meal_allowance" label="餐补" width="80" align="right">
          <template #default="{ row }">{{ formatMoney(row.meal_allowance) }}</template>
        </el-table-column>
        <el-table-column prop="transport_allowance" label="交通补贴" width="90" align="right">
          <template #default="{ row }">{{ formatMoney(row.transport_allowance) }}</template>
        </el-table-column>
        <el-table-column prop="communication_allowance" label="通讯补贴" width="90" align="right">
          <template #default="{ row }">{{ formatMoney(row.communication_allowance) }}</template>
        </el-table-column>
        <el-table-column prop="computer_allowance" label="电脑补贴" width="90" align="right">
          <template #default="{ row }">{{ formatMoney(row.computer_allowance) }}</template>
        </el-table-column>
        <el-table-column prop="housing_allowance" label="住房补贴" width="90" align="right">
          <template #default="{ row }">{{ formatMoney(row.housing_allowance) }}</template>
        </el-table-column>
        <el-table-column prop="change_reason" label="变更原因" min-width="100">
          <template #default="{ row }">{{ row.change_reason || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="调整时间" width="140">
          <template #default="{ row }">{{ row.created_at || '-' }}</template>
        </el-table-column>
        <el-table-column prop="operator_name" label="操作人" width="90">
          <template #default="{ row }">{{ row.operator_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{ row }">
            <el-button type="danger" link size="small" @click="handleDeleteSalary(row)" v-permission="'employee:edit'">删除</el-button>
          </template>
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
          <el-button type="info" :icon="Download" @click="downloadTemplate">
            下载导入模板
          </el-button>
        </div>
        <div class="text-sm text-gray-500">
          <p class="mb-1">请先下载导入模板，按模板格式填写数据后再导入。</p>
          <p class="text-orange-600 font-medium">注意：本模板仅用于补充钉钉同步不到的信息（费用负责人、薪资数据），员工必须先从钉钉同步后再导入。</p>
          <p>必填项：姓名*；填写薪资数据时需同时填写「薪资生效日期」</p>
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
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Delete, ArrowLeft, Refresh } from '@element-plus/icons-vue'
import api from '../../api'
import ColumnSetting from '../../components/ColumnSetting.vue'
import { formatMoney, formatInt } from '../../utils/format'

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
const salaryHistoryEmpId = ref(null)
const salaryHistoryLoading = ref(false)

const editMode = ref(false)
const editCache = reactive({})
const changedSet = ref(new Set())
const confirmVisible = ref(false)
const confirmList = ref([])
const tableMaxHeight = ref(500)

function updateTableHeight() {
  tableMaxHeight.value = Math.max(400, window.innerHeight - 260)
}

const TABLE_COLUMNS = [
  { key: 'selection', label: '选择', required: true },
  { key: 'employee_no', label: '员工编号', required: true },
  { key: 'name', label: '姓名', required: true },
  { key: 'gender', label: '性别' },
  { key: 'contract_company_name', label: '合同公司' },
  { key: 'department_name', label: '部门' },
  { key: 'position_name', label: '职务' },
  { key: 'status_name', label: '状态' },
  { key: 'cost_owner', label: '费用负责人' },
  { key: 'phone', label: '联系电话' },
  { key: 'home_address', label: '家庭住址' },
  { key: 'entry_date', label: '入职时间' },
  { key: 'regular_date', label: '转正时间' },
  { key: 'base_salary', label: '基本工资' },
  { key: 'performance_standard', label: '绩效标准' },
  { key: 'meal_allowance', label: '餐补' },
  { key: 'transport_allowance', label: '交通补贴' },
  { key: 'communication_allowance', label: '通讯补贴' },
  { key: 'computer_allowance', label: '电脑补贴' },
  { key: 'housing_allowance', label: '住房补贴' },
  { key: 'monthly_standard', label: '月薪标准' },
  { key: 'salary_effective_date', label: '薪资生效日' },
  { key: 'id_card', label: '证件号码' },
  { key: 'birth_date', label: '出生日期' },
  { key: 'nation', label: '民族' },
  { key: 'education', label: '学历' },
  { key: 'graduate_school', label: '毕业院校' },
  { key: 'graduate_date', label: '毕业时间' },
  { key: 'major', label: '所学专业' },
  { key: 'cert1', label: '资格证/职称证1' },
  { key: 'cert2', label: '资格证/职称证2' },
  { key: 'marital_status', label: '婚姻状况' },
  { key: 'children_status', label: '子女情况' },
  { key: 'political_status', label: '政治面貌' },
  { key: 'native_place', label: '籍贯' },
  { key: 'residence_type', label: '户籍类型' },
  { key: 'census_address', label: '户籍地址' },
  { key: 'emergency_contact_name', label: '紧急联系人' },
  { key: 'emergency_contact_relation', label: '联系人关系' },
  { key: 'emergency_contact_phone', label: '联系人电话' },
  { key: 'contract_start_date', label: '现合同起始日' },
  { key: 'contract_end_date', label: '现合同到期日' },
  { key: 'insurance_start_date', label: '五险一金起购日' },
  { key: 'insurance_location', label: '社保公积金地' },
  { key: 'recruitment_channel', label: '招聘渠道' },
  { key: 'hobby', label: '特长爱好' },
  { key: 'commercial_insurance_type', label: '商业保险类型' },
  { key: 'first_work_date', label: '首次工作时间' },
  { key: 'bank_branch_detail', label: '开户行支行' },
  { key: 'contract_type', label: '合同类型' },
  { key: 'remark', label: '备注' },
  { key: 'action', label: '操作', required: true },
]

const DEFAULT_VISIBLE_COLUMNS = [
  'selection', 'employee_no', 'name', 'gender', 'contract_company_name',
  'department_name', 'position_name', 'status_name', 'cost_owner',
  'phone', 'entry_date', 'base_salary', 'action'
]

const visibleColumns = ref([])

function isColumnVisible(key) {
  return visibleColumns.value.includes(key)
}

// 编辑模式下仅可编辑工资项目字段（非钉钉同步字段）
const salaryEditFields = [
  'base_salary', 'performance_standard', 'meal_allowance', 'transport_allowance',
  'communication_allowance', 'computer_allowance', 'housing_allowance', 'salary_effective_date'
]

const fieldLabels = {
  base_salary: '基本工资',
  performance_standard: '绩效标准',
  meal_allowance: '餐补',
  transport_allowance: '交通补贴',
  communication_allowance: '通讯补贴',
  computer_allowance: '电脑补贴',
  housing_allowance: '住房补贴',
  salary_effective_date: '薪资生效日'
}


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

function monthlyStandard(row) {
  const base = Number(row.base_salary) || 0
  const perf = Number(row.performance_standard) || 0
  const meal = Number(row.meal_allowance) || 0
  const transport = Number(row.transport_allowance) || 0
  const comm = Number(row.communication_allowance) || 0
  const computer = Number(row.computer_allowance) || 0
  const housing = Number(row.housing_allowance) || 0
  const total = base + perf + meal + transport + comm + computer + housing
  return total === 0 ? null : total
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
  for (const field of salaryEditFields) {
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
    for (const field of salaryEditFields) {
      const oldVal = emp[field]
      const newVal = cache[field]
      if (oldVal == null && (newVal === '' || newVal === 0)) continue
      if (newVal == null && (oldVal === '' || oldVal === 0)) continue
      if (String(oldVal ?? '') !== String(newVal ?? '')) {
        changes.push({
          field,
          label: fieldLabels[field],
          old: oldVal != null ? (typeof oldVal === 'number' ? oldVal.toFixed(2) : String(oldVal)) : '(空)',
          new: newVal != null ? (typeof newVal === 'number' ? newVal.toFixed(2) : String(newVal)) : '(空)'
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
        // 更新员工薪资字段
        const empPayload = {
          base_salary: cache.base_salary,
          performance_standard: cache.performance_standard,
          meal_allowance: cache.meal_allowance,
          transport_allowance: cache.transport_allowance,
          communication_allowance: cache.communication_allowance,
          computer_allowance: cache.computer_allowance,
          housing_allowance: cache.housing_allowance,
          salary_effective_date: cache.salary_effective_date || null
        }
        await api.put(`/employees/${item.id}`, empPayload)

        // 创建薪资历史记录
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
  salaryHistoryEmpId.value = row.id
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

async function handleDeleteSalary(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除生效日期为 ${row.effective_date} 的这条薪资记录吗？`,
      '删除确认',
      { type: 'warning', confirmButtonType: 'danger' }
    )
  } catch {
    return
  }
  try {
    await api.delete(`/employees/salaries/${row.id}`)
    ElMessage.success('删除成功')
    const res = await api.get(`/employees/${salaryHistoryEmpId.value}/salaries`)
    salaryHistory.value = res.data
    await fetchData()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
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

async function downloadTemplate() {
  try {
    const res = await api.get('/employees/import-template', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '员工档案导入模板.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('模板下载成功')
  } catch (e) {
    ElMessage.error('模板下载失败')
  }
}

async function syncRoster() {
  syncingRoster.value = true
  try {
    const res = await api.post('/dingtalk/sync/roster')
    const data = res.data
    if (data.errors && data.errors.length) {
      ElMessage.warning(data.message || `同步完成：新增${data.created}人，更新${data.updated}人，但有${data.errors.length}个错误`)
    } else {
      ElMessage.success(data.message || `钉钉同步完成：新增${data.created}人，更新${data.updated}人`)
    }
    await fetchDicts()
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
  updateTableHeight()
  window.addEventListener('resize', updateTableHeight)
  await fetchDicts()
  // 从 localStorage 恢复偏好设置
  const saved = localStorage.getItem('employee_hide_status_id')
  if (saved) {
    hideStatusId.value = Number(saved)
  }
  fetchData()
})

onUnmounted(() => {
  window.removeEventListener('resize', updateTableHeight)
})
</script>

<style scoped>
.toolbar-sticky {
  position: sticky;
  top: 0;
  z-index: 10;
  background: inherit;
  padding-bottom: 4px;
}
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