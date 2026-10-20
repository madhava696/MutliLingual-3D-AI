import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Keep browser requests same-origin to avoid CORS errors, while forwarding
// API calls to the unchanged FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
