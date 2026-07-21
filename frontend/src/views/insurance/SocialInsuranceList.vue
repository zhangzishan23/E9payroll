<template>
  <div class="apple-card p-6">
    <div class="flex items-center gap-2 mb-4 flex-wrap">
      <h3 class="text-lg font-semibold text-gray-700 shrink-0 mr-1">社保公积金管理</h3>
      <el-date-picker v-model="periodDate" type="month" placeholder="选择月份" size="small" class="!w-40" value-format="YYYYMM" @change="onPeriodChange" />
      <el-select v-model="filterField" placeholder="筛选字段" size="small" class="!w-24">
        <el-option label="员工姓名" value="employee_name" />
      </el-select>
      <el-input v-model="filterValue" placeholder="筛选值" size="small" clearable class="!w-36" @input="fetchData" />
      <el-button :icon="Upload" size="small" @click="showImportOld" v-permission="'insurance:import'">单文件导入</el-button>
      <el-button type="primary" :icon="Upload" size="small" @click="showSmartImport" v-permission="'insurance:import'">智能导入</el-button>
      <el-button type="success" :icon="Download" size="small" @click="handleExport" v-permission="'insurance:export'">导出</el-button>
      <el-button type="warning" :icon="CopyDocument" size="small" :loading="copying" @click="handleCopyFromPrev" v-permission="'insurance:edit'">用上月数据预填</el-button>
      <el-button type="danger" :icon="Delete" size="small" :disabled="!validSelectedCount" @click="handleBatchDelete" v-permission="'insurance:delete'">
        删除{{ validSelectedCount ? `(${validSelectedCount})` : '' }}
      </el-button>
      <el-divider direction="vertical" />
      <el-button size="small" :type="editMode ? 'warning' : 'default'" @click="toggleEditMode" v-permission="'insurance:edit'">
        {{ editMode ? '退出编辑' : '编辑' }}
      </el-button>
      <ColumnSetting
        :columns="SI_TABLE_COLUMNS"
        :default-visible-keys="SI_DEFAULT_VISIBLE"
        v-model="siVisibleColumns"
        storage-key="social_insurance_table_columns"
      />
      <template v-if="editMode">
        <el-button type="primary" size="small" :loading="savingEdits" :disabled="changedSet.size === 0" @click="confirmEdits" v-permission="'insurance:edit'">
          保存{{ changedSet.size ? `(${changedSet.size})` : '' }}
        </el-button>
        <el-button size="small" :disabled="changedSet.size === 0" @click="cancelEdits">取消</el-button>
      </template>
    </div>

    <div class="bg-blue-50 rounded-lg p-3 mb-4 text-sm text-gray-600 flex items-center gap-2">
      <el-icon><InfoFilled /></el-icon>
      <span>提示：不同城市的社保公积金基数、比例不同（北京/广州/邯郸/上海），请按各公司实际情况填写。</span>
    </div>

    <el-table :data="filteredRecords" border stripe v-loading="loading" :max-height="tableMaxHeight" @selection-change="handleSelectionChange" :row-class-name="tableRowClassName">
      <el-table-column v-if="isSiColumnVisible('selection')" type="selection" width="55" :selectable="row => row.id != null" />
      <el-table-column v-if="isSiColumnVisible('index')" type="index" label="序号" width="50" fixed="left" />
      <el-table-column v-if="isSiColumnVisible('employee_name')" prop="employee_name" label="员工姓名" width="80" fixed="left" />

      <!-- 养老保险 -->
      <el-table-column v-if="isSiColumnVisible('pension_group')" label="养老保险" min-width="450">
        <el-table-column prop="pension_personal_base" label="基数(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].pension_personal_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.pension_personal_base) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_personal" label="金额(个人)" width="100" class-name="col-personal-amount">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].pension_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.pension_personal) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_personal_rate" label="比例(个人)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].pension_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.pension_personal_rate, 2) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_company_base" label="基数(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].pension_company_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.pension_company_base) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].pension_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.pension_company) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="pension_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].pension_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.pension_company_rate, 2) }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 失业保险 -->
      <el-table-column v-if="isSiColumnVisible('unemployment_group')" label="失业保险" min-width="450">
        <el-table-column prop="unemployment_personal_base" label="基数(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].unemployment_personal_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.unemployment_personal_base) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_personal" label="金额(个人)" width="100" class-name="col-personal-amount">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].unemployment_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.unemployment_personal) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_personal_rate" label="比例(个人)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].unemployment_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.unemployment_personal_rate, 2) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_company_base" label="基数(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].unemployment_company_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.unemployment_company_base) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].unemployment_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.unemployment_company) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].unemployment_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.unemployment_company_rate, 2) }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 医疗保险 -->
      <el-table-column v-if="isSiColumnVisible('medical_group')" label="医疗保险" min-width="450">
        <el-table-column prop="medical_personal_base" label="基数(个人)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].medical_personal_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.medical_personal_base) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_personal" label="金额(个人)" width="100" class-name="col-personal-amount">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].medical_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.medical_personal) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_personal_rate" label="比例(个人)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].medical_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.medical_personal_rate, 2) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_company_base" label="基数(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].medical_company_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.medical_company_base) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].medical_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.medical_company) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].medical_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.medical_company_rate, 2) }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 工伤保险 -->
      <el-table-column v-if="isSiColumnVisible('injury_group')" label="工伤保险" min-width="300">
        <el-table-column prop="injury_company_base" label="基数(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].injury_company_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.injury_company_base) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="injury_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].injury_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.injury_company) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="injury_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].injury_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.injury_company_rate, 2) }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <!-- 社保合计 -->
      <el-table-column v-if="isSiColumnVisible('si_totals_group')" label="社保合计" min-width="350">
        <el-table-column prop="pension_total" label="养老合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].pension_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.pension_total) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="unemployment_total" label="失业合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].unemployment_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.unemployment_total) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="medical_total" label="医疗合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].medical_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.medical_total) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="injury_total" label="工伤合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].injury_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.injury_total) }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <el-table-column v-if="isSiColumnVisible('si_personal')" prop="si_personal" label="社保个人合计" width="110" class-name="col-personal-amount">
        <template #default="{ row }">
          <template v-if="editMode && editCache[getCacheKey(row)]">
            <el-input-number v-model="editCache[getCacheKey(row)].si_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
          </template>
          <template v-else>{{ formatMoney(row.si_personal) }}</template>
        </template>
      </el-table-column>
      <el-table-column v-if="isSiColumnVisible('si_company')" prop="si_company" label="社保公司合计" width="110">
        <template #default="{ row }">
          <template v-if="editMode && editCache[getCacheKey(row)]">
            <el-input-number v-model="editCache[getCacheKey(row)].si_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
          </template>
          <template v-else>{{ formatMoney(row.si_company) }}</template>
        </template>
      </el-table-column>
      <el-table-column v-if="isSiColumnVisible('si_grand_total')" prop="si_grand_total" label="社保总合计" width="110">
        <template #default="{ row }">
          <template v-if="editMode && editCache[getCacheKey(row)]">
            <el-input-number v-model="editCache[getCacheKey(row)].si_grand_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
          </template>
          <template v-else>{{ formatMoney(row.si_grand_total) }}</template>
        </template>
      </el-table-column>

      <!-- 公积金 -->
      <el-table-column v-if="isSiColumnVisible('hf_group')" label="公积金" min-width="450">
        <el-table-column prop="hf_base" label="缴存基数" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].hf_base" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.hf_base) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_personal" label="金额(个人)" width="100" class-name="col-personal-amount">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].hf_personal" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.hf_personal) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_personal_rate" label="比例(个人)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].hf_personal_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.hf_personal_rate, 2) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_company" label="金额(单位)" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].hf_company" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.hf_company) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_company_rate" label="比例(单位)" width="90">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].hf_company_rate" :min="0" :max="1" :step="0.01" :precision="4" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatPercent(row.hf_company_rate, 2) }}</template>
          </template>
        </el-table-column>
        <el-table-column prop="hf_total" label="公积金合计" width="100">
          <template #default="{ row }">
            <template v-if="editMode && editCache[getCacheKey(row)]">
              <el-input-number v-model="editCache[getCacheKey(row)].hf_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
            </template>
            <template v-else>{{ formatMoney(row.hf_total) }}</template>
          </template>
        </el-table-column>
      </el-table-column>

      <el-table-column v-if="isSiColumnVisible('grand_total')" prop="grand_total" label="社保公积金总合计" width="130">
        <template #default="{ row }">
          <template v-if="editMode && editCache[getCacheKey(row)]">
            <el-input-number v-model="editCache[getCacheKey(row)].grand_total" :min="0" :precision="2" size="small" controls-position="right" class="cell-number" @change="markChanged(getCacheKey(row))" />
          </template>
          <template v-else>{{ formatMoney(row.grand_total) }}</template>
        </template>
      </el-table-column>

      <el-table-column v-if="isSiColumnVisible('action')" label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <div class="action-cell">
            <el-button v-if="row.id && !editMode" type="primary" link size="small" @click="showDialog(row)" v-permission="'insurance:edit'">编辑</el-button>
            <el-button v-else-if="!row.id && !editMode" type="success" link size="small" @click="showDialogForEmployee(row)" v-permission="'insurance:create'">录入</el-button>
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
        <el-form-item label="员工姓名">
          <el-input :model-value="formEmployeeName" disabled />
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

        <div class="upload-area mb-4">
          <el-upload
            ref="smartUploadRef"
            :auto-upload="false"
            multiple
            accept=".xlsx,.xls,.pdf"
            :on-change="handleSmartFileChange"
            :show-file-list="false"
            drag
            class="smart-upload-drag"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击选择文件</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 Excel (.xlsx/.xls) 和 PDF (.pdf)，可一次选择多个文件
              </div>
            </template>
          </el-upload>
        </div>

        <div class="flex justify-center gap-3 mb-4">
          <el-button type="primary" :icon="FolderAdd" @click="triggerFolderSelect">
            选择文件夹
          </el-button>
          <input
            ref="folderInputRef"
            type="file"
            webkitdirectory
            directory
            multiple
            accept=".xlsx,.xls,.pdf"
            class="hidden"
            @change="handleFolderSelect"
          />
        </div>

        <div v-if="smartFiles.length > 0" class="selected-files mb-4">
          <div class="text-sm text-gray-600 mb-2">已选择 {{ smartFiles.length }} 个文件：</div>
          <el-table :data="smartFileListDisplay" border stripe size="small" max-height="200">
            <el-table-column prop="relativePath" label="文件路径" min-width="300" show-overflow-tooltip />
            <el-table-column prop="size" label="大小" width="100">
              <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="70" fixed="right">
              <template #default="{ $index }">
                <el-button type="danger" link size="small" @click="removeSelectedFile($index)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="flex justify-center mt-4">
          <el-button @click="clearSelectedFiles" :disabled="smartFiles.length === 0">清空列表</el-button>
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
        <el-button v-if="hasNoTemplateError" type="warning" @click="goToTemplateConfig">配置缺失模板</el-button>
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
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Download, Upload, Delete, InfoFilled, UploadFilled, WarningFilled, CopyDocument, Setting, FolderAdd } from '@element-plus/icons-vue'
import api from '../../api'
import ColumnSetting from '../../components/ColumnSetting.vue'
import { formatMoney, formatPercent } from '../../utils/format'

