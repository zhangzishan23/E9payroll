<template>
  <div class="space-y-4">
    <div class="apple-card p-6">
      <div class="flex items-center justify-between mb-4 salary-toolbar">
        <div class="flex items-center gap-2">
          <h3 class="text-base font-semibold text-gray-700 shrink-0">薪资核算</h3>
          <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" class="!w-28 shrink-0" size="small" value-format="YYYYMM" @change="onPeriodChange" />
          <el-select v-model="filterField" placeholder="字段" class="!w-20 shrink-0" size="small">
            <el-option label="工号" value="employee_no" />
            <el-option label="姓名" value="employee_name" />
          </el-select>
          <el-input v-model="filterValue" placeholder="筛选" clearable class="!w-24 shrink-0" size="small" @input="fetchResults" />
        </div>
        <div class="flex items-center gap-1">
          <el-button type="primary" size="small" :loading="checking" @click="checkCompleteness">检查</el-button>
          <el-button type="success" size="small" :loading="calculating" :disabled="!canCalculate" @click="startCalculate">核算</el-button>
          <el-button type="warning" size="small" :disabled="!hasResults" @click="calculateNet">实发</el-button>
          <el-button
            size="small"
            :type="editMode ? 'danger' : 'primary'"
            :disabled="!hasResults"
            @click="toggleEditMode"
          >
            {{ editMode ? '退出' : '编辑' }}
          </el-button>
          <template v-if="editMode">
            <el-button type="success" size="small" :loading="savingEdits" @click="confirmEdits">确认</el-button>
            <el-button size="small" @click="cancelEdits">取消</el-button>
          </template>
          <el-button type="danger" size="small" :disabled="!hasResults || isSubmitting" @click="batchSubmitApproval">审核</el-button>
          <el-button type="info" size="small" :disabled="!hasResults" @click="handleExport">导出</el-button>
          <el-button type="danger" size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">删除</el-button>
          <el-button type="warning" size="small" :disabled="!hasResults" @click="showTaxImport">报税</el-button>
        </div>
      </div>

      <div v-if="summary" class="grid grid-cols-4 gap-4 mb-4">
        <div class="bg-blue-50 rounded-xl p-4 text-center">
          <div class="text-2xl font-bold text-blue-600">{{ summary.total_employees }}</div>
          <div class="text-sm text-gray-500">参与员工数</div>
        </div>
        <div class="bg-green-50 rounded-xl p-4 text-center">
          <div class="text-2xl font-bold text-green-600">{{ summary.success_count }}</div>
          <div class="text-sm text-gray-500">核算成功</div>
        </div>
        <div class="bg-orange-50 rounded-xl p-4 text-center">
          <div class="text-2xl font-bold text-orange-600">{{ (summary.total_gross_salary / 10000).toFixed(2) }}万</div>
          <div class="text-sm text-gray-500">总应发工资</div>
        </div>
        <div class="bg-purple-50 rounded-xl p-4 text-center">
          <div class="text-2xl font-bold text-purple-600">{{ (summary.avg_gross_salary / 10000).toFixed(2) }}万</div>
          <div class="text-sm text-gray-500">人均应发工资</div>
        </div>
      </div>

      <div v-if="completeness" class="mb-4">
        <div class="flex gap-4 text-sm">
          <span class="text-green-600">✅ 完整: {{ completeness.complete_count }}人</span>
          <span class="text-red-600">❌ 缺失: {{ completeness.missing_count }}人</span>
          <span class="text-yellow-600">⚠️ 待补充: {{ completeness.optional_missing_count }}人</span>
        </div>
        <div v-for="src in completeness.sources" :key="src.source_key" class="flex items-center gap-2 mt-2 text-sm">
          <span :class="src.status === '完整' ? 'text-green-600' : src.status === '可选数据' ? 'text-blue-500' : 'text-red-600'">
            {{ src.status === '完整' ? '✅' : src.status === '可选数据' ? 'ℹ️' : '❌' }}
          </span>
          <span class="text-gray-600">{{ src.source_name }}: {{ src.count }}条</span>
          <span v-if="src.missing_employees.length" class="text-red-500">
            缺失: {{ src.missing_employees.join(', ') }}
          </span>
        </div>
      </div>

      <div v-if="formulaVisible" class="bg-gray-50 rounded-xl p-4 mb-4 text-sm">
        <h4 class="font-semibold text-gray-700 mb-2">计算公式说明</h4>
        <div class="grid grid-cols-2 gap-2 text-gray-600">
          <div>月薪标准 = 基本工资 + 绩效奖金标准 + 补贴合计</div>
          <div>（如有月中调薪，基本工资和绩效奖金标准使用折算后值）</div>
          <div>折算后基本工资 = ROUND(调前天数×调前基本工资/总计薪天数 + 调后基本工资×调后天数/总计薪天数, 2)</div>
          <div>实发绩效奖金标准 = 绩效奖金标准 × 实发绩效奖金系数</div>
          <div>实发绩效奖金 = 实发绩效奖金标准 × 出勤率</div>
          <div>总应发工资 = (基本工资 + 补贴合计 + 提成/项目奖金/补发) × 出勤率 + 实发绩效奖金</div>
          <div>补贴合计 = 餐补 + 交通补 + 通讯补 + 电脑补贴 + 住房补</div>
          <div>社保、公积金（个人）合计 = 养老(个人) + 失业(个人) + 医疗(个人) + 公积金(个人)</div>
          <div>实发工资 = 总应发工资 - 社保、公积金合计 - 本月应扣个税额 + 税后调整金额</div>
          <div>本月实际报税金额 = 总应发工资 + 上月未报税 + 临时性差旅补贴未报税费用</div>
          <div>电脑补贴为非固定收入，仅当月有效，不纳入薪酬固定部分</div>
        </div>
      </div>
    </div>

    <div class="apple-card p-6">
      <div class="flex justify-between items-center mb-3">
        <h4 class="text-md font-semibold text-gray-700">
          核算结果明细
          <span v-if="editMode" class="text-orange-500 text-sm font-normal ml-2">🔴 编辑模式已开启 - 仅可编辑导入/手动录入的字段</span>
        </h4>
        <el-button link type="primary" @click="formulaVisible = !formulaVisible">
          {{ formulaVisible ? '收起公式' : '查看计算公式' }}
        </el-button>
      </div>
      <el-table :data="results" border stripe max-height="500" v-loading="loading" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="employee_no" width="90" fixed>
          <template #header>
            <el-tooltip content="员工唯一编号，来源于员工档案" placement="top" :show-after="400">
              <span>员工编号</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="employee_name" width="70" fixed>
          <template #header>
            <el-tooltip content="员工姓名，来源于员工档案" placement="top" :show-after="400">
              <span>姓名</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="department" width="90">
          <template #header>
            <el-tooltip content="员工所属部门，来源于员工档案" placement="top" :show-after="400">
              <span>部门</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="entry_date" width="100">
          <template #header>
            <el-tooltip content="员工入职日期，来源于员工档案" placement="top" :show-after="400">
              <span>入职时间</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.entry_date || '' }}</template>
        </el-table-column>
        <el-table-column prop="contract_company" width="95">
          <template #header>
            <el-tooltip content="员工合同所属公司，来源于员工档案" placement="top" :show-after="400">
              <span>合同公司</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="net_salary" width="100" class-name="col-summary">
          <template #header>
            <el-tooltip content="= 总应发工资 - 社保、公积金合计 - 本月应扣个税额 + 税后调整金额" placement="top" :show-after="400">
              <span>实发工资</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span v-if="row.net_salary != null" class="font-semibold text-green-600">{{ row.net_salary.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_work_days" width="95">
          <template #header>
            <el-tooltip content="当月应出勤天数，来源于考勤管理" placement="top" :show-after="400">
              <span>当月总计薪天数</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.total_work_days != null ? row.total_work_days : '' }}</template>
        </el-table-column>
        <el-table-column prop="actual_work_days" width="95">
          <template #header>
            <el-tooltip content="当月实际出勤天数，来源于考勤管理" placement="top" :show-after="400">
              <span>实际计薪天数</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.actual_work_days != null ? row.actual_work_days : '' }}</template>
        </el-table-column>
        <el-table-column prop="attendance_rate" width="75">
          <template #header>
            <el-tooltip content="= 实际计薪天数 ÷ 总计薪天数，来源于考勤管理" placement="top" :show-after="400">
              <span>出勤率</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.attendance_rate != null ? (row.attendance_rate * 100).toFixed(1) + '%' : '' }}</template>
        </el-table-column>
        <el-table-column prop="base_salary" width="95">
          <template #header>
            <el-tooltip content="员工月基本工资，来源于员工薪资档案" placement="top" :show-after="400">
              <span>基本工资</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.base_salary != null ? row.base_salary : '' }}</template>
        </el-table-column>
        <el-table-column prop="base_salary_prorated" width="100">
          <template #header>
            <el-tooltip content="月中调薪折算后的基本工资，如有调薪则使用折算值，否则等于基本工资" placement="top" :show-after="400">
              <span>折算后基本工资</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span v-if="row.base_salary_prorated != null && row.base_salary_prorated !== row.base_salary" class="font-semibold text-orange-600">{{ row.base_salary_prorated.toFixed(2) }}</span>
            <span v-else>{{ row.base_salary_prorated != null ? row.base_salary_prorated : '' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="commission_bonus" width="95">
          <template #header>
            <el-tooltip content="当月提成/项目奖金/补发，手动录入或Excel导入" placement="top" :show-after="400">
              <span>提成/项目奖金/补发</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].commission_bonus" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id, 'commission_bonus')" />
            </template>
            <template v-else>{{ row.commission_bonus != null ? row.commission_bonus : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="meal_allowance" width="70">
          <template #header>
            <el-tooltip content="每月固定餐费补贴，来源于员工薪资档案" placement="top" :show-after="400">
              <span>餐补</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.meal_allowance != null ? row.meal_allowance : '' }}</template>
        </el-table-column>
        <el-table-column prop="transport_allowance" width="75">
          <template #header>
            <el-tooltip content="每月固定交通补贴，来源于员工薪资档案" placement="top" :show-after="400">
              <span>交通补</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.transport_allowance != null ? row.transport_allowance : '' }}</template>
        </el-table-column>
        <el-table-column prop="communication_allowance" width="75">
          <template #header>
            <el-tooltip content="每月固定通讯补贴，来源于员工薪资档案" placement="top" :show-after="400">
              <span>通讯补</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.communication_allowance != null ? row.communication_allowance : '' }}</template>
        </el-table-column>
        <el-table-column prop="computer_allowance" width="95">
          <template #header>
            <el-tooltip content="电脑补贴（非固定收入），仅当月有效，来源于员工薪资档案" placement="top" :show-after="400">
              <span>电脑补贴（非固定收入）</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.computer_allowance != null ? row.computer_allowance : '' }}</template>
        </el-table-column>
        <el-table-column prop="housing_allowance" width="95">
          <template #header>
            <el-tooltip content="住房补贴（非固定收入），仅当月有效，来源于员工薪资档案" placement="top" :show-after="400">
              <span>住房补（非固定收入）</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.housing_allowance != null ? row.housing_allowance : '' }}</template>
        </el-table-column>
        <el-table-column prop="allowance_total" width="85" class-name="col-summary">
          <template #header>
            <el-tooltip content="= 餐补+交通+通讯+电脑+住房补贴，自动计算" placement="top" :show-after="400">
              <span>补贴合计</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.allowance_total != null ? row.allowance_total : '' }}</template>
        </el-table-column>
        <el-table-column prop="performance_standard" width="95">
          <template #header>
            <el-tooltip content="绩效奖金计算基数，来源于员工薪资档案" placement="top" :show-after="400">
              <span>绩效奖金标准</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.performance_standard != null ? row.performance_standard : '' }}</template>
        </el-table-column>
        <el-table-column prop="performance_coefficient" width="95">
          <template #header>
            <el-tooltip content="当月绩效评分系数，来源于绩效管理模块" placement="top" :show-after="400">
              <span>实发绩效奖金系数</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.performance_coefficient != null ? row.performance_coefficient : '' }}</template>
        </el-table-column>
        <el-table-column prop="actual_performance" width="95">
          <template #header>
            <el-tooltip content="= 绩效奖金标准 × 实发绩效奖金系数" placement="top" :show-after="400">
              <span>实发绩效奖金标准</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.actual_performance != null ? row.actual_performance : '' }}</template>
        </el-table-column>
        <el-table-column prop="effective_performance" width="95">
          <template #header>
            <el-tooltip content="= 实发绩效奖金标准 × 出勤率" placement="top" :show-after="400">
              <span>实发绩效奖金</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.effective_performance != null ? row.effective_performance : '' }}</template>
        </el-table-column>
        <el-table-column prop="monthly_standard" width="90" class-name="col-summary">
          <template #header>
            <el-tooltip content="= 基本工资 + 绩效奖金标准 + 补贴合计，自动计算" placement="top" :show-after="400">
              <span>月薪标准</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.monthly_standard != null ? row.monthly_standard : '' }}</template>
        </el-table-column>
        <el-table-column prop="gross_salary" width="100" class-name="col-summary">
          <template #header>
            <el-tooltip content="= (基本工资 + 补贴合计 + 提成/项目奖金/补发) × 出勤率 + 实发绩效奖金" placement="top" :show-after="400">
              <span>总应发工资</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span v-if="row.gross_salary != null" class="font-semibold text-blue-600">{{ row.gross_salary.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="pension_personal" width="95">
          <template #header>
            <el-tooltip content="养老保险个人缴纳金额，来源于社保公积金表" placement="top" :show-after="400">
              <span>养老保险（个人）</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.pension_personal != null ? row.pension_personal : '' }}</template>
        </el-table-column>
        <el-table-column prop="unemployment_personal" width="95">
          <template #header>
            <el-tooltip content="失业保险个人缴纳金额，来源于社保公积金表" placement="top" :show-after="400">
              <span>失业保险（个人）</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.unemployment_personal != null ? row.unemployment_personal : '' }}</template>
        </el-table-column>
        <el-table-column prop="medical_personal" width="95">
          <template #header>
            <el-tooltip content="医疗保险个人缴纳金额，来源于社保公积金表" placement="top" :show-after="400">
              <span>医疗保险（个人）</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.medical_personal != null ? row.medical_personal : '' }}</template>
        </el-table-column>
        <el-table-column prop="housing_fund_personal" width="90">
          <template #header>
            <el-tooltip content="当月公积金个人缴纳金额，来源于社保公积金表" placement="top" :show-after="400">
              <span>公积金（个人）</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.housing_fund_personal != null ? row.housing_fund_personal : '' }}</template>
        </el-table-column>
        <el-table-column prop="si_hf_total" width="100" class-name="col-summary">
          <template #header>
            <el-tooltip content="= 养老保险 + 失业保险 + 医疗保险 + 公积金（均为个人部分）" placement="top" :show-after="400">
              <span>社保、公积金（个人）合计</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.si_hf_total != null ? row.si_hf_total : '' }}</template>
        </el-table-column>
        <el-table-column prop="tax_deduction" width="100">
          <template #header>
            <el-tooltip content="税务局申报后计算的应缴个税额，从本月工资代扣" placement="top" :show-after="400">
              <span>本月应扣个税额</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].tax_deduction" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id, 'tax_deduction')" />
            </template>
            <template v-else>{{ row.tax_deduction != null ? row.tax_deduction : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="posttax_adjustment" width="90">
          <template #header>
            <el-tooltip content="税后特殊调整（调休扣款等），不影响个税，只影响实发工资" placement="top" :show-after="400">
              <span>税后调整金额</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].posttax_adjustment" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id, 'posttax_adjustment')" />
            </template>
            <template v-else>{{ row.posttax_adjustment != null ? row.posttax_adjustment : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="posttax_adjustment_reason" width="120">
          <template #header>
            <el-tooltip content="税后调整的原因说明（如：临时性差旅补贴未报税费用），不填则报税金额应等于总应发工资" placement="top" :show-after="400">
              <span>税后调整原因</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input v-model="editCache[row.id].posttax_adjustment_reason" size="small" class="cell-text" @change="markChanged(row.id, 'posttax_adjustment_reason')" />
            </template>
            <template v-else>{{ row.posttax_adjustment_reason || '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="travel_untaxed" width="100">
          <template #header>
            <el-tooltip content="临时性差旅补贴未报税费用，来源于差旅报销表" placement="top" :show-after="400">
              <span>临时性差旅补贴未报税费用</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].travel_untaxed" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id, 'travel_untaxed')" />
            </template>
            <template v-else>{{ row.travel_untaxed != null ? row.travel_untaxed : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="actual_taxable" width="100" class-name="col-summary">
          <template #header>
            <el-tooltip content="= 总应发工资 + 上月未报税 + 临时性差旅补贴未报税" placement="top" :show-after="400">
              <span>本月实际报税金额</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">{{ row.actual_taxable != null ? row.actual_taxable : '' }}</template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="editConfirmVisible" title="确认修改内容" width="700px" append-to-body>
      <div class="text-sm text-gray-600 mb-3">以下 {{ changedRows.length }} 条记录发生了修改，确认后将重新计算应发/实发工资：</div>
      <el-table :data="changedRows" border stripe max-height="400" size="small">
        <el-table-column prop="employee_name" label="员工" width="80" />
        <el-table-column prop="employee_no" label="编号" width="80" />
        <el-table-column label="修改字段" min-width="200">
          <template #default="{ row }">
            <div v-for="(chg, idx) in row.changes" :key="idx" class="text-sm">
              <span class="text-gray-500">{{ chg.label }}：</span>
              <span class="text-red-400 line-through mr-1">{{ chg.old }}</span>
              <span class="text-green-600 font-semibold">{{ chg.new }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="editConfirmVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdits" @click="saveAllEdits">确认保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="taxImportVisible" title="报税数据导入" width="700px" append-to-body>
      <div class="mb-4 text-sm text-gray-500">
        请粘贴财务提供的报税数据（格式：员工编号,上月未报税,差旅未报税,补偿金报税,专项附加扣除），每行一条
      </div>
      <el-input v-model="taxData" type="textarea" :rows="10" placeholder="E001,0,0,0,5000&#10;E002,0,0,0,3000" />
      <template #footer>
        <el-button @click="taxImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="taxImporting" @click="doTaxImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Delete } from '@element-plus/icons-vue'
import api from '../../api'

const periodDate = ref('202604')
const filterField = ref('')
const filterValue = ref('')
const checking = ref(false)
const calculating = ref(false)
const savingEdits = ref(false)
const loading = ref(false)
const isSubmitting = ref(false)
const completeness = ref(null)
const summary = ref(null)
const results = ref([])
const selectedRows = ref([])
const formulaVisible = ref(false)

const editMode = ref(false)
const editCache = reactive({})
const changedSet = reactive({})
const editConfirmVisible = ref(false)
const changedRows = ref([])

const editableFields = [
  'commission_bonus', 'posttax_adjustment',
  'posttax_adjustment_reason',
  'last_month_untaxed', 'travel_untaxed', 'compensation_tax',
  'special_deduction', 'tax_deduction'
]

const fieldLabels = {
  commission_bonus: '提成/项目奖金/补发',
  posttax_adjustment: '税后调整金额', posttax_adjustment_reason: '税后调整原因',
  tax_deduction: '本月应扣个税额',
  special_deduction: '专项附加扣除', last_month_untaxed: '上月未报税',
  travel_untaxed: '临时性差旅补贴未报税费用', compensation_tax: '补偿金报税'
}

const canCalculate = computed(() => completeness.value && completeness.value.missing_count === 0)
const hasResults = computed(() => results.value.some(r => r.id != null))

function tableRowClassName({ row }) {
  if (editMode.value && row.id && changedSet[row.id]) return 'row-changed'
  return ''
}

function initEditCache() {
  Object.keys(changedSet).forEach(k => delete changedSet[k])
  results.value.forEach(row => {
    if (!row || !row.id) return
    editCache[row.id] = reactive({
      commission_bonus: row.commission_bonus ?? 0,
      posttax_adjustment: row.posttax_adjustment ?? 0,
      posttax_adjustment_reason: row.posttax_adjustment_reason ?? '',
      last_month_untaxed: row.last_month_untaxed ?? 0,
      travel_untaxed: row.travel_untaxed ?? 0,
      compensation_tax: row.compensation_tax ?? 0,
      special_deduction: row.special_deduction ?? 0,
      tax_deduction: row.tax_deduction ?? 0
    })
  })
}

function markChanged(rowId, field) {
  const row = results.value.find(r => r.id === rowId)
  if (!row) return
  const oldVal = row[field] ?? 0
  const newVal = editCache[rowId]?.[field] ?? 0
  const changed = typeof oldVal === 'number' && typeof newVal === 'number'
    ? Math.abs(oldVal - newVal) >= 0.001
    : String(oldVal) !== String(newVal)
  if (!changed) {
    if (changedSet[rowId]) {
      delete changedSet[rowId][field]
      if (Object.keys(changedSet[rowId]).length === 0) delete changedSet[rowId]
    }
  } else {
    if (!changedSet[rowId]) changedSet[rowId] = {}
    changedSet[rowId][field] = true
  }
}

function toggleEditMode() {
  try {
    if (editMode.value) {
      editMode.value = false
      for (const key of Object.keys(editCache)) {
        delete editCache[key]
      }
      for (const key of Object.keys(changedSet)) {
        delete changedSet[key]
      }
      return
    }
    initEditCache()
    editMode.value = true
  } catch (e) {
    console.error('切换编辑模式失败：', e)
    ElMessage.error('切换编辑模式失败，请刷新页面后重试')
  }
}

function cancelEdits() {
  editMode.value = false
  for (const key of Object.keys(editCache)) {
    delete editCache[key]
  }
  for (const key of Object.keys(changedSet)) {
    delete changedSet[key]
  }
}

async function confirmEdits() {
  const changedIds = Object.keys(changedSet).map(Number)
  if (!changedIds.length) {
    ElMessage.warning('没有检测到任何修改')
    return
  }

  const rows = []
  changedIds.forEach(id => {
    const row = results.value.find(r => r.id === id)
    if (!row) return
    const changes = []
    Object.keys(changedSet[id]).forEach(field => {
      const oldVal = row[field] ?? 0
      const newVal = editCache[id]?.[field] ?? 0
      changes.push({
        field,
        label: fieldLabels[field] || field,
        old: typeof oldVal === 'number' ? oldVal.toFixed(2) : String(oldVal),
        new: typeof newVal === 'number' ? newVal.toFixed(2) : String(newVal)
      })
    })
    if (changes.length) {
      rows.push({
        id,
        employee_name: row.employee_name,
        employee_no: row.employee_no,
        changes
      })
    }
  })

  changedRows.value = rows
  editConfirmVisible.value = true
}

async function saveAllEdits() {
  savingEdits.value = true
  const changedIds = Object.keys(changedSet).map(Number)
  let successCount = 0
  let failCount = 0

  try {
    for (const id of changedIds) {
      const cache = editCache[id]
      if (!cache) continue
      const payload = {}
      Object.keys(changedSet[id] || {}).forEach(field => {
        payload[field] = cache[field]
      })
      try {
        await api.put(`/salary/results/${id}`, payload)
        successCount++
      } catch {
        failCount++
      }
    }

    if (failCount === 0) {
      ElMessage.success(`修改成功！共更新 ${successCount} 条记录，应发/实发工资已重新计算`)
    } else {
      ElMessage.warning(`部分成功：${successCount} 条已更新，${failCount} 条失败`)
    }

    editConfirmVisible.value = false
    editMode.value = false
    for (const key of Object.keys(editCache)) {
      delete editCache[key]
    }
    for (const key of Object.keys(changedSet)) {
      delete changedSet[key]
    }
    await fetchResults()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    savingEdits.value = false
  }
}

function onPeriodChange(val) {
  periodDate.value = val
  fetchResults()
}

async function checkCompleteness() {
  checking.value = true
  try {
    const res = await api.get(`/salary/check-completeness/${periodDate.value}`)
    completeness.value = res.data
  } finally {
    checking.value = false
  }
}

async function startCalculate() {
  await ElMessageBox.confirm(`确认开始核算 ${periodDate.value} 月份薪资？`, '确认核算', {
    type: 'info', confirmButtonText: '确认核算', cancelButtonText: '取消'
  })
  calculating.value = true
  try {
    const res = await api.post(`/salary/calculate/${periodDate.value}`)
    summary.value = res.data
    ElMessage.success('核算完成')
    await fetchResults()
  } catch (e) {
    if (e.response?.status === 400) {
      ElMessage.warning('该周期已有核算记录，正在加载已有结果')
      await fetchResults()
    }
  } finally {
    calculating.value = false
  }
}

async function fetchResults() {
  loading.value = true
  try {
    const res = await api.get(`/salary/results/${periodDate.value}`)
    let data = res.data
    if (filterField.value && filterValue.value) {
      const fv = filterValue.value.toLowerCase()
      data = data.filter(r => {
        if (filterField.value === 'employee_no') return (r.employee_no || '').toLowerCase().includes(fv)
        if (filterField.value === 'employee_name') return (r.employee_name || '').toLowerCase().includes(fv)
        return true
      })
    }
    results.value = data
  } catch (e) {
    results.value = []
  } finally {
    loading.value = false
  }
}

function handleSelectionChange(selection) {
  selectedRows.value = selection
}

async function calculateNet() {
  await ElMessageBox.confirm('确认计算实发工资？将根据个税数据更新实发金额。', '确认操作', {
    type: 'info', confirmButtonText: '确认', cancelButtonText: '取消'
  })
  try {
    const res = await api.post(`/salary/calculate-net/${periodDate.value}`)
    summary.value = res.data
    ElMessage.success('实发工资计算完成')
    await fetchResults()
  } catch (e) {
    ElMessage.error('计算失败：' + (e.response?.data?.detail || e.message))
  }
}

async function submitReview(row) {
  await ElMessageBox.confirm(
    `确认将「${row.employee_name}」的核算结果提交审核？`,
    '提交审核',
    { type: 'info', confirmButtonText: '确认提交', cancelButtonText: '取消' }
  )
  try {
    await api.put(`/salary/results/${row.id}`, { review_status: '审核中' })
    ElMessage.success('已提交审核')
    await fetchResults()
  } catch (e) {
    ElMessage.error('提交失败')
  }
}

async function batchSubmitApproval() {
  const pendingCount = results.value.filter(r => r.review_status === '待审核' || !r.review_status).length
  if (pendingCount === 0) {
    ElMessage.warning('没有待审核的记录')
    return
  }

  await ElMessageBox.confirm(
    `确认将 ${periodDate.value} 月份共 ${pendingCount} 条核算记录批量提交审核？\n提交后将生成审批流水，核算数据将不可修改。`,
    '批量提交审核',
    { type: 'warning', confirmButtonText: '确认提交', cancelButtonText: '取消' }
  )

  isSubmitting.value = true
  try {
    const res = await api.post('/approval/submit', { period: periodDate.value })
    ElMessage.success(`提交成功！审批流水号：${res.data.approval_no}`)
    await fetchResults()
  } catch (e) {
    ElMessage.error('提交失败：' + (e.response?.data?.detail || e.message))
  } finally {
    isSubmitting.value = false
  }
}

async function handleExport() {
  try {
    const res = await api.get(`/salary/export/${periodDate.value}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `薪酬核算_${periodDate.value}_${new Date().toISOString().slice(0, 10)}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要删除的核算记录')
    return
  }
  await ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 条核算记录吗？此操作不可恢复。`,
    '批量删除确认',
    { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
  )
  try {
    const ids = selectedRows.value.filter(r => r.id).map(r => r.id)
    if (!ids.length) {
      ElMessage.warning('选中的记录中没有可删除的数据')
      return
    }
    await api.post('/salary/batch-delete', ids)
    ElMessage.success(`成功删除 ${ids.length} 条核算记录`)
    selectedRows.value = []
    await fetchResults()
  } catch (e) {
    ElMessage.error('批量删除失败：' + (e.response?.data?.detail || '请稍后重试'))
  }
}

onMounted(() => {
  fetchResults()
})

const taxImportVisible = ref(false)
const taxImporting = ref(false)
const taxData = ref('')

function showTaxImport() {
  taxData.value = ''
  taxImportVisible.value = true
}

async function doTaxImport() {
  if (!taxData.value.trim()) {
    ElMessage.warning('请输入报税数据')
    return
  }
  const lines = taxData.value.trim().split('\n').filter(l => l.trim())
  const items = []
  for (const line of lines) {
    const parts = line.split(',').map(s => s.trim())
    if (parts.length < 2) continue
    items.push({
      employee_no: parts[0],
      last_month_untaxed: parseFloat(parts[1]) || 0,
      travel_untaxed: parseFloat(parts[2]) || 0,
      compensation_tax: parseFloat(parts[3]) || 0,
      special_deduction: parseFloat(parts[4]) || 0
    })
  }
  if (!items.length) {
    ElMessage.warning('未能解析到有效数据')
    return
  }
  taxImporting.value = true
  try {
    const res = await api.post(`/salary/import-tax/${periodDate.value}`, items)
    ElMessage.success(res.data.message)
    taxImportVisible.value = false
    await fetchResults()
  } catch (e) {
    ElMessage.error('导入失败')
  } finally {
    taxImporting.value = false
  }
}
</script>

<style scoped>
.salary-toolbar {
  width: 100%;
}
.salary-toolbar :deep(.el-button) {
  flex-shrink: 0;
  padding-left: 12px;
  padding-right: 12px;
}
.salary-toolbar :deep(.el-button span) {
  white-space: nowrap;
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
.cell-text {
  width: 100%;
}
.cell-text :deep(.el-input__wrapper) {
  padding: 0 4px;
}
:deep(.row-changed) {
  background-color: #fef3c7 !important;
}
:deep(.col-summary) {
  background-color: #fef9c3 !important;
}
</style>