import React from 'react';
import { ArrowRight, ArrowUp } from 'lucide-react';
import ExampleTag from '@/components/changes/ExampleTag';

export default function CompareIllustration() {
  return (
    <div className="relative flex h-full flex-col justify-center gap-2">
      <ExampleTag />
      <div className="flex items-center gap-1.5">
        <span className="text-[11px] font-medium text-slate-400 line-through">$20</span>
        <ArrowRight className="h-3 w-3 shrink-0 text-slate-300" />
        <span className="text-[13px] font-semibold leading-none text-slate-900">$25</span>
        <span className="text-[9px] text-slate-500">/ month</span>
      </div>
      <span className="inline-flex w-fit items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-[9px] font-medium text-amber-700">
        <ArrowUp className="h-2.5 w-2.5 shrink-0" />
        Price up
      </span>
    </div>
  );
}