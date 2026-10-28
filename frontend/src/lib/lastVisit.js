const STORAGE_KEY = 'brightloop-pricing-watch:last-visit';

let cachedPreviousVisit = null;
let alreadyRead = false;

/**
 * Returns the moment of the previous visit and stores the current one.
 * Read once per browser session so cards that arrive while the tab is open
 * still count as new.
 */
export function readPreviousVisit() {
  if (!alreadyRead) {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    window.localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    cachedPreviousVisit = stored;
    alreadyRead = true;
  }
  return cachedPreviousVisit;
}

export function isNewSinceVisit(seenAt, previousVisit) {
  if (!seenAt || !previousVisit) return false;
  return new Date(seenAt).getTime() > new Date(previousVisit).getTime();
}