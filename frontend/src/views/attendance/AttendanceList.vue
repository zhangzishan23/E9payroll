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
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">录入</el-button>
      <el-button :icon="Upload" size="small" @click="showImport">导入</el-button>
      <el-button type="success" :icon="Download" size="small" @click="handleExport">导出</el-button>
      <el-button type="warning" size="small" :loading="syncingAttendance" @click="syncAttendance">
        <el-icon class="mr-1"><Refresh /></el-icon>同步钉钉
      </el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
        删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
      </el-button>
      <el-divider direction="vertical" />
      <el-button size="small" type="info" @click="openSalaryCalendar">计薪日历</el-button>
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

    <el-table :data="records" border stripe v-loading="loading" max-height="600" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
      <el-table-column type="selection" width="45" />
      <el-table-column type="index" label="序号" width="50" />
      <el-table-column prop="employee_name" label="员工姓名" width="80" fixed show-overflow-tooltip />
      <el-table-column prop="contract_company" label="合同主体" width="120" show-overflow-tooltip />
      <el-table-column prop="department" label="部门" width="100" show-overflow-tooltip />
      <el-table-column prop="salary_start_date" label="计薪开始日期" width="110">
        <template #default="{ row }">{{ formatDate(row.salary_start_date) }}</template>
      </el-table-column>
      <el-table-column prop="salary_end_date" label="计薪截至日期" width="110">
        <template #default="{ row }">{{ formatDate(row.salary_end_date) }}</template>
      </el-table-column>
      <el-table-column prop="total_work_days" label="当月总计薪天数" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].total_work_days" :min="0" :max="31" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.total_work_days) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="adjusted_salary_days" label="应计薪天数" width="95">
        <template #default="{ row }">{{ formatNum(row.adjusted_salary_days) }}</template>
      </el-table-column>
      <el-table-column prop="actual_salary_days" label="计薪天数" width="85">
        <template #default="{ row }">{{ formatNum(row.actual_salary_days) }}</template>
      </el-table-column>
      <el-table-column prop="attendance_rate" label="出勤率" width="80">
        <template #default="{ row }">{{ row.attendance_rate != null ? (row.attendance_rate * 100).toFixed(1) + '%' : '' }}</template>
      </el-table-column>
      <el-table-column prop="half_day_missed_punch" label="半天缺卡（次数）" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].half_day_missed_punch" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatInt(row.half_day_missed_punch, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="absenteeism_days" label="全天缺卡（天数）" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].absenteeism_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.absenteeism_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="late_count" label="迟到次数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].late_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatInt(row.late_count, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="late_duration" label="迟到时长（分钟）" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].late_duration" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatInt(row.late_duration, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="severe_late_count" label="严重迟到次数" width="100">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].severe_late_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatInt(row.severe_late_count, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="severe_late_duration" label="严重迟到时长（分钟）" width="130">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].severe_late_duration" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatInt(row.severe_late_duration, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="early_count" label="早退次数" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].early_count" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatInt(row.early_count, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="early_duration" label="早退时长（分钟）" width="115">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].early_duration" :min="0" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatInt(row.early_duration, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="total_overtime" label="加班（小时）" width="90">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].total_overtime" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.total_overtime, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="late_to_personal_leave_days" label="迟到转事假" width="95">
        <template #default="{ row }">{{ formatNum(row.late_to_personal_leave_days, true) }}</template>
      </el-table-column>
      <el-table-column prop="personal_leave_days" label="事假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].personal_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.personal_leave_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="full_pay_sick_days" label="全薪病假" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].full_pay_sick_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.full_pay_sick_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="reduced_pay_sick_days" label="减薪病假" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].reduced_pay_sick_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.reduced_pay_sick_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="statutory_sick_days" label="法定病假" width="80">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].statutory_sick_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.statutory_sick_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="compensatory_leave_days" label="调休" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].compensatory_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.compensatory_leave_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="annual_leave_days" label="年假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].annual_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.annual_leave_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="prenatal_checkup_days" label="产检假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].prenatal_checkup_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.prenatal_checkup_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="maternity_leave_days" label="产假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].maternity_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.maternity_leave_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="paternity_leave_days" label="陪产假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].paternity_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.paternity_leave_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="marriage_leave_days" label="婚假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].marriage_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.marriage_leave_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="funeral_leave_days" label="丧假" width="70">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].funeral_leave_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.funeral_leave_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="engineering_compensatory_days" label="调休-工程交付（天）" width="140">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].engineering_compensatory_days" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ formatNum(row.engineering_compensatory_days, true) }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="leave_total_days" label="合计" width="70">
        <template #default="{ row }">{{ formatNum(row.leave_total_days, true) }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="130" show-overflow-tooltip>
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input v-model="editCache[row.id].remark" size="small" class="cell-input" @input="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.remark || '' }}</template>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button v-if="row.id && !editMode" type="primary" link size="small" @click="showDialog(row)">编辑</el-button>
            <el-button v-else-if="!row.id && !editMode" type="success" link size="small" @click="showDialogForEmployee(row)">录入</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 录入/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑考勤' : '录入考勤'" width="650px" append-to-body>
      <el-form ref="formRef" :model="form" label-width="120px">
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

    <!-- 计薪日历弹窗 -->
    <el-dialog v-model="calendarVisible" title="计薪日历" width="800px" append-to-body>
      <div class="mb-3">
        <el-date-picker v-model="calendarPeriod" type="month" placeholder="选择月份" value-format="YYYYMM" @change="loadSalaryCalendar" />
        <span class="ml-4 text-gray-500">总计薪天数：<b class="text-blue-600">{{ calendarTotalDays }}</b> | 已覆盖：<b class="text-orange-500">{{ calendarOverrideCount }}</b></span>
        <span class="ml-2 text-xs text-gray-400">蓝=计薪日 | 灰=休息日 | 橙=调休补班 | 红叉=已排除 | 点击切换</span>
      </div>
      <div class="calendar-grid">
        <div class="calendar-header">一</div>
        <div class="calendar-header">二</div>
        <div class="calendar-header">三</div>
        <div class="calendar-header">四</div>
        <div class="calendar-header">五</div>
        <div class="calendar-header">六</div>
        <div class="calendar-header">日</div>
        <template v-for="(blank, i) in calendarBlanks" :key="'b' + i">
          <div class="calendar-cell blank"></div>
        </template>
        <div
          v-for="d in calendarDays"
          :key="d.date"
          class="calendar-cell"
          :class="{
            'workday': d.is_salary_day && !d.is_overridden && d.is_workday,
            'weekend': !d.is_salary_day && !d.is_workday,
            'excluded': !d.is_salary_day && d.is_workday,
            'makeup': d.is_salary_day && !d.is_workday,
          }"
          @click="toggleSalaryDay(d)"
        >
          <span class="day-num">{{ d.day }}</span>
          <span v-if="!d.is_salary_day && d.is_workday" class="excluded-mark">✕</span>
          <span v-if="d.is_salary_day && !d.is_workday" class="makeup-mark">班</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="calendarVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Delete, Refresh } from '@element-plus/icons-vue'
