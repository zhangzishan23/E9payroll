import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const permissions = ref(new Set(JSON.parse(localStorage.getItem('permissions') || '[]')))
  const roles = ref(new Set(JSON.parse(localStorage.getItem('roles') || '[]')))

  const isAdmin = computed(() => user.value?.is_admin === true)

  function hasPermission(permCode) {
    if (isAdmin.value) return true
    return permissions.value.has(permCode)
  }

  function hasAnyPermission(...permCodes) {
    if (isAdmin.value) return true
    return permCodes.some(p => permissions.value.has(p))
  }

  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    const res = await api.post('/auth/login', formData)
    token.value = res.data.access_token
    user.value = {
      id: res.data.user_id,
      username: res.data.username,
      display_name: res.data.display_name,
      is_admin: res.data.is_admin
    }
    const perms = Array.isArray(res.data.permissions) ? res.data.permissions : []
    const roleList = Array.isArray(res.data.roles) ? res.data.roles : []
    permissions.value = new Set(perms)
    roles.value = new Set(roleList)
    localStorage.setItem('token', token.value)
    localStorage.setItem('user', JSON.stringify(user.value))
    localStorage.setItem('permissions', JSON.stringify(perms))
    localStorage.setItem('roles', JSON.stringify(roleList))
    return res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    permissions.value = new Set()
    roles.value = new Set()
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('permissions')
    localStorage.removeItem('roles')
  }

  return { token, user, permissions, roles, isAdmin, hasPermission, hasAnyPermission, login, logout }
})