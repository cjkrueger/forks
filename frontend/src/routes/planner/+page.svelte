<script lang="ts">
  import { onMount } from 'svelte';
  import { getMealPlan, saveMealPlan, listRecipes, getRecipe } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';
  import RecipePicker from '$lib/components/RecipePicker.svelte';
  import { addRecipeToGrocery } from '$lib/grocery';
  import { parseSections } from '$lib/sections';

  interface PlanSlot {
    slug: string;
    title: string;
    fork?: string | null;
  }

  let weekOffset = 0;
  let days: { date: string; label: string; meals: PlanSlot[] }[] = [];
  let loading = true;
  let saving = false;
  let allRecipes: RecipeSummary[] = [];
  let initialized = false;

  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  function getWeekDates(offset: number): { isoWeek: string; dates: string[] } {
    const now = new Date();
    const day = now.getDay();
    const mondayOffset = day === 0 ? -6 : 1 - day;
    const monday = new Date(now);
    monday.setDate(now.getDate() + mondayOffset + offset * 7);

    const dates: string[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      dates.push(d.toISOString().split('T')[0]);
    }

    // ISO week: Thursday of the week determines the ISO year and week number
    const thu = new Date(monday);
    thu.setDate(monday.getDate() + 3);
    const isoYear = thu.getFullYear();
    const jan4 = new Date(isoYear, 0, 4);
    const dayOfWeek = jan4.getDay() || 7; // Mon=1 .. Sun=7
    const week1Monday = new Date(jan4);
    week1Monday.setDate(jan4.getDate() - dayOfWeek + 1);
    const weekNum = Math.round((monday.getTime() - week1Monday.getTime()) / (7 * 86400000)) + 1;
    const isoWeek = `${isoYear}-W${String(weekNum).padStart(2, '0')}`;

    return { isoWeek, dates };
  }

  function titleForSlug(slug: string): string {
    const recipe = allRecipes.find(r => r.slug === slug);
    return recipe?.title || slug;
  }

  async function loadWeek() {
    loading = true;
    const { isoWeek, dates } = getWeekDates(weekOffset);
    try {
      const data = await getMealPlan(isoWeek);
      days = dates.map((date, i) => ({
        date,
        label: DAY_NAMES[i],
        meals: (data.weeks[date] || []).map(m => ({
          slug: m.slug,
          title: titleForSlug(m.slug),
          fork: m.fork || null,
        })),
      }));
    } catch (e) {
      days = dates.map((date, i) => ({ date, label: DAY_NAMES[i], meals: [] }));
    }
    loading = false;
  }

  async function save() {
    saving = true;
    const weeks: Record<string, { slug: string; fork?: string | null }[]> = {};
    for (const day of days) {
      weeks[day.date] = day.meals.map(m => {
        const entry: { slug: string; fork?: string | null } = { slug: m.slug };
        if (m.fork) entry.fork = m.fork;
        return entry;
      });
    }
    try {
      await saveMealPlan(weeks);
    } catch (e) {
      console.error('Failed to save meal plan', e);
    }
    saving = false;
  }

  function addMeal(dayIndex: number, detail: { slug: string; title: string }) {
    days[dayIndex].meals = [...days[dayIndex].meals, { slug: detail.slug, title: detail.title }];
    days = days;
    save();
  }

  function removeMeal(dayIndex: number, mealIndex: number) {
    days[dayIndex].meals = days[dayIndex].meals.filter((_, i) => i !== mealIndex);
    days = days;
    save();
  }

  let addingToGrocery = false;

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

  async function addAllToGrocery() {
    addingToGrocery = true;
    const seen = new Set<string>();
    for (const day of days) {
      for (const meal of day.meals) {
        const key = meal.fork ? `${meal.slug}:${meal.fork}` : meal.slug;
        if (seen.has(key)) continue;
        seen.add(key);
        try {
          const recipe = await getRecipe(meal.slug);
          const lines = getIngredientLines(recipe.content);
          if (lines.length > 0) {
            addRecipeToGrocery(meal.slug, meal.title, lines, meal.fork || null, recipe.servings);
          }
        } catch (e) {
          console.error(`Failed to fetch recipe ${meal.slug}`, e);
        }
      }
    }
    addingToGrocery = false;
  }

  function prevWeek() {
    weekOffset--;
    loadWeek();
  }

  function nextWeek() {
    weekOffset++;
    loadWeek();
  }

  function goToday() {
    weekOffset = 0;
    loadWeek();
  }

  onMount(async () => {
    allRecipes = await listRecipes();
    initialized = true;
    await loadWeek();
  });

  $: weekLabel = (() => {
    if (days.length === 0) return '';
    const first = days[0].date;
    const last = days[6].date;
    return `${first} \u2013 ${last}`;
  })();
