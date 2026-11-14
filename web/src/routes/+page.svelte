<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import LeafletMap, { type MapPoint } from '$lib/LeafletMap.svelte';
	import { extraFilterCount, filterParams, PERIODS, SORTS, type Status } from '$lib/filters';
	import { chf, when, zoneColor } from '$lib/format';

	let { data } = $props();

	type Listing = (typeof data.listings)[number];

	const tabs: [Status | '', string][] = [
		['', 'All'],
		['new', 'New'],
		['favorite', 'Favorites'],
		['applied', 'Applied'],
		['hidden', 'Hidden']
	];

	/** Current filters with some overridden, as a query string. */
	const query = (over: Record<string, string> = {}) => filterParams(data.filter, over);

	const facts = (l: Listing) => `CHF ${chf(l.rent)} · ${l.rooms ?? '?'} rooms`;
	const toggle = (current: Status, target: Status) => (current === target ? 'new' : target);
	const submit = (e: Event) => (e.currentTarget as HTMLInputElement).form?.requestSubmit();

	/** Navigate with only the filters that are set, so URLs stay short and shareable. */
	function applyFilters(e: SubmitEvent) {
		e.preventDefault();
		const params = new URLSearchParams();
		for (const [k, v] of new FormData(e.currentTarget as HTMLFormElement)) {
			const value = String(v).trim();
			if (value && value !== '0' && !(k === 'sort' && value === 'newest')) params.set(k, value);
		}
		goto(`?${params}`, { keepFocus: true, noScroll: true });
	}

	const perM2 = (l: Listing) => (l.rent && l.area ? Math.round(l.rent / l.area) : null);

	let count = $derived(data.listings.length);
	let extras = $derived(extraFilterCount(data.filter));
	let points = $derived(
		data.listings
			.filter((l) => l.lat != null && l.lon != null)
			.map(
				(l): MapPoint => ({
					lat: l.lat!,
					lon: l.lon!,
					color: zoneColor(l.zone),
					href: `#l${l.id}`,
					label: facts(l)
				})
			)
	);
</script>

<svelte:head><title>Flat finder</title></svelte:head>

