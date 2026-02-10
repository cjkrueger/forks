import type { Recipe, RecipeInput, RecipeSummary, ScrapeResponse } from './types';

const BASE = '/api';

export async function listRecipes(tags?: string[]): Promise<RecipeSummary[]> {
  const params = new URLSearchParams();
  if (tags && tags.length > 0) {
    params.set('tags', tags.join(','));
  }
  const url = `${BASE}/recipes${params.toString() ? '?' + params.toString() : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch recipes');
  return res.json();
}

export async function getRecipe(slug: string): Promise<Recipe> {
  const res = await fetch(`${BASE}/recipes/${slug}`);
  if (!res.ok) throw new Error('Recipe not found');
  return res.json();
}

export async function searchRecipes(query: string): Promise<RecipeSummary[]> {
  const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

export async function scrapeRecipe(url: string): Promise<ScrapeResponse> {
  const res = await fetch(`${BASE}/scrape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Scrape failed' }));
    throw new Error(err.detail || 'Scrape failed');
  }
  return res.json();
}

export async function createRecipe(data: RecipeInput): Promise<Recipe> {
  const res = await fetch(`${BASE}/recipes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Create failed' }));
    throw new Error(err.detail || 'Create failed');
  }
  return res.json();
}

export async function updateRecipe(slug: string, data: RecipeInput): Promise<Recipe> {
  const res = await fetch(`${BASE}/recipes/${slug}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Update failed' }));
    throw new Error(err.detail || 'Update failed');
  }
  return res.json();
}

export async function deleteRecipe(slug: string): Promise<void> {
  const res = await fetch(`${BASE}/recipes/${slug}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Delete failed');
}
