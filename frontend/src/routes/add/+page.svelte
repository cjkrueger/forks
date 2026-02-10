<script lang="ts">
  import { goto } from '$app/navigation';
  import { scrapeRecipe, createRecipe } from '$lib/api';
  import RecipeEditor from '$lib/components/RecipeEditor.svelte';
  import type { RecipeInput, ScrapeResponse } from '$lib/types';

  let mode: 'url' | 'manual' = 'url';
  let scrapeUrl = '';
  let scraping = false;
  let scrapeError = '';
  let saving = false;
  let saveError = '';
  let scrapedData: ScrapeResponse | null = null;

  async function handleScrape() {
    if (!scrapeUrl.trim()) return;
    scraping = true;
    scrapeError = '';
    scrapedData = null;
    try {
      scrapedData = await scrapeRecipe(scrapeUrl.trim());
    } catch (e: any) {
      scrapeError = e.message || 'Failed to scrape recipe';
    }
    scraping = false;
  }

  async function handleSave(data: RecipeInput) {
    saving = true;
    saveError = '';
    try {
      const recipe = await createRecipe(data);
      goto(`/recipe/${recipe.slug}`);
    } catch (e: any) {
      saveError = e.message || 'Failed to save recipe';
      saving = false;
    }
  }

  function getInitialData(): Partial<RecipeInput> {
    if (!scrapedData) return {};
    return {
      title: scrapedData.title || '',
      tags: scrapedData.tags || [],
      servings: scrapedData.servings,
      prep_time: scrapedData.prep_time,
      cook_time: scrapedData.cook_time,
      source: scrapedData.source || scrapeUrl,
      image: scrapedData.image_url,
      ingredients: scrapedData.ingredients || [],
      instructions: scrapedData.instructions || [],
      notes: scrapedData.notes ? [scrapedData.notes] : [],
    };
  }
</script>

<svelte:head>
  <title>Add Recipe - Forks</title>
</svelte:head>

<div class="add-page">
  <a href="/" class="back-link">&larr; All recipes</a>
  <h1>Add Recipe</h1>

  <div class="mode-toggle">
    <button
      class="mode-btn"
      class:active={mode === 'url'}
      on:click={() => { mode = 'url'; scrapedData = null; }}
    >
      From URL
    </button>
    <button
      class="mode-btn"
      class:active={mode === 'manual'}
      on:click={() => { mode = 'manual'; scrapedData = null; }}
    >
      Manual
    </button>
  </div>

  {#if mode === 'url'}
    <div class="scrape-section">
      <form class="scrape-form" on:submit|preventDefault={handleScrape}>
        <input
          type="url"
          bind:value={scrapeUrl}
          placeholder="https://example.com/recipe..."
          class="scrape-input"
          required
        />
        <button type="submit" class="scrape-btn" disabled={scraping || !scrapeUrl.trim()}>
          {scraping ? 'Scraping...' : 'Scrape'}
        </button>
      </form>
      {#if scrapeError}
        <p class="error">{scrapeError}</p>
      {/if}
    </div>

    {#if scrapedData}
      {#if saveError}
        <p class="error">{saveError}</p>
      {/if}
      <RecipeEditor
        initialData={getInitialData()}
        imagePreviewUrl={scrapedData.image_url}
        onSave={handleSave}
        {saving}
      />
    {/if}
  {:else}
    {#if saveError}
      <p class="error">{saveError}</p>
    {/if}
    <RecipeEditor
      onSave={handleSave}
      {saving}
    />
  {/if}
</div>

<style>
  .add-page {
    max-width: 720px;
  }

  .back-link {
    display: inline-block;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 1rem;
  }

  .back-link:hover {
    color: var(--color-accent);
  }

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 1.5rem;
  }

  .mode-toggle {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .mode-btn {
    padding: 0.5rem 1.25rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .mode-btn.active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .scrape-section {
    margin-bottom: 2rem;
  }

  .scrape-form {
    display: flex;
    gap: 0.5rem;
  }

  .scrape-input {
    flex: 1;
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.9rem;
    background: var(--color-surface);
    color: var(--color-text);
    outline: none;
  }

  .scrape-input:focus {
    border-color: var(--color-accent);
  }

  .scrape-btn {
    padding: 0.5rem 1.25rem;
    background: var(--color-accent);
    color: white;
    border: none;
    border-radius: var(--radius);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }

  .scrape-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error {
    color: #c0392b;
    font-size: 0.9rem;
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
  }

  @media (max-width: 768px) {
    .scrape-form {
      flex-direction: column;
    }
  }
</style>
