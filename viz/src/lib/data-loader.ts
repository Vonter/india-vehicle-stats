import type {
	CountryData,
	StateData,
	RTOData,
	StatesIndex,
	OptimizedMetrics,
	SimpleMetrics,
	MetricData,
	MonthlyDataPoint,
	StateInfo,
	RTOInfo
} from './types';

// Cache for loaded data to avoid repeated requests
const dataCache = new Map<string, any>();

/**
 * Transform optimized metrics structure to flat MetricData array
 */
export function flattenMetrics(optimizedMetrics: OptimizedMetrics): MetricData[] {
	const flattened: MetricData[] = [];

	for (const [metric, names] of Object.entries(optimizedMetrics)) {
		for (const [name, monthlyData] of Object.entries(names)) {
			let total_count = 0;

			// Handle both optimized structure (array) and simplified structure (object with counts)
			if (Array.isArray(monthlyData)) {
				// Original optimized structure
				total_count = monthlyData.reduce((sum, data) => sum + data.count, 0);
			} else if (typeof monthlyData === 'object' && monthlyData !== null) {
				// Simplified structure from year-wise/month-wise JSONs
				total_count = Object.values(monthlyData as Record<string, number>).reduce(
					(sum, count) => sum + (count as number),
					0
				);
			} else if (typeof monthlyData === 'number') {
				// Direct number value
				total_count = monthlyData;
			}

			flattened.push({
				Metric: metric,
				Name: name,
				total_count
			});
		}
	}

	return flattened.sort((a, b) => b.total_count - a.total_count);
}

/**
 * Calculate metric summaries from optimized metrics structure
 */
export function calculateMetricSummaries(
	optimizedMetrics: OptimizedMetrics
): Array<{ Metric: string; total_count: number }> {
	const summaries = new Map<string, number>();

	for (const [metric, names] of Object.entries(optimizedMetrics)) {
		let metricTotal = 0;
		for (const monthlyData of Object.values(names)) {
			// Handle both optimized structure (array) and simplified structure (object with counts)
			if (Array.isArray(monthlyData)) {
				// Original optimized structure
				metricTotal += monthlyData.reduce((sum, data) => sum + data.count, 0);
			} else if (typeof monthlyData === 'object' && monthlyData !== null) {
				// Simplified structure from year-wise/month-wise JSONs
				metricTotal += Object.values(monthlyData as Record<string, number>).reduce(
					(sum, count) => sum + (count as number),
					0
				);
			} else if (typeof monthlyData === 'number') {
				// Direct number value
				metricTotal += monthlyData;
			}
		}
		summaries.set(metric, metricTotal);
	}

	return Array.from(summaries.entries())
		.map(([Metric, total_count]) => ({ Metric, total_count }))
		.sort((a, b) => b.total_count - a.total_count);
}

/**
 * Get monthly trends for a specific metric-name combination
 */
export function getMonthlyTrends(
	optimizedMetrics: OptimizedMetrics,
	metric: string,
	name: string
): MonthlyDataPoint[] {
	return optimizedMetrics[metric]?.[name] || [];
}

/**
 * Get all monthly trends aggregated across all metrics
 */
export function getAllMonthlyTrends(
	optimizedMetrics: OptimizedMetrics
): Array<{ year: number; month: number; total_count: number }> {
	const trendsMap = new Map<string, number>();

	for (const names of Object.values(optimizedMetrics)) {
		for (const monthlyData of Object.values(names)) {
			for (const data of monthlyData) {
				const key = `${data.year}-${data.month}`;
				trendsMap.set(key, (trendsMap.get(key) || 0) + data.count);
			}
		}
	}

	return Array.from(trendsMap.entries())
		.map(([key, total_count]) => {
			const [year, month] = key.split('-').map(Number);
			return { year, month, total_count };
		})
		.sort((a, b) => a.year - b.year || a.month - b.month);
}

/**
 * Calculate total records from optimized metrics structure
 */
export function calculateTotalRecords(optimizedMetrics: OptimizedMetrics): number {
	let total = 0;
	for (const names of Object.values(optimizedMetrics)) {
		for (const monthlyData of Object.values(names)) {
			// Handle both optimized structure (array) and simplified structure (object with counts)
			if (Array.isArray(monthlyData)) {
				// Original optimized structure
				total += monthlyData.reduce((sum, data) => sum + data.count, 0);
			} else if (typeof monthlyData === 'object' && monthlyData !== null) {
				// Simplified structure from year-wise/month-wise JSONs
				total += Object.values(monthlyData as Record<string, number>).reduce(
					(sum, count) => sum + (count as number),
					0
				);
			} else if (typeof monthlyData === 'number') {
				// Direct number value
				total += monthlyData;
			}
		}
	}
	return total;
}

