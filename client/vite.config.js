import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Keep plotly (a large charting lib) in its own long-lived, cacheable
        // vendor chunk so app-code changes don't invalidate it.
        manualChunks: {
          plotly: ['plotly.js-cartesian-dist-min'],
        },
      },
    },
    // The plotly vendor chunk is intentionally large and is lazy-loaded, so the
    // default 500 kB warning is not meaningful here.
    chunkSizeWarningLimit: 2000,
  },
})
