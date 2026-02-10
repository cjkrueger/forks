<script lang="ts">
  export let columns: { key: string; label: string }[] = [];
  export let visible: string[] = [];
  export let onChange: (visible: string[]) => void = () => {};

  let open = false;

  function toggle(key: string) {
    if (key === 'title') return;
    const next = visible.includes(key)
      ? visible.filter(k => k !== key)
      : [...visible, key];
    onChange(next);
  }

  function handleClickOutside(e: MouseEvent) {
    if (open && !(e.target as HTMLElement).closest('.column-picker')) {
      open = false;
    }
  }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="column-picker">
  <button
    class="picker-btn"
    class:open
    on:click|stopPropagation={() => (open = !open)}
    title="Customize columns"
    aria-label="Customize columns"
  >
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  </button>

  {#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="dropdown" on:click|stopPropagation>
      <div class="dropdown-header">Columns</div>
      {#each columns as col}
        <label class="dropdown-item" class:disabled={col.key === 'title'}>
          <input
            type="checkbox"
            checked={visible.includes(col.key)}
            disabled={col.key === 'title'}
            on:change={() => toggle(col.key)}
          />
          <span>{col.label}</span>
        </label>
      {/each}
    </div>
  {/if}
</div>

<style>
  .column-picker {
    position: relative;
  }

  .picker-btn {
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

  .picker-btn:hover,
  .picker-btn.open {
    color: var(--color-accent);
    border-color: var(--color-accent);
  }

  .dropdown {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    min-width: 180px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-md);
    z-index: 20;
    padding: 0.35rem 0;
  }

  .dropdown-header {
    padding: 0.4rem 0.75rem;
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--color-border);
    margin-bottom: 0.2rem;
  }

  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.75rem;
    font-size: 0.85rem;
    color: var(--color-text);
    cursor: pointer;
    transition: background 0.1s;
  }

  .dropdown-item:hover {
    background: var(--color-surface-hover);
  }

  .dropdown-item.disabled {
    opacity: 0.5;
    cursor: default;
  }

  .dropdown-item input[type="checkbox"] {
    accent-color: var(--color-accent);
    cursor: pointer;
  }

  .dropdown-item.disabled input[type="checkbox"] {
    cursor: default;
  }
</style>
