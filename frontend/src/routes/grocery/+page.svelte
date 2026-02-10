<script lang="ts">
  import {
    groceryStore,
    getMergedItems,
    toggleChecked,
    clearChecked,
    clearAll,
    removeRecipeFromGrocery,
    removeItem,
    addCustomCombine,
  } from '$lib/grocery';
  import type { MergedItem } from '$lib/grocery';

  let selected: Set<string> = new Set();
  let combineMode = false;
  let combineName = '';
  let combineQuantity = '';

  $: items = getMergedItems($groceryStore);
  $: toBuy = items.filter(i => !i.checked);
  $: gotIt = items.filter(i => i.checked);
  $: recipeEntries = Object.entries($groceryStore.recipes);

  function toggleSelect(key: string) {
    if (selected.has(key)) {
      selected.delete(key);
    } else {
      selected.add(key);
    }
    selected = new Set(selected);
  }

  function startCombine() {
    if (selected.size < 2) return;
    const selectedItems = items.filter(i => selected.has(i.key));
    // Try to auto-sum quantities
    let totalQty: number | null = 0;
    let commonUnit: string | null = selectedItems[0]?.unit || null;
    let canSum = true;
    for (const item of selectedItems) {
      if (item.quantity === null || item.unit !== commonUnit) {
        canSum = false;
        break;
      }
      totalQty = (totalQty || 0) + item.quantity;
    }
    if (!canSum) totalQty = null;

    combineQuantity = totalQty !== null ? String(totalQty) : '';
    combineName = selectedItems[0]?.name || '';
    combineMode = true;
  }

  function confirmCombine() {
    const keys = Array.from(selected);
    const qty = combineQuantity ? parseFloat(combineQuantity) : null;
    const selectedItems = items.filter(i => selected.has(i.key));
    const unit = selectedItems[0]?.unit || null;
    addCustomCombine(keys, isNaN(qty as number) ? null : qty, unit, combineName.trim());
    selected = new Set();
    combineMode = false;
    combineName = '';
    combineQuantity = '';
  }

  function cancelCombine() {
    combineMode = false;
    selected = new Set();
    combineName = '';
    combineQuantity = '';
  }
</script>

<svelte:head>
  <title>Grocery List - Forks</title>
</svelte:head>

