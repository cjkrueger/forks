import { writable, derived } from 'svelte/store';
import { ingredientKey, formatQuantity } from './ingredients';
import type { ParsedIngredient } from './ingredients';
import type { GroceryList } from './types';
import {
  getGroceryList,
  addRecipeToGroceryApi,
  removeRecipeFromGroceryApi,
  toggleGroceryChecked,
  removeGroceryItem,
  clearGroceryChecked,
  clearGroceryAll,
} from './api';

export interface GroceryRecipe {
  title: string;
  fork: string | null;
  servings: string | null;
  items: ParsedIngredient[];
}

export interface GroceryStore {
  recipes: Record<string, GroceryRecipe>;
  checked: string[];
  customCombines: Array<{ keys: string[]; quantity: number | null; unit: string | null; name: string }>;
}

function emptyStore(): GroceryStore {
  return { recipes: {}, checked: [], customCombines: [] };
}

function apiToStore(data: GroceryList): GroceryStore {
  return {
    recipes: data.recipes as unknown as Record<string, GroceryRecipe>,
    checked: data.checked,
    customCombines: [],
  };
}

export const groceryStore = writable<GroceryStore>(emptyStore());

export async function initGroceryStore() {
  try {
    const data = await getGroceryList();
    groceryStore.set(apiToStore(data));
  } catch {
    // If API fails, start with empty store
  }
}

export async function addRecipeToGrocery(
  slug: string,
  title: string,
  ingredients: string[],
  fork: string | null = null,
  servings: string | null = null,
) {
  try {
    const data = await addRecipeToGroceryApi(slug, title, ingredients, fork, servings);
    groceryStore.set(apiToStore(data));
  } catch (e) {
    console.error('Failed to add recipe to grocery list', e);
  }
}

export async function removeRecipeFromGrocery(slug: string) {
  try {
    const data = await removeRecipeFromGroceryApi(slug);
    groceryStore.set(apiToStore(data));
  } catch (e) {
    console.error('Failed to remove recipe from grocery list', e);
  }
}

export async function toggleChecked(key: string) {
  try {
    const data = await toggleGroceryChecked(key);
    groceryStore.set(apiToStore(data));
  } catch (e) {
    console.error('Failed to toggle checked', e);
  }
}

export async function clearChecked() {
  try {
    const data = await clearGroceryChecked();
    groceryStore.set(apiToStore(data));
  } catch (e) {
    console.error('Failed to clear checked', e);
  }
}

export async function removeItem(key: string) {
  try {
    const data = await removeGroceryItem(key);
    groceryStore.set(apiToStore(data));
  } catch (e) {
    console.error('Failed to remove item', e);
  }
}

export async function clearAll() {
  try {
    const data = await clearGroceryAll();
    groceryStore.set(apiToStore(data));
  } catch (e) {
    console.error('Failed to clear grocery list', e);
  }
}

export function addCustomCombine(keys: string[], quantity: number | null, unit: string | null, name: string) {
  groceryStore.update(store => {
    store.customCombines.push({ keys, quantity, unit, name });
    return store;
  });
}

export interface MergedItem {
  key: string;
  quantity: number | null;
  unit: string | null;
  name: string;
  displayText: string;
  sources: string[];
  checked: boolean;
}

export function getMergedItems(store: GroceryStore): MergedItem[] {
  const map = new Map<string, { quantity: number | null; unit: string | null; name: string; sources: string[] }>();

  // Collect keys that have been custom-combined
  const combinedKeys = new Set<string>();
  for (const combine of store.customCombines) {
    for (const k of combine.keys) combinedKeys.add(k);
  }

  for (const [slug, recipe] of Object.entries(store.recipes)) {
    for (const item of recipe.items) {
      const key = ingredientKey(item);
      if (combinedKeys.has(`${slug}:${key}`)) continue;

      if (map.has(key)) {
        const existing = map.get(key)!;
        if (existing.quantity !== null && item.quantity !== null && existing.unit === item.unit) {
          existing.quantity += item.quantity;
        }
        if (!existing.sources.includes(recipe.title)) {
          existing.sources.push(recipe.title);
        }
      } else {
        map.set(key, {
          quantity: item.quantity,
          unit: item.unit,
          name: item.name,
          sources: [recipe.title],
        });
      }
    }
  }

  // Add custom combines
  for (const combine of store.customCombines) {
    const key = `custom:${combine.name}`;
    map.set(key, {
      quantity: combine.quantity,
      unit: combine.unit,
      name: combine.name,
      sources: [],
    });
  }

  const items: MergedItem[] = [];
  for (const [key, val] of map) {
    const qtyStr = val.quantity !== null ? formatQuantity(val.quantity) : '';
    const unitStr = val.unit || '';
    const displayText = [qtyStr, unitStr, val.name].filter(Boolean).join(' ');

    items.push({
      key,
      quantity: val.quantity,
      unit: val.unit,
      name: val.name,
      displayText,
      sources: val.sources,
      checked: store.checked.includes(key),
    });
  }

  return items.sort((a, b) => a.name.localeCompare(b.name));
}

export const recipeCount = derived(groceryStore, $store => Object.keys($store.recipes).length);
