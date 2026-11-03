/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Relative base so the static build works from any path (GitHub Pages, file server).
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { target: 'es2020', sourcemap: true },
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
});
