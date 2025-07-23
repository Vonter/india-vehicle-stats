export interface MonthlyDataPoint {
	year: number;
	month: number;
	count: number;
}

export interface MetricData {
	Metric: string;
	Name: string;
	total_count: number;
}

// New optimized metrics structure: { [metric]: { [name]: MonthlyDataPoint[] } }
export interface OptimizedMetrics {
	[metric: string]: {
		[name: string]: MonthlyDataPoint[];
	};
}

// Simple metrics structure for breakdowns: { [metric]: { [name]: total_count } }
export interface SimpleMetrics {
	[metric: string]: {
		[name: string]: number;
	};
}

export interface StateInfo {
	State: string;
	total_count: number;
	rto_count: number;
	metrics: SimpleMetrics;
}

export interface RTOInfo {
	RTO: number;
	'RTO Name': string;
	total_count: number;
	metrics: SimpleMetrics;
}

export interface CountryData {
	level: 'country';
	name: string;
	metrics: OptimizedMetrics;
	states: StateInfo[];
}

export interface StateData {
	level: 'state';
	state: string;
	name: string;
	metrics: OptimizedMetrics;
	rtos: RTOInfo[];
}

export interface RTOData {
	level: 'rto';
	state: string;
	rto: number;
	name: string;
	metrics: OptimizedMetrics;
}

export type LevelData = CountryData | StateData | RTOData;

export interface StatesIndex {
	[key: string]: string;
}

export interface BreadcrumbItem {
	label: string;
	href: string;
	current?: boolean;
}
