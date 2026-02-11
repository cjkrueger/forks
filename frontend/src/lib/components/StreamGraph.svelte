<script lang="ts">
  import type { StreamEvent } from '$lib/types';
  import { buildGraph, totalColumns } from '$lib/streamGraph';
  import type { GraphRow, GraphNode } from '$lib/streamGraph';

  export let events: StreamEvent[] = [];
  export let onForkClick: ((slug: string) => void) | null = null;

  $: graphRows = buildGraph(events);
  $: colCount = totalColumns(graphRows);

  let expanded = new Set<string>();

  function toggleExpand(nodeId: string) {
    if (expanded.has(nodeId)) {
      expanded.delete(nodeId);
    } else {
      expanded.add(nodeId);
    }
    expanded = expanded;
  }

  function nodeColor(type: StreamEvent['type']): string {
    switch (type) {
      case 'created': return 'var(--color-accent)';
      case 'edited': return 'var(--color-border)';
      case 'forked': return 'var(--color-secondary)';
      case 'merged': return 'var(--color-success)';
      case 'unmerged': return 'var(--color-danger)';
      case 'failed': return 'var(--color-danger)';
      case 'unfailed': return 'var(--color-accent)';
      default: return 'var(--color-border)';
    }
  }

  function branchColor(column: number): string {
    return column === 0 ? 'var(--color-border)' : 'var(--color-secondary)';
  }

  function formatDate(dateStr: string): string {
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  }

  function connectorRange(node: GraphNode): { min: number; max: number; type: string } | null {
    if (node.connectors.length === 0) return null;
    const c = node.connectors[0];
    return {
      min: Math.min(c.fromColumn, c.toColumn),
      max: Math.max(c.fromColumn, c.toColumn),
      type: c.type
    };
  }

  function connectorColor(type: string): string {
    switch (type) {
      case 'branch-out': return 'var(--color-secondary)';
      case 'merge-in': return 'var(--color-success)';
      case 'unmerge-out': return 'var(--color-danger)';
      default: return 'var(--color-border)';
    }
  }

  /** Return the connector color if this cell is a connector endpoint (not the node column). */
  function connectorEndpointColor(node: GraphNode, col: number): string | null {
    if (col === node.column) return null;
    for (const conn of node.connectors) {
      if (conn.fromColumn === col || conn.toColumn === col) {
        return connectorColor(conn.type);
      }
    }
    return null;
  }

  /**
   * Compute the vertical line state for a given cell.
   * Returns: 'none' | 'full' | 'above' | 'below' | 'split'
   *   split = above + below with gap for dot
   */
  type VertState = 'none' | 'full' | 'above' | 'below' | 'split';

  function getVertState(row: GraphRow, rowIdx: number, col: number, totalRows: number): VertState {
    const node = row.node;
    const isNodeCol = col === node.column;
    const isActive = row.activeBranches.has(col);

    // Connector endpoint columns (not the node column) get partial lines
    // with a gap around the endpoint dot
    if (!isNodeCol) {
      for (const conn of node.connectors) {
        // Merge: branch above connects down to the horizontal line
        if (conn.type === 'merge-in' && conn.fromColumn === col) return 'above';
        // Unmerge: branch reopens, line continues downward from horizontal line
        if (conn.type === 'unmerge-out' && conn.toColumn === col) return 'below';
        // Branch-out: main line splits around the endpoint dot
        if (conn.type === 'branch-out' && conn.fromColumn === col) return 'split';
      }
    }

    // Node column: split line around dot
    if (isNodeCol) {
      // Failed: branch terminates — line above only
      if (node.event.type === 'failed' && col > 0) return 'above';
      // Unfailed: branch reopens — line below only
      if (node.event.type === 'unfailed' && col > 0) return 'below';
      const showAbove = rowIdx > 0 && (col === 0 || node.event.type !== 'forked');
      const showBelow = rowIdx < totalRows - 1;
      if (showAbove && showBelow) return 'split';
      if (showAbove) return 'above';
      if (showBelow) return 'below';
      return 'none';
    }

    // Active pass-through: continuous vertical line
    if (isActive) return 'full';

    return 'none';
  }
</script>

