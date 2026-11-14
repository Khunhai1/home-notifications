<script lang="ts">
	import { enhance } from '$app/forms';
	import ZoneEditor from '$lib/ZoneEditor.svelte';
	import { when } from '$lib/format';

	let { data, form } = $props();

	let s = $derived(data.settings);
	let errors = $derived<Record<string, string>>(
		(form?.criteria && 'errors' in form.criteria && form.criteria.errors) || {}
	);
	let checking = $state(false);
	let savingCriteria = $state(false);

	// Keep what was typed when the server rejects the form.
	const keepInput = () => {
		savingCriteria = true;
		return async ({ update }: { update: (o?: { reset?: boolean }) => Promise<void> }) => {
			await update({ reset: false });
			savingCriteria = false;
		};
	};
</script>

<svelte:head><title>Settings · Flat finder</title></svelte:head>

<main>
	<h1>Settings</h1>
	<p class="meta note">
		Changes apply at the next check (every 15 min). Last check: {data.lastFetch
			? when(data.lastFetch)
			: 'never'}.
	</p>

	{#if data.canDispatch}
		<form
			class="panel row"
			method="post"
			action="?/check"
			use:enhance={() => {
				checking = true;
				return async ({ update }) => {
					await update();
					checking = false;
				};
			}}
		>
			<button class="primary" disabled={checking}>{checking ? 'Starting…' : 'Check now'}</button>
			{#if form?.check && 'started' in form.check}
				<span class="success">Check started; new listings appear in a minute or two.</span>
			{:else if form?.check && 'error' in form.check}
				<span class="error">{form.check.error}</span>
			{/if}
		</form>
	{/if}

	<section class="panel">
		<h2>Criteria</h2>
		<form method="post" action="?/criteria" use:enhance={keepInput} class="criteria">
			<fieldset>
				<legend>Rooms</legend>
				<label>Min <input name="min_rooms" type="number" min="0" step="0.5" value={s.min_rooms} /></label>
				<label>Max <input name="max_rooms" type="number" min="0" step="0.5" value={s.max_rooms} /></label>
				<span class="meta">0 = no limit</span>
				{#if errors.min_rooms}<p class="error">Min: {errors.min_rooms}</p>{/if}
				{#if errors.max_rooms}<p class="error">Max: {errors.max_rooms}</p>{/if}
			</fieldset>
			<fieldset>
				<legend>Rent (CHF / month)</legend>
				<label>Min <input name="min_rent" type="number" min="0" step="50" value={s.min_rent} /></label>
				<label>Max <input name="max_rent" type="number" min="0" step="50" value={s.max_rent} /></label>
				<span class="meta">0 = no limit</span>
				{#if errors.min_rent}<p class="error">Min: {errors.min_rent}</p>{/if}
				{#if errors.max_rent}<p class="error">Max: {errors.max_rent}</p>{/if}
			</fieldset>
			<fieldset>
				<legend>Area</legend>
				<label>Min m² <input name="min_area" type="number" min="0" step="1" value={s.min_area} /></label>
				{#if errors.min_area}<p class="error">{errors.min_area}</p>{/if}
			</fieldset>

			<label class="block">
				Exclude listings containing (one keyword per line)
				<textarea name="exclude_keywords" rows="4">{s.exclude_keywords.join('\n')}</textarea>
			</label>
			<label class="block">
				Anibis search URLs (one per line)
				<textarea name="anibis_urls" rows="3" placeholder="https://www.anibis.ch/…"
					>{s.anibis_urls.join('\n')}</textarea
				>
				{#if errors.anibis_urls}<span class="error">{errors.anibis_urls}</span>{/if}
			</label>
			<label class="block">
				Notification email
				<input name="notify_to" type="email" value={s.notify_to} />
				{#if errors.notify_to}<span class="error">{errors.notify_to}</span>{/if}
			</label>

			<div class="row">
				<button class="primary" disabled={savingCriteria}>Save criteria</button>
				{#if form?.criteria && 'saved' in form.criteria}
					<span class="success">Saved.</span>
				{:else if Object.keys(errors).length}
					<span class="error">Not saved: fix the fields above.</span>
				{/if}
				<span class="meta">Last saved {when(s.updated_at)}</span>
			</div>
		</form>
	</section>

	<section class="panel">
		<h2>Zones</h2>
		<p class="meta">
			In order of preference. Listings outside every zone don't match. Each postcode can be in
			one zone only.
		</p>
		<ZoneEditor
			saved={data.zones}
			known={data.places}
			error={form?.zones && 'error' in form.zones ? form.zones.error : undefined}
			success={Boolean(form?.zones && 'saved' in form.zones)}
		/>
	</section>
</main>

<style>
	main { max-width:760px; }
	.note { margin:-6px 0 14px; }
	.row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
	.criteria { display:flex; flex-direction:column; gap:12px; }
	fieldset { border:1px solid var(--line); border-radius:8px; padding:8px 12px 10px; display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:0; }
	fieldset p { flex-basis:100%; margin:0; }
	legend { font-weight:600; padding:0 4px; }
	fieldset input { width:110px; }
	.block { display:flex; flex-direction:column; gap:4px; }
	textarea { width:100%; resize:vertical; }
	.block input { max-width:360px; }
</style>
