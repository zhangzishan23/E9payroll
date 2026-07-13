import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/e9salary/',
  server: {
    host: '0.0.0.0',
    port: 5180,
    proxy: {
      '/e9salary/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true
      }
    }
  }
})