/**
 * Load country-level data
 */
export async function loadCountryData(): Promise<CountryData> {
	if (dataCache.has('country')) {
		return dataCache.get('country');
	}

	try {
		const response = await fetch('/data/country.json');
		if (!response.ok) {
			throw new Error(`Failed to load country data: ${response.status}`);
		}
		const data = await response.json();
		dataCache.set('country', data);
		return data;
	} catch (error) {
		console.error('Error loading country data:', error);
		throw error;
	}
}

/**
 * Load country-level data for a specific year
 * Uses client-side aggregation from full country data instead of separate year files
 */
export async function loadCountryYearData(year: number): Promise<CountryData> {
	const cacheKey = `country-year-${year}`;
	if (dataCache.has(cacheKey)) {
		return dataCache.get(cacheKey);
	}

	try {
		// Load the full country data and filter by year client-side
		const fullData = await loadCountryData();

		// Filter metrics by the specific year
		const filteredMetrics = filterMetricsByYear(fullData.metrics, year);

		// Note: State metrics in country data are SimpleMetrics (just totals) and cannot be
		// filtered by specific years. For yearly views, we'll show empty states array
		// since state-level yearly breakdown would require loading individual state data
		const filteredStates: StateInfo[] = [];

		const yearData: CountryData = {
			...fullData,
			metrics: filteredMetrics,
			states: filteredStates
		};

		dataCache.set(cacheKey, yearData);
		return yearData;
	} catch (error) {
		console.error(`Error loading country year data for ${year}:`, error);
		throw error;
	}
}

// Note: Removed filterSimpleMetricsByYearMonth - no longer needed as we use full data for monthly filtering

/**
 * Load country-level data for a specific year and month
 * Uses client-side aggregation from full country data instead of separate monthly files
 */
export async function loadCountryMonthData(year: number, month: number): Promise<CountryData> {
	const cacheKey = `country-month-${year}-${month}`;
	if (dataCache.has(cacheKey)) {
		return dataCache.get(cacheKey);
	}

	try {
		// Load the full country data and filter by year/month client-side
		const fullData = await loadCountryData();

		// Filter metrics by the specific year and month
		const filteredMetrics = filterMetricsByYearMonth(fullData.metrics, year, month);

		// Note: State metrics in country data are SimpleMetrics (just totals) and cannot be
		// filtered by specific months. For monthly views, we'll show empty states array
		// since state-level monthly breakdown would require loading individual state data
		const filteredStates: StateInfo[] = [];

		const monthData: CountryData = {
			...fullData,
			metrics: filteredMetrics,
			states: filteredStates
		};

		dataCache.set(cacheKey, monthData);
		return monthData;
	} catch (error) {
		console.error(`Error loading country month data for ${year}-${month}:`, error);
		throw error;
	}
}

/**
 * Load states index
 */
export async function loadStatesIndex(): Promise<StatesIndex> {
	if (dataCache.has('states-index')) {
		return dataCache.get('states-index');
	}

	try {
		const response = await fetch('/data/states.json');
		if (!response.ok) {
			throw new Error(`Failed to load states index: ${response.status}`);
		}
		const data = await response.json();
		dataCache.set('states-index', data);
		return data;
	} catch (error) {
		console.error('Error loading states index:', error);
		throw error;
	}
}

/**
 * Load state-level data for a specific state
 */
export async function loadStateData(state: string): Promise<StateData> {
	const cacheKey = `state-${state}`;
	if (dataCache.has(cacheKey)) {
		return dataCache.get(cacheKey);
	}

	try {
		const response = await fetch(`/data/state_${state}.json`);
		if (!response.ok) {
			throw new Error(`Failed to load state data for ${state}: ${response.status}`);
		}
		const data = await response.json();
		dataCache.set(cacheKey, data);
		return data;
	} catch (error) {
		console.error(`Error loading state data for ${state}:`, error);
		throw error;
	}
}

/**
 * Load state-level data for a specific state and year
 * Uses client-side aggregation from full state data instead of separate year files
 */
