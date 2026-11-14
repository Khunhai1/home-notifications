import { neon, type NeonQueryFunction } from '@neondatabase/serverless';
import type { Criteria, ZoneInput } from './validation';

export type Sql = NeonQueryFunction<false, false>;
export type Status = 'new' | 'favorite' | 'applied' | 'hidden';
export const STATUSES: Status[] = ['new', 'favorite', 'applied', 'hidden'];

export interface Listing {
	id: number;
	source: string;
	url: string;
	title: string;
	rent: number | null;
	rooms: number | null;
	area: number | null;
	zipcode: number | null;
	city: string;
	street: string;
	lat: number | null;
	lon: number | null;
	image_url: string;
	date: string;
	matched: boolean;
	zone: number | null;
	status: Status;
	also_on: { source: string; url: string }[];
}

export interface Zone {
	position: number;
	name: string;
	npas: number[];
}

export interface Settings extends Criteria {
	updated_at: string;
}

export interface ListingFilter {
	/** '' = everything except hidden */
	status: Status | '';
	zone: number;
	source: string;
	includeUnmatched: boolean;
}

export function db(platform: App.Platform | undefined): Sql {
	const url = platform?.env.DATABASE_URL;
	if (!url) throw new Error('DATABASE_URL is not set');
	return neon(url);
}

// The driver returns numeric columns as strings.
const num = (v: unknown) => (v == null ? null : Number(v));
const iso = (v: unknown) => (v == null ? null : new Date(v as string | Date).toISOString());

const listingsQuery = (sql: Sql, f: ListingFilter) => sql`
	SELECT l.id, l.source, l.url, l.title, l.rent, l.rooms, l.area, l.zipcode, l.city, l.street,
	       l.lat, l.lon, l.image_url, COALESCE(l.published_at, l.first_seen) AS date, l.matched,
	       l.zone, l.status,
	       (SELECT COALESCE(json_agg(json_build_object('source', d.source, 'url', d.url) ORDER BY d.id), '[]')
	          FROM listings d WHERE d.duplicate_of = l.id) AS also_on
	FROM listings l
	WHERE l.duplicate_of IS NULL
	  AND (${f.includeUnmatched} OR l.matched)
	  AND (CASE WHEN ${f.status} = '' THEN l.status <> 'hidden' ELSE l.status = ${f.status} END)
	  AND (${f.zone}::int = 0 OR l.zone = ${f.zone}::int)
	  AND (${f.source} = '' OR l.source = ${f.source})
	ORDER BY COALESCE(l.published_at, l.first_seen) DESC
	LIMIT 300`;

const zonesQuery = (sql: Sql) => sql`
	SELECT z.position, z.name,
	       COALESCE(array_agg(n.npa ORDER BY n.npa) FILTER (WHERE n.npa IS NOT NULL), '{}') AS npas
	FROM zones z LEFT JOIN zone_npas n ON n.zone_id = z.id
	GROUP BY z.id ORDER BY z.position`;

const lastFetchQuery = (sql: Sql) => sql`SELECT value FROM state WHERE key = 'last_fetch'`;

const toZones = (rows: Record<string, unknown>[]): Zone[] =>
	rows.map((r) => ({
		position: Number(r.position),
		name: String(r.name),
		npas: (r.npas as unknown[]).map(Number)
	}));

/** Everything the dashboard needs, in one round trip. */
export async function dashboard(sql: Sql, filter: ListingFilter) {
	const [listings, sources, zones, lastFetch] = await sql.transaction(
		[
			listingsQuery(sql, filter),
			sql`SELECT DISTINCT source FROM listings ORDER BY source`,
			zonesQuery(sql),
			lastFetchQuery(sql)
		],
		{ readOnly: true }
	);
	return {
		listings: listings.map(
			(r): Listing => ({
				id: Number(r.id),
				source: r.source,
				url: r.url,
				title: r.title,
				rent: num(r.rent),
				rooms: num(r.rooms),
				area: num(r.area),
				zipcode: num(r.zipcode),
				city: r.city,
				street: r.street,
				lat: num(r.lat),
				lon: num(r.lon),
				image_url: r.image_url,
				date: iso(r.date)!,
				matched: r.matched,
				zone: num(r.zone),
				status: r.status,
				also_on: r.also_on
			})
		),
		sources: sources.map((r) => String(r.source)),
		zones: toZones(zones),
		lastFetch: (lastFetch[0]?.value as string | undefined) ?? null
	};
}

export async function setStatus(sql: Sql, id: number, status: Status) {
	await sql`UPDATE listings SET status = ${status} WHERE id = ${id}`;
}

export async function settingsPage(sql: Sql) {
	const [settings, zones, lastFetch] = await sql.transaction(
		[sql`SELECT * FROM settings WHERE id = 1`, zonesQuery(sql), lastFetchQuery(sql)],
		{ readOnly: true }
	);
	const s = settings[0];
	if (!s) throw new Error('settings row is missing');
	return {
		settings: {
			min_rooms: Number(s.min_rooms),
			max_rooms: Number(s.max_rooms),
			min_rent: Number(s.min_rent),
			max_rent: Number(s.max_rent),
			min_area: Number(s.min_area),
			exclude_keywords: s.exclude_keywords,
			anibis_urls: s.anibis_urls,
			notify_to: s.notify_to,
			updated_at: iso(s.updated_at)!
		} satisfies Settings,
		zones: toZones(zones),
		lastFetch: (lastFetch[0]?.value as string | undefined) ?? null
	};
}

export async function saveCriteria(sql: Sql, c: Criteria) {
	await sql`
		UPDATE settings SET
			min_rooms = ${c.min_rooms}, max_rooms = ${c.max_rooms},
			min_rent = ${c.min_rent}, max_rent = ${c.max_rent}, min_area = ${c.min_area},
			exclude_keywords = ${c.exclude_keywords}, anibis_urls = ${c.anibis_urls},
			notify_to = ${c.notify_to}, updated_at = now()
		WHERE id = 1`;
}

/** Replaces all zones and their postcodes; positions are 1..n in the given order. */
export async function replaceZones(sql: Sql, zones: ZoneInput[]) {
	await sql.transaction([
		sql`DELETE FROM zones`, // zone_npas rows go with ON DELETE CASCADE
		...zones.map(
			(z, i) => sql`
				WITH z AS (INSERT INTO zones (position, name) VALUES (${i + 1}, ${z.name}) RETURNING id)
				INSERT INTO zone_npas (zone_id, npa) SELECT z.id, unnest(${z.npas}::int[]) FROM z`
		)
	]);
}
