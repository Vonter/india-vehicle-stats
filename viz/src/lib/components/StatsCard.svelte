<script lang="ts">
	import { formatNumber, formatCount, formatCurrency, formatMetricValue } from '../data-loader';
	import * as Card from '$lib/components/ui/card';

	export let title: string;
	export let value: number;
	export let subtitle: string = '';
	export let trend: 'up' | 'down' | 'neutral' = 'neutral';
	export let href: string = '';
	export let compact: boolean = false;
	export let formattedValue: string = ''; // New prop for custom formatted value
	export let metric: string = ''; // Metric context for formatting

	// Use metric-aware formatting with Cr/Lakh support
	$: displayValue =
		formattedValue || (metric ? formatMetricValue(value, metric) : formatCount(value));
</script>

{#if href}
	<a {href} class="block transition-all duration-200 hover:scale-[1.02]">
		<Card.Root class="transition-shadow duration-200 hover:shadow-md {compact ? 'p-3' : 'p-4'}">
			<Card.Content class={compact ? 'p-0' : 'p-0'}>
				<div class="flex items-center justify-between">
					<div class="min-w-0 flex-1">
						<p
							class="truncate text-sm font-medium text-blue-600 text-muted-foreground underline hover:text-blue-800 {compact
								? 'text-xs'
								: ''}"
						>
							{title}
						</p>
						<p
							class="font-numbers text-2xl font-bold text-foreground {compact
								? 'mt-0 text-lg'
								: 'mt-1'}"
						>
							{displayValue}
						</p>
						{#if subtitle && !compact}
							<p class="mt-1 text-xs text-muted-foreground">
								{subtitle}
							</p>
						{/if}
					</div>

					{#if trend !== 'neutral'}
						<div class="ml-2 flex-shrink-0">
							{#if trend === 'up'}
								<svg class="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L10 6.414 6.707 9.707a1 1 0 01-1.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
							{:else}
								<svg class="h-4 w-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</div>
					{/if}
				</div>
			</Card.Content>
		</Card.Root>
	</a>
{:else}
	<Card.Root class={compact ? 'p-3' : 'p-4'}>
		<Card.Content class={compact ? 'p-0' : 'p-0'}>
			<div class="flex items-center justify-between">
				<div class="min-w-0 flex-1">
					<p class="truncate text-sm font-medium text-muted-foreground {compact ? 'text-xs' : ''}">
						{title}
					</p>
					<p
						class="font-numbers text-2xl font-bold text-foreground {compact
							? 'mt-0 text-lg'
							: 'mt-1'}"
					>
						{displayValue}
					</p>
					{#if subtitle && !compact}
						<p class="mt-1 text-xs text-muted-foreground">
							{subtitle}
						</p>
					{/if}
				</div>

				{#if trend !== 'neutral'}
					<div class="ml-2 flex-shrink-0">
						{#if trend === 'up'}
							<svg class="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
								<path
									fill-rule="evenodd"
									d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L10 6.414 6.707 9.707a1 1 0 01-1.414 0z"
									clip-rule="evenodd"
								/>
							</svg>
						{:else}
							<svg class="h-4 w-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
								<path
									fill-rule="evenodd"
									d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z"
									clip-rule="evenodd"
								/>
							</svg>
						{/if}
					</div>
				{/if}
			</div>
		</Card.Content>
	</Card.Root>
{/if}