import api from '../../api'

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

// 计薪日历相关
const calendarVisible = ref(false)
const calendarPeriod = ref(defaultPeriod)
const calendarDays = ref([])
const calendarBlanks = ref(0)
const calendarTotalDays = ref(0)
const calendarOverrideCount = ref(0)

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

function formatNum(val, hideZero = false) {
  if (val == null || val === '') return ''
  const n = Number(val)
  if (isNaN(n)) return ''
  if (hideZero && n === 0) return ''
  return n.toFixed(2)
}

function formatInt(val, hideZero = false) {
  if (val == null || val === '') return ''
  const n = Number(val)
  if (isNaN(n)) return ''
  if (hideZero && n === 0) return ''
  return String(n)
}

function onPeriodChange() { fetchData() }

function tableRowClassName({ row }) {
  if (editMode.value && row.id && changedSet.value.has(row.id)) return 'row-changed'
  return ''
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

// ==================== 计薪日历 ====================

async function openSalaryCalendar() {
  calendarPeriod.value = periodDate.value
  await loadSalaryCalendar()
  calendarVisible.value = true
}

async function loadSalaryCalendar() {
  try {
    const res = await api.get('/attendance/salary-calendar', { params: { period: calendarPeriod.value } })
    const data = res.data
    calendarDays.value = data.days
    calendarTotalDays.value = data.total_salary_days
    calendarOverrideCount.value = data.override_count

    // 计算第一个日期是周几，填充空白格
    if (data.days.length > 0) {
      calendarBlanks.value = data.days[0].weekday
    }
  } catch (e) {
    ElMessage.error('加载计薪日历失败：' + (e.response?.data?.detail || e.message))
  }
}

async function toggleSalaryDay(day) {
  // 判断当前状态并决定操作
  let action
  if (day.is_salary_day && day.is_workday) {
    // 状态1: 工作日计薪 → 点击排除
    action = 'exclude'
  } else if (!day.is_salary_day && day.is_workday) {
    // 状态3: 工作日已排除 → 点击恢复
    action = 'restore'
  } else if (day.is_salary_day && !day.is_workday) {
    // 状态2: 周末已纳入(调休补班) → 点击恢复
    action = 'restore'
  } else {
    // 状态4: 周末休息 → 点击纳入为计薪日
    action = 'include'
  }

  try {
    const formData = new URLSearchParams()
    formData.append('period', calendarPeriod.value)
    formData.append('date', day.date)
    formData.append('action', action)
    if (action === 'exclude') formData.append('reason', '用户手动排除')
    if (action === 'include') formData.append('reason', '调休补班')

    await api.post('/attendance/salary-calendar/toggle', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    await loadSalaryCalendar()
    await fetchData()
    const msgs = { exclude: `已排除 ${day.date}`, include: `已将 ${day.date} 纳入计薪日`, restore: `已恢复 ${day.date} 为默认状态` }
    ElMessage.success(msgs[action])
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
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

/* 计薪日历样式 */
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.calendar-header {
  text-align: center;
  font-weight: 600;
  font-size: 13px;
  color: #606266;
  padding: 6px 0;
  background: #f5f7fa;
  border-radius: 4px;
}
.calendar-cell {
  text-align: center;
  padding: 10px 4px;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  min-height: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  border: 1px solid transparent;
}
.calendar-cell.blank { cursor: default; background: transparent; }
.calendar-cell.workday {
  background: #e8f4fd;
  border-color: #91caff;
  color: #1677ff;
  font-weight: 500;
}
.calendar-cell.workday:hover {
  background: #bae0ff;
  border-color: #4096ff;
}
.calendar-cell.weekend {
  background: #f5f5f5;
  color: #bbb;
}
.calendar-cell.weekend:hover {
  background: #e8e8e8;
  color: #999;
}
.calendar-cell.excluded {
  background: #fff1f0;
  border-color: #ffccc7;
  color: #ff4d4f;
}
.calendar-cell.excluded:hover {
  background: #ffe0e0;
}
.calendar-cell.makeup {
  background: #fff7e6;
  border-color: #ffd591;
  color: #fa8c16;
  font-weight: 500;
}
.calendar-cell.makeup:hover {
  background: #ffe7ba;
  border-color: #ffa940;
}
.day-num { font-size: 15px; }
.excluded-mark {
  font-size: 11px;
  color: #ff4d4f;
  position: absolute;
  top: 2px;
  right: 4px;
}
.makeup-mark {
  font-size: 10px;
  color: #fa8c16;
  position: absolute;
  top: 2px;
  right: 4px;
  font-weight: 600;
}
</style>