const route = useRoute()
const router = useRouter()

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
const copying = ref(false)
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
const folderInputRef = ref(null)
const smartFiles = ref([])
const smartFileList = ref([])
const smartImportResult = ref(null)
const smartBatchId = ref(null)

const smartFileListDisplay = computed(() => {
  return smartFiles.value.map((item, idx) => ({
    name: item.file.name,
    relativePath: item.relativePath,
    size: item.file.size,
    index: idx
  }))
})
const formRef = ref(null)
const editId = ref(null)
const formEmployeeId = ref(null)
const formEmployeeName = ref('')

const editMode = ref(false)
const editCache = reactive({})
const changedSet = ref(new Set())
const editConfirmVisible = ref(false)
const confirmList = ref([])
const tableMaxHeight = ref(700)

function updateTableHeight() {
  tableMaxHeight.value = Math.max(400, window.innerHeight - 260)
}

const SI_TABLE_COLUMNS = [
  { key: 'selection', label: '选择', required: true },
  { key: 'index', label: '序号', required: true },
  { key: 'employee_name', label: '员工姓名', required: true },
  { key: 'pension_group', label: '养老保险（明细）' },
  { key: 'unemployment_group', label: '失业保险（明细）' },
  { key: 'medical_group', label: '医疗保险（明细）' },
  { key: 'injury_group', label: '工伤保险（明细）' },
  { key: 'si_totals_group', label: '社保各险合计' },
  { key: 'si_personal', label: '社保个人合计' },
  { key: 'si_company', label: '社保公司合计' },
  { key: 'si_grand_total', label: '社保总合计' },
  { key: 'hf_group', label: '公积金（明细）' },
  { key: 'grand_total', label: '社保公积金总合计' },
  { key: 'action', label: '操作', required: true },
]

