import { useEffect, useState } from 'react';

// "Go to latest": an older card asks the page to show its latest related card (the engine's latest_item_id,
// never a guess). The page clears the counter filter if that hides it, then scrolls to the card and opens it.
const GO_LATEST = 'pricewatch:go-latest';
export const OPEN_EVENT = 'pricewatch:open-card';

export function requestLatest(id) {
  window.dispatchEvent(new CustomEvent(GO_LATEST, { detail: id }));
}

function openCard(id) {
  window.dispatchEvent(new CustomEvent(OPEN_EVENT, { detail: id }));
  const target = document.querySelector(`[data-card-id="${CSS.escape(id)}"]`);
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// items: the cards in the current date and company filter, before the counter filter.
// Returns the id of a latest card that isn't in them (outside the date range or company), or null.
export function useGoToLatest(items, view, setView) {
  const [wanted, setWanted] = useState(null);
  const [ready, setReady] = useState(null);

  useEffect(() => {
    const onRequest = (event) => setWanted(event.detail);
    window.addEventListener(GO_LATEST, onRequest);
    return () => window.removeEventListener(GO_LATEST, onRequest);
  }, []);

  // Once the card is among the filtered cards, drop the counter filter if it's on, then open it.
  useEffect(() => {
    if (!wanted || !items.some((item) => item.id === wanted)) return;
    if (view) setView('');
    setReady(wanted);
    setWanted(null);
  }, [wanted, items, view, setView]);

  useEffect(() => {
    if (!ready) return undefined;
    const timer = setTimeout(() => {
      openCard(ready);
      setReady(null);
    }, 50);
    return () => clearTimeout(timer);
  }, [ready]);

  return { outsideFilter: wanted, dismiss: () => setWanted(null) };
}
