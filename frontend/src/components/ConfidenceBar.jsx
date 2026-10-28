import React from 'react';
import { cn } from '@/lib/utils';

export default function ConfidenceBar({ value, className }) {
  const numeric = Number(value);
  const width = Number.isFinite(numeric) ? Math.max(0, Math.min(1, numeric)) * 100 : 0;

  return (
    <span className={cn('flex items-center gap-1.5', className)} title={`Confidence ${value}`}>
      <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400">Conf.</span>
      <span className="h-1.5 w-12 overflow-hidden rounded-full bg-slate-200">
        <span
          className="block h-full rounded-full bg-slate-400 transition-[width] duration-500 ease-out"
          style={{ width: `${width}%` }}
        />
      </span>
    </span>
  );
}