<div class="grocery">
  <h1>Grocery List</h1>

  {#if items.length === 0}
    <p class="empty">Your grocery list is empty. Add recipes from their detail pages.</p>
  {:else}
    <div class="actions-bar">
      {#if selected.size >= 2 && !combineMode}
        <button class="action-btn combine-btn" on:click={startCombine}>Combine ({selected.size})</button>
      {/if}
      <button class="action-btn" on:click={clearChecked} disabled={gotIt.length === 0}>Clear checked</button>
      <button class="action-btn danger" on:click={clearAll}>Clear all</button>
    </div>

    {#if combineMode}
      <div class="combine-panel">
        <p class="combine-label">Combine selected items:</p>
        <div class="combine-fields">
          <input type="text" bind:value={combineQuantity} placeholder="Qty" class="combine-qty" />
          <input type="text" bind:value={combineName} placeholder="Ingredient name" class="combine-name" />
        </div>
        <div class="combine-actions">
          <button class="action-btn confirm-btn" on:click={confirmCombine} disabled={!combineName.trim()}>Confirm</button>
          <button class="action-btn" on:click={cancelCombine}>Cancel</button>
        </div>
      </div>
    {/if}

    {#if toBuy.length > 0}
      <h2 class="section-heading">To buy</h2>
      <ul class="item-list">
        {#each toBuy as item (item.key)}
          <li class="item" class:selected={selected.has(item.key)}>
            <label class="item-label">
              <input type="checkbox" checked={item.checked} on:change={() => toggleChecked(item.key)} />
              <span class="item-text">{item.displayText}</span>
            </label>
            {#if item.sources.length > 0}
              <span class="item-sources">{item.sources.join(', ')}</span>
            {/if}
            <button class="select-btn" class:active={selected.has(item.key)} on:click={() => toggleSelect(item.key)} aria-label="Select for combining">
              {selected.has(item.key) ? '\u2713' : '\u25CB'}
            </button>
            <button class="item-remove" on:click={() => removeItem(item.key)} aria-label="Remove item">&times;</button>
          </li>
        {/each}
      </ul>
    {/if}

    {#if gotIt.length > 0}
      <h2 class="section-heading got-it">Got it</h2>
      <ul class="item-list">
        {#each gotIt as item (item.key)}
          <li class="item checked">
            <label class="item-label">
              <input type="checkbox" checked={item.checked} on:change={() => toggleChecked(item.key)} />
              <span class="item-text">{item.displayText}</span>
            </label>
            <button class="item-remove" on:click={() => removeItem(item.key)} aria-label="Remove item">&times;</button>
          </li>
        {/each}
      </ul>
    {/if}

    {#if recipeEntries.length > 0}
      <h2 class="section-heading">Recipes on list</h2>
      <ul class="recipe-list">
        {#each recipeEntries as [slug, recipe]}
          <li class="recipe-entry">
            <a href="/recipe/{slug}">{recipe.title}</a>
            {#if recipe.fork}
              <span class="fork-tag">({recipe.fork})</span>
            {/if}
            {#if recipe.servings}
              <span class="servings-tag">{recipe.servings} servings</span>
            {/if}
            <button class="remove-btn" on:click={() => removeRecipeFromGrocery(slug)}>Remove</button>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>

<style>
  .grocery {
    max-width: 600px;
  }

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 1.5rem;
  }

  .empty {
    color: var(--color-text-muted);
    text-align: center;
    padding: 4rem 1rem;
  }

  .actions-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .action-btn {
    padding: 0.35rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .action-btn:hover:not(:disabled) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .action-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .action-btn.danger:hover {
    border-color: var(--color-danger);
    color: var(--color-danger);
  }

  .combine-btn {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .confirm-btn {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .combine-panel {
    padding: 1rem;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    margin-bottom: 1rem;
    background: var(--color-surface);
  }

  .combine-label {
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .combine-fields {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .combine-qty {
    width: 60px;
    padding: 0.4rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
  }

  .combine-name {
    flex: 1;
    padding: 0.4rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
  }

  .combine-actions {
    display: flex;
    gap: 0.5rem;
  }

  .section-heading {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.5rem;
    margin-top: 1.5rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--color-border);
  }

  .section-heading.got-it {
    opacity: 0.6;
  }

  .item-list {
    list-style: none;
    padding: 0;
  }

  .item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.95rem;
  }

  .item.selected {
    background: var(--color-accent-light, #fdf0e6);
    margin: 0 -0.5rem;
    padding: 0.5rem;
    border-radius: var(--radius);
  }

  .item.checked {
    opacity: 0.5;
  }

  .item.checked .item-text {
    text-decoration: line-through;
  }

  .item-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
    cursor: pointer;
  }

  .item-sources {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    white-space: nowrap;
  }

  .select-btn {
    background: none;
    border: 1px solid var(--color-border);
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 0.7rem;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  .select-btn.active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .recipe-list {
    list-style: none;
    padding: 0;
  }

  .recipe-entry {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    font-size: 0.9rem;
  }

  .recipe-entry a {
    color: var(--color-accent);
  }

  .fork-tag, .servings-tag {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .item-remove {
    background: none;
    border: none;
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
    padding: 0 0.15rem;
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.15s, color 0.15s;
  }

  .item:hover .item-remove {
    opacity: 1;
  }

  .item-remove:hover {
    color: var(--color-danger);
  }

  .remove-btn {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    cursor: pointer;
  }

  .remove-btn:hover {
    color: var(--color-danger);
  }
</style>
