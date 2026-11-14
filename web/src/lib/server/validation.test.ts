import { describe, expect, it } from 'vitest';
import { parseCriteria, parseZones } from './validation';
import { isKnownNpa } from './npa';

const criteria = (over: Record<string, string> = {}) => ({
	min_rooms: '3',
	max_rooms: '4.5',
	min_rent: '',
	max_rent: '2500',
	min_area: '60',
	exclude_keywords: 'Untermiete\n\n  befristet \nUntermiete',
	anibis_urls: 'https://www.anibis.ch/de/q/wohnungen/bern',
	notify_to: 'me@example.com',
	...over
});

describe('parseCriteria', () => {
	it('parses numbers, lines and defaults', () => {
		const r = parseCriteria(criteria());
		expect(r).toEqual({
			ok: true,
			value: {
				min_rooms: 3,
				max_rooms: 4.5,
				min_rent: 0,
				max_rent: 2500,
				min_area: 60,
				exclude_keywords: ['Untermiete', 'befristet'],
				anibis_urls: ['https://www.anibis.ch/de/q/wohnungen/bern'],
				notify_to: 'me@example.com'
			}
		});
	});

	it('rejects negative and non-numeric values', () => {
		const r = parseCriteria(criteria({ min_rooms: '-1', min_area: 'abc' }));
		expect(r.ok).toBe(false);
		if (!r.ok) expect(Object.keys(r.errors).sort()).toEqual(['min_area', 'min_rooms']);
	});

	it('rejects min > max unless max is 0', () => {
		const r = parseCriteria(criteria({ min_rent: '3000', max_rent: '2000' }));
		expect(!r.ok && r.errors.max_rent).toBeTruthy();
		expect(parseCriteria(criteria({ min_rent: '3000', max_rent: '0' })).ok).toBe(true);
		expect(parseCriteria(criteria({ min_rooms: '5', max_rooms: '4' })).ok).toBe(false);
	});

	it('rejects non-Anibis URLs and bad emails', () => {
		const r = parseCriteria(
			criteria({ anibis_urls: 'https://www.homegate.ch/x\nhttp://www.anibis.ch/y', notify_to: 'nope' })
		);
		expect(r.ok).toBe(false);
		if (!r.ok) {
			expect(r.errors.anibis_urls).toContain('homegate');
			expect(r.errors.anibis_urls).toContain('http://www.anibis.ch/y');
			expect(r.errors.notify_to).toBeTruthy();
		}
	});
});

describe('parseZones', () => {
	const json = (v: unknown) => JSON.stringify(v);

	it('accepts known postcodes in order', () => {
		const r = parseZones(json([{ name: ' Centre ', npas: [3011, 3012] }, { name: 'Out', npas: [] }]), isKnownNpa);
		expect(r).toEqual({
			ok: true,
			value: [
				{ name: 'Centre', npas: [3011, 3012] },
				{ name: 'Out', npas: [] }
			]
		});
	});

	it('rejects unknown postcodes', () => {
		const r = parseZones(json([{ name: 'A', npas: [3011, 9999, 30.5] }]), isKnownNpa);
		expect(r.ok).toBe(false);
		if (!r.ok) {
			expect(r.errors.zones).toContain('9999');
			expect(r.errors.zones).toContain('30.5');
		}
	});

	it('rejects a postcode in two zones or twice in one', () => {
		const r = parseZones(json([{ name: 'A', npas: [3011] }, { name: 'B', npas: [3011] }]), isKnownNpa);
		expect(!r.ok && r.errors.zones).toContain('both Zone 1 and Zone 2');
		const twice = parseZones(json([{ name: 'A', npas: [3011, 3011] }]), isKnownNpa);
		expect(!twice.ok && twice.errors.zones).toContain('twice');
	});

	it('rejects missing names and malformed data', () => {
		expect(parseZones(json([{ name: '  ', npas: [] }]), isKnownNpa).ok).toBe(false);
		expect(parseZones('{', isKnownNpa).ok).toBe(false);
		expect(parseZones(json({ name: 'A' }), isKnownNpa).ok).toBe(false);
		expect(parseZones(json([{ name: 'A', npas: '3011' }]), isKnownNpa).ok).toBe(false);
	});
});