const SI_DEFAULT_VISIBLE = [
  'selection', 'index', 'employee_name',
  'si_personal', 'si_company', 'hf_group', 'grand_total', 'action'
]

const siVisibleColumns = ref([])

function isSiColumnVisible(key) {
  return siVisibleColumns.value.includes(key)
}

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

// 检测导入结果中是否有未匹配模板的错误
const hasNoTemplateError = computed(() => {
  if (!smartImportResult.value) return false
  return smartImportResult.value.errors?.some(e => e.error_type === 'no_template')
})

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
  if (editMode.value && changedSet.value.has(getCacheKey(row))) return 'row-changed'
  return ''
}

function getCacheKey(row) {
  return row.id || `_emp_${row.employee_id}`
}

function initEditCache() {
  records.value.forEach(row => {
    if (!row) return
    const cacheKey = row.id || `_emp_${row.employee_id}`
    editCache[cacheKey] = reactive({})
    editFields.forEach(f => {
      editCache[cacheKey][f] = row[f] ?? 0
    })
  })
}

function markChanged(rowId) {
  changedSet.value = new Set(changedSet.value)
  changedSet.value.add(rowId)
}

async function ensureRecordsExist() {
  const hasUncreated = records.value.some(r => r.id == null)
  if (!hasUncreated) return true
  const loading = ElLoading.service({ text: '正在准备数据...' })
  try {
    const params = {}
    const hideStatusId = localStorage.getItem('employee_hide_status_id')
    if (hideStatusId) params.hide_status_id = Number(hideStatusId)
    await api.post(`/social-insurance/ensure-records/${periodDate.value}`, null, { params })
    await fetchData()
    return true
  } catch (e) {
    ElMessage.error('准备数据失败：' + (e.response?.data?.detail || e.message))
    return false
  } finally {
    loading.close()
  }
}

