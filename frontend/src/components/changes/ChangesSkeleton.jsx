import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';

export default function ChangesSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[0, 1, 2].map((key) => (
          <div key={key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <Skeleton className="h-8 w-14" />
            <Skeleton className="mt-2 h-3 w-24" />
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {[0, 1, 2].map((key) => (
          <div key={key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="space-y-1.5">
                <Skeleton className="h-3.5 w-24" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
            <Skeleton className="mt-4 h-4 w-3/4" />
            <Skeleton className="mt-3 h-16 w-full rounded-lg" />
          </div>
        ))}
      </div>
    </div>
  );
}