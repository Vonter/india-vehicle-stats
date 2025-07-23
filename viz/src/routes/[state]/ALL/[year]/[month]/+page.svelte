<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		loadStateData,
		loadStateMonthData,
		generateBreadcrumbs,
		flattenMetrics,
		getFilteredMetricSummaries,
		getMonthName,
		calculateTotalsByMetric,
		calculateTotalsByMetricSimple,
		formatMetricValue,
		formatNumber,
		filterMetricsByYearMonth
	} from '../../../../../lib/data-loader';
	import type { StateData } from '../../../../../lib/types';

	import Breadcrumb from '../../../../../lib/components/Breadcrumb.svelte';
	import StatsCard from '../../../../../lib/components/StatsCard.svelte';
	import MetricTable from '../../../../../lib/components/MetricTable.svelte';
	import LoadingSpinner from '../../../../../lib/components/LoadingSpinner.svelte';
	import MetricSelector from '../../../../../lib/components/MetricSelector.svelte';

	let data: StateData | null = null;
	let loading = true;
	let error = '';
	let state: string;
	let year: string;
	let month: string;

	// Metric selection state - read from URL params
	let selectedMetric = 'Vehicle Manufacturer';
	let selectedName = 'OLA ELECTRIC TECHNOLOGIES PVT LTD';

	$: state = $page.params.state;
	$: year = $page.params.year;
	$: month = $page.params.month;
	$: breadcrumbs = generateBreadcrumbs('state-month', state, undefined, year, month);

	// Flag to prevent circular updates
	let isUpdatingFromURL = false;

	// Read URL parameters and update selections (only when URL actually changes)
	$: {
		if (!isUpdatingFromURL) {
			const urlMetric = $page.url.searchParams.get('metric');
			const urlName = $page.url.searchParams.get('name');

			if (urlMetric && urlMetric !== selectedMetric) {
				selectedMetric = urlMetric;
			} else if (!urlMetric && selectedMetric !== 'Vehicle Manufacturer') {
				selectedMetric = 'Vehicle Manufacturer';
			}

			// Handle URL name parameter: null means not present (use default), empty string means "All"
			if (urlName !== null && urlName !== selectedName) {
				selectedName = urlName; // Can be empty string for "All"
			} else if (
				urlName === null &&
				selectedName !== 'OLA ELECTRIC TECHNOLOGIES PVT LTD' &&
				!$page.url.searchParams.has('name')
			) {
				selectedName = 'OLA ELECTRIC TECHNOLOGIES PVT LTD'; // Default when no URL param
			}
		}
	}

	// Update URL when selections change
	function updateURL() {
		isUpdatingFromURL = true;
		const url = new URL($page.url);
		if (selectedMetric !== 'Vehicle Manufacturer') {
			url.searchParams.set('metric', selectedMetric);
		} else {
			url.searchParams.delete('metric');
		}
		if (selectedName !== 'OLA ELECTRIC TECHNOLOGIES PVT LTD') {
			url.searchParams.set('name', selectedName); // This includes empty string for "All"
		} else {
			url.searchParams.delete('name'); // Default case
		}
		goto(url.toString(), { replaceState: true, keepFocus: true }).then(() => {
			isUpdatingFromURL = false;
		});
	}

	// Helper function to build query string for navigation
	function buildQueryString() {
		const params = new URLSearchParams();
		if (selectedMetric !== 'Vehicle Manufacturer') {
			params.set('metric', selectedMetric);
		}
		if (selectedName !== 'OLA ELECTRIC TECHNOLOGIES PVT LTD') {
			params.set('name', selectedName); // This includes empty string for "All"
		}
		const queryString = params.toString();
		return queryString ? `?${queryString}` : '';
	}

	onMount(async () => {
		await loadData();
	});

	// Reload data when parameters change
	$: if (state && year && month) {
		loadData();
	}

	async function loadData() {
		loading = true;
		error = '';

		try {
			const rawData = await loadStateMonthData(state, parseInt(year), parseInt(month));
			data = rawData;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load state data';
		} finally {
			loading = false;
		}
	}

	// Transform optimized metrics to flat arrays for display
	$: flatMetrics = data ? flattenMetrics(data.metrics) : [];
	$: filteredMetricSummaries = data ? getFilteredMetricSummaries(data.metrics) : [];
	$: monthName = getMonthName(parseInt(month));

	// Update RTO totals based on selected metric
	$: rtosWithMetricTotals =
		data && selectedMetric && data.rtos
			? data.rtos
					.map((rto) => ({
						...rto,
						metric_total: calculateTotalsByMetricSimple(
							rto.metrics,
							selectedMetric,
							selectedName || undefined
						),
						formatted_total: formatMetricValue(
							calculateTotalsByMetricSimple(rto.metrics, selectedMetric, selectedName || undefined),
							selectedMetric
						)
					}))
					.sort((a, b) =>
						selectedMetric ? b.metric_total - a.metric_total : b.total_count - a.total_count
					)
					// Filter out RTOs with no data for this year/month/metric
					.filter((rto) => (selectedMetric ? rto.metric_total > 0 : rto.total_count > 0))
			: [];

	// Expand/collapse state for RTOs
	let showAllRTOs = false;

	// Displayed RTOs based on expand/collapse state
	$: displayedRTOs = showAllRTOs ? rtosWithMetricTotals : rtosWithMetricTotals.slice(0, 10);

	// Check if we have more than 10 RTOs
	$: hasMoreRTOs = rtosWithMetricTotals.length > 10;

	// Calculate total for current selection
	$: currentTotal =
		data && selectedMetric
			? calculateTotalsByMetric(data.metrics, selectedMetric, selectedName || undefined)
			: 0;
	$: formattedCurrentTotal = formatMetricValue(currentTotal, selectedMetric);
