<template>
  <el-card class="template-config-card">
    <!-- 批量配置向导横幅 -->
    <el-alert
      v-if="batchMode"
      :title="`批量模板配置向导（第 ${currentBatchIndex + 1}/${batchUnmatchedFiles.length} 个）`"
      type="warning"
      :closable="false"
      show-icon
      class="mb-4"
    >
      <template #default>
        <div class="flex items-center justify-between w-full">
          <div>
            <p class="font-medium">正在配置：<span class="text-blue-600">{{ currentBatchDisplayName }}</span></p>
            <p class="text-xs mt-1">请核对自动识别的模板配置，确认无误后点击「保存并继续」配置下一个文件</p>
          </div>
          <div class="flex gap-2 ml-4">
            <el-button size="small" @click="skipBatchFile">跳过此文件</el-button>
            <el-button size="small" type="danger" @click="cancelBatch">取消向导</el-button>
          </div>
        </div>
      </template>
    </el-alert>

    <template #header>
      <div class="flex justify-between items-center">
        <span class="text-lg font-semibold">
          {{ batchMode ? '批量模板配置向导' : '社保公积金导入模板配置' }}
        </span>
        <div class="flex gap-2" v-if="!batchMode">
          <el-button type="success" :icon="Upload" size="small" @click="triggerUpload">上传文件自动识别</el-button>
          <el-button type="primary" :icon="Plus" size="small" @click="showDialog(null)">新增模板</el-button>
        </div>
        <div class="flex gap-2" v-else>
          <el-tag type="info">待配置：{{ batchUnmatchedFiles.length - currentBatchIndex - skippedBatchCount }} 个</el-tag>
          <el-tag type="success">已完成：{{ currentBatchIndex + skippedBatchCount }} 个</el-tag>
        </div>
      </div>
    </template>

    <div class="bg-blue-50 rounded-lg p-3 mb-4 text-sm text-gray-600" v-if="!batchMode">
      <el-icon class="mr-1"><InfoFilled /></el-icon>
      配置不同政务平台导出的社保/公积金文件解析规则。配置后，「智能导入」即可自动识别并解析对应格式的文件。
    <span class="text-blue-600 font-medium ml-2">推荐：上传一份样本文件，系统自动提取列名，您手动配置字段映射后保存即可。</span>
    </div>

    <el-table :data="templates" border stripe v-loading="loading" v-if="!batchMode">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="模板名称" width="160" />
      <el-table-column prop="source_category" label="数据类别" width="110">
        <template #default="{ row }">
          <el-tag :type="row.source_category === 'social_insurance' ? '' : 'success'" size="small">
            {{ row.source_category === 'social_insurance' ? '社保' : '公积金' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="file_type" label="文件类型" width="80">
        <template #default="{ row }">
          <el-tag :type="row.file_type === 'excel' ? 'warning' : 'danger'" size="small">
            {{ row.file_type.toUpperCase() }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="city" label="城市" width="80" />
      <el-table-column prop="description" label="说明" min-width="150" show-overflow-tooltip />
      <el-table-column label="数据起始行" width="110">
        <template #default="{ row }">
          第{{ (row.data_start_row || 0) + 1 }}行
        </template>
      </el-table-column>
      <el-table-column label="映射字段数" width="90">
        <template #default="{ row }">
          {{ row.column_mappings ? Object.keys(row.column_mappings).length : 0 }}
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="启用" width="65">
        <template #default="{ row }">
          <el-switch :model-value="row.is_active" size="small" disabled />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-link type="primary" :underline="false" class="mr-2" @click="showDialog(row)">编辑</el-link>
          <el-link type="danger" :underline="false" @click="handleDelete(row)">删除</el-link>
        </template>
      </el-table-column>
    </el-table>

    <!-- 隐藏的文件上传 -->
    <input
      ref="fileInputRef"
      type="file"
      accept=".xlsx,.xls,.pdf"
      style="display: none"
      @change="handleFileChange"
    />

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="getDialogTitle()"
      width="800px"
      append-to-body
      :close-on-click-modal="batchMode ? false : true"
      :show-close="!batchMode"
      @close="onDialogClose"
    >
      <!-- 批量模式提示 -->
      <el-alert
        v-if="batchMode"
        :title="`正在配置「${currentBatchDisplayName}」的模板（第 ${currentBatchIndex + 1}/${batchUnmatchedFiles.length} 个）`"
        type="info"
        :closable="false"
        show-icon
        class="mb-4"
      />
      <!-- 自动识别结果提示 -->
      <el-alert
        v-else-if="isAutoDetected"
        :title="`已根据上传文件自动识别配置。${autoMatchStats}，请核对以下信息是否正确，可手动调整后保存。`"
        type="success"
        :closable="false"
        show-icon
        class="mb-4"
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="right">
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="模板名称" prop="name">
              <el-input v-model="form.name" placeholder="如：邯郸公积金" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="数据类别" prop="source_category">
              <el-select v-model="form.source_category" class="w-full">
                <el-option label="社保" value="social_insurance" />
                <el-option label="公积金" value="housing_fund" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="文件类型" prop="file_type">
              <el-select v-model="form.file_type" class="w-full">
                <el-option label="Excel" value="excel" />
                <el-option label="PDF" value="pdf" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="城市">
              <el-input v-model="form.city" placeholder="如：邯郸" />
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item>
              <template #label>
                <span>
                  文件名匹配
                  <el-tooltip
                    content="系统通过文件名来判断该文件应该使用哪个模板。如文件名叫「邯郸公积金缴费明细.xlsx」，模板中配置了关键词「邯郸」「公积金」，系统就会自动使用这个模板来解析文件。"
                    placement="top"
                  >
                    <el-icon class="ml-1 cursor-help text-gray-400"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <div class="w-full">
                <el-select
                  v-model="form.file_keywords"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="输入关键词后按回车，如：邯郸 公积金"
                  class="w-full"
                  :reserve-keyword="false"
                >
                </el-select>
                <div class="text-xs text-gray-400 mt-1">
                  <template v-if="form.file_keywords.length > 0">
                    文件名中须同时包含：
                    <el-tag v-for="kw in form.file_keywords" :key="kw" size="small" type="info" effect="plain" class="mx-0.5">{{ kw }}</el-tag>
                    才匹配此模板
                  </template>
                  <template v-else>
                    输入文件名中包含的关键词。例如文件叫「邯郸公积金缴费明细.xlsx」，输入「邯郸」「公积金」即可。
                  </template>
                </div>
                <el-collapse-transition>
                  <div v-if="showAdvanced" class="mt-2">
                    <el-input v-model="form.file_pattern" placeholder="正则表达式（高级），如：养老保险|单位缴纳" size="small" />
                    <div class="text-xs text-gray-400 mt-1">高级用户可选：使用正则表达式匹配文件名。留空则使用关键词模式。</div>
                  </div>
                </el-collapse-transition>
                <el-button link type="primary" size="small" class="mt-1 p-0" @click="showAdvanced = !showAdvanced">
                  {{ showAdvanced ? '收起高级选项' : '高级选项（正则匹配）' }}
                </el-button>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item>
              <template #label>
                <span>
                  工作表匹配
                  <el-tooltip
                    content="Excel 文件包含多个工作表时，通过工作表的名称来判断应该读取哪个工作表。通常不需要设置；只有当文件有多个工作表时才需要配置。"
                    placement="top"
                  >
                    <el-icon class="ml-1 cursor-help text-gray-400"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </span>
              </template>
              <el-input v-model="form.sheet_pattern" placeholder="工作表名关键词" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="说明">
              <el-input v-model="form.description" placeholder="模板用途说明，如：邯郸社保分险种文件，表头为通用列名，文件名包含险种和缴纳方向" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">解析配置</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="表头行号" prop="header_rows_str">
              <el-input v-model="form.header_rows_str" placeholder="如：1（第一行是表头）" />
              <div class="text-xs text-gray-400 mt-1">输入Excel中表头所在的行号。多层表头用逗号分隔，如「1,2」表示前两行合并为表头</div>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数据起始行" prop="data_start_row">
              <el-input-number v-model="form.data_start_row" :min="1" class="w-full" />
              <div class="text-xs text-gray-400 mt-1">第一条员工数据从第几行开始（表头之后的第一行）</div>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="跳过末尾行">
              <el-input-number v-model="form.skip_footer_rows" :min="0" class="w-full" />
              <div class="text-xs text-gray-400 mt-1">跳过文件末尾的合计行、备注行等</div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">字段映射（文件列名 → 系统字段）</el-divider>
        <div class="mb-2">
          <el-button size="small" type="primary" :icon="Plus" @click="addMapping">添加映射</el-button>
          <span class="text-xs text-gray-400 ml-2">将文件中的列名对应到系统字段</span>
        </div>

        <div class="mb-3 p-3 bg-blue-50 rounded-lg text-xs">
          <div class="flex items-start gap-2">
            <el-icon class="text-blue-600 mt-0.5"><InfoFilled /></el-icon>
            <div>
              <p class="font-medium text-blue-700 mb-1">💡 两种配置方式：</p>
              <p class="text-gray-600 mb-1">
                <span class="font-medium">① 指定险种模板：</span>直接选择具体险种字段（如"医疗保险个人基数"）。适用于文件内容固定为某一险种的场景。
              </p>
              <p class="text-gray-600">
                <span class="font-medium">② 通用险种模板（推荐用于多险种同格式场景）：</span>选择<span class="text-amber-600 font-medium">[通用]</span>开头的字段，系统将<span class="font-medium">根据文件名自动识别险种</span>。例如邯郸社保：养老/失业/医疗/工伤文件格式相同，但文件名含"养老""医疗"等关键词，只需配置1个通用模板即可适配所有险种文件。
              </p>
            </div>
          </div>
        </div>

        <div v-if="hasGenericMappings" class="mb-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
          <el-icon class="mr-1"><WarningFilled /></el-icon>
          此模板包含通用险种映射字段，系统将根据文件名自动识别险种和缴纳方向。<span class="font-medium">请确保文件名关键词不要限定单一险种</span>（应使用"邯郸 社保"等通用词，让"养老""医疗"等词保留在文件名中供自动识别）。
        </div>

        <template v-if="form.mapping_list.length > 0">
          <div
            v-for="item in form.mapping_list"
            :key="item.flatIndex"
            class="flex gap-2 mb-2 items-center mapping-row"
            :class="{ 'mapping-matched': item.db_field, 'mapping-generic': isGenericField(item.db_field) }"
          >
            <el-input v-model="item.header_name" placeholder="文件中的列名" class="flex-1" size="small" />
            <span class="text-gray-400">→</span>
            <el-select v-model="item.db_field" placeholder="系统字段" class="flex-1" size="small" filterable clearable>
              <el-option label="未映射（留空）" :value="null" />
              <el-option-group label="通用字段（文件名自动识别险种）">
                <el-option v-for="(label, key) in genericFieldLabels" :key="key" :label="label" :value="key" />
              </el-option-group>
              <el-option-group label="基础信息">
                <el-option v-for="(label, key) in fieldGroups.basic" :key="key" :label="label" :value="key" />
              </el-option-group>
              <el-option-group label="养老保险">
                <el-option v-for="(label, key) in fieldGroups.pension" :key="key" :label="label" :value="key" />
              </el-option-group>
              <el-option-group label="失业保险">
                <el-option v-for="(label, key) in fieldGroups.unemployment" :key="key" :label="label" :value="key" />
              </el-option-group>
              <el-option-group label="医疗保险">
                <el-option v-for="(label, key) in fieldGroups.medical" :key="key" :label="label" :value="key" />
              </el-option-group>
              <el-option-group label="工伤保险">
                <el-option v-for="(label, key) in fieldGroups.injury" :key="key" :label="label" :value="key" />
              </el-option-group>
              <el-option-group label="社保汇总">
                <el-option v-for="(label, key) in fieldGroups.si_summary" :key="key" :label="label" :value="key" />
              </el-option-group>
              <el-option-group label="公积金">
                <el-option v-for="(label, key) in fieldGroups.hf" :key="key" :label="label" :value="key" />
              </el-option-group>
              <el-option-group label="合计">
                <el-option v-for="(label, key) in fieldGroups.totals" :key="key" :label="label" :value="key" />
              </el-option-group>
            </el-select>
            <el-tag v-if="item.db_field" size="small" :type="isGenericField(item.db_field) ? 'warning' : 'success'" effect="plain" class="shrink-0">
              {{ isGenericField(item.db_field) ? '通用' : '已匹配' }}
            </el-tag>
            <el-button :icon="Delete" size="small" type="danger" circle @click="removeMapping(item.flatIndex)" />
          </div>
        </template>
        <el-empty v-if="form.mapping_list.length === 0" description="暂无字段映射，请点击「添加映射」" :image-size="40" />

        <el-divider content-position="left">默认缴纳比例配置（用于数据推算）</el-divider>
        <div class="bg-blue-50 rounded-lg p-3 mb-3 text-xs text-gray-600">
          <el-icon class="mr-1"><InfoFilled /></el-icon>
          配置当地各险种和公积金的默认缴纳比例。当导入文件中缺少比例数据、或只有合计金额时，系统将使用此处配置的比例自动推算缺失的基数、金额和比例。<span class="text-blue-600 font-medium">比例请输入百分比数值，如8%输入8。</span>
        </div>
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="border border-gray-200 rounded-lg p-3 mb-2">
              <div class="font-medium text-sm mb-2 text-gray-700">养老保险</div>
              <el-row :gutter="8">
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">个人比例</span>
                    <el-input-number v-model="form.default_rates.pension.personal_rate_pct" :min="0" :max="100" :step="0.1" :precision="2" size="small" class="flex-1" controls-position="right" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">单位比例</span>
                    <el-input-number v-model="form.default_rates.pension.company_rate_pct" :min="0" :max="100" :step="0.1" :precision="2" size="small" class="flex-1" controls-position="right" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
              </el-row>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="border border-gray-200 rounded-lg p-3 mb-2">
              <div class="font-medium text-sm mb-2 text-gray-700">失业保险</div>
              <el-row :gutter="8">
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">个人比例</span>
                    <el-input-number v-model="form.default_rates.unemployment.personal_rate_pct" :min="0" :max="100" :step="0.1" :precision="2" size="small" class="flex-1" controls-position="right" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">单位比例</span>
                    <el-input-number v-model="form.default_rates.unemployment.company_rate_pct" :min="0" :max="100" :step="0.1" :precision="2" size="small" class="flex-1" controls-position="right" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
              </el-row>
            </div>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="border border-gray-200 rounded-lg p-3 mb-2">
              <div class="font-medium text-sm mb-2 text-gray-700">医疗保险</div>
              <el-row :gutter="8">
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">个人比例</span>
                    <el-input-number v-model="form.default_rates.medical.personal_rate_pct" :min="0" :max="100" :step="0.1" :precision="2" size="small" class="flex-1" controls-position="right" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">单位比例</span>
                    <el-input-number v-model="form.default_rates.medical.company_rate_pct" :min="0" :max="100" :step="0.1" :precision="2" size="small" class="flex-1" controls-position="right" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
              </el-row>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="border border-gray-200 rounded-lg p-3 mb-2">
              <div class="font-medium text-sm mb-2 text-gray-700">工伤保险</div>
              <el-row :gutter="8">
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">个人比例</span>
                    <span class="text-xs text-gray-400">（无需缴纳）</span>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">单位比例</span>
                    <el-input-number v-model="form.default_rates.injury.company_rate_pct" :min="0" :max="100" :step="0.01" :precision="3" size="small" class="flex-1" controls-position="right" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
              </el-row>
            </div>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="border border-gray-200 rounded-lg p-3 mb-2">
              <div class="font-medium text-sm mb-2 text-gray-700">住房公积金</div>
              <el-row :gutter="8">
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">个人比例</span>
                    <el-input-number v-model="form.default_rates.hf.personal_rate_pct" :min="0" :max="100" :step="1" :precision="1" size="small" class="flex-1" controls-position="right" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-gray-500 w-16">单位比例</span>
                    <el-input-number v-model="form.default_rates.hf.company_rate_pct" :min="0" :max="100" :step="1" :precision="1" size="small" class="flex-1" controls-position="right" :disabled="form.default_rates.hf.split_equal" />
                    <span class="text-xs text-gray-400">%</span>
                  </div>
                </el-col>
              </el-row>
              <div class="mt-2">
                <el-checkbox v-model="form.default_rates.hf.split_equal" size="small">个人与单位比例相同（自动同步）</el-checkbox>
              </div>
              <div class="text-xs text-gray-400 mt-1">
                示例：邯郸公积金个人和单位比例均为10%，只知道合计金额时系统将自动拆分个人/单位金额并反推缴存基数。
              </div>
            </div>
          </el-col>
        </el-row>

        <el-divider content-position="left">高级配置</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="行过滤条件">
              <div class="w-full">
                <div v-for="(item, index) in form.filter_list" :key="index" class="flex gap-2 mb-1">
                  <el-input v-model="item.col" placeholder="列名" size="small" class="w-1/3" />
                  <el-select v-model="item.op" size="small" class="w-1/4">
                    <el-option label="等于" value="=" />
                    <el-option label="不等于" value="!=" />
                  </el-select>
                  <el-input v-model="item.val" placeholder="值" size="small" class="flex-1" />
                  <el-button :icon="Delete" size="small" type="danger" circle @click="form.filter_list.splice(index, 1)" />
                </div>
                <el-button size="small" :icon="Plus" @click="form.filter_list.push({ col: '', op: '=', val: '' })">添加过滤条件</el-button>
                <div class="text-xs text-gray-400 mt-1">仅导入满足条件的行，如：缴存状态 = 正常</div>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数值解析">
              <el-input v-model="form.remove_chars" placeholder="需去除的字符，逗号分隔" size="small" />
              <div class="text-xs text-gray-400 mt-1">如：,（去除金额中的逗号和百分号）</div>
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="form.is_active" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <template v-if="!batchMode">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </template>
        <template v-else>
          <el-button @click="skipBatchFile">跳过此文件</el-button>
          <el-button type="primary" :loading="saving" @click="handleBatchSave">
            {{ isLastBatchFile ? '保存并执行导入' : '保存并继续下一个' }}
          </el-button>
        </template>
      </template>
    </el-dialog>

    <!-- 批量配置完成弹窗 -->
    <el-dialog
      v-model="batchCompleteVisible"
      title="模板配置完成"
      width="500px"
      append-to-body
      :close-on-click-modal="false"
    >
      <div class="text-center py-4">
        <el-icon class="text-5xl text-green-500 mb-4"><CircleCheckFilled /></el-icon>
        <p class="text-lg font-medium mb-2">所有文件模板配置完成！</p>
        <p class="text-gray-500 text-sm">共处理 {{ batchUnmatchedFiles.length }} 个文件，已配置 {{ savedBatchCount }} 个模板，跳过 {{ skippedBatchCount }} 个文件</p>
      </div>
      <template #footer>
        <el-button @click="cancelBatch">返回模板列表</el-button>
        <el-button type="primary" @click="executeBatchImport">返回并执行导入</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, InfoFilled, Upload, QuestionFilled, WarningFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import api from '../../api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const isAutoDetected = ref(false)
const showAdvanced = ref(false)
const editId = ref(null)
const templates = ref([])
const fieldLabels = ref({})
const formRef = ref(null)
const fileInputRef = ref(null)

// 批量配置向导状态
const batchMode = ref(false)
const batchId = ref(null)
const batchUnmatchedFiles = ref([])
const currentBatchIndex = ref(0)
const skippedBatchCount = ref(0)
const savedBatchCount = ref(0)
const batchCompleteVisible = ref(false)
const autoDetecting = ref(false)

// 通用字段（用于文件名险种推断，中文标签）
// 【使用方法】当多个险种（养老/失业/医疗/工伤）的文件格式完全相同时（如邯郸社保），
// 将列映射到 [通用] 字段，系统会根据文件名中的关键词自动识别险种：
//   - 文件名含"养老"→养老保险、"失业"→失业保险、"医疗"→医疗保险、"工伤"→工伤保险
//   - 文件名含"个人"→个人部分、"单位"/"企业"→单位部分
// 例如：文件叫"邯郸养老保险个人.xlsx"，[通用]缴费基数 → 养老保险个人基数
const genericFieldLabels = {
  amount_base: '[通用] 缴费基数（文件名含个人/单位）',
  rate: '[通用] 费率/比例（文件名含个人/单位）',
  amount: '[通用] 应缴费额（文件名含个人/单位）',
  personal_base: '[通用·个人] 缴费基数',
  personal_amount: '[通用·个人] 应缴费额',
  personal_rate: '[通用·个人] 费率/比例',
  company_base: '[通用·单位] 缴费基数',
  company_amount: '[通用·单位] 应缴费额',
  company_rate: '[通用·单位] 费率/比例',
}

const GENERIC_FIELDS = new Set(Object.keys(genericFieldLabels))

function isGenericField(field) {
  return GENERIC_FIELDS.has(field)
}

// 字段分组配置
const fieldGroups = computed(() => {
  const labels = fieldLabels.value
  return {
    basic: {
      employee_name: labels.employee_name,
      employee_social_insurance_no: labels.employee_social_insurance_no,
    },
    pension: {
      pension_personal_base: labels.pension_personal_base,
      pension_company_base: labels.pension_company_base,
      pension_personal: labels.pension_personal,
      pension_personal_rate: labels.pension_personal_rate,
      pension_company: labels.pension_company,
      pension_company_rate: labels.pension_company_rate,
    },
    unemployment: {
      unemployment_personal_base: labels.unemployment_personal_base,
      unemployment_company_base: labels.unemployment_company_base,
      unemployment_personal: labels.unemployment_personal,
      unemployment_personal_rate: labels.unemployment_personal_rate,
      unemployment_company: labels.unemployment_company,
      unemployment_company_rate: labels.unemployment_company_rate,
    },
    medical: {
      medical_personal_base: labels.medical_personal_base,
      medical_company_base: labels.medical_company_base,
      medical_personal: labels.medical_personal,
      medical_personal_rate: labels.medical_personal_rate,
      medical_company: labels.medical_company,
      medical_company_rate: labels.medical_company_rate,
    },
    injury: {
      injury_company_base: labels.injury_company_base,
      injury_company: labels.injury_company,
      injury_company_rate: labels.injury_company_rate,
    },
    si_summary: {
      si_personal: labels.si_personal,
      si_company: labels.si_company,
    },
    hf: {
      hf_base: labels.hf_base,
      hf_personal: labels.hf_personal,
      hf_personal_rate: labels.hf_personal_rate,
      hf_company: labels.hf_company,
      hf_company_rate: labels.hf_company_rate,
    },
    totals: {
      pension_total: labels.pension_total,
      unemployment_total: labels.unemployment_total,
      medical_total: labels.medical_total,
      injury_total: labels.injury_total,
      si_grand_total: labels.si_grand_total,
      hf_total: labels.hf_total,
      grand_total: labels.grand_total,
    },
  }
})

// 检查是否有通用字段映射
const hasGenericMappings = computed(() => {
  return form.mapping_list.some(item => isGenericField(item.db_field))
})

// 批量模式计算属性
const currentBatchFile = computed(() => {
  if (batchMode.value && batchUnmatchedFiles.value.length > currentBatchIndex.value) {
    return batchUnmatchedFiles.value[currentBatchIndex.value]
  }
  return null
})

const currentBatchDisplayName = computed(() => {
  if (!currentBatchFile.value) return ''
  return currentBatchFile.value.display_name || currentBatchFile.value.filename
})

const isLastBatchFile = computed(() => {
  return currentBatchIndex.value >= batchUnmatchedFiles.value.length - 1
})

function getDialogTitle() {
  if (batchMode.value) {
    return `批量配置模板 - ${currentBatchDisplayName.value || ''}`
  }
  if (isEdit.value) return '编辑模板'
  if (isAutoDetected.value) return '核对自动识别结果'
  return '新增模板'
}

const rules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  source_category: [{ required: true, message: '请选择数据类别', trigger: 'change' }],
  file_type: [{ required: true, message: '请选择文件类型', trigger: 'change' }],
  header_rows_str: [{ required: true, message: '请输入表头行号', trigger: 'blur' }],
  data_start_row: [{ required: true, message: '请输入数据起始行', trigger: 'blur' }],
}

function createEmptyDefaultRates() {
  return {
    pension: { personal_rate_pct: null, company_rate_pct: null },
    unemployment: { personal_rate_pct: null, company_rate_pct: null },
    medical: { personal_rate_pct: null, company_rate_pct: null },
    injury: { company_rate_pct: null },
    hf: { personal_rate_pct: null, company_rate_pct: null, split_equal: true },
  }
}

const form = reactive({
  name: '',
  source_category: 'social_insurance',
  file_type: 'excel',
  city: '',
  description: '',
  file_keywords: [],
  file_pattern: '',
  sheet_pattern: '',
  header_rows_str: '1',
  data_start_row: 2,
  skip_footer_rows: 0,
  mapping_list: [],
  filter_list: [],
  remove_chars: '',
  default_rates: createEmptyDefaultRates(),
  is_active: true,
})

// ── 加载数据 ──
async function fetchTemplates() {
  loading.value = true
  try {
    const res = await api.get('/social-insurance/templates')
    templates.value = res.data
  } finally {
    loading.value = false
  }
}

async function fetchFieldLabels() {
  try {
    const res = await api.get('/social-insurance/field-labels')
    fieldLabels.value = res.data
  } catch {
    // 字段标签获取失败不影响模板管理
  }
}

onMounted(() => {
  fetchTemplates()
  fetchFieldLabels()
  initBatchModeFromRoute()
})

// 监听路由变化，处理批量向导
watch(() => route.query.batch_id, (newBatchId) => {
  if (newBatchId) {
    initBatchMode(newBatchId)
  } else if (batchMode.value) {
    exitBatchMode()
  }
})

// ── 批量配置向导方法 ──
async function initBatchModeFromRoute() {
  const batchIdParam = route.query.batch_id
  if (batchIdParam) {
    await initBatchMode(batchIdParam)
  }
}

async function initBatchMode(b_id) {
  try {
    loading.value = true
    const res = await api.get(`/social-insurance/smart-import-batch/${b_id}`)
    const data = res.data

    batchId.value = b_id
    batchUnmatchedFiles.value = data.unmatched_files || []
    currentBatchIndex.value = 0
    skippedBatchCount.value = 0
    savedBatchCount.value = 0
    batchCompleteVisible.value = false

    if (batchUnmatchedFiles.value.length === 0) {
      ElMessage.info('所有文件都已匹配到模板，无需配置')
      router.replace({ name: 'InsuranceTemplate' })
      return
    }

    batchMode.value = true
    loading.value = false

    await loadCurrentBatchFile()
  } catch (e) {
    console.error('初始化批量模式失败：', e)
    ElMessage.error('批量配置向导初始化失败，可能是会话已过期')
    router.replace({ name: 'InsuranceTemplate' })
  } finally {
    loading.value = false
  }
}

async function loadCurrentBatchFile() {
  if (!currentBatchFile.value) {
    finishBatch()
    return
  }

  autoDetecting.value = true
  try {
    const fileIdx = currentBatchFile.value.index
    const sheetName = currentBatchFile.value.sheet_name
    let url = `/social-insurance/templates/auto-detect-batch/${batchId.value}/${fileIdx}`
    if (sheetName) {
      url += `?sheet_name=${encodeURIComponent(sheetName)}`
    }
    const res = await api.get(url)
    const detected = res.data
    applyDetectedConfig(detected)
    isEdit.value = false
    isAutoDetected.value = true
    editId.value = null
    dialogVisible.value = true
  } catch (e) {
    console.error('自动识别失败：', e)
    ElMessage.error(`文件「${currentBatchDisplayName.value}」自动识别失败，请手动配置`)
    resetForm()
    isEdit.value = false
    isAutoDetected.value = false
    editId.value = null
    dialogVisible.value = true
  } finally {
    autoDetecting.value = false
  }
}

async function handleBatchSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (form.mapping_list.length === 0) {
    ElMessage.warning('请至少添加一个字段映射')
    return
  }

  const column_mappings = {}
  form.mapping_list.forEach(item => {
    if (item.header_name) {
      column_mappings[item.header_name] = item.db_field || null
    }
  })
  if (Object.keys(column_mappings).length === 0) {
    ElMessage.warning('字段映射不完整，请检查')
    return
  }
  const hasValidMapping = Object.values(column_mappings).some(v => v !== null)
  if (!hasValidMapping) {
    ElMessage.warning('请至少为一个字段设置系统映射')
    return
  }

  const row_filters = {}
  form.filter_list.forEach(item => {
    if (item.col && item.val) {
      row_filters[item.col] = item.val
    }
  })

  const remove_chars = form.remove_chars.split(',').map(s => s.trim()).filter(Boolean)
  const number_format = remove_chars.length > 0 ? { remove_chars } : null

  const header_rows = form.header_rows_str.split(',')
    .map(s => parseInt(s.trim()) - 1)
    .filter(n => !isNaN(n) && n >= 0)

  const default_rates = defaultRatesToApi(form.default_rates)

  const payload = {
    name: form.name,
    source_category: form.source_category,
    file_type: form.file_type,
    city: form.city || null,
    description: form.description || null,
    file_pattern: form.file_pattern || null,
    file_keywords: form.file_keywords.length > 0 ? form.file_keywords : null,
    sheet_pattern: form.sheet_pattern || null,
    header_rows,
    data_start_row: form.data_start_row - 1,
    skip_footer_rows: form.skip_footer_rows,
    column_mappings,
    row_filters: Object.keys(row_filters).length > 0 ? row_filters : null,
    number_format,
    default_rates,
    is_active: form.is_active,
  }

  saving.value = true
  try {
    await api.post('/social-insurance/templates', payload)
    savedBatchCount.value++
    ElMessage.success(`模板「${form.name}」保存成功`)
    dialogVisible.value = false
    await fetchTemplates()
    nextBatchFile()
  } catch (e) {
    // error handled by interceptor
  } finally {
    saving.value = false
  }
}

function skipBatchFile() {
  skippedBatchCount.value++
  dialogVisible.value = false
  nextBatchFile()
}

function nextBatchFile() {
  currentBatchIndex.value++
  if (currentBatchIndex.value >= batchUnmatchedFiles.value.length) {
    finishBatch()
  } else {
    loadCurrentBatchFile()
  }
}

function finishBatch() {
  dialogVisible.value = false
  batchCompleteVisible.value = true
}

function exitBatchMode() {
  batchMode.value = false
  batchId.value = null
  batchUnmatchedFiles.value = []
  currentBatchIndex.value = 0
  skippedBatchCount.value = 0
  savedBatchCount.value = 0
  batchCompleteVisible.value = false
  dialogVisible.value = false
}

function cancelBatch() {
  exitBatchMode()
  api.post(`/social-insurance/smart-import-batch/${batchId.value}/cancel`).catch(() => {})
  router.push({ name: 'Insurance' })
}

async function executeBatchImport() {
  try {
    const period = route.query.period
    router.push({
      name: 'Insurance',
      query: {
        execute_batch: batchId.value,
        period: period
      }
    })
  } catch (e) {
    console.error('跳转失败：', e)
  }
}

function onDialogClose() {
  if (!batchMode.value) {
    resetForm()
  }
}

// ── 上传文件自动识别 ──
function triggerUpload() {
  fileInputRef.value?.click()
}

async function handleFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  loading.value = true
  try {
    const res = await api.post('/social-insurance/templates/auto-detect', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    const detected = res.data
    applyDetectedConfig(detected)
    const total = Object.keys(detected.column_mappings || {}).length
    const matched = Object.values(detected.column_mappings || {}).filter(v => v).length
    ElMessage.success(`文件解析完成，共识别 ${total} 个字段，${matched > 0 ? `已自动匹配 ${matched} 个` : '请在下方手动配置字段映射'}`)
  } catch (e) {
    // error handled by interceptor
  } finally {
    loading.value = false
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
  }
}

function pctToDecimal(pct) {
  if (pct === null || pct === undefined || pct === '') return null
  return Math.round(parseFloat(pct) * 100) / 10000  // 8% → 0.08
}

function decimalToPct(dec) {
  if (dec === null || dec === undefined) return null
  return Math.round(parseFloat(dec) * 10000) / 100  // 0.08 → 8
}

function defaultRatesFromApi(apiRates) {
  const result = createEmptyDefaultRates()
  if (!apiRates) return result
  for (const [insKey, rates] of Object.entries(apiRates)) {
    if (result[insKey]) {
      if (rates.personal_rate !== undefined && rates.personal_rate !== null) {
        result[insKey].personal_rate_pct = decimalToPct(rates.personal_rate)
      }
      if (rates.company_rate !== undefined && rates.company_rate !== null) {
        result[insKey].company_rate_pct = decimalToPct(rates.company_rate)
      }
      if (rates.split_equal !== undefined) {
        result[insKey].split_equal = rates.split_equal
      }
    }
  }
  return result
}

function defaultRatesToApi(formRates) {
  const result = {}
  for (const [insKey, rates] of Object.entries(formRates)) {
    const entry = {}
    const pPct = rates.personal_rate_pct
    const cPct = rates.company_rate_pct
    if (pPct !== null && pPct !== undefined && pPct !== '') {
      entry.personal_rate = pctToDecimal(pPct)
    }
    if (cPct !== null && cPct !== undefined && cPct !== '') {
      entry.company_rate = pctToDecimal(cPct)
    }
    if (rates.split_equal !== undefined) {
      entry.split_equal = rates.split_equal
    }
    if (Object.keys(entry).length > 0) {
      result[insKey] = entry
    }
  }
  return Object.keys(result).length > 0 ? result : null
}

function applyDetectedConfig(detected) {
  isEdit.value = false
  isAutoDetected.value = true
  editId.value = null

  form.name = detected.name || ''
  form.source_category = detected.source_category || 'social_insurance'
  form.file_type = detected.file_type || 'excel'
  form.city = detected.city || ''
  form.description = detected.description || ''
  if (detected.file_keywords && detected.file_keywords.length > 0) {
    form.file_keywords = detected.file_keywords || []
    form.file_pattern = ''
    showAdvanced.value = false
  } else if (detected.file_pattern) {
    form.file_keywords = []
    form.file_pattern = detected.file_pattern || ''
    showAdvanced.value = true
  } else {
    form.file_keywords = []
    form.file_pattern = ''
    showAdvanced.value = false
  }
  form.sheet_pattern = detected.sheet_pattern || ''
  // 后端返回0-based行号，前端显示1-based（Excel实际行号），+1转换
  form.header_rows_str = ((detected.header_rows || []).map(r => r + 1)).join(',')
  form.data_start_row = (detected.data_start_row || 0) + 1
  form.skip_footer_rows = detected.skip_footer_rows || 0
  form.is_active = true
  form.default_rates = defaultRatesFromApi(detected.default_rates)

  // 列映射
  form.mapping_list = Object.entries(detected.column_mappings || {}).map(([k, v]) => ({
    header_name: k,
    db_field: v,
  }))
  // 附加 flatIndex
  form.mapping_list.forEach((item, idx) => { item.flatIndex = idx })

  // 行过滤
  form.filter_list = Object.entries(detected.row_filters || {}).map(([k, v]) => ({
    col: k,
    op: '=',
    val: v,
  }))

  // 数值解析
  form.remove_chars = (detected.number_format?.remove_chars || []).join(',')

  dialogVisible.value = true
}

// ── 弹窗操作 ──
function showDialog(row) {
  isEdit.value = !!row
  isAutoDetected.value = false
  editId.value = row?.id || null

  if (row) {
    form.name = row.name
    form.source_category = row.source_category
    form.file_type = row.file_type
    form.city = row.city || ''
    form.description = row.description || ''
    if (row.file_keywords && row.file_keywords.length > 0) {
      form.file_keywords = row.file_keywords || []
      form.file_pattern = ''
      showAdvanced.value = !!row.file_pattern
    } else if (row.file_pattern) {
      form.file_keywords = []
      form.file_pattern = row.file_pattern || ''
      showAdvanced.value = true
    } else {
      form.file_keywords = []
      form.file_pattern = ''
      showAdvanced.value = false
    }
    form.sheet_pattern = row.sheet_pattern || ''
    // 后端返回0-based行号，前端显示1-based（Excel实际行号），+1转换
    form.header_rows_str = ((row.header_rows || []).map(r => r + 1)).join(',')
    form.data_start_row = (row.data_start_row || 0) + 1
    form.skip_footer_rows = row.skip_footer_rows || 0
    form.is_active = row.is_active
    form.default_rates = defaultRatesFromApi(row.default_rates)

    // 列映射 → mapping_list
    form.mapping_list = Object.entries(row.column_mappings || {}).map(([k, v]) => ({
      header_name: k,
      db_field: v,
    }))
    form.mapping_list.forEach((item, idx) => { item.flatIndex = idx })

    // 行过滤 → filter_list
    form.filter_list = Object.entries(row.row_filters || {}).map(([k, v]) => ({
      col: k,
      op: '=',
      val: v,
    }))

    // number_format → remove_chars
    form.remove_chars = (row.number_format?.remove_chars || []).join(',')
  } else {
    resetForm()
  }
  dialogVisible.value = true
}

function resetForm() {
  form.name = ''
  form.source_category = 'social_insurance'
  form.file_type = 'excel'
  form.city = ''
  form.description = ''
  form.file_keywords = []
  form.file_pattern = ''
  form.sheet_pattern = ''
  form.header_rows_str = '1'
  form.data_start_row = 2
  form.skip_footer_rows = 0
  form.mapping_list = []
  form.filter_list = []
  form.remove_chars = ''
  form.default_rates = createEmptyDefaultRates()
  form.is_active = true
  showAdvanced.value = false
  isAutoDetected.value = false
  formRef.value?.resetFields()
}

// ── 公积金比例联动 ──
// watch split_equal for hf - 当勾选"比例相同"时，单位比例跟随个人比例
watch(
  () => [form.default_rates.hf.split_equal, form.default_rates.hf.personal_rate_pct],
  ([equal, pPct]) => {
    if (equal && pPct !== null && pPct !== undefined) {
      form.default_rates.hf.company_rate_pct = pPct
    }
  }
)

// ── 映射操作 ──
function addMapping() {
  form.mapping_list.push({ header_name: '', db_field: 'employee_name' })
  form.mapping_list.forEach((item, idx) => { item.flatIndex = idx })
}

function removeMapping(flatIndex) {
  form.mapping_list.splice(flatIndex, 1)
  form.mapping_list.forEach((item, idx) => { item.flatIndex = idx })
}

// 自动匹配统计
const autoMatchStats = computed(() => {
  if (!isAutoDetected.value) return ''
  const total = form.mapping_list.length
  const matched = form.mapping_list.filter(item => item.db_field).length
  return `AI 已自动匹配 ${matched}/${total} 个字段`
})

// ── 保存 ──
async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (form.mapping_list.length === 0) {
    ElMessage.warning('请至少添加一个字段映射')
    return
  }

  // 构建 column_mappings
  const column_mappings = {}
  form.mapping_list.forEach(item => {
    if (item.header_name) {
      column_mappings[item.header_name] = item.db_field || null
    }
  })
  if (Object.keys(column_mappings).length === 0) {
    ElMessage.warning('字段映射不完整，请检查')
    return
  }
  const hasValidMapping = Object.values(column_mappings).some(v => v !== null)
  if (!hasValidMapping) {
    ElMessage.warning('请至少为一个字段设置系统映射')
    return
  }

  // 构建 row_filters
  const row_filters = {}
  form.filter_list.forEach(item => {
    if (item.col && item.val) {
      row_filters[item.col] = item.val
    }
  })

  // 构建 number_format
  const remove_chars = form.remove_chars.split(',').map(s => s.trim()).filter(Boolean)
  const number_format = remove_chars.length > 0 ? { remove_chars } : null

  // 解析 header_rows（前端显示1-based，转成后端0-based，-1转换）
  const header_rows = form.header_rows_str.split(',')
    .map(s => parseInt(s.trim()) - 1)
    .filter(n => !isNaN(n) && n >= 0)

  // 构建 default_rates
  const default_rates = defaultRatesToApi(form.default_rates)

  const payload = {
    name: form.name,
    source_category: form.source_category,
    file_type: form.file_type,
    city: form.city || null,
    description: form.description || null,
    file_pattern: form.file_pattern || null,
    file_keywords: form.file_keywords.length > 0 ? form.file_keywords : null,
    sheet_pattern: form.sheet_pattern || null,
    header_rows,
    data_start_row: form.data_start_row - 1,
    skip_footer_rows: form.skip_footer_rows,
    column_mappings,
    row_filters: Object.keys(row_filters).length > 0 ? row_filters : null,
    number_format,
    default_rates,
    is_active: form.is_active,
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/social-insurance/templates/${editId.value}`, payload)
      ElMessage.success('模板更新成功')
    } else {
      await api.post('/social-insurance/templates', payload)
      ElMessage.success('模板创建成功')
    }
    dialogVisible.value = false
    await fetchTemplates()
  } catch (e) {
    // error handled by interceptor
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  const confirmTitle = `确认删除模板「${row.name}」?`
  const confirmMsg = '删除后，依赖此模板的导入功能将无法使用。'

  try {
    await ElMessageBox.confirm(confirmMsg, confirmTitle, {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
    })
    await api.delete(`/social-insurance/templates/${row.id}`)
    ElMessage.success('模板已删除')
    await fetchTemplates()
  } catch {
    // 取消删除
  }
}
</script>

<style scoped>
.template-config-card {
  max-width: 1200px;
  margin: 0 auto;
}
.template-config-card :deep(.el-card__header) {
  padding: 16px 20px;
}
.mapping-row {
  padding: 4px 8px;
  border-radius: 6px;
  border-left: 3px solid transparent;
  transition: background-color 0.2s, border-color 0.2s;
}
.mapping-matched {
  background-color: #f0fdf4;
  border-left-color: #22c55e;
}
.mapping-generic {
  background-color: #fffbeb;
  border-left-color: #f59e0b;
}
</style>
