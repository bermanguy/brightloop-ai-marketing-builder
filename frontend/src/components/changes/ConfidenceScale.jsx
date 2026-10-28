import React from 'react';
import { cn } from '@/lib/utils';

const SCALE = [
  { value: '0.9', label: 'own pricing page', bar: 'w-full bg-indigo-500' },
  { value: '0.6', label: 'own site', bar: 'w-2/3 bg-indigo-400' },
  { value: '0.4', label: 'third party', bar: 'w-1/3 bg-indigo-300' },
  { value: '0.2', label: 'rumor (unverified)', bar: 'w-1.5 bg-indigo-200' },
];

export default function ConfidenceScale() {
  return (
    <ul className="flex h-full flex-col justify-center gap-1">
      {SCALE.map((step) => (
        <li key={step.value} className="flex items-center gap-1.5">
          <span className="w-5 shrink-0 text-right text-[10px] font-semibold tabular-nums text-slate-700">
            {step.value}
          </span>
          <span className="w-5 shrink-0">
            <span className={cn('block h-1 rounded-full', step.bar)} />
          </span>
          <span className="text-[10px] leading-tight text-slate-500">{step.label}</span>
        </li>
      ))}
    </ul>
  );
}