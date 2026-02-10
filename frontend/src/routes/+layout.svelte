<script lang="ts">
  import '../app.css';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { listRecipes } from '$lib/api';
  import { recipeCount } from '$lib/grocery';
  import { onMount } from 'svelte';

  let searchQuery = '';
  let allTags: { name: string; count: number }[] = [];
  let sidebarOpen = false;

  $: activeTags = $page.url.searchParams.get('tags')?.split(',').filter(Boolean) || [];

  onMount(async () => {
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
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <a href="/" class="logo">Forks</a>
    </div>
    <form class="search-form" on:submit|preventDefault={handleSearch}>
      <input
        type="text"
        placeholder="Search recipes..."
        bind:value={searchQuery}
        class="search-input"
      />
    </form>
    <a href="/add" class="add-btn" aria-label="Add recipe">+ Add</a>
    <a href="/grocery" class="grocery-link" aria-label="Grocery list">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
      </svg>
      {#if $recipeCount > 0}
        <span class="grocery-badge">{$recipeCount}</span>
      {/if}
    </a>
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
    gap: 1rem;
    padding: 0.75rem 1.5rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    box-shadow: var(--shadow);
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
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
    max-width: 400px;
  }

  .search-input {
    width: 100%;
    padding: 0.5rem 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.9rem;
    background: var(--color-bg);
    color: var(--color-text);
    outline: none;
    transition: border-color 0.2s;
  }

  .search-input:focus {
    border-color: var(--color-accent);
  }

  .add-btn {
    padding: 0.5rem 1rem;
    background: var(--color-accent);
    color: white;
    border-radius: var(--radius);
    font-size: 0.85rem;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
  }

  .add-btn:hover {
    opacity: 0.9;
    text-decoration: none;
  }

  .grocery-link {
    position: relative;
    text-decoration: none;
    color: var(--color-text-muted);
    display: flex;
    align-items: center;
    transition: color 0.15s;
  }

  .grocery-link:hover {
    color: var(--color-accent);
    text-decoration: none;
  }

  .grocery-badge {
    position: absolute;
    top: -6px;
    right: -8px;
    background: var(--color-accent);
    color: white;
    font-size: 0.65rem;
    font-weight: 700;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .layout {
    display: flex;
  }

  .sidebar {
    position: sticky;
    top: 57px;
    width: var(--sidebar-width);
    height: calc(100vh - 57px);
    overflow-y: auto;
    padding: 1.5rem 1rem;
    border-right: 1px solid var(--color-border);
    background: var(--color-surface);
    flex-shrink: 0;
  }

  .sidebar-heading {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.75rem;
  }

  .tag-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
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
    cursor: pointer;
    transition: background 0.15s;
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

  @media (max-width: 768px) {
    .menu-btn {
      display: block;
    }

    .sidebar {
      position: fixed;
      top: 57px;
      left: 0;
      z-index: 50;
      transform: translateX(-100%);
      transition: transform 0.2s ease;
      box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
    }

    .sidebar.open {
      transform: translateX(0);
    }

    .overlay {
      display: block;
      position: fixed;
      inset: 0;
      top: 57px;
      z-index: 40;
      background: rgba(0, 0, 0, 0.3);
      border: none;
      cursor: pointer;
    }

    .content {
      padding: 1rem;
    }
  }
</style>
