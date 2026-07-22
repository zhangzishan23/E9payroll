import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: '/',
  server: {
    host: '0.0.0.0',
    port: 5180,
    strictPort: true,
    hmr: {
      overlay: true
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true
      }
    }
  }
})