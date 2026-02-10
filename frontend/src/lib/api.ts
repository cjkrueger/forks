import type { Recipe, RecipeSummary } from './types';

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
