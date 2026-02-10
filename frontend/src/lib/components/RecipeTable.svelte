<script lang="ts">
  import type { RecipeSummary } from '$lib/types';

  export let recipes: RecipeSummary[] = [];
  export let visibleColumns: string[] = ['title', 'tags', 'cook_time', 'likes', 'last_cooked'];

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

  let sortKey = 'title';
  let sortAsc = true;

  $: columns = allColumns.filter(c => visibleColumns.includes(c.key));

  function getLastCooked(recipe: RecipeSummary): string | null {
    if (!recipe.cook_history || recipe.cook_history.length === 0) return null;
    const dates = recipe.cook_history
      .map(e => e.date)
      .filter(Boolean)
      .sort((a, b) => b.localeCompare(a));
    return dates[0] || null;
  }

  function getDomain(url: string | null): string {
    if (!url) return '';
    try {
      const hostname = new URL(url).hostname;
      return hostname.replace(/^www\./, '');
    } catch {
      return url.length > 30 ? url.slice(0, 30) + '...' : url;
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  }

  function getCellValue(recipe: RecipeSummary, key: string): string | number | null {
    switch (key) {
      case 'title': return recipe.title;
      case 'tags': return recipe.tags.join(', ');
      case 'prep_time': return recipe.prep_time;
      case 'cook_time': return recipe.cook_time;
      case 'servings': return recipe.servings;
      case 'likes': return recipe.likes;
      case 'last_cooked': return getLastCooked(recipe);
      case 'date_added': return recipe.date_added;
      case 'source': return recipe.source;
      default: return null;
    }
  }

  function handleSort(key: string) {
    if (sortKey === key) {
      sortAsc = !sortAsc;
    } else {
      sortKey = key;
      sortAsc = true;
    }
  }

  $: sortedRecipes = [...recipes].sort((a, b) => {
    const aVal = getCellValue(a, sortKey);
    const bVal = getCellValue(b, sortKey);

    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;

    let cmp: number;
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      cmp = aVal - bVal;
    } else {
      cmp = String(aVal).localeCompare(String(bVal), undefined, { sensitivity: 'base' });
    }
    return sortAsc ? cmp : -cmp;
  });
</script>

<div class="table-wrap">
  <table>
    <thead>
      <tr>
        {#each columns as col}
          <th
            class:active={sortKey === col.key}
            on:click={() => handleSort(col.key)}
          >
            <span class="th-label">
              {col.label}
              {#if sortKey === col.key}
                <span class="sort-arrow">{sortAsc ? '▲' : '▼'}</span>
              {/if}
            </span>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each sortedRecipes as recipe (recipe.slug)}
        <tr>
          {#each columns as col}
            <td class="cell-{col.key}">
              {#if col.key === 'title'}
                <a href="/recipe/{recipe.slug}" class="title-link">{recipe.title}</a>
              {:else if col.key === 'tags'}
                <div class="tags-cell">
                  {#each recipe.tags.slice(0, 4) as tag}
                    <span class="pill">{tag}</span>
                  {/each}
                  {#if recipe.tags.length > 4}
                    <span class="pill pill-more">+{recipe.tags.length - 4}</span>
                  {/if}
                </div>
              {:else if col.key === 'likes'}
                {#if recipe.likes > 0}
                  <span class="likes-cell">&hearts; {recipe.likes}</span>
                {:else}
                  <span class="muted">&mdash;</span>
                {/if}
              {:else if col.key === 'last_cooked'}
                {#if getLastCooked(recipe)}
                  {formatDate(getLastCooked(recipe))}
                {:else}
                  <span class="muted">Never</span>
                {/if}
              {:else if col.key === 'date_added'}
                {formatDate(recipe.date_added)}
              {:else if col.key === 'source'}
                {#if recipe.source}
                  <a href={recipe.source} class="source-link" target="_blank" rel="noopener noreferrer">
                    {getDomain(recipe.source)}
                  </a>
                {:else}
                  <span class="muted">&mdash;</span>
                {/if}
              {:else}
                {getCellValue(recipe, col.key) ?? ''}
              {/if}
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .table-wrap {
    overflow-x: auto;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg, var(--radius));
    background: var(--color-surface);
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
    white-space: nowrap;
  }

  thead {
    position: sticky;
    top: 0;
    z-index: 1;
  }

  th {
    padding: 0.65rem 0.85rem;
    text-align: left;
    font-weight: 600;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border-bottom: 2px solid var(--color-border);
    background: var(--color-surface);
    cursor: pointer;
    user-select: none;
    transition: color 0.15s;
  }

  th:hover {
    color: var(--color-accent);
  }

  th.active {
    color: var(--color-accent);
  }

  .th-label {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }

  .sort-arrow {
    font-size: 0.65rem;
    line-height: 1;
  }

  td {
    padding: 0.6rem 0.85rem;
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text);
    vertical-align: middle;
  }

  tr:last-child td {
    border-bottom: none;
  }

  tbody tr {
    transition: background 0.1s;
  }

  tbody tr:hover {
    background: var(--color-surface-hover);
  }

  .title-link {
    font-weight: 600;
    color: var(--color-text);
    text-decoration: none;
  }

  .title-link:hover {
    color: var(--color-accent);
    text-decoration: underline;
  }

  .tags-cell {
    display: flex;
    gap: 0.3rem;
    flex-wrap: wrap;
  }

  .pill {
    font-size: 0.7rem;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    background: var(--color-tag);
    color: var(--color-text-muted);
    white-space: nowrap;
  }

  .pill-more {
    opacity: 0.7;
  }

  .likes-cell {
    color: var(--color-text-muted);
  }

  .source-link {
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .source-link:hover {
    color: var(--color-accent);
  }

  .muted {
    color: var(--color-text-muted);
    opacity: 0.5;
  }

  .cell-tags {
    white-space: normal;
    min-width: 120px;
  }

  .cell-title {
    white-space: normal;
    min-width: 180px;
    max-width: 300px;
  }
</style>
