import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

async function parseBlobError(blob) {
  try {
    const text = await blob.text()
    const json = JSON.parse(text)
    return json.detail || '请求失败，请稍后重试'
  } catch {
    return '请求失败，请稍后重试'
  }
}

api.interceptors.response.use(
  response => response,
  async error => {
    const silent = error.config?.silent === true
    let msg = '请求失败，请稍后重试'
    if (error.response?.data instanceof Blob) {
      msg = await parseBlobError(error.response.data)
    } else {
      msg = error.response?.data?.detail || '请求失败，请稍后重试'
    }
    if (!silent) {
      ElMessage({ message: msg, type: 'error', duration: 6000 })
    }
    if (error.response?.status === 401) {
      const isLoginPage = window.location.pathname === '/login'
      if (!isLoginPage) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api