export async function loadStateYearData(state: string, year: number): Promise<StateData> {
	const cacheKey = `state-year-${state}-${year}`;
	if (dataCache.has(cacheKey)) {
		return dataCache.get(cacheKey);
	}

	try {
		// Load the full state data and filter by year client-side
		const fullData = await loadStateData(state);

		// Filter metrics by the specific year
		const filteredMetrics = filterMetricsByYear(fullData.metrics, year);

		// Note: RTO metrics in state data are SimpleMetrics (just totals) and cannot be
		// filtered by specific years. For yearly views, we'll show empty rtos array
		// since RTO-level yearly breakdown would require loading individual RTO data
		const filteredRTOs: RTOInfo[] = [];

		const yearData: StateData = {
			...fullData,
			metrics: filteredMetrics,
			rtos: filteredRTOs
		};

		dataCache.set(cacheKey, yearData);
		return yearData;
	} catch (error) {
		console.error(`Error loading state year data for ${state}-${year}:`, error);
		throw error;
	}
}

/**
 * Load state-level data for a specific state, year and month
 * Uses client-side aggregation from full state data instead of separate monthly files
 */
export async function loadStateMonthData(
	state: string,
	year: number,
	month: number
): Promise<StateData> {
	const cacheKey = `state-month-${state}-${year}-${month}`;
	if (dataCache.has(cacheKey)) {
		return dataCache.get(cacheKey);
	}

	try {
		// Load the full state data and filter by year/month client-side
		const fullData = await loadStateData(state);

		// Filter metrics by the specific year and month
		const filteredMetrics = filterMetricsByYearMonth(fullData.metrics, year, month);

		// Note: RTO metrics in state data are SimpleMetrics (just totals) and cannot be
		// filtered by specific months. For monthly views, we'll show empty rtos array
		// since RTO-level monthly breakdown would require loading individual RTO data
		const filteredRTOs: RTOInfo[] = [];

		const monthData: StateData = {
			...fullData,
			metrics: filteredMetrics,
			rtos: filteredRTOs
		};

		dataCache.set(cacheKey, monthData);
		return monthData;
	} catch (error) {
		console.error(`Error loading state month data for ${state}-${year}-${month}:`, error);
		throw error;
	}
}

/**
 * Load RTO-level data for a specific state and RTO
 */
export async function loadRTOData(state: string, rto: string): Promise<RTOData> {
	const cacheKey = `rto-${state}-${rto}`;
	if (dataCache.has(cacheKey)) {
		return dataCache.get(cacheKey);
	}

	try {
		const response = await fetch(`/data/rto_${state}_${rto}.json`);
		if (!response.ok) {
			throw new Error(`Failed to load RTO data for ${state}-${rto}: ${response.status}`);
		}
		const data = await response.json();
		dataCache.set(cacheKey, data);
		return data;
	} catch (error) {
		console.error(`Error loading RTO data for ${state}-${rto}:`, error);
		throw error;
	}
}

/**
 * Format large numbers with appropriate suffixes (Indian format)
 */
export function formatNumber(num: number | undefined | null): string {
	// Handle undefined, null, or invalid numbers
	if (num == null || isNaN(num)) {
		return '0';
	}

	if (num >= 10_000_000) {
		// 1 crore
		return (num / 10_000_000).toFixed(1) + ' Cr';
	}
	if (num >= 100_000) {
		// 1 lakh
		return (num / 100_000).toFixed(1) + ' L';
	}
	if (num >= 1_000) {
		return (num / 1_000).toFixed(1) + 'K';
	}
	return num.toString();
}

/**
 * Get month name from month number
 */
export function getMonthName(month: number): string {
	const months = [
		'Jan',
		'Feb',
		'Mar',
		'Apr',
		'May',
		'Jun',
		'Jul',
		'Aug',
		'Sep',
		'Oct',
		'Nov',
		'Dec'
	];
	return months[month - 1] || '';
}

/**
 * Filter optimized metrics by year
 */
export function filterMetricsByYear(
	optimizedMetrics: OptimizedMetrics,
	year: number
): OptimizedMetrics {
	const filtered: OptimizedMetrics = {};

	for (const [metric, names] of Object.entries(optimizedMetrics)) {
		filtered[metric] = {};
		for (const [name, monthlyData] of Object.entries(names)) {
			const yearData = monthlyData.filter((data) => data.year === year);
			if (yearData.length > 0) {
				filtered[metric][name] = yearData;
			}
		}
		// Remove empty metrics
		if (Object.keys(filtered[metric]).length === 0) {
			delete filtered[metric];
		}
	}

	return filtered;
}

