import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5001',
      '/login': 'http://127.0.0.1:5001',
      '/auth': 'http://127.0.0.1:5001',
      '/logout': 'http://127.0.0.1:5001',
    },
  },
})
