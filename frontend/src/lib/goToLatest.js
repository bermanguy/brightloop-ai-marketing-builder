import { useEffect, useState } from 'react';

// "Go to latest": an older card asks the page to show its latest related card (the engine's latest_item_id,
// never a guess). If Focused view hides that card, the page switches to All changes, then scrolls to the card
// and opens it.
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

// items: the cards in the current date and company filter. shown: the cards on screen now.
// showAll: switches to All changes. Returns the id of a latest card outside the date or company filter, or null.
export function useGoToLatest(items, shown, showAll) {
  const [wanted, setWanted] = useState(null);
  const [ready, setReady] = useState(null);

  useEffect(() => {
    const onRequest = (event) => setWanted(event.detail);
    window.addEventListener(GO_LATEST, onRequest);
    return () => window.removeEventListener(GO_LATEST, onRequest);
  }, []);

  // Once the card is among the filtered cards, show it if Focused view hides it, then open it.
  useEffect(() => {
    if (!wanted || !items.some((item) => item.id === wanted)) return;
    if (!shown.some((item) => item.id === wanted)) showAll();
    setReady(wanted);
    setWanted(null);
  }, [wanted, items, shown, showAll]);

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
