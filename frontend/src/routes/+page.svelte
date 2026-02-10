<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { listRecipes, searchRecipes, listRecipesWithSort, getRandomRecipe } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';
  import RecipeCard from '$lib/components/RecipeCard.svelte';

  let recipes: RecipeSummary[] = [];
  let loading = true;

  $: query = $page.url.searchParams.get('q') || '';
  $: tags = $page.url.searchParams.get('tags') || '';
  $: sort = $page.url.searchParams.get('sort') || '';

  $: loadRecipes(query, tags, sort);

  async function loadRecipes(q: string, t: string, s: string) {
    loading = true;
    try {
      if (q) {
        recipes = await searchRecipes(q);
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
      {:else}
        No recipes found.
      {/if}
    </p>
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

  .discovery-chips {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
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
