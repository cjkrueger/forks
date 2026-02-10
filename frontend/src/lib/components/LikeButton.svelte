<script lang="ts">
  export let likes: number;
</script>

<span class="like-display" aria-label="{likes} likes">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" /><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" /><path d="M4 22h16" /><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" /><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" /><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
  </svg>
  <span class="like-count">{likes}</span>
</span>

<style>
  .like-display {
    color: var(--color-text-muted);
    padding: 0.2rem 0.4rem;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.85rem;
  }

  .like-count {
    font-size: 0.8rem;
    line-height: 1;
  }
</style>
