import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': `${__dirname}src`,
        },
    },
    server: {
        port: 5173,
        proxy: {
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true,
            },
            '/api': {
                target: 'http://localhost:8000',
            },
        },
    },
})
