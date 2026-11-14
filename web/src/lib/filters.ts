export type Status = 'new' | 'favorite' | 'applied' | 'hidden';
export const STATUSES: Status[] = ['new', 'favorite', 'applied', 'hidden'];

export const SORTS = {
	newest: 'Newest first',
	oldest: 'Oldest first',
	price: 'Rent: low to high',
	price_desc: 'Rent: high to low',
	ppm2: 'Rent per m²: lowest',
	area: 'Largest',
	rooms: 'Most rooms',
	zone: 'Best zone first'
} as const;
export type Sort = keyof typeof SORTS;

export const PERIODS = { 0: 'Any time', 1: 'Last 24 hours', 3: 'Last 3 days', 7: 'Last week', 30: 'Last month' } as const;

export interface ListingFilter {
	/** '' = everything except hidden */
	status: Status | '';
	zone: number;
	source: string;
	includeUnmatched: boolean;
	sort: Sort;
	/** case-insensitive text in title, description, street, city or postcode; '' = any */
	q: string;
	/** 0 = no limit; listings with an unknown value are left out once a limit is set */
	maxRent: number;
	minRooms: number;
	minArea: number;
	/** only listings first seen in the last N days, 0 = any */
	days: number;
}

const positive = (v: string | null) => {
	const n = Number(v);
	return Number.isFinite(n) && n > 0 ? n : 0;
};

export function parseFilter(p: URLSearchParams): ListingFilter {
	const status = p.get('status') as Status;
	const sort = p.get('sort') as Sort;
	const days = Math.trunc(positive(p.get('days')));
	return {
		status: STATUSES.includes(status) ? status : '',
		zone: Math.trunc(positive(p.get('zone'))),
		source: p.get('source') ?? '',
		includeUnmatched: p.get('all') === '1',
		sort: sort in SORTS ? sort : 'newest',
		q: (p.get('q') ?? '').trim().slice(0, 100),
		maxRent: positive(p.get('max_rent')),
		minRooms: positive(p.get('min_rooms')),
		minArea: positive(p.get('min_area')),
		days: days in PERIODS ? days : 0
	};
}

/** The filter as URL params, leaving out defaults so links stay short. */
export function filterParams(f: ListingFilter, over: Record<string, string> = {}): string {
	const all: Record<string, string> = {
		status: f.status,
		zone: f.zone ? String(f.zone) : '',
		source: f.source,
		all: f.includeUnmatched ? '1' : '',
		sort: f.sort === 'newest' ? '' : f.sort,
		q: f.q,
		max_rent: f.maxRent ? String(f.maxRent) : '',
		min_rooms: f.minRooms ? String(f.minRooms) : '',
		min_area: f.minArea ? String(f.minArea) : '',
		days: f.days ? String(f.days) : '',
		...over
	};
	const params = new URLSearchParams();
	for (const [k, v] of Object.entries(all)) if (v) params.set(k, v);
	return params.toString();
}

/** How many of the optional "more filters" are active (for the toggle's label). */
export const extraFilterCount = (f: ListingFilter) =>
	[f.q, f.maxRent, f.minRooms, f.minArea, f.days].filter(Boolean).length;
