import React from 'react';
import { Check } from 'lucide-react';
import ExampleTag from '@/components/changes/ExampleTag';

export default function ReportIllustration() {
  return (
    <div className="relative h-full">
      <ExampleTag />
      <div className="relative mt-3.5 rounded-lg border border-slate-200 bg-white p-1.5">
        <div className="flex items-center gap-1">
          <span className="h-3 w-3 shrink-0 rounded-full bg-slate-200" />
          <span className="truncate text-[10px] font-semibold text-slate-900">Pro plan raised</span>
        </div>

        <p className="mt-0.5 border-l-2 border-slate-200 pl-1.5 text-[9px] italic leading-tight text-slate-500">
          "$25 / month"
        </p>

        <span className="mt-0.5 inline-block rounded-full border border-slate-200 bg-slate-50 px-1.5 text-[9px] font-medium text-indigo-600">
          View source
        </span>

        <ul className="mt-0.5 space-y-0.5 text-[8px] leading-tight text-slate-500">
          <li>Review margin</li>
          <li>Update comparison</li>
        </ul>

        <span className="absolute bottom-1 right-1 inline-flex items-center gap-0.5 rounded bg-emerald-50 px-1 text-[8px] font-semibold text-emerald-700">
          <Check className="h-2 w-2 shrink-0" />
          Verified
        </span>
      </div>
    </div>
  );
}