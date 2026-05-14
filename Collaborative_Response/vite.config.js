import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  base: '/collaborative-response/',
  plugins: [vue()],
  build: {
    outDir: '../vue-project_all/public/collaborative-response',
    emptyOutDir: true,
  },
})