</script>

<svelte:head>
	<title>{state} Vehicle Statistics - {monthName} {year}</title>
</svelte:head>

<div class="min-h-screen bg-background">
	<div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<Breadcrumb items={breadcrumbs} />

		<!-- Header -->
		<div class="mb-8">
			<h1 class="mb-2 text-3xl font-bold text-foreground sm:text-4xl">
				{state} Vehicle Statistics - {monthName}
				{year}
			</h1>
		</div>

		{#if loading}
			<LoadingSpinner size="large" text="Loading {state} {monthName} {year} data..." />
		{:else if error}
			<div class="rounded-lg border border-destructive/30 bg-destructive/15 p-4">
				<h3 class="mb-2 text-lg font-semibold text-destructive">Error Loading Data</h3>
				<p class="text-destructive/80">{error}</p>
				<div class="mt-3 space-x-4">
					<a
						href={`/${state}/ALL/${year}${buildQueryString()}`}
						class="text-primary underline hover:text-primary/80"
					>
						← Back to {state}
						{year} overview
					</a>
					<a
						href={`/ALL/${year}/${month}${buildQueryString()}`}
						class="text-primary underline hover:text-primary/80"
					>
						Back to {monthName}
						{year} overview
					</a>
				</div>
			</div>
		{:else if data}
			<!-- Check if there's data for this month -->
			{#if flatMetrics.length === 0}
				<div class="rounded-lg border border-yellow-200 bg-yellow-50 p-6 text-center">
					<h3 class="mb-2 text-lg font-semibold text-yellow-800">No Data Available</h3>
					<p class="mb-4 text-yellow-700">
						No transaction records found for {state} in {monthName}
						{year}.
					</p>
					<div class="space-x-4">
						<a
							href={`/${state}/ALL/${year}${buildQueryString()}`}
							class="text-blue-600 underline hover:text-blue-800"
						>
							← Back to {state}
							{year} overview
						</a>
						<a
							href={`/ALL/${year}/${month}${buildQueryString()}`}
							class="text-blue-600 underline hover:text-blue-800"
						>
							Back to {monthName}
							{year} overview
						</a>
					</div>
				</div>
			{:else}
				<!-- Standard Metric Summaries -->
				<div class="mb-8">
					<div class="rounded-lg border border-border bg-card p-6">
						<h2 class="mb-4 text-lg font-semibold text-muted-foreground">
							Total in {monthName}
							{year}
						</h2>
						<div class="grid grid-cols-2 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
							{#each filteredMetricSummaries as metric}
								<div class="rounded bg-muted p-3 text-center">
									<div class="mb-1 text-xs font-medium text-muted-foreground">
										{metric.Metric}
									</div>
									<div class="font-numbers text-sm font-bold text-foreground">
										{metric.formatted_value}
									</div>
								</div>
							{/each}
						</div>
					</div>
				</div>

				<!-- Metric Selector -->
				<MetricSelector
					metrics={data.metrics}
					{selectedMetric}
					{selectedName}
					on:metricChange={(e) => {
						selectedMetric = e.detail.metric;
						selectedName = e.detail.name;
						updateURL();
					}}
				/>

				<!-- RTO Navigation -->
				{#if rtosWithMetricTotals.length > 0}
					<div class="mb-8">
						<h2 class="mb-4 text-xl font-bold text-foreground">
							Total by RTO in {monthName}
							{year}
							{#if selectedName}
								<span class="text-base text-muted-foreground">({selectedName})</span>
							{:else}
								<span class="text-base text-muted-foreground">({selectedMetric})</span>
							{/if}
						</h2>
						<div class="grid grid-cols-2 gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
							{#each displayedRTOs as rto}
								<StatsCard
									title={rto['RTO Name'] || `${state} RTO ${rto.RTO}`}
									value={selectedMetric ? rto.metric_total : rto.total_count}
									formattedValue={selectedMetric
										? rto.formatted_total
										: formatNumber(rto.total_count)}
									subtitle={`RTO ${rto.RTO}`}
									href={`/${state}/${rto.RTO}/${year}/${month}${buildQueryString()}`}
									compact={false}
									metric={selectedMetric}
								/>
							{/each}
						</div>
						{#if hasMoreRTOs}
							<div class="mt-4 text-center">
								<button
									on:click={() => (showAllRTOs = !showAllRTOs)}
									class="inline-flex items-center rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-accent hover:text-accent-foreground focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:outline-none"
								>
									{showAllRTOs ? 'Show Less' : `Show All ${rtosWithMetricTotals.length} RTOs`}
									<svg
										class="ml-2 h-4 w-4 {showAllRTOs
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
					</div>
				{/if}

				<!-- Detailed Metrics -->
				<div class="mb-8">
					<h2 class="mb-4 text-xl font-bold text-foreground">
						List of {selectedMetric} in {state} - {monthName}
						{year}
					</h2>
					<MetricTable data={flatMetrics} title={selectedMetric} {selectedMetric} />
				</div>
			{/if}
		{/if}
	</div>
</div>
