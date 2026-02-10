<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { listRecipes } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';

  export let exclude: string[] = [];

  const dispatch = createEventDispatcher();

  let query = '';
  let allRecipes: RecipeSummary[] = [];
  let open = false;
  let loading = true;

  $: filtered = allRecipes
    .filter(r => !exclude.includes(r.slug))
    .filter(r => !query || r.title.toLowerCase().includes(query.toLowerCase()));

  async function load() {
    loading = true;
    allRecipes = await listRecipes();
    loading = false;
  }

  function toggle() {
    if (!open) {
      load();
    }
    open = !open;
  }

  function select(recipe: RecipeSummary) {
    dispatch('select', { slug: recipe.slug, title: recipe.title });
    open = false;
    query = '';
  }
</script>

<div class="picker">
  <button class="add-btn" on:click={toggle} aria-label="Add recipe">+</button>
  {#if open}
    <div class="dropdown">
      <input
        type="text"
        placeholder="Search recipes..."
        bind:value={query}
        class="picker-search"
      />
      <div class="picker-list">
        {#if loading}
          <p class="picker-empty">Loading...</p>
        {:else if filtered.length === 0}
          <p class="picker-empty">No recipes found</p>
        {:else}
          {#each filtered as recipe}
            <button class="picker-item" on:click={() => select(recipe)}>
              {recipe.title}
            </button>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .picker {
    position: relative;
  }

  .add-btn {
    width: 100%;
    padding: 0.35rem;
    border: 1px dashed var(--color-border);
    border-radius: var(--radius);
    background: transparent;
    color: var(--color-text-muted);
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .add-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    min-width: 200px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-md);
    z-index: 10;
    margin-top: 0.25rem;
  }

  .picker-search {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: none;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.85rem;
    font-family: var(--font-body);
    outline: none;
    background: transparent;
    color: var(--color-text);
  }

  .picker-list {
    max-height: 200px;
    overflow-y: auto;
  }

  .picker-item {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: none;
    background: transparent;
    text-align: left;
    font-size: 0.85rem;
    color: var(--color-text);
    cursor: pointer;
    transition: background 0.1s;
  }

  .picker-item:hover {
    background: var(--color-accent-light);
    color: var(--color-accent);
  }

  .picker-empty {
    padding: 0.75rem;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    text-align: center;
  }
</style>
