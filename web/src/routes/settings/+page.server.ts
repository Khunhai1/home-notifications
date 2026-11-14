import { fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { db, replaceZones, saveCriteria, settingsPage } from '$lib/server/db';
import { isKnownNpa, place } from '$lib/server/npa';
import { parseCriteria, parseZones } from '$lib/server/validation';
import type { Place } from '$lib/npa';

export const load: PageServerLoad = async ({ platform }) => {
	const data = await settingsPage(db(platform));
	// Village names and coordinates of the saved postcodes, so the editor renders before npa.json loads.
	const places: Record<number, Place> = {};
	for (const n of data.zones.flatMap((z) => z.npas)) {
		const p = place(n);
		if (p) places[n] = p;
	}
	return { ...data, places, canDispatch: Boolean(platform?.env.GITHUB_TOKEN) };
};

const formObject = (form: FormData) =>
	Object.fromEntries([...form].map(([k, v]) => [k, typeof v === 'string' ? v : '']));

export const actions: Actions = {
	criteria: async ({ request, platform }) => {
		const r = parseCriteria(formObject(await request.formData()));
		if (!r.ok) return fail(400, { criteria: { errors: r.errors } });
		await saveCriteria(db(platform), r.value);
		return { criteria: { saved: true } };
	},

	zones: async ({ request, platform }) => {
		const json = (await request.formData()).get('zones');
		const r = parseZones(typeof json === 'string' ? json : '', isKnownNpa);
		if (!r.ok) return fail(400, { zones: { error: r.errors.zones } });
		await replaceZones(db(platform), r.value);
		return { zones: { saved: true } };
	},

	check: async ({ platform }) => {
		const env = platform?.env;
		if (!env?.GITHUB_TOKEN || !env.GITHUB_REPO)
			return fail(400, { check: { error: 'GITHUB_TOKEN or GITHUB_REPO is not set.' } });
		const res = await fetch(
			`https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/fetch.yml/dispatches`,
			{
				method: 'POST',
				headers: {
					Authorization: `Bearer ${env.GITHUB_TOKEN}`,
					Accept: 'application/vnd.github+json',
					'User-Agent': 'home-notifications',
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ ref: 'main' })
			}
		);
		if (!res.ok) {
			const body = await res.text();
			let message = body;
			try {
				message = JSON.parse(body).message ?? body;
			} catch {
				// not JSON: keep the raw text
			}
			return fail(502, { check: { error: `GitHub answered ${res.status}: ${message}` } });
		}
		return { check: { started: true } };
	}
};
