import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const apiPort = process.env.LAMATHEK_API_PORT ?? '5001'
const apiOrigin = `http://127.0.0.1:${apiPort}`

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': apiOrigin,
      '/login': apiOrigin,
      '/auth': apiOrigin,
      '/logout': apiOrigin,
    },
  },
})
