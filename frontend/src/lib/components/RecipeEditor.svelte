<script lang="ts">
  import type { RecipeInput } from '$lib/types';
  import { uploadImage } from '$lib/api';

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
  let author = initialData.author || '';
  let image = initialData.image || '';
  let ingredients = (initialData.ingredients || []).join('\n');
  let instructions = (initialData.instructions || []).join('\n');
  let notes = (initialData.notes || []).join('\n');

  let imageMode: 'current' | 'url' | 'upload' = 'current';
  let imageUrl = '';
  let uploading = false;
  let uploadError = '';
  let fileInput: HTMLInputElement;

  // Ingredient amount validation
  let flaggedIngredients: string[] = [];
  let showAmountWarning = false;

  // Reset warning when ingredients change
  $: if (ingredients) {
    showAmountWarning = false;
    flaggedIngredients = [];
  }

  function getFlaggedIngredients(text: string): string[] {
    return text
      .split('\n')
      .map(l => l.trim())
      .filter(Boolean)
      .filter(line => !/^[\d\u00BC-\u00BE\u2150-\u215E]/.test(line));
  }

  $: previewSrc = (() => {
    if (imageMode === 'current' && imagePreviewUrl && image) return imagePreviewUrl;
    if (imageMode === 'url' && imageUrl.trim()) return imageUrl.trim();
    return null;
  })();

  function removeImage() {
    image = '';
    imagePreviewUrl = null;
    imageUrl = '';
    imageMode = 'current';
  }

  function showUrlInput() {
    imageMode = 'url';
    imageUrl = '';
  }

  function applyUrl() {
    if (imageUrl.trim()) {
      image = imageUrl.trim();
      imageMode = 'current';
      imagePreviewUrl = imageUrl.trim();
      imageUrl = '';
    }
  }

  function triggerUpload() {
    fileInput.click();
  }

  async function handleFileSelect(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    uploading = true;
    uploadError = '';
    try {
      const result = await uploadImage(file);
      image = result.path;
      imagePreviewUrl = `/api/images/${result.path.replace('images/', '')}`;
      imageMode = 'current';
    } catch (err: any) {
      uploadError = err.message || 'Upload failed';
    }
    uploading = false;
    input.value = '';
  }

  function cancelUrlInput() {
    imageMode = 'current';
    imageUrl = '';
  }

  function handleSubmit() {
    // Check for ingredients without amounts
    const flagged = getFlaggedIngredients(ingredients);
    if (flagged.length > 0 && !showAmountWarning) {
      flaggedIngredients = flagged;
      showAmountWarning = true;
      return;
    }

    const data: RecipeInput = {
      title: title.trim(),
      tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      servings: servings.trim() || null,
      prep_time: prep_time.trim() || null,
      cook_time: cook_time.trim() || null,
      source: source.trim() || null,
      author: author.trim() || null,
      image: image.trim() || null,
      ingredients: ingredients.split('\n').map(l => l.trim()).filter(Boolean),
      instructions: instructions.split('\n').map(l => l.trim()).filter(Boolean),
      notes: notes.split('\n').map(l => l.trim()).filter(Boolean),
    };
    showAmountWarning = false;
    onSave(data);
  }

  function dismissWarning() {
    showAmountWarning = false;
    flaggedIngredients = [];
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

    <div class="field full">
      <label for="author">Author</label>
      <input id="author" type="text" bind:value={author} placeholder="Recipe author" />
    </div>
  </div>

  <div class="image-section">
    <label class="image-label">Photo</label>
    {#if previewSrc}
      <div class="image-preview">
        <img src={previewSrc} alt="Recipe preview" />
        <div class="image-overlay">
          <button type="button" class="img-action-btn" on:click={showUrlInput}>Change URL</button>
          <button type="button" class="img-action-btn" on:click={triggerUpload}>
            {uploading ? 'Uploading...' : 'Upload new'}
          </button>
          <button type="button" class="img-action-btn danger" on:click={removeImage}>Remove</button>
        </div>
      </div>
    {:else if imageMode === 'url'}
      <div class="image-url-input">
        <input
          type="url"
          bind:value={imageUrl}
          placeholder="https://example.com/photo.jpg"
          class="url-input"
        />
        <button type="button" class="img-btn" on:click={applyUrl} disabled={!imageUrl.trim()}>Set</button>
        <button type="button" class="img-btn secondary" on:click={cancelUrlInput}>Cancel</button>
      </div>
    {:else}
      <div class="image-empty">
        <button type="button" class="img-btn" on:click={triggerUpload} disabled={uploading}>
          {uploading ? 'Uploading...' : 'Upload photo'}
        </button>
        <button type="button" class="img-btn secondary" on:click={showUrlInput}>Paste URL</button>
      </div>
    {/if}
    {#if uploadError}
      <p class="upload-error">{uploadError}</p>
    {/if}
    <input
      type="file"
      accept="image/*"
      bind:this={fileInput}
      on:change={handleFileSelect}
      class="file-input"
    />
  </div>

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

  {#if showAmountWarning}
    <div class="amount-warning">
      <p class="amount-warning-title">Some ingredients may be missing amounts:</p>
      <ul class="amount-warning-list">
        {#each flaggedIngredients as line}
          <li>{line}</li>
        {/each}
      </ul>
      <div class="amount-warning-actions">
        <button type="button" class="img-btn secondary" on:click={dismissWarning}>Go back and fix</button>
        <button type="submit" class="img-btn">Save anyway</button>
      </div>
    </div>
  {/if}

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

  .image-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .image-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .image-preview {
    position: relative;
    border-radius: var(--radius);
    overflow: hidden;
    max-height: 300px;
  }

  .image-preview img {
    width: 100%;
    max-height: 300px;
    object-fit: cover;
    display: block;
  }

  .image-overlay {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    gap: 0.5rem;
    padding: 0.75rem;
    background: linear-gradient(transparent, rgba(0, 0, 0, 0.6));
    opacity: 0;
    transition: opacity 0.2s;
  }

  .image-preview:hover .image-overlay {
    opacity: 1;
  }

  .img-action-btn {
    padding: 0.35rem 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.4);
    border-radius: var(--radius);
    background: rgba(0, 0, 0, 0.3);
    color: white;
    font-size: 0.8rem;
    cursor: pointer;
    transition: background 0.15s;
    backdrop-filter: blur(4px);
  }

  .img-action-btn:hover {
    background: rgba(0, 0, 0, 0.5);
  }

  .img-action-btn.danger:hover {
    background: rgba(220, 38, 38, 0.7);
  }

  .image-url-input {
    display: flex;
    gap: 0.5rem;
  }

  .url-input {
    flex: 1;
  }

  .image-empty {
    display: flex;
    gap: 0.5rem;
    padding: 1.5rem;
    border: 1px dashed var(--color-border);
    border-radius: var(--radius);
    justify-content: center;
  }

  .img-btn {
    padding: 0.4rem 0.85rem;
    border: none;
    border-radius: var(--radius);
    background: var(--color-accent);
    color: white;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .img-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .img-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .img-btn.secondary {
    background: var(--color-surface);
    color: var(--color-text-muted);
    border: 1px solid var(--color-border);
  }

  .img-btn.secondary:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .upload-error {
    font-size: 0.85rem;
    color: var(--color-danger);
  }

  .file-input {
    display: none;
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

  .amount-warning {
    padding: 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
  }

  .amount-warning-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-text);
    margin-bottom: 0.5rem;
  }

  .amount-warning-list {
    margin: 0 0 0.75rem 1.25rem;
    padding: 0;
    font-size: 0.85rem;
    color: var(--color-text-muted);
  }

  .amount-warning-list li {
    margin-bottom: 0.25rem;
  }

  .amount-warning-actions {
    display: flex;
    gap: 0.5rem;
  }

  @media (max-width: 768px) {
    .field-row {
      flex-direction: column;
    }
  }
</style>
