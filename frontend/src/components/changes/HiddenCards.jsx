import React, { useState } from 'react';
import { ChevronDown, Undo2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { restoreAll, setHidden } from '@/lib/hidden';
import Markup from '@/components/Markup';
import RelativeTime from '@/components/RelativeTime';

// "Show hidden (N)" below the feed: the hidden cards in the current filter, each with Restore, and
// "Restore all hidden" behind a confirmation. Restoring only shows a card in Focused view again.
export default function HiddenCards({ items, hiddenTotal }) {
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  if (hiddenTotal === 0) return null;
  const outside = hiddenTotal - items.length;

  return (
    <section className="rounded-xl border border-dashed border-slate-300 bg-white/60 p-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} />
        Show hidden ({items.length})
      </button>
      {open ? (
        <div className="mt-3 space-y-2">
          {items.length === 0 ? (
            <p className="text-xs text-slate-500">No hidden cards in the current date and company filter.</p>
          ) : (
            <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
              {items.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-3 px-3 py-2">
                  <div className="min-w-0 text-sm">
                    <div className="text-xs text-slate-500">
                      {item.competitor} · <RelativeTime value={item.seen_at} />
                    </div>
                    <div className="break-words text-slate-700">
                      <Markup text={item.display_headline || item.headline} />
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setHidden(item.id, false)}
                    className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-indigo-600 hover:underline"
                  >
                    <Undo2 className="h-3.5 w-3.5" />
                    Restore
                  </button>
                </li>
              ))}
            </ul>
          )}
          {confirming ? (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-700">
              <span>
                Restore all {hiddenTotal} hidden {hiddenTotal === 1 ? 'card' : 'cards'}
                {outside > 0 ? `, including ${outside} outside the current filter` : ''}?
              </span>
              <button
                type="button"
                onClick={() => {
                  restoreAll();
                  setConfirming(false);
                }}
                className="rounded-md bg-indigo-600 px-2 py-1 font-medium text-white hover:bg-indigo-700"
              >
                Restore all
              </button>
              <button type="button" onClick={() => setConfirming(false)} className="text-slate-500 hover:underline">
                Cancel
              </button>
            </div>
          ) : (
            <button type="button" onClick={() => setConfirming(true)} className="text-xs font-medium text-slate-600 hover:underline">
              Restore all hidden
            </button>
          )}
        </div>
      ) : null}
    </section>
  );
}
