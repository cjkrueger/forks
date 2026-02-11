<script lang="ts">
  import { onMount } from 'svelte';
  import { getMealPlan, getRecipe, getFork, listRecipes } from '$lib/api';
  import { parseSections, mergeContent } from '$lib/sections';
  import { parseIngredient } from '$lib/ingredients';
  import { getMergedItems } from '$lib/grocery';
  import type { GroceryStore } from '$lib/grocery';
  import { renderMarkdown } from '$lib/markdown';
  import type { RecipeSummary } from '$lib/types';

  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  let loading = true;
  let error = '';
  let weekParam = '';
  let includeRecipes = false;

  let days: { date: string; dayName: string; meals: { title: string; fork?: string | null }[] }[] = [];
  let groceryItems: { displayText: string }[] = [];
  let fullRecipes: { title: string; fork?: string | null; prep_time?: string | null; cook_time?: string | null; servings?: string | null; bodyHtml: string }[] = [];

  function isoWeekToDates(isoWeek: string): string[] {
    const match = isoWeek.match(/^(\d{4})-W(\d{2})$/);
    if (!match) return [];
    const year = parseInt(match[1]);
    const week = parseInt(match[2]);

    const jan4 = new Date(year, 0, 4);
    const dayOfWeek = jan4.getDay() || 7;
    const week1Monday = new Date(jan4);
    week1Monday.setDate(jan4.getDate() - dayOfWeek + 1);

    const monday = new Date(week1Monday);
    monday.setDate(week1Monday.getDate() + (week - 1) * 7);

    const dates: string[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      dates.push(d.toISOString().split('T')[0]);
    }
    return dates;
  }

  function getIngredientLines(content: string): string[] {
    const sections = parseSections(content);
    for (const section of sections) {
      if (section.name.toLowerCase() === 'ingredients') {
        return section.content.split('\n')
          .map(l => l.trim())
          .filter(l => l.startsWith('- '))
          .map(l => l.replace(/^-\s*/, ''));
      }
    }
    return [];
  }

  onMount(async () => {
    const params = new URLSearchParams(window.location.search);
    weekParam = params.get('week') || '';

    if (!weekParam || !/^\d{4}-W\d{2}$/.test(weekParam)) {
      error = 'Missing or invalid week parameter.';
      loading = false;
      return;
    }

    const dates = isoWeekToDates(weekParam);
    if (dates.length !== 7) {
      error = 'Could not compute dates for this week.';
      loading = false;
      return;
    }

    try {
      const [recipeSummaries, planData] = await Promise.all([
        listRecipes(),
        getMealPlan(weekParam),
      ]);

      const slugToTitle = new Map<string, RecipeSummary>();
      for (const r of recipeSummaries) {
        slugToTitle.set(r.slug, r);
      }

      // Build days array
      days = dates.map((date, i) => {
        const dayMeals = planData.weeks[date] || [];
        return {
          date,
          dayName: DAY_NAMES[i],
          meals: dayMeals.map(m => ({
            title: slugToTitle.get(m.slug)?.title || m.slug,
            fork: m.fork || null,
          })),
        };
      });

      // Collect unique recipes by slug:fork key
      const seen = new Set<string>();
      const toFetch: { slug: string; fork: string | null; title: string; summary: RecipeSummary | undefined }[] = [];
      for (const day of days) {
        const dayMeals = planData.weeks[day.date] || [];
        for (let j = 0; j < dayMeals.length; j++) {
          const m = dayMeals[j];
          const key = m.fork ? `${m.slug}:${m.fork}` : m.slug;
          if (seen.has(key)) continue;
          seen.add(key);
          toFetch.push({
            slug: m.slug,
            fork: m.fork || null,
            title: day.meals[j].title,
            summary: slugToTitle.get(m.slug),
          });
        }
      }

      // Fetch recipes and build grocery + full recipe data
      const tempStore: GroceryStore = { recipes: {}, checked: [], customCombines: [] };
      const recipeCache = new Map<string, string>(); // slug -> base content
      fullRecipes = [];

      for (const item of toFetch) {
        try {
          let content: string;
          let baseContent = recipeCache.get(item.slug);
          if (!baseContent) {
            const recipe = await getRecipe(item.slug);
            baseContent = recipe.content;
            recipeCache.set(item.slug, baseContent);
          }

          if (item.fork) {
            try {
              const forkDetail = await getFork(item.slug, item.fork);
              content = mergeContent(baseContent, forkDetail.content);
            } catch {
              content = baseContent;
            }
          } else {
            content = baseContent;
          }

          // Parse ingredients for grocery list
          const lines = getIngredientLines(content);
          if (lines.length > 0) {
            const key = item.fork ? `${item.slug}:${item.fork}` : item.slug;
            tempStore.recipes[key] = {
              title: item.title,
              fork: item.fork,
              servings: item.summary?.servings || null,
              items: lines.map(parseIngredient),
            };
          }

          // Build full recipe entry
          fullRecipes.push({
            title: item.title,
            fork: item.fork,
            prep_time: item.summary?.prep_time || null,
            cook_time: item.summary?.cook_time || null,
            servings: item.summary?.servings || null,
            bodyHtml: renderMarkdown(content),
          });
        } catch (e) {
          console.error(`Failed to fetch recipe ${item.slug}`, e);
        }
      }

      groceryItems = getMergedItems(tempStore);
    } catch (e) {
      error = 'Failed to load meal plan data.';
      console.error(e);
    }

    loading = false;
  });
