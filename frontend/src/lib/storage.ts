import { browser } from '$app/environment';

/**
 * SSR-safe localStorage wrapper.
 *
 * SvelteKit runs module-level and reactive code on the server during
 * pre-rendering, where `localStorage` does not exist. This utility gates
 * all access behind the `browser` flag so the same code works in both
 * environments without throwing ReferenceError.
 */
export const safeLocalStorage = {
  getItem(key: string): string | null {
    if (!browser) return null;
    return localStorage.getItem(key);
  },

  setItem(key: string, value: string): void {
    if (!browser) return;
    localStorage.setItem(key, value);
  },

  removeItem(key: string): void {
    if (!browser) return;
    localStorage.removeItem(key);
  },
};
