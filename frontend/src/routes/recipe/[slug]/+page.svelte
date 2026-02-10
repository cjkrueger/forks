<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getRecipe, getFork, exportForkUrl, addCookHistory, getForkHistory, mergeFork, getRecipeStream } from '$lib/api';
  import { renderMarkdown } from '$lib/markdown';
  import { mergeContent, getModifiedSections, parseSections } from '$lib/sections';
  import { parseIngredient, formatIngredient } from '$lib/ingredients';
  import { groceryStore, addRecipeToGrocery, removeRecipeFromGrocery } from '$lib/grocery';
  import type { Recipe, ForkDetail, StreamEvent } from '$lib/types';
  import CookMode from '$lib/components/CookMode.svelte';
  import CookHistory from '$lib/components/CookHistory.svelte';
  import FavoriteButton from '$lib/components/FavoriteButton.svelte';
  import ServingScaler from '$lib/components/ServingScaler.svelte';
  import StreamGraph from '$lib/components/StreamGraph.svelte';

  let recipe: Recipe | null = null;
  let loading = true;
  let error = false;

  // Fork state
  let selectedFork: string | null = null;
  let forkDetail: ForkDetail | null = null;
  let forkLoading = false;
  let modifiedSections: Set<string> = new Set();

  // Cook mode state
  let cookMode = false;

  // Fork history state
  let historyOpen = false;
  let historyEntries: { hash: string; date: string; message: string; content?: string }[] = [];
  let historyLoading = false;

  // Merge state
  let merging = false;
  let mergeMessage = '';

  // Stream state
  let streamEvents: StreamEvent[] = [];
  let streamOpen = false;
  let streamLoading = false;

  // Scaling state
  let currentServings: number | null = null;
  let originalServings: number | null = null;

  $: {
    if (recipe?.servings) {
      const parsed = parseInt(recipe.servings);
      if (!isNaN(parsed) && parsed > 0) {
        originalServings = parsed;
        if (currentServings === null) currentServings = parsed;
      } else {
        originalServings = null;
      }
    }
  }

  $: scaleFactor = (originalServings && currentServings) ? currentServings / originalServings : 1;

  // Grocery state
  $: onGroceryList = recipe ? recipe.slug in $groceryStore.recipes : false;

  $: slug = $page.params.slug as string;

  onMount(async () => {
    try {
      recipe = await getRecipe(slug);
      // Check query param first, then localStorage
      const queryFork = $page.url.searchParams.get('fork');
      const defaultFork = queryFork || localStorage.getItem(`forks-default-${slug}`);
      if (defaultFork && recipe.forks.some(f => f.name === defaultFork)) {
        await selectFork(defaultFork);
      }
      // Check for cook mode param
      if ($page.url.searchParams.get('cook')) {
        cookMode = true;
      }
    } catch (e) {
      error = true;
    }
    loading = false;
  });

  async function selectFork(forkName: string | null) {
    selectedFork = forkName;
    forkDetail = null;
    modifiedSections = new Set();
    currentServings = originalServings;
    if (forkName && recipe) {
      forkLoading = true;
      try {
        forkDetail = await getFork(slug, forkName);
        modifiedSections = getModifiedSections(forkDetail.content);
      } catch (e) {
        forkDetail = null;
      }
      forkLoading = false;
    }
  }

  function setAsDefault() {
    if (selectedFork) {
      localStorage.setItem(`forks-default-${slug}`, selectedFork);
    } else {
      localStorage.removeItem(`forks-default-${slug}`);
    }
    isDefault = true;
  }

  $: displayContent = (() => {
    if (!recipe) return '';
    if (forkDetail) {
      return mergeContent(recipe.content, forkDetail.content);
    }
    return recipe.content;
  })();

  $: displayTitle = forkDetail ? forkDetail.fork_name : recipe?.title ?? '';

  function renderWithHighlights(content: string, modified: Set<string>, scale: number): string {
    if (modified.size === 0 && scale === 1) return renderMarkdown(content);

    const sections = parseSections(content);
    let html = '';
    for (const section of sections) {
      let sectionContent = section.content;

      // Scale ingredient quantities
      if (section.name.toLowerCase() === 'ingredients' && scale !== 1) {
        sectionContent = sectionContent.split('\n').map(line => {
          if (line.trim().startsWith('- ')) {
            const parsed = parseIngredient(line.trim());
            return `- ${formatIngredient(parsed, scale)}`;
          }
          return line;
        }).join('\n');
      }

      if (section.name === '_preamble') {
        html += renderMarkdown(sectionContent);
      } else {
        const isModified = modified.has(section.name);
        const sectionMd = `## ${section.name}\n\n${sectionContent}`;
        if (isModified) {
          html += `<div class="fork-modified">${renderMarkdown(sectionMd)}</div>`;
        } else {
          html += renderMarkdown(sectionMd);
        }
      }
    }
    return html;
  }

  $: renderedBody = renderWithHighlights(displayContent, modifiedSections, scaleFactor);

  let isDefault = true;
  $: {
    const stored = localStorage.getItem(`forks-default-${slug}`);
    if (selectedFork) {
      isDefault = stored === selectedFork;
    } else {
      isDefault = !stored;
    }
  }

  // Cook mode helpers
  function parseCookData(content: string) {
    const sections = parseSections(content);
    let ingredients: string[] = [];
    let steps: string[] = [];
    let notes: string[] = [];

    for (const section of sections) {
      if (section.name.toLowerCase() === 'ingredients') {
        ingredients = section.content.split('\n')
          .map(l => l.trim())
          .filter(l => l.startsWith('- '))
          .map(l => l.replace(/^-\s*/, ''));
      } else if (section.name.toLowerCase() === 'instructions') {
        steps = section.content.split('\n')
          .map(l => l.trim())
          .filter(l => /^\d+\./.test(l))
          .map(l => l.replace(/^\d+\.\s*/, ''));
      } else if (section.name.toLowerCase() === 'notes') {
        notes = section.content.split('\n')
          .map(l => l.trim())
          .filter(l => l.startsWith('- '))
          .map(l => l.replace(/^-\s*/, ''));
      }
    }

    return { ingredients, steps, notes };
  }

  async function enterCookMode() {
    cookMode = true;
    if (recipe) {
      try {
        const result = await addCookHistory(slug, selectedFork || undefined);
        recipe = { ...recipe, cook_history: result.cook_history };
      } catch (e) {}
    }
    const url = new URL(window.location.href);
    url.searchParams.set('cook', '1');
    window.history.replaceState({}, '', url.toString());
  }

  function exitCookMode() {
    cookMode = false;
    const url = new URL(window.location.href);
    url.searchParams.delete('cook');
    window.history.replaceState({}, '', url.toString());
  }

  $: cookData = parseCookData(displayContent);

  async function toggleHistory() {
    if (historyOpen) {
      historyOpen = false;
      return;
    }
    if (!selectedFork || !recipe) return;
    historyLoading = true;
    historyOpen = true;
    try {
      const data = await getForkHistory(recipe.slug, selectedFork);
      historyEntries = data.history;
    } catch (e) {
      historyEntries = [];
    }
    historyLoading = false;
  }

  async function handleMergeFork() {
    if (!recipe || !selectedFork) return;
    if (!confirm(`Merge "${forkDetail?.fork_name}" changes into the original recipe?`)) return;
    merging = true;
    mergeMessage = '';
    try {
      await mergeFork(recipe.slug, selectedFork);
      recipe = await getRecipe(slug);
      if (selectedFork) await selectFork(selectedFork);
      mergeMessage = 'Fork merged into original';
    } catch (e: any) {
      mergeMessage = e.message || 'Merge failed';
    }
    merging = false;
  }

  async function toggleStream() {
    if (streamOpen) { streamOpen = false; return; }
    if (!recipe) return;
    streamLoading = true;
    streamOpen = true;
    try {
      const data = await getRecipeStream(recipe.slug);
      streamEvents = data.events;
    } catch (e) {
      streamEvents = [];
    }
    streamLoading = false;
  }

  function handleStreamForkClick(forkSlug: string) {
    selectFork(forkSlug);
    streamOpen = false;
  }

  function getIngredientLines(content: string): string[] {
    const sections = parseSections(content);
    for (const section of sections) {
      if (section.name.toLowerCase() === 'ingredients') {
        return section.content.split('\n')
          .map(l => l.trim())
          .filter(l => l.startsWith('- '))
          .map(l => l.replace(/^-\s*/, ''));
      }
    }
    return [];
  }
