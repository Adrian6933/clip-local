import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

export default defineConfig({ integrations: [react()], server: { host: '127.0.0.1', port: 4322 }, devToolbar: { enabled: false }, vite: { server: { strictPort: true, proxy: { '/api': 'http://127.0.0.1:4323' } }, preview: { proxy: { '/api': 'http://127.0.0.1:4323' } } } });
