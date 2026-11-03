import React from 'react';
import { cn } from '@/lib/utils';

const VIEWS = [
  { key: 'all', label: 'All changes' },
  { key: 'focused', label: 'Focused view' },
];

// All changes is the full monitoring history; Focused view is a personal filter that leaves out hidden cards.
export default function FeedViewSelector({ view, onChange, total, hiddenCount }) {
  const focusedCount = total - hiddenCount;
  return (
    <div className="space-y-2">
      <div role="tablist" aria-label="Feed view" className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 shadow-sm">
        {VIEWS.map((option) => {
          const active = view === option.key;
          return (
            <button
              key={option.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onChange(option.key)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300',
                active ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
              )}
            >
              {option.label}
              <span className={cn('ml-1.5 text-xs', active ? 'text-indigo-100' : 'text-slate-400')}>
                {option.key === 'all' ? total : focusedCount}
              </span>
            </button>
          );
        })}
      </div>
      {view === 'focused' ? (
        <p className="rounded-lg border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs leading-relaxed text-indigo-900">
          <span className="font-semibold">Focused view</span> is your personal filter in this browser: showing{' '}
          {focusedCount} of {total} changes, {hiddenCount} hidden. The full monitoring history stays in All changes.
        </p>
      ) : null}
    </div>
  );
}
