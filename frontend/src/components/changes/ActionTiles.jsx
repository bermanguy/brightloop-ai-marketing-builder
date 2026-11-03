import React from 'react';
import { cn } from '@/lib/utils';
import { ACTION_GROUPS, countGroups } from '@/lib/actionGroups';

// The counters above the feed, counted from the cards in the current date and company filter.
// Clicking one shows only its cards; clicking it again shows all of them.
export default function ActionTiles({ items, view, onSelectView }) {
  const counts = countGroups(items);
  const verified = items.filter((item) => !item.unverified).length;

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        {ACTION_GROUPS.map((group) => {
          const active = view === group.key;
          return (
            <button
              key={group.key}
              type="button"
              aria-pressed={active}
              onClick={() => onSelectView(active ? '' : group.key)}
              className={cn(
                'rounded-xl border bg-white p-3 text-left shadow-sm transition-all duration-200 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 sm:p-5',
                active ? 'border-indigo-400 ring-1 ring-indigo-200' : 'border-slate-200'
              )}
            >
              <div className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{counts[group.key]}</div>
              <div className="mt-1 text-[11px] font-medium uppercase leading-tight tracking-wide text-slate-500 sm:text-xs">{group.label}</div>
              <div className="mt-0.5 hidden text-xs text-slate-400 sm:block">{group.hint}</div>
            </button>
          );
        })}
      </div>
      <p className="text-xs text-slate-500">
        Counts are change cards in this view. {verified} of {items.length} are source verified.
        {view ? (
          <>
            {' '}
            <button type="button" onClick={() => onSelectView('')} className="font-medium text-indigo-600 hover:underline">
              Show all
            </button>
          </>
        ) : null}
      </p>
    </div>
  );
}
