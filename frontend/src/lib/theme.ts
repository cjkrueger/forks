import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { safeLocalStorage } from '$lib/storage';

function getInitialTheme(): 'light' | 'dark' {
  if (browser) {
    return (document.documentElement.getAttribute('data-theme') as 'light' | 'dark') || 'light';
  }
  return 'light';
}

export const theme = writable<'light' | 'dark'>(getInitialTheme());

export function toggleTheme() {
  theme.update(t => {
    const next = t === 'light' ? 'dark' : 'light';
    if (browser) {
      document.documentElement.setAttribute('data-theme', next);
      safeLocalStorage.setItem('forks-theme', next);
    }
    return next;
  });
}