/**
 * Filter optimized metrics by year and month
 */
export function filterMetricsByYearMonth(
	optimizedMetrics: OptimizedMetrics,
	year: number,
	month: number
): OptimizedMetrics {
	const filtered: OptimizedMetrics = {};

	for (const [metric, names] of Object.entries(optimizedMetrics)) {
		filtered[metric] = {};
		for (const [name, monthlyData] of Object.entries(names)) {
			const monthData = monthlyData.filter((data) => data.year === year && data.month === month);
			if (monthData.length > 0) {
				filtered[metric][name] = monthData;
			}
		}
		// Remove empty metrics
		if (Object.keys(filtered[metric]).length === 0) {
			delete filtered[metric];
		}
	}

	return filtered;
}

/**
 * Get available years from optimized metrics
 */
export function getAvailableYears(optimizedMetrics: OptimizedMetrics): number[] {
	const years = new Set<number>();

	for (const names of Object.values(optimizedMetrics)) {
		for (const monthlyData of Object.values(names)) {
			for (const data of monthlyData) {
				years.add(data.year);
			}
		}
	}

	return Array.from(years).sort((a, b) => b - a);
}

/**
 * Get available months for a specific year from optimized metrics
 */
export function getAvailableMonths(optimizedMetrics: OptimizedMetrics, year: number): number[] {
	const months = new Set<number>();

	for (const names of Object.values(optimizedMetrics)) {
		for (const monthlyData of Object.values(names)) {
			for (const data of monthlyData) {
				if (data.year === year) {
					months.add(data.month);
				}
			}
		}
	}

	return Array.from(months).sort((a, b) => a - b);
}

/**
 * Generate breadcrumb items based on current level
 */
export function generateBreadcrumbs(
	level: string,
	state?: string,
	rto?: string,
	year?: string,
	month?: string
): Array<{ label: string; href: string; current?: boolean }> {
	const breadcrumbs = [{ label: 'India', href: '/', current: false }];

	// Handle country year routes (no state)
	if (!state && year) {
		breadcrumbs.push({
			label: year,
			href: `/ALL/${year}`,
			current: false
		});

		if (month) {
			breadcrumbs.push({
				label: getMonthName(parseInt(month)),
				href: `/ALL/${year}/${month}`,
				current: true
			});
		}
	}
	// Handle state routes
	else if (state) {
		breadcrumbs.push({
			label: state,
			href: `/${state}`,
			current: false
		});

		// Handle state year routes (no RTO)
		if (year && !rto) {
			breadcrumbs.push({
				label: year,
				href: `/${state}/ALL/${year}`,
				current: false
			});

			if (month) {
				breadcrumbs.push({
					label: getMonthName(parseInt(month)),
					href: `/${state}/ALL/${year}/${month}`,
					current: true
				});
			}
		}
		// Handle RTO routes
		else if (rto) {
			breadcrumbs.push({
				label: `RTO ${rto}`,
				href: `/${state}/${rto}`,
				current: false
			});

			if (year) {
				breadcrumbs.push({
					label: year,
					href: `/${state}/${rto}/${year}`,
					current: false
				});
			}

			if (year && month) {
				breadcrumbs.push({
					label: getMonthName(parseInt(month)),
					href: `/${state}/${rto}/${year}/${month}`,
					current: true
				});
			}
		}
	}

	// Mark the last item as current if not already done
	if (breadcrumbs.length > 0 && !breadcrumbs.some((b) => b.current)) {
		breadcrumbs[breadcrumbs.length - 1].current = true;
	}

	return breadcrumbs;
}

/**
 * Format currency values in Indian format (crore/lakh)
 */
export function formatCurrency(num: number | undefined | null): string {
	// Handle undefined, null, or invalid numbers
	if (num == null || isNaN(num)) {
		return '₹0';
	}

	if (num >= 10_000_000) {
		// 1 crore
		return '₹' + (num / 10_000_000).toFixed(1) + ' Cr';
	}
	if (num >= 100_000) {
		// 1 lakh
		return '₹' + (num / 100_000).toFixed(1) + ' L';
	}
	if (num >= 1_000) {
		return '₹' + (num / 1_000).toFixed(1) + 'K';
	}
	return '₹' + num.toString();
}

/**
 * Format count values in Indian format (crore/lakh)
 */
