import React from 'react';
import { cn } from '@/lib/utils';

export default function EmptyState({ icon: Icon, title, description, className }) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white/70 px-6 py-14 text-center',
        className
      )}
    >
      {Icon ? (
        <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
          <Icon className="h-5 w-5" />
        </span>
      ) : null}
      <div className="text-sm font-medium text-slate-700">{title}</div>
      {description ? <div className="mt-1 max-w-sm text-sm text-slate-500">{description}</div> : null}
    </div>
  );
}