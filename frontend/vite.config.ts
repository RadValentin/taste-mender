import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/*
 * In dev mode Vite serves the front-end, assets are relative to the root.
 * In production mode Django serves the front-end, assets are collected in a /static/ directory.
 * Docs: https://vite.dev/config/
 */
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'serve' ? '/' : '/static/',
  server: {
    port: 5173,
    proxy: {
      // TasteMender API link
      '/api': 'http://127.0.0.1:8000',
    },
  },
}))