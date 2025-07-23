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
		filterMetricsByYear,
		getAvailableMonths,
		calculateTotalsByMetric,
		formatMetricValue
	} from '../../../../lib/data-loader';
	import type { RTOData } from '../../../../lib/types';

	import Breadcrumb from '../../../../lib/components/Breadcrumb.svelte';
	import StatsCard from '../../../../lib/components/StatsCard.svelte';
	import MetricTable from '../../../../lib/components/MetricTable.svelte';
	import LoadingSpinner from '../../../../lib/components/LoadingSpinner.svelte';
	import MetricSelector from '../../../../lib/components/MetricSelector.svelte';

	let data: RTOData | null = null;
	let loading = true;
	let error = '';
	let state: string;
	let rto: string;
	let year: string;

	// Metric selection state - read from URL params
	let selectedMetric = 'Vehicle Manufacturer';
	let selectedName = 'OLA ELECTRIC TECHNOLOGIES PVT LTD';

	$: state = $page.params.state;
	$: rto = $page.params.rto;
	$: year = $page.params.year;
	$: breadcrumbs = generateBreadcrumbs('year', state, rto, year);

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
	$: if (state && rto && year) {
		loadData();
	}

	async function loadData() {
		loading = true;
		error = '';

		try {
			const rawData = await loadRTOData(state, rto);
			// Filter data by year
			const filteredMetrics = filterMetricsByYear(rawData.metrics, parseInt(year));
			data = {
				...rawData,
				metrics: filteredMetrics
			};
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load RTO data';
		} finally {
			loading = false;
		}
	}

	// Transform filtered metrics to flat arrays for display
	$: flatMetrics = data ? flattenMetrics(data.metrics) : [];
	$: filteredMetricSummaries = data ? getFilteredMetricSummaries(data.metrics) : [];
	$: monthlyTrends =
		data && selectedMetric
			? getMonthlyTrendsByMetric(data.metrics, selectedMetric, selectedName || undefined)
			: [];
	$: availableMonths = data ? getAvailableMonths(data.metrics, parseInt(year)) : [];

	// Expand/collapse state for months
	let showAllMonths = false;

	// Displayed months based on expand/collapse state
	$: displayedMonths = showAllMonths ? availableMonths : availableMonths.slice(0, 12);

	// Check if we have more than 12 months
	$: hasMoreMonths = availableMonths.length > 12;

	// Calculate total for current selection
	$: currentTotal =
		data && selectedMetric
			? calculateTotalsByMetric(data.metrics, selectedMetric, selectedName || undefined)
			: 0;
	$: formattedCurrentTotal = formatMetricValue(currentTotal, selectedMetric);
</script>

<svelte:head>
	<title>{data?.name || `${state} RTO ${rto}`} Vehicle Statistics - {year}</title>
</svelte:head>

<div class="min-h-screen bg-background">
	<div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
		<Breadcrumb items={breadcrumbs} />

		<!-- Header -->
		<div class="mb-8">
			<h1 class="mb-2 text-3xl font-bold text-foreground sm:text-4xl">
				{data?.name || `${state} RTO ${rto}`} Vehicle Statistics - {year}
			</h1>
		</div>

		{#if loading}
			<LoadingSpinner size="large" text="Loading {year} data..." />
		{:else if error}
			<div class="rounded-lg border border-red-200 bg-red-50 p-4">
				<h3 class="mb-2 text-lg font-semibold text-red-800">Error Loading Data</h3>
				<p class="text-red-700">{error}</p>
				<div class="mt-3 space-x-4">
					<a
						href="/{state}/{rto}"
						class="text-blue-600 text-muted-foreground underline hover:text-blue-800"
					>
						← Back to RTO overview
					</a>
					<a
						href="/{state}"
						class="text-blue-600 text-muted-foreground underline hover:text-blue-800"
					>
						Back to {state}
					</a>
				</div>
			</div>
		{:else if data}
			<!-- Standard Metric Summaries -->
			<div class="mb-8">
				<div class="rounded-lg border border-gray-200 bg-white p-6">
					<h2 class="mb-4 text-lg font-semibold text-muted-foreground">Total in {year}</h2>
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

			<!-- Monthly Navigation -->
			{#if availableMonths.length > 0}
				<div class="mb-8">
					<h2 class="mb-4 text-xl font-bold text-foreground">
						Total by Month in {year}
						{#if selectedName}
							<span class="text-base text-muted-foreground">({selectedName})</span>
						{:else}
							<span class="text-base text-muted-foreground">
								({selectedMetric})
							</span>
						{/if}
					</h2>
					<div
						class="grid grid-cols-3 gap-4 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-12"
					>
						{#each displayedMonths as month}
							<StatsCard
								title={getMonthName(month)}
								value={monthlyTrends.find((t) => t.month === month)?.total_count || 0}
								formattedValue={formatMetricValue(
									monthlyTrends.find((t) => t.month === month)?.total_count || 0,
									selectedMetric
								)}
								href={`/${state}/${rto}/${year}/${month}${buildQueryString()}`}
								compact={true}
								metric={selectedMetric}
							/>
						{/each}
					</div>
					{#if hasMoreMonths}
						<div class="mt-4 text-center">
							<button
								on:click={() => (showAllMonths = !showAllMonths)}
								class="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none"
							>
								{showAllMonths ? 'Show Less' : `Show All ${availableMonths.length} Months`}
								<svg
									class="ml-2 h-4 w-4 {showAllMonths
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

			<!-- Detailed Metrics Table -->
			<div class="mb-8">
				<MetricTable data={flatMetrics} title={selectedMetric} {selectedMetric} />
			</div>
		{/if}
	</div>
</div>
