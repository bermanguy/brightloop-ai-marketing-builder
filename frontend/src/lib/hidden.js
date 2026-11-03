import { useSyncExternalStore } from 'react';

// Cards hidden from Focused view, by card id, plus the chosen view. Browser-specific: kept in this browser's
// localStorage only and never sent to the server, so hiding a card doesn't change the change itself, the
// monitoring history, the counters, the API, MCP, the scans or the alerts. If storage is blocked it still
// works for this page view.
const HIDDEN_KEY = 'pricewatch.hiddenCards';
const VIEW_KEY = 'pricewatch.feedView';
const listeners = new Set();
let hidden = load();

function load() {
  try {
    const ids = JSON.parse(window.localStorage.getItem(HIDDEN_KEY) || '[]');
    return new Set(Array.isArray(ids) ? ids.filter((id) => typeof id === 'string') : []);
  } catch {
    return new Set();
  }
}

function save(next) {
  hidden = next;
  try {
    window.localStorage.setItem(HIDDEN_KEY, JSON.stringify([...next]));
  } catch {
    // Storage blocked: keep it in memory for this page view.
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useHiddenIds() {
  return useSyncExternalStore(subscribe, () => hidden);
}

export function setHidden(id, value) {
  if (!id || hidden.has(id) === value) return;
  const next = new Set(hidden);
  if (value) next.add(id);
  else next.delete(id);
  save(next);
}

export function restoreAll() {
  save(new Set());
}

// 'all' (the default for a new browser) or 'focused'.
export function readFeedView() {
  try {
    return window.localStorage.getItem(VIEW_KEY) === 'focused' ? 'focused' : 'all';
  } catch {
    return 'all';
  }
}

export function saveFeedView(view) {
  try {
    window.localStorage.setItem(VIEW_KEY, view);
  } catch {
    // Storage blocked: the view still changes for this page view.
  }
}
