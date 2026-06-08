import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import cesium from 'vite-plugin-cesium'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    cesium(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:5001',
      '/2d_deduction.html': 'http://127.0.0.1:5001',
      '/cesium_viewer': 'http://127.0.0.1:5001',
      '/mission.czml': 'http://127.0.0.1:5001',
      '/path_result.json': 'http://127.0.0.1:5001',
      '/Cesium': 'http://127.0.0.1:5001',
    }
  }
})
