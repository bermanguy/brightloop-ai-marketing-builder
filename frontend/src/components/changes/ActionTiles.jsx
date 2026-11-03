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
              title={`${group.label}: ${group.hint}`}
              onClick={() => onSelectView(active ? '' : group.key)}
              className={cn(
                'flex flex-col justify-start rounded-xl border bg-white p-3 text-left shadow-sm transition-all duration-200 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 sm:p-5',
                active ? 'border-indigo-400 ring-1 ring-indigo-200' : 'border-slate-200'
              )}
            >
              <div className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{counts[group.key]}</div>
              <div className="mt-1 text-[11px] font-medium uppercase leading-tight tracking-wide text-slate-500 sm:text-xs">{group.label}</div>
              <div className="mt-0.5 hidden text-xs leading-snug text-slate-400 sm:block">{group.hint}</div>
            </button>
          );
        })}
      </div>
      <p className="text-xs leading-relaxed text-slate-500">
        {items.length} detected change {items.length === 1 ? 'card' : 'cards'} in this view (cards, not unique business
        issues): {counts.investigate} {counts.investigate === 1 ? 'needs' : 'need'} investigation, and {verified} have
        source-verified evidence. Other changes are earlier repeats, page-only edits, unverified claims and cards not
        fully interpreted; that doesn&apos;t mean they were judged unimportant.
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
