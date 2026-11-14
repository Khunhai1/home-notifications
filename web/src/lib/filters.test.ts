import { describe, expect, it } from 'vitest';
import { extraFilterCount, filterParams, parseFilter } from './filters';

const parse = (query: string) => parseFilter(new URLSearchParams(query));

describe('parseFilter', () => {
	it('defaults to newest first with no extra filters', () => {
		expect(parse('')).toEqual({
			status: '',
			zone: 0,
			source: '',
			includeUnmatched: false,
			sort: 'newest',
			q: '',
			maxRent: 0,
			minRooms: 0,
			minArea: 0,
			days: 0
		});
	});

	it('reads every filter', () => {
		const f = parse('status=favorite&zone=2&source=flatfox&all=1&sort=ppm2&q=+balkon+&max_rent=1500&min_rooms=2.5&min_area=50&days=7');
		expect(f).toEqual({
			status: 'favorite',
			zone: 2,
			source: 'flatfox',
			includeUnmatched: true,
			sort: 'ppm2',
			q: 'balkon',
			maxRent: 1500,
			minRooms: 2.5,
			minArea: 50,
			days: 7
		});
		expect(extraFilterCount(f)).toBe(5);
	});

	it('ignores invalid values instead of failing', () => {
		const f = parse('status=deleted&zone=-1&sort=drop+table&max_rent=abc&min_rooms=-2&days=5');
		expect([f.status, f.zone, f.sort, f.maxRent, f.minRooms, f.days]).toEqual(['', 0, 'newest', 0, 0, 0]);
	});

	it('caps the search text', () => {
		expect(parse(`q=${'x'.repeat(500)}`).q).toHaveLength(100);
	});
});

describe('filterParams', () => {
	it('leaves out defaults and round-trips', () => {
		expect(filterParams(parse(''))).toBe('');
		const query = 'zone=1&sort=price&max_rent=1400&days=3';
		expect(parse(filterParams(parse(query)))).toEqual(parse(query));
	});

	it('applies overrides', () => {
		expect(filterParams(parse('sort=area&q=marly'), { q: '', status: 'new' })).toBe('status=new&sort=area');
	});
});
