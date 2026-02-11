<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getRecipe, updateRecipe, deleteRecipe, getFork, updateFork, deleteFork } from '$lib/api';
  import { mergeContent } from '$lib/sections';
  import RecipeEditor from '$lib/components/RecipeEditor.svelte';
  import type { Recipe, RecipeInput, ForkInput, ForkDetail } from '$lib/types';

  let recipe: Recipe | null = null;
  let forkDetail: ForkDetail | null = null;
  let loading = true;
  let saving = false;
  let saveError = '';
  let showDeleteConfirm = false;
  let deleting = false;

  let forkName = '';
  let author = '';
  let recipeVersion: number = 0;
  let forkVersion: number = 0;

  $: slug = $page.params.slug as string;
  $: forkParam = $page.url.searchParams.get('fork');
  $: editingFork = !!forkParam;

  onMount(async () => {
    try {
      recipe = await getRecipe(slug);
      recipeVersion = recipe.version ?? 0;
      if (forkParam && recipe) {
        forkDetail = await getFork(slug, forkParam);
        forkVersion = (forkDetail as any).version ?? 0;
        forkName = forkDetail.fork_name;
        author = forkDetail.author || '';
      }
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

    let content = recipe.content;
    if (forkDetail) {
      content = mergeContent(recipe.content, forkDetail.content);
    }

    const { ingredients, instructions, notes } = parseContent(content);
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
      if (editingFork && forkParam) {
        const forkData: ForkInput = {
          fork_name: forkName.trim(),
          author: author.trim() || null,
          ...data,
          version: forkVersion,
        };
        await updateFork(slug, forkParam, forkData);
        goto(`/recipe/${slug}?fork=${forkParam}`);
      } else {
        await updateRecipe(slug, { ...data, version: recipeVersion });
        goto(`/recipe/${slug}`);
      }
    } catch (e: any) {
      const msg = e.message || 'Failed to save';
      if (msg.includes('modified by another user')) {
        saveError = 'This recipe was updated by someone else. Please reload the page to see the latest version, then re-apply your changes.';
      } else {
        saveError = msg;
      }
      saving = false;
    }
  }

  async function handleDelete() {
    deleting = true;
    try {
      if (editingFork && forkParam) {
        await deleteFork(slug, forkParam);
        goto(`/recipe/${slug}`);
      } else {
        await deleteRecipe(slug);
        goto('/');
      }
    } catch (e) {
      deleting = false;
      showDeleteConfirm = false;
    }
  }

  $: backHref = editingFork ? `/recipe/${slug}?fork=${forkParam}` : `/recipe/${slug}`;
  $: pageTitle = editingFork ? `Edit Fork: ${forkName || forkParam}` : 'Edit Recipe';
  $: deleteLabel = editingFork ? 'Delete Fork' : 'Delete Recipe';
  $: deleteMessage = editingFork
    ? `Are you sure you want to delete the fork "${forkName || forkParam}"? This cannot be undone.`
    : `Are you sure you want to delete "${recipe?.title}"? This cannot be undone.`;
</script>

<svelte:head>
  <title>{pageTitle} - Forks</title>
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
    <a href={backHref} class="back-link">&larr; Back to recipe</a>
    <div class="edit-header">
      <h1>{pageTitle}</h1>
      <button class="delete-btn" on:click={() => showDeleteConfirm = true}>
        {deleteLabel}
      </button>
    </div>

    {#if showDeleteConfirm}
      <div class="delete-confirm">
        <p>{deleteMessage}</p>
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

    {#if editingFork}
      <div class="fork-fields">
        <div class="field">
          <label for="fork-name">Version Name</label>
          <input id="fork-name" type="text" bind:value={forkName} placeholder="Version name" />
        </div>
        <div class="field">
          <label for="author">Author <span class="hint">optional</span></label>
          <input id="author" type="text" bind:value={author} placeholder="Your name" />
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

  .fork-fields {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--color-border);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .field label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .hint {
    font-weight: 400;
    color: var(--color-text-muted);
  }

  .field input {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.9rem;
    font-family: var(--font-body);
    background: var(--color-surface);
    color: var(--color-text);
    outline: none;
    transition: border-color 0.2s;
  }

  .field input:focus {
    border-color: var(--color-accent);
  }

  .delete-btn {
    padding: 0.5rem 1rem;
    background: none;
    border: 1px solid var(--color-danger);
    border-radius: var(--radius);
    color: var(--color-danger);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .delete-btn:hover {
    background: var(--color-danger);
    color: white;
  }

  .delete-confirm {
    background: var(--color-danger-light);
    border: 1px solid var(--color-danger-border);
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
    background: var(--color-danger);
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
    color: var(--color-danger);
    font-size: 0.9rem;
    margin-bottom: 1rem;
  }

  .loading, .error {
    text-align: center;
    padding: 4rem 1rem;
    color: var(--color-text-muted);
  }
</style>
