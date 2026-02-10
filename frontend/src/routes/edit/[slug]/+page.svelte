<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getRecipe, updateRecipe, deleteRecipe } from '$lib/api';
  import RecipeEditor from '$lib/components/RecipeEditor.svelte';
  import type { Recipe, RecipeInput } from '$lib/types';

  let recipe: Recipe | null = null;
  let loading = true;
  let saving = false;
  let saveError = '';
  let showDeleteConfirm = false;
  let deleting = false;

  $: slug = $page.params.slug;

  onMount(async () => {
    try {
      recipe = await getRecipe(slug);
    } catch (e) {
      // handled by template
    }
    loading = false;
  });

  function parseContent(content: string) {
    const sections: Record<string, string[]> = {};
    let currentSection = '';

    for (const line of content.split('\n')) {
      const headingMatch = line.match(/^##\s+(.+)/);
      if (headingMatch) {
        currentSection = headingMatch[1].trim().toLowerCase();
        sections[currentSection] = [];
        continue;
      }
      if (currentSection && line.trim()) {
        sections[currentSection].push(line.trim());
      }
    }

    const ingredients = (sections['ingredients'] || [])
      .map(l => l.replace(/^-\s*/, ''));

    const instructions = (sections['instructions'] || [])
      .map(l => l.replace(/^\d+\.\s*/, ''));

    const notes = (sections['notes'] || [])
      .map(l => l.replace(/^-\s*/, ''));

    return { ingredients, instructions, notes };
  }

  function getInitialData(): Partial<RecipeInput> {
    if (!recipe) return {};
    const { ingredients, instructions, notes } = parseContent(recipe.content);
    return {
      title: recipe.title,
      tags: recipe.tags,
      servings: recipe.servings,
      prep_time: recipe.prep_time,
      cook_time: recipe.cook_time,
      source: recipe.source,
      image: recipe.image,
      ingredients,
      instructions,
      notes,
    };
  }

  function getImagePreview(): string | null {
    if (!recipe?.image) return null;
    return `/api/images/${recipe.image.replace('images/', '')}`;
  }

  async function handleSave(data: RecipeInput) {
    saving = true;
    saveError = '';
    try {
      await updateRecipe(slug, data);
      goto(`/recipe/${slug}`);
    } catch (e: any) {
      saveError = e.message || 'Failed to update recipe';
      saving = false;
    }
  }

  async function handleDelete() {
    deleting = true;
    try {
      await deleteRecipe(slug);
      goto('/');
    } catch (e) {
      deleting = false;
      showDeleteConfirm = false;
    }
  }
</script>

<svelte:head>
  <title>Edit {recipe?.title || 'Recipe'} - Forks</title>
</svelte:head>

{#if loading}
  <p class="loading">Loading recipe...</p>
{:else if !recipe}
  <div class="error">
    <h2>Recipe not found</h2>
    <a href="/">Back to recipes</a>
  </div>
{:else}
  <div class="edit-page">
    <a href="/recipe/{slug}" class="back-link">&larr; Back to recipe</a>
    <div class="edit-header">
      <h1>Edit Recipe</h1>
      <button class="delete-btn" on:click={() => showDeleteConfirm = true}>
        Delete Recipe
      </button>
    </div>

    {#if showDeleteConfirm}
      <div class="delete-confirm">
        <p>Are you sure you want to delete "{recipe.title}"? This cannot be undone.</p>
        <div class="delete-actions">
          <button class="confirm-delete" on:click={handleDelete} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Yes, delete'}
          </button>
          <button class="cancel-delete" on:click={() => showDeleteConfirm = false}>
            Cancel
          </button>
        </div>
      </div>
    {/if}

    {#if saveError}
      <p class="save-error">{saveError}</p>
    {/if}

    <RecipeEditor
      initialData={getInitialData()}
      imagePreviewUrl={getImagePreview()}
      onSave={handleSave}
      {saving}
    />
  </div>
{/if}

<style>
  .edit-page {
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

  .edit-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .edit-header h1 {
    font-size: 1.75rem;
    font-weight: 700;
  }

  .delete-btn {
    padding: 0.5rem 1rem;
    background: none;
    border: 1px solid #c0392b;
    border-radius: var(--radius);
    color: #c0392b;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .delete-btn:hover {
    background: #c0392b;
    color: white;
  }

  .delete-confirm {
    background: #fdf0f0;
    border: 1px solid #e6c3c3;
    border-radius: var(--radius);
    padding: 1rem;
    margin-bottom: 1.5rem;
  }

  .delete-confirm p {
    margin-bottom: 0.75rem;
    font-size: 0.9rem;
  }

  .delete-actions {
    display: flex;
    gap: 0.5rem;
  }

  .confirm-delete {
    padding: 0.4rem 1rem;
    background: #c0392b;
    color: white;
    border: none;
    border-radius: var(--radius);
    font-size: 0.85rem;
    cursor: pointer;
  }

  .confirm-delete:disabled {
    opacity: 0.5;
  }

  .cancel-delete {
    padding: 0.4rem 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
    cursor: pointer;
  }

  .save-error {
    color: #c0392b;
    font-size: 0.9rem;
    margin-bottom: 1rem;
  }

  .loading, .error {
    text-align: center;
    padding: 4rem 1rem;
    color: var(--color-text-muted);
  }
</style>
