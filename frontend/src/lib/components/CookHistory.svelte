<script lang="ts">
  import { deleteCookHistory } from '$lib/api';
  import type { CookHistoryEntry } from '$lib/types';

  export let slug: string;
  export let cookHistory: CookHistoryEntry[];

  let expanded = false;
  let deleting: number | null = null;

  function formatDate(dateStr: string): string {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }

  async function handleDelete(index: number) {
    deleting = index;
    try {
      const result = await deleteCookHistory(slug, index);
      cookHistory = result.cook_history;
    } catch (e) {
      // ignore
    }
    deleting = null;
  }
</script>

{#if cookHistory.length > 0}
  <div class="cook-history">
    <button class="history-toggle" on:click={() => expanded = !expanded}>
      Last cooked {formatDate(cookHistory[0].date)}{cookHistory[0].fork ? ` (${cookHistory[0].fork})` : ''}
      {#if cookHistory.length > 1}
        <span class="history-count">({cookHistory.length} total)</span>
      {/if}
      <span class="chevron" class:open={expanded}></span>
    </button>

    {#if expanded}
      <ul class="history-list">
        {#each cookHistory as entry, i}
          <li class="history-entry">
            <span>{formatDate(entry.date)}{entry.fork ? ` - ${entry.fork}` : ''}</span>
            <button
              class="delete-entry"
              on:click={() => handleDelete(i)}
              disabled={deleting === i}
              aria-label="Delete entry"
            >x</button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
{/if}

<style>
  .cook-history {
    margin-bottom: 0.75rem;
  }

  .history-toggle {
    background: none;
    border: none;
    color: var(--color-text-muted);
    font-size: 0.85rem;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .history-toggle:hover {
    color: var(--color-accent);
  }

  .history-count {
    color: var(--color-text-muted);
    font-size: 0.8rem;
  }

  .chevron {
    display: inline-block;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid currentColor;
    transition: transform 0.15s;
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .history-list {
    list-style: none;
    padding: 0;
    margin-top: 0.5rem;
    margin-left: 0.5rem;
  }

  .history-entry {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.25rem 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .delete-entry {
    background: none;
    border: none;
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 0.75rem;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
  }

  .delete-entry:hover {
    background: #fdf0f0;
    color: #c0392b;
  }
</style>
