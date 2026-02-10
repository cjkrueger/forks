import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { getSyncStatus, triggerSync } from './api';
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

export function startSyncPolling(intervalMs = 90_000, enabled = true) {
  if (!browser) return;
  stopSyncPolling();
  if (!enabled) return;

  async function poll() {
    try {
      const status = await getSyncStatus();
      syncStatus.set(status);

      // Auto-sync: trigger push/pull when connected and there are unpushed changes
      if (status.connected && (status.ahead > 0 || status.behind > 0)) {
        isSyncing.set(true);
        try {
          await triggerSync();
          const updated = await getSyncStatus();
          syncStatus.set(updated);
        } finally {
          isSyncing.set(false);
        }
      }
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
