<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { listRecipes, searchRecipes, listRecipesWithSort, getRandomRecipe } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';
  import RecipeCard from '$lib/components/RecipeCard.svelte';
  import RecipeTable from '$lib/components/RecipeTable.svelte';

  let recipes: RecipeSummary[] = [];
  let loading = true;

  let viewMode: string = (typeof localStorage !== 'undefined' && localStorage.getItem('viewMode')) || 'grid';
  let visibleColumns: string[] = (() => {
    if (typeof localStorage !== 'undefined') {
      const stored = localStorage.getItem('tableColumns');
      if (stored) {
        try { return JSON.parse(stored); } catch { /* ignore */ }
      }
    }
    return ['title', 'tags', 'cook_time', 'likes', 'last_cooked'];
  })();

  $: if (typeof localStorage !== 'undefined') {
    localStorage.setItem('viewMode', viewMode);
  }
  $: if (typeof localStorage !== 'undefined') {
    localStorage.setItem('tableColumns', JSON.stringify(visibleColumns));
  }

  $: query = $page.url.searchParams.get('q') || '';
  $: tags = $page.url.searchParams.get('tags') || '';
  $: sort = $page.url.searchParams.get('sort') || '';

  $: loadRecipes(query, tags, sort);

  async function loadRecipes(q: string, t: string, s: string) {
    loading = true;
    try {
      if (q) {
        recipes = await searchRecipes(q);
      } else if (s === 'most-loved') {
        const tagList = t ? t.split(',').filter(Boolean) : undefined;
        const all = tagList ? await listRecipes(tagList) : await listRecipes();
        recipes = all.filter(r => r.likes > 0).sort((a, b) => b.likes - a.likes);
      } else if (s) {
        const tagList = t ? t.split(',').filter(Boolean) : undefined;
        recipes = await listRecipesWithSort(s, tagList);
      } else if (t) {
        recipes = await listRecipes(t.split(',').filter(Boolean));
      } else {
        recipes = await listRecipes();
      }
    } catch (e) {
      console.error('Failed to load recipes:', e);
      recipes = [];
    }
    loading = false;
  }

  onMount(() => {
    loadRecipes(query, tags, sort);
  });

  const discoveryChips = [
    { label: 'Surprise me', sort: '_random' },
    { label: 'Never tried', sort: 'never-cooked' },
    { label: 'Cook again', sort: 'least-recent' },
    { label: 'Quick meals', sort: 'quick' },
    { label: 'Most loved', sort: 'most-loved' },
  ];

  async function handleChip(chip: typeof discoveryChips[0]) {
    if (chip.sort === '_random') {
      try {
        const recipe = await getRandomRecipe();
        goto(`/recipe/${recipe.slug}`);
      } catch (e) {
        // no recipes
      }
      return;
    }
    const params = new URLSearchParams($page.url.searchParams);
    if (sort === chip.sort) {
      params.delete('sort');
    } else {
      params.set('sort', chip.sort);
    }
    params.delete('q');
    const qs = params.toString();
    goto(qs ? `/?${qs}` : '/');
  }
</script>

<svelte:head>
  <title>Forks - Recipe Manager</title>
</svelte:head>

<div class="home">
  {#if query}
    <p class="result-info">Search results for "{query}"</p>
  {:else}
    <div class="toolbar">
      <div class="discovery-chips">
        {#each discoveryChips as chip}
          <button
            class="chip"
            class:active={sort === chip.sort}
            on:click={() => handleChip(chip)}
          >
            {chip.label}
          </button>
        {/each}
      </div>
      <div class="view-toggle">
        <button
          class="toggle-btn"
          class:active={viewMode === 'grid'}
          on:click={() => viewMode = 'grid'}
          title="Grid view"
          aria-label="Grid view"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
          </svg>
        </button>
        <button
          class="toggle-btn"
          class:active={viewMode === 'table'}
          on:click={() => viewMode = 'table'}
          title="Table view"
          aria-label="Table view"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  {/if}

  {#if loading}
    <p class="loading">Loading recipes...</p>
  {:else if recipes.length === 0}
    <p class="empty">
      {#if sort === 'never-cooked'}
        You've tried everything! Nice work.
      {:else if sort === 'least-recent'}
        No cook history yet. Start cooking to see suggestions here.
      {:else if sort === 'quick'}
        No quick recipes found (under 30 min).
      {:else if sort === 'most-loved'}
        No liked recipes yet. Start liking recipes to see them here.
      {:else}
        No recipes found.
      {/if}
    </p>
  {:else if viewMode === 'table'}
    <RecipeTable recipes={recipes} visibleColumns={visibleColumns} />
  {:else}
    <div class="grid">
      {#each recipes as recipe (recipe.slug)}
        <RecipeCard {recipe} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .home {
    max-width: 1000px;
  }

  .result-info {
    font-size: 0.9rem;
    color: var(--color-text-muted);
    margin-bottom: 1.5rem;
  }

  .toolbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .discovery-chips {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .view-toggle {
    display: flex;
    gap: 0.25rem;
    flex-shrink: 0;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: 0.15rem;
    background: var(--color-surface);
  }

  .toggle-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: calc(var(--radius) - 2px);
    background: transparent;
    color: var(--color-text-muted);
    cursor: pointer;
    transition: all 0.15s;
  }

  .toggle-btn:hover:not(.active) {
    color: var(--color-accent);
    background: var(--color-surface-hover);
  }

  .toggle-btn.active {
    background: var(--color-accent);
    color: white;
  }

  .chip {
    padding: 0.35rem 0.85rem;
    border: 1px solid var(--color-border);
    border-radius: 999px;
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .chip:hover:not(.active) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .chip.active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .loading, .empty {
    color: var(--color-text-muted);
    text-align: center;
    padding: 4rem 1rem;
    font-size: 1.1rem;
  }

  @media (max-width: 768px) {
    .grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }
  }
</style>
