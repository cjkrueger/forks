<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { parseTimers } from '$lib/timers';
  import type { TimerMatch } from '$lib/timers';
  import TimerChip from './TimerChip.svelte';
  import TimerBar from './TimerBar.svelte';
  import type { Timer } from './TimerBar.svelte';

  export let title: string;
  export let ingredients: string[];
  export let steps: string[];
  export let notes: string[];

  const dispatch = createEventDispatcher();

  let currentStep = 0;
  let checkedIngredients: Set<number> = new Set();
  let timers: Timer[] = [];
  let nextTimerId = 1;
  let tickInterval: ReturnType<typeof setInterval> | null = null;
  let wakeLock: WakeLockSentinel | null = null;
  let audioContext: AudioContext | null = null;
  let audioBuffer: AudioBuffer | null = null;
  let notificationPermission: NotificationPermission = 'default';

  let drawerOpen = false;

  let touchStartX = 0;
  let touchStartY = 0;
  let swiping = false;

  $: totalSteps = steps.length;
  $: showNotes = currentStep >= totalSteps && notes.length > 0;
  $: currentStepText = currentStep < totalSteps ? steps[currentStep] : '';
  $: stepTimers = currentStep < totalSteps ? parseTimers(currentStepText) : [];
  $: checkedCount = checkedIngredients.size;
  $: hasTimerBar = timers.some(t => t.status !== 'dismissed');

  interface TextSegment { type: 'text'; text: string; }
  interface TimerSegment { type: 'timer'; match: TimerMatch; }
  type Segment = TextSegment | TimerSegment;

  $: stepSegments = buildSegments(currentStepText, stepTimers);

  function buildSegments(text: string, matches: TimerMatch[]): Segment[] {
    if (matches.length === 0) return [{ type: 'text', text }];
    const segments: Segment[] = [];
    let lastEnd = 0;
    for (const m of matches) {
      if (m.startIndex > lastEnd) {
        segments.push({ type: 'text', text: text.slice(lastEnd, m.startIndex) });
      }
      segments.push({ type: 'timer', match: m });
      lastEnd = m.endIndex;
    }
    if (lastEnd < text.length) {
      segments.push({ type: 'text', text: text.slice(lastEnd) });
    }
    return segments;
  }

  let runningTimerMap: Map<string, number> = new Map();

  function timerKeyForMatch(m: TimerMatch): string {
    return `${currentStep}-${m.startIndex}`;
  }

  function isMatchRunning(m: TimerMatch): boolean {
    const key = timerKeyForMatch(m);
    const id = runningTimerMap.get(key);
    if (id === undefined) return false;
    const t = timers.find(t => t.id === id);
    return t !== undefined && t.status === 'running';
  }

  function getMatchRemaining(m: TimerMatch): number | null {
    const key = timerKeyForMatch(m);
    const id = runningTimerMap.get(key);
    if (id === undefined) return null;
    const t = timers.find(t => t.id === id);
    return t ? t.remainingSeconds : null;
  }

  function startTimer(totalSeconds: number, label: string, match: TimerMatch | null) {
    if (timers.filter(t => t.status !== 'dismissed').length >= 5) {
      const done = timers.find(t => t.status === 'done');
      if (done) {
        done.status = 'dismissed';
        timers = timers;
      } else {
        return;
      }
    }

    const id = nextTimerId++;
    timers = [...timers, {
      id,
      label: `Step ${currentStep + 1} — ${label}`,
      totalSeconds,
      remainingSeconds: totalSeconds,
      status: 'running',
    }];

    if (match) {
      runningTimerMap.set(timerKeyForMatch(match), id);
      runningTimerMap = runningTimerMap;
    }

    ensureTicking();
    requestNotificationPermission();
    initAudio();
  }

  function dismissTimer(id: number) {
    timers = timers.map(t => t.id === id ? { ...t, status: 'dismissed' as const } : t);
    for (const [key, tid] of runningTimerMap) {
      if (tid === id) {
        runningTimerMap.delete(key);
      }
    }
    runningTimerMap = runningTimerMap;
  }

  function ensureTicking() {
    if (tickInterval) return;
    tickInterval = setInterval(() => {
      timers = timers.map(t => {
        if (t.status !== 'running') return t;
        const remaining = t.remainingSeconds - 1;
        if (remaining <= 0) {
          playAlarm();
          fireNotification(t.label);
          return { ...t, remainingSeconds: 0, status: 'done' as const };
        }
        return { ...t, remainingSeconds: remaining };
      });

      if (!timers.some(t => t.status === 'running')) {
        if (tickInterval) {
          clearInterval(tickInterval);
          tickInterval = null;
        }
      }
    }, 1000);
  }

  async function acquireWakeLock() {
    try {
      if ('wakeLock' in navigator) {
        wakeLock = await (navigator as any).wakeLock.request('screen');
      }
    } catch (e) {}
  }

  async function releaseWakeLock() {
    if (wakeLock) {
      try { await wakeLock.release(); } catch (e) {}
      wakeLock = null;
    }
  }

  function handleVisibilityChange() {
    if (document.visibilityState === 'visible' && !wakeLock) {
      acquireWakeLock();
    }
  }

  async function initAudio() {
    if (audioContext) return;
    try {
      audioContext = new AudioContext();
      const sampleRate = audioContext.sampleRate;
      const duration = 0.5;
      const buffer = audioContext.createBuffer(1, sampleRate * duration, sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < data.length; i++) {
        const t = i / sampleRate;
        data[i] = 0.3 * Math.sin(2 * Math.PI * 880 * t) * Math.exp(-3 * t)
                 + 0.2 * Math.sin(2 * Math.PI * 1320 * t) * Math.exp(-4 * t);
      }
      audioBuffer = buffer;
    } catch (e) {}
  }

  function playAlarm() {
    if (!audioContext || !audioBuffer) return;
    try {
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start();
    } catch (e) {}
  }

  async function requestNotificationPermission() {
    if (notificationPermission !== 'default') return;
    if (!('Notification' in window)) return;
    try {
      notificationPermission = await Notification.requestPermission();
    } catch (e) {}
  }

  function fireNotification(label: string) {
    if (notificationPermission !== 'granted') return;
    try {
      new Notification('Timer done!', { body: `${label} is done` });
    } catch (e) {}
  }

  function nextStep() {
    if (currentStep < totalSteps) currentStep++;
  }

  function prevStep() {
    if (currentStep > 0) currentStep--;
  }

  function toggleIngredient(index: number) {
    if (checkedIngredients.has(index)) {
      checkedIngredients.delete(index);
    } else {
      checkedIngredients.add(index);
    }
    checkedIngredients = checkedIngredients;
  }

  function exit() {
    dispatch('exit');
  }

  function handleTouchStart(e: TouchEvent) {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    swiping = false;
  }

  function handleTouchMove(e: TouchEvent) {
    const dx = e.touches[0].clientX - touchStartX;
    const dy = e.touches[0].clientY - touchStartY;
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 20) {
      swiping = true;
    }
  }

  function handleTouchEnd(e: TouchEvent) {
    if (!swiping) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) {
      if (dx < 0) nextStep();
      else prevStep();
    }
  }

  onMount(() => {
    acquireWakeLock();
    document.addEventListener('visibilitychange', handleVisibilityChange);
  });

  onDestroy(() => {
    releaseWakeLock();
    if (tickInterval) clearInterval(tickInterval);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  });