<div class="stream-graph">
  {#each graphRows as row, rowIdx}
    {@const range = connectorRange(row.node)}
    <div class="stream-row">
      <div class="stream-lines">
        {#each Array(colCount) as _, c}
          {@const isNodeCol = c === row.node.column}
          {@const vert = getVertState(row, rowIdx, c, graphRows.length)}
          {@const inRange = range && c >= range.min && c <= range.max}
          {@const color = branchColor(c)}
          {@const endColor = connectorEndpointColor(row.node, c)}
          <div class="line-cell">
            {#if vert === 'full'}
              <div class="vert-line vert-full" style="background: {color}"></div>
            {/if}
            {#if vert === 'above' || vert === 'split'}
              <div class="vert-line vert-above" style="background: {color}"></div>
            {/if}
            {#if vert === 'below' || vert === 'split'}
              <div class="vert-line vert-below" style="background: {color}"></div>
            {/if}

            {#if isNodeCol}
              <div
                class="dot"
                style="border-color: {nodeColor(row.node.event.type)}; background: {row.node.event.type === 'created' ? nodeColor(row.node.event.type) : 'var(--color-surface)'}"
              ></div>
            {/if}

            {#if endColor}
              <div
                class="dot"
                style="border-color: {endColor}; background: var(--color-surface)"
              ></div>
            {/if}

            {#if inRange}
              {@const isStart = c === range.min}
              {@const isEnd = c === range.max}
              <div
                class="horiz-line"
                class:horiz-start={isStart}
                class:horiz-end={isEnd}
                class:horiz-mid={!isStart && !isEnd}
                style="background: {connectorColor(range.type)}"
              ></div>
            {/if}
          </div>
        {/each}
      </div>
      <div class="stream-content">
        {#if row.node.event.type === 'forked' && row.node.branchLabel}
          <span class="branch-label">{row.node.branchLabel}</span>
        {/if}
        {#if row.node.collapsed}
          <button class="collapsed-toggle" on:click={() => toggleExpand(row.node.id)}>
            <span class="chevron" class:chevron-open={expanded.has(row.node.id)}>&#9656;</span>
            <span class="collapsed-text">{row.node.collapsed.count} edits</span>
          </button>
        {:else}
          <span class="stream-message">
            {row.node.event.message}
            {#if (row.node.event.type === 'forked' || row.node.event.type === 'failed' || row.node.event.type === 'unfailed') && row.node.event.fork_slug && onForkClick}
              <button class="stream-fork-link" on:click={() => onForkClick && row.node.event.fork_slug && onForkClick(row.node.event.fork_slug)}>
                view &rarr;
              </button>
            {/if}
          </span>
        {/if}
        <span class="stream-date">{formatDate(row.node.event.date)}</span>
      </div>
    </div>

    <!-- Expanded collapsed edits -->
    {#if row.node.collapsed && expanded.has(row.node.id)}
      {#each row.node.collapsed.events as subEvent, subIdx}
        <div class="stream-row stream-row-expanded">
          <div class="stream-lines">
            {#each Array(colCount) as _, c}
              {@const isSubCol = c === row.node.column}
              {@const isActive = row.activeBranches.has(c)}
              <div class="line-cell">
                {#if isSubCol || isActive}
                  <div class="vert-line vert-full" style="background: {branchColor(c)}"></div>
                {/if}
                {#if isSubCol}
                  <div
                    class="dot dot-small"
                    style="border-color: {nodeColor(subEvent.type)}; background: var(--color-surface)"
                  ></div>
                {/if}
              </div>
            {/each}
          </div>
          <div class="stream-content stream-content-sub">
            <span class="stream-message stream-message-sub">{subEvent.message}</span>
            <span class="stream-date">{formatDate(subEvent.date)}</span>
          </div>
        </div>
      {/each}
    {/if}
  {/each}
</div>

<style>
  .stream-graph {
    display: flex;
    flex-direction: column;
  }

  .stream-row {
    display: flex;
    gap: 0.5rem;
    min-height: 2.5rem;
  }

  .stream-row-expanded {
    min-height: 2rem;
  }

  .stream-lines {
    display: flex;
    flex-shrink: 0;
    align-self: stretch;
  }

  .line-cell {
    position: relative;
    width: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid var(--color-border);
    box-sizing: border-box;
    flex-shrink: 0;
    z-index: 2;
    position: relative;
  }

  .dot-small {
    width: 10px;
    height: 10px;
  }

  .vert-line {
    position: absolute;
    width: 2px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1;
  }

  .vert-above {
    top: 0;
    bottom: calc(50% + 7px);
  }

  .vert-below {
    top: calc(50% + 7px);
    bottom: 0;
  }

  .vert-full {
    top: 0;
    bottom: 0;
  }

  .horiz-line {
    position: absolute;
    height: 2px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 1;
  }

  .horiz-start {
    left: 50%;
    right: 0;
  }

  .horiz-end {
    left: 0;
    right: 50%;
  }

  .horiz-mid {
    left: 0;
    right: 0;
  }

  .stream-content {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
    padding-top: 1px;
    padding-bottom: 0.5rem;
    min-width: 0;
  }

  .stream-content-sub {
    padding-top: 0;
    padding-bottom: 0.25rem;
  }

  .branch-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .stream-message {
    font-size: 0.85rem;
    color: var(--color-text);
    flex: 1;
    min-width: 0;
  }

  .stream-message-sub {
    font-size: 0.8rem;
    color: var(--color-text-muted);
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

  .collapsed-toggle {
    background: none;
    border: none;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    font-style: italic;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .collapsed-toggle:hover {
    color: var(--color-text);
  }

  .chevron {
    display: inline-block;
    font-size: 0.7rem;
    font-style: normal;
    transition: transform 0.15s ease;
  }

  .chevron-open {
    transform: rotate(90deg);
  }

  .collapsed-text {
    font-style: italic;
  }
</style>
