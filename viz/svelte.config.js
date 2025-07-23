import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		adapter: adapter({
			// Static site generation settings
			pages: 'build',
			assets: 'build',
			fallback: 'index.html', // Enable SPA mode for dynamic routes
			precompress: false,
			strict: false // Don't require all routes to be prerenderable
		}),
		// Ensure we can prerender all routes
		prerender: {
			handleMissingId: 'warn',
			handleHttpError: 'warn'
		}
	}
};

export default config;
