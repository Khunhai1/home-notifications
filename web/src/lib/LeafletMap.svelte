<script lang="ts" module>
	export interface MapPoint {
		lat: number;
		lon: number;
		color: string;
		/** Popup link, e.g. to the listing's card. */
		href?: string;
		label: string;
	}
</script>

<script lang="ts">
	import 'leaflet/dist/leaflet.css';
	import { onMount } from 'svelte';
	import type * as Leaflet from 'leaflet';

	let {
		points,
		fallback = null,
		height = '320px',
		radius = 7
	}: {
		points: MapPoint[];
		/** Where to look when there are no points; Switzerland otherwise. */
		fallback?: [number, number] | null;
		height?: string;
		radius?: number;
	} = $props();

	let el: HTMLDivElement;
	let L = $state<typeof Leaflet>();
	let map: Leaflet.Map | undefined;
	let layer: Leaflet.LayerGroup | undefined;

	onMount(() => {
		let observer: ResizeObserver | undefined;
		let cancelled = false;
		import('leaflet').then((mod) => {
			if (cancelled) return;
			const leaflet = (mod.default ?? mod) as typeof Leaflet;
			map = leaflet.map(el);
			leaflet
				.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
					maxZoom: 19,
					attribution: '&copy; OpenStreetMap'
				})
				.addTo(map);
			layer = leaflet.layerGroup().addTo(map);
			// The map has no size yet when the page loads in a background tab.
			observer = new ResizeObserver(() => map?.invalidateSize());
			observer.observe(el);
			L = leaflet;
		});
		return () => {
			cancelled = true;
			observer?.disconnect();
			map?.remove();
		};
	});

	$effect(() => {
		if (!L || !map || !layer) return;
		layer.clearLayers();
		for (const p of points) {
			const marker = L.circleMarker([p.lat, p.lon], {
				radius,
				color: '#fff',
				weight: 2,
				fillColor: p.color,
				fillOpacity: 0.9
			}).addTo(layer);
			const content = document.createElement(p.href ? 'a' : 'span');
			if (p.href) (content as HTMLAnchorElement).href = p.href;
			content.textContent = p.label;
			marker.bindPopup(content);
		}
		map.invalidateSize();
		if (points.length) map.fitBounds(L.latLngBounds(points.map((p) => [p.lat, p.lon])).pad(0.1));
		else if (fallback) map.setView(fallback, 12);
		else map.setView([46.8, 8.2], 8);
	});
</script>

<div class="map" bind:this={el} style:height></div>

<style>
	.map { border-radius:10px; margin-bottom:16px; border:1px solid var(--line); z-index:0; }
</style>
