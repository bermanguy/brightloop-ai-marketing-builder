import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
      <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-amber-50 text-amber-500">
        <AlertTriangle className="h-5 w-5" />
      </span>
      <div className="text-sm font-medium text-slate-700">That didn&apos;t load</div>
      {message ? <div className="mt-1 max-w-md text-sm text-slate-500">{message}</div> : null}
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-4 rounded-lg" onClick={onRetry}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Try again
        </Button>
      ) : null}
    </div>
  );
}