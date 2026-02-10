<script lang="ts">
  import { likeRecipe } from '$lib/api';

  export let slug: string;
  export let likes: number;

  let busy = false;
  let animating = false;

  async function handleLike(e: MouseEvent) {
    e.stopPropagation();
    if (busy) return;
    busy = true;

    const prev = likes;
    likes += 1;
    animating = true;
    setTimeout(() => animating = false, 300);

    try {
      const result = await likeRecipe(slug);
      likes = result.likes;
    } catch {
      likes = prev;
    }
    busy = false;
  }
</script>

<button
  class="like-btn"
  class:animating
  on:click={handleLike}
  aria-label="Like this recipe"
>
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
  <span class="like-count">{likes}</span>
</button>

<style>
  .like-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text-muted);
    padding: 0.2rem 0.4rem;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.85rem;
    transition: color 0.15s;
    border-radius: 4px;
  }

  .like-btn:hover {
    color: var(--color-danger, #e74c3c);
  }

  .like-btn.animating {
    animation: pulse 0.3s ease;
  }

  .like-count {
    font-size: 0.8rem;
    line-height: 1;
  }

  @keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.2); }
    100% { transform: scale(1); }
  }
</style>
