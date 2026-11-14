import adapter from '@sveltejs/adapter-cloudflare';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
export default {
	preprocess: vitePreprocess(),
	kit: {
		// platformProxy gives `vite dev` a platform.env built from wrangler.toml and .dev.vars.
		adapter: adapter({ platformProxy: { configPath: 'wrangler.toml', persist: false } })
	}
};
