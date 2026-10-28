import React from 'react';
import { cn } from '@/lib/utils';
import CompetitorAvatar from '@/components/CompetitorAvatar';

export default function PricingControls({ competitors, competitor, onCompetitorChange, views, view, opensOn, onViewChange }) {
  const showViewToggle = views.length > 1;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-1 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
        {competitors.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => onCompetitorChange(name)}
            className={cn(
              'inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors',
              name === competitor
                ? 'bg-indigo-50 text-indigo-700'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            )}
          >
            <CompetitorAvatar competitor={name} size="sm" />
            {name}
          </button>
        ))}
      </div>

      {showViewToggle ? (
        <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {views.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => onViewChange(name)}
              className={cn(
                'rounded-lg px-3 py-1.5 text-center transition-colors',
                name === view
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              )}
            >
              <span className="block text-sm font-medium">{name}</span>
              {name === opensOn ? (
                <span className="block text-[10px] leading-tight text-slate-400">
                  default on their page
                </span>
              ) : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}