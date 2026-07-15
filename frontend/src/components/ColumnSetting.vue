<template>
  <el-dropdown trigger="click" placement="bottom-end" @command="handleCommand">
    <el-button size="small" :icon="Setting">
      列设置
    </el-button>
    <template #dropdown>
      <el-dropdown-menu class="column-setting-menu" style="max-height: 400px; overflow-y: auto;">
        <div class="px-3 py-2 border-b border-gray-100 flex items-center justify-between gap-2">
          <el-checkbox
            :model-value="isAllChecked"
            :indeterminate="isIndeterminate"
            @change="toggleAll"
          >
            <span class="text-sm font-medium text-gray-700">全选</span>
          </el-checkbox>
          <el-button link type="primary" size="small" @click="resetDefault">
            恢复默认
          </el-button>
        </div>
        <el-dropdown-item
          v-for="col in columns"
          :key="col.key"
          :command="col.key"
          @click.stop
          class="!px-3"
        >
          <el-checkbox
            :model-value="visibleKeys.includes(col.key)"
            :disabled="col.required"
            @change="(val) => toggleColumn(col.key, val)"
            @click.stop
          >
            <span class="text-sm" :class="col.required ? 'text-gray-400' : 'text-gray-700'">
              {{ col.label }}
              <span v-if="col.required" class="text-xs text-gray-400 ml-1">(必选)</span>
            </span>
          </el-checkbox>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Setting } from '@element-plus/icons-vue'

const props = defineProps({
  columns: {
    type: Array,
    required: true,
  },
  modelValue: {
    type: Array,
    default: () => [],
  },
  defaultVisibleKeys: {
    type: Array,
    default: () => [],
  },
  storageKey: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'change'])

const visibleKeys = ref([...props.modelValue])

const isAllChecked = computed(() => {
  const toggleable = props.columns.filter(c => !c.required)
  return toggleable.every(c => visibleKeys.value.includes(c.key))
})

const isIndeterminate = computed(() => {
  const toggleable = props.columns.filter(c => !c.required)
  const checkedCount = toggleable.filter(c => visibleKeys.value.includes(c.key)).length
  return checkedCount > 0 && checkedCount < toggleable.length
})

function loadFromStorage() {
  if (!props.storageKey) return null
  try {
    const saved = localStorage.getItem(props.storageKey)
    if (saved) {
      const keys = JSON.parse(saved)
      if (Array.isArray(keys)) {
        return keys
      }
    }
  } catch (e) {
    console.warn('读取列配置失败:', e)
  }
  return null
}

function saveToStorage(keys) {
  if (!props.storageKey) return
  try {
    localStorage.setItem(props.storageKey, JSON.stringify(keys))
  } catch (e) {
    console.warn('保存列配置失败:', e)
  }
}

function init() {
  const saved = loadFromStorage()
  if (saved) {
    const requiredKeys = props.columns.filter(c => c.required).map(c => c.key)
    visibleKeys.value = [...new Set([...requiredKeys, ...saved.filter(k => props.columns.some(c => c.key === k))])]
  } else {
    visibleKeys.value = props.columns.map(c => c.key)
  }
  emitChange()
}

function toggleColumn(key, val) {
  if (val) {
    if (!visibleKeys.value.includes(key)) {
      visibleKeys.value = [...visibleKeys.value, key]
    }
  } else {
    visibleKeys.value = visibleKeys.value.filter(k => k !== key)
  }
  saveToStorage(visibleKeys.value)
  emitChange()
}

function toggleAll(val) {
  if (val) {
    visibleKeys.value = props.columns.map(c => c.key)
  } else {
    visibleKeys.value = props.columns.filter(c => c.required).map(c => c.key)
  }
  saveToStorage(visibleKeys.value)
  emitChange()
}

function resetDefault() {
  visibleKeys.value = props.columns.map(c => c.key)
  saveToStorage(visibleKeys.value)
  emitChange()
}

function handleCommand() {
  // 阻止dropdown关闭
}

function emitChange() {
  emit('update:modelValue', [...visibleKeys.value])
  emit('change', [...visibleKeys.value])
}

watch(() => props.columns, () => {
  init()
}, { immediate: true })
</script>

<style scoped>
.column-setting-menu {
  min-width: 180px;
}
</style>
