import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Em dev (vite na 3000), faz proxy de /api para a FastAPI (9777).
// Em produção, a FastAPI serve o bundle de dist/ na própria porta.
export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://127.0.0.1:9777',
    },
  },
})
