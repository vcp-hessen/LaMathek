/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

const apiPort = process.env.LAMATHEK_API_PORT ?? '5001'
const apiOrigin = process.env.LAMATHEK_API_ORIGIN ?? `http://127.0.0.1:${apiPort}`
const hmrHost = process.env.VITE_HMR_HOST

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      // Rules shared with the API (server/lamathek/domain), single source of truth.
      '@shared': fileURLToPath(new URL('../server/lamathek/domain', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.spec.ts'],
  },
  server: {
    proxy: {
      '/api': apiOrigin,
      '/login': apiOrigin,
      '/auth': apiOrigin,
      '/logout': apiOrigin,
    },
    hmr: hmrHost
      ? {
          host: hmrHost,
          protocol: 'wss',
          clientPort: 443,
        }
      : undefined,
  },
})
