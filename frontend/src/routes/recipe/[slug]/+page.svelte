<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getRecipe, getFork, exportForkUrl, addCookHistory, getForkHistory, mergeFork, unmergeFork, getRecipeStream } from '$lib/api';
  import { renderMarkdown } from '$lib/markdown';
  import { mergeContent, getModifiedSections, parseSections } from '$lib/sections';
  import { parseIngredient, formatIngredient, formatQuantity } from '$lib/ingredients';
  import { computeSectionDiffs } from '$lib/diff';
  import type { SectionDiff, LineDiff } from '$lib/diff';
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

  $: sectionDiffs = recipe && forkDetail
    ? computeSectionDiffs(recipe.content, forkDetail.content)
    : new Map<string, SectionDiff>();

  function escapeHtml(text: string): string {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderIngredientsWithDiff(diff: SectionDiff, scale: number): string {
    let html = '<h2>Ingredients</h2>\n<ul>\n';
    for (const line of diff.lines) {
      if (line.status === 'removed') {
        const text = line.baseLine!.replace(/^-\s*/, '');
        html += `<li class="diff-removed"><del>${escapeHtml(text)}</del></li>\n`;
      } else if (line.status === 'added') {
        const parsed = parseIngredient(line.forkLine!);
        const text = scale !== 1 ? formatIngredient(parsed, scale) : line.forkLine!.replace(/^-\s*/, '');
        html += `<li class="diff-added">${escapeHtml(text)}</li>\n`;
      } else if (line.status === 'modified') {
        const parsed = parseIngredient(line.forkLine!);
        const text = scale !== 1 ? formatIngredient(parsed, scale) : line.forkLine!.replace(/^-\s*/, '');
        const annotation = line.annotation ? ` <span class="diff-annotation">(${escapeHtml(line.annotation)})</span>` : '';
        html += `<li class="diff-modified">${escapeHtml(text)}${annotation}</li>\n`;
      } else {
        const parsed = parseIngredient(line.forkLine!);
        const text = scale !== 1 ? formatIngredient(parsed, scale) : line.forkLine!.replace(/^-\s*/, '');
        html += `<li>${escapeHtml(text)}</li>\n`;
      }
    }
    html += '</ul>\n';
    return html;
  }

  function renderInstructionsWithDiff(diff: SectionDiff): string {
    let html = '<h2>Instructions</h2>\n<ol>\n';
    let stepNum = 0;
    for (const line of diff.lines) {
      const text = (line.forkLine || line.baseLine || '').replace(/^\d+\.\s*/, '');
      if (line.status === 'removed') {
        html += `<li class="diff-removed diff-unnumbered"><del>${escapeHtml(text)}</del></li>\n`;
      } else {
        stepNum++;
        const cls = line.status === 'added' ? ' class="diff-added"' : line.status === 'modified' ? ' class="diff-modified"' : '';
        html += `<li value="${stepNum}"${cls}>${escapeHtml(text)}</li>\n`;
      }
    }
    html += '</ol>\n';
    return html;
  }

  function renderNotesWithDiff(diff: SectionDiff): string {
    let html = '<h2>Notes</h2>\n<ul>\n';
    for (const line of diff.lines) {
      const text = (line.forkLine || line.baseLine || '').replace(/^-\s*/, '');
      if (line.status === 'removed') {
        html += `<li class="diff-removed"><del>${escapeHtml(text)}</del></li>\n`;
      } else if (line.status === 'added') {
        html += `<li class="diff-added">${escapeHtml(text)}</li>\n`;
      } else if (line.status === 'modified') {
        html += `<li class="diff-modified">${escapeHtml(text)}</li>\n`;
      } else {
        html += `<li>${escapeHtml(text)}</li>\n`;
      }
    }
    html += '</ul>\n';
    return html;
  }

  // Split rendering for two-column layout: ingredients in sidebar, rest in main
  function renderFiltered(content: string, modified: Set<string>, scale: number, include: string[] | null, diffs: Map<string, SectionDiff>): string {
    const sections = parseSections(content);
    let html = '';
    for (const section of sections) {
      const name = section.name.toLowerCase();
      if (section.name === '_preamble') continue;
      if (include !== null) {
        if (!include.includes(name)) continue;
      } else {
        if (name === 'ingredients') continue;
      }

      // Use diff rendering if available for this section
      const diff = diffs.get(section.name);
      if (diff && diff.hasChanges) {
        if (name === 'ingredients') {
          html += renderIngredientsWithDiff(diff, scale);
        } else if (name === 'instructions') {
          html += renderInstructionsWithDiff(diff);
        } else if (name === 'notes') {
          html += renderNotesWithDiff(diff);
        } else {
          // Generic section: use positional diff with unordered list
          let sectionHtml = `<h2>${escapeHtml(section.name)}</h2>\n<ul>\n`;
          for (const line of diff.lines) {
            const text = (line.forkLine || line.baseLine || '').replace(/^-\s*/, '').replace(/^\d+\.\s*/, '');
            if (line.status === 'removed') {
              sectionHtml += `<li class="diff-removed"><del>${escapeHtml(text)}</del></li>\n`;
            } else if (line.status === 'added') {
              sectionHtml += `<li class="diff-added">${escapeHtml(text)}</li>\n`;
            } else if (line.status === 'modified') {
              sectionHtml += `<li class="diff-modified">${escapeHtml(text)}</li>\n`;
            } else {
              sectionHtml += `<li>${escapeHtml(text)}</li>\n`;
            }
          }
          sectionHtml += '</ul>\n';
          html += sectionHtml;
        }
        continue;
      }

      let sectionContent = section.content;
      if (name === 'ingredients' && scale !== 1) {
        sectionContent = sectionContent.split('\n').map(line => {
          if (line.trim().startsWith('- ')) {
            const parsed = parseIngredient(line.trim());
            return `- ${formatIngredient(parsed, scale)}`;
          }
          return line;
        }).join('\n');
      }
      const sectionMd = `## ${section.name}\n\n${sectionContent}`;
      html += renderMarkdown(sectionMd);
    }
    return html;
  }

  $: ingredientsHtml = renderFiltered(displayContent, modifiedSections, scaleFactor, ['ingredients'], sectionDiffs);
  $: mainBodyHtml = renderFiltered(displayContent, modifiedSections, scaleFactor, null, sectionDiffs);

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
  function parseCookData(content: string, scale: number) {
    const sections = parseSections(content);
    let ingredients: string[] = [];
    let steps: string[] = [];
    let notes: string[] = [];

    for (const section of sections) {
      if (section.name.toLowerCase() === 'ingredients') {
        ingredients = section.content.split('\n')
          .map(l => l.trim())
          .filter(l => l.startsWith('- '))
          .map(l => {
            if (scale !== 1) {
              const parsed = parseIngredient(l);
              return formatIngredient(parsed, scale);
            }
            return l.replace(/^-\s*/, '');
          });
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

  $: cookData = parseCookData(displayContent, scaleFactor);

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

  $: selectedForkMerged = recipe?.forks.find(f => f.name === selectedFork)?.merged_at ?? null;

  async function handleUnmergeFork() {
    if (!recipe || !selectedFork) return;
    if (!confirm(`Undo merge of "${forkDetail?.fork_name}" and restore the original recipe?`)) return;
    merging = true;
    mergeMessage = '';
    try {
      await unmergeFork(recipe.slug, selectedFork);
      recipe = await getRecipe(slug);
      if (selectedFork) await selectFork(selectedFork);
      mergeMessage = 'Fork unmerged — original restored';
    } catch (e: any) {
      mergeMessage = e.message || 'Unmerge failed';
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

  function exportOriginal() {
    if (!recipe) return;
    const blob = new Blob([displayContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${recipe.slug}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function getIngredientLines(content: string, scale: number): string[] {
    const sections = parseSections(content);
    for (const section of sections) {
      if (section.name.toLowerCase() === 'ingredients') {
        return section.content.split('\n')
          .map(l => l.trim())
          .filter(l => l.startsWith('- '))
          .map(l => {
            if (scale !== 1) {
              const parsed = parseIngredient(l);
              return formatIngredient(parsed, scale);
            }
            return l.replace(/^-\s*/, '');
          });
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
      <div class="hero-banner">
        <img
          src="/api/images/{recipe.image.replace('images/', '')}"
          alt={recipe.title}
          class="hero-image"
        />
        <div class="hero-overlay">
          <div class="hero-content">
            <h1 class="hero-title">{displayTitle}</h1>
            {#if recipe.author}
              <p class="hero-author">by {recipe.author}</p>
            {/if}
            <div class="hero-meta">
              {#if recipe.prep_time}<span>Prep: {recipe.prep_time}</span>{/if}
              {#if recipe.cook_time}<span>Cook: {recipe.cook_time}</span>{/if}
              {#if recipe.servings}<span>Serves: {currentServings ?? recipe.servings}</span>{/if}
            </div>
          </div>
        </div>
      </div>
    {:else}
      <h1 class="no-hero-title">{displayTitle}</h1>
      {#if recipe.author}
        <p class="recipe-author">by {recipe.author}</p>
      {/if}
    {/if}

    <div class="print-header">
      <h1 class="print-title">{displayTitle}</h1>
      <p class="print-meta">
        {#if recipe.prep_time}Prep: {recipe.prep_time}{/if}
        {#if recipe.cook_time}{#if recipe.prep_time} &middot; {/if}Cook: {recipe.cook_time}{/if}
        {#if recipe.servings}{#if recipe.prep_time || recipe.cook_time} &middot; {/if}Serves: {currentServings ?? recipe.servings}{/if}
      </p>
    </div>

    <div class="action-bar">
      {#if recipe.forks.length > 0}
        <div class="version-row">
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
        </div>
        {#if selectedFork}
          <div class="fork-actions">
            {#if selectedForkMerged}
              <button class="merge-btn unmerge" on:click={handleUnmergeFork} disabled={merging}>
                {merging ? 'Unmerging...' : 'Unmerge'}
              </button>
            {:else}
              <button class="merge-btn" on:click={handleMergeFork} disabled={merging}>
                {merging ? 'Merging...' : 'Merge into Original'}
              </button>
            {/if}
          </div>
        {/if}
      {/if}

      <div class="recipe-actions">
        <button class="cook-btn" on:click={enterCookMode}>Start Cooking</button>
        {#if selectedFork}
          <a href="/edit/{recipe.slug}?fork={selectedFork}" class="edit-btn">Edit Fork</a>
        {:else}
          <a href="/edit/{recipe.slug}" class="edit-btn">Edit Recipe</a>
        {/if}
        <a href="/fork/{recipe.slug}" class="fork-btn">Fork This Recipe</a>
        <div class="action-icons">
          {#if onGroceryList}
            <button class="grocery-icon-btn on-list" on:click={() => { if (recipe) removeRecipeFromGrocery(recipe.slug); }} aria-label="Remove from grocery list">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
              </svg>
            </button>
          {:else}
            <button class="grocery-icon-btn" on:click={() => {
              if (recipe) {
                const lines = getIngredientLines(displayContent, scaleFactor);
                addRecipeToGrocery(recipe.slug, displayTitle, lines, selectedFork, currentServings ? String(currentServings) : recipe.servings);
              }
            }} aria-label="Add to grocery list">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>
              </svg>
            </button>
          {/if}
          <button class="print-btn" on:click={() => window.print()} aria-label="Print recipe">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 6 2 18 2 18 9" />
              <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
              <rect x="6" y="14" width="12" height="8" />
            </svg>
          </button>
          {#if selectedFork}
            <button class="history-btn" class:active={historyOpen} on:click={toggleHistory} aria-label="Fork history">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </button>
          {/if}
          <button class="stream-btn" class:active={streamOpen} on:click={toggleStream} aria-label="Recipe stream">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="6" y1="3" x2="6" y2="15" />
              <circle cx="18" cy="6" r="3" />
              <circle cx="6" cy="18" r="3" />
              <path d="M18 9a9 9 0 0 1-9 9" />
            </svg>
          </button>
          <FavoriteButton slug={recipe.slug} tags={recipe.tags} />
        </div>
      </div>
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

    {#if forkLoading}
      <p class="loading">Loading fork...</p>
    {:else}
      <div class="recipe-layout">
        <aside class="recipe-sidebar">
          <div class="sidebar-meta">
            {#if recipe.prep_time}
              <div class="meta-block">
                <span class="meta-label">Prep</span>
                <span class="meta-value">{recipe.prep_time}</span>
              </div>
            {/if}
            {#if recipe.cook_time}
              <div class="meta-block">
                <span class="meta-label">Cook</span>
                <span class="meta-value">{recipe.cook_time}</span>
              </div>
            {/if}
            {#if recipe.servings}
              <div class="meta-block">
                <span class="meta-label">Serves</span>
                <span class="meta-value">
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
              </div>
            {/if}
          </div>

          <div class="recipe-body sidebar-ingredients">
            {@html ingredientsHtml}
          </div>

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

          {#if selectedFork && forkDetail?.author}
            <p class="fork-author">by {forkDetail.author}</p>
          {/if}

          {#if recipe.cook_history && recipe.cook_history.length > 0}
            <CookHistory slug={recipe.slug} cookHistory={recipe.cook_history} />
          {/if}

          {#if selectedFork}
            <a href={exportForkUrl(recipe.slug, selectedFork)} class="export-btn" download>
              Export Recipe
            </a>
          {:else}
            <button class="export-btn" on:click={exportOriginal}>
              Export Recipe
            </button>
          {/if}
        </aside>

        <div class="recipe-main">
          <div class="recipe-body">
            {@html mainBodyHtml}
          </div>
        </div>
      </div>
    {/if}
  </article>
{/if}

<style>
  .recipe {
    max-width: none;
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

  /* Hero Banner */
  .hero-banner {
    position: relative;
    width: 100%;
    height: 50vh;
    max-height: 500px;
    overflow: hidden;
    border-radius: var(--radius-lg);
  }

  .hero-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: var(--radius-lg);
  }

  .hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 60%);
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding: 2rem;
  }

  .hero-content {
    flex: 1;
    min-width: 0;
  }

  .hero-title {
    color: white;
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 0.5rem;
    text-shadow: 0 1px 4px rgba(0,0,0,0.3);
  }

  .hero-author {
    color: rgba(255,255,255,0.8);
    font-size: 0.95rem;
    margin-bottom: 0.5rem;
    text-shadow: 0 1px 4px rgba(0,0,0,0.3);
  }

  .hero-meta {
    display: flex;
    gap: 1rem;
    color: rgba(255,255,255,0.85);
    font-size: 0.9rem;
  }

  .no-hero-title {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 0.75rem;
  }

  /* Sticky Action Bar */
  .action-bar {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    padding: 0.75rem 0;
    margin-bottom: 1rem;
  }

  /* Two-column layout */
  .recipe-layout {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 2.5rem;
    align-items: start;
    margin-top: 1rem;
  }

  .recipe-sidebar {
    position: static;
  }

  .sidebar-meta {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
    gap: 0.5rem;
    padding: 0.75rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    margin-bottom: 1rem;
  }

  .meta-block {
    text-align: center;
    padding: 0.25rem;
  }

  .meta-label {
    display: block;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-muted);
    margin-bottom: 0.15rem;
  }

  .meta-value {
    display: block;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .sidebar-ingredients {
    padding: 1rem 1.25rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    margin-bottom: 1rem;
  }

  .sidebar-ingredients:global(.recipe-body) :global(h2) {
    margin-top: 0;
    font-size: 1.1rem;
  }

  .export-btn {
    display: block;
    width: 100%;
    padding: 0.5rem;
    margin-top: 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.85rem;
    font-family: var(--font-body);
    text-align: center;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.15s;
  }

  .export-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
    text-decoration: none;
  }

  .recipe-main {
    min-width: 0;
  }

  .recipe-main :global(h2:first-child) {
    margin-top: 0;
  }

  .version-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 0.5rem;
  }

  .version-selector {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
  }

  .fork-actions {
    display: flex;
    gap: 0.4rem;
    align-items: center;
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
  }

  .set-default-link:hover {
    text-decoration: underline;
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
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .action-icons {
    display: flex;
    gap: 0.35rem;
    align-items: center;
    margin-left: auto;
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

  .grocery-icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    padding: 0;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    color: var(--color-text-muted);
    background: var(--color-surface);
    cursor: pointer;
    transition: all 0.15s;
  }

  .grocery-icon-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .grocery-icon-btn.on-list {
    border-color: var(--color-accent);
    color: var(--color-accent);
    background: var(--color-accent-light);
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

  .print-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    padding: 0;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    color: var(--color-text-muted);
    background: var(--color-surface);
    cursor: pointer;
    transition: all 0.15s;
  }

  .print-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .stream-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    padding: 0;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    color: var(--color-text-muted);
    background: var(--color-surface);
    cursor: pointer;
    transition: all 0.15s;
  }

  .stream-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .stream-btn.active {
    border-color: var(--color-accent);
    color: var(--color-accent);
    background: var(--color-accent-light);
  }

  .history-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    padding: 0;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    color: var(--color-text-muted);
    background: var(--color-surface);
    cursor: pointer;
    transition: all 0.15s;
  }

  .history-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .history-btn.active {
    border-color: var(--color-accent);
    color: var(--color-accent);
    background: var(--color-accent-light);
  }

  .print-header {
    display: none;
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

  .merge-btn.unmerge {
    border-color: var(--color-danger, #c0392b);
    color: var(--color-danger, #c0392b);
  }

  .merge-btn.unmerge:hover {
    background: var(--color-danger, #c0392b);
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
    font-size: 1rem;
    color: var(--color-text-muted);
    margin-bottom: 0.75rem;
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

  .recipe-body :global(.diff-added) {
    background: var(--color-success-light);
    border-left: 3px solid var(--color-success);
    padding-left: 0.5rem;
  }

  .recipe-body :global(.diff-removed) {
    background: var(--color-danger-light);
    border-left: 3px solid var(--color-danger);
    padding-left: 0.5rem;
    color: var(--color-text-muted);
  }

  .recipe-body :global(.diff-modified) {
    background: var(--color-accent-light);
    border-left: 3px solid var(--color-accent);
    padding-left: 0.5rem;
  }

  .recipe-body :global(.diff-unnumbered) {
    list-style: none;
  }

  .recipe-body :global(.diff-annotation) {
    font-style: italic;
    font-size: 0.85em;
    color: var(--color-text-muted);
    margin-left: 0.25rem;
  }

  .loading, .error {
    text-align: center;
    padding: 4rem 1rem;
    color: var(--color-text-muted);
  }

  .error h2 {
    margin-bottom: 1rem;
  }

  @media (max-width: 900px) {
    .recipe-layout {
      grid-template-columns: 1fr;
    }

    .recipe-sidebar {
      position: static;
      max-height: none;
      overflow-y: visible;
    }

    .sidebar-ingredients {
      margin-bottom: 1rem;
    }
  }

  @media (max-width: 768px) {
    .hero-banner {
      height: 35vh;
    }

    .hero-title {
      font-size: 1.5rem;
    }

    .hero-overlay {
      padding: 1rem;
    }

    .no-hero-title {
      font-size: 1.5rem;
    }

    .recipe-actions {
      flex-wrap: wrap;
    }

    .recipe-actions :global(button),
    .recipe-actions :global(a) {
      font-size: 0.8rem;
      padding: 0.35rem 0.75rem;
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
