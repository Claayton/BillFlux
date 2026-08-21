import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  base: process.env.NODE_ENV === 'production' ? '/static/app/' : '/',
  server: {
    port: 5174,
    strictPort: true,
    allowedHosts: ['pdv.beeplay.site', '.beeplay.site'],
    proxy: {
      '/api': process.env.BILLFLUX_API_TARGET || 'http://localhost:5000',
    },
  },
  build: {
    outDir: '../billflux/static/app',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})