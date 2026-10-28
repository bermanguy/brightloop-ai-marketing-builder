import React from 'react';
import { AlertTriangle } from 'lucide-react';
import RelativeTime from '@/components/RelativeTime';

export default function UnreadPageNotice({ page }) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-relaxed text-amber-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div>
        Couldn&apos;t read this page at <RelativeTime value={page.fetched_at} />: {page.error}
      </div>
    </div>
  );
}