</script>

<svelte:head>
  <title>Print Meal Plan – {weekParam || 'Forks'}</title>
</svelte:head>

{#if error}
  <div class="print-page">
    <p class="print-error">{error}</p>
    <a href="/planner">Back to Planner</a>
  </div>
{:else if loading}
  <div class="print-page">
    <p class="print-loading">Loading meal plan...</p>
  </div>
{:else}
  <div class="print-page">
    <div class="print-controls no-print">
      <a href="/planner" class="back-link">&larr; Back to Planner</a>
      <label class="include-recipes-toggle">
        <input type="checkbox" bind:checked={includeRecipes} />
        Include full recipes
      </label>
      <button class="print-btn" on:click={() => window.print()}>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
        Print
      </button>
    </div>

    <h1 class="print-week-title">Meal Plan – {weekParam}</h1>

    <!-- Calendar -->
    <table class="calendar-table">
      <thead>
        <tr>
          {#each days as day}
            <th>
              <span class="cal-day-name">{day.dayName}</span>
              <span class="cal-day-date">{day.date.slice(5)}</span>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        <tr>
          {#each days as day}
            <td>
              {#if day.meals.length === 0}
                <span class="empty-day">&mdash;</span>
              {:else}
                {#each day.meals as meal}
                  <div class="cal-meal">
                    {meal.title}
                    {#if meal.fork}
                      <span class="cal-fork">({meal.fork})</span>
                    {/if}
                  </div>
                {/each}
              {/if}
            </td>
          {/each}
        </tr>
      </tbody>
    </table>

    <!-- Grocery List -->
    {#if groceryItems.length > 0}
      <h2 class="section-title">Grocery List</h2>
      <div class="grocery-columns">
        {#each groceryItems as item}
          <div class="grocery-item">
            <span class="grocery-checkbox"></span>
            <span>{item.displayText}</span>
          </div>
        {/each}
      </div>
    {/if}

    <!-- Full Recipes -->
    {#if includeRecipes && fullRecipes.length > 0}
      {#each fullRecipes as recipe}
        <section class="recipe-page">
          <h2 class="recipe-print-title">
            {recipe.title}
            {#if recipe.fork}
              <span class="recipe-fork-label">({recipe.fork})</span>
            {/if}
          </h2>
          {#if recipe.prep_time || recipe.cook_time || recipe.servings}
            <p class="recipe-print-meta">
              {[
                recipe.prep_time ? `Prep: ${recipe.prep_time}` : '',
                recipe.cook_time ? `Cook: ${recipe.cook_time}` : '',
                recipe.servings ? `Serves: ${recipe.servings}` : '',
              ].filter(Boolean).join(' · ')}
            </p>
          {/if}
          <div class="recipe-print-body">
            {@html recipe.bodyHtml}
          </div>
        </section>
      {/each}
    {/if}
  </div>
{/if}

<style>
  .print-page {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
  }

  .print-controls {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 2rem;
    padding: 0.75rem 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
  }

  .print-controls .back-link {
    color: var(--color-text-muted);
    text-decoration: none;
    font-size: 0.85rem;
  }

  .print-controls .back-link:hover {
    color: var(--color-accent);
  }

  .include-recipes-toggle {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.85rem;
    color: var(--color-text);
    cursor: pointer;
    margin-left: auto;
  }

  .print-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.85rem;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    background: var(--color-accent);
    color: white;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .print-btn:hover {
    opacity: 0.9;
  }

  .print-week-title {
    font-size: 1.4rem;
    font-weight: 700;
    margin-bottom: 1.5rem;
  }

  /* Calendar */
  .calendar-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 2rem;
    font-size: 0.85rem;
  }

  .calendar-table th {
    text-align: center;
    padding: 0.5rem 0.25rem;
    border-bottom: 2px solid var(--color-border);
    font-weight: 600;
  }

  .cal-day-name {
    display: block;
    font-size: 0.8rem;
  }

  .cal-day-date {
    display: block;
    font-size: 0.7rem;
    color: var(--color-text-muted);
  }

  .calendar-table td {
    vertical-align: top;
    padding: 0.5rem 0.35rem;
    border-bottom: 1px solid var(--color-border);
    min-height: 3rem;
  }

  .empty-day {
    color: var(--color-text-muted);
  }

  .cal-meal {
    font-size: 0.8rem;
    margin-bottom: 0.25rem;
  }

  .cal-fork {
    font-size: 0.7rem;
    color: var(--color-text-muted);
  }

  /* Grocery List */
  .section-title {
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 1rem;
    padding-bottom: 0.35rem;
    border-bottom: 2px solid var(--color-border);
  }

  .grocery-columns {
    column-count: 2;
    column-gap: 2rem;
    margin-bottom: 2rem;
  }

  .grocery-item {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.2rem 0;
    font-size: 0.85rem;
    break-inside: avoid;
  }

  .grocery-checkbox {
    display: inline-block;
    width: 12px;
    height: 12px;
    min-width: 12px;
    border: 1.5px solid var(--color-border);
    border-radius: 2px;
    flex-shrink: 0;
    position: relative;
    top: 1px;
  }

  /* Full Recipes */
  .recipe-page {
    margin-top: 2rem;
    padding-top: 2rem;
    border-top: 2px solid var(--color-border);
  }

  .recipe-print-title {
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
  }

  .recipe-fork-label {
    font-weight: 400;
    font-size: 0.9rem;
    color: var(--color-text-muted);
  }

  .recipe-print-meta {
    font-size: 0.8rem;
    color: var(--color-text-muted);
    margin-bottom: 1rem;
  }

  .recipe-print-body {
    font-size: 0.9rem;
    line-height: 1.6;
  }

  .recipe-print-body :global(h2) {
    font-size: 1rem;
    font-weight: 700;
    margin-top: 1.25rem;
    margin-bottom: 0.5rem;
  }

  .recipe-print-body :global(ul),
  .recipe-print-body :global(ol) {
    padding-left: 1.25rem;
    margin-bottom: 0.75rem;
  }

  .recipe-print-body :global(li) {
    margin-bottom: 0.3rem;
  }

  .print-loading, .print-error {
    text-align: center;
    padding: 4rem;
    color: var(--color-text-muted);
  }

  .print-error {
    color: var(--color-danger);
  }
</style>
