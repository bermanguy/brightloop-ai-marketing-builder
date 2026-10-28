import React from 'react';
import { cn } from '@/lib/utils';

export default function FlowStep({ icon: Icon, title, caption, children, className }) {
  return (
    <div
      className={cn(
        'flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm',
        className
      )}
    >
      <div className="flex h-7 items-center gap-2">
        <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
          <Icon className="h-4 w-4" />
        </span>
        <span className="truncate text-[15px] font-semibold text-slate-900">{title}</span>
      </div>

      <div className="mt-2.5 h-24 overflow-hidden">{children}</div>

      <p className="mt-auto pt-2 text-[13px] font-normal leading-[1.4] text-slate-600">
        {caption}
      </p>
    </div>
  );
}