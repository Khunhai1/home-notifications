import { fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { parseFilter } from '$lib/filters';
import { dashboard, db, setStatus, STATUSES, type Status } from '$lib/server/db';
import { place } from '$lib/server/npa';

export const load: PageServerLoad = async ({ url, platform }) => {
	const filter = parseFilter(url.searchParams);
	const data = await dashboard(db(platform), filter);
	const zones = data.zones.map((z) => ({
		...z,
		places: z.npas.map((n) => place(n) ?? { npa: n, names: '', lat: NaN, lon: NaN })
	}));
	const located = zones.flatMap((z) => z.places).filter((pl) => Number.isFinite(pl.lat));
	const center: [number, number] | null = located.length
		? [
				located.reduce((s, pl) => s + pl.lat, 0) / located.length,
				located.reduce((s, pl) => s + pl.lon, 0) / located.length
			]
		: null;

	return { ...data, zones, center, filter };
};

export const actions: Actions = {
	status: async ({ request, platform }) => {
		const form = await request.formData();
		const id = Number(form.get('id'));
		const status = form.get('status') as Status;
		if (!Number.isInteger(id) || id <= 0 || !STATUSES.includes(status))
			return fail(400, { error: 'Invalid request.' });
		await setStatus(db(platform), id, status);
	}
};
