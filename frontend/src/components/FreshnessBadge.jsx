import React, { useEffect, useState } from 'react';
import { fetchRuns, newestStartedAt } from '@/api/pricewatch';
import RelativeTime from '@/components/RelativeTime';
import { cn } from '@/lib/utils';

const FRESH_HOURS = 7;
const RELOAD_EVERY_MS = 5 * 60 * 1000;

export default function FreshnessBadge() {
  const [startedAt, setStartedAt] = useState(null);
  const [, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    // Ask the engine again every few minutes and whenever the tab comes back into view,
    // so a tab left open doesn't keep showing the run it saw when it was opened.
    const load = () =>
      fetchRuns()
        .then((runs) => {
          if (cancelled) return;
          setStartedAt(newestStartedAt(runs) || null);
        })
        .catch(() => {});
    const onVisible = () => {
      if (document.visibilityState === 'visible') load();
    };

    load();
    const reload = setInterval(load, RELOAD_EVERY_MS);
    const tick = setInterval(() => setTick((n) => n + 1), 60000);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      cancelled = true;
      clearInterval(reload);
      clearInterval(tick);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  if (!startedAt) return null;

  const stale = Date.now() - new Date(startedAt).getTime() > FRESH_HOURS * 60 * 60 * 1000;

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
      <span
        className={cn('h-2 w-2 shrink-0 rounded-full', stale ? 'bg-amber-500' : 'bg-emerald-500')}
      />
      <RelativeTime
        value={startedAt}
        prefix="Last checked "
        suffix={stale ? ', may be out of date' : ''}
      />
    </span>
  );
}