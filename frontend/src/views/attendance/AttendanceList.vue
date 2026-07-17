<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-1.5 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">考勤管理</h3>
      <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" @change="onPeriodChange" />
      <el-select v-model="filterField" placeholder="筛选字段" size="small" class="!w-24">
        <el-option label="员工编号" value="employee_no" />
        <el-option label="员工姓名" value="employee_name" />
      </el-select>
      <el-input v-model="filterValue" placeholder="筛选值" size="small" clearable class="!w-36" @input="fetchData" />
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)" v-permission="'attendance:create'">录入</el-button>
      <el-button :icon="Upload" size="small" @click="showImport" v-permission="'attendance:import'">导入</el-button>
      <el-button type="success" :icon="Download" size="small" @click="handleExport" v-permission="'attendance:export'">导出</el-button>
      <el-button type="warning" size="small" :loading="syncingAttendance" @click="syncAttendance" v-permission="'attendance:sync'">
        <el-icon class="mr-1"><Refresh /></el-icon>同步钉钉
      </el-button>
      <el-button type="success" size="small" :loading="checkingWriteOff" @click="openMissedPunchCheck" v-permission="'attendance:writeoff'">
        <el-icon class="mr-1"><Check /></el-icon>缺卡核销
      </el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete" v-permission="'attendance:delete'">
        删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
      </el-button>
      <el-divider direction="vertical" />
      <el-button size="small" type="info" @click="openSalaryCalendar">计薪日历</el-button>
      <el-button size="small" :type="editMode ? 'warning' : 'default'" @click="toggleEditMode" v-permission="'attendance:edit'">
        {{ editMode ? '退出编辑' : '编辑' }}
      </el-button>
      <el-divider direction="vertical" />
      <el-tooltip content="锁定后的数据在同步钉钉或导入时不会被覆盖" placement="top">
        <el-button size="small" type="warning" :disabled="!selectedRows.length" @click="batchLockRows" v-permission="'attendance:edit'">
          <el-icon class="mr-1"><Lock /></el-icon>锁定选中{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
        </el-button>
      </el-tooltip>
      <el-button size="small" :disabled="!selectedRows.length" @click="batchUnlockRows" v-permission="'attendance:edit'">
        解锁选中{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
      </el-button>
      <ColumnSetting
        :columns="TABLE_COLUMNS"
        :default-visible-keys="DEFAULT_VISIBLE_COLUMNS"
        v-model="visibleColumns"
        storage-key="attendance_table_columns"
      />
      <template v-if="editMode">
        <el-button type="primary" size="small" :loading="savingEdits" :disabled="changedSet.size === 0" @click="confirmEdits" v-permission="'attendance:edit'">
          保存{{ changedSet.size ? `(${changedSet.size})` : '' }}
        </el-button>
        <el-button size="small" :disabled="changedSet.size === 0" @click="cancelEdits">取消</el-button>
      </template>
    </div>

    <el-alert
      v-if="mismatchCount > 0"
      type="error"
      :closable="false"
      show-icon
      class="mb-4"
      title="计薪天数异常"
    >
      <template #default>
        检测到 <b>{{ mismatchCount }}</b> 条记录的「当月总计薪天数」与「应计薪天数」不一致，请先点击「计薪日历」检查年度工作日历配置是否正确（修改后关闭弹窗会自动重算对应月份），避免工资核算错误！
      </template>
    </el-alert>

    <el-table :data="records" border stripe v-loading="loading" max-height="600" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
      <el-table-column v-if="isColumnVisible('selection')" type="selection" width="45" />
      <el-table-column v-if="isColumnVisible('index')" type="index" label="序号" width="50" />
      <el-table-column v-if="isColumnVisible('employee_name')" prop="employee_name" label="员工姓名" width="80" fixed show-overflow-tooltip />
      <el-table-column v-if="isColumnVisible('contract_company')" prop="contract_company" label="合同主体" width="120" show-overflow-tooltip />
      <el-table-column v-if="isColumnVisible('department')" prop="department" label="部门" width="100" show-overflow-tooltip />
      <el-table-column v-if="isColumnVisible('lock_status')" label="锁定状态" width="95" align="center">
        <template #default="{ row }">
          <el-tooltip v-if="row.is_row_locked" content="整行已锁定，同步/导入时不会被覆盖" placement="top">
            <span class="text-red-500 flex items-center justify-center gap-0.5">
              <el-icon><Lock /></el-icon> 已锁定
            </span>
          </el-tooltip>
          <el-tooltip v-else-if="row.locked_fields && Object.keys(row.locked_fields).length" content="部分字段已锁定" placement="top">
            <span class="text-orange-500 flex items-center justify-center gap-0.5">
              <el-icon><Lock /></el-icon> 部分锁定
            </span>
          </el-tooltip>
          <span v-else class="text-gray-400">未锁定</span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('salary_start_date')" prop="salary_start_date" label="计薪开始日期" width="110">
        <template #default="{ row }">{{ formatDate(row.salary_start_date) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('salary_end_date')" prop="salary_end_date" label="计薪截至日期" width="110">
        <template #default="{ row }">{{ formatDate(row.salary_end_date) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('total_work_days')" prop="total_work_days" label="当月总计薪天数" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'total_work_days')">
            <el-input-number v-model="editCache[row.id].total_work_days" :min="0" :max="31" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'total_work_days') }">{{ formatNumber(row.total_work_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'total_work_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('adjusted_salary_days')" prop="adjusted_salary_days" label="应计薪天数" width="95">
        <template #default="{ row }">
          <span :class="{ 'text-red-600 font-bold': isDaysMismatch(row) }">
            {{ formatNumber(row.adjusted_salary_days, 2) }}
            <el-icon v-if="isDaysMismatch(row)" class="text-red-500 ml-0.5 text-xs align-middle"><WarningFilled /></el-icon>
          </span>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('actual_salary_days')" prop="actual_salary_days" label="计薪天数" width="85">
        <template #default="{ row }">{{ formatNumber(row.actual_salary_days, 2) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('attendance_rate')" prop="attendance_rate" label="出勤率" width="80">
        <template #default="{ row }">{{ formatPercent(row.attendance_rate) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('half_day_missed_punch')" prop="half_day_missed_punch" label="半天缺卡（次数）" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'half_day_missed_punch')">
            <el-input-number v-model="editCache[row.id].half_day_missed_punch" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'half_day_missed_punch') }">{{ formatInt(row.half_day_missed_punch) }}</span>
            <el-icon v-if="isFieldLocked(row, 'half_day_missed_punch')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('absenteeism_days')" prop="absenteeism_days" label="全天缺卡（天数）" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'absenteeism_days')">
            <el-input-number v-model="editCache[row.id].absenteeism_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'absenteeism_days') }">{{ formatNumber(row.absenteeism_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'absenteeism_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('late_count')" prop="late_count" label="迟到次数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'late_count')">
            <el-input-number v-model="editCache[row.id].late_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'late_count') }">{{ formatInt(row.late_count) }}</span>
            <el-icon v-if="isFieldLocked(row, 'late_count')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('late_duration')" prop="late_duration" label="迟到时长（分钟）" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'late_duration')">
            <el-input-number v-model="editCache[row.id].late_duration" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'late_duration') }">{{ formatInt(row.late_duration) }}</span>
            <el-icon v-if="isFieldLocked(row, 'late_duration')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('severe_late_count')" prop="severe_late_count" label="严重迟到次数" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'severe_late_count')">
            <el-input-number v-model="editCache[row.id].severe_late_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'severe_late_count') }">{{ formatInt(row.severe_late_count) }}</span>
            <el-icon v-if="isFieldLocked(row, 'severe_late_count')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('severe_late_duration')" prop="severe_late_duration" label="严重迟到时长（分钟）" width="130">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'severe_late_duration')">
            <el-input-number v-model="editCache[row.id].severe_late_duration" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'severe_late_duration') }">{{ formatInt(row.severe_late_duration) }}</span>
            <el-icon v-if="isFieldLocked(row, 'severe_late_duration')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('early_count')" prop="early_count" label="早退次数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'early_count')">
            <el-input-number v-model="editCache[row.id].early_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'early_count') }">{{ formatInt(row.early_count) }}</span>
            <el-icon v-if="isFieldLocked(row, 'early_count')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('early_duration')" prop="early_duration" label="早退时长（分钟）" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'early_duration')">
            <el-input-number v-model="editCache[row.id].early_duration" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'early_duration') }">{{ formatInt(row.early_duration) }}</span>
            <el-icon v-if="isFieldLocked(row, 'early_duration')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('total_overtime')" prop="total_overtime" label="加班（小时）" width="90">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'total_overtime')">
            <el-input-number v-model="editCache[row.id].total_overtime" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'total_overtime') }">{{ formatNumber(row.total_overtime, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'total_overtime')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('late_to_personal_leave_days')" prop="late_to_personal_leave_days" label="迟到转事假" width="95">
        <template #default="{ row }">{{ formatNumber(row.late_to_personal_leave_days, 2) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('personal_leave_days')" prop="personal_leave_days" label="事假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'personal_leave_days')">
            <el-input-number v-model="editCache[row.id].personal_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'personal_leave_days') }">{{ formatNumber(row.personal_leave_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'personal_leave_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('full_pay_sick_days')" prop="full_pay_sick_days" label="全薪病假" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'full_pay_sick_days')">
            <el-input-number v-model="editCache[row.id].full_pay_sick_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'full_pay_sick_days') }">{{ formatNumber(row.full_pay_sick_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'full_pay_sick_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('reduced_pay_sick_days')" prop="reduced_pay_sick_days" label="减薪病假" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'reduced_pay_sick_days')">
            <el-input-number v-model="editCache[row.id].reduced_pay_sick_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'reduced_pay_sick_days') }">{{ formatNumber(row.reduced_pay_sick_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'reduced_pay_sick_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('statutory_sick_days')" prop="statutory_sick_days" label="法定病假" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'statutory_sick_days')">
            <el-input-number v-model="editCache[row.id].statutory_sick_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'statutory_sick_days') }">{{ formatNumber(row.statutory_sick_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'statutory_sick_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('compensatory_leave_days')" prop="compensatory_leave_days" label="调休" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'compensatory_leave_days')">
            <el-input-number v-model="editCache[row.id].compensatory_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'compensatory_leave_days') }">{{ formatNumber(row.compensatory_leave_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'compensatory_leave_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('annual_leave_days')" prop="annual_leave_days" label="年假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'annual_leave_days')">
            <el-input-number v-model="editCache[row.id].annual_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'annual_leave_days') }">{{ formatNumber(row.annual_leave_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'annual_leave_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('prenatal_checkup_days')" prop="prenatal_checkup_days" label="产检假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'prenatal_checkup_days')">
            <el-input-number v-model="editCache[row.id].prenatal_checkup_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'prenatal_checkup_days') }">{{ formatNumber(row.prenatal_checkup_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'prenatal_checkup_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('maternity_leave_days')" prop="maternity_leave_days" label="产假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'maternity_leave_days')">
            <el-input-number v-model="editCache[row.id].maternity_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'maternity_leave_days') }">{{ formatNumber(row.maternity_leave_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'maternity_leave_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('paternity_leave_days')" prop="paternity_leave_days" label="陪产假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'paternity_leave_days')">
            <el-input-number v-model="editCache[row.id].paternity_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'paternity_leave_days') }">{{ formatNumber(row.paternity_leave_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'paternity_leave_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('marriage_leave_days')" prop="marriage_leave_days" label="婚假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'marriage_leave_days')">
            <el-input-number v-model="editCache[row.id].marriage_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'marriage_leave_days') }">{{ formatNumber(row.marriage_leave_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'marriage_leave_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('funeral_leave_days')" prop="funeral_leave_days" label="丧假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'funeral_leave_days')">
            <el-input-number v-model="editCache[row.id].funeral_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'funeral_leave_days') }">{{ formatNumber(row.funeral_leave_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'funeral_leave_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('engineering_compensatory_days')" prop="engineering_compensatory_days" label="调休-工程交付（天）" width="140">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'engineering_compensatory_days')">
            <el-input-number v-model="editCache[row.id].engineering_compensatory_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'engineering_compensatory_days') }">{{ formatNumber(row.engineering_compensatory_days, 2) }}</span>
            <el-icon v-if="isFieldLocked(row, 'engineering_compensatory_days')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('leave_total_days')" prop="leave_total_days" label="合计" width="70">
        <template #default="{ row }">{{ formatNumber(row.leave_total_days, 2) }}</template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('remark')" prop="remark" label="备注" min-width="130" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id] && !isFieldLocked(row, 'remark')">
            <el-input v-model="editCache[row.id].remark" size="small" class="cell-input" @input="markChanged(row.id)" />
          </template>
          <template v-else>
            <span :class="{ 'text-gray-400': isFieldLocked(row, 'remark') }">{{ row.remark || '' }}</span>
            <el-icon v-if="isFieldLocked(row, 'remark')" class="text-orange-400 ml-0.5 text-xs align-middle"><Lock /></el-icon>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="isColumnVisible('action')" label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <template v-if="!editMode">
              <el-button v-if="row.id" type="primary" link size="small" @click="showDialog(row)" v-permission="'attendance:edit'">编辑</el-button>
              <el-button v-else type="success" link size="small" @click="showDialogForEmployee(row)" v-permission="'attendance:create'">录入</el-button>
              <el-divider direction="vertical" />
              <el-tooltip v-if="row.is_row_locked" content="点击解锁" placement="top">
                <el-button type="warning" link size="small" @click="toggleRowLock(row, false)" v-permission="'attendance:edit'">
                  <el-icon><Unlock /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip v-else content="点击锁定整行（同步/导入时不覆盖）" placement="top">
                <el-button type="info" link size="small" @click="toggleRowLock(row, true)" v-permission="'attendance:edit'">
                  <el-icon><Lock /></el-icon>
                </el-button>
              </el-tooltip>
            </template>
            <template v-else>
              <span v-if="row.is_row_locked" class="text-gray-400 text-xs">已锁定，不可编辑</span>
            </template>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 录入/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑考勤' : '录入考勤'" width="820px" append-to-body class="attendance-dialog">
      <el-form ref="formRef" :model="form" label-width="125px" class="attendance-form">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="核算周期" required>
              <el-input v-model="form.period" placeholder="YYYYMM" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="员工编号">
              <el-input :model-value="formEmployeeNo" disabled />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="当月总计薪天数" required>
              <el-input-number v-model="form.total_work_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="应计薪天数">
              <el-input-number v-model="form.adjusted_salary_days" :min="0" :precision="1" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="迟到次数">
              <el-input-number v-model="form.late_count" :min="0" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="迟到时长(分钟)">
              <el-input-number v-model="form.late_duration" :min="0" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="迟到转事假">
              <el-input-number v-model="form.late_to_personal_leave_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="严重迟到次数">
              <el-input-number v-model="form.severe_late_count" :min="0" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="严重迟到时长">
              <el-input-number v-model="form.severe_late_duration" :min="0" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="加班(小时)">
              <el-input-number v-model="form.total_overtime" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="早退次数">
              <el-input-number v-model="form.early_count" :min="0" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="早退时长(分钟)">
              <el-input-number v-model="form.early_duration" :min="0" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="半天缺卡">
              <el-input-number v-model="form.half_day_missed_punch" :min="0" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">请假明细（天）</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="事假">
              <el-input-number v-model="form.personal_leave_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="全薪病假">
              <el-input-number v-model="form.full_pay_sick_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="减薪病假">
              <el-input-number v-model="form.reduced_pay_sick_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="法定病假">
              <el-input-number v-model="form.statutory_sick_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="调休">
              <el-input-number v-model="form.compensatory_leave_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="年假">
              <el-input-number v-model="form.annual_leave_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="产检假">
              <el-input-number v-model="form.prenatal_checkup_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="产假">
              <el-input-number v-model="form.maternity_leave_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="陪产假">
              <el-input-number v-model="form.paternity_leave_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="婚假">
              <el-input-number v-model="form.marriage_leave_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="丧假">
              <el-input-number v-model="form.funeral_leave_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="调休-工程交付">
              <el-input-number v-model="form.engineering_compensatory_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="全天缺卡">
              <el-input-number v-model="form.absenteeism_days" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导入弹窗 -->
    <el-dialog v-model="importVisible" title="批量导入考勤" width="700px" append-to-body>
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
          <el-button type="success" :loading="importing" :disabled="!importFile" @click="doImport">开始导入</el-button>
        </div>
        <div class="text-sm text-gray-500">
          支持 .xlsx / .xls 格式，表头需包含：员工编号、当月总计薪天数、应计薪天数、计薪天数、半天缺卡(次数)、全天缺卡(天数)、迟到次数/时长、严重迟到次数/时长、早退次数/时长、加班(小时)、迟到转事假、事假、全薪病假、减薪病假、法定病假、调休、年假、产检假、产假、陪产假、婚假、丧假、调休-工程交付(天)、合计、备注
        </div>
        <div v-if="importResult" class="mt-3">
          <el-alert
            :type="importResult.errors && importResult.errors.length ? 'warning' : 'success'"
            :title="importResult.message"
            :closable="false"
          />
          <div v-if="importResult.errors && importResult.errors.length" class="mt-2 text-sm text-red-500">
            <div v-for="(err, i) in importResult.errors" :key="i">{{ err }}</div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 编辑确认弹窗 -->
    <el-dialog v-model="editConfirmVisible" title="确认保存修改" width="600px" append-to-body>
      <div class="mb-2 text-gray-600">以下考勤数据将被更新，请确认：</div>
      <el-table :data="confirmList" border stripe max-height="400">
        <el-table-column prop="employee_name" label="姓名" width="80" />
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
        <el-button @click="editConfirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdits" @click="saveAllEdits">确认保存</el-button>
      </template>
    </el-dialog>

    <!-- 年度工作日历弹窗 -->
    <el-dialog v-model="calendarVisible" title="年度工作日历配置" width="1100px" append-to-body top="5vh" @close="onCalendarClose">
      <div class="mb-4 flex items-center gap-3 flex-wrap">
        <el-date-picker v-model="calendarYearPicker" type="year" placeholder="选择年份" size="default" :clearable="false" style="width: 130px" @change="loadYearCalendar" />
        <el-button type="primary" :icon="MagicStick" :loading="aiGenerating" @click="aiGenerateCalendar">
          AI 预填{{ displayCalendarYear }}年节假日
        </el-button>
        <el-button type="warning" :icon="RefreshRight" :loading="recalculating" :disabled="touchedPeriods.size === 0" @click="recalculateAttendance">
          {{ touchedPeriods.size > 0 ? `立即重算已改月份(${touchedPeriods.size})` : '点击日期切换状态' }}
        </el-button>
        <el-divider direction="vertical" />
        <div class="text-sm text-gray-600">
          全年计薪天数：<b class="text-blue-600 text-base">{{ yearSummary.total_salary_days || 0 }}</b> 天
          <span class="mx-2">|</span>
          工作日：<span class="text-green-600">{{ yearSummary.workdays || 0 }}</span>
          <span class="mx-1">|</span>
          节假日：<span class="text-red-500">{{ yearSummary.holidays || 0 }}</span>
          <span class="mx-1">|</span>
          调休补班：<span class="text-orange-500">{{ yearSummary.makeup_work || 0 }}</span>
        </div>
      </div>
      <div class="mb-3 text-xs text-gray-500 flex items-center gap-4">
        <span><span class="inline-block w-3 h-3 rounded bg-blue-100 border border-blue-300 mr-1 align-middle"></span> 工作日（计薪）</span>
        <span><span class="inline-block w-3 h-3 rounded bg-gray-100 mr-1 align-middle"></span> 周末（不计薪）</span>
        <span><span class="inline-block w-3 h-3 rounded bg-red-100 border border-red-300 mr-1 align-middle"></span> 法定节假日（不计薪）</span>
        <span><span class="inline-block w-3 h-3 rounded bg-orange-100 border border-orange-300 mr-1 align-middle"></span> 调休补班（计薪）</span>
        <span class="ml-auto">点击日期循环切换：工作日 → 节假日 → 调休补班 → 工作日</span>
      </div>
      <div v-loading="calendarLoading" class="year-calendar-grid">
        <div v-for="m in 12" :key="m" class="month-card">
          <div class="month-header">
            <span class="month-title">{{ m }}月</span>
            <span class="month-stats">计薪 <b :class="getMonthSalaryClass(m)">{{ getMonthSalaryDays(m) }}</b> 天</span>
          </div>
          <div class="mini-calendar">
            <div class="mini-weekday" v-for="wd in ['一','二','三','四','五','六','日']" :key="wd">{{ wd }}</div>
            <template v-for="blank in getMonthBlanks(m)" :key="'b'+m+'-'+blank">
              <div class="mini-cell blank"></div>
            </template>
            <div
              v-for="d in getMonthDays(m)"
              :key="d.date"
              class="mini-cell"
              :class="getDayClass(d)"
              :title="getDayTitle(d)"
              @click="toggleDay(d)"
            >
              {{ d.day }}
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="calendarVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 缺卡核销预览弹窗 -->
    <el-dialog v-model="writeOffVisible" title="缺卡核销（特殊申请自动清零）" width="900px" append-to-body top="5vh">
      <div v-loading="checkingWriteOff" class="mb-4">
        <div v-if="writeOffResult" class="mb-4">
          <el-alert type="info" :closable="false" show-icon class="mb-3">
            <template #title>
              查询范围：{{ writeOffResult.apply_range }} 期间提交的审批通过的考勤特殊申请
            </template>
          </el-alert>
          
          <div class="flex gap-4 mb-4">
            <el-statistic title="有缺卡记录员工" :value="writeOffResult.summary.total_miss_employees" />
            <el-statistic title="✅ 申请次数匹配" :value="writeOffResult.summary.matched" class="text-green-600" />
            <el-statistic title="⚠️ 次数不匹配" :value="writeOffResult.summary.mismatched" class="text-orange-600" />
            <el-statistic title="❌ 无申请" :value="writeOffResult.summary.no_apply" class="text-red-600" />
          </div>

          <el-tabs v-model="writeOffActiveTab">
            <el-tab-pane :label="`✅ 可核销 (${writeOffResult.matched.length})`" name="matched">
              <div v-if="writeOffResult.matched.length === 0" class="text-gray-400 text-center py-8">
                暂无可以自动核销的员工
              </div>
              <el-table v-else :data="writeOffResult.matched" border stripe max-height="350" @selection-change="handleWriteOffSelection">
                <el-table-column type="selection" width="45" />
                <el-table-column prop="employee_name" label="员工姓名" width="100" />
                <el-table-column label="系统缺卡" width="200">
                  <template #default="{ row }">
                    <span>半天缺卡: {{ row.half_day_missed_punch }}次</span><br/>
                    <span>全天缺卡: {{ row.absenteeism_days }}天 ({{ row.absenteeism_days * 2 }}次)</span><br/>
                    <b class="text-blue-600">合计: {{ row.total_missed }}次</b>
                  </template>
                </el-table-column>
                <el-table-column label="申请明细" min-width="300">
                  <template #default="{ row }">
                    <div v-for="(apply, idx) in row.applies" :key="idx" class="mb-2 pb-2 border-b last:border-0">
                      <div class="text-sm">
                        <span class="text-green-600 font-medium">申请{{ idx+1 }} ({{ apply.apply_count }}次)</span>
                        <span class="text-gray-400 text-xs ml-2">{{ apply.create_time }}</span>
                      </div>
                      <div class="text-xs text-gray-600 mt-1">{{ apply.description }}</div>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            
            <el-tab-pane :label="`⚠️ 次数不匹配 (${writeOffResult.mismatched.length})`" name="mismatched">
              <div v-if="writeOffResult.mismatched.length === 0" class="text-gray-400 text-center py-8">
                无不匹配记录
              </div>
              <el-table v-else :data="writeOffResult.mismatched" border stripe max-height="350">
                <el-table-column prop="employee_name" label="员工姓名" width="100" />
                <el-table-column label="系统缺卡" width="150">
                  <template #default="{ row }">
                    <b>{{ row.total_missed }}次</b><br/>
                    <span class="text-xs text-gray-500">半天{{ row.half_day_missed_punch }}+全天{{ row.absenteeism_days }}天</span>
                  </template>
                </el-table-column>
                <el-table-column label="申请次数" width="100">
                  <template #default="{ row }">
                    <b class="text-orange-600">{{ row.total_apply_count }}次</b>
                  </template>
                </el-table-column>
                <el-table-column label="差额" width="80">
                  <template #default="{ row }">
                    <span :class="row.total_apply_count - row.total_missed > 0 ? 'text-red-500' : 'text-orange-500'">
                      {{ row.total_apply_count - row.total_missed > 0 ? '+' : '' }}{{ row.total_apply_count - row.total_missed }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="申请说明" min-width="300" show-overflow-tooltip>
                  <template #default="{ row }">
                    <div v-for="(apply, idx) in row.applies" :key="idx" class="text-sm">
                      {{ apply.description }}
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            
            <el-tab-pane :label="`❌ 无申请 (${writeOffResult.no_apply.length})`" name="no_apply">
              <div v-if="writeOffResult.no_apply.length === 0" class="text-gray-400 text-center py-8">
                所有缺卡员工均有申请记录
              </div>
              <el-table v-else :data="writeOffResult.no_apply" border stripe max-height="350">
                <el-table-column prop="employee_name" label="员工姓名" width="120" />
                <el-table-column label="系统缺卡次数" width="200">
                  <template #default="{ row }">
                    <b class="text-red-500">{{ row.total_missed }}次</b>
                    <span class="text-xs text-gray-500 ml-2">
                      (半天{{ row.half_day_missed_punch }}次 + 全天{{ row.absenteeism_days }}天)
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="提示" min-width="200">
                  <template #default>
                    <span class="text-gray-500 text-sm">未查询到审批通过的考勤特殊申请，请人工确认</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="writeOffVisible = false">关闭</el-button>
        <el-button 
          type="primary" 
          :disabled="!writeOffResult || writeOffResult.matched.length === 0 || selectedWriteOffRows.length === 0"
          :loading="writingOff"
          @click="confirmWriteOff"
        >
          核销选中的 {{ selectedWriteOffRows.length }} 人
        </el-button>
        <el-button 
          type="success" 
          :disabled="!writeOffResult || writeOffResult.matched.length === 0"
          :loading="writingOffAll"
          @click="confirmWriteOffAll"
        >
          一键核销全部匹配 ({{ writeOffResult?.matched.length || 0 }}人)
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Delete, Refresh, MagicStick, RefreshRight, WarningFilled, Lock, Unlock, Check } from '@element-plus/icons-vue'
import api from '../../api'
import ColumnSetting from '../../components/ColumnSetting.vue'
import { formatNumber, formatInt, formatPercent } from '../../utils/format'

function getDefaultPeriod() {
  const now = new Date()
  const bjOffset = 8 * 60
  const localOffset = now.getTimezoneOffset()
  const bjTime = new Date(now.getTime() + (bjOffset + localOffset) * 60 * 1000)
  const year = bjTime.getFullYear()
  const month = bjTime.getMonth() + 1
  const day = bjTime.getDate()
  let targetYear, targetMonth
  if (day < 15) {
    if (month === 1) { targetYear = year - 1; targetMonth = 12 }
    else { targetYear = year; targetMonth = month - 1 }
  } else {
    targetYear = year; targetMonth = month
  }
  return `${targetYear}${String(targetMonth).padStart(2, '0')}`
}

const defaultPeriod = getDefaultPeriod()

const TABLE_COLUMNS = [
  { key: 'selection', label: '选择', required: true },
  { key: 'index', label: '序号', required: true },
  { key: 'employee_name', label: '员工姓名', required: true },
  { key: 'contract_company', label: '合同主体' },
  { key: 'department', label: '部门' },
  { key: 'lock_status', label: '锁定状态' },
  { key: 'salary_start_date', label: '计薪开始日期' },
  { key: 'salary_end_date', label: '计薪截至日期' },
  { key: 'total_work_days', label: '当月总计薪天数' },
  { key: 'adjusted_salary_days', label: '应计薪天数', required: true },
  { key: 'actual_salary_days', label: '计薪天数' },
  { key: 'attendance_rate', label: '出勤率' },
  { key: 'half_day_missed_punch', label: '半天缺卡' },
  { key: 'absenteeism_days', label: '全天缺卡' },
  { key: 'late_count', label: '迟到次数' },
  { key: 'late_duration', label: '迟到时长' },
  { key: 'severe_late_count', label: '严重迟到次数' },
  { key: 'severe_late_duration', label: '严重迟到时长' },
  { key: 'early_count', label: '早退次数' },
  { key: 'early_duration', label: '早退时长' },
  { key: 'total_overtime', label: '加班小时' },
  { key: 'late_to_personal_leave_days', label: '迟到转事假' },
  { key: 'personal_leave_days', label: '事假' },
  { key: 'full_pay_sick_days', label: '全薪病假' },
  { key: 'reduced_pay_sick_days', label: '减薪病假' },
  { key: 'statutory_sick_days', label: '法定病假' },
  { key: 'compensatory_leave_days', label: '调休' },
  { key: 'annual_leave_days', label: '年假' },
  { key: 'prenatal_checkup_days', label: '产检假' },
  { key: 'maternity_leave_days', label: '产假' },
  { key: 'paternity_leave_days', label: '陪产假' },
  { key: 'marriage_leave_days', label: '婚假' },
  { key: 'funeral_leave_days', label: '丧假' },
  { key: 'engineering_compensatory_days', label: '调休-工程交付' },
  { key: 'leave_total_days', label: '合计', required: true },
  { key: 'remark', label: '备注' },
  { key: 'action', label: '操作', required: true }
]

const DEFAULT_VISIBLE_COLUMNS = [
  'selection', 'index', 'employee_name', 'department', 'lock_status', 'total_work_days',
  'adjusted_salary_days', 'actual_salary_days', 'attendance_rate', 'late_count',
  'absenteeism_days', 'total_overtime', 'personal_leave_days', 'leave_total_days', 'action'
]

const visibleColumns = ref([])

function isColumnVisible(key) {
  return visibleColumns.value.includes(key)
}

const loading = ref(false)
const saving = ref(false)
const savingEdits = ref(false)
const importing = ref(false)
const syncingAttendance = ref(false)
const dialogVisible = ref(false)
const importVisible = ref(false)
const isEdit = ref(false)
const periodDate = ref(defaultPeriod)
const filterField = ref('')
const filterValue = ref('')
const records = ref([])
const selectedRows = ref([])
const importFile = ref(null)
const fileList = ref([])
const importResult = ref(null)
const uploadRef = ref(null)
const formRef = ref(null)
const editId = ref(null)
const formEmployeeId = ref(null)
const formEmployeeNo = ref('')

const editMode = ref(false)
const editCache = reactive({})
const changedSet = ref(new Set())
const editConfirmVisible = ref(false)
const confirmList = ref([])

// 年度工作日历相关
const calendarVisible = ref(false)
const calendarYearPicker = ref(new Date())
const calendarLoading = ref(false)
const aiGenerating = ref(false)
const recalculating = ref(false)
const yearCalendarDays = ref([])
const yearSummary = ref({})
const touchedPeriods = ref(new Set())

// 缺卡核销相关
const writeOffVisible = ref(false)
const checkingWriteOff = ref(false)
const writingOff = ref(false)
const writingOffAll = ref(false)
const writeOffResult = ref(null)
const writeOffActiveTab = ref('matched')
const selectedWriteOffRows = ref([])

const displayCalendarYear = computed(() => {
  if (!calendarYearPicker.value) return new Date().getFullYear()
  if (calendarYearPicker.value instanceof Date) return calendarYearPicker.value.getFullYear()
  const y = Number(calendarYearPicker.value)
  return isNaN(y) ? new Date().getFullYear() : y
})

const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
const weekdayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

function getMonthDays(month) {
  return yearCalendarDays.value.filter(d => d.month === month)
}

function getMonthBlanks(month) {
  const days = getMonthDays(month)
  if (!days.length) return []
  const firstDay = days[0]
  return Array(firstDay.weekday).fill(0)
}

function getMonthSalaryDays(month) {
  const days = getMonthDays(month)
  return days.filter(d => d.is_salary_day).length
}

function getMonthSalaryClass(month) {
  const days = getMonthDays(month)
  const salary = days.filter(d => d.is_salary_day).length
  const total = days.length
  if (total === 0) return ''
  return salary <= 20 ? 'text-red-500' : 'text-blue-600'
}

function getDayClass(d) {
  const classes = []
  switch (d.day_type) {
    case 'holiday':
      classes.push('day-holiday')
      break
    case 'makeup_work':
      classes.push('day-makeup')
      break
    case 'weekend':
      classes.push('day-weekend')
      break
    default:
      classes.push(d.is_salary_day ? 'day-work' : 'day-weekend')
  }
  if (d.remark) classes.push('day-has-remark')
  return classes.join(' ')
}

function getDayTitle(d) {
  let title = `${d.date} ${weekdayNames[d.weekday]}`
  if (d.remark) title += ` - ${d.remark}`
  title += d.is_salary_day ? '（计薪）' : '（不计薪）'
  return title
}

const fieldLabels = {
  total_work_days: '当月总计薪天数',
  adjusted_salary_days: '应计薪天数',
  actual_salary_days: '计薪天数',
  attendance_rate: '出勤率',
  late_count: '迟到次数',
  late_duration: '迟到时长(分钟)',
  severe_late_count: '严重迟到次数',
  severe_late_duration: '严重迟到时长(分钟)',
  early_count: '早退次数',
  early_duration: '早退时长(分钟)',
  half_day_missed_punch: '半天缺卡(次数)',
  absenteeism_days: '全天缺卡(天数)',
  total_overtime: '加班(小时)',
  late_to_personal_leave_days: '迟到转事假',
  personal_leave_days: '事假',
  full_pay_sick_days: '全薪病假',
  reduced_pay_sick_days: '减薪病假',
  statutory_sick_days: '法定病假',
  compensatory_leave_days: '调休',
  annual_leave_days: '年假',
  prenatal_checkup_days: '产检假',
  maternity_leave_days: '产假',
  paternity_leave_days: '陪产假',
  marriage_leave_days: '婚假',
  funeral_leave_days: '丧假',
  engineering_compensatory_days: '调休-工程交付(天)',
  leave_total_days: '合计',
  remark: '备注'
}

const editFields = [
  'total_work_days', 'late_count', 'late_duration',
  'severe_late_count', 'severe_late_duration',
  'early_count', 'early_duration',
  'half_day_missed_punch', 'absenteeism_days',
  'total_overtime',
  'personal_leave_days', 'full_pay_sick_days',
  'reduced_pay_sick_days', 'statutory_sick_days',
  'compensatory_leave_days', 'annual_leave_days',
  'prenatal_checkup_days', 'maternity_leave_days',
  'paternity_leave_days', 'marriage_leave_days',
  'funeral_leave_days', 'engineering_compensatory_days',
  'remark'
]

const form = reactive({
  period: defaultPeriod, employee_id: null,
  total_work_days: 22, adjusted_salary_days: 22, actual_salary_days: 22,
  late_count: 0, late_duration: 0, late_to_personal_leave_days: 0,
  severe_late_count: 0, severe_late_duration: 0,
  early_count: 0, early_duration: 0,
  half_day_missed_punch: 0, absenteeism_days: 0,
  total_overtime: 0,
  personal_leave_days: 0, full_pay_sick_days: 0, reduced_pay_sick_days: 0,
  statutory_sick_days: 0, compensatory_leave_days: 0, annual_leave_days: 0,
  prenatal_checkup_days: 0, maternity_leave_days: 0, paternity_leave_days: 0,
  marriage_leave_days: 0, funeral_leave_days: 0, engineering_compensatory_days: 0,
  leave_total_days: 0, remark: ''
})

const formValues = () => ({
  period: defaultPeriod, employee_id: null,
  total_work_days: 22, adjusted_salary_days: 22, actual_salary_days: 22,
  late_count: 0, late_duration: 0, late_to_personal_leave_days: 0,
  severe_late_count: 0, severe_late_duration: 0,
  early_count: 0, early_duration: 0,
  half_day_missed_punch: 0, absenteeism_days: 0,
  total_overtime: 0,
  personal_leave_days: 0, full_pay_sick_days: 0, reduced_pay_sick_days: 0,
  statutory_sick_days: 0, compensatory_leave_days: 0, annual_leave_days: 0,
  prenatal_checkup_days: 0, maternity_leave_days: 0, paternity_leave_days: 0,
  marriage_leave_days: 0, funeral_leave_days: 0, engineering_compensatory_days: 0,
  leave_total_days: 0, remark: ''
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  if (dateStr.length === 10 && dateStr.includes('-')) return dateStr
  return dateStr
}



function onPeriodChange() { fetchData() }

function isDaysMismatch(row) {
  if (row.total_work_days == null || row.adjusted_salary_days == null) return false
  return Number(row.total_work_days) !== Number(row.adjusted_salary_days)
}

const mismatchCount = computed(() => {
  return records.value.filter(row => isDaysMismatch(row)).length
})

function tableRowClassName({ row }) {
  const classes = []
  if (editMode.value && row.id && changedSet.value.has(row.id)) classes.push('row-changed')
  if (isDaysMismatch(row)) classes.push('row-mismatch')
  if (row.is_row_locked) classes.push('row-locked')
  return classes.join(' ')
}

function initEditCache() {
  records.value.forEach(row => {
    if (!row || !row.id) return
    editCache[row.id] = reactive({})
    editFields.forEach(f => {
      editCache[row.id][f] = row[f] ?? ''
    })
  })
}

function markChanged(rowId) {
  changedSet.value = new Set(changedSet.value)
  changedSet.value.add(rowId)
}

function toggleEditMode() {
  try {
    if (editMode.value) {
      editMode.value = false
      changedSet.value = new Set()
      for (const key of Object.keys(editCache)) { delete editCache[key] }
      return
    }
    initEditCache()
    editMode.value = true
    changedSet.value = new Set()
  } catch (e) {
    ElMessage.error('切换编辑模式失败，请刷新页面后重试')
  }
}

function cancelEdits() {
  editMode.value = false
  changedSet.value = new Set()
  for (const key of Object.keys(editCache)) { delete editCache[key] }
}

function confirmEdits() {
  if (!changedSet.value.size) {
    ElMessage.warning('没有检测到任何修改')
    return
  }
  const rows = []
  changedSet.value.forEach(id => {
    const row = records.value.find(r => r.id === id)
    if (!row) return
    const changes = []
    editFields.forEach(field => {
      const oldVal = row[field]
      const newVal = editCache[id]?.[field]
      if (String(oldVal ?? '') !== String(newVal ?? '')) {
        changes.push({
          field, label: fieldLabels[field] || field,
          old: oldVal != null ? String(oldVal) : '(空)',
          new: newVal != null ? String(newVal) : '(空)'
        })
      }
    })
    if (changes.length) {
      rows.push({ id, employee_name: row.employee_name, employee_no: row.employee_no, changes })
    }
  })
  confirmList.value = rows
  editConfirmVisible.value = true
}

async function saveAllEdits() {
  savingEdits.value = true
  let successCount = 0, failCount = 0
  try {
    for (const row of confirmList.value) {
      const cache = editCache[row.id]
      if (!cache) continue
      const payload = {}
      editFields.forEach(field => {
        if (cache[field] != null && cache[field] !== '') payload[field] = cache[field]
      })
      try {
        await api.put(`/attendance/${row.id}`, payload)
        successCount++
      } catch { failCount++ }
    }
    if (failCount === 0) ElMessage.success(`修改成功！共更新 ${successCount} 条记录`)
    else ElMessage.warning(`部分成功：${successCount} 条已更新，${failCount} 条失败`)

    editConfirmVisible.value = false
    editMode.value = false
    changedSet.value = new Set()
    for (const key of Object.keys(editCache)) { delete editCache[key] }
    await fetchData()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    savingEdits.value = false
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params = { period: periodDate.value }
    if (filterField.value && filterValue.value) {
      params.filter_field = filterField.value
      params.filter_value = filterValue.value
    }
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get('/attendance/', { params })
    records.value = res.data
  } finally {
    loading.value = false
  }
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  formEmployeeId.value = row?.employee_id || null
  formEmployeeNo.value = row?.employee_no || ''
  if (row) {
    Object.assign(form, {
      period: row.period, employee_id: row.employee_id,
      total_work_days: row.total_work_days ?? 22,
      adjusted_salary_days: row.adjusted_salary_days ?? row.total_work_days ?? 22,
      actual_salary_days: row.actual_salary_days ?? 22,
      late_count: row.late_count ?? 0, late_duration: row.late_duration ?? 0,
      late_to_personal_leave_days: row.late_to_personal_leave_days ?? 0,
      severe_late_count: row.severe_late_count ?? 0, severe_late_duration: row.severe_late_duration ?? 0,
      early_count: row.early_count ?? 0, early_duration: row.early_duration ?? 0,
      half_day_missed_punch: row.half_day_missed_punch ?? 0,
      absenteeism_days: row.absenteeism_days ?? 0,
      total_overtime: row.total_overtime ?? 0,
      personal_leave_days: row.personal_leave_days ?? 0,
      full_pay_sick_days: row.full_pay_sick_days ?? 0,
      reduced_pay_sick_days: row.reduced_pay_sick_days ?? 0,
      statutory_sick_days: row.statutory_sick_days ?? 0,
      compensatory_leave_days: row.compensatory_leave_days ?? 0,
      annual_leave_days: row.annual_leave_days ?? 0,
      prenatal_checkup_days: row.prenatal_checkup_days ?? 0,
      maternity_leave_days: row.maternity_leave_days ?? 0,
      paternity_leave_days: row.paternity_leave_days ?? 0,
      marriage_leave_days: row.marriage_leave_days ?? 0,
      funeral_leave_days: row.funeral_leave_days ?? 0,
      engineering_compensatory_days: row.engineering_compensatory_days ?? 0,
      leave_total_days: row.leave_total_days ?? 0,
      remark: row.remark || ''
    })
  } else {
    Object.assign(form, formValues())
  }
  dialogVisible.value = true
}

function showDialogForEmployee(row) {
  isEdit.value = false
  editId.value = null
  formEmployeeId.value = row.employee_id
  formEmployeeNo.value = row.employee_no
  Object.assign(form, { ...formValues(), period: periodDate.value, employee_id: row.employee_id })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/attendance/${editId.value}`, form)
      ElMessage.success('编辑成功')
    } else {
      await api.post('/attendance/', form)
      ElMessage.success('录入成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

function handleSelectionChange(selection) { selectedRows.value = selection }

async function handleExport() {
  try {
    const params = { period: periodDate.value }
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get('/attendance/export', { params, responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `考勤数据_${periodDate.value}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) { ElMessage.error('导出失败') }
}

async function syncAttendance() {
  syncingAttendance.value = true
  try {
    const period = periodDate.value
    const res = await api.post('/dingtalk/sync/attendance', null, { params: { period } })
    const data = res.data
    if (data.errors && data.errors.length) {
      ElMessage.warning(`同步完成：${data.message}，但有${data.errors.length}个错误`)
    } else {
      ElMessage.success(`钉钉考勤同步完成：${data.message}`)
    }
    await fetchData()
  } catch (e) {
    ElMessage.error('同步失败：' + (e.response?.data?.detail || e.message))
  } finally { syncingAttendance.value = false }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) { ElMessage.warning('请先选择要删除的考勤记录'); return }
  await ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 条考勤记录吗？`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.filter(r => r.id).map(r => r.id)
    if (!ids.length) { ElMessage.warning('选中的记录中没有可删除的已录入数据'); return }
    await api.post('/attendance/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 条考勤记录`)
    selectedRows.value = []
    fetchData()
  } catch (e) {
    ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

function isFieldLocked(row, field) {
  if (row.is_row_locked) return true
  if (row.locked_fields && row.locked_fields[field]) return true
  return false
}

async function toggleRowLock(row, lock) {
  if (!row.id) {
    ElMessage.warning('请先录入该员工考勤数据后再锁定')
    return
  }
  const action = lock ? '锁定' : '解锁'
  try {
    const formData = new FormData()
    formData.append('locked', lock ? 'true' : 'false')
    await api.post(`/attendance/${row.id}/lock-row`, formData)
    ElMessage.success(`${action}成功`)
    await fetchData()
  } catch (e) {
    ElMessage.error(`${action}失败：` + (e.response?.data?.detail || e.message))
  }
}

async function batchLockRows() {
  const lockableRows = selectedRows.value.filter(r => r.id && !r.is_row_locked)
  if (!lockableRows.length) {
    ElMessage.warning('选中的记录中没有可锁定的已录入数据')
    return
  }
  await ElMessageBox.confirm(
    `确定要锁定选中的 ${lockableRows.length} 条考勤记录吗？锁定后的数据在同步钉钉或导入时不会被覆盖。`,
    '批量锁定确认',
    { type: 'warning', confirmButtonText: '确定锁定', cancelButtonText: '取消' }
  )
  let successCount = 0, failCount = 0
  for (const row of lockableRows) {
    try {
      const formData = new FormData()
      formData.append('locked', 'true')
      await api.post(`/attendance/${row.id}/lock-row`, formData)
      successCount++
    } catch {
      failCount++
    }
  }
  if (failCount === 0) {
    ElMessage.success(`成功锁定 ${successCount} 条记录`)
  } else {
    ElMessage.warning(`部分成功：${successCount} 条已锁定，${failCount} 条失败`)
  }
  selectedRows.value = []
  await fetchData()
}

async function batchUnlockRows() {
  const unlockableRows = selectedRows.value.filter(r => r.id && r.is_row_locked)
  if (!unlockableRows.length) {
    ElMessage.warning('选中的记录中没有已锁定的数据')
    return
  }
  await ElMessageBox.confirm(
    `确定要解锁选中的 ${unlockableRows.length} 条考勤记录吗？解锁后同步或导入时可能会覆盖这些数据。`,
    '批量解锁确认',
    { type: 'warning', confirmButtonText: '确定解锁', cancelButtonText: '取消' }
  )
  let successCount = 0, failCount = 0
  for (const row of unlockableRows) {
    try {
      const formData = new FormData()
      formData.append('locked', 'false')
      await api.post(`/attendance/${row.id}/lock-row`, formData)
      successCount++
    } catch {
      failCount++
    }
  }
  if (failCount === 0) {
    ElMessage.success(`成功解锁 ${successCount} 条记录`)
  } else {
    ElMessage.warning(`部分成功：${successCount} 条已解锁，${failCount} 条失败`)
  }
  selectedRows.value = []
  await fetchData()
}

function showImport() {
  importFile.value = null; fileList.value = []; importResult.value = null; importVisible.value = true
}

function handleFileChange(file) { importFile.value = file.raw; importResult.value = null }

async function doImport() {
  if (!importFile.value) { ElMessage.warning('请先选择 Excel 文件'); return }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    formData.append('period', periodDate.value)
    const res = await api.post('/attendance/import', formData, {
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
  } finally { importing.value = false }
}

// ==================== 年度工作日历 ====================

async function openSalaryCalendar() {
  const currentPeriod = periodDate.value
  const year = parseInt(currentPeriod.substring(0, 4))
  calendarYearPicker.value = new Date(year, 0, 1)
  touchedPeriods.value = new Set()
  await loadYearCalendar()
  calendarVisible.value = true
}

async function loadYearCalendar() {
  calendarLoading.value = true
  try {
    const year = displayCalendarYear.value
    const res = await api.get(`/attendance/work-calendar/${year}`)
    yearCalendarDays.value = res.data.days
    yearSummary.value = res.data.summary
  } catch (e) {
    ElMessage.error('加载工作日历失败：' + (e.response?.data?.detail || e.message))
  } finally {
    calendarLoading.value = false
  }
}

function getNextDayState(day) {
  const weekday = day.weekday
  const isWeekend = weekday >= 5
  let nextType, nextSalary, nextRemark
  if (day.day_type === 'workday') {
    nextType = 'holiday'; nextSalary = false; nextRemark = '节假日'
  } else if (day.day_type === 'holiday') {
    nextType = 'makeup_work'; nextSalary = true; nextRemark = '调休补班'
  } else if (day.day_type === 'makeup_work') {
    nextType = isWeekend ? 'weekend' : 'workday'
    nextSalary = !isWeekend
    nextRemark = null
  } else {
    nextType = 'workday'; nextSalary = true; nextRemark = null
  }
  return { day_type: nextType, is_salary_day: nextSalary, remark: nextRemark }
}

async function toggleDay(day) {
  const idx = yearCalendarDays.value.findIndex(d => d.date === day.date)
  if (idx === -1) return

  const nextState = getNextDayState(day)
  const originalState = { day_type: day.day_type, is_salary_day: day.is_salary_day, remark: day.remark }
  const year = displayCalendarYear.value
  const period = day.date.substring(0, 7).replace('-', '')

  yearCalendarDays.value[idx] = { ...yearCalendarDays.value[idx], ...nextState }
  touchedPeriods.value.add(period)

  try {
    const formData = new URLSearchParams()
    formData.append('date', day.date)
    const res = await api.post(`/attendance/work-calendar/${year}/toggle-day`, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    yearSummary.value = res.data.summary
    const updated = res.data
    if (idx !== -1) {
      yearCalendarDays.value[idx] = { ...yearCalendarDays.value[idx], day_type: updated.day_type, is_salary_day: updated.is_salary_day }
    }
  } catch (e) {
    yearCalendarDays.value[idx] = { ...yearCalendarDays.value[idx], ...originalState }
    touchedPeriods.value.delete(period)
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

async function aiGenerateCalendar() {
  const year = displayCalendarYear.value
  await ElMessageBox.confirm(
    `确定要用 AI 预填 ${year} 年的法定节假日和调休补班安排吗？\n这将覆盖已标记的节假日/补班日期，但不会影响您手动设置的其他日期。`,
    'AI 预填节假日',
    { type: 'info', confirmButtonText: '开始预填', cancelButtonText: '取消' }
  )
  aiGenerating.value = true
  try {
    const res = await api.post(`/attendance/work-calendar/${year}/ai-generate`)
    ElMessage.success(res.data.message)
    yearSummary.value = res.data.summary
    await loadYearCalendar()
    for (let m = 1; m <= 12; m++) {
      touchedPeriods.value.add(`${year}${String(m).padStart(2, '0')}`)
    }
  } catch (e) {
    ElMessage.error('AI预填失败：' + (e.response?.data?.detail || e.message))
  } finally {
    aiGenerating.value = false
  }
}

async function recalculateAttendance() {
  const periods = Array.from(touchedPeriods.value)
  if (periods.length === 0) {
    ElMessage.info('请先点击日历日期进行修改')
    return
  }
  const periodNames = periods.map(p => {
    const y = p.substring(0, 4)
    const m = p.substring(4, 6)
    return `${y}年${parseInt(m)}月`
  }).join('、')
  await ElMessageBox.confirm(
    `确定要立即重算以下月份的考勤数据吗？\n${periodNames}\n提示：关闭日历弹窗时也会自动重算这些月份。重算会更新数据库中的「应计薪天数」「计薪天数」和「出勤率」，用于薪资核算。`,
    '重算考勤',
    { type: 'warning', confirmButtonText: '立即重算', cancelButtonText: '取消' }
  )
  recalculating.value = true
  try {
    const formData = new URLSearchParams()
    formData.append('period', periods.join(','))
    const res = await api.post('/attendance/work-calendar/recalculate', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    ElMessage.success(res.data.message)
    touchedPeriods.value = new Set()
    await fetchData()
  } catch (e) {
    ElMessage.error('重算失败：' + (e.response?.data?.detail || e.message))
  } finally {
    recalculating.value = false
  }
}

async function onCalendarClose() {
  const periods = Array.from(touchedPeriods.value)
  touchedPeriods.value = new Set()
  if (periods.length > 0) {
    try {
      const formData = new URLSearchParams()
      formData.append('period', periods.join(','))
      await api.post('/attendance/work-calendar/recalculate', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
    } catch (e) {
      console.error('自动重算考勤失败:', e)
    }
  }
  await fetchData()
}

// ==================== 缺卡核销 ====================

async function openMissedPunchCheck() {
  writeOffVisible.value = true
  writeOffResult.value = null
  writeOffActiveTab.value = 'matched'
  selectedWriteOffRows.value = []
  checkingWriteOff.value = true
  try {
    const res = await api.get('/attendance/missed-punch-check', { params: { period: periodDate.value } })
    writeOffResult.value = res.data
    // 默认选中所有可核销的
    selectedWriteOffRows.value = [...res.data.matched]
  } catch (e) {
    ElMessage.error('查询缺卡申请失败：' + (e.response?.data?.detail || e.message))
    writeOffVisible.value = false
  } finally {
    checkingWriteOff.value = false
  }
}

function handleWriteOffSelection(selection) {
  selectedWriteOffRows.value = selection
}

async function confirmWriteOff() {
  if (selectedWriteOffRows.value.length === 0) {
    ElMessage.warning('请先选择要核销的员工')
    return
  }
  await ElMessageBox.confirm(
    `确定要核销选中的 ${selectedWriteOffRows.value.length} 名员工的缺卡记录吗？\n核销后半天缺卡和全天缺卡将被清零，并记录核销备注。`,
    '确认核销',
    { type: 'warning', confirmButtonText: '确定核销', cancelButtonText: '取消' }
  )
  writingOff.value = true
  try {
    const formData = new URLSearchParams()
    formData.append('period', periodDate.value)
    formData.append('apply_all', 'false')
    const empIds = selectedWriteOffRows.value.map(r => r.employee_id).join(',')
    formData.append('employee_ids', empIds)
    const res = await api.post('/attendance/missed-punch-write-off', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    ElMessage.success(res.data.message)
    writeOffVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error('核销失败：' + (e.response?.data?.detail || e.message))
  } finally {
    writingOff.value = false
  }
}

async function confirmWriteOffAll() {
  if (!writeOffResult.value || writeOffResult.value.matched.length === 0) return
  const count = writeOffResult.value.matched.length
  await ElMessageBox.confirm(
    `确定要一键核销所有 ${count} 名匹配员工的缺卡记录吗？\n核销后半天缺卡和全天缺卡将被清零，并记录核销备注。`,
    '确认一键核销',
    { type: 'warning', confirmButtonText: '确定核销全部', cancelButtonText: '取消' }
  )
  writingOffAll.value = true
  try {
    const formData = new URLSearchParams()
    formData.append('period', periodDate.value)
    formData.append('apply_all', 'true')
    const res = await api.post('/attendance/missed-punch-write-off', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    ElMessage.success(res.data.message)
    writeOffVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error('核销失败：' + (e.response?.data?.detail || e.message))
  } finally {
    writingOffAll.value = false
  }
}

onMounted(() => { fetchData() })
</script>

<style scoped>
.action-cell { white-space: nowrap; }
.cell-number { width: 100%; }
.cell-number :deep(.el-input__wrapper) { padding: 0 4px; }
.cell-input { width: 100%; }
.cell-input :deep(.el-input__wrapper) { padding: 0 4px; }
:deep(.row-changed) { background-color: #fef3c7 !important; }
:deep(.row-mismatch) { background-color: #fef2f2 !important; }
:deep(.row-mismatch:hover) > td { background-color: #fee2e2 !important; }
:deep(.row-locked) { background-color: #f0f9ff !important; }
:deep(.row-locked:hover) > td { background-color: #e0f2fe !important; }
:deep(.row-locked td) { color: #64748b; }

/* 年度工作日历样式 */
.year-calendar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
  padding: 4px;
}
.month-card {
  background: #fafcff;
  border: 1px solid #e8f0fe;
  border-radius: 8px;
  padding: 10px;
  transition: box-shadow 0.2s;
}
.month-card:hover {
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
}
.month-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #eef2f7;
}
.month-title {
  font-weight: 600;
  font-size: 14px;
  color: #1e40af;
}
.month-stats {
  font-size: 12px;
  color: #64748b;
}
.mini-calendar {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
.mini-weekday {
  text-align: center;
  font-size: 10px;
  color: #94a3b8;
  padding: 2px 0;
  font-weight: 500;
}
.mini-cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
  user-select: none;
}
.mini-cell.blank {
  cursor: default;
  background: transparent;
}
.mini-cell.day-work {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 500;
}
.mini-cell.day-work:hover {
  background: #dbeafe;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.2);
}
.mini-cell.day-weekend {
  background: #f8fafc;
  color: #cbd5e1;
}
.mini-cell.day-weekend:hover {
  background: #f1f5f9;
  color: #94a3b8;
}
.mini-cell.day-holiday {
  background: #fef2f2;
  color: #dc2626;
  font-weight: 600;
  border: 1px solid #fecaca;
}
.mini-cell.day-holiday:hover {
  background: #fee2e2;
}
.mini-cell.day-makeup {
  background: #fff7ed;
  color: #ea580c;
  font-weight: 600;
  border: 1px solid #fed7aa;
}
.mini-cell.day-makeup:hover {
  background: #ffedd5;
}
.mini-cell.day-has-remark::after {
  content: '';
  position: absolute;
  bottom: 1px;
  right: 1px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.6;
}

/* 考勤编辑弹窗样式优化 */
.attendance-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
  max-height: 70vh;
  overflow-y: auto;
}
.attendance-form :deep(.el-form-item) {
  margin-bottom: 14px;
}
.attendance-form :deep(.el-form-item__label) {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}
.attendance-form :deep(.el-input-number) {
  width: 100%;
}
.attendance-form :deep(.el-input-number .el-input__wrapper) {
  padding: 0 8px;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-shadow: none;
}
.attendance-form :deep(.el-input-number .el-input__wrapper:hover) {
  border-color: #60a5fa;
}
.attendance-form :deep(.el-input-number .el-input__wrapper.is-focus) {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}
.attendance-form :deep(.el-input-number .el-input__inner) {
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  height: 36px;
  line-height: 36px;
}
.attendance-form :deep(.el-input-number .el-input-number__decrease),
.attendance-form :deep(.el-input-number .el-input-number__increase) {
  width: 36px;
  height: 36px;
  background: #f3f4f6;
  border-color: #d1d5db;
  color: #374151;
  font-size: 16px;
  font-weight: 600;
}
.attendance-form :deep(.el-input-number .el-input-number__decrease:hover),
.attendance-form :deep(.el-input-number .el-input-number__increase:hover) {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
}
.attendance-form :deep(.el-input .el-input__wrapper) {
  padding: 0 10px;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-shadow: none;
}
.attendance-form :deep(.el-input .el-input__wrapper:hover) {
  border-color: #60a5fa;
}
.attendance-form :deep(.el-input .el-input__wrapper.is-focus) {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}
.attendance-form :deep(.el-input .el-input__inner) {
  font-size: 14px;
  color: #1f2937;
  height: 36px;
  line-height: 36px;
}
.attendance-form :deep(.el-textarea .el-textarea__inner) {
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  color: #1f2937;
  padding: 8px 10px;
}
.attendance-form :deep(.el-divider) {
  margin: 12px 0 16px 0;
}
.attendance-form :deep(.el-divider__text) {
  font-size: 15px;
  font-weight: 600;
  color: #1e40af;
  background: linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%);
  padding: 4px 16px;
  border-radius: 4px;
}
.attendance-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}
.attendance-dialog :deep(.el-dialog__footer .el-button) {
  min-width: 80px;
  height: 38px;
  font-size: 14px;
  border-radius: 6px;
}
</style>
