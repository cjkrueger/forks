<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getRecipe, createFork } from '$lib/api';
  import RecipeEditor from '$lib/components/RecipeEditor.svelte';
  import type { Recipe, RecipeInput, ForkInput } from '$lib/types';

  let recipe: Recipe | null = null;
  let loading = true;
  let saving = false;
  let saveError = '';

  let forkName = '';
  let author = '';

  $: slug = $page.params.slug as string;

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
    if (!forkName.trim()) {
      saveError = 'Fork name is required';
      return;
    }
    saving = true;
    saveError = '';
    try {
      const forkData: ForkInput = {
        fork_name: forkName.trim(),
        author: author.trim() || null,
        ...data,
      };
      const result = await createFork(slug, forkData);
      goto(`/recipe/${slug}?fork=${result.name}`);
    } catch (e: any) {
      saveError = e.message || 'Failed to create fork';
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Fork {recipe?.title || 'Recipe'} - Forks</title>
</svelte:head>

{#if loading}
  <p class="loading">Loading recipe...</p>
{:else if !recipe}
  <div class="error">
    <h2>Recipe not found</h2>
    <a href="/">Back to recipes</a>
  </div>
{:else}
  <div class="fork-page">
    <a href="/recipe/{slug}" class="back-link">&larr; Back to recipe</a>
    <h1>Fork: {recipe.title}</h1>
    <p class="subtitle">Create a new version of this recipe with your changes.</p>

    <div class="fork-fields">
      <div class="field">
        <label for="fork-name">Version Name <span class="required">*</span></label>
        <input
          id="fork-name"
          type="text"
          bind:value={forkName}
          placeholder="e.g. Vegan, Gluten Free, Mom's Version"
          required
        />
      </div>
      <div class="field">
        <label for="author">Author <span class="hint">optional</span></label>
        <input
          id="author"
          type="text"
          bind:value={author}
          placeholder="Your name"
        />
      </div>
    </div>

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
  .fork-page {
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

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }

  .subtitle {
    font-size: 0.9rem;
    color: var(--color-text-muted);
    margin-bottom: 1.5rem;
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

  label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .required {
    color: var(--color-danger);
  }

  .hint {
    font-weight: 400;
    color: var(--color-text-muted);
  }

  input {
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

  input:focus {
    border-color: var(--color-accent);
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

  .error h2 {
    margin-bottom: 1rem;
  }
</style>
