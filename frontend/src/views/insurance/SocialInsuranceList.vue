<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-2 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">社保公积金管理</h3>
      <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" @change="onPeriodChange" />
      <el-select v-model="filterField" placeholder="筛选字段" size="small" class="!w-24">
        <el-option label="员工编号" value="employee_no" />
        <el-option label="员工姓名" value="employee_name" />
      </el-select>
      <el-input v-model="filterValue" placeholder="筛选值" size="small" clearable class="!w-36" @input="fetchData" />
      <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">录入</el-button>
      <el-button :icon="Upload" size="small" @click="showImportOld">单文件导入</el-button>
      <el-button type="primary" :icon="Upload" size="small" @click="showSmartImport">智能导入</el-button>
      <el-button type="success" :icon="Download" size="small" @click="handleExport">导出</el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!validSelectedCount" @click="handleBatchDelete">
        删除{{ validSelectedCount ? `(${validSelectedCount})` : '' }}
      </el-button>
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

    <div class="bg-blue-50 rounded-lg p-3 mb-4 text-sm text-gray-600 flex items-center gap-2">
      <el-icon><InfoFilled /></el-icon>
      <span>提示：不同城市的社保公积金基数、比例不同（北京/广州/邯郸/上海），请按各公司实际情况填写。</span>
    </div>

    <el-table :data="filteredRecords" border stripe v-loading="loading" max-height="700" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
      <el-table-column type="selection" width="55" :selectable="row => row.id != null" />
      <el-table-column prop="employee_no" label="员工编号" width="100" fixed />
      <el-table-column prop="employee_name" label="员工姓名" width="80" fixed />
      <el-table-column prop="employee_social_insurance_no" label="个人社保号" width="130" />

      <!-- 养老保险 -->
      <el-table-column label="养老保险" min-width="450">
        <el-table-column prop="pension_personal_base" label="基数(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].pension_personal_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.pension_personal_base != null ? row.pension_personal_base : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_personal" label="金额(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].pension_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.pension_personal != null ? row.pension_personal : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_personal_rate" label="比例(个人)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].pension_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.pension_personal_rate != null ? (row.pension_personal_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_company_base" label="基数(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].pension_company_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.pension_company_base != null ? row.pension_company_base : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].pension_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.pension_company != null ? row.pension_company : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].pension_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.pension_company_rate != null ? (row.pension_company_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 失业保险 -->
      <el-table-column label="失业保险" min-width="450">
        <el-table-column prop="unemployment_personal_base" label="基数(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].unemployment_personal_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.unemployment_personal_base != null ? row.unemployment_personal_base : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_personal" label="金额(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].unemployment_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.unemployment_personal != null ? row.unemployment_personal : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_personal_rate" label="比例(个人)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].unemployment_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.unemployment_personal_rate != null ? (row.unemployment_personal_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_company_base" label="基数(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].unemployment_company_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.unemployment_company_base != null ? row.unemployment_company_base : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].unemployment_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.unemployment_company != null ? row.unemployment_company : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].unemployment_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.unemployment_company_rate != null ? (row.unemployment_company_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 医疗保险 -->
      <el-table-column label="医疗保险" min-width="450">
        <el-table-column prop="medical_personal_base" label="基数(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].medical_personal_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.medical_personal_base != null ? row.medical_personal_base : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_personal" label="金额(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].medical_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.medical_personal != null ? row.medical_personal : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_personal_rate" label="比例(个人)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].medical_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.medical_personal_rate != null ? (row.medical_personal_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_company_base" label="基数(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].medical_company_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.medical_company_base != null ? row.medical_company_base : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].medical_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.medical_company != null ? row.medical_company : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].medical_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.medical_company_rate != null ? (row.medical_company_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 工伤保险 -->
      <el-table-column label="工伤保险" min-width="300">
        <el-table-column prop="injury_company_base" label="基数(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].injury_company_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.injury_company_base != null ? row.injury_company_base : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="injury_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].injury_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.injury_company != null ? row.injury_company : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="injury_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].injury_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.injury_company_rate != null ? (row.injury_company_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 社保合计 -->
      <el-table-column label="社保合计" min-width="350">
        <el-table-column prop="pension_total" label="养老合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].pension_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.pension_total != null ? row.pension_total : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_total" label="失业合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].unemployment_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.unemployment_total != null ? row.unemployment_total : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_total" label="医疗合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].medical_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.medical_total != null ? row.medical_total : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="injury_total" label="工伤合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].injury_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.injury_total != null ? row.injury_total : '' }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <el-table-column prop="si_personal" label="社保个人合计" width="110">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].si_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.si_personal != null ? row.si_personal : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="si_company" label="社保公司合计" width="110">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].si_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.si_company != null ? row.si_company : '' }}</template>
        </template>
      </el-table-column>
      <el-table-column prop="si_grand_total" label="社保总合计" width="110">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].si_grand_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.si_grand_total != null ? row.si_grand_total : '' }}</template>
        </template>
      </el-table-column>

      <!-- 公积金 -->
      <el-table-column label="公积金" min-width="450">
        <el-table-column prop="hf_base" label="缴存基数" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].hf_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.hf_base != null ? row.hf_base : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_personal" label="金额(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].hf_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.hf_personal != null ? row.hf_personal : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_personal_rate" label="比例(个人)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].hf_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.hf_personal_rate != null ? (row.hf_personal_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].hf_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.hf_company != null ? row.hf_company : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].hf_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.hf_company_rate != null ? (row.hf_company_rate * 100).toFixed(2) + '%' : '' }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_total" label="公积金合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[row.id]">
              <el-input-number v-model="editCache[row.id].hf_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
            </template>
            <template v-else>{{ row.hf_total != null ? row.hf_total : '' }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <el-table-column prop="grand_total" label="社保公积金总合计" width="130">
        <template #default="{ row }">
          <template v-if="editMode && editCache[row.id]">
            <el-input-number v-model="editCache[row.id].grand_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(row.id)" />
          </template>
          <template v-else>{{ row.grand_total != null ? row.grand_total : '' }}</template>
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

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑社保公积金' : '录入社保公积金'" width="750px" append-to-body>
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-form-item label="核算周期">
          <el-tag type="info" size="large">{{ formatPeriod(periodDate) }}</el-tag>
          <span class="text-xs text-gray-400 ml-2">数据将录入到当前选中月份</span>
        </el-form-item>
        <el-form-item label="员工编号">
          <el-input :model-value="formEmployeeNo" disabled />
        </el-form-item>
        <el-form-item label="个人社保号">
          <el-input v-model="form.employee_social_insurance_no" placeholder="个人社保号" />
        </el-form-item>

        <el-divider content-position="left">养老保险</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="个人基数">
              <el-input-number v-model="form.pension_personal_base" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="个人金额">
              <el-input-number v-model="form.pension_personal" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="个人比例">
              <el-input-number v-model="form.pension_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="单位基数">
              <el-input-number v-model="form.pension_company_base" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位金额">
              <el-input-number v-model="form.pension_company" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位比例">
              <el-input-number v-model="form.pension_company_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">失业保险</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="个人基数">
              <el-input-number v-model="form.unemployment_personal_base" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="个人金额">
              <el-input-number v-model="form.unemployment_personal" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="个人比例">
              <el-input-number v-model="form.unemployment_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="单位基数">
              <el-input-number v-model="form.unemployment_company_base" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位金额">
              <el-input-number v-model="form.unemployment_company" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位比例">
              <el-input-number v-model="form.unemployment_company_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">医疗保险</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="个人基数">
              <el-input-number v-model="form.medical_personal_base" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="个人金额">
              <el-input-number v-model="form.medical_personal" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="个人比例">
              <el-input-number v-model="form.medical_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="单位基数">
              <el-input-number v-model="form.medical_company_base" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位金额">
              <el-input-number v-model="form.medical_company" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位比例">
              <el-input-number v-model="form.medical_company_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">工伤保险</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="单位基数">
              <el-input-number v-model="form.injury_company_base" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位金额">
              <el-input-number v-model="form.injury_company" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位比例">
              <el-input-number v-model="form.injury_company_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">公积金</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="缴存基数">
              <el-input-number v-model="form.hf_base" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="个人金额">
              <el-input-number v-model="form.hf_personal" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="个人比例">
              <el-input-number v-model="form.hf_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="单位金额">
              <el-input-number v-model="form.hf_company" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单位比例">
              <el-input-number v-model="form.hf_company_rate" :min="0" :max="1" :step="0.01" :precision="4" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="公积金合计">
              <el-input-number v-model="form.hf_total" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">合计</el-divider>
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="养老合计">
              <el-input-number v-model="form.pension_total" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="失业合计">
              <el-input-number v-model="form.unemployment_total" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="医疗合计">
              <el-input-number v-model="form.medical_total" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="工伤合计">
              <el-input-number v-model="form.injury_total" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="社保个人合计">
              <el-input-number v-model="form.si_personal" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="社保公司合计">
              <el-input-number v-model="form.si_company" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="社保总合计">
              <el-input-number v-model="form.si_grand_total" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="社保公积金总合计">
              <el-input-number v-model="form.grand_total" :min="0" :precision="2" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisibleOld" title="单文件导入社保公积金" width="700px" append-to-body>
      <div class="mb-4">
        <div class="bg-blue-50 rounded-lg p-3 mb-3 text-sm">
          <div class="flex items-center gap-2">
            <el-icon class="text-blue-600"><InfoFilled /></el-icon>
            <span class="font-medium text-blue-700">导入月份：<span class="text-blue-900 text-base">{{ formatPeriod(periodDate) }}</span></span>
          </div>
        </div>
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
          支持 .xlsx / .xls 格式，表头需包含：员工编号、社保基数、养老保险个人、失业保险个人、医疗保险个人、社保个人合计、养老保险公司、失业保险公司、医疗保险公司、社保公司合计、公积金基数、公积金个人、公积金公司
        </div>
        <div v-if="importResult" class="mt-3">
          <el-alert
            :type="importResult.created || importResult.updated ? 'success' : 'warning'"
            :title="importResult.message"
            :closable="false"
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisibleOld = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 智能导入弹窗 -->
    <el-dialog v-model="smartImportVisible" title="智能批量导入" width="750px" append-to-body @close="resetSmartImport">
      <div class="mb-4">
        <div class="bg-blue-50 rounded-lg p-3 mb-4 text-sm">
          <div class="flex items-center gap-2 mb-2">
            <el-icon class="text-blue-600"><InfoFilled /></el-icon>
            <span class="font-medium text-blue-700">导入月份：<span class="text-blue-900 text-base">{{ formatPeriod(periodDate) }}</span></span>
          </div>
          <p class="text-gray-600 ml-6">数据将导入到当前页面选中的月份。如需导入其他月份，请先切换页面顶部的月份选择器。</p>
        </div>
        <div class="bg-blue-50 rounded-lg p-3 mb-4 text-sm text-gray-600 flex items-start gap-2">
          <el-icon class="mt-0.5"><InfoFilled /></el-icon>
          <div>
            <p class="font-medium mb-1">智能导入说明</p>
            <p>支持同时上传多个 Excel(.xlsx/.xls) 和 PDF(.pdf) 文件，系统会自动识别文件格式、匹配解析模板、按员工姓名关联档案。请在「模板配置」中预先配置好各政务平台的解析模板。</p>
          </div>
        </div>

        <el-upload
          ref="smartUploadRef"
          :auto-upload="false"
          multiple
          accept=".xlsx,.xls,.pdf"
          :on-change="handleSmartFileChange"
          :file-list="smartFileList"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击选择</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 Excel (.xlsx/.xls) 和 PDF (.pdf)，可一次选择多个文件
            </div>
          </template>
        </el-upload>

        <div class="flex justify-center mt-4">
          <el-button type="primary" :loading="smartImporting" :disabled="smartFiles.length === 0" @click="doSmartImport">
            开始智能导入
          </el-button>
        </div>

        <!-- 导入结果 -->
        <div v-if="smartImportResult" class="mt-4">
          <el-alert
            :type="smartImportResult.created || smartImportResult.updated ? 'success' : 'warning'"
            :closable="false"
            class="mb-3"
          >
            <template #title>
              共解析 {{ smartImportResult.parsed_files }}/{{ smartImportResult.total_files }} 个文件，
              提取 {{ smartImportResult.total_rows }} 行数据，
              新增 {{ smartImportResult.created }} 条，更新 {{ smartImportResult.updated }} 条
            </template>
          </el-alert>

          <!-- 异常详情 -->
          <template v-if="smartImportResult.errors.length || smartImportResult.warnings.length">
            <el-tabs type="border-card" class="import-tabs">
              <el-tab-pane v-if="smartImportResult.errors.length" label="错误">
                <el-table :data="smartImportResult.errors" border stripe size="small" max-height="300">
                  <el-table-column prop="file_name" label="来源文件" min-width="150" show-overflow-tooltip />
                  <el-table-column prop="error_type" label="错误类型" width="120">
                    <template #default="{ row }">
                      <el-tag :type="row.error_level === 'error' ? 'danger' : 'warning'" size="small">
                        {{ errorTypeLabels[row.error_type] || row.error_type }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="error_message" label="错误详情" min-width="250" show-overflow-tooltip />
                </el-table>
              </el-tab-pane>
              <el-tab-pane v-if="smartImportResult.warnings.length" label="预警">
                <el-table :data="smartImportResult.warnings" border stripe size="small" max-height="300">
                  <el-table-column prop="employee_name" label="员工姓名" width="90" />
                  <el-table-column prop="error_type" label="预警类型" width="120">
                    <template #default="{ row }">
                      <el-tag type="warning" size="small">{{ errorTypeLabels[row.error_type] || row.error_type }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="error_message" label="预警详情" min-width="250" show-overflow-tooltip />
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </template>
        </div>
      </div>
      <template #footer>
        <el-button @click="smartImportVisible = false">关闭</el-button>
        <el-button v-if="smartImportResult" type="primary" @click="closeSmartImport">完成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editConfirmVisible" title="确认保存修改" width="600px" append-to-body>
      <div class="mb-2 text-gray-600">以下社保公积金数据将被更新，请确认：</div>
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload, Delete, InfoFilled, UploadFilled } from '@element-plus/icons-vue'
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
    if (month === 1) {
      targetYear = year - 1
      targetMonth = 12
    } else {
      targetYear = year
      targetMonth = month - 1
    }
  } else {
    targetYear = year
    targetMonth = month
  }
  return `${targetYear}${String(targetMonth).padStart(2, '0')}`
}

