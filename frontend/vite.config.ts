import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			'/api': 'http://localhost:8000'
		}
	},
	test: {
		// Use jsdom so DOMPurify has a real DOM to work with.
		environment: 'jsdom',
		include: ['src/**/*.test.ts'],
	},
});
