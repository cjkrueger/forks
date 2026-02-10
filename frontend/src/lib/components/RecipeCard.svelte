<script lang="ts">
  import type { RecipeSummary } from '$lib/types';

  export let recipe: RecipeSummary;
</script>

<a href="/recipe/{recipe.slug}" class="card">
  <div class="card-image">
    {#if recipe.image}
      <img src="/api/images/{recipe.image.replace('images/', '')}" alt={recipe.title} />
    {:else}
      <div class="placeholder">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/>
        </svg>
      </div>
    {/if}
  </div>
  <div class="card-body">
    <h3 class="card-title">{recipe.title}</h3>
    <div class="card-meta">
      {#if recipe.prep_time}
        <span class="meta-item">Prep: {recipe.prep_time}</span>
      {/if}
      {#if recipe.cook_time}
        <span class="meta-item">Cook: {recipe.cook_time}</span>
      {/if}
      {#if recipe.servings}
        <span class="meta-item">Serves: {recipe.servings}</span>
      {/if}
    </div>
    {#if recipe.tags.length > 0}
      <div class="card-tags">
        {#each recipe.tags.slice(0, 4) as tag}
          <span class="tag">{tag}</span>
        {/each}
        {#if recipe.forks && recipe.forks.length > 0}
          <span class="tag fork-count">{recipe.forks.length} {recipe.forks.length === 1 ? 'fork' : 'forks'}</span>
        {/if}
      </div>
    {:else if recipe.forks && recipe.forks.length > 0}
      <div class="card-tags">
        <span class="tag fork-count">{recipe.forks.length} {recipe.forks.length === 1 ? 'fork' : 'forks'}</span>
      </div>
    {/if}
  </div>
</a>

<style>
  .card {
    display: flex;
    flex-direction: column;
    background: var(--color-surface);
    border-radius: var(--radius-lg, var(--radius));
    border: 1px solid var(--color-border);
    overflow: hidden;
    text-decoration: none;
    color: var(--color-text);
    transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
  }

  .card:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
    border-color: transparent;
    text-decoration: none;
  }

  .card-image {
    aspect-ratio: 16 / 10;
    overflow: hidden;
    background: var(--color-tag);
  }

  .card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s ease;
  }

  .card:hover .card-image img {
    transform: scale(1.03);
  }

  .placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-muted);
  }

  .card-body {
    padding: 1rem 1.125rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .card-title {
    font-size: 1.05rem;
    font-weight: 600;
    line-height: 1.3;
  }

  .card-meta {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .meta-item {
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .card-tags {
    display: flex;
    gap: 0.375rem;
    flex-wrap: wrap;
  }

  .tag {
    font-size: 0.7rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    background: var(--color-tag);
    color: var(--color-text-muted);
  }

  .fork-count {
    background: var(--color-accent-light);
    color: var(--color-accent);
  }
</style>
