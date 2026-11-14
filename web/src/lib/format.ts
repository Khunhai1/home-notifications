export const ZONE_COLORS: Record<number, string> = {
	1: '#2e8540',
	2: '#1a5fb4',
	3: '#c46200',
	4: '#8a3ab9'
};
export const NO_ZONE_COLOR = '#77776f';

export const zoneColor = (zone: number | null | undefined) =>
	(zone && ZONE_COLORS[zone]) || NO_ZONE_COLOR;

/** 1234.5 -> "1'235", null -> "?" */
export function chf(value: number | null): string {
	if (value == null) return '?';
	return String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
}

const dateFormat = new Intl.DateTimeFormat('en-GB', {
	day: '2-digit',
	month: 'short',
	hour: '2-digit',
	minute: '2-digit',
	timeZone: 'Europe/Zurich'
});

/** ISO timestamp -> "14 Nov 09:30" (Swiss time), "" when missing or invalid. */
export function when(iso: string | null | undefined): string {
	if (!iso) return '';
	const d = new Date(iso);
	return Number.isNaN(d.getTime()) ? '' : dateFormat.format(d);
}
