<script lang="ts">
	import '../app.css';
</script>

<!-- Main Content -->
<main class="min-h-screen bg-gray-50">
	<slot />
</main>

<!-- Footer -->
<footer class="border-t border-gray-200 bg-white">
	<div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
		<div
			class="flex flex-col items-start justify-between gap-4 text-gray-600 sm:flex-row sm:items-start sm:gap-8"
		>
			<div class="flex-1 space-y-2 text-sm">
				<p class="leading-relaxed">
					Made using
					<a
						href="https://svelte.dev/"
						target="_blank"
						class="text-blue-600 text-muted-foreground underline hover:text-blue-800"
					>
						SvelteKit</a
					>, with assistance from
					<a
						href="https://anthropic.com/claude"
						target="_blank"
						class="text-blue-600 text-muted-foreground underline hover:text-blue-800">Claude</a
					>. Data and code available on
					<a
						href="https://github.com/Vonter/india-vehicle-stats"
						target="_blank"
						class="text-blue-600 text-muted-foreground underline hover:text-blue-800">GitHub</a
					>.
				</p>
				<p class="leading-relaxed text-gray-500">
					Reported vehicle data from 2021 onwards. Numbers may differ slightly from the official <a
						href="https://vahan.parivahan.gov.in/vahan4dashboard/"
						target="_blank"
						class="text-blue-600 text-muted-foreground underline hover:text-blue-800"
						>Vahan Sewa portal</a
					>
					due to data processing delays. In case of major discrepancies, raise an issue on
					<a
						href="https://github.com/Vonter/india-vehicle-stats/issues"
						target="_blank"
						class="text-blue-600 text-muted-foreground underline hover:text-blue-800">GitHub</a
					>.
				</p>
			</div>
		</div>
	</div>
</footer>