async function toggleEditMode() {
  try {
    if (editMode.value) {
      editMode.value = false
      changedSet.value = new Set()
      for (const key of Object.keys(editCache)) {
        delete editCache[key]
      }
      return
    }
    const ok = await ensureRecordsExist()
    if (!ok) return
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

  function findRowByCacheKey(key) {
    const numKey = Number(key)
    if (!isNaN(numKey)) return records.value.find(r => r.id === numKey)
    const empId = parseInt(key.replace('_emp_', ''), 10)
    return records.value.find(r => r.employee_id === empId)
  }

  const items = []
  changedSet.value.forEach(cacheKey => {
    const row = findRowByCacheKey(cacheKey)
    if (!row) return
    const changes = []
    editFields.forEach(f => {
      const oldVal = row[f] ?? 0
      const newVal = editCache[cacheKey]?.[f] ?? 0
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
      items.push({ cacheKey, id: row.id, employee_id: row.employee_id, employee_name: row.employee_name, employee_no: row.employee_no, changes })
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
      const cache = editCache[item.cacheKey]
      if (!cache) continue
      const payload = {}
      editFields.forEach(f => {
        payload[f] = cache[f]
      })
      try {
        if (item.id) {
          await api.put(`/social-insurance/${item.id}`, payload)
        } else {
          payload.period = periodDate.value
          payload.employee_id = item.employee_id
          await api.post('/social-insurance/', payload)
        }
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
  formEmployeeName.value = row?.employee_name || ''

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
  formEmployeeName.value = row.employee_name
  form.period = periodDate.value
  form.employee_id = row.employee_id
  editFields.forEach(f => { form[f] = 0 })

  api.get(`/social-insurance/prev-month-data/${periodDate.value}/${row.employee_id}`).then(res => {
    if (res.data.has_data && res.data.data) {
      const prevData = res.data.data
      editFields.forEach(f => {
        if (prevData[f] != null) {
          form[f] = prevData[f]
        }
      })
      ElMessage.info(`已自动预填${res.data.prev_period.substring(0,4)}年${res.data.prev_period.substring(4,6)}月数据，请核对修改`)
    }
  }).catch(() => {})

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
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function showSmartImport() {
  smartFiles.value = []
  smartFileList.value = []
  smartImportResult.value = null
  smartImportVisible.value = true
}

function handleSmartFileChange(file) {
  const exists = smartFiles.value.some(item => 
    item.file.name === file.raw.name && item.file.size === file.raw.size && item.relativePath === file.raw.name
  )
  if (!exists) {
    smartFiles.value.push({
      file: file.raw,
      relativePath: file.raw.name
    })
    smartFileList.value.push({
      name: file.raw.name,
      relativePath: file.raw.name,
      size: file.raw.size
    })
  }
}

function triggerFolderSelect() {
  folderInputRef.value?.click()
}

function handleFolderSelect(e) {
  const files = e.target.files
  if (!files || files.length === 0) return
  
  let addedCount = 0
  for (let i = 0; i < files.length; i++) {
    const f = files[i]
    const ext = f.name.toLowerCase().split('.').pop()
    if (!['xlsx', 'xls', 'pdf'].includes(ext)) continue
    
    const relativePath = f.webkitRelativePath || f.name
    const exists = smartFiles.value.some(item => 
      item.file.name === f.name && item.relativePath === relativePath
    )
    if (!exists) {
      smartFiles.value.push({
        file: f,
        relativePath: relativePath
      })
      smartFileList.value.push({
        name: f.name,
        relativePath: relativePath,
        size: f.size
      })
      addedCount++
    }
  }
  
  if (addedCount > 0) {
    ElMessage.success(`已添加 ${addedCount} 个文件`)
  }
  e.target.value = ''
}

function removeSelectedFile(index) {
  smartFiles.value.splice(index, 1)
  smartFileList.value.splice(index, 1)
}

function clearSelectedFiles() {
  smartFiles.value = []
  smartFileList.value = []
  if (smartUploadRef.value) {
    smartUploadRef.value.clearFiles()
  }
  if (folderInputRef.value) {
    folderInputRef.value.value = ''
  }
}

function resetSmartImport() {
  clearSelectedFiles()
  smartImportResult.value = null
  smartBatchId.value = null
}

async function doSmartImport() {
  if (!smartFiles.value.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  smartImporting.value = true
  try {
    const formData = new FormData()
    const filePaths = []
    smartFiles.value.forEach(item => {
      formData.append('files', item.file)
      filePaths.push(item.relativePath)
    })
    formData.append('file_paths', JSON.stringify(filePaths))

    // 第一步：上传文件并预检查
    const prepareRes = await api.post(`/social-insurance/smart-import-prepare/${periodDate.value}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const prepareData = prepareRes.data

    // 保存 batch_id，供结果弹窗中配置模板跳转使用
    smartBatchId.value = prepareData.batch_id

    // 如果有未匹配模板的文件，跳转到模板配置页面
    if (prepareData.has_unmatched && prepareData.unmatched_files.length > 0) {
      ElMessage.warning(`检测到 ${prepareData.unmatched_files.length} 个文件/工作表未匹配模板，请先配置模板`)
      smartImportVisible.value = false
      resetSmartImport()
      // 跳转到模板配置页面，传入batch_id和period
      router.push({
        name: 'InsuranceTemplate',
        query: {
          batch_id: prepareData.batch_id,
          period: periodDate.value
        }
      })
      return
    }

    // 所有文件都匹配到模板，直接执行导入
    await executeSmartImportBatch(prepareData.batch_id)
  } catch (e) {
    const msg = e.response?.data?.detail || '智能导入失败'
    ElMessage.error(msg)
  } finally {
    smartImporting.value = false
  }
}

async function executeSmartImportBatch(batchId) {
  try {
    smartImporting.value = true
    smartBatchId.value = batchId
    const res = await api.post(`/social-insurance/smart-import-batch/${batchId}/execute`)

    // 如果返回需要配置模板
    if (res.data.needs_config) {
      if (res.data.partial_success) {
        // 部分成功：已有文件导入成功，显示结果弹窗，让用户点击按钮跳转配置
        smartBatchId.value = res.data.config_batch_id
        smartImportResult.value = res.data
        if (res.data.created > 0 || res.data.updated > 0) {
          ElMessage.success(`导入成功：新增 ${res.data.created} 条，更新 ${res.data.updated} 条`)
        }
        ElMessage.warning(`检测到 ${res.data.unmatched_files?.length || 0} 个文件未匹配模板，请配置模板后继续`)
        smartImportVisible.value = true
        await fetchData()
        return
      }
      // 预检查阶段发现未匹配：直接跳转
      ElMessage.warning(`检测到 ${res.data.unmatched_files.length} 个文件未匹配模板，请先配置模板`)
      smartImportVisible.value = false
      resetSmartImport()
      router.push({
        name: 'InsuranceTemplate',
        query: {
          batch_id: res.data.config_batch_id || batchId,
          period: periodDate.value
        }
      })
      return
    }

    smartImportResult.value = res.data
    if (res.data.created > 0 || res.data.updated > 0) {
      ElMessage.success(`导入成功：新增 ${res.data.created} 条，更新 ${res.data.updated} 条`)
    }
    if (res.data.errors.length > 0 || res.data.warnings.length > 0) {
      ElMessage.warning(`${res.data.errors.length} 个错误，${res.data.warnings.length} 个预警，详见弹窗`)
    }
    smartImportVisible.value = true
    await fetchData()
  } catch (e) {
    const msg = e.response?.data?.detail || '批量导入执行失败'
    ElMessage.error(msg)
    if (batchId) {
      api.post(`/social-insurance/smart-import-batch/${batchId}/cancel`).catch(() => {})
    }
  } finally {
    smartImporting.value = false
  }
}

function closeSmartImport() {
  smartImportVisible.value = false
  resetSmartImport()
}

function goToTemplateConfig() {
  const batchId = smartBatchId.value
  smartImportVisible.value = false
  router.push({
    name: 'InsuranceTemplate',
    query: {
      batch_id: batchId,
      period: periodDate.value
    }
  })
}

async function handleCopyFromPrev() {
  const prevYear = periodDate.value.substring(0, 4)
  const prevMonth = periodDate.value.substring(4, 6)
  let prevPeriod
  if (prevMonth === '01') {
    prevPeriod = `${parseInt(prevYear) - 1}12`
  } else {
    prevPeriod = `${prevYear}${String(parseInt(prevMonth) - 1).padStart(2, '0')}`
  }
  const prevLabel = `${prevPeriod.substring(0,4)}年${prevPeriod.substring(4,6)}月`
  const currLabel = `${prevYear}年${prevMonth}月`

  try {
    await ElMessageBox.confirm(
      `确认将${prevLabel}的社保公积金数据复制到${currLabel}？\n\n注意：本月已有数据的员工不会被覆盖，只会为尚无数据的员工预填。`,
      '用上月数据预填',
      {
        confirmButtonText: '确认预填',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return
  }

  copying.value = true
  try {
    const res = await api.post(`/social-insurance/copy-from-prev/${periodDate.value}`)
    if (res.data.copied > 0) {
      ElMessage.success(res.data.message)
      await fetchData()
    } else {
      ElMessage.warning(res.data.message)
    }
  } catch (e) {
    const msg = e.response?.data?.detail || '预填失败'
    ElMessage.error(msg)
  } finally {
    copying.value = false
  }
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
  updateTableHeight()
  window.addEventListener('resize', updateTableHeight)
  fetchData()
  checkBatchExecute()
})

onUnmounted(() => {
  window.removeEventListener('resize', updateTableHeight)
})

// 检查是否从模板配置向导返回，需要执行批量导入
async function checkBatchExecute() {
  const batchId = route.query.execute_batch
  const period = route.query.period
  if (batchId) {
    // 清理URL参数
    router.replace({ name: 'Insurance' })
    if (period) {
      periodDate.value = period
    }
    ElMessage.info('模板配置完成，正在执行批量导入...')
    await executeSmartImportBatch(batchId)
  }
}
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
:deep(.col-personal-amount) {
  background-color: #fef9c3 !important;
}
.import-tabs {
  box-shadow: none;
}
.import-tabs :deep(.el-tabs__content) {
  padding: 0;
}
.hidden {
  display: none !important;
}
</style>