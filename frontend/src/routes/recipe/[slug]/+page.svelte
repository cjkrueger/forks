<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getRecipe } from '$lib/api';
  import { renderMarkdown } from '$lib/markdown';
  import type { Recipe } from '$lib/types';

  let recipe: Recipe | null = null;
  let loading = true;
  let error = false;

  $: slug = $page.params.slug;

  onMount(async () => {
    try {
      recipe = await getRecipe(slug);
    } catch (e) {
      error = true;
    }
    loading = false;
  });
</script>

<svelte:head>
  <title>{recipe ? recipe.title : 'Recipe'} - Forks</title>
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
      <h1>{recipe.title}</h1>

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
    </header>

    <div class="recipe-body">
      {@html renderMarkdown(recipe.content)}
    </div>
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
