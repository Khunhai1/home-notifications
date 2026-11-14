// See https://svelte.dev/docs/kit/types#app.d.ts
declare global {
	namespace App {
		interface Locals {
			/** Email of the Cloudflare Access user (or DEV_USER locally). */
			user: string;
		}
		interface Platform {
			env: {
				DATABASE_URL: string;
				ACCESS_AUD?: string;
				ACCESS_TEAM_DOMAIN?: string;
				GITHUB_TOKEN?: string;
				GITHUB_REPO?: string;
				/** Local dev only: skips the Access check. Never set in production. */
				DEV_USER?: string;
			};
		}
	}
}

export {};
