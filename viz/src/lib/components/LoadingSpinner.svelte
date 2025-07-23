<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';

	export let size: 'small' | 'medium' | 'large' = 'medium';
	export let text: string = 'Loading...';
</script>

<div class="flex items-center justify-center py-8">
	<div class="flex w-full max-w-md flex-col items-center space-y-4">
		<!-- Main skeleton grid -->
		<div class="grid w-full grid-cols-3 gap-4">
			<Skeleton class="h-20 w-full" />
			<Skeleton class="h-20 w-full" />
			<Skeleton class="h-20 w-full" />
		</div>

		<!-- Additional skeletons for larger loading states -->
		{#if size === 'large'}
			<div class="w-full space-y-2">
				<Skeleton class="h-4 w-full" />
				<Skeleton class="h-4 w-4/5" />
				<Skeleton class="h-4 w-3/5" />
			</div>
		{/if}

		{#if text}
			<p
				class="animate-pulse font-medium text-muted-foreground"
				class:text-sm={size === 'small'}
				class:text-base={size === 'medium'}
				class:text-lg={size === 'large'}
			>
				{text}
			</p>
		{/if}
	</div>
</div>
