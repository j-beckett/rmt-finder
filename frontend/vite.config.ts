import path from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const STATS_ORIGIN = 'https://stats.studiobeckett.ca'

// Production builds only, so dev never contacts the stats host. no_onload:
// the app sends its own page views with clean paths.
function goatcounter(): Plugin {
  return {
    name: 'goatcounter',
    apply: 'build',
    transformIndexHtml: () => [
      {
        tag: 'script',
        attrs: {
          'data-goatcounter': `${STATS_ORIGIN}/count`,
          'data-goatcounter-settings': '{"no_onload": true}',
          async: true,
          src: `${STATS_ORIGIN}/count.js`,
        },
        injectTo: 'head',
      },
    ],
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), goatcounter()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
