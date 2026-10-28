import React from 'react';
import { AlertTriangle } from 'lucide-react';
import CompetitorAvatar from '@/components/CompetitorAvatar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const RANGES = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: 'all', label: 'All time' },
];

export default function FilterBar({
  days,
  onDaysChange,
  competitor,
  onCompetitorChange,
  competitors = [],
  failedPages = [],
  summaryLine,
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white/95 p-3 shadow-sm backdrop-blur">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={days} onValueChange={onDaysChange}>
          <SelectTrigger className="h-9 w-[142px] rounded-lg text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {RANGES.map((range) => (
              <SelectItem key={range.value} value={range.value}>
                {range.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={competitor || 'all'}
          onValueChange={(value) => onCompetitorChange(value === 'all' ? '' : value)}
        >
          <SelectTrigger className="h-9 w-[170px] rounded-lg text-sm">
            <span className="flex min-w-0 items-center gap-1.5">
              {competitor ? <CompetitorAvatar competitor={competitor} size="sm" /> : null}
              <span className="truncate">{competitor || 'All companies'}</span>
            </span>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All companies</SelectItem>
            {competitors.map((name) => (
              <SelectItem key={name} value={name}>
                <span className="flex items-center gap-2">
                  <CompetitorAvatar competitor={name} size="sm" />
                  {name}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {failedPages.length > 0 ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
              <AlertTriangle className="h-3.5 w-3.5" />
              Couldn&apos;t read {failedPages.join(', ')}
            </span>
          ) : null}
        </div>
      </div>

      {summaryLine ? (
        <div className="mt-2.5 border-t border-slate-100 pt-2.5 text-xs font-medium text-slate-500">
          {summaryLine}
        </div>
      ) : null}
    </div>
  );
}