export function formatCount(num: number | undefined | null): string {
	// Handle undefined, null, or invalid numbers
	if (num == null || isNaN(num)) {
		return '0';
	}

	if (num >= 10_000_000) {
		// 1 crore
		return (num / 10_000_000).toFixed(1) + ' Cr';
	}
	if (num >= 100_000) {
		// 1 lakh
		return (num / 100_000).toFixed(1) + ' L';
	}
	if (num >= 1_000) {
		return (num / 1_000).toFixed(1) + 'K';
	}
	return num.toString();
}

/**
 * Get filtered metric summaries for specific metrics with proper formatting
 */
export function getFilteredMetricSummaries(
	optimizedMetrics: OptimizedMetrics
): Array<{ Metric: string; total_count: number; formatted_value: string }> {
	const targetMetrics = ['Revenue (Tax)', 'Revenue (Fee)', 'Transaction', 'Vehicle Manufacturer'];
	const metricTitleMap: Record<string, string> = {
		'Revenue (Tax)': 'Revenue Collection (Tax)',
		'Revenue (Fee)': 'Revenue Collection (Fees)',
		Transaction: 'Number of Transactions',
		'Vehicle Manufacturer': 'Vehicles Registered'
	};

	const summaries = new Map<string, number>();

	for (const [metric, names] of Object.entries(optimizedMetrics)) {
		if (targetMetrics.includes(metric)) {
			let metricTotal = 0;
			for (const monthlyData of Object.values(names)) {
				// Handle both optimized structure (array) and simplified structure (object with counts)
				if (Array.isArray(monthlyData)) {
					// Original optimized structure
					metricTotal += monthlyData.reduce((sum, data) => sum + data.count, 0);
				} else if (typeof monthlyData === 'object' && monthlyData !== null) {
					// Simplified structure from year-wise/month-wise JSONs
					metricTotal += Object.values(monthlyData as Record<string, number>).reduce(
						(sum, count) => sum + (count as number),
						0
					);
				} else if (typeof monthlyData === 'number') {
					// Direct number value
					metricTotal += monthlyData;
				}
			}
			summaries.set(metric, metricTotal);
		}
	}

	// Define the desired display order
	const displayOrder = [
		'Vehicles Registered',
		'Number of Transactions',
		'Revenue Collection (Tax)',
		'Revenue Collection (Fees)'
	];

	return Array.from(summaries.entries())
		.map(([originalMetric, total_count]) => ({
			Metric: metricTitleMap[originalMetric] || originalMetric,
			total_count,
			formatted_value: originalMetric.startsWith('Revenue')
				? formatCurrency(total_count)
				: formatCount(total_count)
		}))
		.sort((a, b) => {
			const indexA = displayOrder.indexOf(a.Metric);
			const indexB = displayOrder.indexOf(b.Metric);
			// If both metrics are in displayOrder, sort by their position
			if (indexA !== -1 && indexB !== -1) {
				return indexA - indexB;
			}
			// If only one is in displayOrder, prioritize it
			if (indexA !== -1) return -1;
			if (indexB !== -1) return 1;
			// If neither is in displayOrder, maintain original order (fallback)
			return 0;
		});
}

/**
 * Calculate totals by specific metric (optionally filtered by name)
 */
export function calculateTotalsByMetric(
	optimizedMetrics: OptimizedMetrics,
	metric: string,
	name?: string
): number {
	if (!optimizedMetrics[metric]) return 0;

	let total = 0;
	for (const [currentName, monthlyData] of Object.entries(optimizedMetrics[metric])) {
		if (!name || currentName === name) {
			// Handle both optimized structure (array) and simplified structure (object with counts)
			if (Array.isArray(monthlyData)) {
				// Original optimized structure
				total += monthlyData.reduce((sum, data) => sum + data.count, 0);
			} else if (typeof monthlyData === 'object' && monthlyData !== null) {
				// Simplified structure from year-wise/month-wise JSONs
				total += Object.values(monthlyData as Record<string, number>).reduce(
					(sum, count) => sum + (count as number),
					0
				);
			} else if (typeof monthlyData === 'number') {
				// Direct number value
				total += monthlyData;
			}
		}
	}

	return total;
}

/**
 * Calculate monthly trends by specific metric (optionally filtered by name)
 */
