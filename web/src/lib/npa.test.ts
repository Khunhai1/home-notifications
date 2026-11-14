import { describe, expect, it } from 'vitest';
import rows from '../../static/npa.json';
import { suggest, toPlace, type NpaRow } from './npa';

const places = (rows as NpaRow[]).map(toPlace);

describe('suggest', () => {
	it('matches postcode prefixes', () => {
		const r = suggest(places, '301');
		expect(r.length).toBeGreaterThan(0);
		expect(r.every((p) => String(p.npa).startsWith('301'))).toBe(true);
	});

	it('puts exact village names first, ignoring case and accents', () => {
		expect(suggest(places, 'bulle')[0].names).toContain('Bulle');
		expect(suggest(places, 'Koniz').some((p) => p.names.includes('Köniz'))).toBe(true);
	});

	it('returns nothing for an empty query', () => {
		expect(suggest(places, '  ')).toEqual([]);
	});
});
