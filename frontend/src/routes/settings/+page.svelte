<script lang="ts">
  import { onMount } from 'svelte';
  import { getSettings, saveSettings, disconnectRemote, triggerSync } from '$lib/api';
  import { syncStatus, isSyncing } from '$lib/sync';
  import type { AppSettings } from '$lib/types';

  let settings: AppSettings = {
    remote: { provider: null, url: null, token: null, local_path: null },
    sync: { enabled: false, interval_seconds: 5400, sync_meal_plans: true },
  };

  let savedProvider: string | null = null;
  let intervalMinutes = 90;
  let loading = true;
  let saving = false;
  let message = '';
  let messageType: 'success' | 'error' = 'success';

  onMount(async () => {
    try {
      settings = await getSettings();
      savedProvider = settings.remote.provider;
      intervalMinutes = Math.round(settings.sync.interval_seconds / 60);
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

  function selectProvider(provider: string) {
    if (settings.remote.provider === provider) {
      settings.remote.provider = null;
    } else {
      settings.remote.provider = provider;
    }
  }

  async function handleSave() {
    saving = true;
    settings.sync.interval_seconds = intervalMinutes * 60;
    try {
      await saveSettings(settings);
      savedProvider = settings.remote.provider;
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
    if (!confirm('Disconnect sync target? Local data will be kept.')) return;
    try {
      await disconnectRemote();
      settings = await getSettings();
      savedProvider = settings.remote.provider;
      showMessage('Sync target disconnected.', 'success');
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
  <title>Sync Settings - Forks</title>
</svelte:head>

<div class="settings-page">
  <a href="/" class="back-link">&larr; All recipes</a>
  <h1>Sync Settings</h1>

  {#if loading}
    <p class="loading-text">Loading settings...</p>
  {:else}
    <section class="section">
      <h2>Backup &amp; Sync</h2>
      <p class="section-desc">
        Sync your recipes to a Git provider or local folder to back up and access them across devices.
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
          <label>Provider</label>
          <div class="provider-picker">
            {#each [
              { id: 'github', label: 'GitHub' },
              { id: 'gitlab', label: 'GitLab' },
              { id: 'tangled', label: 'Tangled' },
              { id: 'generic', label: 'Git' },
              { id: 'local', label: 'Local' },
            ] as p}
              <button
                type="button"
                class="provider-btn"
                class:selected={settings.remote.provider === p.id}
                on:click={() => selectProvider(p.id)}
                title={p.label}
              >
                {#if savedProvider === p.id && $syncStatus.connected}
                  <span class="sync-indicator" class:syncing={$isSyncing}></span>
                {/if}
                {#if p.id === 'github'}
                  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.009-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836a9.59 9.59 0 012.504.337c1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z"/>
                  </svg>
                {:else if p.id === 'gitlab'}
                  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0118.6 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.51L23 13.45a.84.84 0 01-.35.94z"/>
                  </svg>
                {:else if p.id === 'tangled'}
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M8 8c0-2.21 1.79-4 4-4s4 1.79 4 4-1.79 4-4 4"/>
                    <path d="M16 16c0 2.21-1.79 4-4 4s-4-1.79-4-4 1.79-4 4-4"/>
                  </svg>
                {:else if p.id === 'generic'}
                  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M21.62 11.11l-8.73-8.73a1.3 1.3 0 00-1.84 0L9.08 4.35l2.32 2.32a1.54 1.54 0 011.95 1.97l2.24 2.24a1.55 1.55 0 011.6 2.58 1.55 1.55 0 01-2.16-2.16l-2.09-2.09v5.5a1.55 1.55 0 11-1.27-.07V11a1.55 1.55 0 01-.84-2.03L8.52 6.65l-6.14 6.14a1.3 1.3 0 000 1.84l8.73 8.73a1.3 1.3 0 001.84 0l8.67-8.67a1.3 1.3 0 000-1.84v.06z"/>
                  </svg>
                {:else if p.id === 'local'}
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
                  </svg>
                {/if}
                <span>{p.label}</span>
              </button>
            {/each}
          </div>
        </div>

        {#if settings.remote.provider === 'local'}
          <div class="field">
            <label for="local-path">Folder Path</label>
            <input
              id="local-path"
              type="text"
              bind:value={settings.remote.local_path}
              placeholder="/mnt/nas/recipes-backup"
            />
            <p class="field-help">
              Absolute path to a local folder (e.g. mounted NAS or backup drive). A bare git repository will be created automatically if one doesn't exist.
            </p>
          </div>
        {:else if settings.remote.provider === 'tangled'}
          <div class="field">
            <label for="repo-url">Repository URL</label>
            <input
              id="repo-url"
              type="text"
              bind:value={settings.remote.url}
              placeholder="git@tangled.org:you.tangled.org/recipes"
            />
            <p class="field-help">
              SSH URL for your Tangled repo. Add your SSH public key in your <a href="https://tangled.org/settings/keys" target="_blank" rel="noopener">Tangled settings</a> and ensure your <code>~/.ssh/config</code> has an entry for <code>tangled.org</code>.
            </p>
          </div>
        {:else if settings.remote.provider}
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
        {/if}

        {#if settings.remote.provider}
          <div class="field checkbox-field">
            <label>
              <input type="checkbox" bind:checked={settings.sync.enabled} />
              Auto-sync
            </label>
          </div>

          <div class="field">
            <label for="interval">Sync interval (minutes)</label>
            <input
              id="interval"
              type="number"
              min="1"
              step="1"
              bind:value={intervalMinutes}
            />
          </div>

          <div class="field checkbox-field">
            <label>
              <input type="checkbox" bind:checked={settings.sync.sync_meal_plans} />
              Sync meal plans
            </label>
            <p class="field-help">Include weekly meal plans when syncing.</p>
          </div>
        {/if}

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
    margin: 0 auto;
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

  /* Provider picker */
  .provider-picker {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .provider-btn {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.4rem;
    padding: 0.6rem;
    width: 72px;
    background: var(--color-bg);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-lg);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    color: var(--color-text-muted);
  }

  .provider-btn:hover {
    border-color: var(--color-text-muted);
    color: var(--color-text);
  }

  .provider-btn.selected {
    border-color: var(--color-accent);
    background: var(--color-accent-light);
    color: var(--color-accent);
  }

  .provider-btn svg {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
  }

  .provider-btn span {
    font-size: 0.7rem;
    font-weight: 600;
    font-family: var(--font-body);
    line-height: 1;
  }

  .sync-indicator {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-success);
  }

  .sync-indicator.syncing {
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.75); }
  }

  /* Form fields */
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

  .field-help code {
    font-size: 0.78rem;
    background: var(--color-tag);
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
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
