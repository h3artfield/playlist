import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const versionFile = resolve(__dirname, '../packaging/windows/app_version.txt')
const appVersion = readFileSync(versionFile, 'utf8').trim()

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __SCHEDULE_BUILDER_VERSION__: JSON.stringify(appVersion),
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },
})
