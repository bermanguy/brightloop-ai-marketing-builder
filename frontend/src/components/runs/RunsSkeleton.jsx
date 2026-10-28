import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';

export default function RunsSkeleton() {
  return (
    <div className="space-y-3">
      {[0, 1, 2, 3].map((key) => (
        <div key={key} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <Skeleton className="h-2.5 w-2.5 rounded-full" />
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="ml-auto h-4 w-40" />
          </div>
        </div>
      ))}
    </div>
  );
}