function formatPeriod(periodStr) {
  if (!periodStr || periodStr.length < 6) return periodStr
  return `${periodStr.substring(0, 4)}年${periodStr.substring(4, 6)}月`
}

const defaultPeriod = getDefaultPeriod()

const loading = ref(false)
const saving = ref(false)
const savingEdits = ref(false)
const importing = ref(false)
const smartImporting = ref(false)
const dialogVisible = ref(false)
const importVisibleOld = ref(false)
const smartImportVisible = ref(false)
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
// 智能导入相关
const smartUploadRef = ref(null)
const smartFiles = ref([])
const smartFileList = ref([])
const smartImportResult = ref(null)
const formRef = ref(null)
const editId = ref(null)
const formEmployeeId = ref(null)
const formEmployeeNo = ref('')

const editMode = ref(false)
const editCache = reactive({})
const changedSet = ref(new Set())
const editConfirmVisible = ref(false)
const confirmList = ref([])

const fieldLabels = {
  pension_personal_base: '养老基数(个人)', pension_company_base: '养老基数(单位)',
  unemployment_personal_base: '失业基数(个人)', unemployment_company_base: '失业基数(单位)',
  medical_personal_base: '医疗基数(个人)', medical_company_base: '医疗基数(单位)',
  injury_company_base: '工伤基数(单位)',
  pension_personal: '养老保险个人', unemployment_personal: '失业保险个人',
  medical_personal: '医疗保险个人', si_personal: '社保个人合计',
  pension_company: '养老保险公司', unemployment_company: '失业保险公司', medical_company: '医疗保险公司',
  injury_company: '工伤保险公司', si_company: '社保公司合计',
  pension_personal_rate: '养老个人比例', pension_company_rate: '养老单位比例',
  unemployment_personal_rate: '失业个人比例', unemployment_company_rate: '失业单位比例',
  medical_personal_rate: '医疗个人比例', medical_company_rate: '医疗单位比例',
  injury_company_rate: '工伤单位比例',
  pension_total: '养老保险合计', unemployment_total: '失业保险合计',
  medical_total: '医疗保险合计', injury_total: '工伤保险合计',
  si_grand_total: '社保总合计',
  hf_base: '公积金基数', hf_personal: '公积金个人', hf_company: '公积金公司',
  hf_personal_rate: '公积金个人比例', hf_company_rate: '公积金单位比例',
  hf_total: '公积金合计', grand_total: '社保公积金总合计'
}

