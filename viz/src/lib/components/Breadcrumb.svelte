<script lang="ts">
	import type { BreadcrumbItem } from '../types';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb';

	export let items: BreadcrumbItem[] = [];
</script>

<div class="mb-6 text-blue-600 text-muted-foreground underline hover:text-blue-800">
	<Breadcrumb.Root>
		<Breadcrumb.List>
			{#each items as item, index}
				{#if index > 0}
					<Breadcrumb.Separator />
				{/if}
				<Breadcrumb.Item>
					{#if item.current}
						<Breadcrumb.Page>{item.label}</Breadcrumb.Page>
					{:else}
						<Breadcrumb.Link href={item.href}>{item.label}</Breadcrumb.Link>
					{/if}
				</Breadcrumb.Item>
			{/each}
		</Breadcrumb.List>
	</Breadcrumb.Root>
</div>
