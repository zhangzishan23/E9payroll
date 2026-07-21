import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)
  const permissions = ref(new Set())
  const roles = ref(new Set())
  const permissionsLoaded = ref(false)

  const isAdmin = computed(() => user.value?.is_admin === true)

  function hasPermission(permCode) {
    if (isAdmin.value) return true
    return permissions.value.has(permCode)
  }

  function hasAnyPermission(...permCodes) {
    if (isAdmin.value) return true
    return permCodes.some(p => permissions.value.has(p))
  }

  function _saveToStorage() {
    if (token.value) {
      localStorage.setItem('token', token.value)
    }
    if (user.value) {
      localStorage.setItem('user', JSON.stringify(user.value))
    }
    localStorage.setItem('permissions', JSON.stringify([...permissions.value]))
    localStorage.setItem('roles', JSON.stringify([...roles.value]))
  }

  function _setUserData(data) {
    user.value = {
      id: data.id || data.user_id,
      username: data.username,
      display_name: data.display_name,
      is_admin: data.is_admin
    }
    const perms = Array.isArray(data.permissions) ? data.permissions : []
    const roleList = Array.isArray(data.roles) ? data.roles : []
    permissions.value = new Set(perms)
    roles.value = new Set(roleList)
    permissionsLoaded.value = true
  }

  async function fetchUserInfo() {
    if (!token.value) {
      permissionsLoaded.value = true
      return null
    }
    try {
      const res = await api.get('/auth/me')
      _setUserData(res.data)
      _saveToStorage()
      return res.data
    } catch (error) {
      permissionsLoaded.value = true
      if (error.response?.status === 401) {
        logout()
      }
      throw error
    }
  }

  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    const res = await api.post('/auth/login', formData)
    token.value = res.data.access_token
    _setUserData(res.data)
    _saveToStorage()
    return res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    permissions.value = new Set()
    roles.value = new Set()
    permissionsLoaded.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('permissions')
    localStorage.removeItem('roles')
  }

  function initFromStorage() {
    const savedUser = localStorage.getItem('user')
    const savedPerms = localStorage.getItem('permissions')
    const savedRoles = localStorage.getItem('roles')
    if (savedUser) {
      user.value = JSON.parse(savedUser)
    }
    if (savedPerms) {
      permissions.value = new Set(JSON.parse(savedPerms))
    }
    if (savedRoles) {
      roles.value = new Set(JSON.parse(savedRoles))
    }
  }

  initFromStorage()

  return { token, user, permissions, roles, isAdmin, permissionsLoaded, hasPermission, hasAnyPermission, fetchUserInfo, login, logout, initFromStorage }
})