import React from 'react';
import CompetitorAvatar from '@/components/CompetitorAvatar';

const COMPETITORS = ['Lovable', 'Bolt', 'Replit', 'v0'];

export default function ScanVisual() {
  return (
    <div className="flex h-full flex-col justify-center gap-2">
      <div className="relative w-fit overflow-hidden rounded-md">
        <div className="flex items-center gap-1">
          {COMPETITORS.map((name) => (
            <CompetitorAvatar key={name} competitor={name} className="h-7 w-7" />
          ))}
        </div>
        <span className="scan-line pointer-events-none absolute inset-y-0 left-0 w-px bg-indigo-500/70" />
      </div>

      <span className="inline-flex w-fit items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[9px] font-medium text-amber-700">
        <span className="h-1 w-1 rounded-full bg-amber-500" />
        Hacker News
      </span>
    </div>
  );
}