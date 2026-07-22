import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const routePrefix = env.VITE_ROUTE_PREFIX || ''
  const normalizedPrefix = routePrefix
    ? (routePrefix.startsWith('/') ? routePrefix : '/' + routePrefix).replace(/\/$/, '')
    : ''
  const apiPrefix = normalizedPrefix ? `${normalizedPrefix}/api` : '/api'

  return {
    plugins: [vue()],
    base: normalizedPrefix ? `${normalizedPrefix}/` : '/',
    server: {
      host: '0.0.0.0',
      port: 5180,
      strictPort: true,
      hmr: {
        overlay: true
      },
      proxy: {
        [apiPrefix]: {
          target: 'http://127.0.0.1:8010',
          changeOrigin: true,
          rewrite: normalizedPrefix
            ? (path) => path.replace(new RegExp(`^${normalizedPrefix}/api`), '/api')
            : undefined
        }
      }
    }
  }
})
