<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let label: string;
  export let totalSeconds: number;
  export let running = false;
  export let remainingSeconds: number | null = null;

  const dispatch = createEventDispatcher();

  function formatTime(secs: number): string {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function handleClick() {
    if (!running) {
      dispatch('start', { totalSeconds, label });
    }
  }
</script>

<button class="timer-chip" class:running on:click={handleClick} disabled={running}>
  {#if running && remainingSeconds !== null}
    {formatTime(remainingSeconds)}
  {:else}
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5,3 19,12 5,21" />
    </svg>
    {label}
  {/if}
</button>

<style>
  .timer-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.5rem;
    border: 1.5px solid var(--color-accent);
    border-radius: 999px;
    background: var(--color-accent-light, #fdf0e6);
    color: var(--color-accent);
    font-size: 0.85em;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    vertical-align: middle;
    line-height: 1.4;
  }

  .timer-chip:hover:not(:disabled) {
    background: var(--color-accent);
    color: white;
  }

  .timer-chip.running {
    background: var(--color-accent);
    color: white;
    cursor: default;
    font-variant-numeric: tabular-nums;
  }

  .timer-chip:disabled {
    opacity: 0.9;
  }
</style>
