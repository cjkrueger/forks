<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let originalServings: number;
  export let currentServings: number;

  const dispatch = createEventDispatcher();

  function decrease() {
    const step = originalServings;
    const next = currentServings - step;
    if (next >= Math.ceil(step / 2)) {
      dispatch('change', { servings: next });
    }
  }

  function increase() {
    dispatch('change', { servings: currentServings + originalServings });
  }

  $: isDefault = currentServings === originalServings;
</script>

<span class="scaler">
  <button class="scale-btn" on:click={decrease} aria-label="Decrease servings">&minus;</button>
  <span class="scale-value">{currentServings}</span>
  <button class="scale-btn" on:click={increase} aria-label="Increase servings">&plus;</button>
  {#if !isDefault}
    <button class="reset-link" on:click={() => dispatch('change', { servings: originalServings })}>reset</button>
  {/if}
</span>

<style>
  .scaler {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }

  .scale-btn {
    width: 26px;
    height: 26px;
    border: 1px solid var(--color-border);
    border-radius: 50%;
    background: var(--color-surface);
    color: var(--color-text);
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }

  .scale-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .scale-value {
    font-weight: 600;
    min-width: 1.5rem;
    text-align: center;
  }

  .reset-link {
    background: none;
    border: none;
    color: var(--color-accent);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0;
    margin-left: 0.25rem;
  }

  .reset-link:hover {
    text-decoration: underline;
  }
</style>