const editFields = ['pension_personal_base', 'pension_company_base',
  'unemployment_personal_base', 'unemployment_company_base',
  'medical_personal_base', 'medical_company_base', 'injury_company_base',
  'pension_personal', 'unemployment_personal', 'medical_personal', 'si_personal',
  'pension_company', 'unemployment_company', 'medical_company', 'injury_company', 'si_company',
  'pension_personal_rate', 'pension_company_rate',
  'unemployment_personal_rate', 'unemployment_company_rate',
  'medical_personal_rate', 'medical_company_rate', 'injury_company_rate',
  'pension_total', 'unemployment_total', 'medical_total', 'injury_total',
  'si_grand_total',
  'hf_base', 'hf_personal', 'hf_company',
  'hf_personal_rate', 'hf_company_rate', 'hf_total',
  'grand_total']

const form = reactive({
  period: defaultPeriod, employee_id: null,
  pension_personal_base: 0, pension_company_base: 0,
  unemployment_personal_base: 0, unemployment_company_base: 0,
  medical_personal_base: 0, medical_company_base: 0,
  injury_company_base: 0,
  pension_personal: 0, unemployment_personal: 0, medical_personal: 0,
  si_personal: 0, pension_company: 0, unemployment_company: 0, medical_company: 0,
  injury_company: 0, si_company: 0,
  pension_personal_rate: 0, pension_company_rate: 0,
  unemployment_personal_rate: 0, unemployment_company_rate: 0,
  medical_personal_rate: 0, medical_company_rate: 0, injury_company_rate: 0,
  pension_total: 0, unemployment_total: 0, medical_total: 0, injury_total: 0,
  si_grand_total: 0,
  hf_base: 0, hf_personal: 0, hf_company: 0,
  hf_personal_rate: 0, hf_company_rate: 0, hf_total: 0,
  grand_total: 0
})

