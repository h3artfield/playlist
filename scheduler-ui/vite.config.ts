import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

const versionFile = resolve(__dirname, '../packaging/windows/app_version.txt')
const appVersion = readFileSync(versionFile, 'utf8').trim()

function scheduleBuilderVersion(version: string): Plugin {
  return {
    name: 'schedule-builder-version',
    transformIndexHtml: {
      order: 'post',
      handler(html) {
        const meta = `    <meta name="schedule-builder-version" content="${version}" />\n`
        if (html.includes('name="schedule-builder-version"')) {
          return html.replace(/content="[^"]*"\s*\/?>\s*(?=<!-- schedule-builder-version -->|\n)/, `content="${version}" />\n`)
        }
        return html.replace('</head>', `${meta}  </head>`)
      },
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), scheduleBuilderVersion(appVersion)],
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
