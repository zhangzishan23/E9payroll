import { useAuthStore } from '../stores/auth'

export const MODULE_PERMISSIONS = {
  dashboard: ['view'],
  employee: ['view', 'create', 'edit', 'delete', 'export', 'import', 'sync'],
  attendance: ['view', 'create', 'edit', 'delete', 'export', 'import', 'sync', 'writeoff'],
  performance: ['view', 'create', 'edit', 'delete', 'export', 'import'],
  insurance: ['view', 'create', 'edit', 'delete', 'export', 'import', 'template'],
  salary: ['view', 'edit', 'delete', 'check', 'step_confirm', 'tax_export', 'tax_import', 'travel_import', 'export'],
  approval: ['view', 'submit', 'approve'],
  report: ['view', 'export', 'contract_warning_view', 'contract_warning_export'],
  system: ['user', 'role', 'dict', 'log', 'backup'],
}

export const MENU_PERMISSION_MAP = {
  '/dashboard': ['dashboard:view'],
  '/employees': ['employee:view'],
  '/attendance': ['attendance:view'],
  '/performance': ['performance:view'],
  '/insurance': ['insurance:view'],
  '/insurance-template': ['insurance:template'],
  '/salary': ['salary:view'],
  '/approval': ['approval:view'],
  '/reports': ['report:view'],
  '/system/users': ['system:user'],
  '/system/roles': ['system:role'],
  '/system/dict': ['system:dict'],
  '/system/logs': ['system:log'],
  '/system/backup': ['system:backup'],
}

export function hasPermission(permCode) {
  const authStore = useAuthStore()
  return authStore.hasPermission(permCode)
}

export function hasAnyPermission(...permCodes) {
  const authStore = useAuthStore()
  return authStore.hasAnyPermission(...permCodes)
}

export function canAccessMenu(path) {
  const authStore = useAuthStore()
  if (authStore.isAdmin) return true
  if (path === '/profile') return true
  const requiredPerms = MENU_PERMISSION_MAP[path]
  if (!requiredPerms) return true
  return authStore.hasAnyPermission(...requiredPerms)
}
