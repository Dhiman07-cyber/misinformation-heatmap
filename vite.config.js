import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
  root: 'frontend',
  publicDir: '../public',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'frontend/index.html'),
        dashboard: resolve(__dirname, 'frontend/dashboard.html'),
        heatmap: resolve(__dirname, 'frontend/heatmap.html')
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 30000
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 30000
      }
    }
  }
})
