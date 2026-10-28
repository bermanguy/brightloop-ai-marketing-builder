import React from 'react';
import { cn } from '@/lib/utils';

export default function StatTile({ label, value, active, onClick, size = 'lg', icon, className }) {
  const isLarge = size === 'lg';

  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'rounded-xl border bg-white text-left shadow-sm transition-all duration-200 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400',
        isLarge ? 'p-5' : 'min-w-[104px] p-3.5',
        active ? 'border-indigo-400 ring-1 ring-indigo-200' : 'border-slate-200',
        className
      )}
    >
      <div
        className={cn(
          'font-semibold tracking-tight text-slate-900',
          isLarge ? 'text-3xl' : 'text-xl'
        )}
      >
        {value}
      </div>
      <div className={cn('flex items-center gap-2', isLarge ? 'mt-1' : 'mt-1.5')}>
        {icon}
        <span
          className={cn(
            'text-slate-500',
            isLarge ? 'text-xs font-medium uppercase tracking-wide' : 'text-[11px] font-medium'
          )}
        >
          {label}
        </span>
      </div>
    </button>
  );
}