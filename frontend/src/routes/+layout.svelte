<script lang="ts">
  import '../app.css';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { listRecipes, getSettings } from '$lib/api';
  import { recipeCount } from '$lib/grocery';
  import { startSyncPolling, syncStatus, isConnected } from '$lib/sync';
  import { theme, toggleTheme } from '$lib/theme';
  import { onMount } from 'svelte';

  let searchQuery = '';
  let allTags: { name: string; count: number }[] = [];
  let sidebarOpen = false;

  $: activeTags = $page.url.searchParams.get('tags')?.split(',').filter(Boolean) || [];

  onMount(async () => {
    try {
      const settings = await getSettings();
      startSyncPolling(settings.sync.interval_seconds * 1000, settings.sync.enabled);
    } catch {
      startSyncPolling();
    }
    const recipes = await listRecipes();
    const tagMap = new Map<string, number>();
    for (const r of recipes) {
      for (const tag of r.tags) {
        tagMap.set(tag, (tagMap.get(tag) || 0) + 1);
      }
    }
    allTags = Array.from(tagMap.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  });

  function handleSearch() {
    if (searchQuery.trim()) {
      goto(`/?q=${encodeURIComponent(searchQuery.trim())}`);
    } else {
      goto('/');
    }
  }

  function toggleTag(tag: string) {
    let tags = [...activeTags];
    if (tags.includes(tag)) {
      tags = tags.filter(t => t !== tag);
    } else {
      tags.push(tag);
    }
    if (tags.length > 0) {
      goto(`/?tags=${tags.join(',')}`);
    } else {
      goto('/');
    }
    sidebarOpen = false;
  }
</script>

<div class="app">
  <header class="topbar">
    <div class="topbar-left">
      <button class="menu-btn" on:click={() => sidebarOpen = !sidebarOpen} aria-label="Toggle menu">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <a href="/" class="logo"><em>Forks</em></a>
    </div>
    <form class="search-form" on:submit|preventDefault={handleSearch}>
      <input
        type="text"
        placeholder="Search recipes..."
        bind:value={searchQuery}
        class="search-input"
      />
    </form>
    <nav class="topbar-nav">
      <a href="/add" class="add-btn" aria-label="Add recipe">
        <svg class="add-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        <span class="add-label">Add</span>
      </a>
      <a href="/planner" class="nav-link planner-link" aria-label="Meal planner">
        <svg class="planner-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
        <span class="planner-label">Planner</span>
      </a>
      <a href="/grocery" class="nav-link grocery-link" aria-label="Grocery list">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
        </svg>
        {#if $recipeCount > 0}
          <span class="grocery-badge">{$recipeCount}</span>
        {/if}
      </a>
      {#if $isConnected}
        <span class="sync-indicator" class:error={$syncStatus.error} title={$syncStatus.error || 'Synced'}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
          </svg>
        </span>
      {/if}
      <a href="/settings" class="settings-link" aria-label="Settings">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      </a>
      <button class="theme-toggle" on:click={toggleTheme} aria-label="Toggle theme">
        {#if $theme === 'dark'}
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
          </svg>
        {:else}
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </svg>
        {/if}
      </button>
    </nav>
  </header>

  <div class="layout">
    <aside class="sidebar" class:open={sidebarOpen}>
      <nav class="tag-list">
        <h3 class="sidebar-heading">Tags</h3>
        {#each allTags as tag}
          <button
            class="tag-btn"
            class:active={activeTags.includes(tag.name)}
            on:click={() => toggleTag(tag.name)}
          >
            {tag.name}
            <span class="tag-count">{tag.count}</span>
          </button>
        {/each}
      </nav>
    </aside>

    {#if sidebarOpen}
      <button class="overlay" on:click={() => sidebarOpen = false} aria-label="Close menu"></button>
    {/if}

    <main class="content">
      <slot />
    </main>
  </div>
</div>

<style>
  .app {
    min-height: 100vh;
  }

  .topbar {
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 1.25rem;
    padding: 0.75rem 2rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    box-shadow: var(--shadow-sm);
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }

  .menu-btn {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text);
    padding: 0.25rem;
  }

  .logo {
    font-family: var(--font-logo);
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-accent);
    text-decoration: none;
    letter-spacing: -0.02em;
  }

  .logo:hover {
    text-decoration: none;
  }

  .search-form {
    flex: 1;
    max-width: 560px;
  }

  .search-input {
    width: 100%;
    padding: 0.5rem 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.875rem;
    font-family: var(--font-body);
    background: var(--color-bg);
    color: var(--color-text);
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .search-input:focus {
    border-color: var(--color-accent);
    box-shadow: 0 0 0 3px var(--color-accent-light);
  }

  .topbar-nav {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }

  .add-btn {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.5rem 1rem;
    background: var(--color-accent);
    color: white;
    border-radius: var(--radius);
    font-size: 0.85rem;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
    transition: opacity 0.15s;
  }

  .add-btn:hover {
    opacity: 0.9;
    text-decoration: none;
  }

  .add-icon {
    flex-shrink: 0;
  }

  .planner-link {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .planner-icon {
    display: none;
  }

  .nav-link {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    text-decoration: none;
    padding: 0.4rem 0.75rem;
    border-radius: var(--radius);
    transition: color 0.15s, background 0.15s;
    white-space: nowrap;
  }

  .nav-link:hover {
    color: var(--color-accent);
    background: var(--color-accent-light);
    text-decoration: none;
  }

  .grocery-link {
    position: relative;
    display: flex;
    align-items: center;
  }

  .grocery-badge {
    position: absolute;
    top: -2px;
    right: -4px;
    background: var(--color-accent);
    color: white;
    font-size: 0.6rem;
    font-weight: 700;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .theme-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border: 1px solid var(--color-border);
    border-radius: 50%;
    background: var(--color-bg);
    color: var(--color-text-muted);
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s, background 0.15s;
    flex-shrink: 0;
  }

  .theme-toggle:hover {
    color: var(--color-accent);
    border-color: var(--color-accent);
    background: var(--color-accent-light);
  }

  .sync-indicator {
    display: flex;
    align-items: center;
    color: var(--color-success);
  }

  .sync-indicator.error {
    color: var(--color-danger);
  }

  .settings-link {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border: 1px solid var(--color-border);
    border-radius: 50%;
    background: var(--color-bg);
    color: var(--color-text-muted);
    transition: color 0.15s, border-color 0.15s, background 0.15s;
  }

  .settings-link:hover {
    color: var(--color-accent);
    border-color: var(--color-accent);
    background: var(--color-accent-light);
    text-decoration: none;
  }

  .layout {
    display: flex;
  }

  .sidebar {
    position: sticky;
    top: 53px;
    width: var(--sidebar-width);
    height: calc(100vh - 53px);
    overflow-y: auto;
    padding: 1.5rem 1rem;
    border-right: 1px solid var(--color-border);
    background: var(--color-surface);
    flex-shrink: 0;
  }

  .sidebar-heading {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted);
    margin-bottom: 0.75rem;
    font-weight: 600;
  }

  .tag-list {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .tag-btn {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0.75rem;
    border: none;
    border-radius: var(--radius);
    background: transparent;
    color: var(--color-text);
    font-size: 0.85rem;
    font-family: var(--font-body);
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    text-align: left;
  }

  .tag-btn:hover {
    background: var(--color-tag);
  }

  .tag-btn.active {
    background: var(--color-accent-light);
    color: var(--color-accent);
    font-weight: 600;
  }

  .tag-count {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .tag-btn.active .tag-count {
    color: var(--color-accent);
  }

  .content {
    flex: 1;
    padding: 2rem;
    max-width: 1200px;
  }

  .overlay {
    display: none;
  }

  /* Tablet: collapse planner text to icon, shrink add button */
  @media (max-width: 900px) {
    .topbar {
      padding: 0.75rem 1.25rem;
      gap: 1rem;
    }

    .planner-icon {
      display: block;
    }

    .planner-label {
      display: none;
    }

    .add-label {
      display: none;
    }

    .add-btn {
      padding: 0.5rem;
      border-radius: 50%;
    }
  }

  /* Mobile: sidebar as overlay, compact topbar */
  @media (max-width: 768px) {
    .menu-btn {
      display: block;
    }

    .topbar {
      padding: 0.6rem 1rem;
      gap: 0.75rem;
    }

    .search-form {
      max-width: none;
    }

    .topbar-nav {
      gap: 0.5rem;
    }

    .sidebar {
      position: fixed;
      top: 53px;
      left: 0;
      z-index: 50;
      transform: translateX(-100%);
      transition: transform 0.2s ease;
      box-shadow: var(--shadow-lg);
    }

    .sidebar.open {
      transform: translateX(0);
    }

    .overlay {
      display: block;
      position: fixed;
      inset: 0;
      top: 53px;
      z-index: 40;
      background: var(--overlay);
      border: none;
      cursor: pointer;
    }

    .content {
      padding: 1rem;
    }
  }
</style>