const errorTypeLabels = {
  file_error: '文件错误', unsupported_format: '格式不支持', empty_file: '空文件',
  unknown_format: '无法识别格式', no_template: '缺少模板', template_error: '模板错误',
  name_not_found: '姓名未匹配', duplicate_name: '同名员工', empty_name: '姓名为空',
  missing_period: '月份缺失',
  amount_mismatch: '金额不匹配', duplicate_record: '重复记录'
}

const filteredRecords = computed(() => {
  if (!filterField.value || !filterValue.value) return records.value
  const keyword = filterValue.value.toLowerCase()
  return records.value.filter(r => {
    const val = String(r[filterField.value] || '').toLowerCase()
    return val.includes(keyword)
  })
})

const validSelectedCount = computed(() => {
  return selectedRows.value.filter(row => row.id != null).length
})

function onPeriodChange(val) {
  periodDate.value = val
  fetchData()
}

function tableRowClassName({ row }) {
  if (editMode.value && row.id && changedSet.value.has(row.id)) return 'row-changed'
  return ''
}

function initEditCache() {
  records.value.forEach(row => {
    if (!row || !row.id) return
    editCache[row.id] = reactive({})
    editFields.forEach(f => {
      editCache[row.id][f] = row[f] ?? 0
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
      for (const key of Object.keys(editCache)) {
        delete editCache[key]
      }
      return
    }
    initEditCache()
    editMode.value = true
    changedSet.value = new Set()
  } catch (e) {
    console.error('切换编辑模式失败：', e)
    ElMessage.error('切换编辑模式失败，请刷新页面后重试')
  }
}

function cancelEdits() {
  editMode.value = false
  changedSet.value = new Set()
  for (const key of Object.keys(editCache)) {
    delete editCache[key]
  }
}

function confirmEdits() {
  if (!changedSet.value.size) {
    ElMessage.warning('没有检测到任何修改')
    return
  }

  const items = []
  changedSet.value.forEach(id => {
    const row = records.value.find(r => r.id === id)
    if (!row) return
    const changes = []
    editFields.forEach(f => {
      const oldVal = row[f] ?? 0
      const newVal = editCache[id]?.[f] ?? 0
      if (Math.abs(oldVal - newVal) > 0.001) {
        changes.push({
          field: f,
          label: fieldLabels[f] || f,
          old: oldVal.toFixed(2),
          new: newVal.toFixed(2)
        })
      }
    })
    if (changes.length) {
      items.push({ id, employee_name: row.employee_name, employee_no: row.employee_no, changes })
    }
  })

  if (!items.length) {
    ElMessage.warning('没有检测到实际修改')
    return
  }

  confirmList.value = items
  editConfirmVisible.value = true
}

async function saveAllEdits() {
  savingEdits.value = true
  let successCount = 0
  let failCount = 0

  try {
    for (const item of confirmList.value) {
      const cache = editCache[item.id]
      if (!cache) continue
      const payload = {}
      editFields.forEach(f => {
        payload[f] = cache[f]
      })
      try {
        await api.put(`/social-insurance/${item.id}`, payload)
        successCount++
      } catch {
        failCount++
      }
    }

    if (failCount === 0) {
      ElMessage.success(`修改成功！共更新 ${successCount} 条记录`)
    } else {
      ElMessage.warning(`部分成功：${successCount} 条已更新，${failCount} 条失败`)
    }
    editConfirmVisible.value = false
    editMode.value = false
    changedSet.value = new Set()
    for (const key of Object.keys(editCache)) {
      delete editCache[key]
    }
    await fetchData()
  } finally {
    savingEdits.value = false
  }
}

async function fetchData() {
  loading.value = true
  try {
    const params = { period: periodDate.value }
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get('/social-insurance/', { params })
    records.value = res.data
  } catch {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

async function handleBatchDelete() {
  const validRows = selectedRows.value.filter(row => row.id != null)
  if (!validRows.length) {
    ElMessage.warning('选中的记录中没有可删除的有效数据（空行无需删除）')
    return
  }
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${validRows.length} 条社保公积金记录？此操作不可恢复`, '批量删除', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  loading.value = true
  try {
    const ids = validRows.map(row => row.id)
    const res = await api.post('/social-insurance/batch-delete', ids)
    ElMessage.success(res.data.message || `成功删除 ${ids.length} 条记录`)
    await fetchData()
  } catch (e) {
    const msg = e.response?.data?.detail || '删除失败'
    ElMessage.error(msg)
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
    form.period = row.period || periodDate.value
    form.employee_id = row.employee_id
    editFields.forEach(f => { form[f] = row[f] ?? 0 })
  } else {
    form.period = periodDate.value
    form.employee_id = null
    editFields.forEach(f => { form[f] = 0 })
  }
  dialogVisible.value = true
}

function showDialogForEmployee(row) {
  isEdit.value = false
  editId.value = null
  formEmployeeId.value = row.employee_id
  formEmployeeNo.value = row.employee_no
  form.period = periodDate.value
  form.employee_id = row.employee_id
  editFields.forEach(f => { form[f] = 0 })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const payload = {
      period: periodDate.value,
      employee_id: form.employee_id,
    }
    editFields.forEach(f => { payload[f] = form[f] })

    if (isEdit.value) {
      await api.put(`/social-insurance/${editId.value}`, payload)
      ElMessage.success('修改成功')
    } else {
      await api.post('/social-insurance/', payload)
      ElMessage.success('录入成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e) {
    const msg = e.response?.data?.detail || '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

function showImportOld() {
  importFile.value = null
  fileList.value = []
  importResult.value = null
  importVisibleOld.value = true
}

function handleFileChange(file) {
  importFile.value = file.raw
}

async function doImport() {
  if (!importFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)
    const res = await api.post(`/social-insurance/import/${periodDate.value}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    importResult.value = res.data
    ElMessage.success(res.data.message)
    await fetchData()
  } catch (e) {
    const msg = e.response?.data?.detail || '导入失败'
    ElMessage.error(msg)
  } finally {
    importing.value = false
  }
}

// ── 智能导入 ──
function showSmartImport() {
  smartFiles.value = []
  smartFileList.value = []
  smartImportResult.value = null
  smartImportVisible.value = true
}

function handleSmartFileChange(file) {
  smartFiles.value.push(file.raw)
}

function resetSmartImport() {
  smartFiles.value = []
  smartFileList.value = []
  smartImportResult.value = null
}

async function doSmartImport() {
  if (!smartFiles.value.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  smartImporting.value = true
  try {
    const formData = new FormData()
    smartFiles.value.forEach(f => {
      formData.append('files', f)
    })
    const res = await api.post(`/social-insurance/smart-import/${periodDate.value}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    smartImportResult.value = res.data
    if (res.data.created > 0 || res.data.updated > 0) {
      ElMessage.success(`导入成功：新增 ${res.data.created} 条，更新 ${res.data.updated} 条`)
    }
    if (res.data.errors.length > 0 || res.data.warnings.length > 0) {
      ElMessage.warning(`${res.data.errors.length} 个错误，${res.data.warnings.length} 个预警，详见弹窗`)
    }
    await fetchData()
  } catch (e) {
    const msg = e.response?.data?.detail || '智能导入失败'
    ElMessage.error(msg)
  } finally {
    smartImporting.value = false
  }
}

function closeSmartImport() {
  smartImportVisible.value = false
  resetSmartImport()
}

async function handleExport() {
  try {
    const params = {}
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) {
      params.hide_status_id = Number(hideStatusId)
    }
    const res = await api.get(`/social-insurance/export/${periodDate.value}`, { params, responseType: 'blob' })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `社保公积金_${periodDate.value}.xlsx`
    link.click()
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.action-cell {
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
:deep(.row-changed) {
  background-color: #fef3c7 !important;
}
.import-tabs {
  box-shadow: none;
}
.import-tabs :deep(.el-tabs__content) {
  padding: 0;
}
</style>