</script>

<div class="cook-mode">
  <div class="cook-topbar">
    <h2 class="cook-title">{title}</h2>
    <span class="cook-progress">
      {#if showNotes}
        Notes
      {:else}
        Step {currentStep + 1} of {totalSteps}
      {/if}
    </span>
    <button class="cook-exit" on:click={exit}>Exit</button>
  </div>

  <div class="cook-layout">
    <aside class="ingredients-panel">
      <h3 class="panel-heading">Ingredients ({checkedCount}/{ingredients.length})</h3>
      <ul class="ingredient-list">
        {#each ingredients as item, i}
          <li class="ingredient-item" class:checked={checkedIngredients.has(i)}>
            <label>
              <input type="checkbox" checked={checkedIngredients.has(i)} on:change={() => toggleIngredient(i)} />
              <span>{item}</span>
            </label>
          </li>
        {/each}
      </ul>
    </aside>

    <div
      class="step-panel"
      on:touchstart={handleTouchStart}
      on:touchmove={handleTouchMove}
      on:touchend={handleTouchEnd}
    >
      {#if showNotes}
        <div class="step-content">
          <h3 class="notes-heading">Notes</h3>
          <ul class="notes-list">
            {#each notes as note}
              <li>{note}</li>
            {/each}
          </ul>
        </div>
      {:else}
        <div class="step-content">
          <p class="step-text">
            {#each stepSegments as segment}
              {#if segment.type === 'text'}
                {segment.text}
              {:else}
                <TimerChip
                  label={segment.match.label}
                  totalSeconds={segment.match.totalSeconds}
                  running={isMatchRunning(segment.match)}
                  remainingSeconds={getMatchRemaining(segment.match)}
                  on:start={(e) => startTimer(e.detail.totalSeconds, e.detail.label, segment.match)}
                />
              {/if}
            {/each}
          </p>
        </div>
      {/if}

      <div class="step-nav" class:has-timer-bar={hasTimerBar}>
        <button class="nav-btn" on:click={prevStep} disabled={currentStep === 0}>
          Previous
        </button>
        <button
          class="nav-btn nav-next"
          on:click={nextStep}
          disabled={showNotes}
        >
          {currentStep === totalSteps - 1 ? (notes.length > 0 ? 'View Notes' : 'Done') : 'Next'}
        </button>
      </div>
    </div>
  </div>

  <button class="drawer-toggle" class:has-timer-bar={hasTimerBar} on:click={() => drawerOpen = !drawerOpen}>
    Ingredients ({checkedCount}/{ingredients.length})
  </button>

  {#if drawerOpen}
    <button class="drawer-backdrop" on:click={() => drawerOpen = false}></button>
    <div class="drawer">
      <div class="drawer-handle"></div>
      <h3 class="panel-heading">Ingredients ({checkedCount}/{ingredients.length})</h3>
      <ul class="ingredient-list">
        {#each ingredients as item, i}
          <li class="ingredient-item" class:checked={checkedIngredients.has(i)}>
            <label>
              <input type="checkbox" checked={checkedIngredients.has(i)} on:change={() => toggleIngredient(i)} />
              <span>{item}</span>
            </label>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <TimerBar {timers} on:dismiss={(e) => dismissTimer(e.detail.id)} />
</div>

<style>
  .cook-mode {
    position: fixed;
    inset: 0;
    z-index: 300;
    background: var(--color-bg);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .cook-topbar {
    display: flex;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    gap: 1rem;
    flex-shrink: 0;
  }

  .cook-title {
    font-size: 1rem;
    font-weight: 600;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cook-progress {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    white-space: nowrap;
  }

  .cook-exit {
    padding: 0.4rem 0.8rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.85rem;
    cursor: pointer;
    white-space: nowrap;
  }

  .cook-exit:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .cook-layout {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  .ingredients-panel {
    width: 35%;
    max-width: 320px;
    padding: 1.5rem 1rem;
    border-right: 1px solid var(--color-border);
    overflow-y: auto;
    flex-shrink: 0;
  }

  .panel-heading {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 1rem;
  }

  .ingredient-list {
    list-style: none;
    padding: 0;
  }

  .ingredient-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
  }

  .ingredient-item label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    font-size: 1rem;
    min-height: 48px;
  }

  .ingredient-item input[type="checkbox"] {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    accent-color: var(--color-accent);
  }

  .ingredient-item.checked span {
    text-decoration: line-through;
    opacity: 0.5;
  }

  .step-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .step-content {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    overflow-y: auto;
  }

  .step-text {
    font-size: 1.4rem;
    line-height: 1.8;
    max-width: 600px;
    text-align: center;
  }

  .notes-heading {
    font-size: 1.2rem;
    margin-bottom: 1rem;
  }

  .notes-list {
    font-size: 1.1rem;
    line-height: 1.8;
    padding-left: 1.5rem;
  }

  .notes-list li {
    margin-bottom: 0.75rem;
  }

  .step-nav {
    display: flex;
    gap: 0.5rem;
    padding: 1rem;
    border-top: 1px solid var(--color-border);
    flex-shrink: 0;
  }

  .step-nav.has-timer-bar {
    padding-bottom: calc(1rem + 60px);
  }

  .nav-btn {
    flex: 1;
    padding: 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    font-size: 1rem;
    cursor: pointer;
    min-height: 48px;
    transition: all 0.15s;
  }

  .nav-btn:hover:not(:disabled) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .nav-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .nav-next {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .nav-next:hover:not(:disabled) {
    opacity: 0.9;
    color: white;
  }

  .drawer-toggle {
    display: none;
  }

  .drawer-backdrop {
    display: none;
  }

  .drawer {
    display: none;
  }

  @media (max-width: 768px) {
    .ingredients-panel {
      display: none;
    }

    .step-text {
      font-size: 1.2rem;
    }

    .drawer-toggle {
      display: block;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 0.75rem;
      background: var(--color-surface);
      border-top: 1px solid var(--color-border);
      text-align: center;
      font-size: 0.85rem;
      color: var(--color-text-muted);
      cursor: pointer;
      z-index: 250;
      border-left: none;
      border-right: none;
      border-bottom: none;
    }

    .drawer-toggle.has-timer-bar {
      bottom: 60px;
    }

    .step-nav {
      padding-bottom: calc(1rem + 48px);
    }

    .step-nav.has-timer-bar {
      padding-bottom: calc(1rem + 108px);
    }

    .drawer-backdrop {
      display: block;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.3);
      z-index: 260;
      border: none;
      cursor: pointer;
    }

    .drawer {
      display: block;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      max-height: 60vh;
      background: var(--color-surface);
      border-top-left-radius: 12px;
      border-top-right-radius: 12px;
      box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.12);
      z-index: 270;
      padding: 1rem 1.5rem;
      overflow-y: auto;
    }

    .drawer-handle {
      width: 32px;
      height: 4px;
      background: var(--color-border);
      border-radius: 2px;
      margin: 0 auto 1rem;
    }
  }
</style>
