import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { getSyncStatus } from './api';
import type { SyncStatus } from './types';

const defaultStatus: SyncStatus = {
  connected: false,
  last_synced: null,
  ahead: 0,
  behind: 0,
  error: null,
};

export const syncStatus = writable<SyncStatus>(defaultStatus);
export const isSyncing = writable(false);

let pollInterval: ReturnType<typeof setInterval> | null = null;

export function startSyncPolling(intervalMs = 90_000) {
  if (!browser) return;
  stopSyncPolling();

  async function poll() {
    try {
      const status = await getSyncStatus();
      syncStatus.set(status);
    } catch {
      // Silently fail — sync is optional
    }
  }

  poll();
  pollInterval = setInterval(poll, intervalMs);
}

export function stopSyncPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

export const isConnected = derived(syncStatus, $s => $s.connected);
