<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getRecipe, getFork, exportForkUrl } from '$lib/api';
  import { renderMarkdown } from '$lib/markdown';
  import { mergeContent, getModifiedSections, parseSections } from '$lib/sections';
  import type { Recipe, ForkDetail } from '$lib/types';

  let recipe: Recipe | null = null;
  let loading = true;
  let error = false;

  // Fork state
  let selectedFork: string | null = null;
  let forkDetail: ForkDetail | null = null;
  let forkLoading = false;
  let modifiedSections: Set<string> = new Set();

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
    } catch (e) {
      error = true;
    }
    loading = false;
  });

  async function selectFork(forkName: string | null) {
    selectedFork = forkName;
    forkDetail = null;
    modifiedSections = new Set();
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

  function renderWithHighlights(content: string, modified: Set<string>): string {
    if (modified.size === 0) return renderMarkdown(content);

    const sections = parseSections(content);
    let html = '';
    for (const section of sections) {
      if (section.name === '_preamble') {
        html += renderMarkdown(section.content);
      } else {
        const isModified = modified.has(section.name);
        const sectionMd = `## ${section.name}\n\n${section.content}`;
        if (isModified) {
          html += `<div class="fork-modified">${renderMarkdown(sectionMd)}</div>`;
        } else {
          html += renderMarkdown(sectionMd);
        }
      }
    }
    return html;
  }

  $: renderedBody = renderWithHighlights(displayContent, modifiedSections);

  let isDefault = true;
  $: {
    const stored = localStorage.getItem(`forks-default-${slug}`);
    if (selectedFork) {
      isDefault = stored === selectedFork;
    } else {
      isDefault = !stored;
    }
  }
</script>

<svelte:head>
  <title>{displayTitle} - Forks</title>
</svelte:head>

{#if loading}
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
      <h1>{displayTitle}</h1>

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
              on:click={() => selectFork(fork.name)}
            >
              {fork.fork_name}
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
            <strong>Serves:</strong> {recipe.servings}
          </span>
        {/if}
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

      <div class="recipe-actions">
        {#if selectedFork}
          <a href="/edit/{recipe.slug}?fork={selectedFork}" class="edit-btn">Edit Fork</a>
          <a href={exportForkUrl(recipe.slug, selectedFork)} class="edit-btn" download>Export</a>
        {:else}
          <a href="/edit/{recipe.slug}" class="edit-btn">Edit Recipe</a>
        {/if}
        <a href="/fork/{recipe.slug}" class="fork-btn">Fork This Recipe</a>
      </div>

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

  .recipe-header h1 {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 0.75rem;
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
    .recipe-header h1 {
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