<main>
	<h1>
		Flat finder
		<span class="meta">{count} listing{count === 1 ? '' : 's'}</span>
		<span class="meta">· last check {data.lastFetch ? when(data.lastFetch) : 'never'}</span>
	</h1>

	<div class="bar">
		<div class="tabs">
			{#each tabs as [value, label] (value)}
				<a class="tab" class:on={data.filter.status === value} href="?{query({ status: value })}">
					{label}
				</a>
			{/each}
		</div>
		<form method="get" class="filters" onsubmit={applyFilters}>
			{#if data.filter.status}<input type="hidden" name="status" value={data.filter.status} />{/if}
			{#if data.zones.length}
				<select name="zone" onchange={submit} aria-label="Zone">
					<option value="">All zones</option>
					{#each data.zones as z (z.position)}
						<option value={String(z.position)} selected={z.position === data.filter.zone}>
							Zone {z.position}: {z.name}
						</option>
					{/each}
				</select>
			{/if}
			<select name="source" onchange={submit} aria-label="Source">
				<option value="">All sources</option>
				{#each data.sources as s (s)}
					<option value={s} selected={s === data.filter.source}>{s}</option>
				{/each}
			</select>
			<select name="sort" onchange={submit} aria-label="Sort">
				{#each Object.entries(SORTS) as [value, label] (value)}
					<option {value} selected={value === data.filter.sort}>{label}</option>
				{/each}
			</select>
			<label>
				<input
					type="checkbox"
					name="all"
					value="1"
					checked={data.filter.includeUnmatched}
					onchange={submit}
				/>
				include listings outside my criteria
			</label>
			<details class="more" open={extras > 0}>
				<summary>More filters{extras ? ` (${extras})` : ''}</summary>
				<div class="more-fields">
					<input
						type="search"
						name="q"
						value={data.filter.q}
						placeholder="Search title, street, town…"
						aria-label="Search"
					/>
					<label>
						Max rent
						<input type="number" name="max_rent" aria-label="Max rent" min="0" step="50" inputmode="numeric"
							value={data.filter.maxRent || ''} placeholder="CHF" />
					</label>
					<label>
						Min rooms
						<input type="number" name="min_rooms" aria-label="Min rooms" min="0" step="0.5" inputmode="decimal"
							value={data.filter.minRooms || ''} />
					</label>
					<label>
						Min area
						<input type="number" name="min_area" aria-label="Min area" min="0" step="5" inputmode="numeric"
							value={data.filter.minArea || ''} placeholder="m²" />
					</label>
					<select name="days" onchange={submit} aria-label="Added">
						{#each Object.entries(PERIODS) as [value, label] (value)}
							<option {value} selected={Number(value) === data.filter.days}>{label}</option>
						{/each}
					</select>
					<button class="primary">Apply</button>
					{#if extras}
						<a href="?{query({ q: '', max_rent: '', min_rooms: '', min_area: '', days: '' })}">Clear</a>
					{/if}
				</div>
				<p class="meta">Listings with an unknown rent, room count or area are left out while that filter is set.</p>
			</details>
		</form>
	</div>

	{#if data.zones.length}
		<details class="zones panel">
			<summary>Zones</summary>
			<div class="zone-list">
				{#each data.zones as z (z.position)}
					<div>
						<h3>
							<span class="badge zone" style:--z={zoneColor(z.position)}>{z.position}</span>
							{z.name}
						</h3>
						{#each z.places as p (p.npa)}<p><b>{p.npa}</b> {p.names}</p>{/each}
						{#if !z.places.length}<p class="meta">No postcodes yet.</p>{/if}
					</div>
				{/each}
			</div>
		</details>
	{/if}

	<LeafletMap {points} fallback={data.center} />

	{#if !count}
		<p class="empty">
			{extras || data.filter.zone || data.filter.source || data.filter.status
				? 'No listings match these filters.'
				: 'Nothing here yet.'}
		</p>
	{/if}

	<div class="grid">
		{#each data.listings as l (l.id)}
			<div
				class="card"
				class:dim={!l.matched}
				class:zoned={l.zone}
				style:--z={zoneColor(l.zone)}
				id="l{l.id}"
			>
				{#if l.image_url}
					<a href={l.url} target="_blank" rel="noopener">
						<img src={l.image_url} alt="" loading="lazy" referrerpolicy="no-referrer" />
					</a>
				{/if}
				<div class="body">
					<a class="title" href={l.url} target="_blank" rel="noopener">{l.title}</a>
					<div class="facts">
						<b>CHF {chf(l.rent)}</b> · {l.rooms ?? '?'} rooms{#if l.area}{' '}· {Math.round(l.area)} m²{/if}
						{#if perM2(l)}<span class="per-m2">CHF {perM2(l)}/m²</span>{/if}
					</div>
					<div class="meta">{l.street} {l.zipcode ?? ''} {l.city}</div>
					<div class="meta">
						{#if l.zone}<span class="badge zone">Zone {l.zone}</span>{/if}
						<span class="badge">{l.source}</span>
						{#each l.also_on as d (d.url)}
							<a class="badge" href={d.url} target="_blank" rel="noopener">also on {d.source}</a>
						{/each}
						{when(l.date)}
					</div>
				</div>
				<form class="actions" method="post" action="?{query()}&/status" use:enhance>
					<input type="hidden" name="id" value={l.id} />
					<button
						name="status"
						value={toggle(l.status, 'favorite')}
						class:on={l.status === 'favorite'}>★ Favorite</button
					>
					<button
						name="status"
						value={toggle(l.status, 'applied')}
						class:on={l.status === 'applied'}>✓ Applied</button
					>
					<button name="status" value={toggle(l.status, 'hidden')}>
						{l.status === 'hidden' ? 'Unhide' : 'Hide'}
					</button>
				</form>
			</div>
		{/each}
	</div>
</main>

<style>
	.bar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:14px; }
	.tabs, .filters { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
	.tab { padding:5px 12px; border:1px solid var(--line); border-radius:999px; color:var(--text); background:var(--card); }
	.tab.on { background:var(--accent); border-color:var(--accent); color:#fff; }
	.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:14px; }
	.card { background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; display:flex; flex-direction:column; scroll-margin-top:12px; }
	.card.dim { opacity:.55; }
	.card.zoned { border-top:4px solid var(--z); }
	.card:target { outline:2px solid var(--accent); }
	.card img { width:100%; height:170px; object-fit:cover; display:block; background:var(--line); }
	.body { padding:10px 12px; flex:1; }
	.title { font-weight:600; display:block; margin-bottom:4px; overflow-wrap:anywhere; }
	.facts { font-size:16px; }
	.actions { display:flex; flex-wrap:wrap; gap:6px; padding:0 12px 12px; }
	.actions button.on { background:var(--accent); border-color:var(--accent); color:#fff; }
	.empty { color:var(--muted); padding:40px 0; text-align:center; }
	.per-m2 { color:var(--muted); font-size:13px; margin-left:4px; white-space:nowrap; }
	details.more { flex-basis:100%; }
	details.more summary { cursor:pointer; color:var(--accent); width:max-content; }
	.more-fields { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-top:8px; }
	.more-fields label { display:flex; gap:6px; align-items:center; color:var(--muted); font-size:13px; }
	.more-fields input[type='number'] { width:90px; }
	.more-fields input[type='search'] { flex:1 1 220px; min-width:0; }
	details.zones { padding:8px 12px; }
	details.zones summary { cursor:pointer; font-weight:600; }
	.zone-list { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:12px; margin-top:8px; font-size:13px; }
	.zone-list h3 { font-size:14px; margin:0 0 4px; }
	.zone-list p { margin:2px 0; }
	@media (max-width: 600px) {
		.grid { grid-template-columns:1fr; }
		.filters select { flex:1 1 140px; min-width:0; }
		.more-fields label { flex:1 1 140px; justify-content:space-between; }
		.more-fields input[type='number'] { width:auto; flex:1; min-width:0; }
	}
</style>
