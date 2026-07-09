import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/e9salary/api',
  timeout: 120000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    const msg = error.response?.data?.detail || '请求失败，请稍后重试'
    ElMessage({ message: msg, type: 'error', duration: 6000 })
    if (error.response?.status === 401) {
      const isLoginPage = window.location.pathname === '/e9salary/login' || window.location.pathname === '/login'
      if (!isLoginPage) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/e9salary/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api