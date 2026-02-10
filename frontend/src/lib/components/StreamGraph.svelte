<script lang="ts">
  import type { StreamEvent } from '$lib/types';

  export let events: StreamEvent[] = [];
  export let onForkClick: ((slug: string) => void) | null = null;

  function nodeColor(type: StreamEvent['type']): string {
    switch (type) {
      case 'created': return 'var(--color-accent)';
      case 'edited': return 'var(--color-border)';
      case 'forked': return 'var(--color-secondary)';
      case 'merged': return 'var(--color-success)';
      default: return 'var(--color-border)';
    }
  }

  function formatDate(dateStr: string): string {
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  }
</script>

<div class="stream-graph">
  {#each events as event, i}
    <div class="stream-row">
      <div class="stream-line-col">
        <div
          class="stream-node"
          style="border-color: {nodeColor(event.type)}; background: {event.type === 'created' ? nodeColor(event.type) : 'var(--color-surface)'}"
        ></div>
        {#if i < events.length - 1}
          <div class="stream-connector"></div>
        {/if}
      </div>
      <div class="stream-content">
        <span class="stream-message">
          {event.message}
          {#if event.type === 'forked' && event.fork_slug && onForkClick}
            <button class="stream-fork-link" on:click={() => onForkClick && event.fork_slug && onForkClick(event.fork_slug)}>
              view &rarr;
            </button>
          {/if}
        </span>
        <span class="stream-date">{formatDate(event.date)}</span>
      </div>
    </div>
  {/each}
</div>

<style>
  .stream-graph {
    display: flex;
    flex-direction: column;
  }

  .stream-row {
    display: flex;
    gap: 0.75rem;
    min-height: 2.5rem;
  }

  .stream-line-col {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 20px;
    flex-shrink: 0;
  }

  .stream-node {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid var(--color-border);
    flex-shrink: 0;
    box-sizing: border-box;
  }

  .stream-connector {
    width: 2px;
    flex: 1;
    background: var(--color-border);
    min-height: 12px;
  }

  .stream-content {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
    flex: 1;
    padding-top: 1px;
    padding-bottom: 0.5rem;
  }

  .stream-message {
    font-size: 0.85rem;
    color: var(--color-text);
    flex: 1;
  }

  .stream-date {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .stream-fork-link {
    background: none;
    border: none;
    color: var(--color-secondary);
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0 0.25rem;
    text-decoration: none;
  }

  .stream-fork-link:hover {
    text-decoration: underline;
  }
</style>
