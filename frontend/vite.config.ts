import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const env = process.env as Record<string, string | undefined>
const envHost = env.VITE_DEV_HOST
const envPort = env.VITE_DEV_PORT

const devHost = envHost !== undefined && envHost !== '' ? envHost : '127.0.0.1'
const parsedPort =
  envPort !== undefined ? Number.parseInt(envPort, 10) : Number.NaN
const devPort = Number.isFinite(parsedPort) ? parsedPort : 5174

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: devHost,
    port: devPort,
    strictPort: true,
  },
})
