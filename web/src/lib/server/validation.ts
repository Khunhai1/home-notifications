export interface Criteria {
	min_rooms: number;
	max_rooms: number;
	min_rent: number;
	max_rent: number;
	min_area: number;
	exclude_keywords: string[];
	anibis_urls: string[];
	notify_to: string;
}

export interface ZoneInput {
	name: string;
	npas: number[];
}

export type Result<T> = { ok: true; value: T } | { ok: false; errors: Record<string, string> };

export const ANIBIS_PREFIX = 'https://www.anibis.ch/';

const NUMBER_FIELDS = ['min_rooms', 'max_rooms', 'min_rent', 'max_rent', 'min_area'] as const;

const lines = (text: string) =>
	text
		.split(/\r?\n/)
		.map((l) => l.trim())
		.filter(Boolean);

/** Validates the criteria form. Empty number fields mean 0 (no limit). */
export function parseCriteria(form: Record<string, string>): Result<Criteria> {
	const errors: Record<string, string> = {};
	const num: Record<string, number> = {};
	for (const field of NUMBER_FIELDS) {
		const raw = (form[field] ?? '').trim();
		const n = raw === '' ? 0 : Number(raw);
		if (!Number.isFinite(n) || n < 0) errors[field] = 'Must be a number ≥ 0.';
		num[field] = n;
	}
	if (!errors.min_rooms && !errors.max_rooms && num.max_rooms > 0 && num.min_rooms > num.max_rooms)
		errors.max_rooms = 'Must be at least the minimum (or 0 for no limit).';
	if (!errors.min_rent && !errors.max_rent && num.max_rent > 0 && num.min_rent > num.max_rent)
		errors.max_rent = 'Must be at least the minimum (or 0 for no limit).';

	const anibis_urls = lines(form.anibis_urls ?? '');
	const bad = anibis_urls.filter((u) => !u.startsWith(ANIBIS_PREFIX));
	if (bad.length) errors.anibis_urls = `Must start with ${ANIBIS_PREFIX}: ${bad.join(', ')}`;

	const notify_to = (form.notify_to ?? '').trim();
	if (notify_to && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(notify_to))
		errors.notify_to = 'Not an email address.';

	if (Object.keys(errors).length) return { ok: false, errors };
	return {
		ok: true,
		value: {
			min_rooms: num.min_rooms,
			max_rooms: num.max_rooms,
			min_rent: num.min_rent,
			max_rent: num.max_rent,
			min_area: num.min_area,
			exclude_keywords: [...new Set(lines(form.exclude_keywords ?? ''))],
			anibis_urls,
			notify_to
		}
	};
}

/**
 * Validates the zone editor's JSON: a list of {name, npas} in order of preference.
 * Rejects unknown postcodes and a postcode in two zones.
 */
export function parseZones(json: string, isKnown: (npa: number) => boolean): Result<ZoneInput[]> {
	let data: unknown;
	try {
		data = JSON.parse(json);
	} catch {
		return { ok: false, errors: { zones: 'Invalid data.' } };
	}
	if (!Array.isArray(data)) return { ok: false, errors: { zones: 'Invalid data.' } };

	const problems: string[] = [];
	const owner = new Map<number, number>();
	const zones: ZoneInput[] = [];
	data.forEach((z: unknown, i) => {
		const label = `Zone ${i + 1}`;
		const { name, npas } = (z ?? {}) as { name?: unknown; npas?: unknown };
		const trimmed = typeof name === 'string' ? name.trim() : '';
		if (!trimmed) problems.push(`${label} needs a name.`);
		else if (trimmed.length > 100) problems.push(`${label}: name is too long.`);
		if (!Array.isArray(npas)) {
			problems.push(`${label}: invalid postcodes.`);
			return;
		}
		const clean: number[] = [];
		for (const n of npas) {
			if (!Number.isInteger(n) || !isKnown(n)) {
				problems.push(`${label}: ${String(n)} is not a known Swiss postcode.`);
				continue;
			}
			const other = owner.get(n);
			if (other !== undefined) {
				problems.push(
					other === i
						? `${label}: ${n} is listed twice.`
						: `${n} is in both Zone ${other + 1} and ${label}.`
				);
				continue;
			}
			owner.set(n, i);
			clean.push(n);
		}
		zones.push({ name: trimmed, npas: clean });
	});
	if (problems.length) return { ok: false, errors: { zones: problems.join(' ') } };
	return { ok: true, value: zones };
}
