<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		loadRTOData,
		generateBreadcrumbs,
		getMonthName,
		flattenMetrics,
		getFilteredMetricSummaries,
		getMonthlyTrendsByMetric,
		calculateTotalRecords,
		calculateTotalsByMetric,
		formatMetricValue
	} from '../../../lib/data-loader';
	import type { RTOData } from '../../../lib/types';

	import Breadcrumb from '../../../lib/components/Breadcrumb.svelte';
	import StatsCard from '../../../lib/components/StatsCard.svelte';
	import MetricTable from '../../../lib/components/MetricTable.svelte';
	import LoadingSpinner from '../../../lib/components/LoadingSpinner.svelte';
	import MetricSelector from '../../../lib/components/MetricSelector.svelte';

	let data: RTOData | null = null;
	let loading = true;
	let error = '';
	let state: string;
	let rto: string;

	// Metric selection state - read from URL params
	let selectedMetric = 'Vehicle Manufacturer';
	let selectedName = 'OLA ELECTRIC TECHNOLOGIES PVT LTD';

	// Expand/collapse state for years
	let showAllYears = false;

	$: state = $page.params.state;
	$: rto = $page.params.rto;
	$: breadcrumbs = generateBreadcrumbs('rto', state, rto);

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
	$: if (state && rto) {
		loadData();
	}

	async function loadData() {
		loading = true;
		error = '';

		try {
			data = await loadRTOData(state, rto);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load RTO data';
		} finally {
			loading = false;
		}
	}

	// Transform optimized metrics to flat arrays for display
	$: flatMetrics = data ? flattenMetrics(data.metrics) : [];
	$: filteredMetricSummaries = data ? getFilteredMetricSummaries(data.metrics) : [];
	$: totalRecords = data ? calculateTotalRecords(data.metrics) : 0;
	$: monthlyTrends =
		data && selectedMetric
			? getMonthlyTrendsByMetric(data.metrics, selectedMetric, selectedName || undefined)
			: [];

	// Group monthly trends by year for better visualization
	$: yearlyTrends = monthlyTrends.reduce(
		(acc, trend) => {
			const year = trend.year;
			if (!acc[year]) acc[year] = [];
			acc[year].push(trend);
			return acc;
		},
		{} as Record<number, typeof monthlyTrends>
	);

	// Prepare years for display with expand/collapse functionality
	$: sortedYearEntries = Object.entries(yearlyTrends).sort(([a], [b]) => parseInt(b) - parseInt(a));
	$: displayedYearEntries = showAllYears ? sortedYearEntries : sortedYearEntries.slice(0, 2);
	$: hasMoreYears = sortedYearEntries.length > 2;

	// Calculate total for current selection
	$: currentTotal =
		data && selectedMetric
			? calculateTotalsByMetric(data.metrics, selectedMetric, selectedName || undefined)
			: 0;
	$: formattedCurrentTotal = formatMetricValue(currentTotal, selectedMetric);
</script>

<svelte:head>
	<title>{data?.name || `${state} RTO ${rto}`} Vehicle Statistics</title>
</svelte:head>

<div class="min-h-screen bg-background">
	<div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<Breadcrumb items={breadcrumbs} />

		<!-- Header -->
		<div class="mb-8">
			<h1 class="mb-2 text-3xl font-bold text-foreground sm:text-4xl">
				{data?.name || `${state} RTO ${rto}`} Vehicle Statistics
			</h1>
		</div>

		{#if loading}
			<LoadingSpinner size="large" text="Loading RTO data..." />
		{:else if error}
			<div class="rounded-lg border border-red-200 bg-red-50 p-4">
				<h3 class="mb-2 text-lg font-semibold text-red-800">Error Loading Data</h3>
				<p class="text-red-700">{error}</p>
				<div class="mt-3 space-x-4">
					<a
						href="/{state}"
						class="text-blue-600 text-muted-foreground underline hover:text-blue-800"
					>
						← Back to {state}
					</a>
					<a href="/" class="text-blue-600 text-muted-foreground underline hover:text-blue-800">
						Return to India overview
					</a>
				</div>
			</div>
		{:else if data}
			<!-- Standard Metric Summaries -->
			<div class="mb-8">
				<div class="rounded-lg border border-gray-200 bg-white p-6">
					<h2 class="mb-4 text-lg font-semibold text-muted-foreground">Total (since 2021)</h2>
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

			<!-- Monthly Trends by Year -->
			{#if Object.keys(yearlyTrends).length > 0}
				<div class="mb-8">
					<h2 class="mb-4 text-xl font-bold text-foreground">
						Total by Month
						{#if selectedName}
							<span class="text-base text-muted-foreground">({selectedName})</span>
						{:else}
							<span class="text-base text-muted-foreground">
								({selectedMetric})
							</span>
						{/if}
					</h2>
					<div class="space-y-6">
						{#each displayedYearEntries as [year, trends]}
							<div class="rounded-lg border border-gray-200 bg-white p-6">
								<h3 class="mb-4 font-semibold">
									<a
										href={`/${state}/${rto}/${year}${buildQueryString()}`}
										class="text-lg text-muted-foreground underline hover:text-primary/80"
									>
										{year}
									</a>
								</h3>
								<div
									class="grid grid-cols-3 gap-4 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-12"
								>
									{#each trends.sort((a, b) => a.month - b.month) as trend}
										<StatsCard
											title={getMonthName(trend.month)}
											value={trend.total_count}
											formattedValue={formatMetricValue(trend.total_count, selectedMetric)}
											href={`/${state}/${rto}/${year}/${trend.month}${buildQueryString()}`}
											compact={true}
											metric={selectedMetric}
										/>
									{/each}
								</div>
							</div>
						{/each}
						{#if hasMoreYears}
							<div class="mt-4 text-center">
								<button
									on:click={() => (showAllYears = !showAllYears)}
									class="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none"
								>
									{showAllYears ? 'Show Less' : `Show All ${sortedYearEntries.length} Years`}
									<svg
										class="ml-2 h-4 w-4 {showAllYears
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
				</div>
			{/if}

			<!-- Detailed Metrics Table -->
			<div class="mb-8">
				<MetricTable data={flatMetrics} title={selectedMetric} {selectedMetric} />
			</div>
		{/if}
	</div>
</div>
