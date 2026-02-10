<script lang="ts">
  import type { RecipeInput } from '$lib/types';

  export let initialData: Partial<RecipeInput> = {};
  export let imagePreviewUrl: string | null = null;
  export let onSave: (data: RecipeInput) => void;
  export let saving = false;

  let title = initialData.title || '';
  let tags = (initialData.tags || []).join(', ');
  let servings = initialData.servings || '';
  let prep_time = initialData.prep_time || '';
  let cook_time = initialData.cook_time || '';
  let source = initialData.source || '';
  let image = initialData.image || '';
  let ingredients = (initialData.ingredients || []).join('\n');
  let instructions = (initialData.instructions || []).join('\n');
  let notes = (initialData.notes || []).join('\n');

  function handleSubmit() {
    const data: RecipeInput = {
      title: title.trim(),
      tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      servings: servings.trim() || null,
      prep_time: prep_time.trim() || null,
      cook_time: cook_time.trim() || null,
      source: source.trim() || null,
      image: image.trim() || imagePreviewUrl || null,
      ingredients: ingredients.split('\n').map(l => l.trim()).filter(Boolean),
      instructions: instructions.split('\n').map(l => l.trim()).filter(Boolean),
      notes: notes.split('\n').map(l => l.trim()).filter(Boolean),
    };
    onSave(data);
  }
</script>

<form class="editor" on:submit|preventDefault={handleSubmit}>
  <div class="field-group">
    <div class="field full">
      <label for="title">Title</label>
      <input id="title" type="text" bind:value={title} required placeholder="Recipe title" />
    </div>

    <div class="field full">
      <label for="tags">Tags</label>
      <input id="tags" type="text" bind:value={tags} placeholder="mexican, beef, tacos" />
    </div>

    <div class="field-row">
      <div class="field">
        <label for="servings">Servings</label>
        <input id="servings" type="text" bind:value={servings} placeholder="4" />
      </div>
      <div class="field">
        <label for="prep_time">Prep Time</label>
        <input id="prep_time" type="text" bind:value={prep_time} placeholder="15min" />
      </div>
      <div class="field">
        <label for="cook_time">Cook Time</label>
        <input id="cook_time" type="text" bind:value={cook_time} placeholder="30min" />
      </div>
    </div>

    <div class="field full">
      <label for="source">Source URL</label>
      <input id="source" type="text" bind:value={source} placeholder="https://..." />
    </div>
  </div>

  {#if imagePreviewUrl}
    <div class="image-preview">
      <img src={imagePreviewUrl} alt="Recipe preview" />
    </div>
  {/if}

  <div class="field full">
    <label for="ingredients">Ingredients <span class="hint">one per line</span></label>
    <textarea id="ingredients" bind:value={ingredients} rows="10" placeholder="1 cup flour&#10;2 eggs&#10;1/2 cup sugar"></textarea>
  </div>

  <div class="field full">
    <label for="instructions">Instructions <span class="hint">one step per line</span></label>
    <textarea id="instructions" bind:value={instructions} rows="10" placeholder="Preheat oven to 350F&#10;Mix dry ingredients&#10;Add wet ingredients"></textarea>
  </div>

  <div class="field full">
    <label for="notes">Notes <span class="hint">optional, one per line</span></label>
    <textarea id="notes" bind:value={notes} rows="4" placeholder="Great for weeknight dinners&#10;Can substitute..."></textarea>
  </div>

  <div class="actions">
    <button type="submit" class="btn-save" disabled={saving || !title.trim()}>
      {saving ? 'Saving...' : 'Save Recipe'}
    </button>
    <a href="/" class="btn-cancel">Cancel</a>
  </div>
</form>

<style>
  .editor {
    max-width: 720px;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .field.full {
    width: 100%;
  }

  .field-row {
    display: flex;
    gap: 1rem;
  }

  .field-row .field {
    flex: 1;
  }

  label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .hint {
    font-weight: 400;
    color: var(--color-text-muted);
  }

  input, textarea {
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

  input:focus, textarea:focus {
    border-color: var(--color-accent);
  }

  textarea {
    resize: vertical;
    line-height: 1.6;
  }

  .image-preview {
    border-radius: var(--radius);
    overflow: hidden;
    max-height: 300px;
  }

  .image-preview img {
    width: 100%;
    max-height: 300px;
    object-fit: cover;
  }

  .actions {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .btn-save {
    padding: 0.6rem 1.5rem;
    background: var(--color-accent);
    color: white;
    border: none;
    border-radius: var(--radius);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.2s;
  }

  .btn-save:hover:not(:disabled) {
    opacity: 0.9;
  }

  .btn-save:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-cancel {
    font-size: 0.9rem;
    color: var(--color-text-muted);
  }

  @media (max-width: 768px) {
    .field-row {
      flex-direction: column;
    }
  }
</style>
