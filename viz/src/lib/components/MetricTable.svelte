<script lang="ts">
	import { formatCount, formatMetricValue } from '../data-loader';
	import type { MetricData } from '../types';
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';

	export let data: MetricData[] = [];
	export let title: string = '';
	export let showMetricColumn: boolean = false;
	export let compact: boolean = false;
	export let selectedMetric: string = 'Vehicle Manufacturer'; // Default to Vehicle Manufacturer

	let searchTerm: string = '';
	let sortBy: 'name' | 'count' = 'count';
	let sortDirection: 'asc' | 'desc' = 'desc';

	// Expand/collapse state for table rows
	let showAllRows = false;

	// Get unique metrics for filtering
	$: uniqueMetrics = [...new Set(data.map((item) => item.Metric))];

	// Filter data first, then get top 100 by count, then apply user sorting
	$: allFilteredData = data.filter((item) => {
		const matchesSearch =
			item.Name.toLowerCase().includes(searchTerm.toLowerCase()) ||
			item.Metric.toLowerCase().includes(searchTerm.toLowerCase());
		const matchesMetric = item.Metric === selectedMetric;
		return matchesSearch && matchesMetric;
	});

	// Get the top 100 largest items by count from filtered data
	$: top100FilteredData = allFilteredData
		.sort((a, b) => b.total_count - a.total_count)
		.slice(0, 100);

	// Apply user's sorting preference to the top 100 items (for collapsed view)
	$: sortedTop100Data = [...top100FilteredData].sort((a, b) => {
		let comparison = 0;
		if (sortBy === 'name') {
			comparison = a.Name.localeCompare(b.Name);
		} else {
			comparison = a.total_count - b.total_count;
		}
		return sortDirection === 'asc' ? comparison : -comparison;
	});

	// Apply user's sorting preference to ALL filtered data (for expanded view)
	$: sortedAllData = [...allFilteredData].sort((a, b) => {
		let comparison = 0;
		if (sortBy === 'name') {
			comparison = a.Name.localeCompare(b.Name);
		} else {
			comparison = a.total_count - b.total_count;
		}
		return sortDirection === 'asc' ? comparison : -comparison;
	});

	// Display logic: show first 20 of top 100 when collapsed, all filtered data when expanded
	$: filteredData = showAllRows ? sortedAllData : sortedTop100Data.slice(0, 20);

	$: isLimited = allFilteredData.length > 100;
	$: hasMoreRows = sortedTop100Data.length > 20 || allFilteredData.length > 100;

	function toggleSort(newSortBy: 'name' | 'count') {
		if (sortBy === newSortBy) {
			// If clicking the same column, toggle direction
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			// If switching to a different column, set appropriate default direction
			sortBy = newSortBy;
			if (newSortBy === 'name') {
				sortDirection = 'asc'; // Default to A-Z for names
			} else {
				sortDirection = 'desc'; // Default to highest-first for counts
			}
		}
	}
</script>

<Card.Root>
	<Card.Content class="p-0">
		<!-- Filters -->
		<div class="border-b p-4">
			<Input type="text" placeholder="Search..." bind:value={searchTerm} class="max-w-sm" />
		</div>

		<!-- Table -->
		<div class="overflow-x-auto">
			<Table.Root>
				<Table.Header>
					<Table.Row>
						{#if showMetricColumn}
							<Table.Head class="pl-6">Metric</Table.Head>
						{/if}
						<Table.Head class={showMetricColumn ? '' : 'pl-6'}>
							<Button
								variant="ghost"
								class="h-auto p-0 text-xs font-medium tracking-wider uppercase hover:bg-transparent"
								onclick={() => toggleSort('name')}
							>
								<div class="flex items-center space-x-1">
									<span>Name</span>
									{#if sortBy === 'name'}
										<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
											{#if sortDirection === 'asc'}
												<path
													fill-rule="evenodd"
													d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L10 6.414 6.707 9.707a1 1 0 01-1.414 0z"
													clip-rule="evenodd"
												/>
											{:else}
												<path
													fill-rule="evenodd"
													d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z"
													clip-rule="evenodd"
												/>
											{/if}
										</svg>
									{/if}
								</div>
							</Button>
						</Table.Head>
						<Table.Head class="pr-12 text-right">
							<Button
								variant="ghost"
								class="ml-auto h-auto p-0 text-xs font-medium tracking-wider uppercase hover:bg-transparent"
								onclick={() => toggleSort('count')}
							>
								<div class="flex items-center justify-end space-x-1">
									<span>Total</span>
									{#if sortBy === 'count'}
										<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
											{#if sortDirection === 'asc'}
												<path
													fill-rule="evenodd"
													d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L10 6.414 6.707 9.707a1 1 0 01-1.414 0z"
													clip-rule="evenodd"
												/>
											{:else}
												<path
													fill-rule="evenodd"
													d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z"
													clip-rule="evenodd"
												/>
											{/if}
										</svg>
									{/if}
								</div>
							</Button>
						</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each filteredData as item, index}
						<Table.Row>
							{#if showMetricColumn}
								<Table.Cell class="max-w-xs pl-6 text-muted-foreground">
									<div class="truncate" title={item.Metric}>
										{item.Metric}
									</div>
								</Table.Cell>
							{/if}
							<Table.Cell class={`font-medium ${showMetricColumn ? '' : 'pl-6'}`}>
								<div class="max-w-xs truncate lg:max-w-sm" title={item.Name}>
									{item.Name}
								</div>
							</Table.Cell>
							<Table.Cell class="font-numbers pr-12 text-right font-semibold">
								{formatMetricValue(item.total_count, selectedMetric)}
							</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>

		{#if filteredData.length === 0}
			<div class="p-8 text-center text-muted-foreground">
				<p>No data found matching your criteria.</p>
			</div>
		{/if}

		{#if filteredData.length > 0}
			<div class="border-t p-4 text-sm text-muted-foreground">
				{#if isLimited}
					{#if showAllRows}
						Showing all {sortedAllData.length} of {allFilteredData.length} items
					{:else}
						Showing first {Math.min(20, sortedTop100Data.length)} of {allFilteredData.length} items
					{/if}
				{:else if allFilteredData.length < data.length}
					{#if showAllRows}
						Showing all {sortedAllData.length} of {data.length} items
					{:else}
						Showing first {Math.min(20, sortedTop100Data.length)} of {data.length} items
					{/if}
				{:else if showAllRows}
					Showing all {sortedAllData.length} items
				{:else}
					Showing first {Math.min(20, sortedTop100Data.length)} items
				{/if}
			</div>

			{#if hasMoreRows}
				<div class="border-t p-4 text-center">
					<button
						on:click={() => (showAllRows = !showAllRows)}
						class="inline-flex items-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-accent hover:text-accent-foreground focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:outline-none"
					>
						{showAllRows ? 'Show Less' : `Show All ${sortedAllData.length} Items`}
						<svg
							class="ml-2 h-4 w-4 {showAllRows
								? 'rotate-180'
								: ''} transition-transform duration-200"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M19 9l-7 7-7-7"
							/>
						</svg>
					</button>
				</div>
			{/if}
		{/if}
	</Card.Content>
</Card.Root>
