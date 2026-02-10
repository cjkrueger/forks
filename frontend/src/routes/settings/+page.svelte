<script lang="ts">
  import { onMount } from 'svelte';
  import { getSettings, saveSettings, disconnectRemote, triggerSync } from '$lib/api';
  import { syncStatus, isSyncing } from '$lib/sync';
  import type { AppSettings } from '$lib/types';

  let settings: AppSettings = {
    remote: { provider: null, url: null, token: null },
    sync: { enabled: false, interval_seconds: 300 },
  };

  let loading = true;
  let saving = false;
  let message = '';
  let messageType: 'success' | 'error' = 'success';

  onMount(async () => {
    try {
      settings = await getSettings();
    } catch (e: any) {
      showMessage('Failed to load settings', 'error');
    }
    loading = false;
  });

  function showMessage(text: string, type: 'success' | 'error') {
    message = text;
    messageType = type;
    setTimeout(() => { message = ''; }, 4000);
  }

  async function handleSave() {
    saving = true;
    try {
      await saveSettings(settings);
      showMessage('Settings saved.', 'success');
    } catch (e: any) {
      showMessage(e.message || 'Failed to save settings', 'error');
    }
    saving = false;
  }

  async function handleSync() {
    $isSyncing = true;
    try {
      const result = await triggerSync();
      if (result.pull_success && result.push_success) {
        showMessage('Sync complete.', 'success');
      } else {
        showMessage('Sync finished with warnings.', 'error');
      }
    } catch (e: any) {
      showMessage(e.message || 'Sync failed', 'error');
    }
    $isSyncing = false;
  }

  async function handleDisconnect() {
    if (!confirm('Disconnect from remote? Local data will be kept.')) return;
    try {
      await disconnectRemote();
      settings = await getSettings();
      showMessage('Disconnected from remote.', 'success');
    } catch (e: any) {
      showMessage(e.message || 'Failed to disconnect', 'error');
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return 'Never';
    const d = new Date(dateStr);
    return d.toLocaleString();
  }
</script>

<svelte:head>
  <title>Settings - Forks</title>
</svelte:head>

<div class="settings-page">
  <a href="/" class="back-link">&larr; All recipes</a>
  <h1>Settings</h1>

  {#if loading}
    <p class="loading-text">Loading settings...</p>
  {:else}
    <section class="section">
      <h2>Remote Sync</h2>
      <p class="section-desc">
        Connect to a Git remote to back up your recipes and sync across devices.
      </p>

      <div class="status-bar">
        <span class="status-dot" class:connected={$syncStatus.connected}></span>
        <span class="status-label">
          {$syncStatus.connected ? 'Connected' : 'Disconnected'}
        </span>
        {#if $syncStatus.connected}
          <span class="status-detail">
            Last synced: {formatDate($syncStatus.last_synced)}
          </span>
          {#if $syncStatus.ahead > 0 || $syncStatus.behind > 0}
            <span class="status-detail">
              {$syncStatus.ahead} ahead, {$syncStatus.behind} behind
            </span>
          {/if}
        {/if}
        {#if $syncStatus.error}
          <span class="status-error">{$syncStatus.error}</span>
        {/if}
      </div>

      <form class="settings-form" on:submit|preventDefault={handleSave}>
        <div class="field">
          <label for="provider">Provider</label>
          <select id="provider" bind:value={settings.remote.provider}>
            <option value={null}>None</option>
            <option value="github">GitHub</option>
            <option value="gitlab">GitLab</option>
            <option value="generic">Generic Git</option>
          </select>
        </div>

        <div class="field">
          <label for="repo-url">Repository URL</label>
          <input
            id="repo-url"
            type="text"
            bind:value={settings.remote.url}
            placeholder="https://github.com/user/recipes.git"
          />
        </div>

        <div class="field">
          <label for="token">Access Token</label>
          <input
            id="token"
            type="password"
            bind:value={settings.remote.token}
            placeholder={settings.remote.provider === 'github' ? 'ghp_...' : settings.remote.provider === 'gitlab' ? 'glpat-...' : 'token'}
          />
          {#if settings.remote.provider === 'github'}
            <p class="field-help">
              Create a <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">fine-grained personal access token</a> with <strong>Contents</strong> read &amp; write permission for your recipes repo.
            </p>
          {:else if settings.remote.provider === 'gitlab'}
            <p class="field-help">
              Create a <a href="https://gitlab.com/-/user_settings/personal_access_tokens" target="_blank" rel="noopener">personal access token</a> with <strong>read_repository</strong> and <strong>write_repository</strong> scopes.
            </p>
          {:else if settings.remote.provider === 'generic'}
            <p class="field-help">
              Use a personal access token from your git provider with read and write access to the repository.
            </p>
          {/if}
        </div>

        <div class="field checkbox-field">
          <label>
            <input type="checkbox" bind:checked={settings.sync.enabled} />
            Auto-sync
          </label>
        </div>

        <div class="field">
          <label for="interval">Sync interval (seconds)</label>
          <input
            id="interval"
            type="number"
            min="30"
            step="10"
            bind:value={settings.sync.interval_seconds}
          />
        </div>

        <div class="actions">
          <button type="submit" class="btn btn-primary" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          {#if $syncStatus.connected}
            <button
              type="button"
              class="btn btn-secondary"
              on:click={handleSync}
              disabled={$isSyncing}
            >
              {$isSyncing ? 'Syncing...' : 'Sync Now'}
            </button>
            <button
              type="button"
              class="btn btn-danger"
              on:click={handleDisconnect}
            >
              Disconnect
            </button>
          {/if}
        </div>
      </form>

      {#if message}
        <p class="message" class:error={messageType === 'error'} class:success={messageType === 'success'}>
          {message}
        </p>
      {/if}
    </section>
  {/if}
</div>

<style>
  .settings-page {
    max-width: 640px;
  }

  .back-link {
    display: inline-block;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 1rem;
  }

  .back-link:hover {
    color: var(--color-accent);
  }

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 2rem;
  }

  .loading-text {
    color: var(--color-text-muted);
    font-size: 0.9rem;
  }

  .section {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
  }

  h2 {
    font-size: 1.15rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }

  .section-desc {
    color: var(--color-text-muted);
    font-size: 0.875rem;
    margin-bottom: 1.25rem;
    line-height: 1.5;
  }

  .status-bar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    margin-bottom: 1.5rem;
    font-size: 0.85rem;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-text-muted);
    flex-shrink: 0;
  }

  .status-dot.connected {
    background: var(--color-success);
  }

  .status-label {
    font-weight: 600;
  }

  .status-detail {
    color: var(--color-text-muted);
  }

  .status-error {
    color: var(--color-danger);
  }

  .settings-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .field label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .field input[type="text"],
  .field input[type="password"],
  .field input[type="number"],
  .field select {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.9rem;
    font-family: var(--font-body);
    background: var(--color-bg);
    color: var(--color-text);
    outline: none;
    transition: border-color 0.2s;
  }

  .field input:focus,
  .field select:focus {
    border-color: var(--color-accent);
  }

  .field-help {
    font-size: 0.8rem;
    color: var(--color-text-muted);
    line-height: 1.5;
    margin: 0;
  }

  .field-help a {
    color: var(--color-accent);
    text-decoration: underline;
  }

  .field-help a:hover {
    opacity: 0.8;
  }

  .checkbox-field {
    flex-direction: row;
    align-items: center;
  }

  .checkbox-field label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-weight: 500;
  }

  .checkbox-field input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--color-accent);
  }

  .actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 0.5rem;
  }

  .btn {
    padding: 0.5rem 1.25rem;
    border: none;
    border-radius: var(--radius);
    font-size: 0.9rem;
    font-weight: 600;
    font-family: var(--font-body);
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--color-accent);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
  }

  .btn-secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .btn-secondary:hover:not(:disabled) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .btn-danger {
    background: var(--color-danger-light);
    color: var(--color-danger);
    border: 1px solid var(--color-danger-border);
  }

  .btn-danger:hover:not(:disabled) {
    opacity: 0.85;
  }

  .message {
    margin-top: 1rem;
    font-size: 0.85rem;
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius);
  }

  .message.success {
    background: var(--color-success-light);
    color: #2E7D32;
    border: 1px solid #A5D6A7;
  }

  :global([data-theme="dark"]) .message.success {
    background: var(--color-success-light);
    color: var(--color-success);
    border-color: #2E5A2E;
  }

  .message.error {
    background: var(--color-danger-light);
    color: var(--color-danger);
    border: 1px solid var(--color-danger-border);
  }

  @media (max-width: 768px) {
    .settings-page {
      max-width: 100%;
    }

    .actions {
      flex-direction: column;
    }

    .btn {
      width: 100%;
      text-align: center;
    }
  }
</style>
