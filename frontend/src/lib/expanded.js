// Which change cards are open, by card id, for this browser tab. A convenience only: if storage is
// blocked the cards still work and simply start collapsed.
const KEY = 'pricewatch.expandedCards';
let memory = null;

function read() {
  if (memory) return memory;
  try {
    memory = new Set(JSON.parse(window.sessionStorage.getItem(KEY) || '[]'));
  } catch {
    memory = new Set();
  }
  return memory;
}

export function isExpanded(id) {
  return Boolean(id) && read().has(id);
}

export function setExpanded(id, open) {
  if (!id) return;
  const ids = read();
  if (open) ids.add(id);
  else ids.delete(id);
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify([...ids]));
  } catch {
    // Storage blocked: keep it in memory for this page view.
  }
}
