<script lang="ts">
	import { enhance } from '$app/forms';
	import { onMount, untrack } from 'svelte';
	import LeafletMap, { type MapPoint } from '$lib/LeafletMap.svelte';
	import { zoneColor } from '$lib/format';
	import { suggest, toPlace, type NpaRow, type Place } from '$lib/npa';

	interface SavedZone {
		position: number;
		name: string;
		npas: number[];
	}
	interface EditZone {
		key: number;
		name: string;
		npas: number[];
		query: string;
	}

	let {
		saved,
		known,
		error = undefined,
		success = false
	}: {
		saved: SavedZone[];
		/** Places of the saved postcodes, until the full list is loaded. */
		known: Record<number, Place>;
		error?: string;
		success?: boolean;
	} = $props();

	let nextKey = 0;
	const fromSaved = (list: SavedZone[]): EditZone[] =>
		list.map((z) => ({ key: nextKey++, name: z.name, npas: [...z.npas], query: '' }));

	let zones = $state(untrack(() => fromSaved(saved)));
	let all = $state.raw<Place[]>([]);
	let loadError = $state(false);
	let saving = $state(false);

	onMount(async () => {
		try {
			const res = await fetch('/npa.json');
			all = ((await res.json()) as NpaRow[]).map(toPlace);
		} catch {
			loadError = true;
		}
	});

	let lookup = $derived(new Map(all.map((p) => [p.npa, p])));
	const placeOf = (n: number): Place | undefined => lookup.get(n) ?? known[n];
	const isUnknown = (n: number) => all.length > 0 && !lookup.has(n);

	/** Zone number (1-based) that already holds the postcode, other than `index`. */
	function otherZone(n: number, index: number) {
		const i = zones.findIndex((z, j) => j !== index && z.npas.includes(n));
		return i < 0 ? 0 : i + 1;
	}

	const serialize = (list: { name: string; npas: number[] }[]) =>
		JSON.stringify(list.map((z) => ({ name: z.name.trim(), npas: z.npas })));
	let json = $derived(serialize(zones));
	let dirty = $derived(json !== serialize(saved));

	function addZone() {
		zones.push({ key: nextKey++, name: `Zone ${zones.length + 1}`, npas: [], query: '' });
	}
	function move(i: number, by: number) {
		const [z] = zones.splice(i, 1);
		zones.splice(i + by, 0, z);
	}
	function addNpa(z: EditZone, n: number) {
		if (!z.npas.includes(n)) z.npas.push(n);
		z.query = '';
	}
	function onKey(e: KeyboardEvent, z: EditZone) {
		if (e.key !== 'Enter') return;
		e.preventDefault();
		const q = z.query.trim();
		if (/^\d{4}$/.test(q)) addNpa(z, Number(q));
		else {
			const first = suggest(all, q, 1)[0];
			if (first) addNpa(z, first.npa);
		}
	}

	let points = $derived(
		zones.flatMap((z, i) =>
			z.npas.flatMap((n): MapPoint[] => {
				const p = placeOf(n);
				return p ? [{ lat: p.lat, lon: p.lon, color: zoneColor(i + 1), label: `${n} ${p.names}` }] : [];
			})
		)
	);
</script>

<form
	method="post"
	action="?/zones"
	use:enhance={() => {
		saving = true;
		return async ({ result, update }) => {
			await update({ reset: false });
			saving = false;
			if (result.type === 'success') zones = fromSaved(saved);
		};
	}}
>
	<input type="hidden" name="zones" value={json} />

	{#each zones as z, i (z.key)}
		<div class="zone-edit" style:--z={zoneColor(i + 1)}>
			<div class="zone-head">
				<span class="badge zone">{i + 1}</span>
				<input class="name" bind:value={z.name} aria-label="Name of zone {i + 1}" />
				<button type="button" onclick={() => move(i, -1)} disabled={i === 0} title="Move up">↑</button>
				<button
					type="button"
					onclick={() => move(i, 1)}
					disabled={i === zones.length - 1}
					title="Move down">↓</button
				>
				<button type="button" onclick={() => zones.splice(i, 1)} title="Delete zone">Delete</button>
			</div>

			<div class="chips">
				{#each z.npas as n (n)}
					{@const p = placeOf(n)}
					{@const other = otherZone(n, i)}
					<span class="chip" class:bad={isUnknown(n) || other}>
						<b>{n}</b>
						{p?.names ?? ''}
						{#if isUnknown(n)}<em>unknown postcode</em>{/if}
						{#if other}<em>also in zone {other}</em>{/if}
						<button
							type="button"
							class="x"
							onclick={() => z.npas.splice(z.npas.indexOf(n), 1)}
							aria-label="Remove {n}">×</button
						>
					</span>
				{/each}
				{#if !z.npas.length}<span class="meta">No postcodes yet.</span>{/if}
			</div>

			<div class="add">
				<input
					bind:value={z.query}
					onkeydown={(e) => onKey(e, z)}
					placeholder="Add a postcode or village…"
					aria-label="Add a postcode to zone {i + 1}"
					autocomplete="off"
				/>
				{#if z.query.trim()}
					<div class="suggestions">
						{#each suggest(all, z.query) as s (s.npa)}
							<button type="button" onclick={() => addNpa(z, s.npa)}>
								<b>{s.npa}</b>
								{s.names}
							</button>
						{:else}
							<span class="meta">
								{#if /^\d{4}$/.test(z.query.trim())}Press Enter to add {z.query.trim()}.{:else}No match.{/if}
							</span>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	{/each}

	{#if loadError}<p class="error">Could not load the postcode list; suggestions are off.</p>{/if}

	<div class="row">
		<button type="button" onclick={addZone}>+ Add zone</button>
		<button class="primary" disabled={saving || !dirty}>Save zones</button>
		{#if dirty}<span class="meta">Unsaved changes</span>{/if}
		{#if error}<span class="error">{error}</span>{/if}
		{#if success && !dirty}<span class="success">Zones saved.</span>{/if}
	</div>
</form>

<LeafletMap {points} height="260px" radius={6} />

<style>
	.zone-edit { border:1px solid var(--line); border-left:4px solid var(--z); border-radius:8px; padding:10px; margin-bottom:10px; }
	.zone-head { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
	.zone-head .name { flex:1 1 160px; min-width:0; font-weight:600; }
	.chips { display:flex; flex-wrap:wrap; gap:6px; margin:8px 0; }
	.chip { display:inline-flex; align-items:center; gap:4px; font-size:13px; border:1px solid var(--line); border-radius:999px; padding:1px 4px 1px 9px; background:var(--bg); }
	.chip.bad { border-color:var(--error); color:var(--error); }
	.chip em { font-size:12px; }
	.chip .x { border:none; background:none; padding:0 5px; line-height:1.2; font-size:16px; color:inherit; }
	.add { position:relative; }
	.add input { width:100%; max-width:360px; }
	.suggestions { display:flex; flex-direction:column; align-items:stretch; max-width:360px; margin-top:4px; gap:2px; }
	.suggestions button { text-align:left; border-radius:4px; }
	.row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:12px 0; }
</style>
