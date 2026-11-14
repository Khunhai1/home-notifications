import type { Handle } from '@sveltejs/kit';
import { createRemoteJWKSet, jwtVerify } from 'jose';

// One key set per team domain, cached for the lifetime of the isolate.
const keySets = new Map<string, ReturnType<typeof createRemoteJWKSet>>();

function keySet(teamDomain: string) {
	let jwks = keySets.get(teamDomain);
	if (!jwks) {
		jwks = createRemoteJWKSet(new URL(`https://${teamDomain}/cdn-cgi/access/certs`));
		keySets.set(teamDomain, jwks);
	}
	return jwks;
}

const forbidden = () => new Response('Forbidden', { status: 403 });

export const handle: Handle = async ({ event, resolve }) => {
	const env = event.platform?.env;
	if (!env) return forbidden();

	if (env.DEV_USER) {
		event.locals.user = env.DEV_USER;
		return resolve(event);
	}

	const token = event.request.headers.get('Cf-Access-Jwt-Assertion');
	const { ACCESS_TEAM_DOMAIN: team, ACCESS_AUD: aud } = env;
	if (!token || !team || !aud) return forbidden();
	try {
		const { payload } = await jwtVerify(token, keySet(team), {
			issuer: `https://${team}`,
			audience: aud
		});
		if (typeof payload.email !== 'string') return forbidden();
		event.locals.user = payload.email;
	} catch {
		return forbidden();
	}
	return resolve(event);
};
