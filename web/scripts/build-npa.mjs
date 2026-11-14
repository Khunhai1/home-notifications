// Turns ../homenotif/data/npa.csv into static/npa.json: [[npa, "Village A, Village B", lat, lon], ...].
// The browser fetches /npa.json for suggestions; the server imports the same file for validation.
import { readFileSync, writeFileSync } from 'node:fs';

const src = new URL('../../homenotif/data/npa.csv', import.meta.url);
const out = new URL('../static/npa.json', import.meta.url);

const lines = readFileSync(src, 'utf8').split(/\r?\n/).filter((l) => l && !l.startsWith('#'));
const header = lines.shift().split(';');
const col = (name) => header.indexOf(name);
const [iNpa, iLoc, iLat, iLon] = ['npa', 'localities', 'lat', 'lon'].map(col);

const rows = lines.map((line) => {
	const f = line.split(';');
	return [Number(f[iNpa]), f[iLoc].split('|').join(', '), Number(f[iLat]), Number(f[iLon])];
});
writeFileSync(out, JSON.stringify(rows) + '\n');
console.log(`npa.json: ${rows.length} postcodes`);
