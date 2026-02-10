import { writable, derived } from 'svelte/store';
import { parseIngredient, ingredientKey, formatQuantity } from './ingredients';
import type { ParsedIngredient } from './ingredients';

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

const STORAGE_KEY = 'forks-grocery-list';

function loadStore(): GroceryStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { recipes: {}, checked: [], customCombines: [] };
}

function saveStore(store: GroceryStore) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export const groceryStore = writable<GroceryStore>(loadStore());

groceryStore.subscribe(saveStore);

export function addRecipeToGrocery(
  slug: string,
  title: string,
  ingredients: string[],
  fork: string | null = null,
  servings: string | null = null,
) {
  groceryStore.update(store => {
    store.recipes[slug] = {
      title,
      fork,
      servings,
      items: ingredients.map(parseIngredient),
    };
    return store;
  });
}

export function removeRecipeFromGrocery(slug: string) {
  groceryStore.update(store => {
    delete store.recipes[slug];
    return store;
  });
}

export function toggleChecked(key: string) {
  groceryStore.update(store => {
    const idx = store.checked.indexOf(key);
    if (idx >= 0) {
      store.checked.splice(idx, 1);
    } else {
      store.checked.push(key);
    }
    return store;
  });
}

export function clearChecked() {
  groceryStore.update(store => {
    store.checked = [];
    return store;
  });
}

export function clearAll() {
  groceryStore.set({ recipes: {}, checked: [], customCombines: [] });
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