</script>

<svelte:head>
  <title>{displayTitle} - Forks</title>
</svelte:head>

{#if cookMode && recipe}
  <CookMode
    title={displayTitle}
    ingredients={cookData.ingredients}
    steps={cookData.steps}
    notes={cookData.notes}
    on:exit={exitCookMode}
  />
{:else if loading}
  <p class="loading">Loading recipe...</p>
{:else if error || !recipe}
  <div class="error">
    <h2>Recipe not found</h2>
    <a href="/">Back to recipes</a>
  </div>
{:else}
  <article class="recipe">
    <a href="/" class="back-link">&larr; All recipes</a>

    {#if recipe.image}
      <img
        src="/api/images/{recipe.image.replace('images/', '')}"
        alt={recipe.title}
        class="hero-image"
      />
    {/if}

    <header class="recipe-header">
      <div class="title-row">
        <h1>{displayTitle}</h1>
        <FavoriteButton slug={recipe.slug} tags={recipe.tags} />
      </div>

      {#if recipe.forks.length > 0}
        <div class="version-selector">
          <button
            class="version-pill"
            class:active={selectedFork === null}
            on:click={() => selectFork(null)}
          >
            Original
          </button>
          {#each recipe.forks as fork}
            <button
              class="version-pill"
              class:active={selectedFork === fork.name}
              class:merged={fork.merged_at != null}
              on:click={() => selectFork(fork.name)}
            >
              {fork.fork_name}
              {#if fork.merged_at}
                <span class="merged-badge">Merged</span>
              {/if}
            </button>
          {/each}
        </div>
        {#if !isDefault}
          <button class="set-default-link" on:click={setAsDefault}>
            Set as my default
          </button>
        {/if}
      {/if}

      <div class="meta">
        {#if recipe.prep_time}
          <span class="meta-item">
            <strong>Prep:</strong> {recipe.prep_time}
          </span>
        {/if}
        {#if recipe.cook_time}
          <span class="meta-item">
            <strong>Cook:</strong> {recipe.cook_time}
          </span>
        {/if}
        {#if recipe.servings}
          <span class="meta-item">
            <strong>Serves:</strong>
            {#if originalServings}
              <ServingScaler
                {originalServings}
                currentServings={currentServings || originalServings}
                on:change={(e) => currentServings = e.detail.servings}
              />
            {:else}
              {recipe.servings}
            {/if}
          </span>
        {/if}
      </div>

      {#if recipe.cook_history && recipe.cook_history.length > 0}
        <CookHistory slug={recipe.slug} cookHistory={recipe.cook_history} />
      {/if}

      {#if recipe.tags.length > 0}
        <div class="tags">
          {#each recipe.tags as tag}
            <a href="/?tags={tag}" class="tag">{tag}</a>
          {/each}
        </div>
      {/if}

      {#if recipe.source}
        <a href={recipe.source} class="source-link" target="_blank" rel="noopener">
          View original source &rarr;
        </a>
      {/if}

      {#if recipe.author}
        <p class="recipe-author">by {recipe.author}</p>
      {/if}

      <div class="recipe-actions">
        <button class="cook-btn" on:click={enterCookMode}>Start Cooking</button>
        {#if onGroceryList}
          <button class="grocery-btn on-list" on:click={() => { if (recipe) removeRecipeFromGrocery(recipe.slug); }}>
            On Grocery List
          </button>
        {:else}
          <button class="grocery-btn" on:click={() => {
            if (recipe) {
              const lines = getIngredientLines(displayContent);
              addRecipeToGrocery(recipe.slug, displayTitle, lines, selectedFork, currentServings ? String(currentServings) : recipe.servings);
            }
          }}>
            Add to Grocery List
          </button>
        {/if}
        {#if selectedFork}
          <a href="/edit/{recipe.slug}?fork={selectedFork}" class="edit-btn">Edit Fork</a>
          <a href={exportForkUrl(recipe.slug, selectedFork)} class="edit-btn" download>Export</a>
          <button class="merge-btn" on:click={handleMergeFork} disabled={merging}>
            {merging ? 'Merging...' : 'Merge into Original'}
          </button>
        {:else}
          <a href="/edit/{recipe.slug}" class="edit-btn">Edit Recipe</a>
        {/if}
        <a href="/fork/{recipe.slug}" class="fork-btn">Fork This Recipe</a>
        <button class="print-btn" on:click={() => window.print()}>Print</button>
        {#if selectedFork}
          <button class="history-btn" on:click={toggleHistory}>
            {historyOpen ? 'Hide History' : 'History'}
          </button>
        {/if}
        <button class="history-btn" on:click={toggleStream}>
          {streamOpen ? 'Hide Stream' : 'Stream'}
        </button>
      </div>

      {#if mergeMessage}
        <p class="merge-message">{mergeMessage}</p>
      {/if}

      {#if historyOpen}
        <div class="history-panel">
          <h3>Fork History</h3>
          {#if historyLoading}
            <p class="history-loading">Loading history...</p>
          {:else if historyEntries.length === 0}
            <p class="history-empty">No history available</p>
          {:else}
            <div class="history-timeline">
              {#each historyEntries as entry}
                <div class="history-entry">
                  <span class="history-date">{new Date(entry.date).toLocaleDateString()}</span>
                  <span class="history-message">{entry.message}</span>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/if}

      {#if streamOpen}
        <div class="stream-panel">
          <h3>Recipe Stream</h3>
          {#if streamLoading}
            <p class="stream-loading">Loading timeline...</p>
          {:else if streamEvents.length === 0}
            <p class="stream-empty">No history available</p>
          {:else}
            <StreamGraph events={streamEvents} onForkClick={handleStreamForkClick} />
          {/if}
        </div>
      {/if}

      {#if selectedFork && forkDetail?.author}
        <p class="fork-author">by {forkDetail.author}</p>
      {/if}
    </header>

    {#if forkLoading}
      <p class="loading">Loading fork...</p>
    {:else}
      <div class="recipe-body">
        {@html renderedBody}
      </div>
    {/if}
  </article>
{/if}

<style>
  .recipe {
    max-width: 720px;
  }

  .back-link {
    display: inline-block;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 1.5rem;
  }

  .back-link:hover {
    color: var(--color-accent);
  }

  .hero-image {
    width: 100%;
    max-height: 400px;
    object-fit: cover;
    border-radius: var(--radius);
    margin-bottom: 1.5rem;
  }

  .recipe-header {
    margin-bottom: 2rem;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .title-row h1 {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 0;
  }

  .version-selector {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-bottom: 0.5rem;
  }

  .version-pill {
    padding: 0.3rem 0.8rem;
    border: 1px solid var(--color-border);
    border-radius: 999px;
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .version-pill.active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .version-pill:hover:not(.active) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .set-default-link {
    background: none;
    border: none;
    color: var(--color-accent);
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0;
    margin-bottom: 0.75rem;
  }

  .set-default-link:hover {
    text-decoration: underline;
  }

  .meta {
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }

  .meta-item {
    font-size: 0.9rem;
    color: var(--color-text-muted);
  }

  .meta-item strong {
    color: var(--color-text);
  }

  .tags {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }

  .tag {
    font-size: 0.8rem;
    padding: 0.25rem 0.65rem;
    border-radius: 4px;
    background: var(--color-tag);
    color: var(--color-text-muted);
    text-decoration: none;
    transition: background 0.15s;
  }

  .tag:hover {
    background: var(--color-accent-light);
    color: var(--color-accent);
    text-decoration: none;
  }

  .source-link {
    font-size: 0.85rem;
    color: var(--color-accent);
  }

  .recipe-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.75rem;
  }

  .cook-btn {
    display: inline-block;
    padding: 0.4rem 1rem;
    background: var(--color-accent);
    color: white;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    font-size: 0.85rem;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .cook-btn:hover {
    opacity: 0.9;
  }

  .edit-btn {
    display: inline-block;
    padding: 0.4rem 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
    color: var(--color-text-muted);
    text-decoration: none;
    transition: all 0.15s;
  }

  .edit-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
    text-decoration: none;
  }

  .grocery-btn {
    display: inline-block;
    padding: 0.4rem 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
    color: var(--color-text-muted);
    background: var(--color-surface);
    cursor: pointer;
    transition: all 0.15s;
  }

  .grocery-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .grocery-btn.on-list {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .fork-btn {
    display: inline-block;
    padding: 0.4rem 1rem;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    font-size: 0.85rem;
    color: var(--color-accent);
    text-decoration: none;
    transition: all 0.15s;
  }

  .fork-btn:hover {
    background: var(--color-accent);
    color: white;
    text-decoration: none;
  }

  .print-btn,
  .history-btn {
    display: inline-block;
    padding: 0.4rem 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
    color: var(--color-text-muted);
    background: var(--color-surface);
    cursor: pointer;
    transition: all 0.15s;
  }

  .print-btn:hover,
  .history-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .history-panel {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
  }

  .history-panel h3 {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
  }

  .history-timeline {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .history-entry {
    display: flex;
    gap: 0.75rem;
    align-items: baseline;
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--color-border);
  }

  .history-entry:last-child {
    border-bottom: none;
  }

  .history-date {
    font-size: 0.8rem;
    color: var(--color-text-muted);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .history-message {
    font-size: 0.85rem;
    color: var(--color-text);
  }

  .history-loading, .history-empty {
    font-size: 0.85rem;
    color: var(--color-text-muted);
  }

  .stream-panel {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
  }

  .stream-panel h3 {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
  }

  .stream-loading, .stream-empty {
    font-size: 0.85rem;
    color: var(--color-text-muted);
  }

  .merge-btn {
    display: inline-block;
    padding: 0.4rem 1rem;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    font-size: 0.85rem;
    color: var(--color-accent);
    background: var(--color-surface);
    cursor: pointer;
    transition: all 0.15s;
  }

  .merge-btn:hover {
    background: var(--color-accent);
    color: white;
  }

  .merge-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .merge-message {
    font-size: 0.85rem;
    color: var(--color-accent);
    margin-top: 0.5rem;
  }

  .version-pill.merged {
    opacity: 0.7;
  }

  .merged-badge {
    font-size: 0.65rem;
    background: var(--color-tag);
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    margin-left: 0.25rem;
  }

  .recipe-author {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    font-style: italic;
    margin-top: 0.25rem;
  }

  .fork-author {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    font-style: italic;
    margin-top: 0.25rem;
  }

  .recipe-body {
    font-size: 1.05rem;
    line-height: 1.75;
  }

  .recipe-body :global(h1) {
    display: none;
  }

  .recipe-body :global(h2) {
    font-size: 1.3rem;
    font-weight: 600;
    margin-top: 2rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--color-border);
  }

  .recipe-body :global(ul) {
    padding-left: 1.25rem;
    margin-bottom: 1rem;
  }

  .recipe-body :global(li) {
    margin-bottom: 0.4rem;
  }

  .recipe-body :global(ol) {
    padding-left: 1.25rem;
    margin-bottom: 1rem;
  }

  .recipe-body :global(ol li) {
    margin-bottom: 0.75rem;
    padding-left: 0.25rem;
  }

  .recipe-body :global(.fork-modified) {
    border-left: 3px solid var(--color-accent);
    padding-left: 1rem;
    margin-left: -1rem;
    border-radius: 0 var(--radius) var(--radius) 0;
  }

  .loading, .error {
    text-align: center;
    padding: 4rem 1rem;
    color: var(--color-text-muted);
  }

  .error h2 {
    margin-bottom: 1rem;
  }

  @media (max-width: 768px) {
    .title-row h1 {
      font-size: 1.5rem;
    }

    .recipe-body {
      font-size: 1.1rem;
      line-height: 1.8;
    }

    .recipe-body :global(li) {
      margin-bottom: 0.6rem;
    }

    .recipe-body :global(ol li) {
      margin-bottom: 1rem;
    }
  }
</style>