export function getMonthlyTrendsByMetric(
	optimizedMetrics: OptimizedMetrics,
	metric: string,
	name?: string
): Array<{ year: number; month: number; total_count: number }> {
	if (!optimizedMetrics[metric]) return [];

	const trendsMap = new Map<string, number>();

	for (const [currentName, monthlyData] of Object.entries(optimizedMetrics[metric])) {
		if (!name || currentName === name) {
			// Handle both optimized structure (array) and simplified structure (object with counts)
			if (Array.isArray(monthlyData)) {
				// Original optimized structure
				for (const data of monthlyData) {
					const key = `${data.year}-${data.month}`;
					trendsMap.set(key, (trendsMap.get(key) || 0) + data.count);
				}
			} else if (typeof monthlyData === 'object' && monthlyData !== null) {
				// For simplified structures, we can't extract monthly trends
				// This would only work with the full optimized structure
				// So we return an empty array for simplified data
				continue;
			} else if (typeof monthlyData === 'number') {
				// Direct number value - can't extract monthly trends without year/month info
				continue;
			}
		}
	}

	return Array.from(trendsMap.entries())
		.map(([key, total_count]) => {
			const [year, month] = key.split('-').map(Number);
			return { year, month, total_count };
		})
		.sort((a, b) => a.year - b.year || a.month - b.month);
}

/**
 * Get available metrics from optimized data
 */
export function getAvailableMetrics(optimizedMetrics: OptimizedMetrics): string[] {
	return Object.keys(optimizedMetrics).sort();
}

/**
 * Get available names for a specific metric
 */
export function getAvailableNames(optimizedMetrics: OptimizedMetrics, metric: string): string[] {
	if (!optimizedMetrics[metric]) return [];
	return Object.keys(optimizedMetrics[metric]).sort();
}

/**
 * Get available names for a specific metric sorted by total sum (descending) - OPTIMIZED
 * All items sorted by total count with name as tiebreaker for stable sorting
 */
export function getAvailableNamesSortedByTotal(
	optimizedMetrics: OptimizedMetrics,
	metric: string
): string[] {
	if (!optimizedMetrics[metric]) return [];

	// Pre-compute totals more efficiently by avoiding intermediate objects
	const entries = Object.entries(optimizedMetrics[metric]);
	const namesWithTotals = new Array(entries.length);

	// Use for loop for better performance than map/reduce chain
	for (let i = 0; i < entries.length; i++) {
		const [name, monthlyData] = entries[i];
		let total = 0;

		// Handle both optimized structure (array) and simplified structure (object with counts)
		if (Array.isArray(monthlyData)) {
			// Original optimized structure - avoid reduce overhead for better performance
			for (let j = 0; j < monthlyData.length; j++) {
				total += monthlyData[j].count;
			}
		} else if (typeof monthlyData === 'object' && monthlyData !== null) {
			// Simplified structure from year-wise/month-wise JSONs
			total = Object.values(monthlyData as Record<string, number>).reduce(
				(sum, count) => sum + (count as number),
				0
			);
		} else if (typeof monthlyData === 'number') {
			// Direct number value
			total = monthlyData;
		}

		namesWithTotals[i] = { name, total };
	}

	// Sort by total in descending order with name as tiebreaker for stable sort
	const sortedByTotal = namesWithTotals.sort((a, b) => {
		const totalDiff = b.total - a.total;
		if (totalDiff !== 0) return totalDiff;
		// Use name as tiebreaker for stable sort
		return a.name.localeCompare(b.name);
	});

	// Return all items sorted by total count
	return sortedByTotal.map((item) => item.name);
}

/**
 * Get metric display name with proper formatting
 */
export function getMetricDisplayName(metric: string): string {
	const displayNames: Record<string, string> = {
		'Vehicle Manufacturer': 'Vehicle Registrations',
		'Revenue (Tax)': 'Tax Revenue',
		'Revenue (Fee)': 'Fee Revenue',
		Transaction: 'Transactions'
	};

	return displayNames[metric] || metric;
}

/**
 * Format value based on metric type
 */
export function formatMetricValue(value: number, metric: string): string {
	if (metric.startsWith('Revenue')) {
		return formatCurrency(value);
	} else {
		return formatCount(value);
	}
}

/**
 * Calculate totals by specific metric from SimpleMetrics structure (optionally filtered by name)
 */
export function calculateTotalsByMetricSimple(
	simpleMetrics: SimpleMetrics,
	metric: string,
	name?: string
): number {
	if (!simpleMetrics[metric]) return 0;

	let total = 0;
	for (const [currentName, count] of Object.entries(simpleMetrics[metric])) {
		if (!name || currentName === name) {
			total += count;
		}
	}

	return total;
}
