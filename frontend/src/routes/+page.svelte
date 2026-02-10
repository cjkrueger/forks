<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { listRecipes, searchRecipes, listRecipesWithSort, getRandomRecipe } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';
  import RecipeCard from '$lib/components/RecipeCard.svelte';
  import RecipeTable from '$lib/components/RecipeTable.svelte';
  import ColumnPicker from '$lib/components/ColumnPicker.svelte';

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

  const allColumns = [
    { key: 'title', label: 'Title' },
    { key: 'tags', label: 'Tags' },
    { key: 'prep_time', label: 'Prep' },
    { key: 'cook_time', label: 'Cook' },
    { key: 'servings', label: 'Servings' },
    { key: 'likes', label: 'Likes' },
    { key: 'last_cooked', label: 'Last Cooked' },
    { key: 'date_added', label: 'Added' },
    { key: 'source', label: 'Source' },
  ];

  let filterBarOpen = (typeof localStorage !== 'undefined' && localStorage.getItem('filterBarOpen') === 'true') || false;
  $: if (typeof localStorage !== 'undefined') {
    localStorage.setItem('filterBarOpen', String(filterBarOpen));
  }

  $: query = $page.url.searchParams.get('q') || '';
  $: tags = $page.url.searchParams.get('tags') || '';
  $: sort = $page.url.searchParams.get('sort') || '';

  $: activeTags = tags ? tags.split(',').filter(Boolean) : [];

  $: allTags = (() => {
    const tagSet = new Set<string>();
    for (const r of recipes) {
      for (const t of r.tags) tagSet.add(t);
    }
    return [...tagSet].sort((a, b) => a.localeCompare(b));
  })();

  const sortOptions = [
    { value: '', label: 'Default' },
    { value: 'quick', label: 'Quick meals' },
    { value: 'never-cooked', label: 'Never tried' },
    { value: 'least-recent', label: 'Least recent' },
    { value: 'most-loved', label: 'Most loved' },
  ];

  function toggleTag(tag: string) {
    const params = new URLSearchParams($page.url.searchParams);
    let current = activeTags;
    if (current.includes(tag)) {
      current = current.filter(t => t !== tag);
    } else {
      current = [...current, tag];
    }
    if (current.length > 0) {
      params.set('tags', current.join(','));
    } else {
      params.delete('tags');
    }
    params.delete('q');
    const qs = params.toString();
    goto(qs ? `/?${qs}` : '/');
  }

  function handleSortChange(e: Event) {
    const value = (e.target as HTMLSelectElement).value;
    const params = new URLSearchParams($page.url.searchParams);
    if (value) {
      params.set('sort', value);
    } else {
      params.delete('sort');
    }
    params.delete('q');
    const qs = params.toString();
    goto(qs ? `/?${qs}` : '/');
  }

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
      <div class="toolbar-right">
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
        {#if viewMode === 'table'}
          <ColumnPicker
            columns={allColumns}
            visible={visibleColumns}
            onChange={(cols) => { visibleColumns = cols; }}
          />
        {/if}
        <button
          class="filter-toggle-btn"
          class:active={filterBarOpen}
          on:click={() => (filterBarOpen = !filterBarOpen)}
          title="Toggle filters"
          aria-label="Toggle filters"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
        </button>
      </div>
    </div>

    {#if filterBarOpen}
      <div class="filter-bar">
        <div class="filter-section">
          <label class="filter-label" for="sort-select">Sort</label>
          <select id="sort-select" class="sort-select" value={sort} on:change={handleSortChange}>
            {#each sortOptions as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>
        {#if allTags.length > 0}
          <div class="filter-section filter-tags-section">
            <span class="filter-label">Tags</span>
            <div class="filter-tags">
              {#each allTags as tag}
                <button
                  class="tag-pill"
                  class:active={activeTags.includes(tag)}
                  on:click={() => toggleTag(tag)}
                >
                  {tag}
                </button>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}
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

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
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

  .filter-toggle-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text-muted);
    cursor: pointer;
    transition: all 0.15s;
  }

  .filter-toggle-btn:hover,
  .filter-toggle-btn.active {
    color: var(--color-accent);
    border-color: var(--color-accent);
  }

  .filter-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: flex-start;
    padding: 0.75rem 1rem;
    margin-bottom: 1.5rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
  }

  .filter-section {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .filter-tags-section {
    flex: 1;
    align-items: flex-start;
  }

  .filter-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
    line-height: 1.8;
  }

  .sort-select {
    padding: 0.3rem 0.5rem;
    border: 1px solid var(--color-border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--color-bg);
    color: var(--color-text);
    font-size: 0.85rem;
    font-family: var(--font-body);
    cursor: pointer;
  }

  .sort-select:focus {
    outline: none;
    border-color: var(--color-accent);
  }

  .filter-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .tag-pill {
    padding: 0.2rem 0.6rem;
    border: 1px solid var(--color-border);
    border-radius: 999px;
    background: var(--color-bg);
    color: var(--color-text-muted);
    font-size: 0.78rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .tag-pill:hover:not(.active) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .tag-pill.active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  @media (max-width: 768px) {
    .grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .toolbar {
      flex-direction: column;
      gap: 0.75rem;
    }

    .toolbar-right {
      align-self: flex-end;
    }

    .filter-bar {
      flex-direction: column;
      gap: 0.75rem;
    }
  }
</style>
