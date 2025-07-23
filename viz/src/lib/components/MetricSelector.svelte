<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { calculateMetricSummaries, getAvailableNamesSortedByTotal } from '../data-loader';
	import type { OptimizedMetrics } from '../types';
	import * as Select from '$lib/components/ui/select';

	const dispatch = createEventDispatcher<{
		metricChange: { metric: string; name: string };
	}>();

	export let metrics: OptimizedMetrics;
	export let selectedMetric: string = 'Vehicle Manufacturer';
	export let selectedName: string = 'OLA ELECTRIC TECHNOLOGIES PVT LTD';
	export let showNameSelector: boolean = true;

	// Track initial load to prevent unnecessary dispatches
	let isInitialized = false;

	// Search functionality for name selector
	let nameSearchTerm: string = '';
	let showNameDropdown: boolean = false;

	// Derived values with automatic caching via Svelte's reactivity
	$: availableMetrics = metrics
		? calculateMetricSummaries(metrics).map((summary) => summary.Metric)
		: [];

	// Only compute available names when metric changes and limit to top 100 for performance
	$: allAvailableNames =
		selectedMetric && metrics ? getAvailableNamesSortedByTotal(metrics, selectedMetric) : [];

	// Filter names based on search term
	$: filteredNames = nameSearchTerm
		? allAvailableNames.filter((name) => name.toLowerCase().includes(nameSearchTerm.toLowerCase()))
		: allAvailableNames;

	// Reset name selection when metric changes (but not on initial load)
	$: if (isInitialized && selectedMetric) {
		// Only reset if the current name is not in the new available names
		if (selectedName && !allAvailableNames.includes(selectedName)) {
			dispatch('metricChange', { metric: selectedMetric, name: '' });
		}
	}

	// Mark as initialized after first reactive update
	$: if (metrics && availableMetrics.length > 0) {
		isInitialized = true;
	}

	function handleMetricChange(newMetric: string) {
		if (!isInitialized || newMetric === selectedMetric) return;

		dispatch('metricChange', { metric: newMetric, name: '' });
	}

	function handleNameChange(newName: string) {
		if (!isInitialized || newName === selectedName) return;

		nameSearchTerm = '';
		showNameDropdown = false;
		dispatch('metricChange', { metric: selectedMetric, name: newName });
	}

	function handleNameSearch(event: Event) {
		const target = event.target as HTMLInputElement;
		nameSearchTerm = target.value;
		showNameDropdown = true;
	}

	function selectFilteredName(name: string) {
		handleNameChange(name);
	}

	function clearNameSelection() {
		handleNameChange('');
	}
</script>

<div class="mb-6">
	<!-- Main Metric Heading -->
	<div class="mb-2">
		<Select.Root
			type="single"
			value={selectedMetric}
			onValueChange={handleMetricChange}
			disabled={!isInitialized || availableMetrics.length === 0}
		>
			<Select.Trigger
				class="inline-flex items-center border-none bg-transparent p-0 shadow-none hover:bg-transparent"
			>
				<h1
					class="cursor-pointer text-2xl font-bold tracking-tight text-foreground transition-colors hover:text-primary"
				>
					{selectedMetric || 'Select metric'}
				</h1>
			</Select.Trigger>
			<Select.Content>
				{#each availableMetrics as metric (metric)}
					<Select.Item value={metric} class="text-sm">
						{metric}
					</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	</div>

	<!-- Name Selector -->
	{#if showNameSelector && allAvailableNames.length > 0}
		<div class="relative">
			<!-- Combined Search/Selection Input -->
			<div class="relative w-full max-w-md">
				<input
					type="text"
					placeholder={selectedName ? selectedName : 'Search or select a filter...'}
					value={nameSearchTerm}
					on:input={handleNameSearch}
					on:focus={() => (showNameDropdown = true)}
					class="flex h-8 w-full rounded-md border border-input bg-transparent px-3 py-1 pr-16 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
				/>
				{#if selectedName}
					<button
						on:click={clearNameSelection}
						class="absolute top-1/2 right-8 -translate-y-1/2 transform rounded-sm p-1 text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
						title="Clear selection"
					>
						<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				{/if}
				<svg
					class="absolute top-1/2 right-2 h-4 w-4 -translate-y-1/2 transform text-muted-foreground"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<circle cx="11" cy="11" r="8"></circle>
					<path d="M21 21l-4.35-4.35"></path>
				</svg>
			</div>

			<!-- Filtered Results Dropdown -->
			{#if showNameDropdown && filteredNames.length > 0}
				<div
					class="absolute z-50 mt-1 max-h-60 w-full max-w-md overflow-y-auto rounded-md border border-border bg-popover shadow-lg"
				>
					<div class="p-1">
						{#each filteredNames.slice(0, 50) as name (name)}
							<button
								on:click={() => selectFilteredName(name)}
								class="w-full rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
							>
								{name}
							</button>
						{/each}
						{#if filteredNames.length > 50}
							<div class="px-2 py-1.5 text-xs text-muted-foreground">
								... and {filteredNames.length - 50} more
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Click outside handler to close dropdown -->
<svelte:window
	on:click={(e) => {
		if (e.target && e.target instanceof Element && !e.target.closest('.relative')) {
			showNameDropdown = false;
		}
	}}
/>
