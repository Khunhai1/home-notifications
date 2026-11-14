/** One row of static/npa.json: [npa, "Village A, Village B", lat, lon]. */
export type NpaRow = [number, string, number, number];

export interface Place {
	npa: number;
	names: string;
	lat: number;
	lon: number;
}

export const toPlace = ([npa, names, lat, lon]: NpaRow): Place => ({ npa, names, lat, lon });

const fold = (s: string) =>
	s
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '')
		.toLowerCase();

/** Postcodes matching a typed postcode prefix or part of a village name. */
export function suggest(places: Place[], query: string, limit = 8): Place[] {
	const q = query.trim();
	if (!q) return [];
	if (/^\d+$/.test(q)) return places.filter((p) => String(p.npa).startsWith(q)).slice(0, limit);
	const f = fold(q);
	// Rank: a village named exactly that, then names starting with it, then names containing it.
	const ranks: Place[][] = [[], [], []];
	for (const p of places) {
		const names = fold(p.names).split(', ');
		if (names.includes(f)) ranks[0].push(p);
		else if (names.some((n) => n.startsWith(f))) ranks[1].push(p);
		else if (names.some((n) => n.includes(f))) ranks[2].push(p);
	}
	return ranks.flat().slice(0, limit);
}
