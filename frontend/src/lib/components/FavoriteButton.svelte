<script lang="ts">
  import { addFavorite, removeFavorite } from '$lib/api';

  export let slug: string;
  export let tags: string[];

  let favorited = tags.includes('favorite');
  let toggling = false;

  async function toggle() {
    if (toggling) return;
    toggling = true;
    const prev = favorited;
    favorited = !favorited;
    try {
      if (favorited) {
        await addFavorite(slug);
      } else {
        await removeFavorite(slug);
      }
    } catch (e) {
      favorited = prev;
    }
    toggling = false;
  }
</script>

<button
  class="favorite-btn"
  class:active={favorited}
  on:click={toggle}
  aria-label={favorited ? 'Remove from favorites' : 'Add to favorites'}
>
  <svg width="20" height="20" viewBox="0 0 24 24" fill={favorited ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
</button>

<style>
  .favorite-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text-muted);
    padding: 0.25rem;
    transition: color 0.15s;
    display: flex;
    align-items: center;
  }

  .favorite-btn:hover,
  .favorite-btn.active {
    color: var(--color-danger);
  }
</style>
