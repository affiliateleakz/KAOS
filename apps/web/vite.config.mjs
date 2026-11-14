import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backend = env.REACT_APP_BACKEND_URL || '';
  const proxy = env.KAOS_API_PROXY;
  return {
    plugins: [react()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    // Deliberate public values only. Never inline process.env or all loaded secrets.
    define: {
      'process.env.REACT_APP_BACKEND_URL': JSON.stringify(backend),
      'process.env.REACT_APP_GOOGLE_CLIENT_ID': JSON.stringify(env.REACT_APP_GOOGLE_CLIENT_ID || ''),
    },
    build: { outDir: 'build', target: 'es2020', sourcemap: false },
    server: { proxy: proxy ? { '/api': { target: proxy, changeOrigin: true } } : undefined },
    test: { environment: 'node', include: ['src/**/*.test.js'] },
  };
});
