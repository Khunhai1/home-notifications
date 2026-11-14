<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';

	let { children, data } = $props();
</script>

<nav class="top">
	<a href="/" class:on={page.url.pathname === '/'}>Flat finder</a>
	<a href="/settings" class:on={page.url.pathname.startsWith('/settings')}>Settings</a>
	<span class="user">{data.user}</span>
</nav>

{@render children()}