</script>

<svelte:head>
  <title>Meal Planner - Forks</title>
</svelte:head>

<div class="planner">
  <div class="planner-header">
    <h1>Meal Planner</h1>
    <div class="planner-actions">
      <div class="week-nav">
        {#if weekOffset !== 0}
          <button class="today-btn" on:click={goToday}>Today</button>
        {/if}
        <button on:click={prevWeek}>&larr;</button>
        <span class="week-label">{weekLabel}</span>
        <button on:click={nextWeek}>&rarr;</button>
      </div>
      {#if days.some(d => d.meals.length > 0)}
        <button class="grocery-btn" on:click={addAllToGrocery} disabled={addingToGrocery}>
          {addingToGrocery ? 'Adding...' : 'Add all to grocery list'}
        </button>
      {/if}
    </div>
  </div>

  {#if loading}
    <p class="loading">Loading...</p>
  {:else}
    <div class="week-grid">
      {#each days as day, dayIndex}
        <div class="day-column">
          <div class="day-header">
            <span class="day-name">{day.label}</span>
            <span class="day-date">{day.date.slice(5)}</span>
          </div>
          <div class="day-meals">
            {#each day.meals as meal, mealIndex}
              <div class="meal-slot">
                <a href="/recipe/{meal.slug}" class="meal-link">{meal.title}</a>
                {#if meal.fork}
                  <span class="meal-fork">({meal.fork})</span>
                {/if}
                <button class="meal-remove" on:click={() => removeMeal(dayIndex, mealIndex)} aria-label="Remove">&times;</button>
              </div>
            {/each}
            <RecipePicker
              exclude={day.meals.map(m => m.slug)}
              on:select={(e) => addMeal(dayIndex, e.detail)}
            />
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .planner {
    max-width: 1100px;
  }

  .planner-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .planner-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .grocery-btn {
    padding: 0.4rem 0.85rem;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    background: var(--color-accent);
    color: white;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
    white-space: nowrap;
  }

  .grocery-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .grocery-btn:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .planner-header h1 {
    font-size: 1.5rem;
    font-weight: 700;
  }

  .week-nav {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .week-nav button {
    padding: 0.3rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text);
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.15s;
  }

  .week-nav button:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .today-btn {
    font-size: 0.8rem;
    font-weight: 600;
    padding: 0.3rem 0.65rem;
  }

  .week-label {
    font-size: 0.9rem;
    color: var(--color-text-muted);
    min-width: 140px;
    text-align: center;
  }

  .week-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 0.75rem;
  }

  .day-column {
    min-height: 200px;
  }

  .day-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.5rem;
    border-bottom: 2px solid var(--color-border);
    margin-bottom: 0.5rem;
  }

  .day-name {
    font-weight: 600;
    font-size: 0.85rem;
  }

  .day-date {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .day-meals {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .meal-slot {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.35rem 0.5rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.8rem;
  }

  .meal-link {
    flex: 1;
    color: var(--color-text);
    text-decoration: none;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .meal-link:hover {
    color: var(--color-accent);
    text-decoration: none;
  }

  .meal-fork {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  .meal-remove {
    background: none;
    border: none;
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
    padding: 0 0.15rem;
    flex-shrink: 0;
  }

  .meal-remove:hover {
    color: var(--color-accent);
  }

  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--color-text-muted);
  }

  @media (max-width: 768px) {
    .week-grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .day-column {
      min-height: auto;
    }

    .day-header {
      flex-direction: row;
      justify-content: space-between;
    }
  }
</style>
