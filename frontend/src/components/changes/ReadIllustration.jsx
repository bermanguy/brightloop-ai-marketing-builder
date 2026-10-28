import React from 'react';
import { Check } from 'lucide-react';
import ExampleTag from '@/components/changes/ExampleTag';

export default function ReadIllustration() {
  return (
    <div className="relative h-full">
      <ExampleTag />
      <div className="mt-4 rounded-lg border border-slate-200 bg-white p-2">
        <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">Pro</p>
        <p className="mt-1 text-[13px] font-semibold leading-none text-slate-900">
          $25 <span className="text-[9px] font-normal text-slate-500">/ month</span>
        </p>
        <span className="mt-2 inline-flex items-center gap-1 rounded bg-emerald-50 px-1 py-0.5 text-[9px] font-medium text-emerald-700">
          <Check className="h-2.5 w-2.5 shrink-0" />
          matches page text
        </span>
      </div>
    </div>
  );
}