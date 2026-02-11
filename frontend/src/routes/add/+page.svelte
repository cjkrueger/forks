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
  let imageFailedUrl: string | null = null;
  let savedSlug: string | null = null;

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
    imageFailedUrl = null;
    try {
      const recipe = await createRecipe(data);
      if (recipe._image_failed) {
        imageFailedUrl = recipe._image_failed;
        savedSlug = recipe.slug;
        saving = false;
      } else {
        goto(`/recipe/${recipe.slug}`);
      }
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
      author: scrapedData.author,
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
          {scraping ? 'Grabbing...' : 'Grab Recipe'}
        </button>
      </form>
      {#if scrapeError}
        <p class="error">{scrapeError}</p>
      {/if}
    </div>

    {#if imageFailedUrl}
      <div class="image-failed-notice">
        <p>
          <strong>Recipe saved!</strong> But the photo couldn't be downloaded automatically — the website blocked it.
        </p>
        <p>
          You can save it manually:
        </p>
        <ol>
          <li><a href={imageFailedUrl} target="_blank" rel="noopener">Open the image</a> and save it to your device</li>
          <li>Go to <a href="/edit/{savedSlug}">edit the recipe</a> and upload it there</li>
        </ol>
        <div class="image-failed-actions">
          <a href="/recipe/{savedSlug}" class="btn btn-primary">View recipe</a>
          <a href="/edit/{savedSlug}" class="btn btn-secondary">Edit &amp; upload image</a>
        </div>
      </div>
    {:else if scrapedData}
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
    max-width: 640px;
    margin: 0 auto;
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
    color: var(--color-danger);
    font-size: 0.9rem;
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .image-failed-notice {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    font-size: 0.9rem;
    line-height: 1.6;
  }

  .image-failed-notice p {
    margin: 0 0 0.75rem;
  }

  .image-failed-notice ol {
    margin: 0 0 1.25rem;
    padding-left: 1.5rem;
  }

  .image-failed-notice li {
    margin-bottom: 0.35rem;
  }

  .image-failed-notice a:not(.btn) {
    color: var(--color-accent);
    text-decoration: underline;
  }

  .image-failed-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .btn {
    display: inline-block;
    padding: 0.5rem 1.25rem;
    border-radius: var(--radius);
    font-size: 0.9rem;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
    border: none;
  }

  .btn-primary {
    background: var(--color-accent);
    color: white;
  }

  .btn-secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  @media (max-width: 768px) {
    .scrape-form {
      flex-direction: column;
    }
  }
</style>
