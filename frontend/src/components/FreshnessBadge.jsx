import React, { useEffect, useState } from 'react';
import { fetchRuns, newestStartedAt } from '@/api/pricewatch';
import RelativeTime from '@/components/RelativeTime';
import { cn } from '@/lib/utils';

const FRESH_HOURS = 7;

export default function FreshnessBadge() {
  const [startedAt, setStartedAt] = useState(null);
  const [, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    fetchRuns()
      .then((runs) => {
        if (cancelled) return;
        setStartedAt(newestStartedAt(runs) || null);
      })
      .catch(() => {});

    const id = setInterval(() => setTick((tick) => tick + 1), 60000);
    return () => {
      cancelled = true;
      clearInterval(id);
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