<script lang="ts" context="module">
  export interface Timer {
    id: number;
    label: string;
    totalSeconds: number;
    remainingSeconds: number;
    status: 'running' | 'done' | 'dismissed';
  }
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let timers: Timer[] = [];

  const dispatch = createEventDispatcher();

  function formatTime(secs: number): string {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function dismiss(id: number) {
    dispatch('dismiss', { id });
  }

  $: activeTimers = timers.filter(t => t.status !== 'dismissed');
</script>

{#if activeTimers.length > 0}
  <div class="timer-bar">
    {#each activeTimers as timer (timer.id)}
      <div class="timer-pill" class:done={timer.status === 'done'}>
        <span class="timer-label">{timer.label}</span>
        <span class="timer-time">
          {#if timer.status === 'done'}
            Done!
          {:else}
            {formatTime(timer.remainingSeconds)}
          {/if}
        </span>
        <button class="timer-dismiss" on:click={() => dismiss(timer.id)} aria-label="Dismiss timer">x</button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .timer-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--color-surface);
    border-top: 1px solid var(--color-border);
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.08);
    z-index: 200;
    overflow-x: auto;
    justify-content: center;
  }

  .timer-pill {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.75rem;
    background: var(--color-accent);
    color: white;
    border-radius: 999px;
    font-size: 0.85rem;
    min-height: 44px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  .timer-pill.done {
    background: #e74c3c;
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  .timer-label {
    font-weight: 600;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .timer-time {
    font-variant-numeric: tabular-nums;
  }

  .timer-dismiss {
    background: rgba(255, 255, 255, 0.3);
    border: none;
    color: white;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 0.7rem;
    font-weight: bold;
  }

  .timer-dismiss:hover {
    background: rgba(255, 255, 255, 0.5);
  }
</style>
